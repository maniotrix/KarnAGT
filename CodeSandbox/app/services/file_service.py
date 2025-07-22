#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File Service

Simple file management for workspaces.
Only handles direct file uploads and downloads - no staging bullshit.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from app.core.config import Settings
from app.domain.models import (
    FileInfo, WorkspaceStatus
)
from app.infrastructure.jupyter_client import (
    JupyterServerClient, WorkspaceNotFoundError
)
from app.services.workspace_service import WorkspaceService
from app.utils.logger import Loggers


class FileServiceError(Exception):
    """Base exception for file service errors"""
    pass


class FileService:
    """
    Simple file management service
    
    Handles direct file uploads/downloads to workspaces.
    No network access, no staging - just simple file operations.
    """
    
    def __init__(
        self,
        settings: Settings,
        jupyter_client: JupyterServerClient,
        workspace_service: WorkspaceService
    ):
        self.settings = settings
        self.jupyter_client = jupyter_client
        self.workspace_service = workspace_service
        self.logger = Loggers.file_service
        
        self.logger.info("File service initialized",
                        max_file_size_mb=settings.max_file_size_mb,
                        max_files_per_workspace=settings.max_files_per_workspace)
    
    async def upload_file(
        self, 
        workspace_id: str, 
        filename: str, 
        content: bytes
    ) -> FileInfo:
        """
        Upload file directly to workspace
        
        Args:
            workspace_id: Target workspace
            filename: Target filename
            content: File content as bytes
            
        Returns:
            FileInfo for uploaded file
            
        Raises:
            WorkspaceNotFoundError: If workspace doesn't exist
            FileServiceError: If upload fails
        """
        self.logger.info("File upload requested",
                        workspace_id=workspace_id,
                        filename=filename,
                        file_size_bytes=len(content))
        
        # Validate workspace exists and is ready
        workspace_info = await self.workspace_service.get_workspace(workspace_id)
        if not workspace_info:
            self.logger.warning("File upload failed - workspace not found",
                              workspace_id=workspace_id,
                              filename=filename)
            raise WorkspaceNotFoundError(f"Workspace {workspace_id} not found")
        
        if workspace_info.status == WorkspaceStatus.EXPIRED:
            self.logger.warning("File upload failed - workspace expired",
                              workspace_id=workspace_id,
                              filename=filename,
                              status=workspace_info.status)
            raise WorkspaceNotFoundError(f"Workspace {workspace_id} has expired")
        
        # Validate file
        self._validate_file(filename, content)
        
        # Upload to workspace via Jupyter
        self.logger.debug("Uploading file to Jupyter workspace",
                         workspace_id=workspace_id,
                         filename=filename)
        
        try:
            file_info = await self.jupyter_client.upload_file_to_workspace(
                workspace_id=workspace_id,
                filename=filename,
                content=content
            )
            
            # Update workspace activity
            await self.workspace_service.update_workspace_activity(workspace_id)
            
            self.logger.info("File uploaded successfully",
                           workspace_id=workspace_id,
                           filename=filename,
                           file_size_bytes=len(content))
            
            return file_info
            
        except Exception as e:
            self.logger.error("File upload failed",
                            exc=e,
                            workspace_id=workspace_id,
                            filename=filename,
                            file_size_bytes=len(content),
                            error_type=e.__class__.__name__)
            raise FileServiceError(f"Failed to upload file {filename}: {e}")
    
    async def list_files(self, workspace_id: str) -> List[FileInfo]:
        """
        List files in workspace
        
        Args:
            workspace_id: Workspace identifier
            
        Returns:
            List of files in workspace
            
        Raises:
            WorkspaceNotFoundError: If workspace doesn't exist
        """
        self.logger.debug("Listing files in workspace", workspace_id=workspace_id)
        
        # Validate workspace exists
        workspace_info = await self.workspace_service.get_workspace(workspace_id)
        if not workspace_info:
            self.logger.warning("List files failed - workspace not found",
                              workspace_id=workspace_id)
            raise WorkspaceNotFoundError(f"Workspace {workspace_id} not found")
        
        if workspace_info.status == WorkspaceStatus.EXPIRED:
            self.logger.warning("List files failed - workspace expired",
                              workspace_id=workspace_id,
                              status=workspace_info.status)
            raise WorkspaceNotFoundError(f"Workspace {workspace_id} has expired")
        
        # Get files from Jupyter
        files = await self.jupyter_client._get_workspace_files(workspace_id)
        
        # Update workspace activity
        await self.workspace_service.update_workspace_activity(workspace_id)
        
        self.logger.info("Files listed successfully",
                       workspace_id=workspace_id,
                       file_count=len(files),
                       total_size_bytes=sum(f.size for f in files) if files else 0)
        
        return files
    
    def _validate_file(self, filename: str, content: bytes):
        """
        Validate file for upload
        
        Args:
            filename: File name
            content: File content
            
        Raises:
            FileServiceError: If validation fails
        """
        # Check filename
        if not filename or filename.startswith('.') or '/' in filename or '\\' in filename:
            raise FileServiceError("Invalid filename - no paths or hidden files allowed")
        
        # Check file size
        if len(content) > self.settings.max_file_size_bytes:
            raise FileServiceError(f"File too large ({len(content)} bytes, max {self.settings.max_file_size_mb}MB)")
        
        # Check file extension if configured
        if self.settings.allowed_file_extensions:
            file_ext = Path(filename).suffix.lower()
            if file_ext and file_ext not in self.settings.allowed_file_extensions:
                raise FileServiceError(f"File extension {file_ext} not allowed")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get file service statistics
        
        Returns:
            Dictionary with file service stats
        """
        return {
            "max_file_size_mb": self.settings.max_file_size_mb,
            "max_workspace_size_mb": self.settings.max_workspace_size_mb,
            "allowed_extensions": self.settings.allowed_file_extensions,
            "operations": ["upload", "list", "download"]
        } 