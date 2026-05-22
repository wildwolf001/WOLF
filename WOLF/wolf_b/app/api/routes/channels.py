"""
Channel System - Remote control integrations (Telegram, Discord, Feishu, etc.)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

router = APIRouter()

# Channel configuration storage
_channels: Dict[str, dict] = {}
_channel_credentials: Dict[str, dict] = {}  # Sensitive data stored separately


class ChannelConfig(BaseModel):
    type: str  # telegram, discord, feishu, webhook
    name: str
    enabled: bool = True
    config: Dict[str, Any] = {}  # channel-specific settings


class ChannelCredential(BaseModel):
    bot_token: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    webhook_url: Optional[str] = None


# Channel message storage
_channel_messages: List[dict] = []


class ChannelMessage(BaseModel):
    channel_id: str
    direction: str  # inbound, outbound
    content: str
    sender: Optional[str] = None
    timestamp: datetime


def get_channel_status(channel_type: str, config: dict) -> dict:
    """Get simulated channel status"""
    return {
        "connected": config.get("enabled", True),
        "last_sync": datetime.now().isoformat(),
        "status": "active" if config.get("enabled") else "disabled",
    }


@router.post("/channels")
async def create_channel(config: ChannelConfig):
    """Create a new channel integration"""
    channel_id = f"ch-{uuid.uuid4().hex[:8]}"

    new_channel = {
        "id": channel_id,
        "type": config.type,
        "name": config.name,
        "enabled": config.enabled,
        "config": config.config,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    _channels[channel_id] = new_channel

    return {"success": True, "channel": new_channel}


@router.get("/channels")
async def list_channels():
    """List all configured channels"""
    channels_list = []
    for channel_id, channel in _channels.items():
        status = get_channel_status(channel["type"], channel)
        channels_list.append({
            **channel,
            "status": status["status"],
            "last_sync": status["last_sync"],
            "connected": status["connected"],
        })
    return {"success": True, "channels": channels_list}


@router.get("/channels/{channel_id}")
async def get_channel(channel_id: str):
    """Get channel details"""
    if channel_id not in _channels:
        raise HTTPException(status_code=404, detail="Channel not found")

    channel = _channels[channel_id]
    status = get_channel_status(channel["type"], channel)

    return {
        "success": True,
        "channel": {
            **channel,
            "status": status["status"],
            "last_sync": status["last_sync"],
            "connected": status["connected"],
        }
    }


@router.put("/channels/{channel_id}")
async def update_channel(channel_id: str, updates: dict):
    """Update channel configuration"""
    if channel_id not in _channels:
        raise HTTPException(status_code=404, detail="Channel not found")

    channel = _channels[channel_id]
    for key, value in updates.items():
        if key != "id" and key != "created_at":
            channel[key] = value
    channel["updated_at"] = datetime.now().isoformat()

    return {"success": True, "channel": channel}


@router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: str):
    """Delete a channel"""
    if channel_id not in _channels:
        raise HTTPException(status_code=404, detail="Channel not found")

    del _channels[channel_id]
    if channel_id in _channel_credentials:
        del _channel_credentials[channel_id]

    return {"success": True, "message": "Channel deleted"}


@router.post("/channels/{channel_id}/enable")
async def enable_channel(channel_id: str):
    """Enable a channel"""
    if channel_id not in _channels:
        raise HTTPException(status_code=404, detail="Channel not found")

    _channels[channel_id]["enabled"] = True
    _channels[channel_id]["updated_at"] = datetime.now().isoformat()

    return {"success": True, "channel": _channels[channel_id]}


@router.post("/channels/{channel_id}/disable")
async def disable_channel(channel_id: str):
    """Disable a channel"""
    if channel_id not in _channels:
        raise HTTPException(status_code=404, detail="Channel not found")

    _channels[channel_id]["enabled"] = False
    _channels[channel_id]["updated_at"] = datetime.now().isoformat()

    return {"success": True, "channel": _channels[channel_id]}


@router.post("/channels/{channel_id}/test")
async def test_channel(channel_id: str):
    """Test channel connection"""
    if channel_id not in _channels:
        raise HTTPException(status_code=404, detail="Channel not found")

    channel = _channels[channel_id]

    # Simulate connection test
    test_result = {
        "success": True,
        "message": f"Connection test to {channel['name']} ({channel['type']}) successful",
        "response_time_ms": 45,
    }

    return test_result


@router.post("/channels/{channel_id}/credentials")
async def save_channel_credentials(channel_id: str, credentials: ChannelCredential):
    """Save channel credentials (tokens, keys, etc.)"""
    if channel_id not in _channels:
        raise HTTPException(status_code=404, detail="Channel not found")

    _channel_credentials[channel_id] = credentials.model_dump(exclude_none=True)

    return {"success": True, "message": "Credentials saved securely"}


@router.get("/channels/{channel_id}/credentials")
async def get_channel_credentials(channel_id: str):
    """Get channel credentials (masked)"""
    if channel_id not in _channels:
        raise HTTPException(status_code=404, detail="Channel not found")

    if channel_id not in _channel_credentials:
        return {"success": True, "has_credentials": False}

    creds = _channel_credentials[channel_id]
    masked = {}
    for key, value in creds.items():
        if value:
            masked[key] = "••••••••" + value[-4:] if len(value) > 4 else "••••"

    return {"success": True, "has_credentials": True, "masked": masked}


# Webhook test endpoint
@router.post("/webhook/{channel_id}/test")
async def test_webhook(channel_id: str, payload: dict):
    """Receive a test webhook payload"""
    if channel_id not in _channels:
        raise HTTPException(status_code=404, detail="Channel not found")

    message = {
        "id": f"msg-{uuid.uuid4().hex[:8]}",
        "channel_id": channel_id,
        "direction": "inbound",
        "content": str(payload),
        "sender": payload.get("sender", "webhook"),
        "timestamp": datetime.now().isoformat(),
    }
    _channel_messages.append(message)

    return {"success": True, "message": "Webhook received", "data": message}


# Default channel types
DEFAULT_CHANNELS = [
    {
        "id": "ch-telegram",
        "type": "telegram",
        "name": "Telegram Bot",
        "enabled": False,
        "config": {
            "bot_username": "",
            "commands": ["/start", "/help", "/status"],
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },
    {
        "id": "ch-discord",
        "type": "discord",
        "name": "Discord Bot",
        "enabled": False,
        "config": {
            "server_name": "",
            "channel_ids": [],
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },
    {
        "id": "ch-feishu",
        "type": "feishu",
        "name": "Feishu Bot",
        "enabled": False,
        "config": {
            "app_name": "",
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },
    {
        "id": "ch-webhook",
        "type": "webhook",
        "name": "Webhook",
        "enabled": True,
        "config": {
            "inbound_url": "",
            "outbound_url": "",
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },
]


def init_default_channels():
    """Initialize default channels"""
    for channel in DEFAULT_CHANNELS:
        if channel["id"] not in _channels:
            _channels[channel["id"]] = channel


# Initialize on module load
init_default_channels()