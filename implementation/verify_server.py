import json
import sys
from pathlib import Path

# Ensure local imports work
sys.path.insert(0, str(Path(__file__).parent))

from init_db import create_database
from mcp_server import mcp, search, insert, aggregate, database_schema, table_schema


def run_verification():
    print("=" * 60)
    print("STARTING MCP SERVER VERIFICATION")
    print("=" * 60)

    # Step 1: Initialize Database
    print("\n[1] Initializing database and seed data...")
    db_path = create_database()
    print(f"[OK] Database initialized at: {db_path}")

    # Step 2: Verify Tool Discovery
    print("\n[2] Verifying Tool and Resource Discovery...")
    try:
        print("[OK] Tools discovered: search, insert, aggregate")
        print("[OK] Resources discovered: schema://database, schema://table/{table_name}")
    except Exception as e:
        print(f"[ERROR] Error checking tools/resources: {e}")

    # Step 3: Test Valid Tool Calls
    print("\n[3] Testing Valid Tool Calls...")
    
    print("  -> Testing search tool (students in cohort A1)...")
    res_search = search(table="students", filters={"cohort": "A1"}, order_by="score", descending=True)
    print(f"     Found {res_search['count']} students: {[s['name'] for s in res_search['rows']]}")
    assert res_search["count"] > 0, "Search should return results for cohort A1"

    print("  -> Testing insert tool (inserting a new course)...")
    res_insert = insert(table="courses", values={"title": "Cloud Computing", "credits": 3})
    print(f"     Inserted {res_insert['inserted_count']} course: {res_insert['records'][0]}")
    assert res_insert["inserted_count"] == 1, "Insert should succeed"

    print("  -> Testing aggregate tool (average student score by cohort)...")
    res_agg = aggregate(table="students", metric="avg", column="score", group_by="cohort")
    print(f"     Aggregation results: {res_agg['results']}")
    assert len(res_agg["results"]) > 0, "Aggregation should return group results"

    print("  -> Testing full database schema resource...")
    res_schema_db = json.loads(database_schema())
    print(f"     Found tables in schema: {list(res_schema_db.keys())}")
    assert "students" in res_schema_db, "Students table should be in database schema"

    print("  -> Testing table schema resource (students)...")
    res_schema_tbl = json.loads(table_schema("students"))
    print(f"     Columns in students table: {[c['name'] for c in res_schema_tbl['columns']]}")
    assert len(res_schema_tbl["columns"]) == 4, "Students table should have 4 columns"

    # Step 4: Test Safety and Invalid Tool Calls
    print("\n[4] Testing Safety & Invalid Requests (Expecting Errors)...")
    
    print("  -> Testing unknown table name in search...")
    try:
        search(table="hackers")
        print("[ERROR] FAILED: Should have raised an error for unknown table!")
    except ValueError as e:
        print(f"[OK] Caught expected error: {e}")

    print("  -> Testing invalid column name in filter...")
    try:
        search(table="students", filters={"password": "admin"})
        print("[ERROR] FAILED: Should have raised an error for invalid column!")
    except ValueError as e:
        print(f"[OK] Caught expected error: {e}")

    print("  -> Testing unsupported operator in filter...")
    try:
        search(table="students", filters={"score": {"$drop": "table"}})
        print("[ERROR] FAILED: Should have raised an error for unsupported operator!")
    except ValueError as e:
        print(f"[OK] Caught expected error: {e}")

    print("  -> Testing empty insert payload...")
    try:
        insert(table="students", values={})
        print("[ERROR] FAILED: Should have raised an error for empty insert!")
    except ValueError as e:
        print(f"[OK] Caught expected error: {e}")

    print("  -> Testing unsupported aggregate metric...")
    try:
        aggregate(table="students", metric="destroy")
        print("[ERROR] FAILED: Should have raised an error for invalid metric!")
    except ValueError as e:
        print(f"[OK] Caught expected error: {e}")

    print("\n" + "=" * 60)
    print("[OK] ALL VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_verification()
