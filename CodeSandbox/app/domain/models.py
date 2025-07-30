#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Domain Models for CodeSandbox

Core business entities representing workspaces, code execution, and file management.
These models are framework-agnostic and represent the business domain.
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid


class WorkspaceStatus(str, Enum):
    """Workspace lifecycle states"""
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    EXPIRED = "expired"


class ExecutionStatus(str, Enum):
    """Code execution states"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class FileOperationType(str, Enum):
    """File operation types"""
    UPLOAD = "upload"
    DOWNLOAD = "download"
    LIST = "list"
    DELETE = "delete"


class FileInfo(BaseModel):
    """Information about a file in workspace"""
    filename: str
    size: int = Field(..., ge=0)
    mime_type: str = "application/octet-stream"
    created_at: datetime
    relative_path: str = Field(..., description="Path relative to workspace root")
    download_url: Optional[str] = None


class WorkspaceInfo(BaseModel):
    """Workspace information and metadata"""
    workspace_id: str = Field(..., min_length=1)
    kernel_id: Optional[str] = None
    status: WorkspaceStatus = WorkspaceStatus.INITIALIZING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    
    # Resource tracking
    files_count: int = Field(0, ge=0)
    total_size_bytes: int = Field(0, ge=0)


class ExecutionRequest(BaseModel):
    """Request for code execution"""
    workspace_id: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1, description="Python code to execute")
    timeout: int = Field(30, ge=1, le=300, description="Execution timeout in seconds")


class FileRequest(BaseModel):
    """Request for file operations"""
    workspace_id: str = Field(..., min_length=1)
    filename: str = Field(..., min_length=1, description="Target filename")
    operation: FileOperationType
    content_size: Optional[int] = Field(None, ge=0, description="File size for resource planning")
    timeout: int = Field(60, ge=1, le=600, description="File operation timeout in seconds")
    content: Optional[bytes] = Field(None, description="File content for upload operations")


class ExecutionOutput(BaseModel):
    """Output from code execution"""
    type: str = Field(..., description="Output type: stdout, stderr, display_data, etc.")
    content: Union[str, Dict[str, Any]] = Field(..., description="Output content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExecutionResult(BaseModel):
    """Result of code execution"""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str
    status: ExecutionStatus
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Output streams
    stdout: str = ""
    stderr: str = ""
    
    # Structured outputs
    outputs: List[ExecutionOutput] = Field(default_factory=list)
    
    # Result data (if code sets 'result' variable)
    result_data: Optional[Any] = None
    
    # Generated files
    generated_files: List[FileInfo] = Field(default_factory=list)
    
    # Execution metadata
    execution_time_ms: Optional[int] = None
    exit_code: Optional[int] = None


class WorkspaceCreateRequest(BaseModel):
    """Request to create a new workspace"""
    workspace_id: Optional[str] = Field(None, description="Optional workspace ID, auto-generated if not provided")
    ttl_hours: int = Field(2, ge=1, le=24, description="Time-to-live in hours")
    
    @validator('workspace_id')
    def validate_workspace_id(cls, v):
        if v and not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Workspace ID must be alphanumeric with optional hyphens/underscores')
        return v


class WorkspaceFilesResponse(BaseModel):
    """Response for workspace files listing"""
    workspace_id: str
    files: List[FileInfo] = Field(default_factory=list)
    total_files: int = Field(0, ge=0)
    total_size_bytes: int = Field(0, ge=0)


class HealthCheck(BaseModel):
    """Health check response"""
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    jupyter_server_status: Optional[str] = None
    active_workspaces: int = 0 