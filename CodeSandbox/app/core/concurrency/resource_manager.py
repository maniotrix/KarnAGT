#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Resource Manager

Manages global system resources using semaphores.
Prevents system overload by limiting concurrent operations.
"""

import asyncio
import os
from typing import Optional

from app.utils.logger import Loggers

class ResourceManager:
    """
    Manages global system resources with semaphore-based limits
    
    Provides system-wide throttling to prevent CPU/memory exhaustion.
    """
    
    def __init__(self, max_concurrent_executions: Optional[int] = None):
        # Default to 2x CPU cores, but cap at reasonable limit
        if max_concurrent_executions is None:
            cpu_count = os.cpu_count() or 4  # Default to 4 if None
            max_concurrent_executions = min(cpu_count * 2, 20)
        
        self.max_concurrent_executions = max_concurrent_executions
        self._semaphore = asyncio.Semaphore(max_concurrent_executions)
        
        # Metrics
        self._total_acquisitions = 0
        self._current_active = 0
        self._peak_active = 0
        
        self.logger = Loggers.execution_service
        
        self.logger.info("Resource manager initialized",
                        max_concurrent_executions=max_concurrent_executions,
                        cpu_count=os.cpu_count())
    
    async def acquire(self) -> None:
        """
        Acquire a resource slot (blocks if limit reached)
        """
        await self._semaphore.acquire()
        
        self._total_acquisitions += 1
        self._current_active += 1
        self._peak_active = max(self._peak_active, self._current_active)
        
        self.logger.debug("Resource acquired",
                         current_active=self._current_active,
                         max_concurrent=self.max_concurrent_executions)
    
    def release(self) -> None:
        """
        Release a resource slot
        """
        self._semaphore.release()
        self._current_active = max(0, self._current_active - 1)
        
        self.logger.debug("Resource released",
                         current_active=self._current_active)
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self.release()
    
    def available_slots(self) -> int:
        """Get number of available resource slots"""
        return self.max_concurrent_executions - self._current_active
    
    def utilization_percentage(self) -> float:
        """Get current resource utilization as percentage"""
        return (self._current_active / self.max_concurrent_executions) * 100
    
    def is_at_capacity(self) -> bool:
        """Check if resource manager is at full capacity"""
        return self._current_active >= self.max_concurrent_executions
    
    def get_stats(self) -> dict:
        """Get resource manager statistics"""
        return {
            "max_concurrent_executions": self.max_concurrent_executions,
            "current_active": self._current_active,
            "available_slots": self.available_slots(),
            "utilization_percentage": round(self.utilization_percentage(), 1),
            "peak_active": self._peak_active,
            "total_acquisitions": self._total_acquisitions
        } 