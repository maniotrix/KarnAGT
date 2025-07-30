#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Centralized Cleanup Service

Industry-standard approach: Single service responsible for ALL cleanup operations.
Eliminates scattered cleanup logic and provides unified cleanup coordination.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Set, Optional, Any
from enum import Enum

from app.core.config import Settings
from app.core.events import get_event_bus, WorkspaceDeletedEvent
from app.utils.logger import Loggers
from app.services.workspace_service import WorkspaceService
from app.services.execution_service import ExecutionService
from app.core.concurrency.concurrency_manager import ConcurrencyManager
from app.infrastructure.jupyter_kernel_client import JupyterServerClient
from app.services.file_service import FileService

class CleanupReason(str, Enum):
    """Reasons for cleanup operations"""
    EXPIRED = "expired"
    TIMEOUT = "timeout" 
    MANUAL = "manual"
    SHUTDOWN = "shutdown"
    PERIODIC = "periodic"

class CleanupService:
    """
    ✅ CENTRALIZED CLEANUP SERVICE
    
    Single point of control for ALL cleanup operations in the system.
    Follows Single Responsibility Principle - one service, one job: cleanup.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = Loggers.execution_service  # Use existing logger for now
        self.event_bus = get_event_bus()
        
        # References to all components that need cleanup
        self._workspace_service : Optional[WorkspaceService] = None
        self._execution_service : Optional[ExecutionService] = None
        self._jupyter_client : Optional[JupyterServerClient] = None
        self._concurrency_manager : Optional[ConcurrencyManager] = None
        self._file_service : Optional[FileService] = None
        
        # Cleanup state tracking
        self._cleanup_task: Optional[asyncio.Task] = None
        self._should_stop = False
        
        # Statistics
        self._cleanup_stats = {
            "total_cleanups": 0,
            "workspace_cleanups": 0,
            "execution_cleanups": 0,
            "concurrency_cleanups": 0,
            "kernel_cleanups": 0,
            "file_service_cleanups": 0
        }
        
        # Subscribe to workspace deletion events
        self.event_bus.subscribe(WorkspaceDeletedEvent, self._handle_workspace_deleted)
        
        self.logger.info("Centralized cleanup service initialized")
    
    def register_components(self, workspace_service, execution_service, jupyter_client, concurrency_manager, file_service=None):
        """Register all components that need cleanup"""
        self._workspace_service = workspace_service
        self._execution_service = execution_service
        self._jupyter_client = jupyter_client
        self._concurrency_manager = concurrency_manager
        self._file_service = file_service
        
        self.logger.info("All cleanup components registered", 
                        has_file_service=file_service is not None)
    
    async def start(self):
        """Start the centralized cleanup loop"""
        self._cleanup_task = asyncio.create_task(self._unified_cleanup_loop())
        
    async def stop(self):
        """Stop cleanup and perform final cleanup"""
        self._should_stop = True
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Final cleanup on shutdown
        await self._cleanup_all(CleanupReason.SHUTDOWN)
    
    async def _unified_cleanup_loop(self):
        """
        ✅ SINGLE CLEANUP LOOP FOR EVERYTHING
        Instead of 3 different loops in different services
        """
        interval_minutes = self.settings.workspace_cleanup_interval_minutes
        interval_seconds = interval_minutes * 60
        
        self.logger.info("Starting unified cleanup loop",
                        interval_minutes=interval_minutes)
        
        while not self._should_stop:
            try:
                await self._periodic_cleanup()
                await asyncio.sleep(interval_seconds)
                
            except asyncio.CancelledError:
                self.logger.info("Cleanup loop cancelled")
                break
            except Exception as e:
                self.logger.error("Error in cleanup loop", exc=e)
                await asyncio.sleep(60)  # Retry after 1 minute
    
    async def _periodic_cleanup(self):
        """Unified periodic cleanup - handles ALL periodic cleanup in one place"""
        self.logger.info("Starting periodic cleanup (all components)")
        
        cleanup_results = {
            "expired_workspaces": 0,
            "old_executions": 0,
            "expired_locks": 0,
            "idle_kernels": 0,
            "file_service_locks": 0
        }
        
        try:
            # 1. Clean expired workspaces (most important)
            cleanup_results["expired_workspaces"] = await self._cleanup_expired_workspaces()
            
            # 2. Clean old execution results  
            cleanup_results["old_executions"] = await self._cleanup_old_executions()
            
            # 3. Clean expired concurrency locks
            cleanup_results["expired_locks"] = await self._cleanup_expired_locks()
            
            # 4. Clean idle kernels (safety net)
            cleanup_results["idle_kernels"] = await self._cleanup_idle_kernels()
            
            # 5. Clean file service locks and resources
            cleanup_results["file_service_locks"] = await self._cleanup_file_service()
            
            total_cleaned = sum(cleanup_results.values())
            self._cleanup_stats["total_cleanups"] += total_cleaned
            
            if total_cleaned > 0:
                self.logger.info("Periodic cleanup completed",
                               **cleanup_results,
                               total_cleaned=total_cleaned)
            
        except Exception as e:
            self.logger.error("Error during periodic cleanup", exc=e)
    
    async def _handle_workspace_deleted(self, event: WorkspaceDeletedEvent):
        """
        ✅ CENTRALIZED EVENT-DRIVEN CLEANUP
        Single handler for workspace deletion - cleans ALL related data
        """
        try:
            self.logger.info("Handling workspace deletion (centralized)",
                            workspace_id=event.workspace_id,
                            reason=event.reason)
            
            cleanup_results = await self._cleanup_workspace_data(event.workspace_id)
            
            self.logger.info("Workspace deletion cleanup completed",
                            workspace_id=event.workspace_id,
                            **cleanup_results)
        except Exception as e:
            self.logger.error("Error in centralized workspace deletion handler",
                            workspace_id=event.workspace_id,
                            reason=event.reason,
                            error=str(e),
                            exc=e)
    
    async def _cleanup_workspace_data(self, workspace_id: str) -> Dict[str, int]:
        """Clean ALL data related to a specific workspace"""
        results = {
            "executions_cleaned": 0,
            "locks_cleaned": 0,
            "warmed_state_cleaned": 0,
            "file_locks_cleaned": 0
        }
        
        try:
            # 1. Clean execution results for this workspace
            if self._execution_service:
                try:
                    results["executions_cleaned"] = self._execution_service.cleanup_workspace_executions(workspace_id)
                    # Clean warmed workspace state
                    self._execution_service._warmed_workspaces.discard(workspace_id)
                    results["warmed_state_cleaned"] = 1
                except Exception as e:
                    self.logger.error("Error cleaning execution service data",
                                    workspace_id=workspace_id,
                                    error=str(e))
            
            # 2. Clean concurrency locks for this workspace
            if self._concurrency_manager:
                try:
                    self._concurrency_manager.notify_workspace_deleted(workspace_id)
                    results["locks_cleaned"] = 1
                except Exception as e:
                    self.logger.error("Error cleaning concurrency manager data",
                                    workspace_id=workspace_id,
                                    error=str(e))
            
            # 3. Clean file service locks for this workspace
            if self._file_service:
                try:
                    self._file_service.notify_workspace_deleted(workspace_id)
                    results["file_locks_cleaned"] = 1
                except Exception as e:
                    self.logger.error("Error cleaning file service data",
                                    workspace_id=workspace_id,
                                    error=str(e))
            
            self._cleanup_stats["workspace_cleanups"] += 1
            
        except Exception as e:
            self.logger.error("Error cleaning workspace data",
                            workspace_id=workspace_id,
                            exc=e)
        
        return results
    
    async def _cleanup_expired_workspaces(self) -> int:
        """Clean expired workspaces - calls WorkspaceService public method"""
        if not self._workspace_service:
            return 0
            
        try:
            # Call the public cleanup method that returns proper count
            cleaned_count = await self._workspace_service.cleanup_expired_workspaces()
            
            # Update our stats
            self._cleanup_stats["workspace_cleanups"] += cleaned_count
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error("Error cleaning expired workspaces", exc=e)
            return 0
    
    async def _cleanup_old_executions(self) -> int:
        """Clean old execution results - centralized execution cleanup"""
        if not self._execution_service:
            return 0
            
        try:
            cleaned = await self._execution_service.cleanup_old_executions(
                max_age_hours=self.settings.execution_results_max_age_hours
            )
            self._cleanup_stats["execution_cleanups"] += cleaned
            return cleaned
            
        except Exception as e:
            self.logger.error("Error cleaning old executions", exc=e)
            return 0
    
    async def _cleanup_expired_locks(self) -> int:
        """Clean expired concurrency locks"""
        if not self._concurrency_manager:
            return 0
            
        try:
            cleaned = await self._concurrency_manager.periodic_cleanup(
                max_idle_minutes=self.settings.workspace_idle_timeout_minutes
            )
            self._cleanup_stats["concurrency_cleanups"] += cleaned
            return cleaned
            
        except Exception as e:
            self.logger.error("Error cleaning expired locks", exc=e)
            return 0
    
    async def _cleanup_idle_kernels(self) -> int:
        """Clean idle Jupyter kernels"""
        if not self._jupyter_client:
            return 0
            
        try:
            # Count kernels before cleanup
            kernels_before = len(self._jupyter_client._workspaces)
            
            await self._jupyter_client.cleanup_expired_kernels(
                max_idle_minutes=self.settings.workspace_idle_timeout_minutes
            )
            
            kernels_after = len(self._jupyter_client._workspaces)
            cleaned = kernels_before - kernels_after
            
            self._cleanup_stats["kernel_cleanups"] += cleaned
            return cleaned
            
        except Exception as e:
            self.logger.error("Error cleaning idle kernels", exc=e)
            return 0
    
    async def _cleanup_file_service(self) -> int:
        """Clean up file service locks and resources"""
        if not self._file_service:
            return 0
        
        try:
            cleaned = await self._file_service.periodic_cleanup(
                max_idle_minutes=self.settings.workspace_idle_timeout_minutes
            )
            
            self._cleanup_stats["file_service_cleanups"] += cleaned
            return cleaned
            
        except Exception as e:
            self.logger.error("Error cleaning file service resources", exc=e)
            return 0
    
    async def _cleanup_all(self, reason: CleanupReason):
        """Emergency cleanup of everything (shutdown, etc.)"""
        self.logger.info("Performing complete system cleanup", reason=reason)
        
        try:
            # Close all kernels (this is the only service that actually has a cleanup method)
            if self._jupyter_client:
                await self._jupyter_client.close()
                
            self.logger.info("Complete system cleanup finished", reason=reason)
            
        except Exception as e:
            self.logger.error("Error during complete cleanup", exc=e, reason=reason)
    
    def get_cleanup_stats(self) -> Dict[str, Any]:
        """Get comprehensive cleanup statistics"""
        return {
            **self._cleanup_stats,
            "cleanup_service_healthy": not self._should_stop,
            "registered_components": {
                "workspace_service": self._workspace_service is not None,
                "execution_service": self._execution_service is not None,
                "jupyter_client": self._jupyter_client is not None,
                "concurrency_manager": self._concurrency_manager is not None,
                "file_service": self._file_service is not None
            }
        } 