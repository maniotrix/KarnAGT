#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Jupyter Client Integration

Uses jupyter_client library directly instead of manual HTTP requests.
Much simpler and more reliable approach.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from jupyter_client.multikernelmanager import AsyncMultiKernelManager
from jupyter_client.asynchronous.client import AsyncKernelClient

from app.core.config import Settings
from app.domain.models import (
    ExecutionResult, ExecutionStatus,
    FileInfo, ExecutionOutput
)
from app.utils.logger import Loggers


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
    High-level client using jupyter_client library directly
    
    Much simpler approach - let jupyter_client handle the complexity!
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = Loggers.jupyter
        
        # Use AsyncMultiKernelManager - the proper way to manage multiple kernels
        self.kernel_manager = AsyncMultiKernelManager()
        
        # Track workspace directories and kernels
        self._workspaces: Dict[str, Dict[str, Any]] = {}
        self._workspace_base = Path("workspaces")
        
        self.logger.info("Jupyter client initialized using jupyter_client library",
                        workspace_base=str(self._workspace_base))
    
    async def initialize_workspace_directory(self):
        """Initialize required directories during application startup"""
        try:
            self.logger.info("Initializing workspace directories")
            
            # Create the main 'workspaces' directory locally
            self._workspace_base.mkdir(exist_ok=True)
            
            self.logger.info("Workspace directories initialized successfully")
            
        except Exception as e:
            self.logger.error("Unexpected error during directory initialization", exc=e)
            raise JupyterClientError(f"Failed to initialize workspace directories: {e}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def close(self):
        """Close all kernels and cleanup"""
        if hasattr(self, 'kernel_manager'):
            await self.kernel_manager.shutdown_all()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if the kernel manager is healthy"""
        try:
            return {
                "status": "healthy",
                "active_kernels": len(self.kernel_manager),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            raise JupyterClientError(f"Health check failed: {e}")
    
    async def create_workspace_directory(self, workspace_id: str) -> Dict[str, Any]:
        """Create workspace directory locally"""
        workspace_path = self._workspace_base / workspace_id
        
        self.logger.debug("Creating workspace directory",
                        workspace_id=workspace_id,
                        workspace_path=str(workspace_path))
        
        try:
            # Create workspace and outputs directories
            workspace_path.mkdir(exist_ok=True)
            (workspace_path / "outputs").mkdir(exist_ok=True)
            
            # Track workspace
            self._workspaces[workspace_id] = {
                "workspace_path": str(workspace_path),
                "created_at": datetime.utcnow(),
                "status": "created"
            }
            
            self.logger.info("Workspace directory created successfully",
                           workspace_id=workspace_id,
                           workspace_path=str(workspace_path))
            
            return {
                "workspace_path": str(workspace_path),
                "created_at": datetime.utcnow().isoformat(),
                "status": "created"
            }
            
        except Exception as e:
            self.logger.error("Workspace directory creation failed",
                            workspace_id=workspace_id,
                            error=str(e))
            raise JupyterClientError(f"Failed to create workspace directory: {e}")
    
    async def create_kernel(self, workspace_id: str) -> Dict[str, Any]:
        """Create a new Jupyter kernel for the workspace using proper jupyter_client"""
        self.logger.info("Creating Jupyter kernel using jupyter_client",
                        workspace_id=workspace_id)
        
        try:
            # Get workspace path
            if workspace_id not in self._workspaces:
                raise WorkspaceNotFoundError(f"Workspace {workspace_id} not found")
            
            workspace_path = self._workspaces[workspace_id]["workspace_path"]
            
            # Start kernel with proper working directory
            kernel_id = await self.kernel_manager.start_kernel(
                kernel_name="python3",
                cwd=workspace_path  # Set working directory to workspace
            )
            
            # Get the kernel client
            kernel_client: AsyncKernelClient = self.kernel_manager.get_kernel(kernel_id).client()
            
            # Wait for kernel to be ready
            await kernel_client.wait_for_ready(timeout=30)
            
            # Initialize kernel with workspace setup
            await self._initialize_kernel_workspace(workspace_id, kernel_id, kernel_client)
            
            # Store kernel info
            self._workspaces[workspace_id].update({
                "kernel_id": kernel_id,
                "kernel_client": kernel_client,
                "created_at": datetime.utcnow(),
                "last_activity": datetime.utcnow(),
                "status": "ready"
            })
            
            self.logger.info("Jupyter kernel created successfully",
                           workspace_id=workspace_id,
                           kernel_id=kernel_id,
                           active_kernels=len(self.kernel_manager))
            
            return {
                "kernel_id": kernel_id,
                "workspace_id": workspace_id,
                "status": "ready",
                "created_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error("Jupyter kernel creation failed",
                            workspace_id=workspace_id,
                            error=str(e))
            raise JupyterClientError(f"Failed to create kernel: {e}")
    
    async def _initialize_kernel_workspace(self, workspace_id: str, kernel_id: str, kernel_client: AsyncKernelClient):
        """Initialize kernel with workspace-specific setup using proper jupyter_client"""
        setup_code = f"""
import os
import sys
from pathlib import Path

# Workspace is already set as working directory by kernel manager
print(f"Workspace initialized at: {{os.getcwd()}}")

# Add workspace to Python path
current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Create outputs directory if not exists
outputs_dir = Path('outputs')
outputs_dir.mkdir(exist_ok=True)

print("✅ Workspace ready for code execution!")
print("✅ All libraries and functions available (container isolation provides security)")
print("Kernel ready for code execution!")
"""
        
        # Execute setup code using proper jupyter_client
        try:
            msg_id = kernel_client.execute(setup_code)
            
            # Wait for execution to complete
            await self._wait_for_execution(kernel_client, msg_id, timeout=10)
            
            self.logger.info("Kernel workspace initialized successfully",
                           workspace_id=workspace_id,
                           kernel_id=kernel_id)
            
        except Exception as e:
            self.logger.error("Failed to initialize kernel workspace",
                            workspace_id=workspace_id,
                            kernel_id=kernel_id,
                            error=str(e))
            raise JupyterClientError(f"Failed to initialize kernel workspace: {e}")
    
    async def execute_code(self, workspace_id: str, code: str, timeout: Optional[int] = None) -> ExecutionResult:
        """Execute code in workspace kernel using proper jupyter_client"""
        if workspace_id not in self._workspaces:
            self.logger.error("Code execution failed - no workspace found",
                            workspace_id=workspace_id,
                            active_workspaces=list(self._workspaces.keys()))
            raise WorkspaceNotFoundError(f"No workspace found: {workspace_id}")
        
        workspace_info = self._workspaces[workspace_id]
        if "kernel_client" not in workspace_info:
            raise KernelNotFoundError(f"No kernel found for workspace: {workspace_id}")
        
        kernel_client: AsyncKernelClient = workspace_info["kernel_client"]
        execution_timeout = timeout or self.settings.default_execution_timeout
        
        self.logger.debug("Executing code in kernel using jupyter_client",
                         workspace_id=workspace_id,
                         kernel_id=workspace_info["kernel_id"],
                         code_length=len(code),
                         timeout=execution_timeout)
        
        # Update last activity
        workspace_info["last_activity"] = datetime.utcnow()
        
        start_time = datetime.utcnow()
        
        try:
            # Execute code using proper jupyter_client - much simpler!
            self.logger.debug("🚀 Sending code to kernel",
                            workspace_id=workspace_id,
                            kernel_id=workspace_info["kernel_id"])
            
            msg_id = kernel_client.execute(code)
            
            self.logger.debug("📨 Execution message sent",
                            workspace_id=workspace_id,
                            msg_id=msg_id)
            
            # Collect execution results
            stdout_lines = []
            stderr_lines = []
            outputs = []
            
            # Wait for execution to complete and collect outputs
            async for msg in self._collect_execution_results(kernel_client, msg_id, execution_timeout):
                msg_type = msg['header']['msg_type']
                content = msg['content']
                
                self.logger.debug(f"📥 Received kernel message: {msg_type}" + 
                                (f" (state: {content.get('execution_state')})" if msg_type == 'status' else ""),
                                workspace_id=workspace_id)
                
                if msg_type == 'stream':
                    if content['name'] == 'stdout':
                        stdout_lines.append(content['text'])
                        self.logger.debug(f"📝 Captured stdout: {content['text'][:200]}{'...' if len(content['text']) > 200 else ''}",
                                        workspace_id=workspace_id)
                    elif content['name'] == 'stderr':
                        stderr_lines.append(content['text'])
                        self.logger.debug(f"⚠️ Captured stderr: {content['text'][:200]}{'...' if len(content['text']) > 200 else ''}",
                                        workspace_id=workspace_id)
                elif msg_type in ['execute_result', 'display_data']:
                    outputs.append({
                        'type': msg_type,  # Fixed: use 'type' not 'output_type'
                        'data': content.get('data', {}),
                        'metadata': content.get('metadata', {})
                    })
                    self.logger.debug("🎯 Captured output",
                                    workspace_id=workspace_id,
                                    output_type=msg_type,
                                    data_keys=list(content.get('data', {}).keys()))
                elif msg_type == 'error':
                    error_msg = f"Error: {content.get('ename', 'Unknown')}: {content.get('evalue', '')}"
                    stderr_lines.append(error_msg)
                    self.logger.debug("❌ Captured error",
                                    workspace_id=workspace_id,
                                    error_name=content.get('ename'),
                                    error_value=content.get('evalue'))
            
            # Get generated files
            generated_files = await self._get_workspace_files(workspace_id)
            
            execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return ExecutionResult(
                workspace_id=workspace_id,
                status=ExecutionStatus.COMPLETED,
                stdout="".join(stdout_lines),
                stderr="".join(stderr_lines),
                outputs=[ExecutionOutput(**output) for output in outputs],
                result_data=None,
                generated_files=generated_files,
                execution_time_ms=execution_time_ms,
                completed_at=datetime.utcnow()
            )
            
        except asyncio.TimeoutError:
            self.logger.warning("Code execution timed out",
                              workspace_id=workspace_id,
                              timeout=execution_timeout)
            return ExecutionResult(
                workspace_id=workspace_id,
                status=ExecutionStatus.TIMEOUT,
                stderr="Execution timed out",
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                completed_at=datetime.utcnow()
            )
        except Exception as e:
            self.logger.error("Code execution failed",
                            exc=e,
                            workspace_id=workspace_id,
                            error_type=e.__class__.__name__)
            execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return ExecutionResult(
                workspace_id=workspace_id,
                status=ExecutionStatus.FAILED,
                stderr=str(e),
                execution_time_ms=execution_time_ms,
                completed_at=datetime.utcnow()
            )
    
    async def _wait_for_execution(self, kernel_client: AsyncKernelClient, msg_id: str, timeout: int = 30):
        """Wait for execution to complete"""
        deadline = asyncio.get_event_loop().time() + timeout
        
        while asyncio.get_event_loop().time() < deadline:
            try:
                msg = await asyncio.wait_for(kernel_client.get_iopub_msg(), timeout=1.0)
                if (msg['parent_header'].get('msg_id') == msg_id and
                    msg['header']['msg_type'] == 'status' and
                    msg['content']['execution_state'] == 'idle'):
                    return
            except asyncio.TimeoutError:
                continue
        
        raise asyncio.TimeoutError("Execution did not complete within timeout")
    
    async def _collect_execution_results(self, kernel_client: AsyncKernelClient, msg_id: str, timeout: int):
        """Collect all execution results from kernel"""
        deadline = asyncio.get_event_loop().time() + timeout
        
        while asyncio.get_event_loop().time() < deadline:
            try:
                msg = await asyncio.wait_for(kernel_client.get_iopub_msg(), timeout=1.0)
                
                # Only process messages from our execution
                if msg['parent_header'].get('msg_id') == msg_id:
                    yield msg
                    
                    # Stop when execution is complete
                    if (msg['header']['msg_type'] == 'status' and
                        msg['content']['execution_state'] == 'idle'):
                        break
                        
            except asyncio.TimeoutError:
                continue
        
        # Get the final reply
        try:
            reply = await asyncio.wait_for(kernel_client.get_shell_msg(), timeout=5.0)
            if reply['parent_header'].get('msg_id') == msg_id:
                yield reply
        except asyncio.TimeoutError:
            pass
    
    async def upload_file_to_workspace(self, workspace_id: str, filename: str, content: bytes) -> FileInfo:
        """Upload file to workspace directory"""
        try:
            if workspace_id not in self._workspaces:
                raise WorkspaceNotFoundError(f"Workspace {workspace_id} not found")
            
            workspace_path = Path(self._workspaces[workspace_id]["workspace_path"])
            file_path = workspace_path / filename
            
            # Write file to workspace directory
            file_path.write_bytes(content)
            
            return FileInfo(
                filename=filename,
                size=len(content),
                mime_type="application/octet-stream",  # Could detect based on extension
                created_at=datetime.utcnow(),
                relative_path=filename,
                download_url=f"file://{file_path.absolute()}"  # Local file URL
            )
            
        except Exception as e:
            raise JupyterClientError(f"File upload failed: {e}")
    
    async def _get_workspace_files(self, workspace_id: str) -> List[FileInfo]:
        """Get list of files in workspace"""
        try:
            if workspace_id not in self._workspaces:
                return []
            
            workspace_path = Path(self._workspaces[workspace_id]["workspace_path"])
            files = []
            
            # List all files in workspace (recursively)
            for file_path in workspace_path.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    relative_path = file_path.relative_to(workspace_path)
                    files.append(FileInfo(
                        filename=file_path.name,
                        size=file_path.stat().st_size,
                        mime_type="application/octet-stream",
                        created_at=datetime.fromtimestamp(file_path.stat().st_ctime),
                        relative_path=str(relative_path),
                        download_url=f"file://{file_path.absolute()}"
                    ))
            
            return files
            
        except Exception as e:
            self.logger.error("Failed to list workspace files",
                            workspace_id=workspace_id,
                            error=str(e))
            return []
    
    async def delete_kernel(self, workspace_id: str) -> bool:
        """Delete kernel associated with workspace"""
        if workspace_id not in self._workspaces:
            self.logger.debug("Kernel deletion skipped - no workspace found",
                            workspace_id=workspace_id)
            return False
        
        workspace_info = self._workspaces[workspace_id]
        if "kernel_id" not in workspace_info:
            return False
        
        kernel_id = workspace_info["kernel_id"]
        
        self.logger.info("Deleting Jupyter kernel",
                        workspace_id=workspace_id,
                        kernel_id=kernel_id)
        
        try:
            # Shutdown kernel using proper jupyter_client
            await self.kernel_manager.shutdown_kernel(kernel_id)
            
            # Remove from tracking
            del self._workspaces[workspace_id]
            
            self.logger.info("Jupyter kernel deleted successfully",
                           workspace_id=workspace_id,
                           kernel_id=kernel_id,
                           remaining_kernels=len(self.kernel_manager))
            
            return True
            
        except Exception as e:
            self.logger.error("Jupyter kernel deletion failed",
                            workspace_id=workspace_id,
                            kernel_id=kernel_id,
                            error=str(e))
            raise JupyterClientError(f"Failed to delete kernel: {e}")
    
    async def cleanup_expired_kernels(self, max_idle_minutes: int = 60):
        """Clean up kernels that have been idle for too long"""
        now = datetime.utcnow()
        expired_workspaces = []
        
        for workspace_id, workspace_info in self._workspaces.items():
            if "last_activity" in workspace_info:
                last_activity = workspace_info["last_activity"]
                idle_time = now - last_activity
                
                if idle_time.total_seconds() > (max_idle_minutes * 60):
                    expired_workspaces.append(workspace_id)
        
        if expired_workspaces:
            self.logger.info("Found idle kernels for cleanup",
                           expired_count=len(expired_workspaces),
                           max_idle_minutes=max_idle_minutes,
                           total_kernels=len(self._workspaces))
        
        # Delete expired kernels
        cleaned_count = 0
        for workspace_id in expired_workspaces:
            try:
                await self.delete_kernel(workspace_id)
                cleaned_count += 1
            except Exception as e:
                self.logger.error("Failed to cleanup idle kernel",
                                exc=e,
                                workspace_id=workspace_id)
        
        if cleaned_count > 0:
            self.logger.info("Idle kernel cleanup completed",
                           cleaned_count=cleaned_count,
                           remaining_kernels=len(self._workspaces))
    
    def get_kernel_info(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Get kernel information for workspace"""
        workspace_info = self._workspaces.get(workspace_id)
        if workspace_info and "kernel_id" in workspace_info:
            return {
                "kernel_id": workspace_info["kernel_id"],
                "workspace_path": workspace_info["workspace_path"],
                "status": workspace_info.get("status"),
                "created_at": workspace_info.get("created_at"),
                "last_activity": workspace_info.get("last_activity")
            }
        return None
    
    def list_active_kernels(self) -> List[str]:
        """List all active workspace IDs with kernels"""
        return [ws_id for ws_id, info in self._workspaces.items() if "kernel_id" in info] 