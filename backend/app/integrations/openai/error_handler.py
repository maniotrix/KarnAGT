"""
OpenAI Error Handler

This module provides comprehensive error handling for OpenAI API integrations,
including retry logic, rate limiting, and FastAPI exception translation.
"""

import asyncio
import time
from typing import Any, Dict, Optional, Callable, Union
from functools import wraps
from datetime import datetime, timedelta

from fastapi import HTTPException, status
import openai
from openai import OpenAI

from app.core.exceptions import (
    OpenAIException,
    RateLimitExceededException,
    QuotaExceededException,
    ExternalServiceException
)

from aicore.logger import get_logger

# Set up logger
logger = get_logger(__name__)


class OpenAIErrorHandler:
    """
    Handles OpenAI API errors with retry logic and proper exception translation
    
    Features:
    - Automatic retry with exponential backoff
    - Rate limit handling
    - Quota management
    - Error translation to FastAPI exceptions
    - Circuit breaker pattern
    """
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        """
        Initialize the error handler
        
        Args:
            max_retries: Maximum number of retries
            base_delay: Base delay for exponential backoff
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.circuit_breaker = CircuitBreaker()
        
        logger.info(f"OpenAIErrorHandler initialized with {max_retries} max retries")
    
    def handle_openai_error(self, error: Exception) -> HTTPException:
        """
        Convert OpenAI errors to appropriate FastAPI exceptions
        
        Args:
            error: The OpenAI exception
            
        Returns:
            FastAPI HTTPException
        """
        logger.error(f"Handling OpenAI error: {type(error).__name__}: {str(error)}")
        
        if isinstance(error, openai.RateLimitError):
            return RateLimitExceededException(
                "Rate limit exceeded. Please try again later.",
                retry_after=getattr(error, 'retry_after', 60)
            )
        
        elif isinstance(error, openai.AuthenticationError):
            return HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="OpenAI API authentication failed"
            )
        
        elif isinstance(error, openai.PermissionDeniedError):
            return HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for OpenAI API"
            )
        
        elif isinstance(error, openai.NotFoundError):
            return HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OpenAI model or resource not found"
            )
        
        elif isinstance(error, openai.BadRequestError):
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid request to OpenAI API: {str(error)}"
            )
        
        elif isinstance(error, openai.ConflictError):
            return HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conflict with OpenAI API request"
            )
        
        elif isinstance(error, openai.UnprocessableEntityError):
            return HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unprocessable entity: {str(error)}"
            )
        
        elif isinstance(error, openai.InternalServerError):
            return HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="OpenAI API internal server error"
            )
        
        elif isinstance(error, openai.APITimeoutError):
            return HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="OpenAI API request timeout"
            )
        
        elif isinstance(error, openai.APIConnectionError):
            return HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to connect to OpenAI API"
            )
        
        else:
            # Generic OpenAI API error
            return OpenAIException(
                f"OpenAI API error: {str(error)}"
            )
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic and error handling
        
        Args:
            func: The function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            HTTPException: Converted OpenAI error
        """
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Check circuit breaker
                if self.circuit_breaker.is_open():
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="OpenAI API circuit breaker is open"
                    )
                
                # Execute the function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Success - reset circuit breaker
                self.circuit_breaker.record_success()
                
                if attempt > 0:
                    logger.info(f"OpenAI API call succeeded after {attempt} retries")
                
                return result
                
            except Exception as error:
                last_error = error
                
                # Record failure for circuit breaker
                self.circuit_breaker.record_failure()
                
                # Check if we should retry
                if not self._should_retry(error, attempt):
                    break
                
                # Calculate delay with exponential backoff
                delay = self._calculate_delay(attempt, error)
                
                logger.warning(
                    f"OpenAI API call failed (attempt {attempt + 1}/{self.max_retries + 1}), "
                    f"retrying in {delay:.2f}s: {str(error)}"
                )
                
                if attempt < self.max_retries:
                    await asyncio.sleep(delay)
        
        # All retries exhausted, raise the last error
        raise self.handle_openai_error(last_error)
    
    def _should_retry(self, error: Exception, attempt: int) -> bool:
        """
        Determine if an error should trigger a retry
        
        Args:
            error: The exception that occurred
            attempt: Current attempt number
            
        Returns:
            True if should retry, False otherwise
        """
        if attempt >= self.max_retries:
            return False
        
        # Retry on specific error types
        retry_errors = (
            openai.RateLimitError,
            openai.InternalServerError,
            openai.APITimeoutError,
            openai.APIConnectionError,
        )
        
        return isinstance(error, retry_errors)
    
    def _calculate_delay(self, attempt: int, error: Exception) -> float:
        """
        Calculate delay for retry with exponential backoff
        
        Args:
            attempt: Current attempt number
            error: The exception that occurred
            
        Returns:
            Delay in seconds
        """
        # Base exponential backoff
        delay = self.base_delay * (2 ** attempt)
        
        # Add jitter to prevent thundering herd
        jitter = delay * 0.1 * (time.time() % 1)
        delay += jitter
        
        # For rate limit errors, use the retry-after header if available
        if isinstance(error, openai.RateLimitError):
            retry_after = getattr(error, 'retry_after', None)
            if retry_after:
                delay = max(delay, float(retry_after))
        
        # Cap maximum delay
        return min(delay, 60.0)


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for OpenAI API calls
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Time to wait before attempting to close circuit
            expected_exception: Exception type to track
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        
        logger.info(f"CircuitBreaker initialized with threshold {failure_threshold}")
    
    def is_open(self) -> bool:
        """Check if circuit breaker is open"""
        if self.state == "open":
            # Check if timeout has passed
            if (self.last_failure_time and 
                time.time() - self.last_failure_time >= self.timeout):
                self.state = "half-open"
                logger.info("CircuitBreaker moved to half-open state")
                return False
            return True
        return False
    
    def record_success(self):
        """Record a successful operation"""
        if self.state == "half-open":
            self.state = "closed"
            logger.info("CircuitBreaker closed after successful operation")
        
        self.failure_count = 0
        self.last_failure_time = None
    
    def record_failure(self):
        """Record a failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"CircuitBreaker opened after {self.failure_count} failures")


# Decorator for automatic error handling
def handle_openai_errors(
    max_retries: int = 3,
    base_delay: float = 1.0
):
    """
    Decorator to automatically handle OpenAI errors with retry logic
    
    Args:
        max_retries: Maximum number of retries
        base_delay: Base delay for exponential backoff
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            error_handler = OpenAIErrorHandler(max_retries, base_delay)
            return await error_handler.execute_with_retry(func, *args, **kwargs)
        return wrapper
    return decorator


# Global error handler instance
error_handler = OpenAIErrorHandler()


# Utility functions
def is_retryable_error(error: Exception) -> bool:
    """
    Check if an error is retryable
    
    Args:
        error: The exception to check
        
    Returns:
        True if retryable, False otherwise
    """
    retryable_errors = (
        openai.RateLimitError,
        openai.InternalServerError,
        openai.APITimeoutError,
        openai.APIConnectionError,
    )
    
    return isinstance(error, retryable_errors)


def get_error_details(error: Exception) -> Dict[str, Any]:
    """
    Extract error details from OpenAI exceptions
    
    Args:
        error: The OpenAI exception
        
    Returns:
        Dictionary with error details
    """
    details = {
        "error_type": type(error).__name__,
        "message": str(error),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Add specific details for rate limit errors
    if isinstance(error, openai.RateLimitError):
        details.update({
            "retry_after": getattr(error, 'retry_after', None),
            "error_code": "rate_limit_exceeded"
        })
    
    # Add status code if available
    if hasattr(error, 'status_code'):
        details["status_code"] = error.status_code
    
    return details 