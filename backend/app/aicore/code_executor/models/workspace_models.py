#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Workspace Models - Exact Server Response Models

These models match the CodeSandbox server responses exactly.
DO NOT modify these without checking the server code first!
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class WorkspaceStatus(str, Enum):
    """Workspace status enum - matches server"""
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    EXPIRED = "expired"


class WorkspaceInfo(BaseModel):
    """Workspace information - HTTP response format"""
    workspace_id: str = Field(..., min_length=1)
    kernel_id: Optional[str] = None
    status: str  # Server returns enum as string in HTTP response
    created_at: str  # Server returns datetime as ISO string in HTTP response
    expires_at: str  # Server returns datetime as ISO string in HTTP response
    last_activity: str  # Server returns datetime as ISO string in HTTP response
    
    # Resource tracking
    files_count: int = Field(0, ge=0)
    total_size_bytes: int = Field(0, ge=0)


class WorkspaceCreateRequest(BaseModel):
    """Request to create a new workspace - matches server"""
    workspace_id: Optional[str] = Field(None, description="Optional workspace ID, auto-generated if not provided")
    ttl_hours: int = Field(2, ge=1, le=24, description="Time-to-live in hours")


class HealthCheck(BaseModel):
    """Health check response - matches server"""
    status: str
    jupyter_server_status: str = "unknown"
    active_workspaces: int = 0


class HealthCheckResult(BaseModel):
    """Result of health check operation"""
    success: bool
    health_check: Optional[HealthCheck] = None
    system_healthy: bool = False
    codesandbox_server: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    @classmethod
    def success_result(cls, health_check: HealthCheck, codesandbox_details: Dict[str, Any]) -> "HealthCheckResult":
        """Create a successful health check result"""
        return cls(
            success=True,
            health_check=health_check,
            system_healthy=health_check.status == "healthy",
            codesandbox_server=codesandbox_details
        )
    
    @classmethod
    def error_result(cls, error: str, codesandbox_details: Optional[Dict[str, Any]] = None) -> "HealthCheckResult":
        """Create an error health check result"""
        return cls(
            success=False,
            system_healthy=False,
            error=error,
            codesandbox_server=codesandbox_details
        )


class SystemStatsResult(BaseModel):
    """Result of system stats operation"""
    success: bool
    stats: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    @classmethod
    def success_result(cls, stats: Dict[str, Any]) -> "SystemStatsResult":
        """Create a successful result"""
        return cls(success=True, stats=stats)
    
    @classmethod
    def error_result(cls, error: str) -> "SystemStatsResult":
        """Create an error result"""
        return cls(success=False, error=error)


class SystemConfigResult(BaseModel):
    """Result of system config operation"""
    success: bool
    config: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    @classmethod
    def success_result(cls, config: Dict[str, Any]) -> "SystemConfigResult":
        """Create a successful result"""
        return cls(success=True, config=config)
    
    @classmethod
    def error_result(cls, error: str) -> "SystemConfigResult":
        """Create an error result"""
        return cls(success=False, error=error)


# Result wrapper models for client responses
class WorkspaceGetResult(BaseModel):
    """Result of get workspace operation"""
    success: bool
    workspace_info: Optional[WorkspaceInfo] = None
    error: Optional[str] = None
    
    @classmethod
    def success_result(cls, workspace_info: WorkspaceInfo) -> "WorkspaceGetResult":
        """Create a successful result"""
        return cls(success=True, workspace_info=workspace_info)
    
    @classmethod
    def error_result(cls, error: str) -> "WorkspaceGetResult":
        """Create an error result"""
        return cls(success=False, error=error)


class WorkspaceCreateResult(BaseModel):
    """Result of workspace creation operation"""
    success: bool
    workspace_info: Optional[WorkspaceInfo] = None
    error: Optional[str] = None
    
    @classmethod
    def success_result(cls, workspace_info: WorkspaceInfo) -> "WorkspaceCreateResult":
        """Create a successful result"""
        return cls(success=True, workspace_info=workspace_info)
    
    @classmethod
    def error_result(cls, error: str) -> "WorkspaceCreateResult":
        """Create an error result"""
        return cls(success=False, error=error)


class WorkspaceDeleteResult(BaseModel):
    """Result of workspace deletion operation"""
    success: bool
    workspace_id: str
    message: Optional[str] = None
    error: Optional[str] = None
    
    @classmethod
    def success_result(cls, workspace_id: str, message: str = "Workspace deleted successfully") -> "WorkspaceDeleteResult":
        """Create a successful result"""
        return cls(success=True, workspace_id=workspace_id, message=message)
    
    @classmethod
    def error_result(cls, workspace_id: str, error: str) -> "WorkspaceDeleteResult":
        """Create an error result"""
        return cls(success=False, workspace_id=workspace_id, error=error)


class WorkspaceTTLExtendResult(BaseModel):
    """Result of workspace TTL extension operation"""
    success: bool
    workspace_info: Optional[WorkspaceInfo] = None
    error: Optional[str] = None
    
    @classmethod
    def success_result(cls, workspace_info: WorkspaceInfo) -> "WorkspaceTTLExtendResult":
        """Create a successful result"""
        return cls(success=True, workspace_info=workspace_info)
    
    @classmethod
    def error_result(cls, error: str) -> "WorkspaceTTLExtendResult":
        """Create an error result"""
        return cls(success=False, error=error) 