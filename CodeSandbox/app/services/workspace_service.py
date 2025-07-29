#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Workspace Service

High-level business logic for workspace management.
Orchestrates Jupyter client operations and manages workspace lifecycle.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from app.core.config import Settings
from app.domain.models import (
    WorkspaceInfo, WorkspaceStatus, WorkspaceCreateRequest,
    FileInfo, WorkspaceFilesResponse
)
from app.infrastructure.jupyter_kernel_client import (
    JupyterServerClient, JupyterClientError, WorkspaceNotFoundError
)
from app.core.events import get_event_bus, WorkspaceDeletedEvent
from app.utils.logger import Loggers


class WorkspaceService:
    """
    Service for managing workspace lifecycle
    
    Handles workspace creation, file management, and cleanup operations.
    Coordinates between the domain models and Jupyter infrastructure.
    """
    
    def __init__(self, settings: Settings, jupyter_client: JupyterServerClient):
        self.settings = settings
        self.jupyter_client = jupyter_client
        self.logger = Loggers.workspace_service
        
        # Track active workspaces
        self._workspaces: Dict[str, WorkspaceInfo] = {}
        
        # NOTE: Cleanup now handled by centralized CleanupService
        # (removed individual cleanup task)
        
        # Event bus for clean service communication
        self.event_bus = get_event_bus()
        
        self.logger.info("Workspace service initialized",
                        cleanup_interval_minutes=settings.workspace_cleanup_interval_minutes,
                        max_ttl_hours=settings.workspace_max_ttl_hours)
    
    async def start(self):
        """Start the workspace service and background tasks"""
        # NOTE: Cleanup now handled by centralized CleanupService
        # (removed start/stop cleanup task methods)
    
    async def create_workspace(self, request: WorkspaceCreateRequest) -> WorkspaceInfo:
        """
        Create a new workspace with Jupyter kernel
        
        Args:
            request: Workspace creation request
            
        Returns:
            WorkspaceInfo: Created workspace information
            
        Raises:
            JupyterClientError: If workspace creation fails
        """
        # Generate workspace ID if not provided
        workspace_id = request.workspace_id or f"ws_{uuid.uuid4().hex[:8]}"
        
        self.logger.info("Creating workspace", 
                        workspace_id=workspace_id, 
                        ttl_hours=request.ttl_hours)
        
        # Validate workspace ID uniqueness
        if workspace_id in self._workspaces:
            existing = self._workspaces[workspace_id]
            if existing.status != WorkspaceStatus.EXPIRED:
                # Return existing active workspace
                self.logger.info("Returning existing workspace",
                               workspace_id=workspace_id,
                               status=existing.status)
                return existing
        
        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(hours=request.ttl_hours)
        
        # Initialize workspace info
        workspace_info = WorkspaceInfo(
            workspace_id=workspace_id,
            status=WorkspaceStatus.INITIALIZING,
            expires_at=expires_at,
            files_count=0,
            total_size_bytes=0
        )
        
        # Store workspace info
        self._workspaces[workspace_id] = workspace_info
        
        try:
            # Create workspace directory in Jupyter
            self.logger.debug("Creating workspace directory", workspace_id=workspace_id)
            await self.jupyter_client.create_workspace_directory(workspace_id)
            
            # Create and initialize kernel
            self.logger.debug("Creating Jupyter kernel", workspace_id=workspace_id)
            kernel_result = await self.jupyter_client.create_kernel(workspace_id)
            
            # Update workspace info
            workspace_info.kernel_id = kernel_result["kernel_id"]
            workspace_info.status = WorkspaceStatus.READY
            workspace_info.last_activity = datetime.utcnow()
            
            self.logger.info("Workspace created successfully",
                           workspace_id=workspace_id,
                           kernel_id=kernel_result["kernel_id"],
                           expires_at=workspace_info.expires_at.isoformat(),
                           active_count=len(self._workspaces))
            
            return workspace_info
            
        except Exception as e:
            # Mark workspace as error
            workspace_info.status = WorkspaceStatus.ERROR
            
            self.logger.error("Workspace creation failed",
                            exc=e,
                            workspace_id=workspace_id,
                            ttl_hours=request.ttl_hours,
                            error_stage="jupyter_setup")
            
            raise JupyterClientError(f"Failed to create workspace: {e}")
    
    async def get_workspace(self, workspace_id: str) -> Optional[WorkspaceInfo]:
        """
        Get workspace information
        
        Args:
            workspace_id: Workspace identifier
            
        Returns:
            WorkspaceInfo if found, None otherwise
        """
        workspace_info = self._workspaces.get(workspace_id)
        
        if workspace_info and self._is_expired(workspace_info):
            # Mark as expired
            workspace_info.status = WorkspaceStatus.EXPIRED
            
        return workspace_info
    
    async def list_workspaces(self) -> List[WorkspaceInfo]:
        """
        List all active workspaces
        
        Returns:
            List of workspace information
        """
        workspaces = []
        for workspace_info in self._workspaces.values():
            if self._is_expired(workspace_info):
                workspace_info.status = WorkspaceStatus.EXPIRED
            workspaces.append(workspace_info)
        
        return workspaces
    
    async def delete_workspace(self, workspace_id: str, reason: str = "manual") -> bool:
        """
        Delete workspace and all its resources
        
        Args:
            workspace_id: Workspace to delete
            
        Returns:
            True if deleted, False if not found
        """
        if workspace_id not in self._workspaces:
            return False
        
        self.logger.info("Deleting workspace", workspace_id=workspace_id)
        
        try:
            # Delete kernel (this also deletes the entire workspace directory)
            await self.jupyter_client.delete_kernel(workspace_id)
            
            # Remove from memory tracking
            del self._workspaces[workspace_id]
            
            # ✅ CLEAN: Publish event for other services to handle
            await self.event_bus.publish(WorkspaceDeletedEvent(workspace_id, reason))
            
            self.logger.info("Workspace deleted successfully", workspace_id=workspace_id)
            return True
            
        except Exception as e:
            # Log error but still remove from tracking to prevent memory leaks
            self.logger.error("Error deleting workspace", workspace_id=workspace_id, error=str(e))
            if workspace_id in self._workspaces:
                del self._workspaces[workspace_id]
                
                # Still publish event even if deletion failed
                await self.event_bus.publish(WorkspaceDeletedEvent(workspace_id, f"failed_{reason}"))
            return True
    
    async def extend_workspace_ttl(self, workspace_id: str, additional_hours: int) -> Optional[WorkspaceInfo]:
        """
        Extend workspace TTL
        
        Args:
            workspace_id: Workspace to extend
            additional_hours: Hours to add to TTL
            
        Returns:
            Updated WorkspaceInfo or None if not found
        """
        workspace_info = self._workspaces.get(workspace_id)
        if not workspace_info:
            return None
        
        # Check maximum TTL limit
        current_ttl_hours = (workspace_info.expires_at - workspace_info.created_at).total_seconds() / 3600
        new_ttl_hours = current_ttl_hours + additional_hours
        
        if new_ttl_hours > self.settings.workspace_max_ttl_hours:
            raise ValueError(f"Maximum TTL of {self.settings.workspace_max_ttl_hours} hours exceeded")
        
        # Extend expiration
        workspace_info.expires_at += timedelta(hours=additional_hours)
        workspace_info.last_activity = datetime.utcnow()
        
        return workspace_info
    
    async def get_workspace_files(self, workspace_id: str) -> WorkspaceFilesResponse:
        """
        Get files in workspace
        
        Args:
            workspace_id: Workspace identifier
            
        Returns:
            WorkspaceFilesResponse with file list
            
        Raises:
            WorkspaceNotFoundError: If workspace not found
        """
        workspace_info = self._workspaces.get(workspace_id)
        if not workspace_info:
            raise WorkspaceNotFoundError(f"Workspace {workspace_id} not found")
        
        if workspace_info.status == WorkspaceStatus.EXPIRED:
            raise WorkspaceNotFoundError(f"Workspace {workspace_id} has expired")
        
        # Get files from Jupyter
        files = await self.jupyter_client._get_workspace_files(workspace_id)
        
        # Update workspace stats
        workspace_info.files_count = len(files)
        workspace_info.total_size_bytes = sum(f.size for f in files)
        workspace_info.last_activity = datetime.utcnow()
        
        return WorkspaceFilesResponse(
            workspace_id=workspace_id,
            files=files,
            total_files=len(files),
            total_size_bytes=sum(f.size for f in files)
        )
    
    async def update_workspace_activity(self, workspace_id: str):
        """Update workspace last activity timestamp"""
        if workspace_id in self._workspaces:
            self._workspaces[workspace_id].last_activity = datetime.utcnow()
    
    def _is_expired(self, workspace_info: WorkspaceInfo) -> bool:
        """Check if workspace has expired"""
        return datetime.utcnow() > workspace_info.expires_at
    
    # NOTE: _cleanup_loop removed - now handled by centralized CleanupService
    
    async def cleanup_expired_workspaces(self) -> int:
        """Clean up expired workspaces and return count"""
        try:
            now = datetime.utcnow()
            expired_workspace_ids = []
            
            # Find expired workspaces (thread-safe approach)
            try:
                for workspace_id, workspace_info in self._workspaces.items():
                    if now > workspace_info.expires_at:
                        expired_workspace_ids.append(workspace_id)
            except RuntimeError as e:
                # Handle "dictionary changed size during iteration"
                self.logger.warning("Dictionary changed during workspace cleanup iteration",
                                  error=str(e))
                # Retry with snapshot approach
                workspace_items = list(self._workspaces.items())
                for workspace_id, workspace_info in workspace_items:
                    if workspace_id in self._workspaces and now > workspace_info.expires_at:
                        expired_workspace_ids.append(workspace_id)
            
            if expired_workspace_ids:
                self.logger.info("Found expired workspaces for cleanup",
                               expired_count=len(expired_workspace_ids),
                               total_workspaces=len(self._workspaces))
            
            # Delete expired workspaces  
            cleaned_count = 0
            for workspace_id in expired_workspace_ids:
                try:
                    # Double-check workspace still exists and is expired
                    if workspace_id in self._workspaces and now > self._workspaces[workspace_id].expires_at:
                        # Delete the workspace with proper reason (will publish WorkspaceDeletedEvent)
                        success = await self.delete_workspace(workspace_id, reason="expired")
                        if success:
                            cleaned_count += 1
                        self.logger.debug("Cleaned up expired workspace", 
                                        workspace_id=workspace_id,
                                        success=success)
                    else:
                        self.logger.debug("Workspace already cleaned up or no longer expired",
                                        workspace_id=workspace_id)
                except Exception as e:
                    self.logger.error("Error cleaning up workspace", 
                                    exc=e, 
                                    workspace_id=workspace_id)
            
            if cleaned_count > 0:
                self.logger.info("Workspace cleanup completed",
                               cleaned_count=cleaned_count,
                               remaining_workspaces=len(self._workspaces))
            
            # Also cleanup idle kernels in Jupyter client (use consistent timeout)
            try:
                await self.jupyter_client.cleanup_expired_kernels(
                    max_idle_minutes=self.settings.workspace_idle_timeout_minutes
                )
            except Exception as e:
                self.logger.error("Error cleaning up Jupyter kernels", exc=e)
                
            return cleaned_count
            
        except Exception as e:
            self.logger.error("Error during workspace cleanup",
                            error=str(e),
                            exc=e)
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get workspace service statistics"""
        now = datetime.utcnow()
        active_count = 0
        expired_count = 0
        total_files = 0
        total_size = 0
        
        for workspace_info in self._workspaces.values():
            if now > workspace_info.expires_at:
                expired_count += 1
            else:
                active_count += 1
                total_files += workspace_info.files_count
                total_size += workspace_info.total_size_bytes
        
        return {
            "total_workspaces": len(self._workspaces),
            "active_workspaces": active_count,
            "expired_workspaces": expired_count,
            "total_files": total_files,
            "total_size_bytes": total_size,
            "active_kernels": len(self.jupyter_client.list_active_kernels())
        } 