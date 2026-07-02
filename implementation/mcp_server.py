import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from fastmcp import FastMCP

from db import SQLiteAdapter, ValidationError
from init_db import create_database

# Ensure database is initialized
DB_PATH = Path(__file__).parent / "school.db"
if not DB_PATH.exists():
    create_database(DB_PATH)

# Create the FastMCP server object
mcp = FastMCP("SQLite Lab MCP Server")
adapter = SQLiteAdapter(DB_PATH)


@mcp.tool(name="search")
def search(
    table: str,
    filters: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
    columns: Optional[List[str]] = None,
    limit: int = 20,
    offset: int = 0,
    order_by: Optional[str] = None,
    descending: bool = False
) -> Dict[str, Any]:
    """
    Searches rows in a SQLite table with filtering, sorting, and pagination.
    
    Args:
        table: Name of the table to search (e.g., 'students', 'courses', 'enrollments').
        filters: Filtering conditions. Can be a dict like {"cohort": "A1", "score": {">": 80}} or list of filter dicts.
        columns: List of column names to retrieve. Defaults to all columns if None.
        limit: Maximum number of rows to return (default 20).
        offset: Number of rows to skip for pagination (default 0).
        order_by: Column name to sort results by.
        descending: Whether to sort descending (True) or ascending (False).
    """
    try:
        return adapter.search(
            table=table,
            columns=columns,
            filters=filters,
            limit=limit,
            offset=offset,
            order_by=order_by,
            descending=descending
        )
    except ValidationError as e:
        raise ValueError(f"Validation Error: {e}")


@mcp.tool(name="insert")
def insert(
    table: str,
    values: Union[Dict[str, Any], List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Inserts one or more new records into a SQLite table securely.
    
    Args:
        table: Name of the table to insert into.
        values: A dictionary representing a single row or a list of dictionaries for bulk insert.
    """
    try:
        return adapter.insert(table=table, values=values)
    except ValidationError as e:
        raise ValueError(f"Validation Error: {e}")


@mcp.tool(name="aggregate")
def aggregate(
    table: str,
    metric: str,
    column: Optional[str] = None,
    filters: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
    group_by: Optional[str] = None
) -> Dict[str, Any]:
    """
    Computes aggregate statistical metrics (count, avg, sum, min, max) on a table.
    
    Args:
        table: Name of the table to aggregate.
        metric: Aggregate function to run ('count', 'avg', 'sum', 'min', 'max').
        column: Column name to apply the metric on. Can be '*' or None for count.
        filters: Optional filtering conditions before aggregating.
        group_by: Optional column name to group results by.
    """
    try:
        return adapter.aggregate(
            table=table,
            metric=metric,
            column=column,
            filters=filters,
            group_by=group_by
        )
    except ValidationError as e:
        raise ValueError(f"Validation Error: {e}")


@mcp.resource("schema://database")
def database_schema() -> str:
    """Returns the full database schema snapshot as formatted JSON text."""
    try:
        tables = adapter.list_tables()
        full_schema = {t: adapter.get_table_schema(t) for t in tables}
        return json.dumps(full_schema, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """Returns the schema description for a single specific table as JSON text."""
    try:
        schema = adapter.get_table_schema(table_name)
        return json.dumps({"table": table_name, "columns": schema}, indent=2, ensure_ascii=False)
    except ValidationError as e:
        return json.dumps({"error": f"Validation Error: {e}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run()
