#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Comprehensive Logging Configuration

Industry-standard logging setup with:
- Structured JSON logging for production
- Pretty console logging for development  
- Request correlation IDs
- Module-specific loggers with configurable levels
- Exception handling with stack traces
- Performance monitoring
- File rotation
- Environment-based configuration
"""

import logging
import logging.config
import json
import sys
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

from app.core.config import get_settings


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging in production
    """
    
    def format(self, record: logging.LogRecord) -> str:
        # Create base log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),  # Use local time instead of UTC
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "thread_name": record.threadName,
        }
        
        # Add correlation ID if available
        correlation_id = getattr(record, 'correlation_id', None)
        if correlation_id:
            log_entry["correlation_id"] = correlation_id
            
        # Add request context if available
        request_id = getattr(record, 'request_id', None)
        if request_id:
            log_entry["request_id"] = request_id
        user_id = getattr(record, 'user_id', None)
        if user_id:
            log_entry["user_id"] = user_id
        workspace_id = getattr(record, 'workspace_id', None)
        if workspace_id:
            log_entry["workspace_id"] = workspace_id
            
        # Add performance metrics if available
        duration_ms = getattr(record, 'duration_ms', None)
        if duration_ms is not None:
            log_entry["duration_ms"] = duration_ms
        status_code = getattr(record, 'status_code', None)
        if status_code:
            log_entry["status_code"] = status_code
            
        # Add HTTP context if available
        http_method = getattr(record, 'http_method', None)
        if http_method:
            log_entry["http_method"] = http_method
        http_path = getattr(record, 'http_path', None)
        if http_path:
            log_entry["http_path"] = http_path
        http_status = getattr(record, 'http_status', None)
        if http_status:
            log_entry["http_status"] = http_status
            
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }
            
        # Add extra fields from record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated', 
                          'thread', 'threadName', 'processName', 'process', 'message',
                          'correlation_id', 'request_id', 'user_id', 'workspace_id',
                          'duration_ms', 'status_code', 'http_method', 'http_path', 'http_status']:
                extra_fields[key] = value
                
        if extra_fields:
            log_entry["extra"] = extra_fields
            
        return json.dumps(log_entry, ensure_ascii=False, default=str)


class ColoredConsoleFormatter(logging.Formatter):
    """
    Colored console formatter for development
    """
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    def format(self, record: logging.LogRecord) -> str:
        # Color the log level
        level_color = self.COLORS.get(record.levelname, '')
        colored_level = f"{level_color}{record.levelname}{self.RESET}"
        
        # Format timestamp
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Build the base message
        base_msg = f"{timestamp} {colored_level:<15} {self.BOLD}{record.name}{self.RESET} | {record.getMessage()}"
        
        # Add context information
        context_parts = []
        
        correlation_id = getattr(record, 'correlation_id', None)
        if correlation_id:
            context_parts.append(f"id={correlation_id[:8]}")
        workspace_id = getattr(record, 'workspace_id', None)
        if workspace_id:
            context_parts.append(f"ws={workspace_id}")
        user_id = getattr(record, 'user_id', None)
        if user_id:
            context_parts.append(f"user={user_id}")
        duration_ms = getattr(record, 'duration_ms', None)
        if duration_ms is not None:
            context_parts.append(f"took={duration_ms}ms")
        http_method = getattr(record, 'http_method', None)
        http_path = getattr(record, 'http_path', None)
        if http_method and http_path:
            context_parts.append(f"{http_method} {http_path}")
        http_status = getattr(record, 'http_status', None)
        if http_status:
            context_parts.append(f"→ {http_status}")
            
        if context_parts:
            context = " ".join(context_parts)
            base_msg += f" \033[90m[{context}]\033[0m"
            
        # Add exception info if present
        if record.exc_info:
            base_msg += f"\n{self.formatException(record.exc_info)}"
            
        return base_msg


class LoggingConfig:
    """
    Central logging configuration manager
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.is_development = self.settings.is_development()
        
    def setup_logging(self):
        """
        Set up comprehensive logging configuration
        """
        # Create logs directory if it doesn't exist
        # Use settings.logs_base_path consistently across all environments
        log_dir = Path(self.settings.logs_base_path)
        # Ensure parent directories are created as well (cross-platform safety)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine log level
        log_level = getattr(logging, self.settings.log_level.upper(), logging.INFO)
        
        # Configure logging
        logging_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": JSONFormatter,
                },
                "console": {
                    "()": ColoredConsoleFormatter,
                },
                "standard": {
                    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "DEBUG",
                    "formatter": "console" if self.is_development else "json",
                    "stream": "ext://sys.stdout",
                },
                "app_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": log_level,
                    "formatter": "json",
                    "filename": str(log_dir / "app.log"),
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 5,
                    "encoding": "utf-8",
                },
                "access_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "INFO",
                    "formatter": "json", 
                    "filename": str(log_dir / "access.log"),
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 5,
                    "encoding": "utf-8",
                },
                "error_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "ERROR",
                    "formatter": "json",
                    "filename": str(log_dir / "error.log"), 
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 10,
                    "encoding": "utf-8",
                },
            },
            "loggers": {
                # Main application loggers
                "app": {
                    "handlers": ["console", "app_file"],
                    "level": log_level,
                    "propagate": False,
                },
                "app.api": {
                    "handlers": ["console", "app_file"],
                    "level": log_level,
                    "propagate": False,
                },
                "app.services": {
                    "handlers": ["console", "app_file"],
                    "level": log_level,
                    "propagate": False,
                },
                "app.middleware": {
                    "handlers": ["console", "app_file"],
                    "level": log_level,
                    "propagate": False,
                },
                "app.jupyter": {
                    "handlers": ["console", "app_file"],
                    "level": log_level,
                    "propagate": False,
                },
                
                # Access logs (HTTP requests)
                "app.access": {
                    "handlers": ["console", "access_file"],
                    "level": "INFO",
                    "propagate": False,
                },
                
                # Error logs
                "app.errors": {
                    "handlers": ["console", "error_file"],
                    "level": "ERROR",
                    "propagate": False,
                },
                
                # Third-party loggers
                "uvicorn": {
                    "handlers": ["console", "access_file"],
                    "level": "INFO",
                    "propagate": False,
                },
                "uvicorn.error": {
                    "handlers": ["console", "error_file"],
                    "level": "INFO",
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": [],
                    "level": "INFO",
                    "propagate": False,
                },
                "httpx": {
                    "handlers": ["console", "app_file"],
                    "level": "WARNING",
                    "propagate": False,
                },
                
                # Jupyter-related
                "jupyter_client": {
                    "handlers": ["console", "app_file"],
                    "level": "WARNING",
                    "propagate": False,
                },
                "jupyter_server": {
                    "handlers": ["console", "app_file"],
                    "level": "WARNING",
                    "propagate": False,
                },
            },
            "root": {
                "handlers": ["console", "app_file"],
                "level": log_level,
            },
        }
        
        # Apply the configuration
        logging.config.dictConfig(logging_config)
        
        # Log the configuration
        logger = logging.getLogger("app.logging")
        logger.info(
            "Logging system initialized",
            extra={
                "environment": self.settings.environment,
                "log_level": self.settings.log_level,
                "json_logging": not self.is_development,
                "log_files_enabled": True,
            }
        )
        
        return logging_config


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance
    
    Args:
        name: Logger name (e.g., 'app.services.workspace')
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def setup_logging():
    """
    Initialize the logging system
    """
    config = LoggingConfig()
    return config.setup_logging()


# Module-level logger names for easy import
class LoggerNames:
    """Centralized logger names"""
    APP = "app"
    API = "app.api"
    SERVICES = "app.services"
    MIDDLEWARE = "app.middleware"
    JUPYTER = "app.jupyter"
    ACCESS = "app.access"
    ERRORS = "app.errors"
    
    # Service-specific
    WORKSPACE_SERVICE = "app.services.workspace"
    EXECUTION_SERVICE = "app.services.execution"
    FILE_SERVICE = "app.services.file"
    CLEANUP_SERVICE = "app.services.cleanup"
    
    # Management loggers
    CONCURRENCY_MANAGER = "app.core.concurrency.concurrency_manager"
    FILE_CONCURRENCY_MANAGER = "app.core.concurrency.file_concurrency_manager"
    FILE_LOCK_MANAGER = "app.core.concurrency.file_lock_manager"
    EVENT_BUS = "app.core.events.event_bus"
    
    # API-specific  
    API_ROUTES = "app.api.routes"
    API_DEPENDENCIES = "app.api.dependencies"
    
    # Middleware-specific
    LOGGING_MIDDLEWARE = "app.middleware.logging"
    AUTH_MIDDLEWARE = "app.middleware.auth" 