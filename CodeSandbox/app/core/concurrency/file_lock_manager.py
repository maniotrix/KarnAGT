#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File Lock Manager

Manages per-file locks to prevent concurrent operations
on the same file. This is Layer 1 of file concurrency control.
"""

import asyncio
from typing import Dict
from datetime import datetime

from app.utils.logger import Loggers

class FileLockManager:
    """
    Manages file-specific locks (Layer 1 file concurrency)
    
    Ensures only one operation per file at a time to prevent:
    - File corruption from concurrent writes
    - Read-while-write inconsistencies
    - File system race conditions
    - Data loss from simultaneous uploads
    """
    
    def __init__(self):
        self._file_locks: Dict[str, asyncio.Lock] = {}
        self._lock_creation_lock = asyncio.Lock()  # Protects lock creation
        self.logger = Loggers.file_lock_manager
        
        # Metrics
        self._lock_acquisitions = 0
        self._active_files: Dict[str, datetime] = {}
        
        self.logger.info("File lock manager initialized")
    
    async def acquire_file_lock(self, workspace_id: str, filename: str) -> asyncio.Lock:
        """
        Get and acquire lock for specific file
        
        Args:
            workspace_id: Workspace identifier
            filename: File name within workspace
            
        Returns:
            Acquired lock for the file
        """
        # Create unique lock key for this file
        lock_key = f"{workspace_id}:{filename}"
        
        # Get or create lock for this file (thread-safe)
        async with self._lock_creation_lock:
            if lock_key not in self._file_locks:
                self._file_locks[lock_key] = asyncio.Lock()
                self.logger.debug("Created new file lock",
                                lock_key=lock_key,
                                workspace_id=workspace_id,
                                file_name=filename)
        
        # Acquire the file lock
        file_lock = self._file_locks[lock_key]
        await file_lock.acquire()
        
        # Track metrics
        self._lock_acquisitions += 1
        self._active_files[lock_key] = datetime.utcnow()
        
        self.logger.debug("File lock acquired",
                         lock_key=lock_key,
                         workspace_id=workspace_id,
                         file_name=filename,
                         total_active_files=len(self._active_files))
        
        return file_lock
    
    def release_file_lock(self, workspace_id: str, filename: str, lock: asyncio.Lock):
        """
        Release file lock
        
        Args:
            workspace_id: Workspace identifier
            filename: File name within workspace
            lock: Lock to release
        """
        lock.release()
        
        # Remove from active tracking
        lock_key = f"{workspace_id}:{filename}"
        self._active_files.pop(lock_key, None)
        
        self.logger.debug("File lock released",
                         lock_key=lock_key,
                         workspace_id=workspace_id,
                         file_name=filename,
                         total_active_files=len(self._active_files))
    
    async def execute_with_file_lock(self, workspace_id: str, filename: str, func, *args, **kwargs):
        """
        Execute function with file lock protection
        
        Args:
            workspace_id: Workspace identifier
            filename: File name within workspace
            func: Function to execute
            *args, **kwargs: Function arguments
            
        Returns:
            Function result
        """
        file_lock = await self.acquire_file_lock(workspace_id, filename)
        
        try:
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        finally:
            # Always release the lock
            self.release_file_lock(workspace_id, filename, file_lock)
    
    def cleanup_expired_locks(self, max_idle_minutes: int = 60):
        """
        Clean up locks for files that haven't been used recently
        
        Args:
            max_idle_minutes: Maximum idle time before cleanup
        """
        current_time = datetime.utcnow()
        expired_files = []
        
        for lock_key, last_activity in self._active_files.items():
            idle_minutes = (current_time - last_activity).total_seconds() / 60
            if idle_minutes > max_idle_minutes:
                expired_files.append(lock_key)
        
        # Remove expired locks
        for lock_key in expired_files:
            if lock_key in self._file_locks:
                # Only remove if not currently locked
                lock = self._file_locks[lock_key]
                if not lock.locked():
                    del self._file_locks[lock_key]
                    self._active_files.pop(lock_key, None)
                    self.logger.debug("Cleaned up expired file lock",
                                    lock_key=lock_key)
        
        return len(expired_files)
    
    def cleanup_workspace_locks(self, workspace_id: str) -> int:
        """
        Clean up all file locks for a specific workspace
        
        Args:
            workspace_id: Workspace ID to clean up locks for
            
        Returns:
            Number of locks cleaned up
        """
        cleaned_count = 0
        lock_keys_to_remove = []
        
        # Find all locks for this workspace
        for lock_key in list(self._file_locks.keys()):
            if lock_key.startswith(f"{workspace_id}:"):
                lock_keys_to_remove.append(lock_key)
        
        # Remove locks if not currently locked
        for lock_key in lock_keys_to_remove:
            if lock_key in self._file_locks:
                lock = self._file_locks[lock_key]
                if not lock.locked():
                    del self._file_locks[lock_key]
                    self._active_files.pop(lock_key, None)
                    cleaned_count += 1
                    self.logger.debug("Cleaned up file lock for deleted workspace",
                                    lock_key=lock_key,
                                    workspace_id=workspace_id)
        
        if cleaned_count > 0:
            self.logger.info("Cleaned up file locks for workspace",
                           workspace_id=workspace_id,
                           cleaned_count=cleaned_count)
        
        return cleaned_count
    
    def get_stats(self) -> dict:
        """Get file lock manager statistics"""
        return {
            "total_file_locks": len(self._file_locks),
            "active_files": len(self._active_files),
            "total_lock_acquisitions": self._lock_acquisitions,
            "file_lock_keys": list(self._file_locks.keys())
        } 