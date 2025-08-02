#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File Models - Exact Server Response Models

These models match the CodeSandbox server responses exactly.
DO NOT modify these without checking the server code first!
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class FileInfo(BaseModel):
    """File information - HTTP response format"""
    filename: str
    size: int = Field(..., ge=0)
    mime_type: str = "application/octet-stream"
    relative_path: str = Field(..., description="Path relative to workspace root")
    download_url: Optional[str] = None  # Server sets this in API layer


class WorkspaceFilesResponse(BaseModel):
    """Response for workspace files listing - matches server"""
    workspace_id: str
    files: List[FileInfo] = Field(default_factory=list)
    total_files: int = Field(0, ge=0)
    total_size_bytes: int = Field(0, ge=0)


# Result wrapper models for client responses
class FileUploadResult(BaseModel):
    """Result of file upload operation"""
    success: bool
    file_info: Optional[FileInfo] = None
    error: Optional[str] = None
    
    @classmethod
    def success_result(cls, file_info: FileInfo) -> "FileUploadResult":
        """Create a successful result"""
        return cls(success=True, file_info=file_info)
    
    @classmethod
    def error_result(cls, error: str) -> "FileUploadResult":
        """Create an error result"""
        return cls(success=False, error=error)


class FileDownloadResult(BaseModel):
    """Result of file download operation"""
    success: bool
    filename: Optional[str] = None
    content: Optional[bytes] = None  # Raw bytes content
    content_text: Optional[str] = None  # Text content if decodable
    size: Optional[int] = None
    mime_type: Optional[str] = None
    error: Optional[str] = None
    
    @classmethod
    def success_result(cls, filename: str, content: bytes, mime_type: str = None) -> "FileDownloadResult":
        """Create a successful result"""
        content_text = None
        try:
            # Try to decode as text
            content_text = content.decode('utf-8')
        except UnicodeDecodeError:
            pass  # Binary file, leave content_text as None
            
        return cls(
            success=True,
            filename=filename,
            content=content,
            content_text=content_text,
            size=len(content),
            mime_type=mime_type
        )
    
    @classmethod
    def error_result(cls, error: str) -> "FileDownloadResult":
        """Create an error result"""
        return cls(success=False, error=error)


class FileListResult(BaseModel):
    """Result of file listing operation"""
    success: bool
    files: List[FileInfo] = Field(default_factory=list)
    total_files: int = 0
    total_size_bytes: int = 0
    error: Optional[str] = None
    
    @classmethod
    def success_result(cls, files: List[FileInfo]) -> "FileListResult":
        """Create a successful result"""
        total_size = sum(f.size for f in files)
        return cls(
            success=True,
            files=files,
            total_files=len(files),
            total_size_bytes=total_size
        )
    
    @classmethod
    def error_result(cls, error: str) -> "FileListResult":
        """Create an error result"""
        return cls(success=False, error=error) 