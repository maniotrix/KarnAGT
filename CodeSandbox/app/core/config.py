#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration Management

Environment-based configuration using Pydantic BaseModel.
Loads configuration from environment variables with sensible defaults.
"""

import os
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application settings loaded from environment variables"""
    
    # === Application Settings ===
    app_name: str = "CodeSandbox"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True
    
    # === Server Configuration ===
    host: str = "127.0.0.1"
    port: int = 8080
    workers: int = 1
    
    # === CORS Configuration ===
    cors_origins: List[str] = ["*"]
    cors_allow_credentials: bool = True
    
    # === Jupyter Server Configuration ===
    jupyter_host: str = "127.0.0.1" 
    jupyter_port: int = 8888
    jupyter_token: str = ""
    jupyter_password: str = ""
    
    # === Workspace Configuration ===
    workspace_base_path: str = "/tmp/workspaces"
    workspace_default_ttl_hours: int = 2
    workspace_max_ttl_hours: int = 24
    workspace_cleanup_interval_minutes: int = 15
    
    # === File Management ===
    max_file_size_mb: int = 100
    max_files_per_workspace: int = 50
    max_workspace_size_mb: int = 500
    allowed_file_extensions: List[str] = [".py", ".txt", ".csv", ".json", ".yaml", ".yml", ".md", ".pdf", ".png", ".jpg", ".jpeg"]
    
    # === Execution Configuration ===
    default_execution_timeout: int = 30
    max_execution_timeout: int = 300
    blocked_imports: List[str] = ["subprocess", "os.system", "eval", "exec", "requests", "urllib", "socket", "http"]
    
    # === Logging Configuration ===
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: Optional[str] = None
    
    def __init__(self, **data):
        # Load from environment variables
        env_data = {
            # Application
            "app_name": os.getenv("APP_NAME", "CodeSandbox"),
            "app_version": os.getenv("APP_VERSION", "1.0.0"), 
            "environment": os.getenv("ENVIRONMENT", "development"),
            "debug": os.getenv("DEBUG", "true").lower() == "true",
            
            # Server
            "host": os.getenv("HOST", "127.0.0.1"),
            "port": int(os.getenv("PORT", "8080")),
            "workers": int(os.getenv("WORKERS", "1")),
            
            # CORS
            "cors_origins": os.getenv("CORS_ORIGINS", "*").split(",") if os.getenv("CORS_ORIGINS") else ["*"],
            "cors_allow_credentials": os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true",
            
            # Jupyter
            "jupyter_host": os.getenv("JUPYTER_HOST", "127.0.0.1"),
            "jupyter_port": int(os.getenv("JUPYTER_PORT", "8888")),
            "jupyter_token": os.getenv("JUPYTER_TOKEN", ""),
            "jupyter_password": os.getenv("JUPYTER_PASSWORD", ""),
            
            # Workspace
            "workspace_base_path": os.getenv("WORKSPACE_BASE_PATH", "/tmp/workspaces"),
            "workspace_default_ttl_hours": int(os.getenv("WORKSPACE_DEFAULT_TTL_HOURS", "2")),
            "workspace_max_ttl_hours": int(os.getenv("WORKSPACE_MAX_TTL_HOURS", "24")),
            "workspace_cleanup_interval_minutes": int(os.getenv("WORKSPACE_CLEANUP_INTERVAL_MINUTES", "15")),
            
            # Files
            "max_file_size_mb": int(os.getenv("MAX_FILE_SIZE_MB", "100")),
            "max_files_per_workspace": int(os.getenv("MAX_FILES_PER_WORKSPACE", "50")),
            "max_workspace_size_mb": int(os.getenv("MAX_WORKSPACE_SIZE_MB", "500")),
            "allowed_file_extensions": os.getenv("ALLOWED_FILE_EXTENSIONS", ".py,.txt,.csv,.json,.yaml,.yml,.md,.pdf,.png,.jpg,.jpeg").split(","),
            
            # Execution
            "default_execution_timeout": int(os.getenv("DEFAULT_EXECUTION_TIMEOUT", "30")),
            "max_execution_timeout": int(os.getenv("MAX_EXECUTION_TIMEOUT", "300")),
            "blocked_imports": os.getenv("BLOCKED_IMPORTS", "subprocess,os.system,eval,exec,requests,urllib,socket,http").split(","),
            
            # Logging
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "log_format": os.getenv("LOG_FORMAT", "json"),
            "log_file": os.getenv("LOG_FILE"),
        }
        
        # Merge with provided data (provided data takes precedence)
        env_data.update(data)
        super().__init__(**env_data)
    
    @property
    def jupyter_url(self) -> str:
        """Complete Jupyter server URL"""
        return f"http://{self.jupyter_host}:{self.jupyter_port}"
    
    @property 
    def max_file_size_bytes(self) -> int:
        """Max file size in bytes"""
        return self.max_file_size_mb * 1024 * 1024
    
    @property
    def max_workspace_size_bytes(self) -> int:
        """Max workspace size in bytes"""
        return self.max_workspace_size_mb * 1024 * 1024
    
    def get_jupyter_headers(self) -> Dict[str, str]:
        """Get headers for Jupyter API requests"""
        headers = {"Content-Type": "application/json"}
        if self.jupyter_token:
            headers["Authorization"] = f"token {self.jupyter_token}"
        return headers
    
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.environment.lower() in ("development", "dev", "local")
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.environment.lower() in ("production", "prod")


# Global settings instance
_settings = None


def get_settings() -> Settings:
    """Get global settings instance (singleton)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings 