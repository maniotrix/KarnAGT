#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Workspace Lock Manager

Manages per-workspace locks to prevent concurrent executions
within the same workspace. This is Layer 1 of concurrency control.
"""

import asyncio
from typing import Dict
from datetime import datetime

from app.utils.logger import Loggers

class WorkspaceLockManager:
    """
    Manages workspace-specific locks (Layer 1 concurrency)
    
    Ensures only one execution per workspace at a time to prevent:
    - Kernel state corruption
    - File system conflicts
    - Inconsistent execution results
    """
    
    def __init__(self):
        self._workspace_locks: Dict[str, asyncio.Lock] = {}
        self._lock_creation_lock = asyncio.Lock()  # Protects lock creation
        self.logger = Loggers.execution_service
        
        # Metrics
        self._lock_acquisitions = 0
        self._active_workspaces: Dict[str, datetime] = {}
        
        self.logger.info("Workspace lock manager initialized")
    
    async def acquire_workspace_lock(self, workspace_id: str) -> asyncio.Lock:
        """
        Get and acquire lock for specific workspace
        
        Args:
            workspace_id: Workspace identifier
            
        Returns:
            Acquired lock for the workspace
        """
        # Get or create lock for this workspace (thread-safe)
        async with self._lock_creation_lock:
            if workspace_id not in self._workspace_locks:
                self._workspace_locks[workspace_id] = asyncio.Lock()
                self.logger.debug("Created new workspace lock",
                                workspace_id=workspace_id)
        
        # Acquire the workspace lock
        workspace_lock = self._workspace_locks[workspace_id]
        await workspace_lock.acquire()
        
        # Track metrics
        self._lock_acquisitions += 1
        self._active_workspaces[workspace_id] = datetime.utcnow()
        
        self.logger.debug("Workspace lock acquired",
                         workspace_id=workspace_id,
                         total_active_workspaces=len(self._active_workspaces))
        
        return workspace_lock
    
    def release_workspace_lock(self, workspace_id: str, lock: asyncio.Lock):
        """
        Release workspace lock
        
        Args:
            workspace_id: Workspace identifier
            lock: Lock to release
        """
        lock.release()
        
        # Remove from active tracking
        self._active_workspaces.pop(workspace_id, None)
        
        self.logger.debug("Workspace lock released",
                         workspace_id=workspace_id,
                         total_active_workspaces=len(self._active_workspaces))
    
    async def execute_with_workspace_lock(self, workspace_id: str, func, *args, **kwargs):
        """
        Execute function with workspace lock protection
        
        Args:
            workspace_id: Workspace identifier
            func: Function to execute
            *args, **kwargs: Function arguments
            
        Returns:
            Function result
        """
        workspace_lock = await self.acquire_workspace_lock(workspace_id)
        
        try:
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        finally:
            # Always release the lock
            self.release_workspace_lock(workspace_id, workspace_lock)
    
    def cleanup_expired_locks(self, max_idle_minutes: int = 60):
        """
        Clean up locks for workspaces that haven't been used recently
        
        Args:
            max_idle_minutes: Maximum idle time before cleanup
        """
        current_time = datetime.utcnow()
        expired_workspaces = []
        
        for workspace_id, last_activity in self._active_workspaces.items():
            idle_minutes = (current_time - last_activity).total_seconds() / 60
            if idle_minutes > max_idle_minutes:
                expired_workspaces.append(workspace_id)
        
        # Remove expired locks
        for workspace_id in expired_workspaces:
            if workspace_id in self._workspace_locks:
                # Only remove if not currently locked
                lock = self._workspace_locks[workspace_id]
                if not lock.locked():
                    del self._workspace_locks[workspace_id]
                    self._active_workspaces.pop(workspace_id, None)
                    self.logger.debug("Cleaned up expired workspace lock",
                                    workspace_id=workspace_id)
        
        return len(expired_workspaces)
    
    def get_stats(self) -> dict:
        """Get workspace lock manager statistics"""
        return {
            "total_workspace_locks": len(self._workspace_locks),
            "active_workspaces": len(self._active_workspaces),
            "total_lock_acquisitions": self._lock_acquisitions,
            "workspace_ids": list(self._workspace_locks.keys())
        } 