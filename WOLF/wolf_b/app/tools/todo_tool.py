"""
Todo Tool - Manage todo items
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid

router = APIRouter()

# Todo storage
todos_db: List[dict] = []


class TodoInput(BaseModel):
    text: str
    priority: str = "medium"  # low, medium, high
    completed: bool = False
    tags: List[str] = []


class TodoUpdate(BaseModel):
    text: Optional[str] = None
    priority: Optional[str] = None
    completed: Optional[bool] = None
    tags: Optional[List[str]] = None


@router.post("/todos")
async def create_todo(input: TodoInput) -> dict:
    """Create a new todo"""
    todo_id = f"todo-{uuid.uuid4().hex[:8]}"

    todo = {
        "id": todo_id,
        "text": input.text,
        "priority": input.priority,
        "completed": input.completed,
        "tags": input.tags,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    todos_db.append(todo)
    return todo


@router.get("/todos")
async def list_todos(completed: Optional[bool] = None, priority: Optional[str] = None) -> List[dict]:
    """List all todos, optionally filtered"""
    todos = todos_db

    if completed is not None:
        todos = [t for t in todos if t["completed"] == completed]
    if priority:
        todos = [t for t in todos if t["priority"] == priority]

    return todos


@router.get("/todos/{todo_id}")
async def get_todo(todo_id: str) -> dict:
    """Get a todo by ID"""
    for todo in todos_db:
        if todo["id"] == todo_id:
            return todo

    raise HTTPException(status_code=404, detail="Todo not found")


@router.put("/todos/{todo_id}")
async def update_todo(todo_id: str, updates: TodoUpdate) -> dict:
    """Update a todo"""
    for todo in todos_db:
        if todo["id"] == todo_id:
            if updates.text is not None:
                todo["text"] = updates.text
            if updates.priority is not None:
                todo["priority"] = updates.priority
            if updates.completed is not None:
                todo["completed"] = updates.completed
            if updates.tags is not None:
                todo["tags"] = updates.tags
            todo["updated_at"] = datetime.now().isoformat()
            return todo

    raise HTTPException(status_code=404, detail="Todo not found")


@router.delete("/todos/{todo_id}")
async def delete_todo(todo_id: str) -> dict:
    """Delete a todo"""
    global todos_db
    original_len = len(todos_db)
    todos_db = [t for t in todos_db if t["id"] != todo_id]

    if len(todos_db) == original_len:
        raise HTTPException(status_code=404, detail="Todo not found")

    return {"success": True, "message": "Todo deleted"}


@router.post("/todos/clear")
async def clear_completed() -> dict:
    """Clear all completed todos"""
    global todos_db
    todos_db = [t for t in todos_db if not t["completed"]]
    return {"success": True, "message": "Completed todos cleared"}