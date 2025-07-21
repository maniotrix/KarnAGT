#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logging configuration for the code executor module.
"""

import logging
import os
import sys
import inspect

# Default log level
DEFAULT_LOG_LEVEL = logging.INFO

# Store configured loggers to avoid reconfiguration
_configured_loggers = set()

def configure_logging(level=None):
    """
    Configure the logging settings for the code executor module.
    
    Args:
        level: The logging level to use (default: INFO)
    """
    # Use environment variable if set, otherwise use the provided level or default
    log_level = level or os.environ.get('CODE_EXECUTOR_LOG_LEVEL', DEFAULT_LOG_LEVEL)
    
    # Convert string log level to actual level if needed
    if isinstance(log_level, str):
        log_level = getattr(logging, log_level.upper(), DEFAULT_LOG_LEVEL)
    
    return log_level

def _setup_logger(logger_name: str, level=None):
    """
    Set up a specific logger with the code executor configuration.
    
    Args:
        logger_name: Name for the logger
        level: Log level to use
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(logger_name)
    
    # Skip if already configured
    if logger_name in _configured_loggers:
        return logger
    
    # Get log level
    log_level = configure_logging(level)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Set formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Configure logger
    logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Add the console handler
    logger.addHandler(console_handler)
    
    # Disable propagation to prevent duplicate messages from parent loggers
    logger.propagate = False
    
    # Mark as configured
    _configured_loggers.add(logger_name)
    
    return logger

def get_logger(name=None):
    """
    Get a logger with optional custom name.
    
    Args:
        name: Optional logger name. If not provided, tries to detect from caller.
              Can be class name, module name, or any identifier.
              
    Returns:
        Configured logger instance
        
    Examples:
        # Auto-detect from caller
        logger = get_logger()
        
        # Explicit class name  
        logger = get_logger("HTTPCodeExecutorAgent")
        
        # Module name
        logger = get_logger("new_code_tool")
        
        # Method name
        logger = get_logger("execute_code_func")
    """
    if name is None:
        # Try to auto-detect the caller's context
        frame = inspect.currentframe()
        if frame and frame.f_back:
            caller_frame = frame.f_back
            # Get the filename and create a name from it
            filename = caller_frame.f_code.co_filename
            module_name = os.path.basename(filename).replace('.py', '')
            
            # Try to get class name if we're in a class method
            if 'self' in caller_frame.f_locals:
                class_name = caller_frame.f_locals['self'].__class__.__name__
                name = f"code_executor.{module_name}.{class_name}"
            else:
                name = f"code_executor.{module_name}"
        else:
            # Fallback to default
            name = "code_executor"
    elif not name.startswith('code_executor'):
        # Prefix with code_executor for consistency
        name = f"code_executor.{name}"
    
    return _setup_logger(name)

def set_log_level(level):
    """
    Set the logging level for all code executor loggers.
    
    Args:
        level: New log level to apply
    """
    # Clear configured loggers so they get reconfigured with new level
    _configured_loggers.clear()
    
    # Update any existing code_executor loggers
    for logger_name in list(logging.Logger.manager.loggerDict.keys()):
        if logger_name.startswith('code_executor'):
            logger = logging.getLogger(logger_name)
            new_level = configure_logging(level)
            logger.setLevel(new_level)

# Create default logger for backwards compatibility
logger = get_logger("code_executor") 