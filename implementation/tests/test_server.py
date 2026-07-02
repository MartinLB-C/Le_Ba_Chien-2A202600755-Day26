import json
import pytest
from pathlib import Path
import sys

# Add implementation directory to sys.path for testing
sys.path.insert(0, str(Path(__file__).parent.parent))

from init_db import create_database
from db import SQLiteAdapter, ValidationError
from mcp_server import search, insert, aggregate, database_schema, table_schema


@pytest.fixture(scope="module")
def test_db():
    """Creates a temporary database seeded with test data inside the workspace."""
    test_dir = Path(__file__).parent.parent / ".test_tmp"
    test_dir.mkdir(exist_ok=True)
    db_path = test_dir / "test_school.db"
    if db_path.exists():
        db_path.unlink()
    create_database(db_path)
    return db_path


@pytest.fixture(scope="module")
def adapter(test_db):
    return SQLiteAdapter(test_db)


def test_list_tables(adapter):
    tables = adapter.list_tables()
    assert "students" in tables
    assert "courses" in tables
    assert "enrollments" in tables


def test_get_table_schema(adapter):
    schema = adapter.get_table_schema("students")
    col_names = [c["name"] for c in schema]
    assert "id" in col_names
    assert "name" in col_names
    assert "cohort" in col_names
    assert "score" in col_names


def test_search_valid(adapter):
    res = adapter.search("students", filters={"cohort": "A1"})
    assert res["count"] == 2
    for row in res["rows"]:
        assert row["cohort"] == "A1"


def test_search_with_operators(adapter):
    res = adapter.search("students", filters={"score": {">": 90}})
    assert res["count"] >= 2
    for row in res["rows"]:
        assert row["score"] > 90


def test_insert_valid(adapter):
    new_student = {"name": "Test User", "cohort": "Z9", "score": 100.0}
    res = adapter.insert("students", new_student)
    assert res["inserted_count"] == 1
    assert res["records"][0]["name"] == "Test User"
    assert "id" in res["records"][0]


def test_aggregate_valid(adapter):
    res = adapter.aggregate("students", metric="count")
    assert res["results"][0]["value"] >= 6


def test_aggregate_group_by(adapter):
    res = adapter.aggregate("students", metric="avg", column="score", group_by="cohort")
    assert len(res["results"]) >= 2
    for group in res["results"]:
        assert "group_key" in group
        assert "value" in group


def test_invalid_table(adapter):
    with pytest.raises(ValidationError):
        adapter.search("non_existent_table")


def test_invalid_column_filter(adapter):
    with pytest.raises(ValidationError):
        adapter.search("students", filters={"invalid_col": "val"})


def test_unsupported_operator(adapter):
    with pytest.raises(ValidationError):
        adapter.search("students", filters={"score": {"$hack": 100}})


def test_empty_insert(adapter):
    with pytest.raises(ValidationError):
        adapter.insert("students", {})


def test_invalid_aggregate_metric(adapter):
    with pytest.raises(ValidationError):
        adapter.aggregate("students", metric="invalid_func")


def test_mcp_tool_wrappers():
    # Test wrapper error translation to ValueError
    with pytest.raises(ValueError):
        search("missing_table")
    with pytest.raises(ValueError):
        insert("students", {})
    with pytest.raises(ValueError):
        aggregate("students", "bad_metric")


def test_mcp_resources():
    db_res = json.loads(database_schema())
    assert "students" in db_res
    
    tbl_res = json.loads(table_schema("courses"))
    assert tbl_res["table"] == "courses"
    assert len(tbl_res["columns"]) > 0
