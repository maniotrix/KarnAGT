#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Function tool implementation for executing code in agent tools.
"""

import inspect
import subprocess
import sys
from typing import Any, Dict, Optional, List
from pydantic import BaseModel
from agents import function_tool
from aicore.code_executor.code_executor import execute_code_string, CodeExecutionResult
from aicore.code_executor.logger import get_logger

# Get logger
logger = get_logger()

class SystemCommandResult(BaseModel):
    """Result of running a system command"""
    stdout: str
    stderr: str
    status: str
    exit_code: int

@function_tool(strict_mode=False)
async def execute_code(code: str, *args: Any, **kwargs: Any) -> CodeExecutionResult:
    """
    Execute the provided code string with the given arguments.
    
    Args:
        code: String containing Python code to execute
        *args: Variable positional arguments to pass to the function
        **kwargs: Variable keyword arguments to pass to the function
        
    Returns:
        A result object containing the execution result or error
    """
    # Get caller information for debugging
    caller_frame = inspect.currentframe().f_back
    caller_info = f"{caller_frame.f_code.co_filename}:{caller_frame.f_lineno}"
    
    logger.info(f"execute_code called from {caller_info}")
    logger.info(f"args: {args}")
    logger.info(f"kwargs: {kwargs}")
    logger.debug(f"Full code:\n```python\n{code}\n```")
    
    # Execute the code and return the result
    # Note: execute_code_string now only takes the code string.
    # It expects the code string to be self-contained and assign output to a 'result' variable.
    # The *args and **kwargs passed to this tool are now ignored by the executor.
    result = await execute_code_string(code)
    
    logger.info(f"execution complete, status: {result.status}")
    return result

@function_tool(strict_mode=False)
async def execute_system_command(command: str, allowed_prefixes: Optional[List[str]] = None) -> SystemCommandResult:
    """
    Execute a system command for environment setup
    
    Args:
        command: The command to execute
        allowed_prefixes: List of allowed command prefixes (for security)
        
    Returns:
        SystemCommandResult with stdout, stderr, and status
    """
    # Get caller information for debugging
    caller_frame = inspect.currentframe().f_back
    caller_info = f"{caller_frame.f_code.co_filename}:{caller_frame.f_lineno}"
    
    logger.info(f"execute_system_command called from {caller_info}")
    logger.info(f"command: {command}")
    
    # Default security: only allow python and pip commands
    if allowed_prefixes is None:
        allowed_prefixes = ["python ", "pip ", "python -m "]
    
    # Security check
    if not any(command.startswith(prefix) for prefix in allowed_prefixes):
        logger.warning(f"Command not allowed: {command}")
        return SystemCommandResult(
            stdout="",
            stderr=f"Command not allowed. Must start with one of: {', '.join(allowed_prefixes)}",
            status="error",
            exit_code=1
        )
    
    try:
        # Use subprocess to execute the command
        logger.info(f"Executing system command: {command}")
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Capture output
        stdout, stderr = process.communicate()
        exit_code = process.returncode
        
        logger.info(f"Command completed with exit code: {exit_code}")
        if stdout:
            logger.debug(f"Command stdout: {stdout}")
        if stderr:
            logger.debug(f"Command stderr: {stderr}")
        
        return SystemCommandResult(
            stdout=stdout,
            stderr=stderr,
            status="success" if exit_code == 0 else "error",
            exit_code=exit_code
        )
    except Exception as e:
        logger.error(f"Error executing system command: {str(e)}")
        return SystemCommandResult(
            stdout="",
            stderr=f"Error executing command: {str(e)}",
            status="error",
            exit_code=1
        )