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
from app.infrastructure.jupyter_kernel_client import (
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
                        file_name=filename,  # Renamed to avoid LogRecord conflict
                        file_size_bytes=len(content))
        
        # Validate workspace exists and is ready
        workspace_info = await self.workspace_service.get_workspace(workspace_id)
        if not workspace_info:
            self.logger.warning("File upload failed - workspace not found",
                              workspace_id=workspace_id,
                              file_name=filename)  # Renamed to avoid LogRecord conflict
            raise WorkspaceNotFoundError(f"Workspace {workspace_id} not found")
        
        if workspace_info.status == WorkspaceStatus.EXPIRED:
            self.logger.warning("File upload failed - workspace expired",
                              workspace_id=workspace_id,
                              file_name=filename,
                              status=workspace_info.status)
            raise WorkspaceNotFoundError(f"Workspace {workspace_id} has expired")
        
        # Validate file
        self._validate_file(filename, content)
        
        # Upload to workspace via Jupyter
        self.logger.debug("Uploading file to Jupyter workspace",
                         workspace_id=workspace_id,
                         file_name=filename)  # Renamed to avoid LogRecord conflict
        
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
                           file_name=filename,  # Renamed to avoid LogRecord conflict
                           file_size_bytes=len(content))
            
            return file_info
            
        except Exception as e:
            self.logger.error("File upload failed",
                            exc=e,
                            workspace_id=workspace_id,
                            file_name=filename,  # Renamed to avoid LogRecord conflict
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
    
    async def download_file(self, workspace_id: str, filename: str) -> tuple[bytes, FileInfo]:
        """
        Download file from workspace
        
        Args:
            workspace_id: Workspace identifier
            filename: Name of file to download (can include subdirectories)
            
        Returns:
            Tuple of (file_content, file_info)
            
        Raises:
            WorkspaceNotFoundError: If workspace doesn't exist
            FileNotFoundError: If file doesn't exist
            FileServiceError: If download fails
        """
        self.logger.info("File download requested",
                        workspace_id=workspace_id,
                        file_name=filename)
        
        # Validate workspace exists and is ready
        workspace_info = await self.workspace_service.get_workspace(workspace_id)
        if not workspace_info:
            self.logger.warning("File download failed - workspace not found",
                              workspace_id=workspace_id,
                              file_name=filename)
            raise WorkspaceNotFoundError(f"Workspace {workspace_id} not found")
        
        if workspace_info.status == WorkspaceStatus.EXPIRED:
            self.logger.warning("File download failed - workspace expired",
                              workspace_id=workspace_id,
                              file_name=filename,
                              status=workspace_info.status)
            raise WorkspaceNotFoundError(f"Workspace {workspace_id} has expired")
        
        try:
            # Get the workspace path from jupyter client
            workspace_path = Path(self.settings.workspace_base_path) / workspace_id
            file_path = workspace_path / filename
            
            # Security check: ensure file is within workspace
            resolved_file_path = file_path.resolve()
            resolved_workspace_path = workspace_path.resolve()
            
            if not str(resolved_file_path).startswith(str(resolved_workspace_path)):
                raise FileServiceError(f"Access denied: {filename} is outside workspace")
            
            # Check if file exists
            if not file_path.exists() or not file_path.is_file():
                self.logger.warning("File download failed - file not found",
                                  workspace_id=workspace_id,
                                  file_name=filename,
                                  file_path=str(file_path))
                raise FileNotFoundError(f"File {filename} not found in workspace {workspace_id}")
            
            # Read file content
            file_content = file_path.read_bytes()
            
            # Create FileInfo without download_url (generated at API layer)
            file_info = FileInfo(
                filename=file_path.name,
                size=len(file_content),
                mime_type=self._get_mime_type(filename),
                created_at=datetime.fromtimestamp(file_path.stat().st_ctime),
                relative_path=filename,
                download_url=""  # Generated at API layer
            )
            
            # Update workspace activity
            await self.workspace_service.update_workspace_activity(workspace_id)
            
            self.logger.info("File downloaded successfully",
                           workspace_id=workspace_id,
                           file_name=filename,
                           file_size_bytes=len(file_content))
            
            return file_content, file_info
            
        except FileNotFoundError:
            # Re-raise as is
            raise
        except FileServiceError:
            # Re-raise as is
            raise
        except Exception as e:
            self.logger.error("File download failed",
                            exc=e,
                            workspace_id=workspace_id,
                            file_name=filename,
                            error_type=e.__class__.__name__)
            raise FileServiceError(f"Failed to download file {filename}: {e}")
    
    def _get_mime_type(self, filename: str) -> str:
        """
        Get MIME type for file based on extension
        
        Args:
            filename: File name
            
        Returns:
            MIME type string
        """
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or "application/octet-stream"
    
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
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get file service statistics
        
        Returns:
            Dictionary with file service stats
        """
        return {
            "max_file_size_mb": self.settings.max_file_size_mb,
            "max_workspace_size_mb": self.settings.max_workspace_size_mb,
            "operations": ["upload", "list", "download"]
        } 