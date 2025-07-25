#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Function tool implementation for executing code in agent tools via HTTP FastAPI server.
Provides secure, isolated code execution with per-execution workspaces and automatic file handling.
"""

import inspect
import asyncio
import os
from typing import Any, Dict, Optional, List
import aiohttp
from pydantic import BaseModel
from agents import function_tool
from app.logging.logger import get_logger, set_log_level

# Get logger with module-specific name
logger = get_logger(__name__)
set_log_level("DEBUG")

# Configuration
FASTAPI_SERVER_URL = os.getenv("FASTAPI_CODE_EXECUTOR_URL", "http://localhost:8080")
DEFAULT_TIMEOUT = int(os.getenv("CODE_EXECUTOR_TIMEOUT", "60"))
MAX_RETRIES = int(os.getenv("CODE_EXECUTOR_MAX_RETRIES", "3"))

class CodeExecutionResult(BaseModel):
    """Result of executing code via HTTP server with per-execution workspace"""
    execution_id: str
    workspace_id: str  # Changed from session_id
    result: Any
    stdout: str
    stderr: str
    status: str
    error: Optional[str]
    output_files: List[Dict[str, Any]] = []
    downloaded_files: Dict[str, Dict[str, Any]] = {}  # filename -> {content: bytes, metadata...}
    execution_time: float
    workspace_expires_at: str

class SystemCommandResult(BaseModel):
    """Result of running a system command via HTTP server"""
    execution_id: str
    workspace_id: str  # Changed from session_id
    command: str
    stdout: str
    stderr: str
    status: str
    exit_code: int
    execution_time: float
    workspace_expires_at: str

class CodeExecutorHTTPClient:
    """HTTP client for interacting with the per-execution FastAPI code executor service"""
    
    def __init__(self, base_url: str = FASTAPI_SERVER_URL):
        self.base_url = base_url.rstrip('/')
        
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling and retries"""
        url = f"{self.base_url}{endpoint}"
        
        async with aiohttp.ClientSession() as session:
            for attempt in range(MAX_RETRIES):
                try:
                    logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                    
                    async with session.request(method, url, **kwargs) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            error_text = await response.text()
                            raise aiohttp.ClientResponseError(
                                request_info=response.request_info,
                                history=response.history,
                                status=response.status,
                                message=f"HTTP {response.status}: {error_text}"
                            )
                            
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    if attempt == MAX_RETRIES - 1:  # Last attempt
                        raise e
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        # This should never be reached due to exceptions, but satisfy the type checker
        raise RuntimeError("Unexpected end of _make_request function")
                    
    async def health_check(self) -> bool:
        """Check if the FastAPI server is running"""
        try:
            result = await self._make_request("GET", "/health")
            return result.get("status") == "healthy"
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
            
    async def execute_code_http(self, code: str, files: Optional[List[tuple]] = None, timeout: int = DEFAULT_TIMEOUT) -> CodeExecutionResult:
        """Execute code via HTTP server with per-execution workspace"""
        try:
            # Prepare form data for multipart request
            data = aiohttp.FormData()
            data.add_field('code', code)
            data.add_field('timeout', str(timeout))
            
            # Add files if provided
            if files:
                for filename, content in files:
                    if isinstance(content, str):
                        content = content.encode('utf-8')
                    data.add_field('files', content, filename=filename)
            
            url = f"{self.base_url}/execute"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, 
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=timeout + 10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return CodeExecutionResult(**result)
                    else:
                        error_text = await response.text()
                        raise RuntimeError(f"Code execution failed: HTTP {response.status}: {error_text}")
            
        except Exception as e:
            logger.error(f"Code execution failed: {e}")
            # Return error result instead of raising
            return CodeExecutionResult(
                execution_id="error",
                workspace_id="unknown",
                result=None,
                stdout="",
                stderr=str(e),
                status="error",
                error=str(e),
                output_files=[],
                downloaded_files={},
                execution_time=0.0,
                workspace_expires_at=""
            )
            
    async def execute_system_command_http(self, command: str, allowed_prefixes: Optional[List[str]] = None) -> SystemCommandResult:
        """Execute system command via HTTP server"""
        try:
            payload = {
                "command": command,
                "allowed_prefixes": allowed_prefixes
            }
            
            result = await self._make_request(
                "POST",
                "/system-command", 
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            return SystemCommandResult(**result)
            
        except Exception as e:
            logger.error(f"System command execution failed: {e}")
            # Return error result instead of raising
            return SystemCommandResult(
                execution_id="error",
                workspace_id="unknown",
                command=command,
                stdout="",
                stderr=str(e),
                status="error",
                exit_code=1,
                execution_time=0.0,
                workspace_expires_at=""
            )
            
    async def download_file(self, workspace_id: str = None, filename: str = None, full_url: str = None) -> bytes:
        """Download a file from workspace outputs directory or from full URL"""
        file_identifier = "unknown"  # Initialize for error logging
        try:
            if full_url:
                url = full_url
                file_identifier = full_url.split('/')[-1]  # Get filename from URL for logging
            else:
                url = f"{self.base_url}/download/{workspace_id}/{filename}"
                file_identifier = filename or "unknown"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        logger.info(f"Downloaded file {file_identifier}: {len(content)} bytes")
                        return content
                    else:
                        error_text = await response.text()
                        raise RuntimeError(f"File download failed: HTTP {response.status}: {error_text}")
                        
        except Exception as e:
            logger.error(f"Failed to download file {file_identifier}: {e}")
            raise RuntimeError(f"File download failed: {e}")

# Global HTTP client instance
_http_client = CodeExecutorHTTPClient()

@function_tool(strict_mode=False)
async def execute_code(
    code: str, 
    files: Optional[List[tuple]] = None, 
    timeout: int = DEFAULT_TIMEOUT, 
    download_files: bool = False,
    *args: Any, 
    **kwargs: Any
) -> CodeExecutionResult:   
    """
    Execute Python code via secure HTTP FastAPI server with automatic file handling.
    
    Each execution gets a fresh isolated workspace with inputs/ and outputs/ directories.
    This tool automatically handles:
    - Fresh workspace creation for each execution
    - File uploads (if files provided)
    - Code execution in isolated environment
    - Optional download of any generated output files (plots, CSVs, etc.)
    
    Args:
        code: Python code to execute. Use relative paths:
              - Read input files from: 'inputs/filename.ext'
              - Save output files to: 'outputs/filename.ext'
        files: Optional list of (filename, content) tuples to upload before execution
        timeout: Execution timeout in seconds (default: 60)
        download_files: Whether to automatically download generated output files (default: True)
        *args: Additional args (for compatibility)
        **kwargs: Additional kwargs (for compatibility)
        
    Returns:
        CodeExecutionResult with execution results and optionally downloaded files:
        - execution_id: Unique execution identifier
        - workspace_id: Workspace used for this execution
        - result: Execution result (if any)
        - stdout: Standard output from code execution
        - stderr: Standard error from code execution  
        - status: "success" or "error"
        - error: Error message (if status is "error")
        - output_files: List of file metadata with full download URLs for generated files
        - downloaded_files: Dict mapping filename -> {content: bytes, download_url: str, size: int, mime_type: str, created_at: str} for downloaded files
        - execution_time: Execution duration in seconds
        - workspace_expires_at: When workspace will be cleaned up
        
    Example:
        # Execute code that generates a plot (with automatic download)
        result = await execute_code('''
import matplotlib
matplotlib.use('Agg')  # For headless environments
import matplotlib.pyplot as plt
import os

os.makedirs('outputs', exist_ok=True)
plt.plot([1,2,3,4], [1,4,2,3])
plt.savefig('outputs/my_plot.png')
print("Plot created!")
        ''')
        
        # Access the generated plot automatically
        if "my_plot.png" in result.downloaded_files:
            file_info = result.downloaded_files["my_plot.png"]
            plot_data = file_info["content"]  # PNG file content as bytes
            download_url = file_info["download_url"]  # Full HTTP download URL
            print(f"Downloaded: {download_url}")
            
    Example with file upload:
        # Process uploaded CSV file
        csv_data = "name,value\\nAlice,10\\nBob,20"
        result = await execute_code('''
import pandas as pd
import os

df = pd.read_csv('inputs/data.csv')
processed = df.copy()
processed['doubled'] = df['value'] * 2

os.makedirs('outputs', exist_ok=True)
processed.to_csv('outputs/processed.csv', index=False)
print(f"Processed {len(df)} rows")
        ''', files=[("data.csv", csv_data)])
        
        # Access processed file
        if "processed.csv" in result.downloaded_files:
            file_info = result.downloaded_files["processed.csv"]
            csv_content = file_info["content"].decode('utf-8')
            download_url = file_info["download_url"]
    """
    return await execute_code_func(code, files, timeout, download_files, *args, **kwargs)

async def execute_code_func(
    code: str, 
    files: Optional[List[tuple]] = None, 
    timeout: int = DEFAULT_TIMEOUT, 
    download_files: bool = False,
    *args: Any, 
    **kwargs: Any
) -> CodeExecutionResult:
    """
    Execute Python code via secure HTTP FastAPI server with automatic file handling.
    
    Each execution gets a fresh isolated workspace with inputs/ and outputs/ directories.
    This tool automatically handles:
    - Fresh workspace creation for each execution
    - File uploads (if files provided)
    - Code execution in isolated environment
    - Optional download of any generated output files (plots, CSVs, etc.)
    
    Args:
        code: Python code to execute. Use relative paths:
              - Read input files from: 'inputs/filename.ext'
              - Save output files to: 'outputs/filename.ext'
        files: Optional list of (filename, content) tuples to upload before execution
        timeout: Execution timeout in seconds (default: 60)
        download_files: Whether to automatically download generated output files (default: True)
        *args: Additional args (for compatibility)
        **kwargs: Additional kwargs (for compatibility)
        
    Returns:
        CodeExecutionResult with execution results and optionally downloaded files:
        - execution_id: Unique execution identifier
        - workspace_id: Workspace used for this execution
        - result: Execution result (if any)
        - stdout: Standard output from code execution
        - stderr: Standard error from code execution  
        - status: "success" or "error"
        - error: Error message (if status is "error")
        - output_files: List of file metadata with full download URLs for generated files
        - downloaded_files: Dict mapping filename -> {content: bytes, download_url: str, size: int, mime_type: str, created_at: str} for downloaded files
        - execution_time: Execution duration in seconds
        - workspace_expires_at: When workspace will be cleaned up
        
    Example:
        # Execute code that generates a plot (with automatic download)
        result = await execute_code_func('''
import matplotlib
matplotlib.use('Agg')  # For headless environments
import matplotlib.pyplot as plt
import os

os.makedirs('outputs', exist_ok=True)
plt.plot([1,2,3,4], [1,4,2,3])
plt.savefig('outputs/my_plot.png')
print("Plot created!")
        ''')
        
        # Access the generated plot automatically
        if "my_plot.png" in result.downloaded_files:
            file_info = result.downloaded_files["my_plot.png"]
            plot_data = file_info["content"]  # PNG file content as bytes
            download_url = file_info["download_url"]  # Full HTTP download URL
            print(f"Downloaded: {download_url}")
            
    Example with file upload:
        # Process uploaded CSV file
        csv_data = "name,value\\nAlice,10\\nBob,20"
        result = await execute_code('''
import pandas as pd
import os

df = pd.read_csv('inputs/data.csv')
processed = df.copy()
processed['doubled'] = df['value'] * 2

os.makedirs('outputs', exist_ok=True)
processed.to_csv('outputs/processed.csv', index=False)
print(f"Processed {len(df)} rows")
        ''', files=[("data.csv", csv_data)])
        
        # Access processed file
        if "processed.csv" in result.downloaded_files:
            file_info = result.downloaded_files["processed.csv"]
            csv_content = file_info["content"].decode('utf-8')
            download_url = file_info["download_url"]
    """
    # Get caller information for debugging
    caller_frame = inspect.currentframe().f_back if inspect.currentframe() else None
    caller_info = f"{caller_frame.f_code.co_filename}:{caller_frame.f_lineno}" if caller_frame else "unknown"
    
    logger.info(f"execute_code called from {caller_info}")
    logger.info(f"Files to upload: {len(files) if files else 0}")
    logger.info(f"Code length: {len(code)} characters")
    logger.debug(f"Full code:\n```python\n{code}\n```")
    
    try:
        # Health check first
        if not await _http_client.health_check():
            logger.error("FastAPI server is not available")
            return CodeExecutionResult(
                execution_id="error",
                workspace_id="unknown",
                result=None,
                stdout="",
                stderr="FastAPI server is not available. Please ensure the server is running at " + FASTAPI_SERVER_URL,
                status="error",
                error="Server not available",
                output_files=[],
                downloaded_files={},
                execution_time=0.0,
                workspace_expires_at=""
            )
        
        # Execute the code with files (if any) in fresh workspace
        result = await _http_client.execute_code_http(code, files, timeout)
    
        logger.info(f"Code execution completed: status={result.status}, time={result.execution_time:.3f}s")
        logger.info(f"Workspace ID: {result.workspace_id}")
        
        # Optionally download generated output files
        if result.output_files and download_files:
            logger.info(f"Generated {len(result.output_files)} output files - downloading automatically...")
            downloaded_files = {}
            
            for file_info in result.output_files:
                file_name = file_info["name"]
                download_url = file_info["download_url"]
                try:
                    file_content = await _http_client.download_file(full_url=download_url)
                    # Store file with full metadata
                    downloaded_files[file_name] = {
                        "content": file_content,
                        "download_url": download_url,
                        "size": file_info.get("size", len(file_content)),
                        "mime_type": file_info.get("mime_type", "application/octet-stream"),
                        "created_at": file_info.get("created_at", "")
                    }
                    logger.info(f"Downloaded {file_name}: {len(file_content)} bytes from {download_url}")
                except Exception as e:
                    logger.error(f"Failed to download {file_name}: {e}")
                    # Continue with other files even if one fails
            
            # Add downloaded files to result
            result.downloaded_files = downloaded_files
            logger.info(f"Successfully downloaded {len(downloaded_files)} files with metadata")
        elif result.output_files and not download_files:
            logger.info(f"Generated {len(result.output_files)} output files - download_files=False, skipping download")
        else:
            logger.info("No output files generated")
            
        return result
        
    except Exception as e:
        logger.error(f"Unexpected error in execute_code: {e}")
        return CodeExecutionResult(
            execution_id="error",
            workspace_id="unknown",
            result=None,
            stdout="",
            stderr=f"Unexpected error: {e}",
            status="error",
            error=str(e),
            output_files=[],
            downloaded_files={},
            execution_time=0.0,
            workspace_expires_at=""
        )
        
        

@function_tool(strict_mode=False)
async def execute_system_command(command: str, allowed_prefixes: Optional[List[str]] = None) -> SystemCommandResult:
    """
    Execute system command via secure HTTP FastAPI server for environment setup.
    
    Each command gets a fresh isolated workspace for execution.
    This tool automatically handles:
    - Fresh workspace creation for each command
    - Command execution with security filtering
    
    Primary use cases: package installation, environment setup, simple commands.
    For code that generates files, use execute_code instead.
    
    Args:
        command: System command to execute
        allowed_prefixes: List of allowed command prefixes for security (default: ["python ", "pip ", "python -m "])
        
    Returns:
        SystemCommandResult with command execution results:
        - execution_id: Unique execution identifier
        - workspace_id: Workspace used for execution
        - command: The command that was executed
        - stdout: Command standard output
        - stderr: Command standard error
        - status: "success" or "error"
        - exit_code: Command exit code
        - execution_time: Execution duration in seconds
        - workspace_expires_at: When workspace will be cleaned up
        
    Example:
        # Install a package
        result = await execute_system_command("pip install matplotlib")
        
        # Check installation success
        if result.status == "success":
            print(f"Package installed: {result.stdout}")
    """
    return await execute_system_command_func(command, allowed_prefixes)

async def execute_system_command_func(command: str, allowed_prefixes: Optional[List[str]] = None) -> SystemCommandResult:
    """
    Execute system command via secure HTTP FastAPI server for environment setup.
    
    Each command gets a fresh isolated workspace for execution.
    This tool automatically handles:
    - Fresh workspace creation for each command
    - Command execution with security filtering
    
    Primary use cases: package installation, environment setup, simple commands.
    For code that generates files, use execute_code instead.
    
    Args:
        command: System command to execute
        allowed_prefixes: List of allowed command prefixes for security (default: ["python ", "pip ", "python -m "])
        
    Returns:
        SystemCommandResult with command execution results:
        - execution_id: Unique execution identifier
        - workspace_id: Workspace used for execution
        - command: The command that was executed
        - stdout: Command standard output
        - stderr: Command standard error
        - status: "success" or "error"
        - exit_code: Command exit code
        - execution_time: Execution duration in seconds
        - workspace_expires_at: When workspace will be cleaned up
        
    Example:
        # Install a package
        result = await execute_system_command("pip install matplotlib")
        
        # Check installation success
        if result.status == "success":
            print(f"Package installed: {result.stdout}")
    """
    # Get caller information for debugging
    caller_frame = inspect.currentframe().f_back if inspect.currentframe() else None
    caller_info = f"{caller_frame.f_code.co_filename}:{caller_frame.f_lineno}" if caller_frame else "unknown"
    
    logger.info(f"execute_system_command called from {caller_info}")
    logger.info(f"Command: {command}")
    
    try:
        # Health check first
        if not await _http_client.health_check():
            logger.error("FastAPI server is not available")
            return SystemCommandResult(
                execution_id="error",
                workspace_id="unknown",
                command=command,
                stdout="",
                stderr="FastAPI server is not available. Please ensure the server is running at " + FASTAPI_SERVER_URL,
                status="error",
                exit_code=1,
                execution_time=0.0,
                workspace_expires_at=""
            )
        
        # Execute the system command
        result = await _http_client.execute_system_command_http(command, allowed_prefixes)
        
        logger.info(f"System command completed: status={result.status}, exit_code={result.exit_code}")
        logger.debug(f"result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Unexpected error in execute_system_command: {e}")
        return SystemCommandResult(
            execution_id="error",
            workspace_id="unknown",
            command=command,
            stdout="",
            stderr=f"Unexpected error: {e}",
            status="error",
            exit_code=1,
            execution_time=0.0,
            workspace_expires_at=""
        )



