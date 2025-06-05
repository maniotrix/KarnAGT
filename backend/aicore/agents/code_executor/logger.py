#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logging configuration for the code executor module.
"""

import logging
import os
import sys

# Create the logger
logger = logging.getLogger('code_executor')

# Default log level
DEFAULT_LOG_LEVEL = logging.INFO

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
    
    # Remove existing handlers to avoid duplicates when reconfiguring
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Add the console handler
    logger.addHandler(console_handler)
    
    return logger

# Initialize with default configuration
configure_logging()

def get_logger():
    """Get the code executor logger"""
    return logger

def set_log_level(level):
    """Set the logging level"""
    configure_logging(level) 