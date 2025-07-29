#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Execution Service

High-level business logic for code execution in workspaces.
Handles execution requests and manages execution lifecycle.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from app.core.config import Settings
from app.domain.models import (
    ExecutionRequest, ExecutionResult, ExecutionStatus,
    WorkspaceStatus
)
from app.infrastructure.jupyter_kernel_client import (
    JupyterServerClient, WorkspaceNotFoundError, KernelNotFoundError
)
from app.services.workspace_service import WorkspaceService
from app.utils.logger import Loggers
from app.core.concurrency import ConcurrencyManager, ServiceUnavailableError
from app.core.events import get_event_bus, WorkspaceDeletedEvent


PREVIEW_CUTOFF_STDOUT = 1000
PREVIEW_CUTOFF_STDERR = 1000
PREVIEW_FULL_DATA = -1

def preview_data(data: str, cutoff: int) -> str:
    if cutoff == PREVIEW_FULL_DATA:
        return data
    else:
        return data[:cutoff] + ("..." if len(data) > cutoff else "")

class ExecutionService:
    """
    Service for managing code execution
    
    Handles execution requests, validates inputs, and coordinates
    with workspace and Jupyter services.
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
        self.logger = Loggers.execution_service
        
        # Track execution history
        self._executions: Dict[str, ExecutionResult] = {}
        
        # NOTE: Workspace locks are now managed by ConcurrencyManager
        # (removed old _workspace_locks implementation)
        
        # Track which workspaces have been warmed up
        self._warmed_workspaces: set = set()
        
        # Initialize concurrency manager for layered concurrency control
        self._concurrency_manager = ConcurrencyManager(
            max_concurrent_executions=settings.max_concurrent_executions,
            max_concurrent_requests=settings.max_queued_requests,
            circuit_breaker_threshold=settings.circuit_breaker_failure_threshold,
            circuit_recovery_timeout=settings.circuit_breaker_recovery_timeout,
            request_timeout_seconds=settings.request_timeout_seconds
        )
        
        # Event bus for clean service communication
        self.event_bus = get_event_bus()
        
        # NOTE: Cleanup now handled by centralized CleanupService
        # (removed individual cleanup task)
        
        # ✅ CLEAN: Subscribe to workspace deletion events
        self.event_bus.subscribe(WorkspaceDeletedEvent, self._handle_workspace_deleted)
        
        self.logger.info("Execution service initialized",
                        default_timeout=settings.default_execution_timeout,
                        max_timeout=settings.max_execution_timeout)
    
    # NOTE: Cleanup now handled by centralized CleanupService
    # (removed start/stop cleanup task methods)
    
    # NOTE: _cleanup_loop removed - now handled by centralized CleanupService
    
    async def execute_code(self, request: ExecutionRequest) -> ExecutionResult:
        """
        Execute code in a workspace with full concurrency control
        
        Args:
            request: Code execution request
            
        Returns:
            ExecutionResult with execution details
            
        Raises:
            WorkspaceNotFoundError: If workspace doesn't exist
            ValueError: If request validation fails
            ServiceUnavailableError: If system is overloaded
        """
        self.logger.info("Code execution requested",
                        workspace_id=request.workspace_id,
                        code_length=len(request.code),
                        timeout=request.timeout)
        
        # Validate request
        self._validate_execution_request(request)
        
        try:
            # Execute with layered concurrency control (all layers now centralized)
            return await self._concurrency_manager.execute_with_concurrency_control(
                request, self._execute_code_locked
            )
        except ServiceUnavailableError as e:
            # Convert to HTTP 503 compatible error
            self.logger.warning("Execution rejected due to system overload",
                              workspace_id=request.workspace_id,
                              reason=str(e))
            raise ValueError(f"Service temporarily unavailable: {e}")
    
    async def _execute_code_locked(self, request: ExecutionRequest) -> ExecutionResult:
        # Check workspace exists and is ready
        workspace_info = await self.workspace_service.get_workspace(request.workspace_id)
        if not workspace_info:
            self.logger.warning("Execution failed - workspace not found",
                              workspace_id=request.workspace_id)
            raise WorkspaceNotFoundError(f"Workspace {request.workspace_id} not found")
        
        if workspace_info.status == WorkspaceStatus.EXPIRED:
            raise WorkspaceNotFoundError(f"Workspace {request.workspace_id} has expired")
        
        if workspace_info.status != WorkspaceStatus.READY:
            raise ValueError(f"Workspace {request.workspace_id} is not ready (status: {workspace_info.status})")
        
        # Update workspace activity
        await self.workspace_service.update_workspace_activity(request.workspace_id)
        
        # Warm up kernel for consistent performance (only on first execution)
        if request.workspace_id not in self._warmed_workspaces:
            await self._ensure_kernel_ready(request.workspace_id)
            self._warmed_workspaces.add(request.workspace_id)
        
        # Execute code via Jupyter client
        self.logger.debug("Executing code in Jupyter kernel",
                         workspace_id=request.workspace_id,
                         kernel_id=workspace_info.kernel_id)
        
        # Log the actual code being executed (for debugging)
        code_preview = preview_data(request.code, 200)
        self.logger.info(f"📝 Code to execute: {code_preview}",
                        workspace_id=request.workspace_id)
        
        # Show full code in debug mode (be careful with sensitive code)
        self.logger.debug(f"📄 Full code content:\n{request.code}",
                         workspace_id=request.workspace_id)
        
        try:
            result = await self.jupyter_client.execute_code(
                workspace_id=request.workspace_id,
                code=request.code,
                timeout=request.timeout
            )
            
            # Store execution result
            self._executions[result.execution_id] = result
            
            # Handle timeout status - cleanup workspace
            if result.status == ExecutionStatus.TIMEOUT:
                self.logger.warning("Execution timed out - cleaning up workspace",
                                   workspace_id=request.workspace_id,
                                   elapsed_seconds=(result.execution_time_ms or 0) / 1000)
                
                cleanup_message = "Workspace has been destroyed due to timeout. Create a new workspace to continue."
                # ✅ CLEAN: Simple timeout cleanup via workspace service
                try:
                    await self.workspace_service.delete_workspace(request.workspace_id, reason="timeout")
                    # WorkspaceService will publish WorkspaceDeletedEvent
                    # We'll handle cleanup via our event subscriber
                except Exception as cleanup_error:
                    self.logger.error("Failed to cleanup timed out workspace", 
                                     workspace_id=request.workspace_id, 
                                     cleanup_error=str(cleanup_error))
                
                # Update result with cleanup message
                result = ExecutionResult(
                    workspace_id=result.workspace_id,
                    status=ExecutionStatus.TIMEOUT,
                    stderr=f"{result.stderr}\n{cleanup_message}",
                    execution_time_ms=result.execution_time_ms,
                    completed_at=result.completed_at
                )
                
                # Store updated result
                self._executions[result.execution_id] = result
            
            # Update workspace activity again after successful execution
            await self.workspace_service.update_workspace_activity(request.workspace_id)
            
            # Log detailed execution results
            self.logger.info("✅ Code execution completed",
                           workspace_id=request.workspace_id,
                           execution_id=result.execution_id,
                           status=result.status,
                           execution_time_ms=result.execution_time_ms,
                           stdout_length=len(result.stdout) if result.stdout else 0,
                           stderr_length=len(result.stderr) if result.stderr else 0,
                           output_count=len(result.outputs),
                           generated_files=len(result.generated_files))
            
            # Log actual outputs for debugging
            self.logger.debug("🎯 Execution outputs",
                            workspace_id=request.workspace_id,
                            output_types=[out.type for out in result.outputs])
            
            if result.stdout:
                stdout_preview = preview_data(result.stdout, PREVIEW_FULL_DATA)
                self.logger.debug(f"📤 Execution stdout:\n{stdout_preview}",
                                workspace_id=request.workspace_id)
            
            if result.stderr:
                stderr_preview = preview_data(result.stderr, PREVIEW_FULL_DATA)
                self.logger.debug(f"⚠️ Execution stderr:\n{stderr_preview}",
                                workspace_id=request.workspace_id)
            
            if result.outputs:
                self.logger.debug("🎯 Execution outputs",
                                workspace_id=request.workspace_id,
                                output_types=[out.type for out in result.outputs])  # Fixed: use 'type' not 'output_type'
            
            return result
            
        except WorkspaceNotFoundError:
            # Re-raise as is
            raise
        except KernelNotFoundError:
            # Kernel was deleted, mark workspace as error
            if workspace_info:
                workspace_info.status = WorkspaceStatus.ERROR
            raise WorkspaceNotFoundError(f"Execution environment for workspace {request.workspace_id} is not available")
        except Exception as e:
            self.logger.error("Code execution failed",
                            exc=e,
                            workspace_id=request.workspace_id,
                            code_length=len(request.code),
                            timeout=request.timeout,
                            error_type=e.__class__.__name__)
            
            # Create error result
            error_result = ExecutionResult(
                workspace_id=request.workspace_id,
                status=ExecutionStatus.FAILED,
                stderr=f"Execution failed: {str(e)}",
                completed_at=datetime.utcnow()
            )
            
            # Store error result
            self._executions[error_result.execution_id] = error_result
            
            return error_result
    
    async def _ensure_kernel_ready(self, workspace_id: str):
        """
        Ensure kernel is warmed up and ready for consistent execution performance.
        This helps prevent timing inconsistencies on first execution.
        """
        try:
            # Run a simple warm-up command that doesn't interfere with user code
            warmup_code = "import sys; _ = 1 + 1"  # Simple operation to wake up kernel
            
            self.logger.debug("Warming up kernel for consistent performance",
                            workspace_id=workspace_id)
            
            # Execute warm-up with short timeout
            await self.jupyter_client.execute_code(
                workspace_id=workspace_id,
                code=warmup_code,
                timeout=5  # Short timeout for warm-up
            )
            
        except Exception as e:
            # Warm-up failure shouldn't block execution, just log it
            self.logger.warning("Kernel warm-up failed, proceeding anyway",
                              workspace_id=workspace_id,
                              error=str(e))
    
    def _validate_execution_request(self, request: ExecutionRequest):
        """
        Validate execution request
        
        Args:
            request: Request to validate
            
        Raises:
            ValueError: If validation fails
        """
        # Check code length
        if len(request.code) > 50000:  # 50KB limit
            raise ValueError("Code too long (max 50KB)")
        
        # Check timeout limits
        if request.timeout > self.settings.max_execution_timeout:
            raise ValueError(f"Timeout too long (max {self.settings.max_execution_timeout}s)")
        
        # No code pattern restrictions for MVP - container isolation provides security
        # For production security patterns, see SECURITY_ROADMAP.md 
    
    async def get_execution_result(self, execution_id: str) -> Optional[ExecutionResult]:
        """
        Get execution result by ID
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            ExecutionResult if found, None otherwise
        """
        return self._executions.get(execution_id)
    
    async def list_workspace_executions(self, workspace_id: str, limit: int = 50) -> List[ExecutionResult]:
        """
        List executions for a workspace
        
        Args:
            workspace_id: Workspace identifier
            limit: Maximum number of results
            
        Returns:
            List of execution results for the workspace
        """
        workspace_executions = [
            result for result in self._executions.values()
            if result.workspace_id == workspace_id
        ]
        
        # Sort by start time (newest first) and limit
        workspace_executions.sort(key=lambda x: x.started_at, reverse=True)
        return workspace_executions[:limit]
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics
        
        Returns:
            Dictionary with execution statistics
        """
        total_executions = len(self._executions)
        
        status_counts = {
            ExecutionStatus.COMPLETED: 0,
            ExecutionStatus.FAILED: 0,
            ExecutionStatus.TIMEOUT: 0,
            ExecutionStatus.PENDING: 0,
            ExecutionStatus.RUNNING: 0
        }
        
        total_execution_time = 0
        execution_times = []
        
        for result in self._executions.values():
            status_counts[result.status] += 1
            
            if result.execution_time_ms:
                total_execution_time += result.execution_time_ms
                execution_times.append(result.execution_time_ms)
        
        # Calculate average execution time
        avg_execution_time = 0
        if execution_times:
            avg_execution_time = sum(execution_times) / len(execution_times)
        
        return {
            "total_executions": total_executions,
            "status_counts": dict(status_counts),
            "total_execution_time_ms": total_execution_time,
            "average_execution_time_ms": round(avg_execution_time, 2),
            "success_rate": round(
                status_counts[ExecutionStatus.COMPLETED] / max(total_executions, 1) * 100, 2
            ),
            "concurrency_stats": self._concurrency_manager.get_system_stats(),
            "event_bus_stats": self.event_bus.get_stats()
        }
    
    async def cleanup_old_executions(self, max_age_hours: int = 24) -> int:
        """
        Clean up old execution results to prevent memory leaks (time-based cleanup)
        
        This is now mainly a safety net since event-driven cleanup handles
        most execution cleanup when workspaces are deleted.
        
        Args:
            max_age_hours: Maximum age of executions to keep
            
        Returns:
            Number of executions cleaned up
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        old_execution_ids = []
        
        for execution_id, result in self._executions.items():
            if result.started_at < cutoff_time:
                old_execution_ids.append(execution_id)
        
        # Remove old executions
        for execution_id in old_execution_ids:
            del self._executions[execution_id]
        
        if old_execution_ids:
            self.logger.info("Time-based execution cleanup completed",
                           cleaned_executions=len(old_execution_ids))
        
        return len(old_execution_ids)
    
    def cleanup_workspace_executions(self, workspace_id: str) -> int:
        """
        Clean up all execution results for a specific workspace (event-driven cleanup)
        
        Args:
            workspace_id: Workspace ID to clean up executions for
            
        Returns:
            Number of executions cleaned up
        """
        execution_ids_to_remove = []
        
        # Find all executions for this workspace
        for execution_id, result in self._executions.items():
            if result.workspace_id == workspace_id:
                execution_ids_to_remove.append(execution_id)
        
        # Remove them
        for execution_id in execution_ids_to_remove:
            del self._executions[execution_id]
        
        if execution_ids_to_remove:
            self.logger.info("Cleaned up workspace executions (event-driven)",
                           workspace_id=workspace_id,
                           execution_count=len(execution_ids_to_remove))
        
        return len(execution_ids_to_remove)


    
    def _handle_workspace_deleted(self, event: WorkspaceDeletedEvent):
        """
        Handle workspace deletion events (clean event-driven approach)
        
        Args:
            event: WorkspaceDeletedEvent containing workspace_id and reason
        """
        # 1. Clean up local execution service state
        self._warmed_workspaces.discard(event.workspace_id)
        
        # 2. ✅ EVENT-DRIVEN: Clean up ALL executions for this workspace immediately
        cleaned_executions = self.cleanup_workspace_executions(event.workspace_id)
        
        # 3. Clean up concurrency manager state
        self._concurrency_manager.notify_workspace_deleted(event.workspace_id)
        
        self.logger.debug("Handled workspace deletion event",
                         workspace_id=event.workspace_id,
                         reason=event.reason,
                         cleaned_executions=cleaned_executions) 