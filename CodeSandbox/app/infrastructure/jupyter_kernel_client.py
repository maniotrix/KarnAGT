#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Jupyter Client Integration

Uses jupyter_client library directly instead of manual HTTP requests.
Much simpler and more reliable approach.
"""

import asyncio
import os
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
        
        # Configure a dedicated runtime directory for Jupyter connection files
        self._jupyter_runtime_dir = Path(self.settings.user_temp_base_path) / "jupyter_runtime"
        self._jupyter_runtime_dir.mkdir(parents=True, exist_ok=True)

        # Propagate to environment for any child processes (optional, helps external tools)
        os.environ["JUPYTER_RUNTIME_DIR"] = str(self._jupyter_runtime_dir)

        # Use AsyncMultiKernelManager with explicit connection_dir so files are placed there
        self.kernel_manager = AsyncMultiKernelManager(connection_dir=str(self._jupyter_runtime_dir))
        
        # Track workspace directories and kernels
        self._workspaces: Dict[str, Dict[str, Any]] = {}
        self._workspace_base = Path(self.settings.workspace_base_path)
        
        self.logger.info("Jupyter client initialized using jupyter_client library",
                        workspace_base=str(self._workspace_base))
    
    async def initialize_workspace_directory(self):
        """Initialize required directories during application startup"""
        try:
            self.logger.info("Initializing workspace directories")
            
            # Create the main 'workspaces' directory locally (create parents too)
            self._workspace_base.mkdir(parents=True, exist_ok=True)
            
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
            # Ensure workspace and outputs directories exist (create parents just in case)
            workspace_path.mkdir(parents=True, exist_ok=True)
            (workspace_path / "outputs").mkdir(parents=True, exist_ok=True)
            
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
        kernel_id = workspace_info["kernel_id"]
        execution_timeout = timeout or self.settings.default_execution_timeout
        
        self.logger.debug("Executing code in kernel using jupyter_client",
                         workspace_id=workspace_id,
                         kernel_id=kernel_id,
                         code_length=len(code),
                         timeout=execution_timeout)
        
        # Update last activity
        workspace_info["last_activity"] = datetime.utcnow()
        
        start_time = datetime.utcnow()
        
        try:
            # Execute code using proper jupyter_client - much simpler!
            self.logger.debug("🚀 Sending code to kernel",
                            workspace_id=workspace_id,
                            kernel_id=kernel_id)
            
            msg_id = kernel_client.execute(code)
            
            self.logger.debug("📨 Execution message sent",
                            workspace_id=workspace_id,
                            msg_id=msg_id)
            
            # Collect execution results with proper timeout enforcement
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
                        'content': content.get('data', {}),  # Use 'content' field as expected by ExecutionOutput model
                        # Note: metadata is not stored separately but could be included in content if needed
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
                     
            # Check if execution timed out (soft timeout from _collect_execution_results)
            current_time = datetime.utcnow()
            elapsed_time = (current_time - start_time).total_seconds()
            
            if elapsed_time >= execution_timeout:
                # Execution timed out - return timeout result
                self.logger.warning("Execution timed out",
                                  workspace_id=workspace_id,
                                  kernel_id=kernel_id,
                                  elapsed_time=elapsed_time,
                                  timeout=execution_timeout)
                
                # Return timeout result
                execution_time_ms = int(elapsed_time * 1000)
                return ExecutionResult(
                    workspace_id=workspace_id,
                    status=ExecutionStatus.TIMEOUT,
                    stderr=f"Execution timed out after {elapsed_time:.1f} seconds",
                    execution_time_ms=execution_time_ms,
                    completed_at=current_time
                )
            
            # Filter out unmodified uploaded files from generated_files
            filtered_generated_files = await self._filter_generated_files(workspace_id)
            
            execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return ExecutionResult(
                workspace_id=workspace_id,
                status=ExecutionStatus.COMPLETED,
                stdout="".join(stdout_lines),
                stderr="".join(stderr_lines),
                outputs=[ExecutionOutput(**output) for output in outputs],
                result_data=None,
                generated_files=filtered_generated_files,
                execution_time_ms=execution_time_ms,
                completed_at=datetime.utcnow()
            )
            
        except asyncio.TimeoutError:
            # This shouldn't happen with the inner timeout, but just in case
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
                            kernel_id=kernel_id,
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
            
            # Add to uploaded files list
            self._add_uploaded_file(workspace_id, filename)
            
            return FileInfo(
                filename=filename,
                size=len(content),
                mime_type=self._get_mime_type(filename),
                created_at=datetime.utcnow(),
                relative_path=filename,
                download_url=""  # No URL generation at infrastructure layer
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
                        mime_type=self._get_mime_type(str(relative_path)),
                        created_at=datetime.fromtimestamp(file_path.stat().st_ctime),
                        relative_path=relative_path.as_posix(),  # Use forward slashes consistently
                        download_url=""  # No URL generation at infrastructure layer
                    ))
            
            return files
            
        except Exception as e:
            self.logger.error("Failed to list workspace files",
                            workspace_id=workspace_id,
                            error=str(e))
            return []
    
    async def _filter_generated_files(self, workspace_id: str) -> List[FileInfo]:
        """
        Filter files to only include truly generated files (excludes unmodified uploaded files)
        
        Args:
            workspace_id: Workspace identifier            
        Returns:
            List of files that were generated or modified by code execution
        """
        # Get generated files
        all_files = await self._get_workspace_files(workspace_id)
        uploaded_files_metadata = self._read_uploaded_files(workspace_id)
        workspace_path = Path(self._workspaces[workspace_id]["workspace_path"])
        
        filtered_files = []
        for file in all_files:
            if file.relative_path not in uploaded_files_metadata:
                # File was never uploaded, definitely generated
                filtered_files.append(file)
            else:
                # File was uploaded, check if it was modified
                try:
                    stored_metadata = uploaded_files_metadata[file.relative_path]
                    current_file_path = workspace_path / file.relative_path
                    current_stat = current_file_path.stat()
                    
                    # Check if mtime or size changed
                    if (current_stat.st_mtime != stored_metadata["mtime"] or 
                        current_stat.st_size != stored_metadata["size"]):
                        # File was modified by code execution
                        filtered_files.append(file)
                        self.logger.debug("Uploaded file was modified by execution",
                                        workspace_id=workspace_id,
                                        file_path=file.relative_path,
                                        old_mtime=stored_metadata["mtime"],
                                        new_mtime=current_stat.st_mtime,
                                        old_size=stored_metadata["size"],
                                        new_size=current_stat.st_size)
                    # else: File unchanged, exclude from generated_files
                except (OSError, KeyError) as e:
                    # File might have been deleted or metadata corrupted, treat as generated
                    filtered_files.append(file)
                    self.logger.debug("Could not check file modification, treating as generated",
                                    workspace_id=workspace_id,
                                    file_path=file.relative_path,
                                    error=str(e))
        
        return filtered_files
    
    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type for file based on extension"""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or "application/octet-stream"
    
    def _get_uploaded_files_path(self, workspace_id: str) -> Path:
        """Get path to the .uploaded_files tracking file"""
        if workspace_id not in self._workspaces:
            raise WorkspaceNotFoundError(f"Workspace {workspace_id} not found")
        workspace_path = Path(self._workspaces[workspace_id]["workspace_path"])
        return workspace_path / ".uploaded_files"
    
    def _read_uploaded_files(self, workspace_id: str) -> Dict[str, Dict[str, Any]]:
        """Read uploaded files metadata from .uploaded_files"""
        try:
            uploaded_files_path = self._get_uploaded_files_path(workspace_id)
            if uploaded_files_path.exists():
                import json
                return json.loads(uploaded_files_path.read_text())
            return {}
        except Exception as e:
            self.logger.warning("Failed to read uploaded files list",
                              workspace_id=workspace_id,
                              error=str(e))
            return {}
    
    def _write_uploaded_files(self, workspace_id: str, uploaded_files: Dict[str, Dict[str, Any]]):
        """Write uploaded files metadata to .uploaded_files"""
        try:
            uploaded_files_path = self._get_uploaded_files_path(workspace_id)
            import json
            uploaded_files_path.write_text(json.dumps(uploaded_files, indent=2))
            self.logger.debug("Updated uploaded files list",
                            workspace_id=workspace_id,
                            uploaded_count=len(uploaded_files))
        except Exception as e:
            self.logger.error("Failed to write uploaded files list",
                            exc=e,
                            workspace_id=workspace_id)
    
    def _add_uploaded_file(self, workspace_id: str, relative_path: str):
        """Add a file to the uploaded files list with metadata"""
        try:
            # Get file metadata
            workspace_path = Path(self._workspaces[workspace_id]["workspace_path"])
            file_path = workspace_path / relative_path
            file_stat = file_path.stat()
            
            # Read current uploaded files
            uploaded_files = self._read_uploaded_files(workspace_id)
            
            # Add/update file metadata
            from datetime import datetime
            uploaded_files[relative_path] = {
                "uploaded_at": datetime.utcnow().isoformat(),
                "mtime": file_stat.st_mtime,
                "size": file_stat.st_size
            }
            
            # Write back to file
            self._write_uploaded_files(workspace_id, uploaded_files)
            
            self.logger.debug("Added uploaded file with metadata",
                            workspace_id=workspace_id,
                            file_path=relative_path,
                            mtime=file_stat.st_mtime,
                            size=file_stat.st_size)
            
        except Exception as e:
            self.logger.error("Failed to add uploaded file metadata",
                            exc=e,
                            workspace_id=workspace_id,
                            file_path=relative_path)
    
    async def delete_kernel(self, workspace_id: str) -> bool:
        """
        Delete kernel associated with workspace with improved error handling
        
        Enhanced to handle:
        - Already deleted kernels gracefully
        - ZMQ context cleanup issues
        - Timeout scenarios
        - Partial cleanup states
        """
        try:
            # Check if workspace exists - if not, consider it already cleaned
            if workspace_id not in self._workspaces:
                self.logger.debug("Kernel deletion skipped - workspace already cleaned",
                                workspace_id=workspace_id)
                return True  # Already deleted, return success
            
            workspace_info = self._workspaces[workspace_id]
            
            # If no kernel_id, just clean up workspace info
            if "kernel_id" not in workspace_info:
                self.logger.debug("Kernel deletion - no kernel to delete, cleaning workspace info",
                                workspace_id=workspace_id)
                del self._workspaces[workspace_id]
                self._cleanup_workspace_files(workspace_id)
                return True
            
            kernel_id = workspace_info["kernel_id"]
            
            self.logger.info("Deleting Jupyter kernel",
                            workspace_id=workspace_id,
                            kernel_id=kernel_id)
            
            # Step 1: Graceful kernel shutdown with timeout
            try:
                await asyncio.wait_for(
                    self.kernel_manager.shutdown_kernel(kernel_id), 
                    timeout=5.0
                )
                self.logger.debug("Kernel shutdown completed gracefully",
                                workspace_id=workspace_id,
                                kernel_id=kernel_id)
            except asyncio.TimeoutError:
                self.logger.warning("Kernel shutdown timeout, attempting force shutdown",
                               workspace_id=workspace_id,
                               kernel_id=kernel_id)
                try:
                    # Force shutdown
                    await self.kernel_manager.shutdown_kernel(kernel_id, now=True)
                except Exception as force_error:
                    self.logger.warning("Force shutdown also failed, proceeding with cleanup",
                                      workspace_id=workspace_id,
                                      kernel_id=kernel_id,
                                      error=str(force_error))
            except Exception as shutdown_error:
                self.logger.warning("Kernel shutdown failed, proceeding with cleanup",
                                  workspace_id=workspace_id,
                                  kernel_id=kernel_id,
                                  error=str(shutdown_error))
            
            # Step 2: Always clean up tracking (even if shutdown failed)
            try:
                del self._workspaces[workspace_id]
                self.logger.debug("Workspace tracking cleaned up",
                                workspace_id=workspace_id)
            except KeyError:
                # Already removed, that's fine
                pass
            
            # Step 3: Clean up workspace files
            self._cleanup_workspace_files(workspace_id)
            
            self.logger.info("Kernel cleanup completed",
                           workspace_id=workspace_id,
                           kernel_id=kernel_id,
                           remaining_kernels=len(self._workspaces))
            
            return True
            
        except Exception as e:
            # Log error but don't re-raise - cleanup should be fault-tolerant
            self.logger.error("Kernel cleanup encountered unexpected error",
                            workspace_id=workspace_id,
                            error=str(e),
                            error_type=type(e).__name__)
            
            # Still attempt to clean up tracking to prevent memory leaks
            try:
                self._workspaces.pop(workspace_id, None)
                self._cleanup_workspace_files(workspace_id)
                self.logger.info("Emergency cleanup completed despite errors",
                               workspace_id=workspace_id)
            except Exception as cleanup_error:
                self.logger.error("Emergency cleanup also failed",
                                workspace_id=workspace_id,
                                cleanup_error=str(cleanup_error))
            
            return False
    
    def _cleanup_workspace_files(self, workspace_id: str) -> None:
        """Clean up entire workspace directory and all files"""
        import shutil
        
        # Always initialize workspace_path
        workspace_path = None
        
        try:
            # Try to get path from tracking first
            if workspace_id in self._workspaces:
                workspace_path = Path(self._workspaces[workspace_id]["workspace_path"])
            else:
                # Fallback: construct path manually if not in tracking
                workspace_path = self._workspace_base / workspace_id
            
            if workspace_path and workspace_path.exists():
                # Log what we're about to delete
                try:
                    # Get directory size for logging
                    total_size = sum(f.stat().st_size for f in workspace_path.rglob('*') if f.is_file())
                    file_count = len(list(workspace_path.rglob('*')))
                    
                    self.logger.info("Removing entire workspace directory",
                                   workspace_id=workspace_id,
                                   workspace_path=str(workspace_path),
                                   total_files=file_count,
                                   total_size_bytes=total_size)
                except Exception:
                    # Don't fail cleanup if we can't get stats
                    self.logger.info("Removing workspace directory",
                                   workspace_id=workspace_id,
                                   workspace_path=str(workspace_path))
                
                # Remove entire directory tree
                shutil.rmtree(workspace_path, ignore_errors=False)
                
                # Verify deletion was successful
                if workspace_path.exists():
                    self.logger.warning("Workspace directory still exists after deletion attempt",
                                      workspace_id=workspace_id,
                                      workspace_path=str(workspace_path))
                    # Try with ignore_errors=True as fallback
                    shutil.rmtree(workspace_path, ignore_errors=True)
                else:
                    self.logger.info("Workspace directory successfully removed",
                                   workspace_id=workspace_id,
                                   workspace_path=str(workspace_path))
            else:
                self.logger.debug("Workspace directory not found, nothing to clean",
                                workspace_id=workspace_id,
                                workspace_path=str(workspace_path) if workspace_path else "unknown")
                
        except PermissionError as e:
            self.logger.error("Permission error during workspace cleanup",
                            workspace_id=workspace_id,
                            error=str(e))
            # Try alternative cleanup approaches
            try:
                # Try to at least clear the contents
                if workspace_path is not None and workspace_path.exists():
                    for item in workspace_path.iterdir():
                        try:
                            if item.is_file():
                                item.unlink()
                            elif item.is_dir():
                                shutil.rmtree(item, ignore_errors=True)
                        except Exception:
                            continue
                    # Try to remove the empty directory
                    workspace_path.rmdir()
            except Exception as fallback_error:
                self.logger.error("Alternative cleanup also failed",
                                workspace_id=workspace_id,
                                fallback_error=str(fallback_error))
                
        except Exception as e:
            self.logger.error("Workspace directory cleanup failed",
                            workspace_id=workspace_id,
                            error=str(e),
                            error_type=type(e).__name__)
            # Don't raise - cleanup should be fault-tolerant, but try one more approach
            try:
                if workspace_path is not None and workspace_path.exists():
                    shutil.rmtree(workspace_path, ignore_errors=True)
            except Exception:
                pass  # Final fallback - just continue
    
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