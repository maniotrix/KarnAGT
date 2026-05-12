#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logging Middleware

Comprehensive request tracing and logging middleware that provides:
- Unique correlation IDs for request tracing
- Request/response logging
- Performance monitoring  
- Exception handling and logging
- Context propagation
"""

import time
import uuid
import logging
from typing import Any, Callable, Dict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp
import traceback

from app.core.logging_config import LoggerNames, get_logger


class LoggingContextFilter(logging.Filter):
    """
    Logging filter that adds request context to log records
    """
    
    def __init__(self):
        super().__init__()
        self._context = {}
    
    def set_context(self, **kwargs):
        """Set context variables"""
        self._context.update(kwargs)
    
    def clear_context(self):
        """Clear context variables"""
        self._context.clear()
    
    def filter(self, record):
        """Add context to log record"""
        for key, value in self._context.items():
            setattr(record, key, value)
        return True


# Global context filter instance
_context_filter = LoggingContextFilter()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Request logging middleware with correlation IDs and performance monitoring
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.access_logger = get_logger(LoggerNames.ACCESS)
        self.app_logger = get_logger(LoggerNames.MIDDLEWARE)
        self.error_logger = get_logger(LoggerNames.ERRORS)
        
        # Add context filter to all relevant loggers
        self._setup_context_filters()
    
    def _setup_context_filters(self):
        """Set up context filters for loggers"""
        logger_names = [
            LoggerNames.APP,
            LoggerNames.API,
            LoggerNames.SERVICES,
            LoggerNames.MIDDLEWARE,
            LoggerNames.JUPYTER,
            LoggerNames.ACCESS,
            LoggerNames.ERRORS,
        ]
        
        for logger_name in logger_names:
            logger = get_logger(logger_name)
            logger.addFilter(_context_filter)
    
    def _generate_correlation_id(self) -> str:
        """Generate a unique correlation ID"""
        return str(uuid.uuid4())
    
    def _get_client_info(self, request: Request) -> Dict[str, Any]:
        """Extract client information from request"""
        client = request.client
        client_ip = "unknown"
        client_port = 0
        
        if client:
            client_ip = client.host
            client_port = client.port
            
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
            
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            client_ip = real_ip
            
        return {
            "client_ip": client_ip,
            "client_port": client_port,
            "user_agent": request.headers.get("user-agent", ""),
            "forwarded_for": forwarded_for,
            "real_ip": real_ip,
        }
    
    def _should_log_request(self, request: Request) -> bool:
        """Determine if request should be logged"""
        path = request.url.path
        
        # Skip health checks and static assets
        skip_paths = ["/health", "/metrics", "/favicon.ico", "/robots.txt"]
        
        for skip_path in skip_paths:
            if path.startswith(skip_path):
                return False
                
        return True
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with comprehensive logging
        """
        # Generate correlation ID
        correlation_id = request.headers.get("x-correlation-id") or self._generate_correlation_id()
        
        # Extract request information
        client_info = self._get_client_info(request)
        request_info = {
            "correlation_id": correlation_id,
            "http_method": request.method,
            "http_path": request.url.path,
            "http_query": str(request.url.query) if request.url.query else "",
            "http_scheme": request.url.scheme,
            "content_type": request.headers.get("content-type", ""),
        }
        
        # Set context for all loggers
        _context_filter.set_context(
            correlation_id=correlation_id,
            http_method=request.method,
            http_path=request.url.path,
            client_ip=client_info["client_ip"],
        )
        
        # Start timing
        start_time = time.perf_counter()
        
        # Log incoming request if enabled
        if self._should_log_request(request):
            self.app_logger.info(
                f"Incoming request: {request.method} {request.url.path}",
                extra={
                    **request_info,
                    **client_info,
                }
            )
        
        # Process request
        response = None
        status_code = 500
        exception_info = None
        
        try:
            # Call the next middleware/endpoint
            response = await call_next(request)
            status_code = response.status_code
            
        except Exception as exc:
            # Log the exception
            exception_info = {
                "exception_type": exc.__class__.__name__,
                "exception_message": str(exc),
                "traceback": traceback.format_exc(),
            }
            
            self.error_logger.error(
                f"Unhandled exception in request processing: {exc}",
                extra={
                    **request_info,
                    **client_info,
                    **exception_info,
                },
                exc_info=True
            )
            
            # Return error response
            response = JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred",
                    "correlation_id": correlation_id,
                },
            )
            status_code = 500
        
        # Calculate duration
        end_time = time.perf_counter()
        duration_ms = round((end_time - start_time) * 1000, 2)
        
        # Add response context
        _context_filter.set_context(
            http_status=status_code,
            duration_ms=duration_ms,
        )
        
        # Log response if enabled
        if self._should_log_request(request):
            log_level = logging.ERROR if status_code >= 500 else logging.WARNING if status_code >= 400 else logging.INFO
            
            self.access_logger.log(
                log_level,
                f"{client_info['client_ip']} - \"{request.method} {request.url.path}\" {status_code}",
                extra={
                    **request_info,
                    **client_info,
                    "http_status": status_code,
                    "duration_ms": duration_ms,
                    "response_size": getattr(response, "headers", {}).get("content-length", "unknown"),
                    **(exception_info or {}),
                }
            )
        
        # Add correlation ID to response headers
        if response and hasattr(response, "headers"):
            response.headers["x-correlation-id"] = correlation_id
        
        # Clear context for next request
        _context_filter.clear_context()
        
        return response


class PerformanceLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for detailed performance logging
    """
    
    def __init__(self, app: ASGIApp, slow_request_threshold_ms: float = 1000.0):
        super().__init__(app)
        self.perf_logger = get_logger("app.performance")
        self.slow_request_threshold_ms = slow_request_threshold_ms
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Log performance metrics for requests
        """
        start_time = time.perf_counter()
        
        # Process request
        response = await call_next(request)
        
        # Calculate timing
        end_time = time.perf_counter()
        duration_ms = round((end_time - start_time) * 1000, 2)
        
        # Log slow requests
        if duration_ms >= self.slow_request_threshold_ms:
            self.perf_logger.warning(
                f"Slow request detected: {request.method} {request.url.path}",
                extra={
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "http_status": response.status_code,
                    "duration_ms": duration_ms,
                    "slow_request": True,
                    "threshold_ms": self.slow_request_threshold_ms,
                }
            )
        
        return response


def get_correlation_id() -> str:
    """
    Get the current correlation ID from context
    """
    return getattr(_context_filter._context, 'correlation_id', 'unknown')


def log_with_context(logger: logging.Logger, level: str, message: str, **extra):
    """
    Log with additional context
    
    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **extra: Additional context to include
    """
    log_func = getattr(logger, level.lower())
    log_func(message, extra=extra) 