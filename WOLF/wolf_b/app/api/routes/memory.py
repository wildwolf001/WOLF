"""
Memory API - 用户记忆管理
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import uuid
import os
import json

router = APIRouter()

# Memory storage directory
MEMORY_DIR = os.path.join(os.getcwd(), "wolf_data", "memory")
os.makedirs(MEMORY_DIR, exist_ok=True)


class MemoryEntry(BaseModel):
    """记忆条目"""
    id: str
    name: str
    description: Optional[str] = ""
    type: str  # user, feedback, project, reference
    content: str
    why: Optional[str] = ""
    howToApply: Optional[str] = ""
    usageCount: int = 0
    createdAt: str = ""
    updatedAt: str = ""
    lastUsedAt: Optional[str] = None


class MemoryCreate(BaseModel):
    """创建记忆请求"""
    name: str
    description: Optional[str] = ""
    type: str = "reference"
    content: str
    why: Optional[str] = ""
    howToApply: Optional[str] = ""


class MemoryUpdate(BaseModel):
    """更新记忆请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    content: Optional[str] = None
    why: Optional[str] = None
    howToApply: Optional[str] = None


def _get_session_file(session_id: str) -> str:
    """获取session的memory文件路径"""
    return os.path.join(MEMORY_DIR, f"session_{session_id}.json")


def _load_session_memories(session_id: str) -> List[Dict[str, Any]]:
    """加载session的记忆"""
    filepath = _get_session_file(session_id)
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def _save_session_memories(session_id: str, memories: List[Dict[str, Any]]):
    """保存session的记忆"""
    filepath = _get_session_file(session_id)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(memories, f, ensure_ascii=False, indent=2)


@router.get("/")
async def get_memories(session_id: str) -> List[Dict[str, Any]]:
    """获取session的所有记忆"""
    memories = _load_session_memories(session_id)
    return memories


@router.post("/")
async def create_memory(session_id: str, memory: MemoryCreate) -> Dict[str, Any]:
    """创建新记忆"""
    now = datetime.now().isoformat()

    new_memory = {
        "id": f"mem-{uuid.uuid4().hex[:8]}",
        "name": memory.name,
        "description": memory.description or "",
        "type": memory.type,
        "content": memory.content,
        "why": memory.why or "",
        "howToApply": memory.howToApply or "",
        "usageCount": 0,
        "createdAt": now,
        "updatedAt": now,
        "lastUsedAt": None
    }

    memories = _load_session_memories(session_id)
    memories.append(new_memory)
    _save_session_memories(session_id, memories)

    return {"success": True, "memory": new_memory}


@router.put("/{memory_id}")
async def update_memory(session_id: str, memory_id: str, updates: MemoryUpdate) -> Dict[str, Any]:
    """更新记忆"""
    memories = _load_session_memories(session_id)

    for i, m in enumerate(memories):
        if m["id"] == memory_id:
            if updates.name is not None:
                m["name"] = updates.name
            if updates.description is not None:
                m["description"] = updates.description
            if updates.type is not None:
                m["type"] = updates.type
            if updates.content is not None:
                m["content"] = updates.content
            if updates.why is not None:
                m["why"] = updates.why
            if updates.howToApply is not None:
                m["howToApply"] = updates.howToApply
            m["updatedAt"] = datetime.now().isoformat()

            _save_session_memories(session_id, memories)
            return {"success": True, "memory": m}

    raise HTTPException(status_code=404, detail="Memory not found")


@router.delete("/{memory_id}")
async def delete_memory(session_id: str, memory_id: str) -> Dict[str, Any]:
    """删除记忆"""
    memories = _load_session_memories(session_id)
    original_len = len(memories)
    memories = [m for m in memories if m["id"] != memory_id]

    if len(memories) == original_len:
        raise HTTPException(status_code=404, detail="Memory not found")

    _save_session_memories(session_id, memories)
    return {"success": True, "message": "Memory deleted"}


@router.post("/{memory_id}/use")
async def use_memory(session_id: str, memory_id: str) -> Dict[str, Any]:
    """标记记忆被使用"""
    memories = _load_session_memories(session_id)

    for m in memories:
        if m["id"] == memory_id:
            m["usageCount"] = m.get("usageCount", 0) + 1
            m["lastUsedAt"] = datetime.now().isoformat()
            _save_session_memories(session_id, memories)
            return {"success": True, "memory": m}

    raise HTTPException(status_code=404, detail="Memory not found")


@router.get("/search")
async def search_memories(session_id: str, query: str) -> List[Dict[str, Any]]:
    """搜索记忆"""
    memories = _load_session_memories(session_id)
    query_lower = query.lower()

    results = []
    for m in memories:
        if (query_lower in m.get("name", "").lower() or
            query_lower in m.get("content", "").lower() or
            query_lower in m.get("description", "").lower()):
            results.append(m)

    return results