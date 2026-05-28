from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "WOLF"
    DEBUG: bool = True
    API_VERSION: str = "v1"

    # Database
    DATABASE_URL: str = "sqlite:///./wolf.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Local Storage Paths
    LOCAL_STORAGE_PATH: str = "./wolf_data"  # 本地文件存储根目录
    KNOWLEDGE_BASE_PATH: str = "./wolf_data/knowledge"  # 知识库存储路径
    SESSIONS_PATH: str = "./wolf_data/sessions"  # 会话历史存储路径
    UPLOAD_PATH: str = "./wolf_data/uploads"  # 上传文件存储路径

    # LLM Configuration
    LLM_PROVIDER: str = "minimax"
    # MiniMax
    MINIMAX_API_KEY: Optional[str] = None
    MINIMAX_GROUP_ID: Optional[str] = None
    MINIMAX_MODEL: str = "abab6.5s-chat"
    # OpenAI (fallback)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4"
    # Anthropic (fallback)
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "MiniMax-M2.7"

    # Vector DB
    VECTOR_DB_URL: str = "http://localhost:6333"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
