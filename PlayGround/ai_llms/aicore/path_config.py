#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Path configuration for the AgentMeet project.
This module centralizes all path-related configurations to make directory 
management consistent across the application.
"""

import os
import sys
from pathlib import Path


current_dir = Path(__file__).parent

ROOT_DIR = current_dir

# Main directories
WORKSPACE_DIR = ROOT_DIR
DATA_DIR = os.path.join(ROOT_DIR, "data")
LOGS_DIR = os.path.join(ROOT_DIR, "logs")
CONFIG_DIR = os.path.join(ROOT_DIR, "config")

# Chat system directories
CHAT_SYSTEM_DIR = ROOT_DIR
CODE_EXECUTOR_DIR = os.path.join(CHAT_SYSTEM_DIR, "code_executor")

# Output directories
OUTPUT_DIR = os.path.join(ROOT_DIR, "output")
PLOTS_DIR = os.path.join(DATA_DIR, "output_plots")

# Ensure essential directories exist
ESSENTIAL_DIRS = [DATA_DIR, LOGS_DIR, OUTPUT_DIR, PLOTS_DIR]
for directory in ESSENTIAL_DIRS:
    os.makedirs(directory, exist_ok=True)

def get_path(path_name):
    """
    Get the absolute path for a named directory.
    
    Args:
        path_name: Name of the directory path to retrieve
        
    Returns:
        str: Absolute path to the requested directory
        
    Raises:
        KeyError: If path_name is not defined in this module
    """
    if path_name in globals():
        return globals()[path_name]
    else:
        raise KeyError(f"Path '{path_name}' not defined in path_config")

def join_path(base_path_name, *args):
    """
    Join a base path with additional path components.
    
    Args:
        base_path_name: Name of the base directory path
        *args: Additional path components to join
        
    Returns:
        str: Joined path
    """
    base_path = get_path(base_path_name)
    return os.path.join(base_path, *args)

if __name__ == "__main__":
    # Print all paths when module is run directly
    print("AgentMeet Path Configuration:")
    # Create a copy of the paths to avoid modifying globals during iteration
    path_dict = {var_name: value for var_name, value in globals().items() 
               if var_name.isupper() and isinstance(value, str)}
    
    for var_name, value in path_dict.items():
        if os.path.exists(value):
            print(f"{var_name}: {value}")
