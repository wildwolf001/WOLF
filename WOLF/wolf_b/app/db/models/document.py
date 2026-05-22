from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text)
    type = Column(String)  # paper, plan, doc
    version = Column(Integer, default=1)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=True)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
