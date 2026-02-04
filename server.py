"""
Pyrus API MCP Server

MCP server for Pyrus task management system with multi-account support.
Provides tools for managing tasks, forms, contacts, announcements, and more.

Usage with Claude Desktop:
    Configure in claude_desktop_config.json:
    {
        "mcpServers": {
            "pyrus": {
                "command": "/path/to/.venv/bin/python",
                "args": ["/path/to/server.py"]
            }
        }
    }
"""

VERSION = "0.0.2"

import json
import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from mcp.server.fastmcp import FastMCP
from pyrus import client
from pyrus.models import requests as req

# Configure logging to file (stdout is reserved for MCP protocol)
SCRIPT_DIR = Path(__file__).parent
LOG_FILE = SCRIPT_DIR / "pyrus_mcp.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE)],
)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("Pyrus")

# Account configuration
ACCOUNTS_FILE = SCRIPT_DIR / "accounts.json"
accounts_config: dict[str, Any] = {}
pyrus_clients: dict[str, client.PyrusAPI] = {}


# =============================================================================
# Account Management
# =============================================================================


def load_accounts() -> None:
    """Load accounts configuration from accounts.json."""
    global accounts_config

    if not ACCOUNTS_FILE.exists():
        logger.error(f"Accounts file not found: {ACCOUNTS_FILE}")
        raise FileNotFoundError(f"accounts.json not found at {ACCOUNTS_FILE}")

    with open(ACCOUNTS_FILE) as f:
        accounts_config = json.load(f)

    if "accounts" not in accounts_config:
        raise ValueError("accounts.json must contain 'accounts' key")

    if not accounts_config["accounts"]:
        raise ValueError("accounts.json must have at least one account configured")

    logger.info(f"Loaded {len(accounts_config['accounts'])} account(s)")


def get_client(account: str | None = None) -> client.PyrusAPI:
    """
    Get authenticated PyrusAPI client for the specified account.

    Args:
        account: Account key from accounts.json. If None, uses default_account.

    Returns:
        Authenticated PyrusAPI client.

    Raises:
        ValueError: If account not found in configuration.
    """
    if account is None:
        account = accounts_config.get("default_account")
        if account is None:
            # Use first account if no default specified
            account = next(iter(accounts_config["accounts"].keys()))

    if account not in accounts_config["accounts"]:
        available = list(accounts_config["accounts"].keys())
        raise ValueError(f"Account '{account}' not found. Available: {available}")

    # Return cached client if available
    if account in pyrus_clients:
        return pyrus_clients[account]

    # Create new client
    acc_config = accounts_config["accounts"][account]
    pyrus_client = client.PyrusAPI(
        login=acc_config["login"],
        security_key=acc_config["security_key"],
    )

    # Authenticate
    auth_response = pyrus_client.auth()
    if not auth_response.access_token:
        error = getattr(auth_response, "error_code", "Unknown error")
        raise RuntimeError(f"Authentication failed for {account}: {error}")

    logger.info(f"Authenticated account: {account}")
    pyrus_clients[account] = pyrus_client
    return pyrus_client


# =============================================================================
# Formatting Helpers
# =============================================================================


def format_person(person) -> dict | None:
    """Format Person object to dict."""
    if person is None:
        return None
    return {
        "id": person.id,
        "name": f"{person.first_name or ''} {person.last_name or ''}".strip(),
        "email": person.email,
    }


def format_task_header(task) -> dict:
    """Format TaskHeader to dict."""
    return {
        "id": task.id,
        "text": task.text,
        "author": format_person(task.author),
        "responsible": format_person(task.responsible) if task.responsible else None,
        "create_date": str(task.create_date) if task.create_date else None,
        "due_date": str(task.due_date) if task.due_date else None,
    }


def format_task(task) -> dict:
    """Format Task/TaskWithComments to dict."""
    result = format_task_header(task)
    result.update({
        "subject": task.subject,
        "status": "closed" if task.close_date else "open",
        "close_date": str(task.close_date) if task.close_date else None,
        "form_id": task.form_id,
        "scheduled_date": str(task.scheduled_date) if task.scheduled_date else None,
    })

    # Add comments if available
    if hasattr(task, "comments") and task.comments:
        result["comments"] = [format_comment(c) for c in task.comments]

    # Add form fields if available
    if task.fields:
        result["fields"] = [format_field(f) for f in task.fields]

    # Add attachments if available
    if hasattr(task, "attachments") and task.attachments:
        result["attachments"] = [format_file(f) for f in task.attachments]

    return result


def format_file(file) -> dict:
    """Format File attachment to dict."""
    return {
        "id": file.id,
        "name": file.name,
        "size": file.size,
        "md5": file.md5,
        "url": file.url,
        "version": getattr(file, "version", None),
        "root_id": getattr(file, "root_id", None),
    }


def format_comment(comment) -> dict:
    """Format TaskComment to dict."""
    result = {
        "id": comment.id,
        "text": comment.text,
        "author": format_person(comment.author),
        "create_date": str(comment.create_date) if comment.create_date else None,
        "action": comment.action,
    }
    if hasattr(comment, "attachments") and comment.attachments:
        result["attachments"] = [format_file(f) for f in comment.attachments]
    return result


def format_field(field) -> dict:
    """Format FormField to dict."""
    value = field.value
    # Convert complex values to serializable format
    if hasattr(value, "__dict__"):
        value = str(value)
    return {
        "id": field.id,
        "name": field.name,
        "type": field.type,
        "value": value,
    }


def format_form(form) -> dict:
    """Format Form to dict."""
    return {
        "id": form.id,
        "name": form.name,
        "steps": getattr(form, "steps", None),
        "fields": [format_form_field_info(f) for f in form.fields] if form.fields else [],
    }


def format_form_field_info(field) -> dict:
    """Format form field info (template definition)."""
    return {
        "id": field.id,
        "name": field.name,
        "type": field.type,
        "required_step": field.info.required_step if field.info else None,
    }


def format_organization(org) -> dict:
    """Format Organization to dict."""
    return {
        "id": org.organization_id,
        "name": org.name,
        "persons": [format_person(p) for p in org.persons] if org.persons else [],
        "roles": [format_role(r) for r in org.roles] if org.roles else [],
    }


def format_role(role) -> dict:
    """Format Role to dict."""
    return {
        "id": role.id,
        "name": role.name,
        "member_ids": role.member_ids,
    }


def format_announcement(ann) -> dict:
    """Format Announcement to dict."""
    return {
        "id": ann.id,
        "text": ann.text,
        "author": format_person(ann.author),
        "create_date": str(ann.create_date) if ann.create_date else None,
        "comments": [format_announcement_comment(c) for c in ann.comments] if ann.comments else [],
    }


def format_announcement_comment(comment) -> dict:
    """Format AnnouncementComment to dict."""
    return {
        "id": comment.id,
        "text": comment.text,
        "author": format_person(comment.author),
        "create_date": str(comment.create_date) if comment.create_date else None,
    }


def format_list(task_list) -> dict:
    """Format TaskList to dict."""
    return {
        "id": task_list.id,
        "name": task_list.name,
        "children": [format_list(c) for c in task_list.children] if task_list.children else [],
    }


def format_catalog_item(item) -> dict:
    """Format CatalogItem to dict."""
    return {
        "item_id": item.item_id,
        "values": item.values,
    }


# =============================================================================
# MCP Tools - Account Management
# =============================================================================


@mcp.tool()
def list_accounts() -> list[dict]:
    """
    List all configured Pyrus accounts.

    Returns a list of available accounts with their names and descriptions.
    Use this to help determine which account to use for a task.
    """
    result = []
    for key, config in accounts_config["accounts"].items():
        result.append({
            "key": key,
            "name": config.get("name", key),
            "description": config.get("description", ""),
            "login": config.get("login", ""),
            "is_default": key == accounts_config.get("default_account"),
        })
    return result


@mcp.tool()
def get_profile(account: str | None = None) -> dict:
    """
    Get the current user's profile for the specified account.

    Args:
        account: Account key (optional, uses default if not specified).

    Returns:
        User profile information including name, email, and organization.
    """
    pyrus = get_client(account)
    response = pyrus.get_profile()

    if hasattr(response, "error_code") and response.error_code:
        raise RuntimeError(f"API error: {response.error_code}")

    org = None
    if response.organization:
        org = {
            "id": response.organization.organization_id,
            "name": response.organization.name,
        }

    return {
        "person_id": response.person_id,
        "first_name": response.first_name,
        "last_name": response.last_name,
        "email": response.email,
        "organization_id": response.organization_id,
        "organization": org,
    }


# =============================================================================
# MCP Tools - Inbox & Tasks
# =============================================================================


@mcp.tool()
def get_inbox(account: str | None = None, limit: int = 50) -> dict:
    """
    Get inbox tasks for the specified account.

    Args:
        account: Account key (optional, uses default if not specified).
        limit: Maximum number of tasks to return (default 50).

    Returns:
        List of inbox tasks with basic information.
    """
    pyrus = get_client(account)
    response = pyrus.get_inbox(tasks_count=limit)

    if hasattr(response, "error_code") and response.error_code:
        raise RuntimeError(f"API error: {response.error_code}")

    tasks = []
    if response.tasks:
        tasks = [format_task_header(t) for t in response.tasks]

    # Include grouped tasks if available
    groups = []
    if hasattr(response, "task_groups") and response.task_groups:
        for group in response.task_groups:
            groups.append({
                "id": group.id,
                "name": group.name,
                "tasks": [format_task_header(t) for t in group.tasks] if group.tasks else [],
            })

    return {
        "tasks": tasks,
        "groups": groups,
    }


@mcp.tool()
def get_task(task_id: int, account: str | None = None) -> dict:
    """
    Get a specific task with all its comments and details.

    Args:
        task_id: The ID of the task to retrieve.
        account: Account key (optional, uses default if not specified).

    Returns:
        Complete task information including all comments.
    """
    pyrus = get_client(account)
    response = pyrus.get_task(task_id)

    if hasattr(response, "error_code") and response.error_code:
        raise RuntimeError(f"API error: {response.error_code}")

    return format_task(response.task)


@mcp.tool()
def create_task(
    text: str,
    subject: str | None = None,
    responsible: str | None = None,
    due_date: str | None = None,
    participants: list[str] | None = None,
    attachments: list[dict] | None = None,
    account: str | None = None,
) -> dict:
    """
    Create a new simple task.

    Args:
        text: Task description/content (required).
        subject: Task subject/title (optional).
        responsible: Email or ID of person responsible (optional).
        due_date: Due date in YYYY-MM-DD format (optional).
        participants: List of participant emails or IDs (optional).
        attachments: List of file attachments (use upload_file first to get guid).
                     Each dict can have: 'guid' (from upload_file), 'root_id' (for versioning),
                     'attachment_id' (existing file), 'url', 'name'.
        account: Account key (optional, uses default if not specified).

    Returns:
        The created task.
    """
    from pyrus.models import entities

    pyrus = get_client(account)

    # Parse due date if provided
    due_dt = None
    if due_date:
        due_dt = datetime.strptime(due_date, "%Y-%m-%d")

    # Build attachment objects if provided
    attachment_objects = None
    if attachments:
        attachment_objects = []
        for att in attachments:
            new_file = entities.NewFile()
            if "guid" in att:
                new_file.guid = att["guid"]
            if "root_id" in att:
                new_file.root_id = att["root_id"]
            if "attachment_id" in att:
                new_file.attachment_id = att["attachment_id"]
            if "url" in att:
                new_file.url = att["url"]
            if "name" in att:
                new_file.name = att["name"]
            attachment_objects.append(new_file)

    request = req.CreateTaskRequest(
        text=text,
        subject=subject,
        responsible=responsible,
        due_date=due_dt,
        participants=participants,
        attachments=attachment_objects,
    )

    response = pyrus.create_task(request)

    if hasattr(response, "error_code") and response.error_code:
        raise RuntimeError(f"API error: {response.error_code}")

    return format_task(response.task)


@mcp.tool()
def comment_task(
    task_id: int,
    text: str | None = None,
    action: str | None = None,
    reassign_to: str | None = None,
    # List management
    added_list_ids: list[int] | None = None,
    removed_list_ids: list[int] | None = None,
    # Scheduling
    scheduled_date: str | None = None,
    cancel_schedule: bool | None = None,
    # Due dates
    due_date: str | None = None,
    due: str | None = None,
    duration: int | None = None,
    cancel_due: bool | None = None,
    # Task metadata
    subject: str | None = None,
    spent_minutes: int | None = None,
    # People management
    subscribers_added: list[str] | None = None,
    subscribers_removed: list[str] | None = None,
    participants_added: list[str] | None = None,
    participants_removed: list[str] | None = None,
    # Form task approvals
    approval_choice: str | None = None,
    field_updates: list[dict] | None = None,
    # File attachments
    attachments: list[dict] | None = None,
    # Options
    skip_notification: bool | None = None,
    account: str | None = None,
) -> dict:
    """
    Add a comment to a task or perform an action. This is the main tool for modifying tasks.

    Args:
        task_id: The ID of the task.
        text: Comment text (optional).
        action: Action to perform: 'finished' or 'reopened' (optional).
        reassign_to: Email or ID of person to reassign to (optional).

        # List Management (use get_lists to find list IDs):
        added_list_ids: List IDs to add the task to (e.g., [123, 456]).
        removed_list_ids: List IDs to remove the task from.

        # Scheduling (moves task to calendar):
        scheduled_date: Schedule date in YYYY-MM-DD format.
        cancel_schedule: Set True to cancel schedule and move task to inbox.

        # Due Dates:
        due_date: Due date in YYYY-MM-DD format (date only).
        due: Due datetime in YYYY-MM-DDTHH:MM format (date and time).
        duration: Duration in minutes (only with 'due', for calendar events).
        cancel_due: Set True to remove due date.

        # Task Metadata:
        subject: Change task subject/title.
        spent_minutes: Log time spent in minutes.

        # People Management (use email or person ID):
        subscribers_added: List of emails/IDs to add as subscribers.
        subscribers_removed: List of emails/IDs to remove from subscribers.
        participants_added: List of emails/IDs to add as participants (simple tasks).
        participants_removed: List of emails/IDs to remove from participants.

        # Form Task Approvals:
        approval_choice: 'approved', 'rejected', or 'acknowledged'.
        field_updates: List of field updates [{"id": 123, "value": "new value"}].

        # File Attachments (use upload_file first to get guid):
        attachments: List of file attachments. Each dict can have:
                     'guid' (from upload_file), 'root_id' (for versioning),
                     'attachment_id' (existing file), 'url', 'name'.

        # Options:
        skip_notification: Set True to skip sending notifications.
        account: Account key (optional, uses default if not specified).

    Returns:
        The updated task with all comments.

    Examples:
        Add task to list: comment_task(123, added_list_ids=[456])
        Schedule for tomorrow: comment_task(123, scheduled_date="2024-01-15")
        Set due date with time: comment_task(123, due="2024-01-15T14:00")
        Log time: comment_task(123, text="Fixed the bug", spent_minutes=30)
        Approve form task: comment_task(123, approval_choice="approved")
        Attach file: comment_task(123, attachments=[{"guid": "abc-123"}])
    """
    from pyrus.models import entities

    pyrus = get_client(account)

    # Parse dates
    scheduled_dt = None
    if scheduled_date:
        scheduled_dt = datetime.strptime(scheduled_date, "%Y-%m-%d")

    due_date_dt = None
    if due_date:
        due_date_dt = datetime.strptime(due_date, "%Y-%m-%d")

    due_dt = None
    if due:
        due_dt = datetime.strptime(due, "%Y-%m-%dT%H:%M")

    # Build attachment objects if provided
    attachment_objects = None
    if attachments:
        attachment_objects = []
        for att in attachments:
            new_file = entities.NewFile()
            if "guid" in att:
                new_file.guid = att["guid"]
            if "root_id" in att:
                new_file.root_id = att["root_id"]
            if "attachment_id" in att:
                new_file.attachment_id = att["attachment_id"]
            if "url" in att:
                new_file.url = att["url"]
            if "name" in att:
                new_file.name = att["name"]
            attachment_objects.append(new_file)

    request = req.TaskCommentRequest(
        text=text,
        action=action,
        reassign_to=reassign_to,
        # List management
        added_list_ids=added_list_ids,
        removed_list_ids=removed_list_ids,
        # Scheduling
        scheduled_date=scheduled_dt,
        cancel_schedule=cancel_schedule,
        # Due dates
        due_date=due_date_dt,
        due=due_dt,
        duration=duration,
        cancel_due=cancel_due,
        # Task metadata
        subject=subject,
        spent_minutes=spent_minutes,
        # People management
        subscribers_added=subscribers_added,
        subscribers_removed=subscribers_removed,
        participants_added=participants_added,
        participants_removed=participants_removed,
        # Form task approvals
        approval_choice=approval_choice,
        field_updates=field_updates,
        # File attachments
        attachments=attachment_objects,
        # Options
        skip_notification=skip_notification,
    )

    response = pyrus.comment_task(task_id, request)

    if hasattr(response, "error_code") and response.error_code:
        raise RuntimeError(f"API error: {response.error_code}")

    return format_task(response.task)


@mcp.tool()
def complete_task(task_id: int, account: str | None = None) -> dict:
    """
    Mark a task as finished/completed.

    Args:
        task_id: The ID of the task to complete.
        account: Account key (optional, uses default if not specified).

    Returns:
        The updated task.
    """
    return comment_task(task_id, action="finished", account=account)


@mcp.tool()
def reopen_task(task_id: int, account: str | None = None) -> dict:
    """
    Reopen a closed task.

    Args:
        task_id: The ID of the task to reopen.
        account: Account key (optional, uses default if not specified).

    Returns:
        The updated task.
    """
    return comment_task(task_id, action="reopened", account=account)


# =============================================================================
# MCP Tools - Forms & Registry
# =============================================================================


@mcp.tool()
def get_forms(account: str | None = None) -> list[dict]:
    """
    Get all available form templates.

    Args:
        account: Account key (optional, uses default if not specified).

    Returns:
        List of form templates with their IDs and names.
    """
    pyrus = get_client(account)
    response = pyrus.get_forms()

    if hasattr(response, "error_code") and response.error_code:
        raise RuntimeError(f"API error: {response.error_code}")

    return [{"id": f.id, "name": f.name} for f in response.forms] if response.forms else []


@mcp.tool()
def get_form(form_id: int, account: str | None = None) -> dict:
    """
    Get a specific form template with all field definitions.

    Args:
        form_id: The ID of the form template.
        account: Account key (optional, uses default if not specified).

    Returns:
        Form template with field definitions.
    """
    pyrus = get_client(account)
    response = pyrus.get_form(form_id)

    if hasattr(response, "error_code") and response.error_code:
        raise RuntimeError(f"API error: {response.error_code}")

    return format_form(response)


@mcp.tool()
def get_registry(
    form_id: int,
    limit: int = 100,
    include_archived: bool = False,
    account: str | None = None,
) -> list[dict]:
    """
    Get tasks from a form registry (tasks created from a specific form).

    Args:
        form_id: The ID of the form template.
        limit: Maximum number of tasks to return (default 100).
        include_archived: Include archived tasks (default False).
        account: Account key (optional, uses default if not specified).

    Returns:
        List of tasks from the form registry.
    """
    pyrus = get_client(account)

    request = req.FormRegisterRequest(
        item_count=limit,
        include_archived=include_archived,
    )

    response = pyrus.get_registry(form_id, request)

    if hasattr(response, "error_code") and response.error_code:
        raise RuntimeError(f"API error: {response.error_code}")

    return [format_task(t) for t in response.tasks] if response.tasks else []


@mcp.tool()
def create_form_task(
    form_id: int,
    fields: list[dict] | None = None,
    fill_defaults: bool = True,
    account: str | None = None,
) -> dict:
    """
    Create a new task from a form template.

    Args:
        form_id: The ID of the form template.
        fields: List of field values, each with 'id' or 'name' and 'value'.
        fill_defaults: Fill default values from form template (default True).
        account: Account key (optional, uses default if not specified).

    Returns:
        The created task.

    Example fields:
        [{"name": "Description", "value": "My task"}, {"id": 123, "value": "Some value"}]
    """
    pyrus = get_client(account)

    request = req.CreateTaskRequest(
        form_id=form_id,
        fields=fields,
        fill_defaults=fill_defaults,
    )

    response = pyrus.create_task(request)

    if hasattr(response, "error_code") and response.error_code:
        raise RuntimeError(f"API error: {response.error_code}")

    return format_task(response.task)


# =============================================================================
# MCP Tools - Contacts & Organization
# =============================================================================


@mcp.tool()
def get_contacts(include_inactive: bool = False, account: str | None = None) -> list[dict]:
    """
    Get all contacts grouped by organization.

    Args:
        include_inactive: Include inactive users (default False).
        account: Account key (optional, uses default if not specified).

    Returns:
        List of organizations with their members.
    """
    pyrus = get_client(account)
    response = pyrus.get_contacts(include_inactive=include_inactive)

    if hasattr(response, "error_code") and response.error_code:
        raise RuntimeError(f"API error: {response.error_code}")

    return [format_organization(o) for o in response.organizations] if response.organizations else []


@mcp.tool()
def get_members(account: str | None = None) -> list[dict]:
    """
    Get all members of the organization.

    Args:
        account: Account key (optional, uses default if not specified).

    Returns:
        List of organization members.
    """
    pyrus = get_client(account)
    response = pyrus.get_members()

    if hasattr(response, "error_code") and response.error_code:
        raise RuntimeError(f"API error: {response.error_code}")

    return [format_person(m) for m in response.members] if response.members else []


@mcp.tool()
def get_roles(account: str | None = None) -> list[dict]:
    """
    Get all roles in the organization.

    Args:
        account: Account key (optional, uses default if not specified).

    Returns:
        List of roles with their members.
    """
    pyrus = get_client(account)
    response = pyrus.get_roles()

    if hasattr(response, "error_code") and response.error_code:
        raise RuntimeError(f"API error: {response.error_code}")

    return [format_role(r) for r in response.roles] if response.roles else []


# =============================================================================
# MCP Tools - Announcements
# =============================================================================


@mcp.tool()
def get_announcements(limit: int = 100, account: str | None = None) -> list[dict]:
    """
    Get all announcements.

    Args:
        limit: Maximum number of announcements to return (default 100).
        account: Account key (optional, uses default if not specified).

    Returns:
        List of announcements.
    """
    pyrus = get_client(account)
    response = pyrus.get_announcements(item_count=limit)

    if hasattr(response, "error_code") and response.error_code:
        raise RuntimeError(f"API error: {response.error_code}")

    # Use original_response due to pyrus-api library bug with announcement parsing
    raw = response.original_response
    if not raw or "announcements" not in raw:
        return []

    result = []
    for ann in raw["announcements"]:
        result.append({
            "id": ann.get("id"),
            "text": ann.get("text"),
            "create_date": ann.get("create_date"),
            "author": {
                "id": ann["author"].get("id"),
                "name": f"{ann['author'].get('first_name', '')} {ann['author'].get('last_name', '')}".strip(),
                "email": ann["author"].get("email"),
            } if ann.get("author") else None,
            "comments_count": len(ann.get("comments", [])),
        })
    return result


@mcp.tool()
def create_announcement(text: str, account: str | None = None) -> dict:
    """
    Create a new announcement.

    Args:
        text: Announcement text content.
        account: Account key (optional, uses default if not specified).

    Returns:
        The created announcement.
    """
    pyrus = get_client(account)

    request = req.CreateAnnouncementRequest(text=text)
    response = pyrus.create_announcement(request)

    if hasattr(response, "error_code") and response.error_code:
        raise RuntimeError(f"API error: {response.error_code}")

    return format_announcement(response.announcement)


# =============================================================================
# MCP Tools - Calendar & Lists
# =============================================================================


@mcp.tool()
def get_calendar(
    start_date: str,
    end_date: str,
    include_meetings: bool = True,
    account: str | None = None,
) -> list[dict]:
    """
    Get calendar tasks for a date range.

    Args:
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        include_meetings: Include meetings (default True).
        account: Account key (optional, uses default if not specified).

    Returns:
        List of tasks with due dates in the specified range.
    """
    pyrus = get_client(account)

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    request = req.CalendarRequest(
        start_date_utc=start_dt,
        end_date_utc=end_dt,
        include_meetings=include_meetings,
    )

    response = pyrus.get_calendar_tasks(request)

    if hasattr(response, "error_code") and response.error_code:
        raise RuntimeError(f"API error: {response.error_code}")

    return [format_task(t) for t in response.tasks] if response.tasks else []


@mcp.tool()
def get_lists(account: str | None = None) -> list[dict]:
    """
    Get all task lists available to the user.

    Args:
        account: Account key (optional, uses default if not specified).

    Returns:
        List of task lists (hierarchical structure).
    """
    pyrus = get_client(account)
    response = pyrus.get_lists()

    if hasattr(response, "error_code") and response.error_code:
        raise RuntimeError(f"API error: {response.error_code}")

    return [format_list(lst) for lst in response.lists] if response.lists else []


@mcp.tool()
def get_list_tasks(list_id: int, limit: int = 200, account: str | None = None) -> list[dict]:
    """
    Get all tasks in a specific list.

    Args:
        list_id: The ID of the list.
        limit: Maximum number of tasks to return (default 200).
        account: Account key (optional, uses default if not specified).

    Returns:
        List of tasks in the list.
    """
    pyrus = get_client(account)

    request = req.TaskListRequest(item_count=limit)
    response = pyrus.get_task_list(list_id, request)

    if hasattr(response, "error_code") and response.error_code:
        raise RuntimeError(f"API error: {response.error_code}")

    return [format_task_header(t) for t in response.tasks] if response.tasks else []


# =============================================================================
# MCP Tools - Catalogs
# =============================================================================


@mcp.tool()
def get_catalog(catalog_id: int, account: str | None = None) -> dict:
    """
    Get a catalog with all its items.

    Args:
        catalog_id: The ID of the catalog.
        account: Account key (optional, uses default if not specified).

    Returns:
        Catalog information with headers and items.
    """
    pyrus = get_client(account)
    response = pyrus.get_catalog(catalog_id)

    if hasattr(response, "error_code") and response.error_code:
        raise RuntimeError(f"API error: {response.error_code}")

    return {
        "catalog_id": response.catalog_id,
        "name": response.name,
        "headers": response.catalog_headers,
        "items": [format_catalog_item(i) for i in response.items] if response.items else [],
    }


# =============================================================================
# MCP Tools - Files
# =============================================================================


@mcp.tool()
def download_file(
    file_id: int,
    save_dir: str | None = None,
    account: str | None = None,
) -> dict:
    """
    Download a file attachment from Pyrus to disk.

    Args:
        file_id: The ID of the file to download (from task/comment attachments).
        save_dir: Directory to save the file (default: ~/Downloads).
        account: Account key (optional, uses default if not specified).

    Returns:
        Dict with keys: status, filename, saved_to, size, and optionally warning.

    Raises:
        RuntimeError: If Pyrus API returns error, no file data, or file write fails.
        ValueError: If save_dir exists but is not a directory.

    Notes:
        Creates save_dir if it does not exist.
        Overwrites existing files with the same name.
        If API returns no filename, uses 'file_{file_id}' as fallback.
        Sanitizes filename to prevent path traversal attacks.
        Zero-byte files are saved with a warning in the response.
    """
    if save_dir is None:
        save_dir = str(Path.home() / "Downloads")

    save_path = Path(save_dir)

    # Create directory if needed. exist_ok=True handles concurrent creation gracefully.
    # Note: mkdir with exist_ok=True only raises PermissionError/OSError, not FileExistsError.
    # The is_dir() check below handles the case where a FILE exists at save_path.
    try:
        save_path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        raise RuntimeError(
            f"Cannot create directory '{save_dir}': permission denied. "
            "Please check permissions or choose a different save location."
        )
    except OSError as e:
        raise RuntimeError(f"Cannot create directory '{save_dir}': {e}")

    # Final validation that we have a directory
    if not save_path.is_dir():
        raise ValueError(f"Cannot save file: '{save_dir}' exists but is not a directory")

    pyrus = get_client(account)
    response = pyrus.download_file(file_id)

    if hasattr(response, "error_code") and response.error_code:
        raise RuntimeError(f"API error: {response.error_code}")

    # Validate response contains file data
    if not hasattr(response, "raw_file") or response.raw_file is None:
        raise RuntimeError(f"API returned no file data for file_id {file_id}")

    # Track warnings to surface to user (not just log file)
    # Critical: Users need to know when something is wrong, not just see "success"
    warning = None

    if len(response.raw_file) == 0:
        warning = "File has 0 bytes - may be empty or corrupted on server"
        logger.warning(f"File {file_id} has 0 bytes - this may indicate an issue")

    # Sanitize filename to prevent path traversal attacks (e.g., "../../etc/passwd")
    # Path.name extracts only the filename component, stripping any directory parts
    if hasattr(response, "filename") and response.filename:
        # Decode URL-encoded filename (non-ASCII chars from HTTP Content-Disposition)
        decoded_filename = unquote(response.filename).replace('+', ' ')
        safe_filename = Path(decoded_filename).name
        if not safe_filename:
            logger.warning(f"File {file_id} has invalid filename '{response.filename}', using fallback")
            safe_filename = f"file_{file_id}"
    else:
        logger.warning(f"File {file_id} has no filename from API, using fallback")
        safe_filename = f"file_{file_id}"

    file_path = save_path / safe_filename

    try:
        with open(file_path, "wb") as f:
            f.write(response.raw_file)
    except PermissionError:
        raise RuntimeError(f"Cannot write file '{file_path}': permission denied")
    except OSError as e:
        # Clean up partial file if it exists
        cleanup_warning = ""
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError as cleanup_error:
                cleanup_warning = f" (warning: partial file may remain: {cleanup_error})"
                logger.warning(f"Failed to clean up partial file '{file_path}': {cleanup_error}")
        raise RuntimeError(f"Failed to write file to '{file_path}': {e}{cleanup_warning}")

    logger.info(f"Downloaded file {file_id} ({len(response.raw_file)} bytes) to {file_path}")

    result = {
        "status": "downloaded",
        "filename": safe_filename,
        "saved_to": str(file_path),
        "size": len(response.raw_file),
    }
    # Include warning in response so users are informed of potential issues
    # (don't just log to file where they'll never see it)
    if warning:
        result["warning"] = warning
    return result


@mcp.tool()
def upload_file(file_path: str, root_id: int | None = None, account: str | None = None) -> dict:
    """
    Upload a file to Pyrus for attachment to tasks.

    Args:
        file_path: Path to the file to upload.
        root_id: If provided, creates a new version of existing file.
        account: Account key (optional, uses default if not specified).

    Returns:
        Upload result with guid for use in attachments.
    """
    pyrus = get_client(account)

    # Validate file exists
    file_path_obj = Path(file_path).expanduser()
    if not file_path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        response = pyrus.upload_file(str(file_path_obj))
    except Exception as e:
        error_msg = str(e)
        if "Expecting value" in error_msg:
            raise RuntimeError(
                f"Upload failed: Pyrus returned an invalid response. "
                f"This may indicate a server issue. Original error: {error_msg}"
            )
        raise

    if hasattr(response, "error_code") and response.error_code:
        raise RuntimeError(f"API error: {response.error_code}")

    return {
        "guid": response.guid,
        "md5_hash": response.md5_hash,
        "root_id": root_id,  # Pass through for reference
    }


@mcp.tool()
def upload_file_content(
    content_base64: str,
    filename: str,
    account: str | None = None,
) -> dict:
    """
    Upload file content directly to Pyrus (without file path).

    Args:
        content_base64: Base64-encoded file content.
        filename: Name for the uploaded file (e.g., 'report.pdf').
        account: Account key (optional, uses default if not specified).

    Returns:
        Upload result with guid for use in attachments.
    """
    import base64

    pyrus = get_client(account)

    # Decode base64 content
    try:
        content = base64.b64decode(content_base64)
    except Exception as e:
        raise ValueError(f"Invalid base64 content: {e}")

    # Sanitize filename for use in temp file path
    safe_filename = Path(filename).name or "upload"

    # Write to temp file and use pyrus-api library's upload
    # This ensures correct URL and headers from authenticated client
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=f"_{safe_filename}",
        prefix="pyrus_upload_"
    ) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        response = pyrus.upload_file(tmp_path)

        if hasattr(response, "error_code") and response.error_code:
            raise RuntimeError(f"API error: {response.error_code}")

        return {
            "guid": response.guid,
            "md5_hash": response.md5_hash,
        }
    except Exception as e:
        error_msg = str(e)
        if "Expecting value" in error_msg:
            raise RuntimeError(
                f"Upload failed: Pyrus returned an invalid response. "
                f"Original error: {error_msg}"
            )
        raise
    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            logger.warning(f"Failed to clean up temp file: {tmp_path}")


@mcp.tool()
def attach_file_to_task(
    task_id: int,
    file_path: str | None = None,
    content_base64: str | None = None,
    filename: str | None = None,
    text: str | None = None,
    root_id: int | None = None,
    account: str | None = None,
) -> dict:
    """
    Upload and attach a file to a task in one action.

    Args:
        task_id: The task to attach the file to.
        file_path: Path to file (use this OR content_base64).
        content_base64: Base64-encoded file content (use this OR file_path).
        filename: Required when using content_base64.
        text: Optional comment text.
        root_id: If provided, creates new version of existing file.
        account: Account key (optional, uses default if not specified).

    Returns:
        The updated task with the new attachment.
    """
    # Validate: exactly one of file_path or content_base64 must be provided
    if file_path and content_base64:
        raise ValueError("Provide either file_path or content_base64, not both")
    if not file_path and not content_base64:
        raise ValueError("Must provide either file_path or content_base64")
    if content_base64 and not filename:
        raise ValueError("filename is required when using content_base64")

    # Step 1: Upload
    if file_path:
        upload_result = upload_file(file_path, root_id, account)
    else:
        upload_result = upload_file_content(content_base64, filename, account)

    # Step 2: Attach via comment
    attachment = {"guid": upload_result["guid"]}
    if root_id:
        attachment["root_id"] = root_id

    return comment_task(
        task_id=task_id,
        text=text,
        attachments=[attachment],
        account=account,
    )


# =============================================================================
# Main Entry Point
# =============================================================================


if __name__ == "__main__":
    try:
        load_accounts()
        logger.info("Starting Pyrus MCP server")
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
