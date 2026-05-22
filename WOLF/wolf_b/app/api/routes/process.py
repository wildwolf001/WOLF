"""
Process API - Unified endpoint for user requests

================================================================================
DEPRECATED: Multi-agent orchestration removed
================================================================================

All requests now use single-agent direct execution via MainAgent.
No more PM decomposition or multi-agent coordination.

- OLD: orchestration_service.process_user_request() → PM → Multi-Agent
- NEW: MainAgent.think() → Direct Response

================================================================================
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Any
from app.services.knowledge_service import knowledge_service

router = APIRouter()


class UserRequest(BaseModel):
    """User's request - now handled by single-agent MainAgent"""
    message: str
    session_id: Optional[str] = "default"

class TaskResult(BaseModel):
    """Result from task execution"""
    task_id: str
    type: str
    title: str
    status: str
    result: str

class ProcessResponse(BaseModel):
    """Response from processing user request"""
    success: bool
    message: str
    tasks: List[TaskResult]
    final_report: Optional[str] = None
    session_id: str


@router.post("/process", response_model=ProcessResponse)
async def process_user_request(request: UserRequest):
    """
    Unified endpoint for user requests.
    Now uses MainAgent with single-agent direct execution.
    """
    try:
        from app.agents.main_agent import MainAgent

        main_agent = MainAgent()
        result = await main_agent.think(request.message)

        return ProcessResponse(
            success=True,
            message="Task completed by MainAgent",
            tasks=[
                TaskResult(
                    task_id="main-001",
                    type="main",
                    title="MainAgent Execution",
                    status="completed",
                    result=result
                )
            ],
            final_report=None,
            session_id=request.session_id
        )
    except Exception as e:
        return ProcessResponse(
            success=False,
            message=str(e),
            tasks=[],
            session_id=request.session_id
        )


@router.get("/team-status")
async def get_team_status():
    """Get agent status - deprecated, single-agent mode"""
    return {
        "success": True,
        "agents": [{"role": "main", "status": "idle", "name": "MainAgent"}],
        "message": "Single-agent mode (MainAgent)"
    }


class KnowledgeSearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5


@router.post("/knowledge/search")
async def search_knowledge(request: KnowledgeSearchRequest):
    """Search the knowledge base"""
    results = await knowledge_service.search(
        query=request.query,
        top_k=request.top_k
    )
    return {"success": True, "results": results}


@router.post("/knowledge/add")
async def add_knowledge(content: str, metadata: Optional[dict] = None):
    """Add content to knowledge base"""
    entry_id = knowledge_service.add_document(content, metadata)
    return {"success": True, "entry_id": entry_id}


@router.get("/knowledge/list")
async def list_knowledge(limit: int = 100):
    """List all knowledge entries"""
    entries = knowledge_service.list_entries(limit=limit)
    return {"success": True, "entries": entries}


class MemoryExtractionRequest(BaseModel):
    """Request to extract memories from conversation"""
    messages: List[dict]
    task_results: Optional[List[dict]] = None
    final_report: Optional[str] = None


class SuggestedMemory(BaseModel):
    """A suggested memory to save"""
    name: str
    description: str
    type: str
    content: str
    why: Optional[str] = None
    how_to_apply: Optional[str] = None


@router.post("/extract-memories")
async def extract_memories(request: MemoryExtractionRequest):
    """
    Analyze conversation and suggest memories to save.
    """
    conversation_text = []
    for msg in request.messages[-20:]:
        role = "User" if msg.get("isUser") else "Assistant"
        content = msg.get("content", "")
        if content:
            conversation_text.append(f"{role}: {content}")

    conv_str = "\n".join(conversation_text)

    results_str = ""
    if request.task_results:
        results_parts = []
        for r in request.task_results:
            results_parts.append(f"## {r.get('title', 'Task')}\n{r.get('result', '')}")
        results_str = "\n\n".join(results_parts)

    final_report_section = ""
    if request.final_report:
        final_report_section = f"Final Report:\n{request.final_report}\n\n"

    extraction_prompt = f"""Analyze this conversation and extract important information that should be remembered for future interactions.

Conversation:
{conv_str}

Task Results:
{results_str}

{final_report_section}
Your task:
1. Identify factual information (names, dates, numbers, technical details)
2. Identify user preferences (coding style, communication preferences, tools used)
3. Identify project context (what they're working on, goals, constraints)
4. Identify feedback about past interactions (what worked, what didn't)

For each piece of information, determine:
- name: A short, descriptive name (max 50 chars)
- description: Brief explanation of what this is (max 100 chars)
- type: One of 'user' (preferences), 'feedback' (lessons learned), 'project' (project context), 'reference' (factual info)
- content: The actual information to remember
- why: Why this is important to remember
- how_to_apply: How to use this in future conversations

Return as JSON array of memories (max 5, only include if genuinely useful):
[
    {{
        "name": "User prefers Python",
        "description": "User's preferred programming language",
        "type": "user",
        "content": "The user prefers Python over other languages",
        "why": "To provide code examples in Python by default",
        "how_to_apply": "When generating code, prefer Python unless user specifies otherwise"
    }}
]

Only return memories that are genuinely useful to remember. If nothing worth remembering, return empty array."""

    try:
        from app.services.llm_service import llm_service
        response = await llm_service.complete(
            prompt=extraction_prompt,
            system_prompt="You are an AI assistant that extracts important information from conversations. Be selective and only suggest memories that are genuinely useful."
        )

        if not response.get("success"):
            return {"success": True, "memories": []}

        content = response.get("content", "")

        import re
        import json
        json_match = re.search(r'\[[\s\S]*\]', content)
        if json_match:
            try:
                memories = json.loads(json_match.group())
                valid_types = {'user', 'feedback', 'project', 'reference'}
                sanitized = []
                for m in memories:
                    if isinstance(m, dict) and m.get('name') and m.get('type') in valid_types:
                        sanitized.append({
                            "name": str(m.get('name', ''))[:50],
                            "description": str(m.get('description', ''))[:100],
                            "type": m.get('type'),
                            "content": str(m.get('content', '')),
                            "why": str(m.get('why', '')) if m.get('why') else None,
                            "how_to_apply": str(m.get('how_to_apply', '')) if m.get('how_to_apply') else None,
                        })
                return {"success": True, "memories": sanitized}
            except json.JSONDecodeError:
                pass

        return {"success": True, "memories": []}
    except Exception as e:
        return {"success": True, "memories": [], "error": str(e)}