"""
Memory Route
Persistent memory management using file-based MemoryDirectory
"""
import time
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class MemoryItem(BaseModel):
    name: str
    description: str = ""
    type: str = "reference"
    content: str = ""
    why: Optional[str] = None
    howToApply: Optional[str] = None


def _get_memory_dir():
    """获取 MemoryDirectory 实例"""
    from ...memory.directory import get_memory_directory
    return get_memory_directory()


@router.get("/memory")
async def get_memory(
    session_id: str,
    workspace_id: str = "default"
) -> dict:
    """Get session memory (from persistent storage)"""
    from ...services.session_memory.session_memory import SessionMemory

    memory = SessionMemory(session_id=session_id)
    items = [
        {
            "id": item.id,
            "content": item.content,
            "type": item.type,
            "timestamp": item.timestamp
        }
        for item in memory._items
    ]

    return {
        "session_id": session_id,
        "item_count": len(items),
        "items": items
    }


@router.delete("/memory")
async def clear_memory(session_id: str) -> dict:
    """Clear session memory"""
    from ...services.session_memory.session_memory import SessionMemory

    memory = SessionMemory(session_id=session_id)
    memory.clear()

    return {"status": "ok"}


@router.get("/memory/recent")
async def get_recent_memory(
    session_id: str,
    count: int = 10,
    workspace_id: str = "default"
) -> dict:
    """Get recent memory items"""
    from ...services.session_memory.session_memory import SessionMemory

    memory = SessionMemory(session_id=session_id)
    recent = memory.get_recent(count)

    return {
        "session_id": session_id,
        "items": [
            {
                "id": item.id,
                "content": item.content,
                "type": item.type,
                "timestamp": item.timestamp
            }
            for item in recent
        ]
    }


# ============== PERSISTENT MEMORY ENDPOINTS (File-based) ==============

@router.get("/memory/all")
async def get_all_memories(
    session_id: str,
    workspace_id: str = "default"
) -> dict:
    """
    Get all persistent memories, organized by type.
    """
    memory_dir = _get_memory_dir()
    files = memory_dir.list_memory_files()

    memories = []
    by_type: Dict[str, list] = {
        "user": [],
        "feedback": [],
        "project": [],
        "reference": []
    }

    for filepath, entry in files:
        d = entry.to_dict()
        memories.append(d)
        mtype = entry.memory_type.value
        if mtype in by_type:
            by_type[mtype].append(d)

    return {
        "session_id": session_id,
        "memories": memories,
        "by_type": by_type,
        "total": len(memories)
    }


@router.post("/memory/sync")
async def sync_memories(
    session_id: str,
    memories: List[Dict[str, Any]]
) -> dict:
    """
    Sync memories from frontend to persistent storage.
    Each memory in the list is written as a .md file.
    """
    from ...memory.types import MemoryEntry, MemoryTypeEnum

    memory_dir = _get_memory_dir()
    synced = 0

    for m in memories:
        try:
            memory_type = MemoryTypeEnum.from_string(m.get("type", "reference"))
            entry = MemoryEntry(
                name=m.get("name", "untitled"),
                description=m.get("description", ""),
                memory_type=memory_type,
                content=m.get("content", ""),
                why=m.get("why"),
                how_to_apply=m.get("howToApply"),
            )
            memory_dir.write_memory(entry)
            synced += 1
        except Exception as e:
            pass  # skip invalid entries

    return {
        "status": "ok",
        "session_id": session_id,
        "synced_count": synced
    }


@router.get("/memory/stats")
async def get_memory_stats(
    session_id: str,
    workspace_id: str = "default"
) -> dict:
    """
    Get memory statistics from persistent storage.
    """
    memory_dir = _get_memory_dir()
    files = memory_dir.list_memory_files()

    by_type: Dict[str, int] = {
        "user": 0,
        "feedback": 0,
        "project": 0,
        "reference": 0
    }

    total_usage = 0
    for _, entry in files:
        mtype = entry.memory_type.value
        if mtype in by_type:
            by_type[mtype] += 1
        total_usage += entry.usage_count

    total = len(files)
    return {
        "session_id": session_id,
        "total": total,
        "by_type": by_type,
        "avg_usage": total_usage / total if total else 0,
        "total_usage": total_usage
    }


@router.post("/memory")
async def create_memory(
    session_id: str,
    memory: MemoryItem,
    workspace_id: str = "default"
) -> dict:
    """
    Create a new persistent memory entry.
    """
    from ...memory.types import MemoryEntry, MemoryTypeEnum

    memory_dir = _get_memory_dir()
    memory_type = MemoryTypeEnum.from_string(memory.type)

    entry = MemoryEntry(
        name=memory.name,
        description=memory.description,
        memory_type=memory_type,
        content=memory.content,
        why=memory.why,
        how_to_apply=memory.howToApply,
    )

    filepath = memory_dir.write_memory(entry)

    return {
        "status": "ok",
        "memory": entry.to_dict(),
        "filepath": filepath,
    }


@router.patch("/memory/{memory_id}")
async def update_memory(
    session_id: str,
    memory_id: str,
    updates: Dict[str, Any]
) -> dict:
    """
    Update a persistent memory entry by ID.
    """
    from ...memory.types import MemoryEntry

    memory_dir = _get_memory_dir()

    # Find the file by entry_id
    target_entry = None
    target_filepath = None
    for filepath, entry in memory_dir.list_memory_files():
        if entry.entry_id == memory_id:
            target_entry = entry
            target_filepath = filepath
            break

    if target_entry is None:
        return {"status": "error", "message": "Memory not found"}

    # Apply updates
    if "name" in updates and updates["name"] is not None:
        target_entry.name = updates["name"]
    if "description" in updates and updates["description"] is not None:
        target_entry.description = updates["description"]
    if "type" in updates and updates["type"] is not None:
        from ...memory.types import parse_memory_type
        new_type = parse_memory_type(updates["type"])
        if new_type:
            target_entry.memory_type = new_type
    if "content" in updates and updates["content"] is not None:
        target_entry.content = updates["content"]
    if "why" in updates:
        target_entry.why = updates["why"]
    if "howToApply" in updates:
        target_entry.how_to_apply = updates["howToApply"]

    from datetime import datetime
    target_entry.updated_at = datetime.utcnow()

    # Write updated entry (this will update MEMORY.md index)
    memory_dir.write_memory(target_entry)

    return {"status": "ok", "memory": target_entry.to_dict()}


@router.delete("/memory/{memory_id}")
async def delete_memory(
    session_id: str,
    memory_id: str
) -> dict:
    """
    Delete a persistent memory entry by ID.
    """
    memory_dir = _get_memory_dir()

    # Find the file by entry_id
    target_filename = None
    for filepath, entry in memory_dir.list_memory_files():
        if entry.entry_id == memory_id:
            # Extract filename from path
            import os
            target_filename = os.path.basename(filepath)
            break

    if target_filename is None:
        return {"status": "error", "message": "Memory not found", "deleted": 0}

    deleted = memory_dir.delete_memory(target_filename)

    return {
        "status": "ok" if deleted else "error",
        "deleted": 1 if deleted else 0
    }


@router.post("/memory/{memory_id}/use")
async def use_memory(
    session_id: str,
    memory_id: str
) -> dict:
    """
    Mark a memory as used (increment usage count, update lastUsedAt).
    """
    from datetime import datetime

    memory_dir = _get_memory_dir()

    for filepath, entry in memory_dir.list_memory_files():
        if entry.entry_id == memory_id:
            entry.usage_count += 1
            entry.last_used_at = datetime.utcnow()
            memory_dir.write_memory(entry)
            return {"status": "ok", "memory": entry.to_dict()}

    return {"status": "error", "message": "Memory not found"}
