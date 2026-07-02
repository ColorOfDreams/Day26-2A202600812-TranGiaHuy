from __future__ import annotations

import json

try:
    from .db import SQLiteAdapter, ValidationError
    from .init_db import create_database
except ImportError:
    from db import SQLiteAdapter, ValidationError
    from init_db import create_database


def main() -> None:
    create_database(reset=True)
    adapter = SQLiteAdapter()

    checks = {
        "tables": adapter.list_tables(),
        "schema_resource_payload": json.loads(adapter.schema_json())["tables"],
        "search_students_a1": adapter.search(
            "students",
            filters={"cohort": "A1"},
            columns=["id", "name", "cohort", "gpa"],
            order_by="gpa",
            descending=True,
        ),
        "insert_student": adapter.insert(
            "students",
            {
                "name": "Mai Phuong",
                "cohort": "A1",
                "email": "phuong.mai@example.edu",
                "gpa": 3.66,
            },
        ),
        "count_students": adapter.aggregate("students", "count"),
        "avg_gpa_by_cohort": adapter.aggregate("students", "avg", column="gpa", group_by="cohort"),
        "avg_score_filtered": adapter.aggregate(
            "enrollments",
            "avg",
            column="score",
            filters={"score": {"gte": 80}},
        ),
    }

    try:
        adapter.search("missing_table")
    except ValidationError as exc:
        checks["invalid_table_error"] = str(exc)

    try:
        adapter.aggregate("students", "median", column="gpa")
    except ValidationError as exc:
        checks["invalid_metric_error"] = str(exc)

    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
