#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logger Utilities

Easy-to-use logger utilities that provide:
- Convenient logger instances for different modules
- Performance timing decorators
- Exception logging helpers
- Structured logging with context
- Workspace and user context binding
"""

import functools
import time
import logging
import traceback
from typing import Any, Callable, Dict, Optional, Union, TypeVar, cast
from contextlib import contextmanager

from app.core.logging_config import LoggerNames, get_logger

F = TypeVar('F', bound=Callable[..., Any])


class AppLogger:
    """
    Application logger with structured logging and context support
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(name)
    
    def debug(self, message: str, **context):
        """Log debug message with context"""
        self.logger.debug(message, extra=context)
    
    def info(self, message: str, **context):
        """Log info message with context"""
        self.logger.info(message, extra=context)
    
    def warning(self, message: str, **context):
        """Log warning message with context"""
        self.logger.warning(message, extra=context)
    
    def error(self, message: str, exc: Optional[Exception] = None, **context):
        """Log error message with optional exception and context"""
        if exc:
            context.update({
                "exception_type": exc.__class__.__name__,
                "exception_message": str(exc),
            })
            self.logger.error(message, extra=context, exc_info=exc)
        else:
            self.logger.error(message, extra=context)
    
    def critical(self, message: str, exc: Optional[Exception] = None, **context):
        """Log critical message with optional exception and context"""
        if exc:
            context.update({
                "exception_type": exc.__class__.__name__,
                "exception_message": str(exc),
            })
            self.logger.critical(message, extra=context, exc_info=exc)
        else:
            self.logger.critical(message, extra=context)
    
    def exception(self, message: str, **context):
        """Log exception with full traceback"""
        self.logger.exception(message, extra=context)


class TimingLogger:
    """
    Logger for performance timing and monitoring
    """
    
    def __init__(self, logger: AppLogger, threshold_ms: float = 100.0):
        self.logger = logger
        self.threshold_ms = threshold_ms
    
    @contextmanager
    def time_operation(self, operation_name: str, **context):
        """
        Context manager for timing operations
        
        Usage:
            with timing_logger.time_operation("database_query", table="users"):
                # Your operation here
                result = db.query()
        """
        start_time = time.perf_counter()
        exception_occurred = False
        
        try:
            self.logger.debug(f"Starting operation: {operation_name}", **context)
            yield
        except Exception as e:
            exception_occurred = True
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self.logger.error(
                f"Operation failed: {operation_name}",
                exc=e,
                duration_ms=duration_ms,
                operation=operation_name,
                **context
            )
            raise
        finally:
            if not exception_occurred:
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                
                if duration_ms > self.threshold_ms:
                    self.logger.warning(
                        f"Slow operation: {operation_name}",
                        duration_ms=duration_ms,
                        threshold_ms=self.threshold_ms,
                        operation=operation_name,
                        slow_operation=True,
                        **context
                    )
                else:
                    self.logger.debug(
                        f"Completed operation: {operation_name}",
                        duration_ms=duration_ms,
                        operation=operation_name,
                        **context
                    )


def timed_operation(
    logger: AppLogger, 
    operation_name: Optional[str] = None,
    threshold_ms: float = 100.0,
    log_level: str = "info"
):
    """
    Decorator for timing function execution
    
    Args:
        logger: Logger instance to use
        operation_name: Name of the operation (defaults to function name)
        threshold_ms: Threshold for slow operation warning
        log_level: Log level for normal operations
        
    Usage:
        @timed_operation(logger, "workspace_creation", threshold_ms=500)
        async def create_workspace(workspace_data):
            # Function implementation
            pass
    """
    def decorator(func: F) -> F:
        name = operation_name or func.__name__
        timing_logger = TimingLogger(logger, threshold_ms)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with timing_logger.time_operation(
                name,
                function=func.__name__,
                module=func.__module__,
            ):
                return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with timing_logger.time_operation(
                name,
                function=func.__name__,
                module=func.__module__,
            ):
                return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return cast(F, async_wrapper)
        else:
            return cast(F, sync_wrapper)
    
    return decorator


def log_exception(logger: AppLogger, message: str = "An exception occurred", **context):
    """
    Decorator for automatic exception logging
    
    Usage:
        @log_exception(logger, "Failed to process request")
        async def process_request():
            # Function that might raise exceptions
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"{message}: {func.__name__}",
                    exc=e,
                    function=func.__name__,
                    module=func.__module__,
                    **context
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"{message}: {func.__name__}",
                    exc=e,
                    function=func.__name__,
                    module=func.__module__,
                    **context
                )
                raise
        
        # Return appropriate wrapper based on function type
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return cast(F, async_wrapper)
        else:
            return cast(F, sync_wrapper)
    
    return decorator


class WorkspaceLogger:
    """
    Logger with workspace context binding
    """
    
    def __init__(self, logger: AppLogger, workspace_id: str):
        self.logger = logger
        self.workspace_id = workspace_id
    
    def _add_workspace_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Add workspace context to log context"""
        context["workspace_id"] = self.workspace_id
        return context
    
    def debug(self, message: str, **context):
        self.logger.debug(message, **self._add_workspace_context(context))
    
    def info(self, message: str, **context):
        self.logger.info(message, **self._add_workspace_context(context))
    
    def warning(self, message: str, **context):
        self.logger.warning(message, **self._add_workspace_context(context))
    
    def error(self, message: str, exc: Optional[Exception] = None, **context):
        self.logger.error(message, exc=exc, **self._add_workspace_context(context))
    
    def critical(self, message: str, exc: Optional[Exception] = None, **context):
        self.logger.critical(message, exc=exc, **self._add_workspace_context(context))


# Pre-configured logger instances for different modules
class Loggers:
    """Pre-configured logger instances"""
    
    # Main application loggers
    app = AppLogger(LoggerNames.APP)
    api = AppLogger(LoggerNames.API)
    services = AppLogger(LoggerNames.SERVICES)
    middleware = AppLogger(LoggerNames.MIDDLEWARE)
    jupyter = AppLogger(LoggerNames.JUPYTER)
    
    # Service-specific loggers
    workspace_service = AppLogger(LoggerNames.WORKSPACE_SERVICE)
    execution_service = AppLogger(LoggerNames.EXECUTION_SERVICE)
    file_service = AppLogger(LoggerNames.FILE_SERVICE)
    
    # API-specific loggers
    api_routes = AppLogger(LoggerNames.API_ROUTES)
    api_dependencies = AppLogger(LoggerNames.API_DEPENDENCIES)


def get_workspace_logger(workspace_id: str) -> WorkspaceLogger:
    """
    Get a logger bound to a specific workspace
    
    Args:
        workspace_id: Workspace identifier
        
    Returns:
        WorkspaceLogger instance with workspace context
    """
    return WorkspaceLogger(Loggers.workspace_service, workspace_id)


def log_function_call(logger: AppLogger, include_args: bool = False):
    """
    Decorator to log function calls
    
    Args:
        logger: Logger instance to use
        include_args: Whether to include function arguments in log
        
    Usage:
        @log_function_call(Loggers.api_routes)
        async def create_workspace():
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            context = {
                "function": func.__name__,
                "module": func.__module__,
            }
            
            if include_args:
                context["args_count"] = len(args)
                context["kwargs_keys"] = list(kwargs.keys())
            
            logger.debug(f"Calling function: {func.__name__}", **context)
            
            try:
                result = await func(*args, **kwargs)
                logger.debug(f"Function completed: {func.__name__}", **context)
                return result
            except Exception as e:
                logger.error(f"Function failed: {func.__name__}", exc=e, **context)
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            context = {
                "function": func.__name__,
                "module": func.__module__,
            }
            
            if include_args:
                context["args_count"] = len(args)
                context["kwargs_keys"] = list(kwargs.keys())
            
            logger.debug(f"Calling function: {func.__name__}", **context)
            
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Function completed: {func.__name__}", **context)
                return result
            except Exception as e:
                logger.error(f"Function failed: {func.__name__}", exc=e, **context)
                raise
        
        # Return appropriate wrapper based on function type
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return cast(F, async_wrapper)
        else:
            return cast(F, sync_wrapper)
    
    return decorator 