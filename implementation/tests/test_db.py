import json

import pytest

from implementation.db import SQLiteAdapter, ValidationError
from implementation.init_db import create_database


@pytest.fixture()
def adapter(tmp_path):
    db_path = tmp_path / "sqlite_lab.db"
    create_database(db_path, reset=True)
    return SQLiteAdapter(db_path, initialize=False)


def test_search_filters_ordering_and_pagination(adapter):
    result = adapter.search(
        "students",
        filters={"cohort": "A1"},
        columns=["name", "cohort", "gpa"],
        order_by="gpa",
        descending=True,
        limit=1,
    )

    assert result["count"] == 1
    assert result["rows"][0]["name"] == "Nguyen Minh Anh"
    assert result["rows"][0]["cohort"] == "A1"


def test_search_supports_comparison_filters(adapter):
    result = adapter.search(
        "enrollments",
        filters={"score": {"gte": 90}},
        columns=["student_id", "score"],
        order_by="score",
        descending=True,
    )

    assert result["count"] == 5
    assert result["rows"][0]["score"] == 95.0


def test_insert_returns_inserted_row(adapter):
    result = adapter.insert(
        "students",
        {
            "name": "Mai Phuong",
            "cohort": "A2",
            "email": "phuong.mai@example.edu",
            "gpa": 3.5,
        },
    )

    assert result["inserted_id"] > 0
    assert result["row"]["email"] == "phuong.mai@example.edu"


def test_aggregate_count_and_average_by_group(adapter):
    count_result = adapter.aggregate("students", "count")
    avg_result = adapter.aggregate("students", "avg", column="gpa", group_by="cohort")

    assert count_result["rows"] == [{"value": 6}]
    assert {row["cohort"] for row in avg_result["rows"]} == {"A1", "A2", "B1"}


def test_schema_json_contains_expected_tables(adapter):
    schema = json.loads(adapter.schema_json())
    table_names = {table["table"] for table in schema["tables"]}

    assert {"students", "courses", "enrollments"} <= table_names


@pytest.mark.parametrize(
    "call",
    [
        lambda adapter: adapter.search("missing"),
        lambda adapter: adapter.search("students", columns=["not_a_column"]),
        lambda adapter: adapter.search("students", filters={"gpa": {"between": [3.0, 4.0]}}),
        lambda adapter: adapter.insert("students", {}),
        lambda adapter: adapter.aggregate("students", "median", column="gpa"),
        lambda adapter: adapter.aggregate("students", "avg"),
    ],
)
def test_invalid_requests_raise_validation_errors(adapter, call):
    with pytest.raises(ValidationError):
        call(adapter)
