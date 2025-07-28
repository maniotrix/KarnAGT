#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Code Executor Server Configuration

Centralized configuration for CodeSandbox server connection and URL construction.
This allows services to construct proper download URLs without the client knowing about it.

Industry Standard Approach:
- Client: Pure HTTP communication, matches server responses exactly
- Config: Centralized server configuration and URL construction logic
- Services: Business logic layer that uses config to construct full URLs
"""

import os
from typing import Optional, List, Union
from pydantic import BaseModel, Field, validator
from urllib.parse import urljoin, urlparse


class CodeExecutorServerConfig(BaseModel):
    """
    Configuration for CodeSandbox server connection and URL construction.
    
    This class handles:
    - Server connection details
    - URL construction logic for download links
    - Environment-aware configuration
    """
    
    # Server connection settings
    base_url: str = Field(
        default_factory=lambda: os.getenv("CODESANDBOX_URL", "http://localhost:8080/api/v1"),
        description="Base URL of the CodeSandbox API server"
    )
    
    timeout: int = Field(
        default_factory=lambda: int(os.getenv("CODESANDBOX_TIMEOUT", "60")),
        description="Default timeout for requests in seconds"
    )
    
    max_retries: int = Field(
        default_factory=lambda: int(os.getenv("CODESANDBOX_MAX_RETRIES", "3")),
        description="Maximum number of retry attempts"
    )
    
    # URL construction settings
    public_base_url: Optional[str] = Field(
        default_factory=lambda: os.getenv("CODESANDBOX_PUBLIC_URL", None),
        description="Public base URL for download links (if different from base_url, e.g., behind CDN)"
    )
    
    @validator('base_url', 'public_base_url')
    def validate_url_format(cls, v):
        """Ensure URLs are properly formatted"""
        if v is None:
            return v
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v.rstrip('/')
    
    @property
    def download_base_url(self) -> str:
        """
        Get the base URL to use for constructing download URLs.
        
        Uses public_base_url if set (for CDN/proxy scenarios),
        otherwise falls back to base_url.
        """
        return self.public_base_url or self.base_url
    
    def construct_download_url(self, workspace_id: str, relative_path: str) -> str:
        """
        Construct full download URL from workspace ID and relative path.
        
        Args:
            workspace_id: Workspace identifier
            relative_path: File path relative to workspace root
            
        Returns:
            Full HTTP URL for downloading the file
            
        Examples:
            >>> config = CodeExecutorServerConfig()
            >>> config.construct_download_url("ws_123", "plot.png")
            "http://localhost:8080/api/v1/workspace/ws_123/files/plot.png"
            
            >>> config.construct_download_url("ws_123", "outputs/data.csv")
            "http://localhost:8080/api/v1/workspace/ws_123/files/outputs/data.csv"
        """
        # Ensure relative_path doesn't start with '/'
        clean_path = relative_path.lstrip('/')
        
        # Construct the full URL path
        url_path = f"/workspace/{workspace_id}/files/{clean_path}"
        
        # Join with base URL
        return urljoin(self.download_base_url + '/', url_path.lstrip('/'))
    
    def is_same_server(self, url: str) -> bool:
        """
        Check if a URL belongs to the same server as this configuration.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL is from the same server
        """
        try:
            parsed_url = urlparse(url)
            parsed_base = urlparse(self.base_url)
            return (parsed_url.scheme == parsed_base.scheme and 
                    parsed_url.netloc == parsed_base.netloc)
        except Exception:
            return False


# Global configuration instance
# Services can import this and use it directly
_server_config: Optional[CodeExecutorServerConfig] = None


def get_server_config() -> CodeExecutorServerConfig:
    """
    Get the global server configuration instance.
    
    Returns:
        CodeExecutorServerConfig instance
        
    Usage:
        from app.aicore.code_executor.config import get_server_config
        
        config = get_server_config()
        download_url = config.construct_download_url("ws_123", "plot.png")
    """
    global _server_config
    if _server_config is None:
        _server_config = CodeExecutorServerConfig()
    return _server_config


def reset_server_config():
    """Reset the global configuration (useful for testing)"""
    global _server_config
    _server_config = None


# Utility functions for services to enhance FileInfo objects with full URLs
def enhance_file_info_with_full_url(file_info, workspace_id: str):
    """
    Enhance a FileInfo object with full download URL.
    
    This modifies the file_info object in-place, replacing relative URLs with full URLs.
    
    Args:
        file_info: FileInfo object to enhance
        workspace_id: Workspace identifier for URL construction
        
    Usage:
        from app.aicore.code_executor.config import enhance_file_info_with_full_url
        
        # After getting file_info from client
        enhance_file_info_with_full_url(file_info, workspace_id)
        # Now file_info.download_url is a full HTTP URL
    """
    if hasattr(file_info, 'download_url') and hasattr(file_info, 'relative_path'):
        config = get_server_config()
        old_url = file_info.download_url
        new_url = config.construct_download_url(workspace_id, file_info.relative_path)
        file_info.download_url = new_url
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔗 Enhanced URL: {old_url} → {new_url} for file {file_info.filename}")


def enhance_file_list_with_full_urls(file_list: List, workspace_id: str):
    """
    Enhance a list of FileInfo objects with full download URLs.
    
    Args:
        file_list: List of FileInfo objects to enhance
        workspace_id: Workspace identifier for URL construction
        
    Usage:
        from app.aicore.code_executor.config import enhance_file_list_with_full_urls
        
        # After getting execution result from client
        enhance_file_list_with_full_urls(execution_result.generated_files, workspace_id)
        # Now all files have full HTTP URLs
    """
    for file_info in file_list:
        enhance_file_info_with_full_url(file_info, workspace_id)


def enhance_execution_result_with_full_urls(execution_result, workspace_id: str):
    """
    Enhance an ExecutionResult object with full download URLs for all generated files.
    
    Args:
        execution_result: ExecutionResult object to enhance
        workspace_id: Workspace identifier for URL construction
        
    Usage:
        from app.aicore.code_executor.config import enhance_execution_result_with_full_urls
        
        # After getting execution result from client
        enhance_execution_result_with_full_urls(execution_result, workspace_id)
        # Now all generated files have full HTTP URLs
    """
    if hasattr(execution_result, 'generated_files') and execution_result.generated_files:
        enhance_file_list_with_full_urls(execution_result.generated_files, workspace_id) 