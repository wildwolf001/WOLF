from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from app.db.database import Base

class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
