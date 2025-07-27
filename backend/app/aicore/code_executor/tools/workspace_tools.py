#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Workspace Management Tools

Atomic function tools for workspace lifecycle management.
Thin wrappers around WorkspaceService for LLM tool usage.
"""

from agents import function_tool

from app.aicore.code_executor.models import (
    WorkspaceInfo,
    WorkspaceCreateResult,
    WorkspaceDeleteResult,
    WorkspaceTTLExtendResult
)
from app.aicore.code_executor.services import WorkspaceService

# Shared service instance
_workspace_service = WorkspaceService()


@function_tool(strict_mode=False)
async def create_workspace(ttl_hours: int = 2) -> WorkspaceCreateResult:
    """
    Create a new isolated workspace for code execution.
    
    Each workspace provides:
    - Fresh Python environment with Jupyter kernel
    - Isolated file system (inputs/ and outputs/ directories)
    - Configurable time-to-live (TTL)
    - Persistent state across multiple code executions
    
    Args:
        ttl_hours: Workspace lifetime in hours (default: 2, max: 24)
        
    Returns:
        WorkspaceCreateResult containing:
        - success: True if created successfully
        - workspace_info: WorkspaceInfo with details if successful
        - error: Error message if failed
        
    Example:
        result = await create_workspace(ttl_hours=4)
        if result.success:
            workspace_id = result.workspace_info.workspace_id
            print(f"Created workspace {workspace_id}, expires at {result.workspace_info.expires_at}")
        else:
            print(f"Failed to create workspace: {result.error}")
    """
    return await _workspace_service.create_workspace(ttl_hours)


@function_tool(strict_mode=False)
async def get_workspace(workspace_id: str) -> WorkspaceInfo:
    """
    Get information about an existing workspace.
    
    Args:
        workspace_id: Workspace identifier
        
    Returns:
        WorkspaceInfo containing workspace details
        
    Example:
        info = await get_workspace("ws_abc123")
        if info.status == "ready":
            print(f"Workspace ready, expires at {info.expires_at}")
    """
    return await _workspace_service.get_workspace(workspace_id)


@function_tool(strict_mode=False)
async def delete_workspace(workspace_id: str) -> WorkspaceDeleteResult:
    """
    Delete a workspace and clean up all its resources.
    
    This will:
    - Shut down the Jupyter kernel
    - Delete all workspace files
    - Remove the workspace from the system
    
    Args:
        workspace_id: Workspace to delete
        
    Returns:
        WorkspaceDeleteResult containing:
        - success: True if deleted successfully
        - workspace_id: The workspace ID
        - message: Success message if successful
        - error: Error message if failed
        
    Example:
        result = await delete_workspace("ws_abc123")
        if result.success:
            print(f"Workspace {result.workspace_id} deleted successfully")
        else:
            print(f"Failed to delete: {result.error}")
    """
    return await _workspace_service.delete_workspace(workspace_id)


@function_tool(strict_mode=False)
async def extend_workspace_ttl(workspace_id: str, additional_hours: int) -> WorkspaceTTLExtendResult:
    """
    Extend the time-to-live (TTL) of a workspace.
    
    Useful when you need more time to complete work in a workspace.
    The total TTL cannot exceed the system maximum (typically 24 hours).
    
    Args:
        workspace_id: Workspace to extend
        additional_hours: Hours to add to the current TTL
        
    Returns:
        WorkspaceTTLExtendResult containing:
        - success: True if extended successfully
        - workspace_id: The workspace ID
        - new_expires_at: New expiration timestamp if successful
        - message: Success message if successful
        - error: Error message if failed
        
    Example:
        result = await extend_workspace_ttl("ws_abc123", 2)
        if result.success:
            print(f"Workspace extended until {result.new_expires_at}")
        else:
            print(f"Failed to extend: {result.error}")
    """
    return await _workspace_service.extend_workspace_ttl(workspace_id, additional_hours) 