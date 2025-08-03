#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File Service

Core business logic for workspace file management.
Separated from tool decorators for flexibility and reusability.
"""

import base64
from pathlib import Path
from typing import Union, Optional
from pathvalidate import ValidationError as PathValidationError, validate_filename, Platform
from pydantic import ValidationError
from app.logging.logger import get_logger
from app.utils.async_http_client import AsyncHTTPClient, DownloadError, FileTooLargeError, HTTPClientError
from app.utils.file_utils import get_file_content
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
from app.aicore.code_executor.config import (
    enhance_file_info_with_full_url,
    enhance_file_list_with_full_urls
)

# Get logger
logger = get_logger(__name__)

MAX_FILE_SIZE_MB = 20


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
    
    def _get_auth_headers_for_url(self, url: str) -> dict:
        """
        Get authentication headers for URL if it's an internal proxy endpoint
        
        Args:
            url: The URL to check
            
        Returns:
            Dictionary of headers to include in the request
        """
        from app.core.config import get_settings
        import logging
        
        logger = logging.getLogger(__name__)
        settings = get_settings()
        
        # Debug logging
        is_internal = settings.is_internal_proxy_url(url)
        token_available = bool(settings.CODE_EXECUTOR_TOKEN)
        
        logger.info(f"[AUTH-DEBUG] URL: {url}")
        logger.info(f"[AUTH-DEBUG] Is internal: {is_internal}")
        logger.info(f"[AUTH-DEBUG] Token available: {token_available}")
        logger.info(f"[AUTH-DEBUG] Server base URL: {settings.server_base_url}")
        
        if is_internal:
            auth_header = {"Authorization": f"Bearer {settings.CODE_EXECUTOR_TOKEN}"}
            logger.info(f"[AUTH-DEBUG] Adding auth header: Bearer {settings.CODE_EXECUTOR_TOKEN[:10]}...")
            return auth_header
        
        logger.info(f"[AUTH-DEBUG] No auth header needed for external URL")
        return {}
        
    async def download_and_upload_file_to_workspace(
        self,
        workspace_id: str,
        source: str, 
        file_name: Optional[str] = None,
        max_size_mb: int = MAX_FILE_SIZE_MB
    ) -> FileUploadResult:
        """Download from local path or URL and upload to workspace
        
        Args:
            source: File path or URL
            workspace_id: Target workspace identifier
            filename: Name of the file
            max_size_mb: Maximum file size in MB
            
        Returns:
            FileUploadResult with success/error status and file info
        """
        
        # Input validation
        if not source or not source.strip():
            return FileUploadResult.error_result("Source URL cannot be empty")
        
        if not workspace_id or not workspace_id.strip():
            return FileUploadResult.error_result("Workspace ID cannot be empty. Provide a valid workspace ID or create a new workspace before uploading file.")
        
        try:
            if source.startswith(('http://', 'https://')):
                # Handle remote file using async HTTP client
                try:
                    # Get authentication headers for internal URLs
                    auth_headers = self._get_auth_headers_for_url(source)
                    
                    async with AsyncHTTPClient() as http_client:
                        content, extracted_filename = await http_client.download_file(
                            url=source,
                            max_size_mb=max_size_mb,
                            filename=file_name,
                            headers=auth_headers
                        )
                except (DownloadError, FileTooLargeError, HTTPClientError) as e:
                    return FileUploadResult.error_result(f"Failed to download from URL {source}: {e}")
                    
                final_filename = file_name or extracted_filename
            
            else:
                # Handle local file
                try:
                    content, extracted_filename = await get_file_content(source, max_size_mb, file_name)
                    if not content:
                        return FileUploadResult.error_result(f"File content is empty: {source}")
                except FileNotFoundError as e:
                    return FileUploadResult.error_result(f"Local file not found: {source}")
                except ValueError as e:
                    return FileUploadResult.error_result(f"File validation error: {e}")
                except Exception as e:
                    return FileUploadResult.error_result(f"Failed to read local file {source}: {e}")

                final_filename = file_name or extracted_filename
            
            # Upload to workspace - this already returns FileUploadResult
            return await self.upload_file(workspace_id, final_filename, content)
            
        except Exception as e:
            logger.error(f"Unexpected error in download_and_upload_file_to_workspace: {e}")
            return FileUploadResult.error_result(f"Unexpected error processing file {source}: {e}")
    
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
        # Input validation
        if not workspace_id or not workspace_id.strip():
            logger.warning("Attempted to upload file with empty workspace ID")
            return FileUploadResult.error_result("Workspace ID cannot be empty")
            
        if not filename or not filename.strip():
            logger.warning("Attempted to upload file with empty filename")
            return FileUploadResult.error_result("Filename cannot be empty")
        
        # CLIENT-SIDE FILENAME VALIDATION (Defense in Depth)
        # Validate filename before sending to server to fail fast and provide consistent behavior
        validation_error = self._validate_filename_client_side(filename)
        if validation_error:
            logger.warning(f"Client-side filename validation failed for '{filename}': {validation_error}")
            return FileUploadResult.error_result(validation_error)
        
        try:
            logger.info(f"Uploading file {filename} to workspace {workspace_id}")
            
            # Convert content to bytes if it's a string
            content_bytes = content.encode('utf-8') if isinstance(content, str) else content
                
            if self.sandbox_client:
                client_file_info = await self.sandbox_client.upload_file(workspace_id, filename, content_bytes)
            else:
                async with SandboxClient() as client:
                    client_file_info = await client.upload_file(workspace_id, filename, content_bytes)
            
            # Enhance file info with full download URL
            enhance_file_info_with_full_url(client_file_info, workspace_id)
            
            logger.info(f"Successfully uploaded {filename} to workspace {workspace_id} ({client_file_info.size} bytes)")
            return FileUploadResult.success_result(client_file_info)
            
        except WorkspaceNotFoundError as e:
            logger.warning(f"Workspace {workspace_id} not found for file upload: {e}")
            return FileUploadResult.error_result(f"Workspace {workspace_id} not found: {e} - Please provide a valid workspace ID or create a new workspace before uploading files.")
        except FileOperationError as e:
            logger.error(f"Failed to upload file {filename} to workspace {workspace_id}: {e}")
            return FileUploadResult.error_result(f"Failed to upload {filename} to workspace {workspace_id}: {e}")
        except ValidationError as e:
            logger.warning(f"Server returned invalid file info structure for upload: {e}")
            return FileUploadResult.error_result("Invalid file info format received from server")
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
        # Input validation
        if not workspace_id or not workspace_id.strip():
            logger.warning("Attempted to download file with empty workspace ID")
            return FileDownloadResult.error_result("Workspace ID cannot be empty")
            
        if not file_path or not file_path.strip():
            logger.warning("Attempted to download file with empty file path")
            return FileDownloadResult.error_result("File path cannot be empty")
        
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
        except ValidationError as e:
            logger.warning(f"Server returned invalid response for file download: {e}")
            return FileDownloadResult.error_result("Invalid file download response from server")
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
        # Input validation
        if not workspace_id or not workspace_id.strip():
            logger.warning("Attempted to list files with empty workspace ID")
            return FileListResult.error_result("Workspace ID cannot be empty")
        
        try:
            logger.debug(f"Listing files in workspace {workspace_id}")
            
            if self.sandbox_client:
                client_files = await self.sandbox_client.list_workspace_files(workspace_id)
            else:
                async with SandboxClient() as client:
                    client_files = await client.list_workspace_files(workspace_id)
            
            # Enhance all file info objects with full download URLs
            enhance_file_list_with_full_urls(client_files.files, workspace_id)
            
            # Convert to our models
            # Client and service now use same models - no conversion needed
            files = client_files.files
            
            logger.info(f"Successfully listed {len(files)} files in workspace {workspace_id}")
            return FileListResult.success_result(files)
            
        except WorkspaceNotFoundError as e:
            logger.warning(f"Workspace {workspace_id} not found for file listing: {e}")
            return FileListResult.error_result(f"Workspace {workspace_id} not found: {e}")
        except ValidationError as e:
            logger.warning(f"Server returned invalid file list structure for workspace {workspace_id}: {e}")
            return FileListResult.error_result("Invalid file list format received from server")
        except Exception as e:
            logger.error(f"Failed to list files in workspace {workspace_id}: {e}")
            return FileListResult.error_result(f"Failed to list files in workspace {workspace_id}: {e}")
    
    def _validate_filename_client_side(self, filename: str) -> Optional[str]:
        """
        Client-side filename validation (mirrors server-side validation)
        
        This provides defense-in-depth by catching invalid filenames before
        they're sent to the server, enabling fail-fast behavior and consistent
        validation even when the server is unavailable.
        
        CRITICAL SECURITY CHECKS (restored from original logic):
        1. No empty filenames
        2. No hidden files (.) - prevents access to .env, .git, .ssh, etc.
        3. No path separators (/ or \\) - prevents directory traversal attacks
        4. Additional pathvalidate checks for cross-platform compatibility
        
        Args:
            filename: Filename to validate (should be URL-decoded)
            
        Returns:
            Error message string if validation fails, None if valid
        """
        # Check for empty filename
        if not filename or not filename.strip():
            return "Filename cannot be empty"
        
        # CRITICAL SECURITY: Check for hidden files (starting with dot)
        # This prevents access to .env, .git, .ssh, etc.
        if filename.startswith('.'):
            return "Hidden files (starting with '.') are not allowed - security restriction"
        
        # CRITICAL SECURITY: Check for path separators - NO DIRECTORIES ALLOWED
        # This prevents directory traversal attacks like ../../../etc/passwd
        if '/' in filename:
            return "Forward slashes (/) are not allowed in filenames - no subdirectories permitted for security"
        
        if '\\' in filename:
            return "Backslashes (\\\\) are not allowed in filenames - no subdirectories permitted for security"
        
        try:
            # Use pathvalidate for additional cross-platform validation
            # This handles reserved names, invalid chars, length limits, etc.
            validate_filename(filename, platform=Platform.UNIVERSAL)
            return None  # Valid filename
            
        except PathValidationError as e:
            return f"Invalid filename: {str(e)}"
        except Exception as e:
            # Fallback for any unexpected errors
            return f"Filename validation error: {e}"