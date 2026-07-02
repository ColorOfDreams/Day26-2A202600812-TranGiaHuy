from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

try:
    from .init_db import DATABASE_PATH, create_database
except ImportError:  # Allows running files directly from implementation/.
    from init_db import DATABASE_PATH, create_database


class ValidationError(Exception):
    """Raised when a request cannot be safely executed."""


class SQLiteAdapter:
    """Small validated SQLite adapter for the lab MCP tools."""

    ALLOWED_OPERATORS = {"eq", "ne", "lt", "lte", "gt", "gte", "like", "contains", "in", "is_null"}
    ALLOWED_METRICS = {"count", "avg", "sum", "min", "max"}

    def __init__(self, db_path: str | Path | None = None, initialize: bool = True):
        self.db_path = Path(db_path) if db_path is not None else DATABASE_PATH
        if initialize and not self.db_path.exists():
            create_database(self.db_path)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def list_tables(self) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        return [row["name"] for row in rows]

    def get_table_schema(self, table: str) -> dict[str, Any]:
        table = self._validate_table(table)
        with self.connect() as conn:
            rows = conn.execute(f"PRAGMA table_info({self._quote_identifier(table)})").fetchall()

        return {
            "table": table,
            "columns": [
                {
                    "name": row["name"],
                    "type": row["type"],
                    "not_null": bool(row["notnull"]),
                    "default": row["dflt_value"],
                    "primary_key": bool(row["pk"]),
                }
                for row in rows
            ],
        }

    def get_database_schema(self) -> dict[str, Any]:
        return {"tables": [self.get_table_schema(table) for table in self.list_tables()]}

    def search(
        self,
        table: str,
        columns: list[str] | None = None,
        filters: dict[str, Any] | list[dict[str, Any]] | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict[str, Any]:
        table = self._validate_table(table)
        selected_columns = self._validate_selected_columns(table, columns)
        limit = self._validate_limit(limit)
        offset = self._validate_offset(offset)

        where_sql, params = self._build_where_clause(table, filters)
        sql = f"SELECT {', '.join(selected_columns)} FROM {self._quote_identifier(table)}"
        if where_sql:
            sql += f" WHERE {where_sql}"
        if order_by:
            sql += f" ORDER BY {self._quote_identifier(self._validate_column(table, order_by))}"
            sql += " DESC" if descending else " ASC"
        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.connect() as conn:
            rows = [dict(row) for row in conn.execute(sql, params).fetchall()]

        return {
            "table": table,
            "columns": [column.strip('"') for column in selected_columns],
            "rows": rows,
            "limit": limit,
            "offset": offset,
            "count": len(rows),
        }

    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]:
        table = self._validate_table(table)
        if not isinstance(values, dict) or not values:
            raise ValidationError("insert values must be a non-empty object")

        columns = [self._validate_column(table, column) for column in values.keys()]
        placeholders = ", ".join("?" for _ in columns)
        quoted_columns = ", ".join(self._quote_identifier(column) for column in columns)
        sql = f"INSERT INTO {self._quote_identifier(table)} ({quoted_columns}) VALUES ({placeholders})"

        with self.connect() as conn:
            cursor = conn.execute(sql, [values[column] for column in values.keys()])
            conn.commit()
            inserted_id = cursor.lastrowid
            row = conn.execute(
                f"SELECT * FROM {self._quote_identifier(table)} WHERE rowid = ?",
                [inserted_id],
            ).fetchone()

        return {
            "table": table,
            "inserted_id": inserted_id,
            "row": dict(row) if row is not None else dict(values),
        }

    def aggregate(
        self,
        table: str,
        metric: str,
        column: str | None = None,
        filters: dict[str, Any] | list[dict[str, Any]] | None = None,
        group_by: str | None = None,
    ) -> dict[str, Any]:
        table = self._validate_table(table)
        metric = self._validate_metric(metric)

        if metric == "count":
            metric_sql = "COUNT(*)"
            column_name = "*"
        else:
            if not column:
                raise ValidationError(f"metric '{metric}' requires a column")
            column_name = self._validate_column(table, column)
            metric_sql = f"{metric.upper()}({self._quote_identifier(column_name)})"

        select_parts = []
        if group_by:
            group_by = self._validate_column(table, group_by)
            select_parts.append(self._quote_identifier(group_by))
        select_parts.append(f"{metric_sql} AS value")

        where_sql, params = self._build_where_clause(table, filters)
        sql = f"SELECT {', '.join(select_parts)} FROM {self._quote_identifier(table)}"
        if where_sql:
            sql += f" WHERE {where_sql}"
        if group_by:
            sql += f" GROUP BY {self._quote_identifier(group_by)} ORDER BY {self._quote_identifier(group_by)}"

        with self.connect() as conn:
            rows = [dict(row) for row in conn.execute(sql, params).fetchall()]

        return {
            "table": table,
            "metric": metric,
            "column": column_name,
            "group_by": group_by,
            "rows": rows,
        }

    def schema_json(self, table: str | None = None) -> str:
        payload = self.get_table_schema(table) if table else self.get_database_schema()
        return json.dumps(payload, indent=2)

    def _validate_table(self, table: str) -> str:
        if not isinstance(table, str) or not table:
            raise ValidationError("table must be a non-empty string")
        tables = set(self.list_tables())
        if table not in tables:
            raise ValidationError(f"unknown table '{table}'. Available tables: {sorted(tables)}")
        return table

    def _validate_column(self, table: str, column: str) -> str:
        if not isinstance(column, str) or not column:
            raise ValidationError("column name must be a non-empty string")
        columns = {item["name"] for item in self.get_table_schema(table)["columns"]}
        if column not in columns:
            raise ValidationError(f"unknown column '{column}' for table '{table}'. Available columns: {sorted(columns)}")
        return column

    def _validate_selected_columns(self, table: str, columns: list[str] | None) -> list[str]:
        if columns is None:
            return [self._quote_identifier(column["name"]) for column in self.get_table_schema(table)["columns"]]
        if not isinstance(columns, list) or not columns:
            raise ValidationError("columns must be a non-empty list when provided")
        return [self._quote_identifier(self._validate_column(table, column)) for column in columns]

    def _validate_metric(self, metric: str) -> str:
        if not isinstance(metric, str) or metric.lower() not in self.ALLOWED_METRICS:
            raise ValidationError(f"unsupported metric '{metric}'. Allowed metrics: {sorted(self.ALLOWED_METRICS)}")
        return metric.lower()

    def _validate_limit(self, limit: int) -> int:
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            raise ValidationError("limit must be an integer between 1 and 100")
        return limit

    def _validate_offset(self, offset: int) -> int:
        if not isinstance(offset, int) or offset < 0:
            raise ValidationError("offset must be a non-negative integer")
        return offset

    def _build_where_clause(
        self,
        table: str,
        filters: dict[str, Any] | list[dict[str, Any]] | None,
    ) -> tuple[str, list[Any]]:
        if filters is None:
            return "", []

        clauses: list[str] = []
        params: list[Any] = []

        for column, operator, value in self._normalize_filters(filters):
            column = self._validate_column(table, column)
            operator = self._validate_operator(operator)
            quoted_column = self._quote_identifier(column)

            if operator == "eq":
                clauses.append(f"{quoted_column} = ?")
                params.append(value)
            elif operator == "ne":
                clauses.append(f"{quoted_column} != ?")
                params.append(value)
            elif operator == "lt":
                clauses.append(f"{quoted_column} < ?")
                params.append(value)
            elif operator == "lte":
                clauses.append(f"{quoted_column} <= ?")
                params.append(value)
            elif operator == "gt":
                clauses.append(f"{quoted_column} > ?")
                params.append(value)
            elif operator == "gte":
                clauses.append(f"{quoted_column} >= ?")
                params.append(value)
            elif operator == "like":
                clauses.append(f"{quoted_column} LIKE ?")
                params.append(value)
            elif operator == "contains":
                clauses.append(f"{quoted_column} LIKE ?")
                params.append(f"%{value}%")
            elif operator == "in":
                if not isinstance(value, list) or not value:
                    raise ValidationError("in operator requires a non-empty list value")
                clauses.append(f"{quoted_column} IN ({', '.join('?' for _ in value)})")
                params.extend(value)
            elif operator == "is_null":
                clauses.append(f"{quoted_column} IS {'NULL' if value else 'NOT NULL'}")

        return " AND ".join(clauses), params

    def _normalize_filters(self, filters: dict[str, Any] | list[dict[str, Any]]) -> list[tuple[str, str, Any]]:
        normalized: list[tuple[str, str, Any]] = []

        if isinstance(filters, dict):
            for column, expression in filters.items():
                if isinstance(expression, dict):
                    for operator, value in expression.items():
                        normalized.append((column, operator, value))
                else:
                    normalized.append((column, "eq", expression))
            return normalized

        if isinstance(filters, list):
            for item in filters:
                if not isinstance(item, dict):
                    raise ValidationError("each list filter must be an object")
                try:
                    column = item["column"]
                    value = item.get("value")
                except KeyError as exc:
                    raise ValidationError("list filters require a column field") from exc
                operator = item.get("operator", item.get("op", "eq"))
                normalized.append((column, operator, value))
            return normalized

        raise ValidationError("filters must be an object, a list, or null")

    def _validate_operator(self, operator: str) -> str:
        if not isinstance(operator, str) or operator not in self.ALLOWED_OPERATORS:
            raise ValidationError(f"unsupported operator '{operator}'. Allowed operators: {sorted(self.ALLOWED_OPERATORS)}")
        return operator

    def _quote_identifier(self, identifier: str) -> str:
        return f'"{identifier.replace(chr(34), chr(34) + chr(34))}"'
