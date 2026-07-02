import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


class ValidationError(Exception):
    """Raised when a request cannot be safely executed."""
    pass


class SQLiteAdapter:
    """
    Adapter for interacting with SQLite database securely.
    Provides methods to inspect schema, search, insert, and aggregate data
    while preventing SQL injection by validating identifiers and using parameterized queries.
    """

    SUPPORTED_OPERATORS = {
        "=": "=", "eq": "=", "$eq": "=",
        "==": "=",
        "!=": "!=", "neq": "!=", "$ne": "!=", "<>": "!=",
        ">": ">", "gt": ">", "$gt": ">",
        ">=": ">=", "gte": ">=", "$gte": ">=",
        "<": "<", "lt": "<", "$lt": "<",
        "<=": "<=", "lte": "<=", "$lte": "<=",
        "like": "LIKE", "LIKE": "LIKE", "$like": "LIKE",
        "in": "IN", "IN": "IN", "$in": "IN"
    }

    SUPPORTED_METRICS = {"count", "avg", "sum", "min", "max"}

    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise ValidationError(f"Database file not found: {self.db_path}")

    def connect(self) -> sqlite3.Connection:
        """Opens and returns a SQLite connection with Row factory enabled."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def list_tables(self) -> List[str]:
        """Returns a list of non-internal table names in the database."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
            )
            rows = cursor.fetchall()
            return [row["name"] for row in rows]

    def get_table_schema(self, table: str) -> List[Dict[str, Any]]:
        """Returns normalized schema information for a given table."""
        tables = self.list_tables()
        if table not in tables:
            raise ValidationError(f"Table '{table}' does not exist. Available tables: {tables}")

        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info(\"{table}\");")
            rows = cursor.fetchall()
            if not rows:
                raise ValidationError(f"Could not retrieve schema for table '{table}'.")

            schema = []
            for row in rows:
                schema.append({
                    "cid": row["cid"],
                    "name": row["name"],
                    "type": row["type"],
                    "notnull": bool(row["notnull"]),
                    "default_value": row["dflt_value"],
                    "pk": bool(row["pk"])
                })
            return schema

    def _validate_table_and_columns(self, table: str, columns: Optional[List[str]] = None) -> List[str]:
        """Validates that the table and requested columns exist."""
        schema = self.get_table_schema(table)
        valid_cols = [col["name"] for col in schema]

        if columns:
            if not isinstance(columns, (list, tuple)):
                raise ValidationError("Columns parameter must be a list of column names.")
            for col in columns:
                if col not in valid_cols:
                    raise ValidationError(f"Column '{col}' does not exist in table '{table}'. Valid columns: {valid_cols}")
            return list(columns)
        return valid_cols

    def _build_where_clause(self, filters: Union[Dict, List, None], valid_columns: List[str]) -> Tuple[str, List[Any]]:
        """
        Safely builds a parameterized WHERE clause from filters.
        Supports dictionary: {"column": "value"} or {"column": {"op": "value"}}
        Or list of dicts: [{"column": "col", "operator": "op", "value": val}]
        """
        if not filters:
            return "", []

        conditions = []
        params = []

        if isinstance(filters, dict):
            for col, condition in filters.items():
                if col not in valid_columns:
                    raise ValidationError(f"Invalid column in filter: '{col}'. Valid columns: {valid_columns}")
                
                if isinstance(condition, dict):
                    for op_raw, val in condition.items():
                        op_clean = str(op_raw).strip()
                        if op_clean not in self.SUPPORTED_OPERATORS:
                            raise ValidationError(f"Unsupported filter operator: '{op_raw}'")
                        op_sql = self.SUPPORTED_OPERATORS[op_clean]
                        if op_sql == "IN" and isinstance(val, (list, tuple)):
                            if not val:
                                raise ValidationError(f"IN operator for column '{col}' requires a non-empty list.")
                            placeholders = ", ".join(["?"] * len(val))
                            conditions.append(f"\"{col}\" IN ({placeholders})")
                            params.extend(val)
                        else:
                            conditions.append(f"\"{col}\" {op_sql} ?")
                            params.append(val)
                else:
                    conditions.append(f"\"{col}\" = ?")
                    params.append(condition)

        elif isinstance(filters, list):
            for item in filters:
                if not isinstance(item, dict):
                    raise ValidationError("Filter list items must be dictionaries.")
                col = item.get("column") or item.get("field")
                op_raw = item.get("operator", "=")
                val = item.get("value")

                if not col or col not in valid_columns:
                    raise ValidationError(f"Invalid or missing column in filter item: '{col}'. Valid columns: {valid_columns}")

                op_clean = str(op_raw).strip()
                if op_clean not in self.SUPPORTED_OPERATORS:
                    raise ValidationError(f"Unsupported filter operator: '{op_raw}'")
                op_sql = self.SUPPORTED_OPERATORS[op_clean]

                if op_sql == "IN" and isinstance(val, (list, tuple)):
                    if not val:
                        raise ValidationError(f"IN operator for column '{col}' requires a non-empty list.")
                    placeholders = ", ".join(["?"] * len(val))
                    conditions.append(f"\"{col}\" IN ({placeholders})")
                    params.extend(val)
                else:
                    conditions.append(f"\"{col}\" {op_sql} ?")
                    params.append(val)
        else:
            raise ValidationError("Filters must be a dictionary or a list of filter conditions.")

        if conditions:
            return " WHERE " + " AND ".join(conditions), params
        return "", []

    def search(
        self,
        table: str,
        columns: Optional[List[str]] = None,
        filters: Union[Dict, List, None] = None,
        limit: int = 20,
        offset: int = 0,
        order_by: Optional[str] = None,
        descending: bool = False
    ) -> Dict[str, Any]:
        """Searches rows in a table with validation, filtering, pagination, and sorting."""
        valid_cols = self._validate_table_and_columns(table, columns)
        all_table_cols = [col["name"] for col in self.get_table_schema(table)]

        try:
            limit = int(limit)
            offset = int(offset)
            if limit < 0 or offset < 0:
                raise ValueError
        except (ValueError, TypeError):
            raise ValidationError("Limit and offset must be non-negative integers.")

        cols_sql = ", ".join([f"\"{c}\"" for c in valid_cols])
        sql = f"SELECT {cols_sql} FROM \"{table}\""

        where_sql, params = self._build_where_clause(filters, all_table_cols)
        sql += where_sql

        if order_by:
            if order_by not in all_table_cols:
                raise ValidationError(f"Invalid order_by column '{order_by}'. Valid columns: {all_table_cols}")
            direction = "DESC" if descending else "ASC"
            sql += f" ORDER BY \"{order_by}\" {direction}"

        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]

        return {
            "table": table,
            "count": len(results),
            "limit": limit,
            "offset": offset,
            "rows": results
        }

    def insert(self, table: str, values: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Inserts one or more records into a table securely using parameterized queries."""
        all_table_cols = [col["name"] for col in self.get_table_schema(table)]

        if not values:
            raise ValidationError("Insert values cannot be empty.")

        records = [values] if isinstance(values, dict) else values
        if not isinstance(records, list) or len(records) == 0:
            raise ValidationError("Insert values must be a non-empty dictionary or list of dictionaries.")

        inserted_records = []
        with self.connect() as conn:
            cursor = conn.cursor()
            for record in records:
                if not isinstance(record, dict) or not record:
                    raise ValidationError("Each record to insert must be a non-empty dictionary.")
                
                cols_to_insert = []
                vals_to_insert = []
                for k, v in record.items():
                    if k not in all_table_cols:
                        raise ValidationError(f"Column '{k}' does not exist in table '{table}'. Valid columns: {all_table_cols}")
                    cols_to_insert.append(k)
                    vals_to_insert.append(v)

                if not cols_to_insert:
                    raise ValidationError("No valid columns provided for insert.")

                cols_sql = ", ".join([f"\"{c}\"" for c in cols_to_insert])
                placeholders = ", ".join(["?"] * len(cols_to_insert))
                sql = f"INSERT INTO \"{table}\" ({cols_sql}) VALUES ({placeholders})"
                
                cursor.execute(sql, vals_to_insert)
                last_id = cursor.lastrowid

                # Fetch the newly inserted record
                pk_col = "id" if "id" in all_table_cols else cols_to_insert[0]
                cursor.execute(f"SELECT * FROM \"{table}\" WHERE rowid = ?", (last_id,))
                new_row = cursor.fetchone()
                if new_row:
                    inserted_records.append(dict(new_row))
                else:
                    record_copy = dict(record)
                    record_copy["rowid"] = last_id
                    inserted_records.append(record_copy)

            conn.commit()

        return {
            "inserted_count": len(inserted_records),
            "records": inserted_records
        }

    def aggregate(
        self,
        table: str,
        metric: str,
        column: Optional[str] = None,
        filters: Union[Dict, List, None] = None,
        group_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Computes aggregate metrics (count, avg, sum, min, max) securely."""
        if not metric or not isinstance(metric, str):
            raise ValidationError("Aggregate metric must be a string.")
        
        metric_clean = metric.lower().strip()
        if metric_clean not in self.SUPPORTED_METRICS:
            raise ValidationError(f"Unsupported aggregate metric '{metric}'. Supported: {self.SUPPORTED_METRICS}")

        all_table_cols = [col["name"] for col in self.get_table_schema(table)]

        if metric_clean == "count":
            target_col = "*"
            if column and column != "*":
                if column not in all_table_cols:
                    raise ValidationError(f"Invalid column '{column}' for COUNT. Valid columns: {all_table_cols}")
                target_col = f"\"{column}\""
        else:
            if not column or column == "*":
                raise ValidationError(f"Metric '{metric.upper()}' requires a specific valid column name.")
            if column not in all_table_cols:
                raise ValidationError(f"Invalid column '{column}' for aggregate '{metric.upper()}'. Valid columns: {all_table_cols}")
            target_col = f"\"{column}\""

        select_clauses = [f"{metric_clean.upper()}({target_col}) AS value"]
        if group_by:
            if group_by not in all_table_cols:
                raise ValidationError(f"Invalid group_by column '{group_by}'. Valid columns: {all_table_cols}")
            select_clauses.insert(0, f"\"{group_by}\" AS group_key")

        sql = f"SELECT {', '.join(select_clauses)} FROM \"{table}\""

        where_sql, params = self._build_where_clause(filters, all_table_cols)
        sql += where_sql

        if group_by:
            sql += f" GROUP BY \"{group_by}\""

        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]

        return {
            "table": table,
            "metric": metric_clean,
            "column": column or "*",
            "group_by": group_by,
            "results": results
        }
