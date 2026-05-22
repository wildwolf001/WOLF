"""
Ask User Question Tool - Prompt user for input
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Any

router = APIRouter()

# Pending questions storage
pending_questions: List[dict] = []


class QuestionInput(BaseModel):
    question: str
    options: Optional[List[str]] = None  # For multiple choice
    default: Optional[str] = None
    timeout_seconds: int = 300


class QuestionOutput(BaseModel):
    question_id: str
    question: str
    answer: Optional[str] = None
    status: str  # pending, answered, timeout


@router.post("/question")
async def ask_question(input: QuestionInput) -> dict:
    """Ask a question to the user"""
    import uuid
    question_id = f"q-{uuid.uuid4().hex[:8]}"

    question = {
        "id": question_id,
        "question": input.question,
        "options": input.options,
        "default": input.default,
        "timeout_seconds": input.timeout_seconds,
        "status": "pending",
        "created_at": str(int(__import__('time').time()))
    }

    pending_questions.append(question)

    return {
        "question_id": question_id,
        "question": input.question,
        "status": "pending"
    }


@router.get("/question/{question_id}")
async def get_question_status(question_id: str) -> dict:
    """Get the status of a question"""
    for q in pending_questions:
        if q["id"] == question_id:
            return q

    raise HTTPException(status_code=404, detail="Question not found")


@router.post("/question/{question_id}/answer")
async def answer_question(question_id: str, answer: str) -> dict:
    """Submit an answer to a question"""
    for q in pending_questions:
        if q["id"] == question_id:
            q["answer"] = answer
            q["status"] = "answered"
            return {"question_id": question_id, "answer": answer, "status": "answered"}

    raise HTTPException(status_code=404, detail="Question not found")


@router.get("/questions/pending")
async def list_pending_questions() -> List[dict]:
    """List all pending questions"""
    return [q for q in pending_questions if q["status"] == "pending"]