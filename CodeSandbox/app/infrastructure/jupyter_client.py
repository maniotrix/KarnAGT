#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Jupyter Server Integration Client

Handles communication with Jupyter Server for kernel and file management.
Provides high-level abstractions over Jupyter's REST API.
"""

import asyncio
import base64
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, AsyncGenerator
import httpx
from pathlib import Path

from app.core.config import Settings
from app.domain.models import (
    WorkspaceInfo, WorkspaceStatus, ExecutionResult, ExecutionStatus,
    FileInfo, ExecutionOutput
)


class JupyterClientError(Exception):
    """Base exception for Jupyter client errors"""
    pass


class KernelNotFoundError(JupyterClientError):
    """Kernel not found error"""
    pass


class WorkspaceNotFoundError(JupyterClientError):
    """Workspace directory not found error"""
    pass


class JupyterServerClient:
    """
    High-level client for Jupyter Server API
    
    Manages kernels, executes code, and handles file operations
    through Jupyter Server's REST API.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.jupyter_url
        self.timeout = settings.max_execution_timeout  # Use execution timeout for Jupyter API calls
        self.headers = settings.get_jupyter_headers()
        
        # Track active kernels
        self._kernels: Dict[str, Dict[str, Any]] = {}
        
        # HTTP client with proper configuration
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=httpx.Timeout(self.timeout)
        )
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def close(self):
        """Close the HTTP client"""
        if hasattr(self, '_client'):
            await self._client.aclose()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if Jupyter Server is healthy"""
        try:
            response = await self._client.get("/api/status")
            response.raise_for_status()
            return {
                "status": "healthy",
                "jupyter_status": response.json(),
                "timestamp": datetime.utcnow().isoformat()
            }
        except httpx.RequestError as e:
            raise JupyterClientError(f"Failed to connect to Jupyter Server: {e}")
        except httpx.HTTPStatusError as e:
            raise JupyterClientError(f"Jupyter Server returned error: {e.response.status_code}")
    
    async def create_workspace_directory(self, workspace_id: str) -> Dict[str, Any]:
        """Create workspace directory via Jupyter contents API"""
        try:
            workspace_path = f"workspaces/{workspace_id}"
            
            # Create main workspace directory
            response = await self._client.put(
                f"/api/contents/{workspace_path}",
                json={"type": "directory"}
            )
            response.raise_for_status()
            
            # Create outputs subdirectory
            outputs_response = await self._client.put(
                f"/api/contents/{workspace_path}/outputs",
                json={"type": "directory"}
            )
            outputs_response.raise_for_status()
            
            return {
                "workspace_path": workspace_path,
                "created_at": datetime.utcnow().isoformat(),
                "status": "created"
            }
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                # Directory already exists, that's fine
                return {
                    "workspace_path": f"workspaces/{workspace_id}",
                    "status": "exists"
                }
            raise JupyterClientError(f"Failed to create workspace directory: {e.response.text}")
    
    async def create_kernel(self, workspace_id: str) -> Dict[str, Any]:
        """Create a new Jupyter kernel for the workspace"""
        try:
            # Create kernel
            response = await self._client.post(
                "/api/kernels",
                json={"name": "python3"}
            )
            response.raise_for_status()
            kernel_info = response.json()
            
            # Store kernel info
            self._kernels[workspace_id] = {
                "kernel_id": kernel_info["id"],
                "kernel_info": kernel_info,
                "created_at": datetime.utcnow(),
                "last_activity": datetime.utcnow()
            }
            
            # Initialize kernel with workspace setup
            await self._initialize_kernel_workspace(workspace_id, kernel_info["id"])
            
            return {
                "kernel_id": kernel_info["id"],
                "workspace_id": workspace_id,
                "status": "ready",
                "created_at": datetime.utcnow().isoformat()
            }
            
        except httpx.HTTPStatusError as e:
            raise JupyterClientError(f"Failed to create kernel: {e.response.text}")
    
    async def _initialize_kernel_workspace(self, workspace_id: str, kernel_id: str):
        """Initialize kernel with workspace-specific setup"""
        setup_code = f"""
import os
import sys
import json
from pathlib import Path

# Set working directory to workspace  
workspace_path = Path('/workspaces/{workspace_id}').resolve()
workspace_path.mkdir(parents=True, exist_ok=True)
os.chdir(str(workspace_path))

# Add workspace to Python path
sys.path.insert(0, str(workspace_path))

# Create outputs directory
outputs_dir = workspace_path / 'outputs'
outputs_dir.mkdir(exist_ok=True)

# Security: Block dangerous imports
import builtins
_original_import = builtins.__import__

BLOCKED_MODULES = {json.dumps(self.settings.blocked_imports)}

def _secure_import(name, *args, **kwargs):
    if any(blocked in name for blocked in BLOCKED_MODULES):
        raise ImportError(f"Module '{{name}}' is blocked for security reasons")
    return _original_import(name, *args, **kwargs)

builtins.__import__ = _secure_import

print(f"Workspace initialized at: {{os.getcwd()}}")
print(f"Security restrictions applied for: {', '.join(self.settings.blocked_imports)}")
"""
        
        # Execute setup code
        await self._execute_code_in_kernel(kernel_id, setup_code)
    
    async def execute_code(self, workspace_id: str, code: str, timeout: Optional[int] = None) -> ExecutionResult:
        """Execute code in workspace kernel"""
        if workspace_id not in self._kernels:
            raise WorkspaceNotFoundError(f"No kernel found for workspace: {workspace_id}")
        
        kernel_info = self._kernels[workspace_id]
        kernel_id = kernel_info["kernel_id"]
        execution_timeout = timeout or self.settings.default_execution_timeout
        
        # Update last activity
        kernel_info["last_activity"] = datetime.utcnow()
        
        # Wrap code to capture results
        wrapped_code = self._wrap_code_for_execution(code)
        
        try:
            # Execute code and collect outputs
            result = await self._execute_code_in_kernel(kernel_id, wrapped_code, execution_timeout)
            
            # Get generated files
            generated_files = await self._get_workspace_files(workspace_id)
            
            return ExecutionResult(
                workspace_id=workspace_id,
                status=ExecutionStatus.COMPLETED,
                stdout=result.get("stdout", ""),
                stderr=result.get("stderr", ""),
                outputs=result.get("outputs", []),
                result_data=result.get("result_data"),
                generated_files=generated_files,
                execution_time_ms=result.get("execution_time_ms"),
                completed_at=datetime.utcnow()
            )
            
        except asyncio.TimeoutError:
            return ExecutionResult(
                workspace_id=workspace_id,
                status=ExecutionStatus.TIMEOUT,
                stderr="Execution timed out",
                completed_at=datetime.utcnow()
            )
        except Exception as e:
            return ExecutionResult(
                workspace_id=workspace_id,
                status=ExecutionStatus.FAILED,
                stderr=str(e),
                completed_at=datetime.utcnow()
            )
    
    def _wrap_code_for_execution(self, code: str) -> str:
        """Wrap user code to capture outputs and results"""
        return f"""
import sys
import json
import traceback
from io import StringIO
from datetime import datetime

# Capture stdout/stderr
stdout_capture = StringIO()
stderr_capture = StringIO()

start_time = datetime.utcnow()

try:
    # Redirect streams
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = stdout_capture, stderr_capture
    
    # User code execution
{self._indent_code(code, 4)}
    
finally:
    # Restore streams
    sys.stdout, sys.stderr = old_stdout, old_stderr

end_time = datetime.utcnow()
execution_time_ms = int((end_time - start_time).total_seconds() * 1000)

# Capture outputs
captured_stdout = stdout_capture.getvalue()
captured_stderr = stderr_capture.getvalue()

# Print structured output for parsing
print("<<<EXECUTION_RESULT>>>")
print(json.dumps({{
    "stdout": captured_stdout,
    "stderr": captured_stderr,
    "execution_time_ms": execution_time_ms,
    "result_data": locals().get('result'),
    "status": "success"
}}))
print("<<<EXECUTION_END>>>")
"""
    
    def _indent_code(self, code: str, spaces: int = 4) -> str:
        """Indent code for wrapping in try block"""
        indent = " " * spaces
        return "\n".join(indent + line for line in code.split("\n"))
    
    async def _execute_code_in_kernel(self, kernel_id: str, code: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Execute code in specific kernel and return structured result"""
        try:
            # Start code execution
            response = await self._client.post(
                f"/api/kernels/{kernel_id}/execute",
                json={"code": code},
                timeout=timeout or self.timeout
            )
            response.raise_for_status()
            
            # Parse execution result
            execution_data = response.json()
            
            # Extract structured output if present
            if "output" in execution_data:
                output = execution_data["output"]
                if "<<<EXECUTION_RESULT>>>" in output and "<<<EXECUTION_END>>>" in output:
                    start_marker = output.find("<<<EXECUTION_RESULT>>>") + len("<<<EXECUTION_RESULT>>>")
                    end_marker = output.find("<<<EXECUTION_END>>>")
                    result_json = output[start_marker:end_marker].strip()
                    
                    try:
                        return json.loads(result_json)
                    except json.JSONDecodeError:
                        pass
            
            # Fallback to basic output parsing
            return {
                "stdout": execution_data.get("output", ""),
                "stderr": execution_data.get("error", ""),
                "status": execution_data.get("status", "unknown")
            }
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise KernelNotFoundError(f"Kernel {kernel_id} not found")
            raise JupyterClientError(f"Code execution failed: {e.response.text}")
    
    async def upload_file_to_workspace(self, workspace_id: str, filename: str, content: bytes) -> FileInfo:
        """Upload file to workspace via Jupyter contents API"""
        try:
            workspace_path = f"workspaces/{workspace_id}"
            file_path = f"{workspace_path}/{filename}"
            
            # Encode content as base64
            b64_content = base64.b64encode(content).decode("utf-8")
            
            # Upload file
            response = await self._client.put(
                f"/api/contents/{file_path}",
                json={
                    "type": "file",
                    "format": "base64",
                    "content": b64_content
                }
            )
            response.raise_for_status()
            
            file_info = response.json()
            
            return FileInfo(
                filename=filename,
                size=len(content),
                mime_type=file_info.get("mimetype", "application/octet-stream"),
                created_at=datetime.utcnow(),
                relative_path=filename,
                download_url=f"{self.base_url}/files/{file_path}"
            )
            
        except httpx.HTTPStatusError as e:
            raise JupyterClientError(f"File upload failed: {e.response.text}")
    
    async def _get_workspace_files(self, workspace_id: str) -> List[FileInfo]:
        """Get list of files in workspace"""
        try:
            workspace_path = f"workspaces/{workspace_id}"
            
            response = await self._client.get(f"/api/contents/{workspace_path}")
            response.raise_for_status()
            
            contents = response.json()
            files = []
            
            for item in contents.get("content", []):
                if item["type"] == "file":
                    files.append(FileInfo(
                        filename=item["name"],
                        size=item.get("size", 0),
                        mime_type=item.get("mimetype", "application/octet-stream"),
                        created_at=datetime.utcnow(),  # Jupyter doesn't provide creation time
                        relative_path=item["path"].replace(f"{workspace_path}/", ""),
                        download_url=f"{self.base_url}/files/{item['path']}"
                    ))
            
            return files
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []  # Workspace doesn't exist yet
            raise JupyterClientError(f"Failed to list workspace files: {e.response.text}")
    
    async def delete_kernel(self, workspace_id: str) -> bool:
        """Delete kernel associated with workspace"""
        if workspace_id not in self._kernels:
            return False
        
        try:
            kernel_info = self._kernels[workspace_id]
            kernel_id = kernel_info["kernel_id"]
            
            response = await self._client.delete(f"/api/kernels/{kernel_id}")
            response.raise_for_status()
            
            # Remove from tracking
            del self._kernels[workspace_id]
            
            return True
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Kernel already deleted
                if workspace_id in self._kernels:
                    del self._kernels[workspace_id]
                return True
            raise JupyterClientError(f"Failed to delete kernel: {e.response.text}")
    
    async def cleanup_expired_kernels(self, max_idle_minutes: int = 60):
        """Clean up kernels that have been idle for too long"""
        now = datetime.utcnow()
        expired_workspaces = []
        
        for workspace_id, kernel_info in self._kernels.items():
            last_activity = kernel_info["last_activity"]
            idle_time = now - last_activity
            
            if idle_time.total_seconds() > (max_idle_minutes * 60):
                expired_workspaces.append(workspace_id)
        
        # Delete expired kernels
        for workspace_id in expired_workspaces:
            try:
                await self.delete_kernel(workspace_id)
            except Exception as e:
                # Log but don't fail cleanup
                print(f"Warning: Failed to cleanup kernel for workspace {workspace_id}: {e}")
    
    def get_kernel_info(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Get kernel information for workspace"""
        return self._kernels.get(workspace_id)
    
    def list_active_kernels(self) -> List[str]:
        """List all active workspace IDs with kernels"""
        return list(self._kernels.keys()) 