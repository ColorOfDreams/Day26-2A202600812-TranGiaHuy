# SQLite Lab MCP Server

This repository implements a FastMCP server backed by SQLite. It exposes three MCP tools:

- `search`
- `insert`
- `aggregate`

It also exposes schema context through MCP resources:

- `schema://database`
- `schema://table/{table_name}`

## Project Structure

```text
implementation/
  __init__.py
  db.py
  init_db.py
  mcp_server.py
  verify_server.py
  start_inspector.ps1
  tests/
    test_db.py
pseudocode/
  db.py
  init_db.py
  mcp_server.py
requirements.txt
Rubric.md
Tips.md
```

## Data Model

The SQLite database contains three related tables:

- `students`: student profile records with cohort and GPA
- `courses`: course catalog records
- `enrollments`: student-course records with semester and score

The database file is created at `implementation/sqlite_lab.db`. It can be rebuilt at any time from the seed SQL.

## Setup

Use Python 3.11 or newer.

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Initialize or reset the database:

```bash
python implementation\init_db.py
```

Run the repeatable verification script:

```bash
python implementation\verify_server.py
```

Run automated tests:

```bash
python -m pytest implementation\tests
```

Start the MCP server over stdio:

```bash
python implementation\mcp_server.py
```

## Tool Reference

### `search`

Searches a validated table with optional selected columns, filters, ordering, limit, and offset.

Example arguments:

```json
{
  "table": "students",
  "filters": {"cohort": "A1"},
  "columns": ["id", "name", "cohort", "gpa"],
  "order_by": "gpa",
  "descending": true,
  "limit": 5
}
```

Supported filter operators:

- `eq`
- `ne`
- `lt`
- `lte`
- `gt`
- `gte`
- `like`
- `contains`
- `in`
- `is_null`

Filters can be compact:

```json
{"cohort": "A1", "gpa": {"gte": 3.5}}
```

Or list-based:

```json
[
  {"column": "cohort", "operator": "eq", "value": "A1"},
  {"column": "gpa", "operator": "gte", "value": 3.5}
]
```

### `insert`

Inserts one row into a validated table and returns the inserted row.

Example arguments:

```json
{
  "table": "students",
  "values": {
    "name": "Mai Phuong",
    "cohort": "A1",
    "email": "phuong.mai@example.edu",
    "gpa": 3.66
  }
}
```

### `aggregate`

Computes `count`, `avg`, `sum`, `min`, or `max` over a validated table. Non-`count` metrics require a column.

Example arguments:

```json
{
  "table": "students",
  "metric": "avg",
  "column": "gpa",
  "group_by": "cohort"
}
```

## Resources

Read the full database schema:

```text
schema://database
```

Read one table schema:

```text
schema://table/students
```

Both resources return JSON text.

## Safety

The implementation rejects:

- unknown table names
- unknown column names
- unsupported filter operators
- invalid aggregate metrics
- missing aggregate columns for `avg`, `sum`, `min`, and `max`
- empty inserts
- invalid pagination values

SQL values use bound parameters. Table and column identifiers are only used after validation against SQLite schema metadata.

## MCP Inspector

From PowerShell:

```powershell
.\implementation\start_inspector.ps1
```

Equivalent manual command:

```bash
npx -y @modelcontextprotocol/inspector /ABSOLUTE/PATH/TO/python /ABSOLUTE/PATH/TO/implementation/mcp_server.py
```

Inspector demo checklist:

1. Confirm the server starts.
2. Confirm tools `search`, `insert`, and `aggregate` are discoverable.
3. Confirm resources `schema://database` and `schema://table/{table_name}` are discoverable.
4. Call `search` for students in cohort `A1`.
5. Call `insert` with a new student.
6. Call `aggregate` with average GPA grouped by cohort.
7. Call `search` with a missing table and confirm the error is clear.

## Client Configuration Examples

### Claude Code

`.mcp.json` example:

```json
{
  "mcpServers": {
    "sqlite-lab": {
      "type": "stdio",
      "command": "python",
      "args": ["D:/vinuni/Day26-2A202600812-TranGiaHuy/implementation/mcp_server.py"],
      "env": {}
    }
  }
}
```

### Codex

`~/.codex/config.toml` example:

```toml
[mcp_servers.sqlite_lab]
command = "python"
args = ["D:/vinuni/Day26-2A202600812-TranGiaHuy/implementation/mcp_server.py"]
```

### Gemini CLI

```bash
gemini mcp add sqlite-lab python D:/vinuni/Day26-2A202600812-TranGiaHuy/implementation/mcp_server.py --description "SQLite lab FastMCP server" --timeout 10000
gemini mcp list
```

Smoke prompt:

```bash
gemini --allowed-mcp-server-names sqlite-lab --yolo -p "Use the sqlite-lab MCP server. Show the top 2 students by GPA and then read schema://table/students."
```

## Demo Script

For a short demo video, show this sequence:

1. Run `python implementation\verify_server.py`.
2. Open MCP Inspector with `.\implementation\start_inspector.ps1`.
3. Show the three tools and schema resources.
4. Call `search` on `students` with cohort `A1`.
5. Call `insert` to add one student.
6. Call `aggregate` to compute average GPA by cohort.
7. Call an invalid table request and show the clear validation error.
