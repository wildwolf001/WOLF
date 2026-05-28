"""
Task API Routes — CRUD for tasks (reads from disk)
"""
from fastapi import APIRouter, HTTPException
from typing import Optional

router = APIRouter()


@router.get("/tasks")
async def list_tasks(status: Optional[str] = None):
    """List all tasks, optionally filtered by status"""
    from ...tools.definitions.task import _load_all_tasks

    tasks = _load_all_tasks()
    if status:
        tasks = [t for t in tasks if t['status'] == status]

    # Sort: in_progress > pending > completed
    order = {'in_progress': 0, 'pending': 1, 'completed': 2}
    tasks.sort(key=lambda t: order.get(t['status'], 99))

    summary = {
        'total': len(tasks),
        'pending': sum(1 for t in tasks if t['status'] == 'pending'),
        'in_progress': sum(1 for t in tasks if t['status'] == 'in_progress'),
        'completed': sum(1 for t in tasks if t['status'] == 'completed'),
    }

    return {"tasks": tasks, "summary": summary}


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get a single task by ID"""
    from ...tools.definitions.task import _load_task

    task = _load_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task": task}


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a task"""
    import os
    from ...tools.definitions.task import _task_path

    path = _task_path(task_id)
    if os.path.isfile(path):
        os.remove(path)
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Task not found")
