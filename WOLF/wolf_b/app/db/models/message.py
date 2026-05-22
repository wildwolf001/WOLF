from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, index=True)
    from_agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    to_agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    content = Column(Text, nullable=False)
    type = Column(String)  # task, result, question, approval, rejection
    task_id = Column(String, ForeignKey("tasks.id"), nullable=True)
    session_id = Column(String, nullable=True)
    msg_metadata = Column(Text)  # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())
