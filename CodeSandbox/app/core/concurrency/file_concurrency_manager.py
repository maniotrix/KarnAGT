#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File Concurrency Manager

Main orchestrator for file operation concurrency control.
Provides a unified interface for layered file concurrency control.
"""

import asyncio
from typing import TypeVar, Optional, Callable, Any, Awaitable

from .admission_controller import AdmissionController
from .circuit_breaker import CircuitBreaker, CircuitBreakerError
from .resource_manager import ResourceManager
from .file_lock_manager import FileLockManager
from app.domain.models import FileRequest
from app.utils.logger import Loggers

T = TypeVar('T')

class FileServiceUnavailableError(Exception):
    """File service is temporarily unavailable"""
    pass

class FileConcurrencyManager:
    """
    Unified file concurrency control manager
    
    Orchestrates all file concurrency primitives:
    - File locks (Layer 1)
    - Resource management (Layer 2)
    - Admission control (Layer 3)
    - Circuit breaker (Layer 4)
    """
    
    def __init__(
        self,
        max_concurrent_file_operations: int = 15,  # Lower than code executions
        max_concurrent_requests: int = 40,         # Lower than code execution queue
        circuit_breaker_threshold: int = 8,        # Higher tolerance for file errors
        circuit_recovery_timeout: int = 20,        # Faster recovery than executions
        request_timeout_seconds: int = 180         # 3 minutes for large files
    ):
        # Initialize all concurrency components for file operations
        self.admission_controller = AdmissionController[FileRequest](
            max_concurrent_requests=max_concurrent_requests
        )
        
        self.resource_manager = ResourceManager(
            max_concurrent_executions=max_concurrent_file_operations
        )
        
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_breaker_threshold,
            recovery_timeout=circuit_recovery_timeout,
            resource_manager=self.resource_manager
        )
        
        self.file_lock_manager = FileLockManager()  # Custom file locks
        
        # Timeout configuration
        self.request_timeout_seconds = request_timeout_seconds
        
        self.logger = Loggers.file_concurrency_manager
        
        self.logger.info("File concurrency manager initialized",
                        max_concurrent_file_ops=max_concurrent_file_operations,
                        max_concurrent_requests=max_concurrent_requests,
                        circuit_threshold=circuit_breaker_threshold,
                        request_timeout=request_timeout_seconds)
    
    async def execute_with_file_concurrency_control(
        self,
        request: FileRequest,
        file_operation_func: Callable[..., Awaitable[T]]
    ) -> T:
        """
        Execute file operation with full concurrency control
        
        Args:
            request: File operation request
            file_operation_func: Function to execute
            
        Returns:
            File operation result
            
        Raises:
            FileServiceUnavailableError: If system is overloaded
            CircuitBreakerError: If circuit breaker is open
            asyncio.TimeoutError: If request times out
        """
        # LAYER 3: Admission Control - Check if system can accept request
        if not await self.admission_controller.acquire_admission():
            self.admission_controller._rejected_requests += 1
            raise FileServiceUnavailableError(
                "File service overloaded - too many concurrent file operations"
            )
        
        # Track admission
        self.admission_controller._total_requests += 1
        
        try:
            # Apply timeout to the entire file operation
            result = await asyncio.wait_for(
                self.circuit_breaker.call(  # type: ignore[misc]
                    self._execute_file_with_resources,
                    request,  # Pass the original request
                    file_operation_func
                ),
                timeout=self.request_timeout_seconds
            )
            return result  # type: ignore[return-value]
                
        except asyncio.TimeoutError:
            self.logger.warning("File operation timed out",
                              workspace_id=request.workspace_id,
                              file_name=request.filename,
                              operation=request.operation.value,
                              timeout_seconds=self.request_timeout_seconds)
            raise FileServiceUnavailableError(
                f"File operation timed out after {self.request_timeout_seconds} seconds"
            )
        except CircuitBreakerError as e:
            self.logger.warning("Circuit breaker blocked file operation", 
                              workspace_id=request.workspace_id,
                              file_name=request.filename,
                              operation=request.operation.value,
                              circuit_error=str(e))
            raise FileServiceUnavailableError(
                "File service temporarily unavailable - circuit breaker is open"
            )
        finally:
            # Always release admission slot
            await self.admission_controller.release_admission()
    
    async def _execute_file_with_resources(
        self,
        request: FileRequest,
        file_operation_func: Callable[[FileRequest], Awaitable[T]]
    ) -> T:
        """
        Execute with resource management and file locks (Layers 1 & 2)
        
        Args:
            request: File operation request
            file_operation_func: Function to execute
            
        Returns:
            File operation result
        """
        # LAYER 2: Resource Management
        async with self.resource_manager:
            self.logger.debug("Executing file operation with resource control",
                            workspace_id=request.workspace_id,
                            file_name=request.filename,
                            operation=request.operation.value,
                            active_operations=self.resource_manager._current_active)
            
            # LAYER 1: File-Level Isolation
            return await self.file_lock_manager.execute_with_file_lock(
                request.workspace_id,
                request.filename,
                file_operation_func,
                request
            )
    
    def get_system_stats(self) -> dict:
        """Get comprehensive file concurrency statistics"""
        return {
            "file_locks": self.file_lock_manager.get_stats(),
            "file_resource_manager": self.resource_manager.get_stats(),
            "file_admission_controller": self.admission_controller.get_stats(),
            "file_circuit_breaker": self.circuit_breaker.get_stats(),
            "file_system_health": {
                "file_request_utilization": (
                    self.admission_controller.current_requests() / 
                    self.admission_controller.max_concurrent_requests * 100
                ),
                "file_resource_utilization": self.resource_manager.utilization_percentage(),
                "file_circuit_healthy": self.circuit_breaker.state.value == "closed"
            }
        }
    
    def is_system_healthy(self) -> bool:
        """Check if file system is healthy and can accept requests"""
        return (
            not self.admission_controller.is_at_capacity() and
            self.circuit_breaker.state.value != "open" and
            not self.resource_manager.is_at_capacity()
        )
    
    def notify_workspace_deleted(self, workspace_id: str):
        """
        Notify file concurrency manager that a workspace was deleted
        
        This ensures proper cleanup of file locks and prevents
        memory leaks when workspaces are deleted by other services.
        
        Args:
            workspace_id: ID of the deleted workspace
        """
        # Clean up file lock state for this workspace
        cleaned_count = self.file_lock_manager.cleanup_workspace_locks(workspace_id)
        
        if cleaned_count > 0:
            self.logger.info("Cleaned up file locks for deleted workspace",
                           workspace_id=workspace_id,
                           cleaned_locks=cleaned_count)
    
    async def periodic_cleanup(self, max_idle_minutes: int = 60):
        """
        Perform periodic cleanup of stale file concurrency state
        
        Args:
            max_idle_minutes: Maximum idle time before cleanup
            
        Returns:
            Number of items cleaned up
        """
        total_cleaned = 0
        
        try:
            # 1. Clean up expired file locks
            cleaned_locks = self.file_lock_manager.cleanup_expired_locks(max_idle_minutes)
            total_cleaned += cleaned_locks
        except Exception as e:
            self.logger.error("Error cleaning up file locks", exc=e)
        
        try:
            # 2. Clean up old admission controller metrics (prevent memory growth)
            if len(self.admission_controller._request_start_times) > 1000:
                # Keep only last 1000 start time measurements
                self.admission_controller._request_start_times = self.admission_controller._request_start_times[-1000:]
                self.logger.debug("Trimmed file admission controller metrics")
        except Exception as e:
            self.logger.error("Error trimming file admission controller metrics", exc=e)
        
        if total_cleaned > 0:
            self.logger.info("File concurrency periodic cleanup completed",
                           cleaned_locks=total_cleaned,
                           total_cleaned=total_cleaned)
        
        return total_cleaned 