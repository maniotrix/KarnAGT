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
    
    Uses counter-based admission control to prevent system overload
    without the complexity and bugs of request queuing.
    """
    
    def __init__(self, max_concurrent_requests: int = 100):
        self.max_concurrent_requests = max_concurrent_requests
        self._current_requests = 0
        self._requests_lock = asyncio.Lock()
        self.logger = Loggers.execution_service
        
        # Metrics
        self._total_requests = 0
        self._rejected_requests = 0
        self._request_start_times = []
        
        self.logger.info("Admission controller initialized", 
                        max_concurrent_requests=max_concurrent_requests)
    
    async def acquire_admission(self) -> bool:
        """
        Try to acquire admission for a request
        
        Returns:
            True if admitted, False if rejected
        """
        async with self._requests_lock:
            if self._current_requests >= self.max_concurrent_requests:
                return False
            
            self._current_requests += 1
            self._request_start_times.append(datetime.utcnow())
            return True
    
    async def release_admission(self):
        """Release admission slot when request completes"""
        async with self._requests_lock:
            self._current_requests = max(0, self._current_requests - 1)
    
    def current_requests(self) -> int:
        """Get current number of admitted requests"""
        return self._current_requests
    
    def is_at_capacity(self) -> bool:
        """Check if admission controller is at capacity"""
        return self._current_requests >= self.max_concurrent_requests
    
    def get_rejection_rate(self) -> float:
        """Get current rejection rate (0.0 to 1.0)"""
        if self._total_requests == 0:
            return 0.0
        return self._rejected_requests / self._total_requests
    
    def get_stats(self) -> dict:
        """Get admission controller statistics"""
        avg_processing_time = 0.0
        current_time = datetime.utcnow()
        
        if self._request_start_times:
            active_times = [(current_time - start).total_seconds() 
                          for start in self._request_start_times[-self._current_requests:]]
            if active_times:
                avg_processing_time = sum(active_times) / len(active_times)
        
        return {
            "total_requests": self._total_requests,
            "rejected_requests": self._rejected_requests,
            "rejection_rate": self.get_rejection_rate(),
            "current_requests": self._current_requests,
            "max_concurrent_requests": self.max_concurrent_requests,
            "average_processing_time_seconds": round(avg_processing_time, 3)
        } 