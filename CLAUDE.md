# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP (Model Context Protocol) server for Pyrus task management API. Enables Claude Desktop to interact with Pyrus for tasks, forms, contacts, announcements, calendar, and catalogs. Supports multiple Pyrus accounts.

## Commands

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run server (used by Claude Desktop, not manually)
.venv/bin/python server.py

# Test authentication and tools
.venv/bin/python -c "import server; server.load_accounts(); print(server.get_profile())"
```

## Architecture

**Single-file MCP server** (`server.py`):
- Uses `FastMCP` from `mcp.server.fastmcp` with stdio transport
- Wraps `pyrus-api` library for Pyrus API calls
- Logs to `pyrus_mcp.log` (stdout reserved for MCP protocol)

**Key components:**
- `load_accounts()` / `get_client(account)` - Multi-account management with lazy auth
- `_upload_file_direct()` - Direct upload using pyrus-api token (workaround for pyrus-api bug)
- `format_*()` functions - Convert Pyrus model objects to JSON-serializable dicts
- `@mcp.tool()` decorated functions - MCP tools exposed to Claude

**Configuration:**
- `accounts.json` - Credentials (gitignored, use `accounts.json.example` as template)
- Each account has: `name`, `description`, `login`, `security_key`
- `default_account` specifies which to use when not specified

## Dependencies

- `pyrus-api` (upstream, simplygoodsoftware) — Pyrus API client library

**Known pyrus-api bugs and workarounds:**

1. **Announcement parsing** — `get_announcements()` uses `response.original_response` to access raw JSON
2. **File uploads** — `_upload_file_direct()` uses pyrus-api token but makes direct HTTP request to correct `_files_host` endpoint (pyrus-api sends uploads to wrong host)

**Updating pyrus-api:**
```bash
pip install --upgrade pyrus-api
```

## Adding New Tools

1. Add `@mcp.tool()` decorated function in appropriate section
2. Use `get_client(account)` to get authenticated PyrusAPI client
3. Check `response.error_code` (truthy check, not just hasattr)
4. Return JSON-serializable dict using `format_*()` helpers
