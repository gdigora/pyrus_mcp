# Pyrus API MCP Server

MCP (Model Context Protocol) server for [Pyrus](https://pyrus.com) task management system. Enables Claude Desktop to interact with Pyrus for task management, form processing, contacts, announcements, and more.

## Features

- **Multi-account support** - Configure multiple Pyrus accounts and switch between them
- **Full Pyrus API coverage**:
  - Inbox and task management
  - Form-based tasks and registries
  - Contacts and organization members
  - Announcements
  - Calendar tasks
  - Task lists
  - Catalogs

## Installation

1. Clone this repository or copy the files to your desired location

2. Create and activate a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure your Pyrus accounts in `accounts.json`:
```json
{
  "accounts": {
    "work": {
      "name": "Work Pyrus",
      "description": "Work project management",
      "login": "your.email@company.com",
      "security_key": "your-api-security-key"
    },
    "personal": {
      "name": "Personal Pyrus",
      "description": "Personal task tracking",
      "login": "personal@email.com",
      "security_key": "another-security-key"
    }
  },
  "default_account": "work"
}
```

### Getting your Pyrus Security Key

1. Log in to Pyrus
2. Go to your Profile settings
3. Navigate to the Authorization section
4. Copy your API security key (or generate a new one)

## Claude Desktop Configuration

See [CLAUDE_DESKTOP.md](CLAUDE_DESKTOP.md) for detailed setup instructions.

Quick setup - add to your Claude Desktop config:
```json
{
  "mcpServers": {
    "pyrus": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}
```

## Available Tools

### Account Management
- `list_accounts()` - List all configured accounts
- `get_profile(account?)` - Get user profile

### Inbox & Tasks
- `get_inbox(account?, limit?)` - Get inbox tasks
- `get_task(task_id, account?)` - Get task with comments
- `create_task(text, subject?, responsible?, due_date?, participants?, account?)` - Create simple task
- `comment_task(task_id, text?, action?, reassign_to?, account?)` - Add comment or action
- `complete_task(task_id, account?)` - Mark task finished
- `reopen_task(task_id, account?)` - Reopen closed task

### Forms & Registry
- `get_forms(account?)` - List form templates
- `get_form(form_id, account?)` - Get form with field definitions
- `get_registry(form_id, limit?, include_archived?, account?)` - Get tasks by form
- `create_form_task(form_id, fields?, fill_defaults?, account?)` - Create form-based task

### Contacts & Organization
- `get_contacts(include_inactive?, account?)` - Get contacts by organization
- `get_members(account?)` - Get organization members
- `get_roles(account?)` - Get roles

### Announcements
- `get_announcements(limit?, account?)` - Get announcements
- `create_announcement(text, account?)` - Create announcement

### Calendar & Lists
- `get_calendar(start_date, end_date, include_meetings?, account?)` - Get calendar tasks
- `get_lists(account?)` - Get task lists
- `get_list_tasks(list_id, limit?, account?)` - Get tasks in list

### Catalogs
- `get_catalog(catalog_id, account?)` - Get catalog items

## Usage Examples

In Claude Desktop, you can say:

- "Show me my Pyrus inbox"
- "Create a task: Review quarterly report, due next Friday"
- "What tasks do I have in my work Pyrus account?"
- "Show me all form templates available"
- "Get the tasks from form 12345"
- "Mark task 67890 as complete"
- "What announcements are there?"

## Logs

Server logs are written to `pyrus_mcp.log` in the project directory.

## License

MIT
