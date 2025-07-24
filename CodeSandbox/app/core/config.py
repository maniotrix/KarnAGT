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
    
    # === User Configuration ===
    cs_user: str = "code_sandbox"
    
    # === Server Configuration ===
    host: str = "127.0.0.1"
    port: int = 8080
    workers: int = 1
    
    # === CORS Configuration ===
    # List of allowed CORS origins. IMPORTANT SECURITY RULES:
    #   - Cannot use "*" with credentials in production (security risk)
    #   - Always include protocol (http:// or https://)
    #   - No wildcard patterns like *.domain.com (not supported by spec)
    #   - Use comma-separated values with NO spaces after commas in .env
    # Examples:
    #   ["*"] - Allow all origins (DEV ONLY - security risk)
    #   ["http://localhost:3000", "http://localhost:8080"] - Local development
    #   ["https://app.mydomain.com", "https://admin.mydomain.com"] - Production
    cors_origins: List[str] = ["*"]
    cors_allow_credentials: bool = True
    
    # === Jupyter Server Configuration ===
    jupyter_host: str = "127.0.0.1" 
    jupyter_port: int = 8888
    jupyter_token: str = ""
    jupyter_password: str = ""
    
    # === Workspace Configuration ===
    user_temp_base_path: str = "/tmp/code_sandbox"
    workspace_default_ttl_hours: int = 2
    workspace_max_ttl_hours: int = 24
    workspace_cleanup_interval_minutes: int = 15
    
    # === File Management ===
    max_file_size_mb: int = 100
    max_files_per_workspace: int = 50
    max_workspace_size_mb: int = 500
    
    # === Execution Configuration ===
    default_execution_timeout: int = 30
    max_execution_timeout: int = 300
    # No blocked imports for MVP - relying on container isolation for security
    blocked_imports: List[str] = []
    
    # === Logging Configuration ===
    log_level: str = "INFO"
    log_json_format: bool = False  # Auto-detected based on environment
    log_file_enabled: bool = True
    log_max_file_size_mb: int = 10
    log_backup_count: int = 5
    log_correlation_id_header: str = "x-correlation-id"
    log_performance_threshold_ms: float = 1000.0
    
    @property
    def workspace_base_path(self) -> str:
        """Workspace base path derived from user temp base path"""
        return f"{self.user_temp_base_path}/workspaces"
    
    @property
    def logs_base_path(self) -> str:
        """Logs base path derived from user temp base path"""
        return f"{self.user_temp_base_path}/logs"
    
    def _parse_cors_origins(self, origins_str: str) -> List[str]:
        """Parse CORS origins from environment variable with proper validation"""
        if not origins_str or origins_str.strip() == "":
            return ["*"]
        
        # Split by comma and strip whitespace
        origins = [origin.strip() for origin in origins_str.split(",")]
        
        # Filter out empty strings
        origins = [origin for origin in origins if origin]
        
        # Validate origins format (basic check)
        validated_origins = []
        for origin in origins:
            if origin == "*":
                validated_origins.append(origin)
            elif origin.startswith(("http://", "https://")):
                validated_origins.append(origin)
            else:
                # Log warning but still allow (for flexibility)
                print(f"Warning: CORS origin '{origin}' should include protocol (http:// or https://)")
                validated_origins.append(origin)
        
        return validated_origins if validated_origins else ["*"]

    def _validate_cors_security(self) -> None:
        """Validate CORS configuration for security issues"""
        # Check for dangerous combination: wildcard origins with credentials
        if "*" in self.cors_origins and self.cors_allow_credentials and not self.is_development():
            print(
                "WARNING: Using CORS_ORIGINS=* with CORS_ALLOW_CREDENTIALS=true in production "
                "is a MAJOR security risk. This allows ANY domain to make authenticated requests "
                "to your API. Please specify explicit origins for production."
            )

    def __init__(self, **data):
        # Load from environment variables
        cs_user = os.getenv("CS_USER", "code_sandbox")
        
        env_data = {
            # Application
            "app_name": os.getenv("APP_NAME", "CodeSandbox"),
            "app_version": os.getenv("APP_VERSION", "1.0.0"), 
            "environment": os.getenv("ENVIRONMENT", "development"),
            "debug": os.getenv("DEBUG", "true").lower() == "true",
            
            # User
            "cs_user": cs_user,
            
            # Server
            "host": os.getenv("HOST", "127.0.0.1"),
            "port": int(os.getenv("PORT", "8080")),
            "workers": int(os.getenv("WORKERS", "1")),
            
            # CORS
            "cors_origins": self._parse_cors_origins(os.getenv("CORS_ORIGINS", "*")),
            "cors_allow_credentials": os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true",
            
            # Jupyter
            "jupyter_host": os.getenv("JUPYTER_HOST", "127.0.0.1"),
            "jupyter_port": int(os.getenv("JUPYTER_PORT", "8888")),
            "jupyter_token": os.getenv("JUPYTER_TOKEN", ""),
            "jupyter_password": os.getenv("JUPYTER_PASSWORD", ""),
            
            # Workspace - using user temp base path structure
            "user_temp_base_path": os.getenv("USER_TEMP_BASE_PATH", f"/tmp/{cs_user}"),
            "workspace_default_ttl_hours": int(os.getenv("WORKSPACE_DEFAULT_TTL_HOURS", "2")),
            "workspace_max_ttl_hours": int(os.getenv("WORKSPACE_MAX_TTL_HOURS", "24")),
            "workspace_cleanup_interval_minutes": int(os.getenv("WORKSPACE_CLEANUP_INTERVAL_MINUTES", "15")),
            
            # Files
            "max_file_size_mb": int(os.getenv("MAX_FILE_SIZE_MB", "100")),
            "max_files_per_workspace": int(os.getenv("MAX_FILES_PER_WORKSPACE", "50")),
            "max_workspace_size_mb": int(os.getenv("MAX_WORKSPACE_SIZE_MB", "500")),
            
            # Execution
            "default_execution_timeout": int(os.getenv("DEFAULT_EXECUTION_TIMEOUT", "30")),
            "max_execution_timeout": int(os.getenv("MAX_EXECUTION_TIMEOUT", "300")),
            "blocked_imports": os.getenv("BLOCKED_IMPORTS", "").split(",") if os.getenv("BLOCKED_IMPORTS") else [],
            
            # Logging
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "log_format": os.getenv("LOG_FORMAT", "json"),
            "log_file": os.getenv("LOG_FILE"),
        }
        
        # Merge with provided data (provided data takes precedence)
        env_data.update(data)
        super().__init__(**env_data)
        
        # Validate configuration for security issues
        self._validate_cors_security()
    
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
    
    def get_jupyter_command_args(self) -> List[str]:
        """Generate Jupyter server command arguments from settings"""
        cmd = [
            "jupyter", "server",
            f"--ip={self.jupyter_host}",
            f"--port={self.jupyter_port}",
            "--no-browser"
        ]
        
        # Add authentication if provided
        if self.jupyter_token:
            cmd.append(f"--ServerApp.token={self.jupyter_token}")
            
        if self.jupyter_password:
            cmd.append(f"--ServerApp.password={self.jupyter_password}")
        
        # Add CORS origins
        for origin in self.cors_origins:
            cmd.append(f"--ServerApp.allow_origin={origin}")
            
        # Add other server settings
        cmd.append("--ServerApp.allow_remote_access=True")
        
        return cmd
    
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