from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

try:
    from .db import SQLiteAdapter, ValidationError
    from .init_db import create_database
except ImportError:  # Allows: python implementation/mcp_server.py
    from db import SQLiteAdapter, ValidationError
    from init_db import create_database


create_database(reset=False)
adapter = SQLiteAdapter()
mcp = FastMCP("SQLite Lab MCP Server")


def _friendly_error(exc: ValidationError) -> ValueError:
    return ValueError(str(exc))


@mcp.tool(name="search")
def search(
    table: str,
    filters: dict[str, Any] | list[dict[str, Any]] | None = None,
    columns: list[str] | None = None,
    limit: int = 20,
    offset: int = 0,
    order_by: str | None = None,
    descending: bool = False,
) -> dict[str, Any]:
    """Search rows in a known table with validated filters, ordering, and pagination."""
    try:
        return adapter.search(
            table=table,
            columns=columns,
            filters=filters,
            limit=limit,
            offset=offset,
            order_by=order_by,
            descending=descending,
        )
    except ValidationError as exc:
        raise _friendly_error(exc) from exc


@mcp.tool(name="insert")
def insert(table: str, values: dict[str, Any]) -> dict[str, Any]:
    """Insert one row into a known table and return the inserted row."""
    try:
        return adapter.insert(table=table, values=values)
    except ValidationError as exc:
        raise _friendly_error(exc) from exc


@mcp.tool(name="aggregate")
def aggregate(
    table: str,
    metric: str,
    column: str | None = None,
    filters: dict[str, Any] | list[dict[str, Any]] | None = None,
    group_by: str | None = None,
) -> dict[str, Any]:
    """Compute count, avg, sum, min, or max over a known table."""
    try:
        return adapter.aggregate(
            table=table,
            metric=metric,
            column=column,
            filters=filters,
            group_by=group_by,
        )
    except ValidationError as exc:
        raise _friendly_error(exc) from exc


@mcp.resource("schema://database")
def database_schema() -> str:
    """Return the full SQLite schema as JSON text."""
    return adapter.schema_json()


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """Return one table schema as JSON text."""
    try:
        return adapter.schema_json(table_name)
    except ValidationError as exc:
        raise _friendly_error(exc) from exc


if __name__ == "__main__":
    mcp.run()
