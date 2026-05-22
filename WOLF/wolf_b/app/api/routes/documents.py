from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.db.models import Document
from app.db.schemas import DocumentCreate, DocumentUpdate, DocumentResponse

router = APIRouter()

@router.get("", response_model=List[DocumentResponse])
async def get_documents(
    type: Optional[str] = None,
    task_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all documents with optional filtering"""
    query = db.query(Document)
    if type:
        query = query.filter(Document.type == type)
    if task_id:
        query = query.filter(Document.task_id == task_id)

    documents = query.all()
    return documents

@router.post("", response_model=DocumentResponse)
async def create_document(doc: DocumentCreate, db: Session = Depends(get_db)):
    """Create a new document"""
    doc_id = f"doc-{len(db.query(Document).all()) + 1}"
    db_doc = Document(
        id=doc_id,
        title=doc.title,
        content=doc.content,
        type=doc.type,
        task_id=doc.task_id,
        created_by=doc.created_by,
        version=1
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc

@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str, db: Session = Depends(get_db)):
    """Get document by ID"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.put("/{doc_id}", response_model=DocumentResponse)
async def update_document(doc_id: str, updates: DocumentUpdate, db: Session = Depends(get_db)):
    """Update document"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    update_data = updates.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(doc, key, value)

    if updates.content:
        doc.version += 1

    db.commit()
    db.refresh(doc)
    return doc

@router.get("/{doc_id}/versions")
async def get_document_versions(doc_id: str, db: Session = Depends(get_db)):
    """Get document version history"""
    return []
