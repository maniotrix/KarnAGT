#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Admission Controller

Manages incoming request queues to prevent system overload.
Provides backpressure control and graceful degradation.
"""

import asyncio
from typing import Generic, TypeVar, Optional
from datetime import datetime

from app.utils.logger import Loggers

T = TypeVar('T')

class AdmissionController(Generic[T]):
    """
    Controls admission of requests into the system
    
    Prevents memory explosion by limiting queue size and
    providing fast-fail behavior when overwhelmed.
    """
    
    def __init__(self, max_queue_size: int = 100):
        self.max_queue_size = max_queue_size
        self._queue = asyncio.Queue(maxsize=max_queue_size)
        self.logger = Loggers.execution_service
        
        # Metrics
        self._total_requests = 0
        self._rejected_requests = 0
        self._queue_wait_times = []
        
        self.logger.info("Admission controller initialized", 
                        max_queue_size=max_queue_size)
    
    async def admit_request(self, request: T, timeout: float = 1.0) -> bool:
        """
        Try to admit a request into the queue
        
        Args:
            request: Request to admit
            timeout: Maximum time to wait for queue space
            
        Returns:
            True if admitted, False if rejected
        """
        self._total_requests += 1
        start_time = datetime.utcnow()
        
        try:
            # Try to put request in queue with timeout
            await asyncio.wait_for(
                self._queue.put(request), 
                timeout=timeout
            )
            
            # Track wait time
            wait_time = (datetime.utcnow() - start_time).total_seconds()
            self._queue_wait_times.append(wait_time)
            
            self.logger.debug("Request admitted to queue",
                            queue_size=self._queue.qsize(),
                            wait_time_ms=int(wait_time * 1000))
            return True
            
        except asyncio.TimeoutError:
            # Queue is full, reject request
            self._rejected_requests += 1
            self.logger.warning("Request rejected - queue full",
                              queue_size=self._queue.qsize(),
                              rejection_rate=self.get_rejection_rate())
            return False
    
    async def get_next_request(self) -> T:
        """
        Get next request from queue (blocks if empty)
        
        Returns:
            Next request in queue
        """
        return await self._queue.get()
    
    def queue_size(self) -> int:
        """Get current queue size"""
        return self._queue.qsize()
    
    def is_queue_full(self) -> bool:
        """Check if queue is at capacity"""
        return self._queue.qsize() >= self.max_queue_size
    
    def get_rejection_rate(self) -> float:
        """Get current rejection rate (0.0 to 1.0)"""
        if self._total_requests == 0:
            return 0.0
        return self._rejected_requests / self._total_requests
    
    def get_stats(self) -> dict:
        """Get admission controller statistics"""
        avg_wait_time = 0.0
        if self._queue_wait_times:
            avg_wait_time = sum(self._queue_wait_times) / len(self._queue_wait_times)
        
        return {
            "total_requests": self._total_requests,
            "rejected_requests": self._rejected_requests,
            "rejection_rate": self.get_rejection_rate(),
            "current_queue_size": self._queue.qsize(),
            "max_queue_size": self.max_queue_size,
            "average_wait_time_seconds": round(avg_wait_time, 3)
        } 