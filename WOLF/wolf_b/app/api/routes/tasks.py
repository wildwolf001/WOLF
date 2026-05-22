from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.db.models import Task
from app.db.schemas import TaskCreate, TaskUpdate, TaskAssign, TaskResponse
from app.services.task_cancellation_service import cancellation_service

router = APIRouter()

@router.get("", response_model=List[TaskResponse])
async def get_tasks(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):
    """Get all tasks with optional filtering"""
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)

    tasks = query.offset((page - 1) * page_size).limit(page_size).all()
    return tasks

@router.post("", response_model=TaskResponse)
async def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task"""
    task_id = f"task-{len(db.query(Task).all()) + 1}"
    db_task = Task(
        id=task_id,
        title=task.title,
        description=task.description,
        type=task.type,
        priority=task.priority,
        assignee_id=task.assignee_id,
        created_by="user",
        status="pending",
        dependencies=str(task.dependencies) if task.dependencies else "[]"
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: Session = Depends(get_db)):
    """Get task by ID"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, updates: TaskUpdate, db: Session = Depends(get_db)):
    """Update task"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = updates.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)
    return task

@router.delete("/{task_id}")
async def delete_task(task_id: str, db: Session = Depends(get_db)):
    """Delete task"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()
    return {"message": "Task deleted"}

@router.post("/{task_id}/assign", response_model=TaskResponse)
async def assign_task(task_id: str, assignment: TaskAssign, db: Session = Depends(get_db)):
    """Assign task to an agent"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.assignee_id = assignment.assignee_id
    task.status = "in_progress"
    db.commit()
    db.refresh(task)
    return task


@router.post("/cancel/{task_id}")
async def cancel_task(task_id: str):
    """
    Cancel a running task by task_id

    This endpoint is used when user presses Ctrl+Z to cancel a running task.
    The cancellation is async - it sets a flag that the running task checks periodically.
    """
    # Cancel via cancellation service
    cancelled = await cancellation_service.cancel_task(task_id)

    # Also try to cancel via DB if task exists
    try:
        db = next(get_db())
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = "cancelled"
            db.commit()
    except Exception:
        pass

    return {
        "success": True,
        "task_id": task_id,
        "cancelled": cancelled,
        "message": "Task cancellation requested"
    }


@router.post("/cancel-all")
async def cancel_all_tasks():
    """
    Cancel all running tasks

    Used when user wants to stop all ongoing operations.
    """
    await cancellation_service.cancel_all()

    return {
        "success": True,
        "message": "All tasks cancellation requested"
    }


@router.get("/active")
async def get_active_tasks():
    """Get list of currently active/cancelled task IDs"""
    return {
        "active_tasks": cancellation_service.get_active_tasks(),
        "cancelled_tasks": cancellation_service.get_cancelled_tasks()
    }
