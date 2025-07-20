#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FastAPI server wrapper for the code executor system.
Provides HTTP endpoints for code execution, system commands, and file handling.
"""

import os
import uuid
import shutil
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
import tempfile
import mimetypes

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Import your existing code executor functions
from code_executor import execute_code_string, CodeExecutionResult
from code_tool import SystemCommandResult
from logger import get_logger
import subprocess
import sys

# Configure logger
logger = get_logger()

# FastAPI app configuration
app = FastAPI(
    title="Code Executor Service",
    description="Secure code execution service with file handling capabilities",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for development (configure appropriately for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
WORKSPACE_BASE = os.getenv("WORKSPACE_BASE", "/tmp/code-executor-sessions")
SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "24"))
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "100")) * 1024 * 1024  # 100MB default
MAX_FILES_PER_SESSION = int(os.getenv("MAX_FILES_PER_SESSION", "50"))

# Ensure workspace directory exists
Path(WORKSPACE_BASE).mkdir(parents=True, exist_ok=True)

# Session storage (in production, use Redis or database)
active_sessions: Dict[str, Dict] = {}

# Request/Response models
class CodeExecutionRequest(BaseModel):
    code: str = Field(..., description="Python code to execute")
    timeout: Optional[int] = Field(30, description="Execution timeout in seconds")
    session_id: Optional[str] = Field(None, description="Session ID for file access")

class SystemCommandRequest(BaseModel):
    command: str = Field(..., description="System command to execute") 
    allowed_prefixes: Optional[List[str]] = Field(None, description="Allowed command prefixes")
    session_id: Optional[str] = Field(None, description="Session ID for file access")

class ExecutionResponse(BaseModel):
    execution_id: str
    session_id: str
    result: Any
    stdout: str
    stderr: str
    status: str
    error: Optional[str]
    output_files: List[Dict[str, Any]] = []
    execution_time: float

class SessionInfo(BaseModel):
    session_id: str
    created_at: datetime
    workspace_path: str
    input_files: List[str] = []
    output_files: List[str] = []

class HealthCheck(BaseModel):
    status: str
    version: str
    timestamp: datetime

# Utility functions
def create_session() -> str:
    """Create a new execution session with workspace."""
    session_id = str(uuid.uuid4())
    session_path = Path(WORKSPACE_BASE) / session_id
    
    # Create session directories
    input_dir = session_path / "inputs"
    output_dir = session_path / "outputs" 
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Store session info  
    active_sessions[session_id] = {
        "created_at": datetime.now(),
        "workspace_path": str(session_path),
        "input_files": [],
        "output_files": []
    }
    
    logger.info(f"Created new session: {session_id}")
    return session_id

def get_session_path(session_id: str) -> Path:
    """Get the workspace path for a session."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return Path(active_sessions[session_id]["workspace_path"])

def cleanup_expired_sessions():
    """Clean up expired sessions."""
    now = datetime.now()
    expired_sessions = []
    
    for session_id, session_data in active_sessions.items():
        created_at = session_data["created_at"]
        if now - created_at > timedelta(hours=SESSION_TTL_HOURS):
            expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        try:
            session_path = Path(active_sessions[session_id]["workspace_path"])
            if session_path.exists():
                shutil.rmtree(session_path)
            del active_sessions[session_id]
            logger.info(f"Cleaned up expired session: {session_id}")
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")

def scan_output_files(session_id: str) -> List[Dict[str, Any]]:
    """Scan session output directory for generated files."""
    try:
        session_path = get_session_path(session_id)
        output_dir = session_path / "outputs"
        
        output_files = []
        if output_dir.exists():
            for file_path in output_dir.rglob("*"):
                if file_path.is_file():
                    stat = file_path.stat()
                    mime_type, _ = mimetypes.guess_type(str(file_path))
                    
                    # Safely calculate relative path
                    try:
                        relative_path = str(file_path.relative_to(output_dir))
                    except ValueError:
                        relative_path = file_path.name
                    
                    output_files.append({
                        "name": file_path.name,
                        "relative_path": relative_path,
                        "size": stat.st_size,
                        "mime_type": mime_type or "application/octet-stream",
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
                    })
        
        # Update session info
        if isinstance(active_sessions[session_id]["output_files"], list):
            active_sessions[session_id]["output_files"] = [f["relative_path"] for f in output_files]
        return output_files
        
    except Exception as e:
        logger.error(f"Error scanning output files for session {session_id}: {e}")
        return []

# API Endpoints
@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint."""
    return HealthCheck(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now()
    )

@app.post("/session", response_model=SessionInfo)
async def create_execution_session():
    """Create a new execution session with workspace."""
    session_id = create_session()
    session_data = active_sessions[session_id]
    
    return SessionInfo(
        session_id=session_id,
        created_at=session_data["created_at"],
        workspace_path=session_data["workspace_path"]
    )

@app.get("/session/{session_id}", response_model=SessionInfo)
async def get_session_info(session_id: str):
    """Get information about a specific session."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = active_sessions[session_id]
    return SessionInfo(
        session_id=session_id,
        created_at=session_data["created_at"],
        workspace_path=session_data["workspace_path"],
        input_files=session_data["input_files"],
        output_files=session_data["output_files"]
    )

@app.post("/session/{session_id}/upload")
async def upload_files(
    session_id: str,
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Upload files to a session workspace."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_path = get_session_path(session_id)
    input_dir = session_path / "inputs"
    
    # Check file limits
    current_file_count = len(list(input_dir.glob("*")))
    if current_file_count + len(files) > MAX_FILES_PER_SESSION:
        raise HTTPException(
            status_code=413, 
            detail=f"Too many files. Maximum {MAX_FILES_PER_SESSION} files per session"
        )
    
    uploaded_files = []
    
    for file in files:
        # Check file size
        if file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File {file.filename} too large. Maximum size: {MAX_FILE_SIZE/1024/1024:.1f}MB"
            )
        
        # Save file (handle None filename)
        filename = file.filename or "uploaded_file"
        file_path = input_dir / filename
        try:
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            uploaded_files.append({
                "filename": file.filename,
                "size": len(content),
                "path": str(file_path.relative_to(session_path))
            })
            
            # Update session info
            if "input_files" not in active_sessions[session_id]:
                active_sessions[session_id]["input_files"] = []
            active_sessions[session_id]["input_files"].append(file.filename)
            
        except Exception as e:
            logger.error(f"Error saving file {file.filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Error saving file: {file.filename}")
    
    # Schedule cleanup
    background_tasks.add_task(cleanup_expired_sessions)
    
    return {
        "session_id": session_id,
        "uploaded_files": uploaded_files,
        "total_files": len(active_sessions[session_id]["input_files"])
    }

@app.post("/execute", response_model=ExecutionResponse)
async def execute_python_code(request: CodeExecutionRequest):
    """Execute Python code with optional session file access."""
    start_time = datetime.now()
    execution_id = str(uuid.uuid4())
    
    # Create session if not provided
    if not request.session_id:
        session_id = create_session()
    else:
        session_id = request.session_id
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Modify code to include workspace paths if session exists
        session_path = get_session_path(session_id)
        modified_code = f"""
import os
import sys

# Set up workspace paths
WORKSPACE_PATH = r"{session_path}"
INPUT_PATH = os.path.join(WORKSPACE_PATH, "inputs")  
OUTPUT_PATH = os.path.join(WORKSPACE_PATH, "outputs")

# Add paths to sys.path for imports
sys.path.append(INPUT_PATH)

# Change working directory to workspace
os.chdir(WORKSPACE_PATH)

# Original code starts here
{request.code}
"""
        
        # Execute the code using your existing function
        result = await execute_code_string(modified_code)
        
        # Scan for output files
        output_files = scan_output_files(session_id)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return ExecutionResponse(
            execution_id=execution_id,
            session_id=session_id,
            result=result.result,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            status=result.status,
            error=result.error,
            output_files=output_files,
            execution_time=execution_time
        )
        
    except Exception as e:
        logger.error(f"Error executing code: {e}")
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return ExecutionResponse(
            execution_id=execution_id,
            session_id=session_id,
            result=None,
            stdout="",
            stderr=str(e),
            status="error",
            error=str(e),
            output_files=[],
            execution_time=execution_time
        )

@app.post("/system-command")
async def execute_system_command_endpoint(request: SystemCommandRequest):
    """Execute system command with optional session access."""
    execution_id = str(uuid.uuid4())
    start_time = datetime.now()
    
    # Create session if not provided
    if not request.session_id:
        session_id = create_session()
    else:
        session_id = request.session_id
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Execute system command with basic security checks
        allowed_prefixes = request.allowed_prefixes or ["python ", "pip ", "python -m "]
        
        # Security check
        if not any(request.command.startswith(prefix) for prefix in allowed_prefixes):
            return {
                "execution_id": execution_id,
                "session_id": session_id,
                "stdout": "",
                "stderr": f"Command not allowed. Must start with one of: {', '.join(allowed_prefixes)}",
                "status": "error",
                "exit_code": 1,
                "execution_time": 0.0
            }
        
        # Execute command using subprocess
        process = subprocess.Popen(
            request.command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=get_session_path(session_id) if session_id in active_sessions else None
        )
        
        stdout, stderr = process.communicate()
        exit_code = process.returncode
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "execution_id": execution_id,
            "session_id": session_id,
            "stdout": stdout,
            "stderr": stderr,
            "status": "success" if exit_code == 0 else "error",
            "exit_code": exit_code,
            "execution_time": execution_time
        }
        
    except Exception as e:
        logger.error(f"Error executing system command: {e}")
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "execution_id": execution_id,
            "session_id": session_id,
            "stdout": "",
            "stderr": str(e),
            "status": "error",
            "exit_code": 1,
            "execution_time": execution_time
        }

@app.get("/session/{session_id}/files")
async def list_session_files(session_id: str):
    """List all files in a session (inputs and outputs)."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_path = get_session_path(session_id)
    
    files_info = {
        "session_id": session_id,
        "input_files": [],
        "output_files": scan_output_files(session_id)
    }
    
    # Scan input files
    input_dir = session_path / "inputs"
    if input_dir.exists():
        for file_path in input_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                mime_type, _ = mimetypes.guess_type(str(file_path))
                
                files_info["input_files"].append({
                    "name": file_path.name,
                    "size": stat.st_size,
                    "mime_type": mime_type or "application/octet-stream",
                    "uploaded_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
                })
    
    return files_info

@app.get("/session/{session_id}/download/{file_type}/{filename}")
async def download_file(session_id: str, file_type: str, filename: str):
    """Download a file from session workspace."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if file_type not in ["inputs", "outputs"]:
        raise HTTPException(status_code=400, detail="file_type must be 'inputs' or 'outputs'")
    
    session_path = get_session_path(session_id)
    file_path = session_path / file_type / filename
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Security check: ensure file is within session directory
    try:
        file_path.resolve().relative_to(session_path.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='application/octet-stream'
    )

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and all its files."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        session_path = get_session_path(session_id)
        if session_path.exists():
            shutil.rmtree(session_path)
        
        del active_sessions[session_id]
        logger.info(f"Deleted session: {session_id}")
        
        return {"message": f"Session {session_id} deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Error deleting session")

@app.get("/sessions")
async def list_active_sessions():
    """List all active sessions."""
    return {
        "active_sessions": len(active_sessions),
        "sessions": [
            {
                "session_id": sid,
                "created_at": data["created_at"],
                "input_files": len(data["input_files"]),
                "output_files": len(data["output_files"])
            }
            for sid, data in active_sessions.items()
        ]
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the service."""
    logger.info("Code Executor Service starting up...")
    logger.info(f"Workspace base directory: {WORKSPACE_BASE}")
    logger.info(f"Session TTL: {SESSION_TTL_HOURS} hours")
    logger.info(f"Max file size: {MAX_FILE_SIZE/1024/1024:.1f}MB")

# Main entry point
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting Code Executor Service on {host}:{port}")
    
    uvicorn.run(
        "fastapi_server:app",
        host=host,
        port=port,
        reload=False,  # Set to True for development
        access_log=True,
        log_level="info"
    ) 