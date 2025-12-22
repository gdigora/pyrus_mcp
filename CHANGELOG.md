# Changelog

All notable changes to this project will be documented in this file.

## [0.0.2] - 2025-12-23

### Added
- Enhanced `comment_task` with 18 new parameters for comprehensive task management:
  - **List management**: `added_list_ids`, `removed_list_ids` - add/remove tasks from lists
  - **Scheduling**: `scheduled_date`, `cancel_schedule` - schedule tasks to calendar
  - **Due dates**: `due_date`, `due`, `duration`, `cancel_due` - manage deadlines
  - **Task metadata**: `subject`, `spent_minutes` - update title and log time
  - **People management**: `subscribers_added`, `subscribers_removed`, `participants_added`, `participants_removed`
  - **Form approvals**: `approval_choice`, `field_updates` - approve/reject and update form fields
  - **Options**: `skip_notification` - control notifications

### Fixed
- Closed GitHub issue #1: Users can now add tasks to lists via `comment_task(task_id, added_list_ids=[list_id])`

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
