"""
Task Tools — TaskCreate, TaskUpdate, TaskList
参考 cc-haha TaskCreateTool/TaskUpdateTool/TaskListTool

Tasks are persisted to disk (JSON per task) so they survive restarts.
The LLM uses these to break complex work into trackable subtasks.
"""
import os
import json
import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Task storage directory
TASK_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'wolf_data', 'tasks')


def _ensure_task_dir():
    os.makedirs(TASK_DIR, exist_ok=True)


def _task_path(task_id: str) -> str:
    return os.path.join(TASK_DIR, f'{task_id}.json')


def _next_id() -> str:
    """Generate next task ID using high-watermark (like cc-haha)"""
    _ensure_task_dir()
    max_id = 0
    for fname in os.listdir(TASK_DIR):
        if fname.endswith('.json'):
            try:
                n = int(fname.replace('.json', ''))
                if n > max_id:
                    max_id = n
            except ValueError:
                pass
    return str(max_id + 1)


def _save_task(task_dict: dict):
    _ensure_task_dir()
    with open(_task_path(task_dict['id']), 'w', encoding='utf-8') as f:
        json.dump(task_dict, f, ensure_ascii=False, indent=2)


def _load_task(task_id: str) -> Optional[dict]:
    path = _task_path(task_id)
    if not os.path.isfile(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _load_all_tasks() -> List[dict]:
    _ensure_task_dir()
    tasks = []
    for fname in os.listdir(TASK_DIR):
        if fname.endswith('.json'):
            try:
                with open(os.path.join(TASK_DIR, fname), 'r', encoding='utf-8') as f:
                    tasks.append(json.load(f))
            except Exception:
                pass
    return tasks


# ==================== TaskCreate ====================

async def task_create(args: dict, context: dict) -> Any:
    """Create a new task"""
    from ...tools.registry import ToolResult

    subject = args.get('subject', '')
    description = args.get('description', '')
    active_form = args.get('activeForm', '')

    if not subject:
        return ToolResult(
            tool_call_id=context.get('tool_call_id', ''),
            name='TaskCreate',
            result=None, success=False,
            error='subject is required'
        )

    task = {
        'id': _next_id(),
        'subject': subject,
        'description': description,
        'activeForm': active_form,
        'status': 'pending',
        'blocks': [],
        'blockedBy': [],
        'owner': None,
        'created_at': time.time(),
        'metadata': {}
    }
    _save_task(task)
    logger.info(f"TaskCreate: #{task['id']} '{subject}'")

    return ToolResult(
        tool_call_id=context.get('tool_call_id', ''),
        name='TaskCreate',
        result={'success': True, 'task': task},
        success=True
    )


TASK_CREATE_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {
            "type": "string",
            "description": "A brief, actionable title in imperative form (e.g., 'Fix auth bug in login flow')"
        },
        "description": {
            "type": "string",
            "description": "What needs to be done"
        },
        "activeForm": {
            "type": "string",
            "description": "Present continuous form shown in spinner when task is in_progress (e.g., 'Fixing auth bug')"
        }
    },
    "required": ["subject", "description"]
}


# ==================== TaskUpdate ====================

async def task_update(args: dict, context: dict) -> Any:
    """Update a task — status, owner, dependencies"""
    from ...tools.registry import ToolResult

    task_id = args.get('taskId', '')
    if not task_id:
        return ToolResult(
            tool_call_id=context.get('tool_call_id', ''),
            name='TaskUpdate', result=None, success=False,
            error='taskId is required'
        )

    task = _load_task(task_id)
    if not task:
        return ToolResult(
            tool_call_id=context.get('tool_call_id', ''),
            name='TaskUpdate', result=None, success=False,
            error=f'Task #{task_id} not found'
        )

    # Update fields
    if 'status' in args:
        task['status'] = args['status']
    if 'subject' in args:
        task['subject'] = args['subject']
    if 'description' in args:
        task['description'] = args['description']
    if 'owner' in args:
        task['owner'] = args['owner']
    if 'addBlocks' in args:
        for bid in args['addBlocks']:
            if bid not in task['blocks']:
                task['blocks'].append(str(bid))
    if 'addBlockedBy' in args:
        for bid in args['addBlockedBy']:
            if bid not in task['blockedBy']:
                task['blockedBy'].append(str(bid))
    if 'metadata' in args and isinstance(args['metadata'], dict):
        task['metadata'].update(args['metadata'])

    _save_task(task)

    status_str = task['status']
    logger.info(f"TaskUpdate: #{task_id} status={status_str}")

    return ToolResult(
        tool_call_id=context.get('tool_call_id', ''),
        name='TaskUpdate',
        result={'success': True, 'task': task},
        success=True
    )


TASK_UPDATE_SCHEMA = {
    "type": "object",
    "properties": {
        "taskId": {
            "type": "string",
            "description": "The ID of the task to update"
        },
        "status": {
            "type": "string",
            "enum": ["pending", "in_progress", "completed", "deleted"],
            "description": "New status for the task"
        },
        "subject": {
            "type": "string",
            "description": "New subject for the task"
        },
        "description": {
            "type": "string",
            "description": "New description for the task"
        },
        "owner": {
            "type": "string",
            "description": "New owner for the task"
        },
        "addBlocks": {
            "type": "array", "items": {"type": "string"},
            "description": "Task IDs that this task blocks"
        },
        "addBlockedBy": {
            "type": "array", "items": {"type": "string"},
            "description": "Task IDs that block this task"
        }
    },
    "required": ["taskId"]
}


# ==================== TaskList ====================

async def task_list(args: dict, context: dict) -> Any:
    """List all tasks, optionally filtered by status"""
    from ...tools.registry import ToolResult

    status_filter = args.get('status', None)
    tasks = _load_all_tasks()

    if status_filter:
        tasks = [t for t in tasks if t['status'] == status_filter]

    # Sort: in_progress > pending > completed
    order = {'in_progress': 0, 'pending': 1, 'completed': 2}
    tasks.sort(key=lambda t: order.get(t['status'], 99))

    summary = {
        'total': len(tasks),
        'pending': sum(1 for t in tasks if t['status'] == 'pending'),
        'in_progress': sum(1 for t in tasks if t['status'] == 'in_progress'),
        'completed': sum(1 for t in tasks if t['status'] == 'completed'),
    }

    return ToolResult(
        tool_call_id=context.get('tool_call_id', ''),
        name='TaskList',
        result={'success': True, 'tasks': tasks, 'summary': summary},
        success=True
    )


TASK_LIST_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["pending", "in_progress", "completed"],
            "description": "Filter by status (omit for all)"
        }
    },
    "required": []
}


# ==================== Helpers ====================

def describe_tool_call(name: str, arguments: dict) -> str:
    """Generate a human-readable one-line description of a tool call"""
    if not arguments:
        return name
    if name == 'Bash':
        cmd = arguments.get('command', '')
        return cmd[:80] if cmd else 'bash'
    elif name in ('Write', 'Edit'):
        return arguments.get('file_path', 'file')[:80]
    elif name == 'Read':
        return arguments.get('file_path', 'file')[:80]
    elif name == 'Grep':
        return arguments.get('pattern', 'grep')[:80]
    elif name == 'Glob':
        return arguments.get('pattern', 'glob')[:80]
    elif name == 'Skill':
        return f"Skill: {arguments.get('skill', '')}"
    elif name == 'TaskCreate':
        return f"Plan: {arguments.get('subject', '')}"
    elif name == 'TaskUpdate':
        return f"Update #{arguments.get('taskId', '')} → {arguments.get('status', '')}"
    else:
        import json as _json
        return _json.dumps(arguments, ensure_ascii=False)[:80]
