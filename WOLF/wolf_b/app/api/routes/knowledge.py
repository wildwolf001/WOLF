from fastapi import APIRouter, HTTPException
from typing import List, Optional
from app.services.knowledge_service import knowledge_service

router = APIRouter()


@router.post("/search")
async def search_knowledge(query: str, top_k: int = 5, filters: Optional[dict] = None):
    """Search knowledge base using RAG service"""
    results = await knowledge_service.search(query, top_k=top_k, filters=filters)
    return {
        "success": True,
        "query": query,
        "results": results,
        "count": len(results)
    }


@router.post("")
async def add_knowledge_entry(entry: dict):
    """Add entry to knowledge base via RAG service"""
    content = entry.get("content", "")
    metadata = entry.get("metadata", {})
    doc_id = entry.get("id")

    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    entry_id = knowledge_service.add_document(content, metadata, doc_id)
    return {
        "success": True,
        "id": entry_id,
        "message": "Entry added to knowledge base"
    }


@router.delete("/{entry_id}")
async def delete_knowledge_entry(entry_id: str):
    """Delete entry from knowledge base"""
    success = knowledge_service.delete_entry(entry_id)
    if success:
        return {"success": True, "message": "Entry deleted"}
    raise HTTPException(status_code=404, detail="Entry not found")


@router.get("/{entry_id}")
async def get_knowledge_entry(entry_id: str):
    """Get a specific knowledge entry"""
    entry = knowledge_service.get_entry(entry_id)
    if entry:
        return {"success": True, "entry": entry}
    raise HTTPException(status_code=404, detail="Entry not found")


@router.get("/")
async def list_knowledge_entries(limit: int = 100):
    """List all knowledge entries"""
    entries = knowledge_service.list_entries(limit=limit)
    return {"success": True, "entries": entries, "count": len(entries)}
