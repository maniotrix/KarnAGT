"""
Core Configuration Settings
"""
from typing import List, Optional, Union
from pydantic import BaseSettings, validator, AnyHttpUrl
from functools import lru_cache
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings"""
    
    # Basic App Config
    PROJECT_NAME: str = "ChatGPT Clone Backend"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # Database URLs
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/chatgpt_clone"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Vector Database (Qdrant)
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_CHAT_MEMORIES: str = "chat_memories"
    QDRANT_COLLECTION_KNOWLEDGE_FILES: str = "knowledge_files"
    QDRANT_COLLECTION_USER_PROFILES: str = "user_profiles"
    
    # Graph Database (Neo4j)
    NEO4J_URL: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    
    # AI Services
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_MAX_TOKENS: int = 4000
    OPENAI_TEMPERATURE: float = 0.7
    
    # Graphiti Configuration
    GRAPHITI_OPENAI_API_KEY: Optional[str] = None  # Will use OPENAI_API_KEY if not set
    GRAPHITI_NEO4J_URL: Optional[str] = None  # Will use NEO4J_URL if not set
    GRAPHITI_NEO4J_USERNAME: Optional[str] = None
    GRAPHITI_NEO4J_PASSWORD: Optional[str] = None
    
    # Background Processing (Celery)
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    
    # File Storage
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_FILE_TYPES: List[str] = [".pdf", ".docx", ".txt", ".md"]
    
    # Memory Management
    MEMORY_IMPORTANCE_THRESHOLD: float = 0.6
    MEMORY_DECAY_RATE: float = 0.1
    MEMORY_MAX_AGE_DAYS: int = 365
    
    # Cost Management
    COST_TRACKING_ENABLED: bool = True
    DEFAULT_USER_QUOTA_USD: float = 10.0
    COST_ALERT_THRESHOLD: float = 0.8  # 80% of quota
    
    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    LOG_LEVEL: str = "INFO"
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    @validator("DATABASE_URL", pre=True)
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL")
        return v
    
    def get_graphiti_neo4j_url(self) -> str:
        """Get Neo4j URL for Graphiti (fallback to main Neo4j URL)"""
        return self.GRAPHITI_NEO4J_URL or self.NEO4J_URL
    
    def get_graphiti_openai_key(self) -> str:
        """Get OpenAI API key for Graphiti (fallback to main OpenAI key)"""
        return self.GRAPHITI_OPENAI_API_KEY or self.OPENAI_API_KEY
    
    def get_upload_path(self) -> Path:
        """Get upload directory path"""
        return Path(self.UPLOAD_DIR)
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings() 