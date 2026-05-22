"""
Task Management Tools - Full task lifecycle management
Already migrated: create_task, list_tasks, get_task, update_task, delete_task
This file adds task output and stop functionality
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

router = APIRouter()

# Shared task storage (imported from task_tools for consistency)
# In production this would be a database
task_storage: dict = {}


class TaskOutput(BaseModel):
    task_id: str
    output: Any
    timestamp: str


class TaskResult(BaseModel):
    task_id: str
    status: str
    result: Optional[str] = None
    error: Optional[str] = None


# ========== Task Output ==========

@router.post("/tasks/{task_id}/output")
async def save_task_output(task_id: str, output: Any) -> dict:
    """Save output from a task execution"""
    task_output = {
        "task_id": task_id,
        "output": output,
        "timestamp": datetime.now().isoformat()
    }

    # Store in a separate outputs dict
    outputs_key = f"output_{task_id}"
    if outputs_key not in task_storage:
        task_storage[outputs_key] = []
    task_storage[outputs_key].append(task_output)

    return {"success": True, "output": task_output}


@router.get("/tasks/{task_id}/output")
async def get_task_output(task_id: str) -> List[dict]:
    """Get all outputs for a task"""
    outputs_key = f"output_{task_id}"
    outputs = task_storage.get(outputs_key, [])
    return outputs


# ========== Task Results ==========

@router.post("/tasks/{task_id}/result")
async def save_task_result(task_id: str, result: TaskResult) -> dict:
    """Save the result of a task execution"""
    task_result = {
        "task_id": task_id,
        "status": result.status,
        "result": result.result,
        "error": result.error,
        "timestamp": datetime.now().isoformat()
    }

    results_key = f"result_{task_id}"
    task_storage[results_key] = task_result

    return {"success": True, "result": task_result}


@router.get("/tasks/{task_id}/result")
async def get_task_result(task_id: str) -> dict:
    """Get the result of a task"""
    results_key = f"result_{task_id}"
    result = task_storage.get(results_key)

    if not result:
        raise HTTPException(status_code=404, detail="Task result not found")

    return result


# ========== Task Stop ==========

@router.post("/tasks/{task_id}/stop")
async def stop_task(task_id: str) -> dict:
    """Stop a running task"""
    stop_key = f"stop_{task_id}"
    task_storage[stop_key] = {
        "requested": True,
        "timestamp": datetime.now().isoformat()
    }

    return {"success": True, "message": f"Stop requested for task {task_id}"}


@router.get("/tasks/{task_id}/stop")
async def get_stop_request(task_id: str) -> dict:
    """Check if a stop has been requested for a task"""
    stop_key = f"stop_{task_id}"
    stop_request = task_storage.get(stop_key, {"requested": False})

    return stop_request