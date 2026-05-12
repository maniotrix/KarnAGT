#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logging module for the chat system.
"""

import logging
import os
import sys
from datetime import datetime
from typing import Optional

# Configure logging format
DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DEBUG_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s"

# Create logs directory if it doesn't exist
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Set up log file with timestamp
LOG_FILE = os.path.join(LOG_DIR, f"aicore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Keep track of loggers
_loggers = {}

def get_logger(name: str, log_level: Optional[int] = None) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Parameters:
    -----------
    name : str
        The name of the logger, typically __name__ of the calling module
    log_level : int, optional
        The logging level. If None, uses INFO level
        
    Returns:
    --------
    logging.Logger
        The configured logger
    """
    if name in _loggers:
        return _loggers[name]
    
    # Default log level if not specified
    if log_level is None:
        log_level = logging.INFO
    
    # Create the logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    logger.propagate = False
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Use more detailed format for debug level
    if log_level == logging.DEBUG:
        formatter = logging.Formatter(DEBUG_LOG_FORMAT)
    else:
        formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Add file handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Store the logger
    _loggers[name] = logger
    
    return logger

def set_log_level(level: str or int) -> None:
    """
    Set the log level for all registered loggers.
    
    Parameters:
    -----------
    level : str or int
        The logging level to set
    """
    if isinstance(level, str):
        level = level.upper()
        
    if level == "CRITICAL" or level == logging.CRITICAL:
        log_level = logging.CRITICAL
    elif level == "ERROR" or level == logging.ERROR:
        log_level = logging.ERROR
    elif level == "WARNING" or level == logging.WARNING:
        log_level = logging.WARNING
    elif level == "INFO" or level == logging.INFO:
        log_level = logging.INFO
    elif level == "DEBUG" or level == logging.DEBUG:
        log_level = logging.DEBUG
    else:
        raise ValueError(f'Undefined log level "{level}"')
    
    for logger in _loggers.values():
        logger.setLevel(log_level) 