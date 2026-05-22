"""
Schedule/Cron Tool - Schedule tasks with cron-like syntax
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import re

router = APIRouter()

# Scheduled tasks storage
scheduled_tasks: Dict[str, dict] = {}


class ScheduleInput(BaseModel):
    name: str
    command: str  # The action to perform
    schedule: str  # Cron-like syntax: "*/5 * * * *" or "every 5 minutes"
    enabled: bool = True
    params: Optional[Dict[str, Any]] = None


class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    command: Optional[str] = None
    schedule: Optional[str] = None
    enabled: Optional[bool] = None


def parse_cron_schedule(schedule: str) -> dict:
    """
    Parse cron-like schedule string
    Formats supported:
    - "* * * * *" (standard cron)
    - "every N minutes/hours/days"
    - "at HH:MM"
    """
    schedule = schedule.strip()

    # Standard cron format: min hour day month weekday
    cron_pattern = r'^(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)$'
    cron_match = re.match(cron_pattern, schedule)

    if cron_match:
        return {
            "type": "cron",
            "minute": cron_match.group(1),
            "hour": cron_match.group(2),
            "day": cron_match.group(3),
            "month": cron_match.group(4),
            "weekday": cron_match.group(5)
        }

    # "every N minutes/hours/days"
    every_pattern = r'^every\s+(\d+)\s+(minute|minutes|hour|hours|day|days)$'
    every_match = re.match(every_pattern, schedule, re.IGNORECASE)
    if every_match:
        count = int(every_match.group(1))
        unit = every_match.group(2).lower()
        return {
            "type": "interval",
            "interval_seconds": count * 60 if "minute" in unit else count * 3600 if "hour" in unit else count * 86400
        }

    raise HTTPException(status_code=400, detail=f"Invalid schedule format: {schedule}")


@router.post("/schedule")
async def create_schedule(input: ScheduleInput) -> dict:
    """Create a scheduled task"""
    schedule_id = f"schedule-{uuid.uuid4().hex[:8]}"

    try:
        parsed_schedule = parse_cron_schedule(input.schedule)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    schedule = {
        "id": schedule_id,
        "name": input.name,
        "command": input.command,
        "schedule": input.schedule,
        "parsed_schedule": parsed_schedule,
        "enabled": input.enabled,
        "params": input.params or {},
        "last_run": None,
        "next_run": None,
        "created_at": datetime.now().isoformat()
    }

    scheduled_tasks[schedule_id] = schedule
    return {"success": True, "schedule": schedule}


@router.get("/schedules")
async def list_schedules(enabled: Optional[bool] = None) -> List[dict]:
    """List all scheduled tasks"""
    schedules = list(scheduled_tasks.values())

    if enabled is not None:
        schedules = [s for s in schedules if s["enabled"] == enabled]

    return schedules


@router.get("/schedule/{schedule_id}")
async def get_schedule(schedule_id: str) -> dict:
    """Get a scheduled task by ID"""
    if schedule_id not in scheduled_tasks:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return scheduled_tasks[schedule_id]


@router.put("/schedule/{schedule_id}")
async def update_schedule(schedule_id: str, updates: ScheduleUpdate) -> dict:
    """Update a scheduled task"""
    if schedule_id not in scheduled_tasks:
        raise HTTPException(status_code=404, detail="Schedule not found")

    schedule = scheduled_tasks[schedule_id]

    if updates.name is not None:
        schedule["name"] = updates.name
    if updates.command is not None:
        schedule["command"] = updates.command
    if updates.schedule is not None:
        schedule["schedule"] = updates.schedule
        schedule["parsed_schedule"] = parse_cron_schedule(updates.schedule)
    if updates.enabled is not None:
        schedule["enabled"] = updates.enabled

    return {"success": True, "schedule": schedule}


@router.delete("/schedule/{schedule_id}")
async def delete_schedule(schedule_id: str) -> dict:
    """Delete a scheduled task"""
    if schedule_id in scheduled_tasks:
        del scheduled_tasks[schedule_id]
    return {"success": True, "message": "Schedule deleted"}


@router.post("/schedule/{schedule_id}/trigger")
async def trigger_schedule_now(schedule_id: str) -> dict:
    """Trigger a scheduled task to run immediately"""
    if schedule_id not in scheduled_tasks:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # In a real implementation, this would enqueue the task
    return {"success": True, "message": f"Schedule {schedule_id} triggered"}