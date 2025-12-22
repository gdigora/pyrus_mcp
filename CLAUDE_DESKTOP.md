# Claude Desktop Configuration for Pyrus MCP Server

This guide explains how to configure Claude Desktop to use the Pyrus MCP server.

## Configuration File Location

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

## Configuration

Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pyrus": {
      "command": "/Users/digora/Documents/Documents_cloud/Work/pyrus_api_mcp/.venv/bin/python",
      "args": ["/Users/digora/Documents/Documents_cloud/Work/pyrus_api_mcp/server.py"]
    }
  }
}
```

**Important**: Replace the paths with the actual absolute paths on your system.

## Requirements

1. **Python virtual environment** must exist at the specified path with dependencies installed:
   ```bash
   cd /path/to/pyrus_api_mcp
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **accounts.json** must exist in the project directory with at least one account configured

3. **Absolute paths** are required - relative paths will not work

## Verification

After configuring:

1. **Completely restart Claude Desktop** (quit and reopen, not just close window)
2. Look for the hammer icon in the chat input area - this indicates MCP tools are available
3. Ask Claude "What Pyrus accounts are available?" to verify the connection

## Troubleshooting

### MCP tools not appearing

1. Verify JSON syntax is valid (no trailing commas)
2. Check all paths are absolute and correct
3. Ensure virtual environment has all dependencies installed
4. Restart Claude Desktop completely

### Check logs

- **Claude Desktop logs**:
  - macOS: `~/Library/Logs/Claude/mcp*.log`
  - Windows: `%APPDATA%\Claude\logs\mcp*.log`

- **Server logs**: `pyrus_mcp.log` in the project directory

### Common errors

**"accounts.json not found"**
- Ensure `accounts.json` exists in the same directory as `server.py`

**"Authentication failed"**
- Verify your Pyrus login and security key in `accounts.json`
- Check if the security key has been regenerated in Pyrus

**"Module not found"**
- Run `pip install -r requirements.txt` in the virtual environment

## Multiple MCP Servers

You can have multiple MCP servers configured. Example with Pyrus and other servers:

```json
{
  "mcpServers": {
    "pyrus": {
      "command": "/path/to/pyrus_api_mcp/.venv/bin/python",
      "args": ["/path/to/pyrus_api_mcp/server.py"]
    },
    "other-server": {
      "command": "/path/to/other/.venv/bin/python",
      "args": ["/path/to/other/server.py"]
    }
  }
}
```
