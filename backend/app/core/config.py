"""
Core Configuration Settings
"""
from typing import List, Optional, Union
from pydantic import validator
from pydantic_settings import BaseSettings
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
    
    # Base URL Configuration
    BASE_URL: Optional[str] = None  # Override via BASE_URL env var
    DOMAIN: Optional[str] = None    # Set via DOMAIN env var for production
    
    # Security
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    
    # Service-to-Service Authentication
    CODE_EXECUTOR_TOKEN: str = "code-executor-service-token-change-in-production"
    TRUSTED_INTERNAL_DOMAINS: str = "localhost,127.0.0.1,0.0.0.0"
    
    # Email Verification
    REQUIRE_EMAIL_VERIFICATION: bool = False  # Set to True to require email verification
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001"
    ALLOWED_HOSTS: str = "*"
    
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
    ALLOWED_FILE_TYPES: str = ".pdf,.docx,.txt,.md"
    
    # Image Storage (MinIO/S3 compatible)
    STORAGE_BACKEND: str = "minio"
    S3_BUCKET_NAME: str = "chatgpt-files"
    S3_ENDPOINT_URL: Optional[str] = "http://localhost:9000"
    S3_ACCESS_KEY_ID: str = "minioadmin"
    S3_SECRET_ACCESS_KEY: str = "minioadmin123"
    S3_REGION: str = "us-east-1"
    
    # Image Processing
    MAX_IMAGE_SIZE: int = 20 * 1024 * 1024  # 20MB (OpenAI limit)
    ALLOWED_IMAGE_TYPES: str = ".png,.jpg,.jpeg,.gif,.webp"
    IMAGE_QUALITY: int = 85
    IMAGE_BASE_URL: str = "http://localhost:8000/api/images"
    PRESIGNED_URL_EXPIRE_SECONDS: int = 3600
    
    # OpenAI Files API
    OPENAI_FILES_MAX_SIZE: int = 512 * 1024 * 1024  # 512MB (OpenAI limit)
    OPENAI_FILES_SUPPORTED_FORMATS: str = (
        # Vision purposes
        ".png,.jpg,.jpeg,.gif,.webp,"
        # Assistant purposes  
        ".txt,.md,.pdf,.docx,.pptx,.xlsx,"
        # Fine-tuning purposes
        ".jsonl"
    )
    OPENAI_FILES_PURPOSES: str = "vision,assistants,fine-tune"
    
    # Thumbnail Settings
    THUMBNAIL_SIZES: str = "150x150,300x300"  # Comma-separated list of WxH sizes
    THUMBNAIL_QUALITY: int = 75
    THUMBNAIL_FORMAT: str = "JPEG"  # JPEG, PNG, WEBP
    
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
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> str:
        if isinstance(v, list):
            # Convert list back to comma-separated string
            return ",".join(v)
        elif isinstance(v, str):
            # Return as-is if already string
            return v
        else:
            # Return default as string
            return "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001"
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as a list"""
        if isinstance(self.CORS_ORIGINS, str):
            return [i.strip() for i in self.CORS_ORIGINS.split(",") if i.strip()]
        return self.CORS_ORIGINS
    
    def get_allowed_hosts(self) -> List[str]:
        """Get allowed hosts as a list"""
        if isinstance(self.ALLOWED_HOSTS, str):
            if self.ALLOWED_HOSTS == "*":
                return ["*"]
            return [i.strip() for i in self.ALLOWED_HOSTS.split(",") if i.strip()]
        return self.ALLOWED_HOSTS
    
    def get_allowed_file_types(self) -> List[str]:
        """Get allowed file types as a list"""
        if isinstance(self.ALLOWED_FILE_TYPES, str):
            return [i.strip() for i in self.ALLOWED_FILE_TYPES.split(",") if i.strip()]
        return self.ALLOWED_FILE_TYPES
    
    def get_allowed_image_types(self) -> List[str]:
        """Get allowed image types as a list"""
        if isinstance(self.ALLOWED_IMAGE_TYPES, str):
            return [i.strip() for i in self.ALLOWED_IMAGE_TYPES.split(",") if i.strip()]
        return self.ALLOWED_IMAGE_TYPES
    
    def get_thumbnail_sizes(self) -> List[tuple]:
        """Get thumbnail sizes as a list of (width, height) tuples"""
        if isinstance(self.THUMBNAIL_SIZES, str):
            sizes = []
            for size_str in self.THUMBNAIL_SIZES.split(","):
                if "x" in size_str:
                    width, height = size_str.strip().split("x")
                    sizes.append((int(width), int(height)))
            return sizes
        return self.THUMBNAIL_SIZES
    
    def get_trusted_internal_domains(self) -> List[str]:
        """Get trusted internal domains as a list"""
        if isinstance(self.TRUSTED_INTERNAL_DOMAINS, str):
            return [i.strip() for i in self.TRUSTED_INTERNAL_DOMAINS.split(",") if i.strip()]
        return self.TRUSTED_INTERNAL_DOMAINS
    
    def is_internal_proxy_url(self, url: str) -> bool:
        """
        Check if URL is an internal file proxy endpoint
        Uses server base URL and file proxy constants for accurate detection
        """
        from urllib.parse import urlparse
        
        try:
            parsed = urlparse(url)
            
            # Check if domain is in trusted list
            trusted_domains = self.get_trusted_internal_domains()
            domain_with_port = f"{parsed.hostname}:{parsed.port}" if parsed.port else parsed.hostname
            
            is_trusted_domain = (
                parsed.hostname in trusted_domains or 
                domain_with_port in trusted_domains
            )
            
            if not is_trusted_domain:
                return False
            
            # Check if URL matches our server base URL and has proxy endpoints
            server_base = self.server_base_url
            if url.startswith(server_base):
                # Import here to avoid circular imports
                from app.core.file_proxy_constants import FileProxyEndpoints
                return FileProxyEndpoints.BASE_PATH in parsed.path
                
            return False
            
        except Exception:
            # If parsing fails, assume it's external
            return False
    
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
    
    @property
    def server_scheme(self) -> str:
        """Get the appropriate scheme based on environment"""
        return "https" if self.ENVIRONMENT == "production" else "http"
    
    @property
    def server_host(self) -> str:
        """Get the appropriate host for external access"""
        if self.ENVIRONMENT == "development":
            return "localhost"
        elif self.DOMAIN:
            return self.DOMAIN
        elif self.HOST == "0.0.0.0":
            # In production, you should set DOMAIN env var
            return "localhost"  # fallback
        return self.HOST
    
    @property
    def server_port_suffix(self) -> str:
        """Get port suffix if needed"""
        standard_ports = {80, 443}
        if self.PORT in standard_ports:
            return ""
        return f":{self.PORT}"
    
    @property
    def server_base_url(self) -> str:
        """Get the base URL of the FastAPI server"""
        if self.BASE_URL:
            return self.BASE_URL.rstrip('/')
        
        return f"{self.server_scheme}://{self.server_host}{self.server_port_suffix}"
    
    def get_full_url(self, path: str = "") -> str:
        """Get a full URL for a given path"""
        path = path.lstrip('/')
        return f"{self.server_base_url}/{path}" if path else self.server_base_url
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        env_ignore_empty = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings() 