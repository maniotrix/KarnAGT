#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Circuit Breaker Pattern

Prevents cascade failures by temporarily blocking requests
when failure rate exceeds threshold.
"""

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, TypeVar, Any, Optional

from app.utils.logger import Loggers

T = TypeVar('T')

class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreakerError(Exception):
    """Circuit breaker is open"""
    pass

class CircuitBreaker:
    """
    Circuit breaker for protecting against cascade failures
    
    Monitors failure rate and temporarily blocks requests
    when system is unhealthy.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        test_requests: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.test_requests = test_requests
        
        # State tracking
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state_changed_time = datetime.utcnow()
        
        self.logger = Loggers.execution_service
        
        self.logger.info("Circuit breaker initialized",
                        failure_threshold=failure_threshold,
                        recovery_timeout=recovery_timeout)
    
    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to execute
            *args, **kwargs: Function arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
        """
        # Check if we should block the request
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                raise CircuitBreakerError(
                    f"Circuit breaker is open. Last failure: {self.last_failure_time}"
                )
        
        try:
            # Execute the function (handle both sync and async)
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure(e)
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if not self.last_failure_time:
            return True
        
        time_since_failure = datetime.utcnow() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful execution"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            
            # If enough test requests succeeded, close circuit
            if self.success_count >= self.test_requests:
                self._transition_to_closed()
        
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = max(0, self.failure_count - 1)
    
    def _on_failure(self, exception: Exception):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        self.logger.warning("Circuit breaker recorded failure",
                          failure_count=self.failure_count,
                          threshold=self.failure_threshold,
                          exception=str(exception))
        
        # Open circuit if threshold exceeded
        if self.failure_count >= self.failure_threshold:
            if self.state == CircuitState.CLOSED:
                self._transition_to_open()
            elif self.state == CircuitState.HALF_OPEN:
                self._transition_to_open()
    
    def _transition_to_open(self):
        """Transition to OPEN state"""
        self.state = CircuitState.OPEN
        self.state_changed_time = datetime.utcnow()
        
        self.logger.warning("Circuit breaker OPENED",
                          failure_count=self.failure_count,
                          threshold=self.failure_threshold)
    
    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state"""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.state_changed_time = datetime.utcnow()
        
        self.logger.info("Circuit breaker HALF-OPENED - testing recovery")
    
    def _transition_to_closed(self):
        """Transition to CLOSED state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.state_changed_time = datetime.utcnow()
        
        self.logger.info("Circuit breaker CLOSED - service recovered")
    
    def get_stats(self) -> dict:
        """Get circuit breaker statistics"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "state_changed_time": self.state_changed_time.isoformat(),
            "time_in_current_state_seconds": (datetime.utcnow() - self.state_changed_time).total_seconds()
        } 