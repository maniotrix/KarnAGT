#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FastAPI server for per-execution code execution with isolated workspaces.
Each execution gets a fresh workspace with inputs/outputs directories.
"""

import os
import uuid
import shutil
import asyncio
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
import tempfile
import mimetypes

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Import your existing code executor functions
from code_executor import execute_code_string, CodeExecutionResult
from logger import get_logger
from serialization import SerializableResponse

# Configure logger with server-specific name
logger = get_logger("fastapi_server")

# FastAPI app configuration
app = FastAPI(
    title="Code Executor Service",
    description="Per-execution isolated workspace code execution service",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
WORKSPACE_BASE = os.getenv("WORKSPACE_BASE", "/tmp/code-executor-workspaces")
WORKSPACE_TTL_HOURS = int(os.getenv("WORKSPACE_TTL_HOURS", "1"))
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "100")) * 1024 * 1024  # 100MB default
MAX_FILES_PER_EXECUTION = int(os.getenv("MAX_FILES_PER_EXECUTION", "20"))
MAX_WORKSPACE_SIZE = int(os.getenv("MAX_WORKSPACE_SIZE", "200")) * 1024 * 1024  # 200MB

# Server configuration for full URL generation
SERVER_HOST = os.getenv("SERVER_HOST", "localhost")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8080"))
SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", f"http://{SERVER_HOST}:{SERVER_PORT}")

# Ensure workspace directory exists
Path(WORKSPACE_BASE).mkdir(parents=True, exist_ok=True)

# Active workspaces tracking (in production, use Redis or database)
active_workspaces: Dict[str, Dict] = {}

# Request/Response models
class CodeExecutionRequest(BaseModel):
    code: str = Field(..., description="Python code to execute")
    timeout: Optional[int] = Field(30, description="Execution timeout in seconds")

class SystemCommandRequest(BaseModel):
    command: str = Field(..., description="System command to execute")
    allowed_prefixes: Optional[List[str]] = Field(None, description="List of allowed command prefixes for security")

class OutputFileInfo(BaseModel):
    name: str = Field(..., description="Filename")
    download_url: str = Field(..., description="URL to download the file")
    size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type of the file")
    created_at: str = Field(..., description="File creation timestamp")

class ExecutionResponse(BaseModel):
    execution_id: str
    workspace_id: str
    result: Any
    stdout: str
    stderr: str
    status: str
    error: Optional[str]
    output_files: List[OutputFileInfo] = []
    execution_time: float
    workspace_expires_at: str

class SystemCommandResponse(BaseModel):
    execution_id: str
    workspace_id: str
    command: str
    stdout: str
    stderr: str
    status: str
    exit_code: int
    execution_time: float
    workspace_expires_at: str

class HealthCheck(BaseModel):
    status: str
    version: str
    timestamp: datetime
    active_workspaces: int

# Utility functions
def create_execution_workspace() -> str:
    """Create a fresh workspace for code execution."""
    workspace_id = f"workspace-{uuid.uuid4()}"
    workspace_path = Path(WORKSPACE_BASE) / workspace_id
    
    # Create workspace directories
    inputs_dir = workspace_path / "inputs"
    outputs_dir = workspace_path / "outputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    
    # Track workspace
    active_workspaces[workspace_id] = {
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(hours=WORKSPACE_TTL_HOURS),
        "workspace_path": str(workspace_path)
    }
    
    logger.info(f"Created execution workspace: {workspace_id}")
    return workspace_id

def get_workspace_path(workspace_id: str) -> Path:
    """Get the workspace path if valid and not expired."""
    if workspace_id not in active_workspaces:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    workspace_info = active_workspaces[workspace_id]
    if datetime.now() > workspace_info["expires_at"]:
        # Cleanup expired workspace
        cleanup_workspace(workspace_id)
        raise HTTPException(status_code=404, detail="Workspace expired")
    
    return Path(workspace_info["workspace_path"])

def cleanup_workspace(workspace_id: str):
    """Clean up a workspace and remove from tracking."""
    if workspace_id in active_workspaces:
        try:
            workspace_path = Path(active_workspaces[workspace_id]["workspace_path"])
            if workspace_path.exists():
                shutil.rmtree(workspace_path)
            del active_workspaces[workspace_id]
            logger.info(f"Cleaned up workspace: {workspace_id}")
        except Exception as e:
            logger.error(f"Error cleaning up workspace {workspace_id}: {e}")

def scan_output_files(workspace_id: str, outputs_dir: Path) -> List[OutputFileInfo]:
    """Scan outputs directory and generate download URLs for all files."""
    output_files = []
    
    if outputs_dir.exists():
        for file_path in outputs_dir.rglob("*"):
            if file_path.is_file():
                try:
                    # Get file info
                    stat = file_path.stat()
                    relative_path = file_path.relative_to(outputs_dir)
                    mime_type, _ = mimetypes.guess_type(str(file_path))
                    
                    output_files.append(OutputFileInfo(
                        name=file_path.name,
                        download_url=f"{SERVER_BASE_URL}/download/{workspace_id}/{relative_path}",
                        size=stat.st_size,
                        mime_type=mime_type or "application/octet-stream",
                        created_at=datetime.fromtimestamp(stat.st_ctime).isoformat()
                    ))
                except Exception as e:
                    logger.warning(f"Error processing output file {file_path}: {e}")
    
    return output_files

def cleanup_expired_workspaces():
    """Clean up all expired workspaces."""
    now = datetime.now()
    expired_workspaces = [
        wid for wid, info in active_workspaces.items()
        if now > info["expires_at"]
    ]
    
    for workspace_id in expired_workspaces:
        cleanup_workspace(workspace_id)

def validate_file_path(file_path: str) -> bool:
    """Validate that file path is safe (no directory traversal)."""
    try:
        # Normalize the path and check for directory traversal
        normalized = Path(file_path).resolve()
        return ".." not in str(file_path) and not str(file_path).startswith("/")
    except:
        return False
    
def get_serializable_response(content: Any) -> SerializableResponse:
    """Get a SerializableResponse object with the given content."""
    return SerializableResponse(content=content)

# API Endpoints
@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint."""
    cleanup_expired_workspaces()  # Opportunistic cleanup
    
    return HealthCheck(
        status="healthy",
        version="2.0.0", 
        timestamp=datetime.now(),
        active_workspaces=len(active_workspaces)
    )

@app.post("/execute")
async def execute_python_code(
    code: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    timeout: Optional[int] = Form(30)
):
    """Execute Python code in an isolated workspace with optional file uploads."""
    start_time = datetime.now()
    execution_id = str(uuid.uuid4())
    
    # Create fresh workspace for this execution
    workspace_id = create_execution_workspace()
    workspace_path = get_workspace_path(workspace_id)
    inputs_dir = workspace_path / "inputs"
    outputs_dir = workspace_path / "outputs"
    
    try:
        # Handle uploaded files
        if files:
            if len(files) > MAX_FILES_PER_EXECUTION:
                raise HTTPException(
                    status_code=413,
                    detail=f"Too many files. Maximum {MAX_FILES_PER_EXECUTION} files per execution"
                )
            
            for file in files:
                if not file.filename:
                    continue
                    
                # Check file size
                content = await file.read()
                if len(content) > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File {file.filename} too large. Maximum size: {MAX_FILE_SIZE/1024/1024:.1f}MB"
                    )
                
                # Save to inputs directory
                file_path = inputs_dir / file.filename
                with open(file_path, "wb") as f:
                    f.write(content)
                
                logger.info(f"Uploaded file: {file.filename} ({len(content)} bytes)")
        
        # Execute code in workspace (NO CODE INJECTION!)
        original_cwd = os.getcwd()
        try:
            # Simple environment setup - just change working directory
            os.chdir(workspace_path)
            logger.info(f"Executing code in workspace: {workspace_path}")
            
            # Execute the original code as-is
            result = await execute_code_string(code)
            
        finally:
            # Restore original working directory
            os.chdir(original_cwd)
        
        # Scan for output files and generate download URLs
        output_files = scan_output_files(workspace_id, outputs_dir)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        expires_at = active_workspaces[workspace_id]["expires_at"]
        
        logger.info(f"Execution completed: {execution_id}, {len(output_files)} output files")
        
        response_data = {
            "execution_id": execution_id,
            "workspace_id": workspace_id,
            "result": result.result,  # This will be serialized by SerializableResponse
            "stdout": result.stdout or "",
            "stderr": result.stderr or "",
            "status": result.status,
            "error": result.error,
            "output_files": [file.dict() for file in output_files],
            "execution_time": execution_time,
            "workspace_expires_at": expires_at.isoformat()
        }
        
        return get_serializable_response(response_data)
        
    except HTTPException:
        # Cleanup workspace on HTTP errors
        cleanup_workspace(workspace_id)
        raise
    except Exception as e:
        logger.error(f"Error executing code: {e}")
        cleanup_workspace(workspace_id)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        error_data = {
            "execution_id": execution_id,
            "workspace_id": workspace_id,
            "result": None,
            "stdout": "",
            "stderr": str(e),
            "status": "error",
            "error": str(e),
            "output_files": [],
            "execution_time": execution_time,
            "workspace_expires_at": datetime.now().isoformat()
        }
        
        return get_serializable_response(error_data)

@app.post("/system-command")
async def execute_system_command_endpoint(request: SystemCommandRequest):
    """Execute a system command in an isolated workspace with security filtering."""
    start_time = datetime.now()
    execution_id = str(uuid.uuid4())
    
    # Create fresh workspace for this execution
    workspace_id = create_execution_workspace()
    workspace_path = get_workspace_path(workspace_id)
    
    try:
        # Default security: only allow python and pip commands
        allowed_prefixes = request.allowed_prefixes
        if allowed_prefixes is None:
            allowed_prefixes = ["python ", "pip ", "python -m "]
        
        # Security check
        if not any(request.command.startswith(prefix) for prefix in allowed_prefixes):
            logger.warning(f"Command not allowed: {request.command}")
            cleanup_workspace(workspace_id)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            expires_at = active_workspaces.get(workspace_id, {}).get("expires_at", datetime.now())
            
            error_data = {
                "execution_id": execution_id,
                "workspace_id": workspace_id,
                "command": request.command,
                "stdout": "",
                "stderr": f"Command not allowed. Must start with one of: {', '.join(allowed_prefixes)}",
                "status": "error",
                "exit_code": 1,
                "execution_time": execution_time,
                "workspace_expires_at": expires_at.isoformat() if hasattr(expires_at, 'isoformat') else str(expires_at)
            }
            
            return get_serializable_response(error_data)
        
        # Execute command in workspace context
        original_cwd = os.getcwd()
        try:
            # Change to workspace directory for execution
            os.chdir(workspace_path)
            logger.info(f"Executing system command in workspace {workspace_id}: {request.command}")
            
            # Use subprocess to execute the command
            process = subprocess.Popen(
                request.command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(workspace_path)
            )
            
            # Capture output
            stdout, stderr = process.communicate()
            exit_code = process.returncode
            
            logger.info(f"Command completed with exit code: {exit_code}")
            if stdout:
                logger.debug(f"Command stdout: {stdout}")
            if stderr:
                logger.debug(f"Command stderr: {stderr}")
                
        finally:
            # Restore original working directory
            os.chdir(original_cwd)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        expires_at = active_workspaces[workspace_id]["expires_at"]
        
        logger.info(f"System command execution completed: {execution_id}")
        
        response_data = {
            "execution_id": execution_id,
            "workspace_id": workspace_id,
            "command": request.command,
            "stdout": stdout,
            "stderr": stderr,
            "status": "success" if exit_code == 0 else "error",
            "exit_code": exit_code,
            "execution_time": execution_time,
            "workspace_expires_at": expires_at.isoformat()
        }
        
        return get_serializable_response(response_data)
        
    except HTTPException:
        # Cleanup workspace on HTTP errors
        cleanup_workspace(workspace_id)
        raise
    except Exception as e:
        logger.error(f"Error executing system command: {e}")
        cleanup_workspace(workspace_id)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        error_data = {
            "execution_id": execution_id,
            "workspace_id": workspace_id,
            "command": request.command,
            "stdout": "",
            "stderr": f"Error executing command: {str(e)}",
            "status": "error",
            "exit_code": 1,
            "execution_time": execution_time,
            "workspace_expires_at": datetime.now().isoformat()
        }
        
        return get_serializable_response(error_data)

@app.get("/download/{workspace_id}/{file_path:path}")
async def download_file(workspace_id: str, file_path: str, request: Request):
    """Download a file from an execution workspace."""
    
    # Validate workspace
    try:
        workspace_path = get_workspace_path(workspace_id)
    except HTTPException:
        raise HTTPException(404, "Workspace not found or expired")
    
    # Validate file path for security
    if not validate_file_path(file_path):
        raise HTTPException(403, "Invalid file path")
    
    # Build full file path
    outputs_dir = workspace_path / "outputs"
    full_file_path = outputs_dir / file_path
    
    # Security check: Ensure file is within outputs directory
    try:
        full_file_path.resolve().relative_to(outputs_dir.resolve())
    except ValueError:
        raise HTTPException(403, "Access denied - path outside outputs directory")
    
    # Check file exists
    if not full_file_path.exists() or not full_file_path.is_file():
        raise HTTPException(404, "File not found")
    
    # Get MIME type
    mime_type, _ = mimetypes.guess_type(str(full_file_path))
    
    logger.info(f"Downloading file: {workspace_id}/{file_path}")
    
    # Return file
    return FileResponse(
        path=str(full_file_path),
        filename=Path(file_path).name,
        media_type=mime_type or "application/octet-stream"
    )

@app.get("/workspace/{workspace_id}/files")
async def list_workspace_files(workspace_id: str):
    """List all files in a workspace (inputs and outputs)."""
    try:
        workspace_path = get_workspace_path(workspace_id)
    except HTTPException:
        raise HTTPException(404, "Workspace not found or expired")
    
    inputs_dir = workspace_path / "inputs"
    outputs_dir = workspace_path / "outputs"
    
    # Scan input files
    input_files = []
    if inputs_dir.exists():
        for file_path in inputs_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                mime_type, _ = mimetypes.guess_type(str(file_path))
                
                input_files.append({
                    "name": file_path.name,
                    "size": stat.st_size,
                    "mime_type": mime_type or "application/octet-stream",
                    "uploaded_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
                })
    
    # Get output files with download URLs
    output_files = scan_output_files(workspace_id, outputs_dir)
    
    return {
        "workspace_id": workspace_id,
        "expires_at": active_workspaces[workspace_id]["expires_at"].isoformat(),
        "input_files": input_files,
        "output_files": [file.dict() for file in output_files]
    }

@app.delete("/workspace/{workspace_id}")
async def delete_workspace(workspace_id: str):
    """Manually delete a workspace and all its files."""
    if workspace_id not in active_workspaces:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    cleanup_workspace(workspace_id)
    return {"message": f"Workspace {workspace_id} deleted successfully"}

@app.get("/workspaces")
async def list_active_workspaces():
    """List all active workspaces."""
    cleanup_expired_workspaces()  # Clean up first
    
    return {
        "active_workspaces": len(active_workspaces),
        "workspaces": [
            {
                "workspace_id": wid,
                "created_at": info["created_at"].isoformat(),
                "expires_at": info["expires_at"].isoformat()
            }
            for wid, info in active_workspaces.items()
        ]
    }

# Background task for cleanup
@app.on_event("startup")
async def startup_event():
    """Initialize the service."""
    logger.info("Code Executor Service v2.0 starting up...")
    logger.info(f"Workspace base directory: {WORKSPACE_BASE}")
    logger.info(f"Workspace TTL: {WORKSPACE_TTL_HOURS} hours")
    logger.info(f"Max file size: {MAX_FILE_SIZE/1024/1024:.1f}MB")
    logger.info("Per-execution workspace mode enabled")

# Periodic cleanup task
async def periodic_cleanup():
    """Periodic cleanup of expired workspaces."""
    while True:
        try:
            cleanup_expired_workspaces()
            await asyncio.sleep(300)  # Run every 5 minutes
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")
            await asyncio.sleep(60)  # Retry after 1 minute

@app.on_event("startup")
async def start_background_tasks():
    """Start background tasks."""
    asyncio.create_task(periodic_cleanup())

# Main entry point
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting Code Executor Service v2.0 on {host}:{port}")
    
    uvicorn.run(
        "fastapi_server:app",
        host=host,
        port=port,
        reload=False,
        access_log=True,
        log_level="info"
    ) 