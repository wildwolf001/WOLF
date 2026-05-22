"""
Task Tools - Create, list, get, update, delete tasks
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid

router = APIRouter()

# In-memory task storage (would be replaced with database in production)
tasks_db: dict = {}


class TaskInput(BaseModel):
    title: str
    description: Optional[str] = ""
    status: str = "pending"  # pending, in_progress, completed, failed
    priority: str = "medium"  # low, medium, high, critical
    assignee: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee: Optional[str] = None


class Task(BaseModel):
    id: str
    title: str
    description: str
    status: str
    priority: str
    assignee: Optional[str] = None
    created_at: str
    updated_at: str


@router.post("/tasks")
async def create_task(input: TaskInput) -> Task:
    """Create a new task"""
    now = datetime.now().isoformat()
    task_id = f"task-{uuid.uuid4().hex[:8]}"

    task = {
        "id": task_id,
        "title": input.title,
        "description": input.description,
        "status": input.status,
        "priority": input.priority,
        "assignee": input.assignee,
        "created_at": now,
        "updated_at": now,
    }

    tasks_db[task_id] = task
    return task


@router.get("/tasks")
async def list_tasks(status: Optional[str] = None) -> List[Task]:
    """List all tasks, optionally filtered by status"""
    tasks = list(tasks_db.values())
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    return tasks


@router.get("/tasks/{task_id}")
async def get_task(task_id: str) -> Task:
    """Get a task by ID"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_db[task_id]


@router.put("/tasks/{task_id}")
async def update_task(task_id: str, updates: TaskUpdate) -> Task:
    """Update a task"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks_db[task_id]
    update_data = updates.model_dump(exclude_none=True)

    for key, value in update_data.items():
        task[key] = value

    task["updated_at"] = datetime.now().isoformat()

    return task


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str) -> dict:
    """Delete a task"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")

    del tasks_db[task_id]
    return {"success": True, "message": "Task deleted"}


@router.post("/tasks/{task_id}/stop")
async def stop_task(task_id: str) -> Task:
    """Stop a running task"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks_db[task_id]
    task["status"] = "failed"
    task["updated_at"] = datetime.now().isoformat()

    return task