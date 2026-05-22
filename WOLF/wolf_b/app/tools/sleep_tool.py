"""
Sleep Tool - Delay execution for specified duration
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import asyncio

router = APIRouter()


class SleepInput(BaseModel):
    duration_seconds: float
    reason: str = ""


class SleepOutput(BaseModel):
    slept_seconds: float
    woke_at: str


@router.post("/sleep")
async def sleep(input: SleepInput) -> SleepOutput:
    """Sleep for specified duration"""
    if input.duration_seconds < 0:
        raise HTTPException(status_code=400, detail="Duration must be non-negative")

    if input.duration_seconds > 3600:
        raise HTTPException(status_code=400, detail="Maximum sleep duration is 3600 seconds (1 hour)")

    await asyncio.sleep(input.duration_seconds)

    return {
        "slept_seconds": input.duration_seconds,
        "woke_at": datetime.now().isoformat()
    }