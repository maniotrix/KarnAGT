#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File Service

Core business logic for workspace file management.
Separated from tool decorators for flexibility and reusability.
"""

import base64
from typing import Union, Optional
from app.logging.logger import get_logger
from app.aicore.code_executor.clients import (
    SandboxClient, 
    WorkspaceNotFoundError, 
    FileOperationError
)
from app.aicore.code_executor.models import (
    FileUploadResult,
    FileDownloadResult,
    FileListResult
)

# Get logger
logger = get_logger(__name__)


class FileService:
    """
    Service class for workspace file management.
    
    Provides clean methods that can be used directly or wrapped with decorators.
    All methods return proper Pydantic result models.
    """
    
    def __init__(self, sandbox_client: Optional[SandboxClient] = None):
        """
        Initialize the file service.
        
        Args:
            sandbox_client: Optional pre-configured client. If None, creates new clients per operation.
        """
        self.sandbox_client = sandbox_client
    
    async def upload_file(
        self, 
        workspace_id: str, 
        filename: str, 
        content: Union[str, bytes]
    ) -> FileUploadResult:
        """
        Upload a file to a workspace.
        
        Args:
            workspace_id: Target workspace identifier
            filename: Name of the file (can include subdirectory)
            content: File content as string or bytes
            
        Returns:
            FileUploadResult with success/error status and file info
        """
        try:
            logger.info(f"Uploading file {filename} to workspace {workspace_id}")
            
            # Convert content to bytes if it's a string
            content_bytes = content.encode('utf-8') if isinstance(content, str) else content
                
            if self.sandbox_client:
                client_file_info = await self.sandbox_client.upload_file(workspace_id, filename, content_bytes)
            else:
                async with SandboxClient() as client:
                    client_file_info = await client.upload_file(workspace_id, filename, content_bytes)
            
            logger.info(f"Successfully uploaded {filename} to workspace {workspace_id} ({client_file_info.size} bytes)")
            return FileUploadResult.success_result(client_file_info)
            
        except WorkspaceNotFoundError as e:
            logger.warning(f"Workspace {workspace_id} not found for file upload: {e}")
            return FileUploadResult.error_result(f"Workspace {workspace_id} not found: {e}")
        except FileOperationError as e:
            logger.error(f"Failed to upload file {filename} to workspace {workspace_id}: {e}")
            return FileUploadResult.error_result(f"Failed to upload {filename} to workspace {workspace_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error uploading file {filename} to workspace {workspace_id}: {e}")
            return FileUploadResult.error_result(f"Unexpected upload error for {filename} in workspace {workspace_id}: {e}")
    
    async def download_file(self, workspace_id: str, file_path: str) -> FileDownloadResult:
        """
        Download a file from a workspace.
        
        Args:
            workspace_id: Source workspace identifier
            file_path: Path to the file relative to workspace root
            
        Returns:
            FileDownloadResult with success/error status and file content
        """
        try:
            logger.info(f"Downloading file {file_path} from workspace {workspace_id}")
            
            if self.sandbox_client:
                content_bytes = await self.sandbox_client.download_file(workspace_id, file_path)
            else:
                async with SandboxClient() as client:
                    content_bytes = await client.download_file(workspace_id, file_path)
            
            # Always provide base64 content for binary safety
            content_b64 = base64.b64encode(content_bytes).decode('utf-8')
            
            # Try to decode as text for convenience
            content_text = None
            try:
                content_text = content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                # Binary file, text content not available
                pass
            
            filename = file_path.split('/')[-1]  # Extract filename from path
            
            logger.info(f"Successfully downloaded {file_path} from workspace {workspace_id} ({len(content_bytes)} bytes)")
            return FileDownloadResult.success_result(filename, content_bytes)
            
        except WorkspaceNotFoundError as e:
            logger.warning(f"Workspace {workspace_id} not found for file download: {e}")
            return FileDownloadResult.error_result(f"Workspace {workspace_id} not found: {e}")
        except FileOperationError as e:
            logger.error(f"Failed to download file {file_path} from workspace {workspace_id}: {e}")
            return FileDownloadResult.error_result(f"Failed to download {file_path} from workspace {workspace_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error downloading file {file_path} from workspace {workspace_id}: {e}")
            return FileDownloadResult.error_result(f"Unexpected download error for {file_path} in workspace {workspace_id}: {e}")
    
    async def list_workspace_files(self, workspace_id: str) -> FileListResult:
        """
        List all files in a workspace.
        
        Args:
            workspace_id: Workspace to list files from
            
        Returns:
            FileListResult with success/error status and file list
        """
        try:
            logger.debug(f"Listing files in workspace {workspace_id}")
            
            if self.sandbox_client:
                client_files = await self.sandbox_client.list_workspace_files(workspace_id)
            else:
                async with SandboxClient() as client:
                    client_files = await client.list_workspace_files(workspace_id)
            
            # Convert to our models
            # Client and service now use same models - no conversion needed
            files = client_files.files
            
            logger.info(f"Successfully listed {len(files)} files in workspace {workspace_id}")
            return FileListResult.success_result(files)
            
        except WorkspaceNotFoundError as e:
            logger.warning(f"Workspace {workspace_id} not found for file listing: {e}")
            return FileListResult.error_result(f"Workspace {workspace_id} not found: {e}")
        except Exception as e:
            logger.error(f"Failed to list files in workspace {workspace_id}: {e}")
            return FileListResult.error_result(f"Failed to list files in workspace {workspace_id}: {e}")
    
# Conversion method removed - client and service now use same models 