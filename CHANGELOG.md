# Changelog

All notable changes to this project will be documented in this file.

## [0.0.1] - 2025-12-22

### Added
- Claude Desktop configuration updated with Pyrus MCP server
- Version command for release management (`.claude/commands/version.md`)

### Fixed
- Fixed MCP import path (`mcp.server.fastmcp.FastMCP`)
- Fixed error checking for API responses (check truthy `error_code`)
- Fixed `get_profile` response parsing (use direct attributes instead of nested object)
- Fixed `get_announcements` parsing (workaround for pyrus-api library bug)

## [0.0.0] - 2025-12-22

### Added
- Initial release of Pyrus MCP Server
- Multi-account support with `accounts.json` configuration
- Account management: `list_accounts`, `get_profile`
- Inbox and tasks: `get_inbox`, `get_task`, `create_task`, `comment_task`, `complete_task`, `reopen_task`
- Forms and registry: `get_forms`, `get_form`, `get_registry`, `create_form_task`
- Organization: `get_contacts`, `get_members`, `get_roles`
- Announcements: `get_announcements`, `create_announcement`
- Calendar and lists: `get_calendar`, `get_lists`, `get_list_tasks`
- Catalogs: `get_catalog`

### Documentation
- README with installation and usage instructions
- Claude Desktop setup guide (CLAUDE_DESKTOP.md)
- Example account configuration
