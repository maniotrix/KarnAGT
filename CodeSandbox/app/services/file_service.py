#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File Service

Enhanced file management with concurrency controls for workspaces.
Uses 4-layer concurrency architecture for safe file operations.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from pathvalidate import validate_filename, ValidationError as PathValidationError, Platform

from app.core.config import Settings
from app.domain.models import (
    FileInfo, WorkspaceStatus, FileRequest, FileOperationType, WorkspaceFilesResponse
)
from app.infrastructure.jupyter_kernel_client import (
    JupyterServerClient, WorkspaceNotFoundError
)
from app.services.workspace_service import WorkspaceService
from app.core.concurrency import FileConcurrencyManager, FileServiceUnavailableError
from app.utils.logger import Loggers


class FileServiceError(Exception):
    """Base exception for file service errors"""
    pass


class FileService:
    """
    Enhanced file management service with concurrency controls
    
    Handles direct file uploads/downloads to workspaces with:
    - File-level locking (Layer 1)
    - Resource management (Layer 2) 
    - Admission control (Layer 3)
    - Circuit breaker (Layer 4)
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
        
        # Initialize file concurrency manager with 4-layer architecture
        self._file_concurrency_manager = FileConcurrencyManager(
            max_concurrent_file_operations=settings.max_concurrent_file_operations,
            max_concurrent_requests=settings.max_queued_file_requests,
            circuit_breaker_threshold=settings.file_circuit_breaker_threshold,
            circuit_recovery_timeout=settings.file_circuit_recovery_timeout,
            request_timeout_seconds=settings.file_timeout_seconds
        )
        
        self.logger.info("File service initialized with concurrency controls",
                        max_file_size_mb=settings.max_file_size_mb,
                        max_files_per_workspace=settings.max_files_per_workspace,
                        max_concurrent_file_ops=settings.max_concurrent_file_operations)
    
    async def upload_file(
        self, 
        workspace_id: str, 
        filename: str, 
        content: bytes
    ) -> FileInfo:
        """
        Upload file with full concurrency control
        
        Args:
            workspace_id: Target workspace
            filename: Target filename
            content: File content as bytes
            
        Returns:
            FileInfo for uploaded file
            
        Raises:
            WorkspaceNotFoundError: If workspace doesn't exist
            FileServiceError: If upload fails
            FileServiceUnavailableError: If system is overloaded
        """
        request = FileRequest(
            workspace_id=workspace_id,
            filename=filename,
            operation=FileOperationType.UPLOAD,
            content_size=len(content),
            timeout=self.settings.file_timeout_seconds,
            content=content
        )
        
        self.logger.info("File upload requested with concurrency control",
                        workspace_id=workspace_id,
                        file_name=filename,
                        file_size_bytes=len(content))
        
        try:
            return await self._file_concurrency_manager.execute_with_file_concurrency_control(
                request, 
                self._upload_file_locked
            )
        except FileServiceUnavailableError as e:
            self.logger.warning("File upload rejected due to system overload",
                              workspace_id=workspace_id,
                              file_name=filename,
                              reason=str(e))
            raise FileServiceError(f"File service temporarily unavailable: {e}")
    
    async def _upload_file_locked(self, request: FileRequest) -> FileInfo:
        """Execute file upload with all concurrency protections active"""
        
        # Validate workspace exists and is ready
        workspace_info = await self.workspace_service.get_workspace(request.workspace_id)
        if not workspace_info:
            self.logger.warning("File upload failed - workspace not found",
                              workspace_id=request.workspace_id,
                              file_name=request.filename)
            raise WorkspaceNotFoundError(f"Workspace {request.workspace_id} not found")
        
        if workspace_info.status == WorkspaceStatus.EXPIRED:
            self.logger.warning("File upload failed - workspace expired",
                              workspace_id=request.workspace_id,
                              file_name=request.filename,
                              status=workspace_info.status)
            raise WorkspaceNotFoundError(f"Workspace {request.workspace_id} has expired")
        
        # Validate file (protected by file lock)
        self._validate_file(request.filename, request.content)
        
        # Upload to workspace via Jupyter (protected by file lock)
        self.logger.debug("Uploading file to Jupyter workspace with file lock",
                         workspace_id=request.workspace_id,
                         file_name=request.filename)
        
        try:
            file_info = await self.jupyter_client.upload_file_to_workspace(
                workspace_id=request.workspace_id,
                filename=request.filename,
                content=request.content
            )
            
            # Update workspace activity
            await self.workspace_service.update_workspace_activity(request.workspace_id)
            
            self.logger.info("File uploaded successfully with concurrency control",
                           workspace_id=request.workspace_id,
                           file_name=request.filename,
                           file_size_bytes=len(request.content))
            
            return file_info
            
        except Exception as e:
            self.logger.error("File upload failed",
                            exc=e,
                            workspace_id=request.workspace_id,
                            file_name=request.filename,
                            file_size_bytes=len(request.content),
                            error_type=e.__class__.__name__)
            raise FileServiceError(f"Failed to upload file {request.filename}: {e}")
    
    async def list_files(self, workspace_id: str) -> WorkspaceFilesResponse:
        """
        List files with concurrency control
        
        Args:
            workspace_id: Workspace identifier
            
        Returns:
            WorkspaceFilesResponse with complete file information
            
        Raises:
            WorkspaceNotFoundError: If workspace doesn't exist
            FileServiceUnavailableError: If system is overloaded
        """
        request = FileRequest(
            workspace_id=workspace_id,
            filename="*",  # Special marker for list operation
            operation=FileOperationType.LIST,
            content_size=None,  # Not applicable for list operations
            timeout=self.settings.file_timeout_seconds,
            content=None  # Not applicable for list operations
        )
        
        self.logger.debug("File list requested with concurrency control",
                        workspace_id=workspace_id)
        
        try:
            return await self._file_concurrency_manager.execute_with_file_concurrency_control(
                request,
                self._list_files_locked
            )
        except FileServiceUnavailableError as e:
            self.logger.warning("File list rejected due to system overload",
                              workspace_id=workspace_id,
                              reason=str(e))
            raise FileServiceError(f"File service temporarily unavailable: {e}")
    
    async def _list_files_locked(self, request: FileRequest) -> WorkspaceFilesResponse:
        """Execute file listing with all concurrency protections active"""
        
        # Use WorkspaceService for proper layering and consistent validation
        # This ensures workspace validation, stats updates, and activity tracking
        try:
            workspace_files_response = await self.workspace_service.get_workspace_files(request.workspace_id)
            
            self.logger.info("Files listed successfully with concurrency control",
                           workspace_id=request.workspace_id,
                           file_count=workspace_files_response.total_files,
                           total_size_bytes=workspace_files_response.total_size_bytes)
            
            # Return the complete response (no need to extract and rebuild)
            return workspace_files_response
            
        except WorkspaceNotFoundError:
            # Re-raise WorkspaceNotFoundError as-is (already properly formatted)
            raise
    
    async def download_file(self, workspace_id: str, filename: str) -> Tuple[bytes, FileInfo]:
        """
        Download file with full concurrency control
        
        Args:
            workspace_id: Workspace identifier
            filename: Name of file to download (can include subdirectories)
            
        Returns:
            Tuple of (file_content, file_info)
            
        Raises:
            WorkspaceNotFoundError: If workspace doesn't exist
            FileNotFoundError: If file doesn't exist
            FileServiceError: If download fails
            FileServiceUnavailableError: If system is overloaded
        """
        request = FileRequest(
            workspace_id=workspace_id,
            filename=filename,
            operation=FileOperationType.DOWNLOAD,
            content_size=None,  # Not known until file is read
            timeout=self.settings.file_timeout_seconds,
            content=None  # Not applicable for download operations
        )
        
        self.logger.info("File download requested with concurrency control",
                        workspace_id=workspace_id,
                        file_name=filename)
        
        try:
            return await self._file_concurrency_manager.execute_with_file_concurrency_control(
                request,
                self._download_file_locked
            )
        except FileServiceUnavailableError as e:
            self.logger.warning("File download rejected due to system overload",
                              workspace_id=workspace_id,
                              file_name=filename,
                              reason=str(e))
            raise FileServiceError(f"File service temporarily unavailable: {e}")
    
    async def _download_file_locked(self, request: FileRequest) -> Tuple[bytes, FileInfo]:
        """Execute file download with all concurrency protections active"""
        
        # Validate workspace exists and is ready
        workspace_info = await self.workspace_service.get_workspace(request.workspace_id)
        if not workspace_info:
            self.logger.warning("File download failed - workspace not found",
                              workspace_id=request.workspace_id,
                              file_name=request.filename)
            raise WorkspaceNotFoundError(f"Workspace {request.workspace_id} not found")
        
        if workspace_info.status == WorkspaceStatus.EXPIRED:
            self.logger.warning("File download failed - workspace expired",
                              workspace_id=request.workspace_id,
                              file_name=request.filename,
                              status=workspace_info.status)
            raise WorkspaceNotFoundError(f"Workspace {request.workspace_id} has expired")
        
        try:
            # Get the workspace path from jupyter client
            workspace_path = Path(self.settings.workspace_base_path) / request.workspace_id
            file_path = workspace_path / request.filename
            
            # Security check: ensure file is within workspace
            resolved_file_path = file_path.resolve()
            resolved_workspace_path = workspace_path.resolve()
            
            if not str(resolved_file_path).startswith(str(resolved_workspace_path)):
                raise FileServiceError(f"Access denied: {request.filename} is outside workspace")
            
            # Check if file exists (protected by file lock)
            if not file_path.exists() or not file_path.is_file():
                self.logger.warning("File download failed - file not found",
                                  workspace_id=request.workspace_id,
                                  file_name=request.filename,
                                  file_path=str(file_path))
                raise FileNotFoundError(f"File {request.filename} not found in workspace {request.workspace_id}")
            
            # Read file content (protected by file lock)
            file_content = file_path.read_bytes()
            
            # Create FileInfo without download_url (generated at API layer)
            file_info = FileInfo(
                filename=file_path.name,
                size=len(file_content),
                mime_type=self._get_mime_type(request.filename),
                created_at=datetime.fromtimestamp(file_path.stat().st_ctime),
                relative_path=request.filename,
                download_url=""  # Generated at API layer
            )
            
            # Update workspace activity
            await self.workspace_service.update_workspace_activity(request.workspace_id)
            
            self.logger.info("File downloaded successfully with concurrency control",
                           workspace_id=request.workspace_id,
                           file_name=request.filename,
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
                            workspace_id=request.workspace_id,
                            file_name=request.filename,
                            error_type=e.__class__.__name__)
            raise FileServiceError(f"Failed to download file {request.filename}: {e}")
    
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
            filename: File name (must be URL-decoded before calling this method)
            content: File content
            
        Raises:
            FileServiceError: If validation fails
        """
        # CRITICAL SECURITY CHECKS (must match client-side validation)
        
        # Check for empty filename
        if not filename or not filename.strip():
            raise FileServiceError("Filename cannot be empty")
        
        # CRITICAL SECURITY: Check for hidden files (starting with dot)
        # This prevents access to .env, .git, .ssh, etc.
        if filename.startswith('.'):
            raise FileServiceError("Hidden files (starting with '.') are not allowed - security restriction")
        
        # CRITICAL SECURITY: Check for path separators - NO DIRECTORIES ALLOWED
        # This prevents directory traversal attacks like ../../../etc/passwd
        if '/' in filename:
            raise FileServiceError("Forward slashes (/) are not allowed in filenames - no subdirectories permitted for security")
        
        if '\\' in filename:
            raise FileServiceError("Backslashes (\\) are not allowed in filenames - no subdirectories permitted for security")
        
        # Use pathvalidate library for additional cross-platform validation
        try:
            # Validate using universal platform for maximum compatibility
            # This handles reserved names, invalid chars, length limits, etc.
            validate_filename(filename, platform=Platform.UNIVERSAL)
            
        except PathValidationError as e:
            raise FileServiceError(f"Invalid filename: {e}")
        except ImportError:
            # Fallback if pathvalidate is not available (should not happen in production)
            if len(filename) > 255:
                raise FileServiceError("Filename too long (max 255 characters)")
        
        # Check file size
        if len(content) > self.settings.max_file_size_bytes:
            raise FileServiceError(f"File too large ({len(content)} bytes, max {self.settings.max_file_size_mb}MB)")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive file service statistics including concurrency metrics
        
        Returns:
            Dictionary with file service and concurrency stats
        """
        file_stats = {
            "max_file_size_mb": self.settings.max_file_size_mb,
            "max_workspace_size_mb": self.settings.max_workspace_size_mb,
            "operations": ["upload", "list", "download"]
        }
        
        # Add concurrency statistics
        concurrency_stats = self._file_concurrency_manager.get_system_stats()
        
        return {
            "file_service": file_stats,
            "concurrency": concurrency_stats,
            "system_healthy": self._file_concurrency_manager.is_system_healthy()
        }
    
    def notify_workspace_deleted(self, workspace_id: str):
        """
        Notify file service that a workspace was deleted
        
        This ensures proper cleanup of file locks.
        
        Args:
            workspace_id: ID of the deleted workspace
        """
        self._file_concurrency_manager.notify_workspace_deleted(workspace_id)
    
    async def periodic_cleanup(self, max_idle_minutes: int = 60):
        """
        Perform periodic cleanup of file service resources
        
        Args:
            max_idle_minutes: Maximum idle time before cleanup
            
        Returns:
            Number of items cleaned up
        """
        return await self._file_concurrency_manager.periodic_cleanup(max_idle_minutes) 