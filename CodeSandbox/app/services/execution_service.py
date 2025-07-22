#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Execution Service

High-level business logic for code execution in workspaces.
Handles execution requests and manages execution lifecycle.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from app.core.config import Settings
from app.domain.models import (
    ExecutionRequest, ExecutionResult, ExecutionStatus,
    WorkspaceStatus
)
from app.infrastructure.jupyter_client import (
    JupyterServerClient, WorkspaceNotFoundError, KernelNotFoundError
)
from app.services.workspace_service import WorkspaceService


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
        
        # Track execution history
        self._executions: Dict[str, ExecutionResult] = {}
    
    async def execute_code(self, request: ExecutionRequest) -> ExecutionResult:
        """
        Execute code in a workspace
        
        Args:
            request: Code execution request
            
        Returns:
            ExecutionResult with execution details
            
        Raises:
            WorkspaceNotFoundError: If workspace doesn't exist
            ValueError: If request validation fails
        """
        # Validate request
        self._validate_execution_request(request)
        
        # Check workspace exists and is ready
        workspace_info = await self.workspace_service.get_workspace(request.workspace_id)
        if not workspace_info:
            raise WorkspaceNotFoundError(f"Workspace {request.workspace_id} not found")
        
        if workspace_info.status == WorkspaceStatus.EXPIRED:
            raise WorkspaceNotFoundError(f"Workspace {request.workspace_id} has expired")
        
        if workspace_info.status != WorkspaceStatus.READY:
            raise ValueError(f"Workspace {request.workspace_id} is not ready (status: {workspace_info.status})")
        
        # Update workspace activity
        await self.workspace_service.update_workspace_activity(request.workspace_id)
        
        # Execute code via Jupyter client
        try:
            result = await self.jupyter_client.execute_code(
                workspace_id=request.workspace_id,
                code=request.code,
                timeout=request.timeout
            )
            
            # Store execution result
            self._executions[result.execution_id] = result
            
            # Update workspace activity again after successful execution
            await self.workspace_service.update_workspace_activity(request.workspace_id)
            
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
        
        # Check for obviously dangerous code patterns
        dangerous_patterns = [
            "import subprocess",
            "import os",
            "os.system",
            "eval(",
            "exec(",
            "__import__"
        ]
        
        code_lower = request.code.lower()
        for pattern in dangerous_patterns:
            if pattern.lower() in code_lower:
                raise ValueError(f"Potentially dangerous code pattern detected: {pattern}")
    
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
            )
        }
    
    async def cleanup_old_executions(self, max_age_hours: int = 24):
        """
        Clean up old execution results to prevent memory leaks
        
        Args:
            max_age_hours: Maximum age of executions to keep
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
            print(f"Cleaned up {len(old_execution_ids)} old execution results") 