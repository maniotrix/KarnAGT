#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FastAPI Routes

Main API endpoints for workspace management, code execution, and file operations.
"""

from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.domain.models import (
    WorkspaceCreateRequest, WorkspaceInfo, WorkspaceFilesResponse,
    ExecutionRequest, ExecutionResult, HealthCheck
)
from app.services.workspace_service import WorkspaceService
from app.services.execution_service import ExecutionService
from app.services.file_service import FileService, FileServiceError
from app.infrastructure.jupyter_kernel_client import WorkspaceNotFoundError, JupyterClientError
from app.api.dependencies import (
    get_workspace_service, get_execution_service, get_file_service, get_settings_cached
)

from app.utils.serialization import SerializableResponse

# Create router
router = APIRouter()


def get_serializable_response(content: Any) -> SerializableResponse:
    """Get a SerializableResponse object with the given content."""
    return SerializableResponse(content=content)


# ============================================================================
# Health & Status Endpoints
# ============================================================================

@router.get("/health", response_model=HealthCheck)
async def health_check(
    workspace_service: WorkspaceService = Depends(get_workspace_service)
):
    """Health check endpoint"""
    try:
        # Get Jupyter status
        jupyter_client = workspace_service.jupyter_client
        jupyter_health = await jupyter_client.health_check()
        
        # Get workspace stats
        stats = workspace_service.get_stats()
        
        return HealthCheck(
            status="healthy",
            jupyter_server_status=jupyter_health.get("status", "unknown"),
            active_workspaces=stats.get("active_workspaces", 0)
        )
    except Exception as e:
        return HealthCheck(
            status="unhealthy",
            jupyter_server_status="error",
            active_workspaces=0
        )


@router.get("/stats")
async def get_system_stats(
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    execution_service: ExecutionService = Depends(get_execution_service),
    file_service: FileService = Depends(get_file_service)
):
    """Get system statistics"""
    stats_data = {
        "workspace_stats": workspace_service.get_stats(),
        "execution_stats": execution_service.get_execution_stats(),
        "file_stats": file_service.get_stats()
    }
    return get_serializable_response(stats_data)


# ============================================================================
# Workspace Management Endpoints
# ============================================================================

@router.post("/workspace/create", response_model=WorkspaceInfo)
async def create_workspace(
    request: WorkspaceCreateRequest,
    workspace_service: WorkspaceService = Depends(get_workspace_service)
):
    """Create a new workspace"""
    try:
        workspace_info = await workspace_service.create_workspace(request)
        return workspace_info
    except JupyterClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create workspace: {e}")


@router.get("/workspace/{workspace_id}", response_model=WorkspaceInfo)
async def get_workspace(
    workspace_id: str,
    workspace_service: WorkspaceService = Depends(get_workspace_service)
):
    """Get workspace information"""
    workspace_info = await workspace_service.get_workspace(workspace_id)
    if not workspace_info:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace_info


@router.get("/workspaces", response_model=List[WorkspaceInfo])
async def list_workspaces(
    workspace_service: WorkspaceService = Depends(get_workspace_service)
):
    """List all workspaces"""
    return await workspace_service.list_workspaces()


@router.delete("/workspace/{workspace_id}")
async def delete_workspace(
    workspace_id: str,
    workspace_service: WorkspaceService = Depends(get_workspace_service)
):
    """Delete a workspace"""
    success = await workspace_service.delete_workspace(workspace_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"message": "Workspace deleted successfully"}


@router.post("/workspace/{workspace_id}/extend")
async def extend_workspace_ttl(
    workspace_id: str,
    additional_hours: int = Form(..., description="Hours to add to TTL"),
    workspace_service: WorkspaceService = Depends(get_workspace_service)
):
    """Extend workspace TTL"""
    try:
        workspace_info = await workspace_service.extend_workspace_ttl(workspace_id, additional_hours)
        if not workspace_info:
            raise HTTPException(status_code=404, detail="Workspace not found")
        return workspace_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Code Execution Endpoints (CRITICAL: Use SerializableResponse!)
# ============================================================================

@router.post("/workspace/{workspace_id}/execute")
async def execute_code(
    workspace_id: str,
    code: str = Form(..., description="Python code to execute"),
    timeout: int = Form(30, description="Execution timeout in seconds"),
    execution_service: ExecutionService = Depends(get_execution_service)
):
    """Execute code in workspace - RETURNS COMPLEX OBJECTS (numpy, pandas, etc.)"""
    try:
        request = ExecutionRequest(
            workspace_id=workspace_id,
            code=code,
            timeout=timeout
        )
        result = await execution_service.execute_code(request)
        
        # 🔥 THIS IS THE CRITICAL PART - Use enhanced serialization for complex objects!
        result_data = {
            "execution_id": result.execution_id,
            "workspace_id": result.workspace_id,
            "status": result.status.value,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "result_data": result.result_data,  # This could be numpy/pandas/matplotlib objects!
            "outputs": [
                {
                    "type": output.type,
                    "content": output.content,  # This could be complex objects too!
                    "timestamp": output.timestamp.isoformat()
                } 
                for output in result.outputs
            ],
            "generated_files": [
                {
                    "filename": file.filename,
                    "size": file.size,
                    "mime_type": file.mime_type,
                    "download_url": file.download_url,
                    "relative_path": file.relative_path
                }
                for file in result.generated_files
            ],
            "execution_time_ms": result.execution_time_ms,
            "started_at": result.started_at.isoformat(),
            "completed_at": result.completed_at.isoformat() if result.completed_at else None
        }
        
        # 🚀 Use enhanced serialization to safely handle complex objects
        from app.utils.serialization import safe_serialize_execution_result, get_serializable_response
        safe_result = safe_serialize_execution_result(result_data)
        return get_serializable_response(safe_result)
        
    except WorkspaceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {e}")


@router.get("/execution/{execution_id}")
async def get_execution_result(
    execution_id: str,
    execution_service: ExecutionService = Depends(get_execution_service)
):
    """Get execution result by ID - RETURNS COMPLEX OBJECTS"""
    result = await execution_service.get_execution_result(execution_id)
    if not result:
        raise HTTPException(status_code=404, detail="Execution result not found")
    
    # Use SerializableResponse for complex result_data
    result_data = {
        "execution_id": result.execution_id,
        "workspace_id": result.workspace_id,
        "status": result.status.value,
        "started_at": result.started_at.isoformat(),
        "completed_at": result.completed_at.isoformat() if result.completed_at else None,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "result_data": result.result_data,  # Could be complex objects!
        "outputs": [
            {
                "type": output.type,
                "content": output.content,
                "timestamp": output.timestamp.isoformat()
            } 
            for output in result.outputs
        ],
        "generated_files": [
            {
                "filename": file.filename,
                "size": file.size,
                "mime_type": file.mime_type,
                "download_url": file.download_url,
                "relative_path": file.relative_path
            }
            for file in result.generated_files
        ],
        "execution_time_ms": result.execution_time_ms
    }
    
    # Use enhanced serialization for safety
    from app.utils.serialization import safe_serialize_execution_result, get_serializable_response
    safe_result = safe_serialize_execution_result(result_data)
    return get_serializable_response(safe_result)


@router.get("/workspace/{workspace_id}/executions")
async def list_workspace_executions(
    workspace_id: str,
    limit: int = 50,
    execution_service: ExecutionService = Depends(get_execution_service)
):
    """List executions for workspace"""
    executions = await execution_service.list_workspace_executions(workspace_id, limit)
    
    # Convert to serializable format with enhanced safety
    executions_data = []
    for execution in executions:
        execution_data = {
            "execution_id": execution.execution_id,
            "workspace_id": execution.workspace_id,
            "status": execution.status.value,
            "started_at": execution.started_at.isoformat(),
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "stdout": execution.stdout,
            "stderr": execution.stderr,
            "result_data": execution.result_data,  # Could be complex!
            "outputs": [
                {
                    "type": output.type,
                    "content": output.content,
                    "timestamp": output.timestamp.isoformat()
                } 
                for output in execution.outputs
            ],
            "generated_files": [
                {
                    "filename": file.filename,
                    "size": file.size,
                    "mime_type": file.mime_type,
                    "download_url": file.download_url,
                    "relative_path": file.relative_path
                }
                for file in execution.generated_files
            ],
            "execution_time_ms": execution.execution_time_ms
        }
        
        # Use safe serialization for each execution
        from app.utils.serialization import safe_serialize_execution_result
        safe_execution = safe_serialize_execution_result(execution_data)
        executions_data.append(safe_execution)

    from app.utils.serialization import get_serializable_response
    return get_serializable_response({"executions": executions_data})


# ============================================================================
# File Management Endpoints
# ============================================================================

@router.post("/workspace/{workspace_id}/upload")
async def upload_file(
    workspace_id: str,
    file: UploadFile = File(...),
    file_service: FileService = Depends(get_file_service)
):
    """Upload file to workspace"""
    import logging
    import urllib.parse
    logger = logging.getLogger(__name__)
    
    try:
        # CRITICAL FIX: URL-decode the filename before validation
        # The original filename from multipart form data is URL-encoded,
        # but validation must check the actual filename that will be written to disk
        decoded_filename = urllib.parse.unquote(file.filename) if file.filename else ""
        
        logger.info(f"File upload started: {file.filename} (decoded: {decoded_filename}) to workspace {workspace_id}")
        
        # Read file content
        content = await file.read()
        logger.debug(f"File content read: {len(content)} bytes")
        
        # Upload file with decoded filename
        file_info = await file_service.upload_file(
            workspace_id=workspace_id,
            filename=decoded_filename,
            content=content
        )
        
        # Generate download URL at API layer (proper separation of concerns)
        upload_result = {
            "filename": file_info.filename,
            "size": file_info.size,
            "mime_type": file_info.mime_type,
            "download_url": f"/workspace/{workspace_id}/files/{file_info.relative_path}",
            "relative_path": file_info.relative_path
        }
        
        logger.info(f"File upload successful: {decoded_filename}")
        return get_serializable_response(upload_result)
        
    except WorkspaceNotFoundError as e:
        logger.error(f"Workspace not found for upload: {workspace_id}", exc_info=True)
        raise HTTPException(status_code=404, detail=str(e))
    except FileServiceError as e:
        logger.error(f"File service error during upload: {file.filename}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during file upload: {file.filename} to {workspace_id}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"File upload failed: {e}")


@router.get("/workspace/{workspace_id}/files/{filename:path}")
async def download_file(
    workspace_id: str,
    filename: str,
    file_service: FileService = Depends(get_file_service)
):
    """Download file from workspace"""
    import logging
    from fastapi.responses import Response
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"File download requested: {filename} from workspace {workspace_id}")
        
        # Get file content and info from file service
        file_content, file_info = await file_service.download_file(workspace_id, filename)
        
        logger.info(f"File download successful: {filename} ({file_info.size} bytes)")
        
        # Return file content with appropriate headers
        return Response(
            content=file_content,
            media_type=file_info.mime_type or "application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{file_info.filename}"',
                "Content-Length": str(file_info.size)
            }
        )
        
    except WorkspaceNotFoundError as e:
        logger.error(f"Workspace not found for download: {workspace_id}")
        raise HTTPException(status_code=404, detail="Workspace not found")
    except FileNotFoundError as e:
        logger.error(f"File not found for download: {filename} in workspace {workspace_id}")
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        logger.error(f"Unexpected error during file download: {filename} from {workspace_id}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"File download failed: {e}")


@router.get("/workspace/{workspace_id}/files", response_model=WorkspaceFilesResponse)
async def list_workspace_files(
    workspace_id: str,
    workspace_service: WorkspaceService = Depends(get_workspace_service)
):
    """List files in workspace"""
    try:
        files_response = await workspace_service.get_workspace_files(workspace_id)
        
        # Generate download URLs at API layer (proper separation of concerns)
        for file_info in files_response.files:
            file_info.download_url = f"/workspace/{workspace_id}/files/{file_info.relative_path}"
        
        return files_response
    except WorkspaceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {e}")


# ============================================================================
# Configuration Endpoints
# ============================================================================

@router.get("/config")
async def get_configuration():
    """Get system configuration (safe subset)"""
    settings = get_settings_cached()
    config_data = {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "environment": settings.environment,
        "workspace_default_ttl_hours": settings.workspace_default_ttl_hours,
        "workspace_max_ttl_hours": settings.workspace_max_ttl_hours,
        "max_file_size_mb": settings.max_file_size_mb,
        "max_workspace_size_mb": settings.max_workspace_size_mb,
        "default_execution_timeout": settings.default_execution_timeout,
        "max_execution_timeout": settings.max_execution_timeout,
        "serialization_available": True
    }
    
    return get_serializable_response(config_data) 