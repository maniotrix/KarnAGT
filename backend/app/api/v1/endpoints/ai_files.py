"""
AI Files API Endpoints - Staging Area Management
Handles image staging for LLM inference with optimal resource usage
"""
import os
import uuid
import asyncio
import time
from typing import Optional, List, Dict, Any
from fastapi import (
    APIRouter, 
    Depends, 
    HTTPException, 
    status, 
    UploadFile, 
    File,
    Form,
    Query,
    Body
)
from pydantic import BaseModel
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import get_settings
from app.core.exceptions import (
    QuotaExceededException,
    ValidationException
)
from app.models.database.user import User
from app.models.schemas.common_schemas import BaseResponse
from app.api.v1.dependencies.auth import (
    get_current_verified_user,
    check_image_quota
)
from app.services.storage.storage import storage_service
from app.services.storage.staging_storage import staging_service

from aicore.logger import get_logger

# Set up logger
logger = get_logger(__name__)

router = APIRouter()
settings = get_settings()

# Staging configuration
MAX_BULK_STAGING_FILES = 10


# Pydantic models for request bodies
class BulkDiscardRequest(BaseModel):
    staging_ids: List[str]


@router.get("/status")
async def get_ai_files_status():
    """Get AI files service status"""
    return {
        "status": "AI Files staging service ready",
        "version": "1.0.0",
        "features": [
            "bulk_staging_upload",
            "staging_discard", 
            "simple_workflow"
        ],
        "staging_config": {
            "max_bulk_files": MAX_BULK_STAGING_FILES,
            "no_thumbnails": True,
            "no_db_commits": True
        }
    }


@router.post("/staging/bulk-upload", status_code=status.HTTP_201_CREATED)
async def bulk_upload_to_staging(
    files: List[UploadFile] = File(..., description="Images to upload to staging area"),
    max_concurrent_uploads: int = Form(5, ge=1, le=10, description="Max concurrent uploads"),
    current_user: User = Depends(check_image_quota),
) -> Dict[str, Any]:
    """
    Bulk upload images to staging area for later LLM inference
    
    Simple flow:
    1. Upload files to staging
    2. Get back staging_ids (these ARE the file IDs)
    3. Use those same staging_ids to discard files later
    
    Returns staging IDs for later use in chat or discard
    """
    logger.info(f"Bulk staging upload from user {current_user.user_id}, {len(files)} files")
    
    # Validate bulk limits
    if len(files) > MAX_BULK_STAGING_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files. Maximum {MAX_BULK_STAGING_FILES} files allowed per bulk staging upload"
        )
    
    if len(files) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )
    
    start_time = time.time()
    
    try:
        # Prepare files data for staging service
        files_data = []
        for file in files:
            if not file.filename:
                continue
            
            file_data = await file.read()
            files_data.append((
                file_data,
                file.filename,
                file.content_type or "image/jpeg"
            ))
        
        # Use staging service for bulk upload
        result = await staging_service.bulk_upload_to_staging(
            files_data=files_data,
            user_id=current_user.user_id,
            max_concurrent=max_concurrent_uploads
        )
        
        upload_duration = time.time() - start_time
        
        response = {
            "success": True,
            "message": f"Bulk staging completed: {result['successfully_staged']} successful, {result['failed_uploads']} failed",
            "total_requested": result["total_requested"],
            "successfully_staged": result["successfully_staged"],
            "failed_uploads": result["failed_uploads"],
            "staged_files": result["staged_files"],  # Contains staging_ids client needs
            "failed_files": result["failed_files"],
            "total_size_bytes": result["total_size_bytes"],
            "upload_duration_seconds": upload_duration
        }
        
        logger.info(f"Bulk staging completed for user {current_user.user_id}: {result['successfully_staged']} successful")
        return response
        
    except ValidationException as e:
        logger.warning(f"Bulk staging validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except QuotaExceededException as e:
        logger.warning(f"Quota exceeded for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in bulk staging upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process bulk staging upload"
        )


@router.delete("/staging/{staging_id}")
async def discard_staged_file(
    staging_id: str,
    current_user: User = Depends(get_current_verified_user)
) -> BaseResponse:
    """
    Discard a staged file - SIMPLE VERSION
    
    Client sends back the same staging_id they got from upload
    """
    logger.info(f"Discarding staged file {staging_id} for user {current_user.user_id}")
    
    try:
        # Use staging service for discard (with ownership validation)
        await staging_service.discard_staged_file(staging_id, current_user.user_id)
        
        # If we get here, discard was successful (no exception thrown)
        return BaseResponse(
            success=True,
            message=f"Staged file {staging_id} discarded successfully"
        )
            
    except FileNotFoundError as e:
        logger.warning(f"Staging file {staging_id} not found for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staged file not found or access denied"
        )
    except Exception as e:
        logger.error(f"Error discarding staged file {staging_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to discard staged file"
        )


@router.delete("/staging/bulk-discard")
async def bulk_discard_staged_files(
    request: BulkDiscardRequest,
    current_user: User = Depends(get_current_verified_user)
) -> Dict[str, Any]:
    """
    Bulk discard multiple staged files - SIMPLE VERSION
    
    Client sends back the same staging_ids they got from upload
    """
    staging_ids = request.staging_ids
    logger.info(f"Bulk discarding {len(staging_ids)} staged files for user {current_user.user_id}")
    
    if len(staging_ids) > MAX_BULK_STAGING_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files to discard. Maximum {MAX_BULK_STAGING_FILES} allowed"
        )
    
    # Handle empty list case
    if len(staging_ids) == 0:
        return {
            "success": True,
            "message": "No files to discard",
            "total_requested": 0,
            "successfully_discarded": 0,
            "failed_discards": 0,
            "discarded_staging_ids": [],
            "failed_staging_ids": []
        }
    
    try:
        # Use staging service for bulk discard
        result = await staging_service.bulk_discard_staged_files(staging_ids, current_user.user_id)
        
        return {
            "success": True,
            "message": f"Bulk discard completed: {result['successfully_discarded']} successful, {result['failed_discards']} failed",
            "total_requested": result["total_requested"],
            "successfully_discarded": result["successfully_discarded"],
            "failed_discards": result["failed_discards"],
            "discarded_staging_ids": result["discarded_staging_ids"],
            "failed_staging_ids": result["failed_staging_ids"]
        }
        
    except Exception as e:
        logger.error(f"Error in bulk discard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process bulk discard"
        )

 

