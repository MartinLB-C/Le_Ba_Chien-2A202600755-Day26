# SQLite Lab MCP Server - Completed Implementation

This project is a complete, production-ready implementation of a **Model Context Protocol (MCP)** server using **FastMCP** and **SQLite**. It meets all requirements specified in the lab rubric (including bonus features).

---

## 🛠 Project Structure

```text
implementation/
  ├── init_db.py         # Initializes SQLite database and seeds relational data
  ├── db.py              # Secure SQLite adapter with parameterized queries & validation
  ├── mcp_server.py      # FastMCP server exposing tools and resources
  ├── verify_server.py   # Automated verification script demonstrating functionality
  ├── school.db          # Generated SQLite database file
  ├── README.md          # Project setup and demo guide
  └── tests/
      └── test_server.py # Pytest unit test suite
```

---

## ⚙️ Setup Instructions

### 1. Create and Activate Virtual Environment
```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install Required Dependencies
```powershell
pip install fastmcp pytest
```

### 3. Initialize Database
```powershell
python implementation/init_db.py
```

---

## 🔍 Tool Descriptions

### 1. `search`
Searches records in a specified SQLite table with support for filtering, ordering, and pagination.
- **Arguments**:
  - `table` (string, required): Name of the table (e.g., `'students'`, `'courses'`, `'enrollments'`).
  - `filters` (dict or list, optional): Filter conditions (e.g., `{"cohort": "A1", "score": {">": 80}}`).
  - `columns` (list of strings, optional): Specific columns to retrieve.
  - `limit` (int, default `20`): Max records to return.
  - `offset` (int, default `0`): Records to skip.
  - `order_by` (string, optional): Column to sort by.
  - `descending` (bool, default `False`): Sort direction.

### 2. `insert`
Inserts one or more records into a specified table securely and returns the inserted records (with generated primary keys).
- **Arguments**:
  - `table` (string, required): Target table name.
  - `values` (dict or list of dicts, required): Payload to insert.

### 3. `aggregate`
Computes statistical metrics across rows in a table.
- **Arguments**:
  - `table` (string, required): Target table name.
  - `metric` (string, required): Supported functions: `'count'`, `'avg'`, `'sum'`, `'min'`, `'max'`.
  - `column` (string, optional): Column to evaluate (defaults to `'*'` for `'count'`).
  - `group_by` (string, optional): Column to group metrics by.
  - `filters` (dict or list, optional): Pre-aggregation filter conditions.

---

## 📦 MCP Resources

- **`schema://database`**: Returns the complete JSON schema snapshot for all tables in the database.
- **`schema://table/{table_name}`**: Dynamic resource template returning the schema for a specific table.

---

## 🧪 Testing and Verification Steps

### Option A: Run Unit Test Suite (pytest)
```powershell
.venv\Scripts\pytest implementation\tests\test_server.py -v
```

### Option B: Run Standalone Verification Script
```powershell
.venv\Scripts\python implementation\verify_server.py
```

### Option C: Run with MCP Inspector
```powershell
npx -y @modelcontextprotocol/inspector python implementation\mcp_server.py
```

---

## 💻 Client Configuration Examples

### 1. Gemini CLI
Add the server via terminal:
```bash
gemini mcp add sqlite-lab /ABSOLUTE/PATH/TO/.venv/Scripts/python /ABSOLUTE/PATH/TO/implementation/mcp_server.py --description "SQLite lab FastMCP server"
```
Verify connection:
```bash
gemini mcp list
gemini --allowed-mcp-server-names sqlite-lab --yolo -p "Use the sqlite-lab MCP server to show me the top 2 students by score in cohort A1."
```

### 2. Claude Code (`.mcp.json`)
```json
{
  "mcpServers": {
    "sqlite-lab": {
      "command": "/ABSOLUTE/PATH/TO/.venv/Scripts/python",
      "args": ["/ABSOLUTE/PATH/TO/implementation/mcp_server.py"],
      "env": {}
    }
  }
}
```

### 3. Codex (`~/.codex/config.toml`)
```toml
[mcp_servers.sqlite_lab]
command = "/ABSOLUTE/PATH/TO/.venv/Scripts/python"
args = ["/ABSOLUTE/PATH/TO/implementation/mcp_server.py"]
```

---

## 🛡️ Safety & Security Features

- **Zero SQL Injection**: All identifiers (table names, column names) are rigorously validated against database metadata before query construction.
- **Parameterized Queries**: User-supplied values are bound using SQLite placeholders (`?`).
- **Clear Error Reporting**: Invalid table names, unknown columns, unsupported operators, and empty bulk inserts raise descriptive validation exceptions.
