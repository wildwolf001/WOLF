from sqlalchemy import Column, String, Text, DateTime, Enum
from sqlalchemy.sql import func
from app.db.database import Base
import enum

class AgentStatus(str, enum.Enum):
    IDLE = "idle"
    ANALYZING = "analyzing"
    WORKING = "working"
    WAITING = "waiting"
    ERROR = "error"
    COMPLETED = "completed"

class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, index=True)
    role = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    system_prompt = Column(Text)
    status = Column(String, default=AgentStatus.IDLE.value)
    current_task = Column(String)
    capabilities = Column(Text)  # JSON string
    llm_provider = Column(String)
    model = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
