from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Enum
from sqlalchemy.sql import func
from app.db.database import Base
import enum

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"

class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    type = Column(String)  # research, model_development, coding, etc.
    status = Column(String, default=TaskStatus.PENDING.value)
    priority = Column(String, default=TaskPriority.MEDIUM.value)
    assignee_id = Column(String, ForeignKey("agents.id"), nullable=True)
    parent_id = Column(String, nullable=True)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    dependencies = Column(Text)  # JSON string
    task_metadata = Column(Text)  # JSON string
