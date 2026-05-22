"""
Config Tool - Get and set configuration values
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime

router = APIRouter()

# Config storage
config_db: Dict[str, Any] = {
    "work_directory": None,
    "model": "default",
    "max_tokens": 4096,
    "temperature": 0.7,
}


class ConfigUpdate(BaseModel):
    key: str
    value: Any


@router.get("/config")
async def get_config() -> dict:
    """Get all configuration"""
    return config_db


@router.get("/config/{key}")
async def get_config_value(key: str) -> dict:
    """Get a specific config value"""
    if key not in config_db:
        raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")
    return {"key": key, "value": config_db[key]}


@router.post("/config")
async def set_config(update: ConfigUpdate) -> dict:
    """Set a config value"""
    config_db[update.key] = update.value
    return {"success": True, "key": update.key, "value": update.value}


@router.put("/config/{key}")
async def update_config_key(key: str, value: Any) -> dict:
    """Update a config value"""
    config_db[key] = value
    return {"success": True, "key": key, "value": value}


@router.delete("/config/{key}")
async def delete_config_key(key: str) -> dict:
    """Delete a config value"""
    if key in config_db:
        del config_db[key]
    return {"success": True, "message": f"Config key '{key}' deleted"}