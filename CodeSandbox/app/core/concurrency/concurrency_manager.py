#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Concurrency Manager

Main orchestrator for all concurrency control components.
Provides a unified interface for layered concurrency control.
"""

import asyncio
from typing import TypeVar, Optional, Callable, Any, Union, Coroutine, Awaitable

from .admission_controller import AdmissionController
from .circuit_breaker import CircuitBreaker, CircuitBreakerError
from .resource_manager import ResourceManager
from .workspace_lock_manager import WorkspaceLockManager
from app.domain.models import ExecutionRequest
from app.utils.logger import Loggers

T = TypeVar('T')

class ServiceUnavailableError(Exception):
    """Service is temporarily unavailable"""
    pass

class ConcurrencyManager:
    """
    Unified concurrency control manager
    
    Orchestrates all concurrency primitives:
    - Workspace locks (Layer 1)
    - Resource management (Layer 2)
    - Admission control (Layer 3)
    - Circuit breaker (Layer 4)
    """
    
    def __init__(
        self,
        max_concurrent_executions: Optional[int] = None,
        max_queue_size: int = 100,
        circuit_breaker_threshold: int = 5,
        circuit_recovery_timeout: int = 60
    ):
        # Initialize all concurrency components
        self.admission_controller = AdmissionController[ExecutionRequest](
            max_queue_size=max_queue_size
        )
        
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_breaker_threshold,
            recovery_timeout=circuit_recovery_timeout
        )
        
        self.resource_manager = ResourceManager(
            max_concurrent_executions=max_concurrent_executions
        )
        
        self.workspace_lock_manager = WorkspaceLockManager()
        
        self.logger = Loggers.concurrency_manager
        
        self.logger.info("Concurrency manager initialized",
                        max_concurrent=max_concurrent_executions,
                        max_queue_size=max_queue_size,
                        circuit_threshold=circuit_breaker_threshold)
    
    async def execute_with_concurrency_control(
        self,
        request: ExecutionRequest,
        execution_func: Callable[..., Awaitable[T]]
    ) -> T:
        """
        Execute request with full concurrency control
        
        Args:
            request: Execution request
            execution_func: Function to execute
            
        Returns:
            Execution result
            
        Raises:
            ServiceUnavailableError: If system is overloaded
            CircuitBreakerError: If circuit breaker is open
        """
        # LAYER 3: Admission Control
        admitted = await self.admission_controller.admit_request(
            request, timeout=1.0
        )
        
        if not admitted:
            raise ServiceUnavailableError(
                "System overloaded - request queue is full"
            )
        
        # Get request from queue (will be immediate since we just added it)
        queued_request = await self.admission_controller.get_next_request()
        
        # LAYER 4: Circuit Breaker Protection
        try:
            result = await self.circuit_breaker.call(  # type: ignore[misc]
                self._execute_with_resources,
                queued_request,
                execution_func
            )
            return result  # type: ignore[return-value]
            
        except CircuitBreakerError:
            raise ServiceUnavailableError(
                "Service temporarily unavailable - circuit breaker is open"
            )
    
    async def _execute_with_resources(
        self,
        request: ExecutionRequest,
        execution_func: Callable[[ExecutionRequest], Awaitable[T]]
    ) -> T:
        """
        Execute with resource management and workspace locks (Layers 1 & 2)
        
        Args:
            request: Execution request
            execution_func: Function to execute
            
        Returns:
            Execution result
        """
        # LAYER 2: Resource Management
        async with self.resource_manager:
            self.logger.debug("Executing with resource control",
                            workspace_id=request.workspace_id,
                            active_executions=self.resource_manager._current_active)
            
            # LAYER 1: Workspace Isolation
            return await self.workspace_lock_manager.execute_with_workspace_lock(
                request.workspace_id,
                execution_func,
                request
            )
    
    def get_system_stats(self) -> dict:
        """Get comprehensive concurrency statistics"""
        return {
            "workspace_locks": self.workspace_lock_manager.get_stats(),
            "resource_manager": self.resource_manager.get_stats(),
            "admission_controller": self.admission_controller.get_stats(),
            "circuit_breaker": self.circuit_breaker.get_stats(),
            "system_health": {
                "queue_utilization": (
                    self.admission_controller.queue_size() / 
                    self.admission_controller.max_queue_size * 100
                ),
                "resource_utilization": self.resource_manager.utilization_percentage(),
                "circuit_healthy": self.circuit_breaker.state.value == "closed"
            }
        }
    
    def is_system_healthy(self) -> bool:
        """Check if system is healthy and can accept requests"""
        return (
            not self.admission_controller.is_queue_full() and
            self.circuit_breaker.state.value != "open" and
            not self.resource_manager.is_at_capacity()
        )
    
    def notify_workspace_deleted(self, workspace_id: str):
        """
        Notify concurrency manager that a workspace was deleted
        
        This ensures proper cleanup of workspace locks and prevents
        memory leaks when workspaces are deleted by other services.
        
        Args:
            workspace_id: ID of the deleted workspace
        """
        # Clean up workspace lock state
        if workspace_id in self.workspace_lock_manager._workspace_locks:
            lock = self.workspace_lock_manager._workspace_locks[workspace_id]
            
            # Only remove if not currently locked (safety check)
            if not lock.locked():
                del self.workspace_lock_manager._workspace_locks[workspace_id]
                self.workspace_lock_manager._active_workspaces.pop(workspace_id, None)
                
                self.logger.info("Cleaned up workspace lock for deleted workspace",
                               workspace_id=workspace_id)
            else:
                self.logger.warning("Cannot cleanup workspace lock - currently in use",
                                  workspace_id=workspace_id)
    
    async def periodic_cleanup(self, max_idle_minutes: int = 60):
        """
        Perform periodic cleanup of stale concurrency state
        
        Args:
            max_idle_minutes: Maximum idle time before cleanup
            
        Returns:
            Number of items cleaned up
        """
        total_cleaned = 0
        
        try:
            # 1. Clean up expired workspace locks
            cleaned_locks = self.workspace_lock_manager.cleanup_expired_locks(max_idle_minutes)
            total_cleaned += cleaned_locks
        except Exception as e:
            self.logger.error("Error cleaning up workspace locks", exc=e)
        
        try:
            # 2. Clean up old admission controller metrics (prevent memory growth)
            if len(self.admission_controller._queue_wait_times) > 1000:
                # Keep only last 1000 wait time measurements
                self.admission_controller._queue_wait_times = self.admission_controller._queue_wait_times[-1000:]
                self.logger.debug("Trimmed admission controller metrics")
        except Exception as e:
            self.logger.error("Error trimming admission controller metrics", exc=e)
        
        if total_cleaned > 0:
            self.logger.info("Concurrency periodic cleanup completed",
                           cleaned_locks=total_cleaned,
                           total_cleaned=total_cleaned)
        
        return total_cleaned 