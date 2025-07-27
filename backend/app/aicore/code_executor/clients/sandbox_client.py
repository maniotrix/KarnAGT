#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Sandbox Client

Clean HTTP client for interacting with CodeSandbox API endpoints.
Provides atomic operations for workspace management, file operations, and code execution.
"""

import asyncio
import os
from typing import Dict, List, Optional, Any, Tuple
import aiohttp

from app.logging.logger import get_logger
from .exceptions import (
    SandboxClientError,
    WorkspaceError,
    WorkspaceNotFoundError,
    ExecutionError,
    ExecutionTimeoutError,
    FileOperationError,
    NetworkError,
    AuthenticationError
)
from ..models import (
    WorkspaceInfo,
    ExecutionResult,
    FileInfo,
    HealthCheck,
    WorkspaceFilesResponse
)

# Get logger
logger = get_logger(__name__)

# Configuration
DEFAULT_BASE_URL = os.getenv("CODESANDBOX_URL", "http://localhost:8080/api/v1")
DEFAULT_TIMEOUT = int(os.getenv("CODESANDBOX_TIMEOUT", "60"))
MAX_RETRIES = int(os.getenv("CODESANDBOX_MAX_RETRIES", "3"))


# Models are now imported from centralized location


class SandboxClient:
    """
    Clean HTTP client for CodeSandbox API
    
    Provides atomic operations for:
    - Workspace management (create, delete, extend TTL)
    - File operations (upload, download, list)
    - Code execution (execute, get results)
    """
    
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: int = DEFAULT_TIMEOUT):
        """
        Initialize the sandbox client
        
        Args:
            base_url: Base URL of the CodeSandbox API
            timeout: Default timeout for requests in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"SandboxClient initialized with base_url={self.base_url}, timeout={self.timeout}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure aiohttp session is created"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def close(self):
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request with error handling and retries
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for aiohttp request
            
        Returns:
            JSON response data
            
        Raises:
            NetworkError: For network/HTTP errors
            AuthenticationError: For authentication errors
            SandboxClientError: For other client errors
        """
        await self._ensure_session()
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(MAX_RETRIES):
            try:
                logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                async with self.session.request(method, url, **kwargs) as response:
                    response_text = await response.text()
                    
                    if response.status == 200:
                        try:
                            return await response.json()
                        except Exception:
                            # If JSON parsing fails, return the text as content
                            return {"content": response_text}
                    elif response.status == 401:
                        raise AuthenticationError(f"Authentication failed: {response_text}")
                    elif response.status == 404:
                        raise WorkspaceNotFoundError(f"Resource not found: {response_text}")
                    elif response.status >= 400:
                        raise SandboxClientError(f"HTTP {response.status}: {response_text}")
                    else:
                        raise NetworkError(f"Unexpected status {response.status}: {response_text}")
                        
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == MAX_RETRIES - 1:  # Last attempt
                    raise NetworkError(f"Network error after {MAX_RETRIES} attempts: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        raise NetworkError("Unexpected end of _make_request")
    
    async def health_check(self) -> HealthCheck:
        """
        Check if the CodeSandbox API is healthy
        
        Returns:
            HealthCheck model with status info
        """
        try:
            result = await self._make_request("GET", "/health")
            return HealthCheck.model_validate(result)
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthCheck(
                status="unhealthy",
                jupyter_server_status="error",
                active_workspaces=0
            )
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get system statistics
        
        Returns:
            Dictionary containing system statistics
            
        Raises:
            SandboxClientError: If stats request fails
        """
        try:
            result = await self._make_request("GET", "/stats")
            return result
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            raise SandboxClientError(f"Failed to get stats: {e}")
    
    async def get_config(self) -> Dict[str, Any]:
        """
        Get system configuration
        
        Returns:
            Dictionary containing system configuration
            
        Raises:
            SandboxClientError: If config request fails
        """
        try:
            result = await self._make_request("GET", "/config")
            return result
        except Exception as e:
            logger.error(f"Failed to get config: {e}")
            raise SandboxClientError(f"Failed to get config: {e}")
    
    # =============================================================================
    # Workspace Management
    # =============================================================================
    
    async def create_workspace(self, ttl_hours: int = 2, workspace_id: Optional[str] = None) -> WorkspaceInfo:
        """
        Create a new workspace
        
        Args:
            ttl_hours: Time-to-live in hours (default: 2)
            workspace_id: Optional workspace ID, auto-generated if not provided
            
        Returns:
            WorkspaceInfo: Created workspace information
            
        Raises:
            WorkspaceError: If workspace creation fails
        """
        try:
            payload = {"ttl_hours": ttl_hours}
            if workspace_id is not None:
                payload["workspace_id"] = workspace_id
            result = await self._make_request(
                "POST", 
                "/workspace/create", 
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            workspace_info = WorkspaceInfo.model_validate(result)
            logger.info(f"Created workspace {workspace_info.workspace_id} with TTL {ttl_hours}h")
            return workspace_info
            
        except Exception as e:
            logger.error(f"Failed to create workspace: {e}")
            raise WorkspaceError(f"Workspace creation failed: {e}")
    
    async def get_workspace(self, workspace_id: str) -> WorkspaceInfo:
        """
        Get workspace information
        
        Args:
            workspace_id: Workspace identifier
            
        Returns:
            WorkspaceInfo: Workspace information
            
        Raises:
            WorkspaceNotFoundError: If workspace not found
        """
        try:
            result = await self._make_request("GET", f"/workspace/{workspace_id}")
            return WorkspaceInfo.model_validate(result)
            
        except WorkspaceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get workspace {workspace_id}: {e}")
            raise WorkspaceError(f"Failed to get workspace: {e}")
    
    async def list_workspaces(self) -> List[WorkspaceInfo]:
        """
        List all workspaces
        
        Returns:
            List of workspace information
        """
        try:
            result = await self._make_request("GET", "/workspaces")
            # Server returns List[WorkspaceInfo] directly  
            if isinstance(result, list):
                return [WorkspaceInfo.model_validate(ws) for ws in result]
            else:
                # Handle case where server returns wrapped response
                workspaces = result.get("workspaces", [])
                return [WorkspaceInfo.model_validate(ws) for ws in workspaces]
            
        except Exception as e:
            logger.error(f"Failed to list workspaces: {e}")
            raise WorkspaceError(f"Failed to list workspaces: {e}")
    
    async def delete_workspace(self, workspace_id: str) -> bool:
        """
        Delete a workspace
        
        Args:
            workspace_id: Workspace to delete
            
        Returns:
            True if deleted successfully
            
        Raises:
            WorkspaceNotFoundError: If workspace not found
        """
        try:
            await self._make_request("DELETE", f"/workspace/{workspace_id}")
            logger.info(f"Deleted workspace {workspace_id}")
            return True
            
        except WorkspaceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete workspace {workspace_id}: {e}")
            raise WorkspaceError(f"Failed to delete workspace: {e}")
    
    async def extend_workspace_ttl(self, workspace_id: str, additional_hours: int) -> WorkspaceInfo:
        """
        Extend workspace TTL
        
        Args:
            workspace_id: Workspace to extend
            additional_hours: Hours to add to TTL
            
        Returns:
            Updated workspace information
            
        Raises:
            WorkspaceNotFoundError: If workspace not found
        """
        try:
            data = aiohttp.FormData()
            data.add_field('additional_hours', str(additional_hours))
            
            result = await self._make_request(
                "POST", 
                f"/workspace/{workspace_id}/extend",
                data=data
            )
            
            workspace_info = WorkspaceInfo.model_validate(result)  
            logger.info(f"Extended workspace {workspace_id} TTL by {additional_hours}h")
            return workspace_info
            
        except WorkspaceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to extend workspace {workspace_id} TTL: {e}")
            raise WorkspaceError(f"Failed to extend workspace TTL: {e}")
    
    # =============================================================================
    # File Operations
    # =============================================================================
    
    async def upload_file(self, workspace_id: str, filename: str, content: bytes) -> FileInfo:
        """
        Upload file to workspace
        
        Args:
            workspace_id: Target workspace
            filename: Name of the file
            content: File content as bytes
            
        Returns:
            FileInfo: Uploaded file information
            
        Raises:
            WorkspaceNotFoundError: If workspace not found
            FileOperationError: If upload fails
        """
        try:
            data = aiohttp.FormData()
            data.add_field('file', content, filename=filename)
            
            result = await self._make_request(
                "POST",
                f"/workspace/{workspace_id}/upload",
                data=data
            )
            
            file_info = FileInfo.model_validate(result)
            logger.info(f"Uploaded file {filename} to workspace {workspace_id} ({len(content)} bytes)")
            return file_info
            
        except WorkspaceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to upload file {filename} to workspace {workspace_id}: {e}")
            raise FileOperationError(f"File upload failed: {e}")
    
    async def download_file(self, workspace_id: str, filename: str) -> bytes:
        """
        Download file from workspace
        
        Args:
            workspace_id: Source workspace
            filename: Path to the file in workspace
            
        Returns:
            File content as bytes
            
        Raises:
            WorkspaceNotFoundError: If workspace not found
            FileOperationError: If download fails
        """
        try:
            await self._ensure_session()
            url = f"{self.base_url}/workspace/{workspace_id}/files/{filename}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    logger.info(f"Downloaded file {filename} from workspace {workspace_id} ({len(content)} bytes)")
                    return content
                elif response.status == 404:
                    raise FileOperationError(f"File not found: {filename}")
                else:
                    error_text = await response.text()
                    raise FileOperationError(f"Download failed: HTTP {response.status}: {error_text}")
                    
        except FileOperationError:
            raise
        except Exception as e:
            logger.error(f"Failed to download file {filename} from workspace {workspace_id}: {e}")
            raise FileOperationError(f"File download failed: {e}")
    
    async def list_workspace_files(self, workspace_id: str) -> WorkspaceFilesResponse:
        """
        List files in workspace
        
        Args:
            workspace_id: Workspace to list files from
            
        Returns:
            WorkspaceFilesResponse with file listing
            
        Raises:
            WorkspaceNotFoundError: If workspace not found
        """
        try:
            result = await self._make_request("GET", f"/workspace/{workspace_id}/files")
            return WorkspaceFilesResponse.model_validate(result)
            
        except WorkspaceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to list files in workspace {workspace_id}: {e}")
            raise FileOperationError(f"Failed to list files: {e}")
    
    # =============================================================================
    # Code Execution
    # =============================================================================
    
    async def execute_code(
        self, 
        workspace_id: str, 
        code: str, 
        timeout: int = DEFAULT_TIMEOUT
    ) -> ExecutionResult:
        """
        Execute code in workspace
        
        Args:
            workspace_id: Target workspace
            code: Python code to execute
            timeout: Execution timeout in seconds
            
        Returns:
            ExecutionResult: Execution results
            
        Raises:
            WorkspaceNotFoundError: If workspace not found
            ExecutionError: If execution fails
            ExecutionTimeoutError: If execution times out
        """
        try:
            data = aiohttp.FormData()
            data.add_field('code', code)
            data.add_field('timeout', str(timeout))
            
            # Use custom timeout for this request
            request_timeout = aiohttp.ClientTimeout(total=timeout + 10)
            
            await self._ensure_session()
            url = f"{self.base_url}/workspace/{workspace_id}/execute"
            
            async with self.session.post(url, data=data, timeout=request_timeout) as response:
                if response.status == 200:
                    result = await response.json()
                    execution_result = ExecutionResult.model_validate(result)
                    logger.info(f"Executed code in workspace {workspace_id} (status: {execution_result.status})")
                    return execution_result
                elif response.status == 404:
                    raise WorkspaceNotFoundError(f"Workspace {workspace_id} not found")
                else:
                    error_text = await response.text()
                    raise ExecutionError(f"Execution failed: HTTP {response.status}: {error_text}")
                    
        except asyncio.TimeoutError:
            raise ExecutionTimeoutError(f"Code execution timed out after {timeout} seconds")
        except (WorkspaceNotFoundError, ExecutionError, ExecutionTimeoutError):
            raise
        except Exception as e:
            logger.error(f"Failed to execute code in workspace {workspace_id}: {e}")
            raise ExecutionError(f"Code execution failed: {e}")
    
    async def get_execution_result(self, execution_id: str) -> ExecutionResult:
        """
        Get execution result by ID
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            ExecutionResult: Execution results
            
        Raises:
            ExecutionError: If execution result not found
        """
        try:
            result = await self._make_request("GET", f"/execution/{execution_id}")
            return ExecutionResult.model_validate(result)
            
        except Exception as e:
            logger.error(f"Failed to get execution result {execution_id}: {e}")
            raise ExecutionError(f"Failed to get execution result: {e}")
    
    async def list_workspace_executions(
        self, 
        workspace_id: str, 
        limit: int = 50
    ) -> List[ExecutionResult]:
        """
        List executions for workspace
        
        Args:
            workspace_id: Workspace to list executions from
            limit: Maximum number of executions to return
            
        Returns:
            List of execution results
            
        Raises:
            WorkspaceNotFoundError: If workspace not found
        """
        try:
            result = await self._make_request(
                "GET", 
                f"/workspace/{workspace_id}/executions",
                params={"limit": limit}
            )
            executions = result.get("executions", [])
            return [ExecutionResult.model_validate(exec_data) for exec_data in executions]
            
        except WorkspaceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to list executions for workspace {workspace_id}: {e}")
            raise ExecutionError(f"Failed to list executions: {e}") 