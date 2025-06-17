"""
File Management API Endpoints
Handles image uploads and file serving for chat functionality
"""
import os
from typing import Optional, List
from fastapi import (
    APIRouter, 
    Depends, 
    HTTPException, 
    status, 
    UploadFile, 
    File, 
    Form,
    Query,
    Response
)
from fastapi.responses import StreamingResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image
import io

from app.core.database import get_db
from app.core.config import get_settings
from app.core.exceptions import (
    QuotaExceededException,
    ValidationException
)
from app.models.database.user import User
from app.models.schemas.image_schemas import (
    ImageUploadResponse,
    ImageMetadataResponse,
    ImageListResponse,
    ImageValidationError
)
from app.models.schemas.common_schemas import BaseResponse
from app.api.v1.dependencies.auth import (
    get_current_verified_user,
    check_image_quota
)
from app.services.storage.storage import storage_service

from aicore.logger import get_logger

# Set up logger
logger = get_logger(__name__)

router = APIRouter()

settings = get_settings()


@router.get("/files_status")
async def get_files_status():
    """Get files service status"""
    return {
        "status": "Files service ready", 
        "version": "1.0.0",
        "features": ["image_upload", "image_serving"],
        "max_image_size_mb": settings.MAX_IMAGE_SIZE / (1024 * 1024),
        "allowed_types": settings.get_allowed_image_types()
    }


@router.post("/images/upload", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(..., description="Image file to upload"),
    conversation_id: Optional[str] = Form(None, description="Associated conversation ID"),
    current_user: User = Depends(check_image_quota),  # Includes quota and auth check
    db: AsyncSession = Depends(get_db)
) -> ImageUploadResponse:
    """
    Upload an image for chat usage
    
    - **file**: Image file (PNG, JPEG, GIF, WebP, max 20MB)
    - **conversation_id**: Optional conversation context
    - Returns: Image metadata including display URLs and file references
    
    **Subscription Requirements:**
    - Pro or Enterprise subscription required
    - Consumes quota based on file size and processing
    """
    logger.info(f"Image upload request from user {current_user.user_id}, file: {file.filename}")
    
    try:
        # Validate file
        if not file.filename:
            raise ValidationException("Filename is required")
        
        # Read file data
        file_data = await file.read()
        
        # Upload using storage service
        upload_result = await storage_service.upload_image(
            file_data=file_data,
            filename=file.filename,
            content_type=file.content_type or "image/jpeg",
            user_id=current_user.user_id
        )
        
        # Extract dimensions if possible
        dimensions = None
        try:
            with Image.open(io.BytesIO(file_data)) as img:
                dimensions = {"width": img.width, "height": img.height}
        except Exception as e:
            logger.warning(f"Could not extract image dimensions: {e}")
        
        # TODO: Integrate with OpenAI Files API for vision functionality
        # For now, we'll leave openai_file_id as None
        
        response = ImageUploadResponse(
            success=True,
            message="Image uploaded successfully",
            file_id=upload_result["file_id"],
            filename=upload_result["filename"],
            original_filename=file.filename,
            content_type=upload_result["content_type"],
            size=upload_result["size"],
            dimensions=dimensions,
            urls=upload_result["urls"],
            s3_key=upload_result["s3_key"],
            uploaded_at=upload_result["uploaded_at"],
            openai_file_id=None,  # TODO: Implement OpenAI Files API integration
            openai_expires_at=None
        )
        
        logger.info(f"Image uploaded successfully: {upload_result['file_id']}")
        return response
        
    except ValidationException as e:
        logger.warning(f"Image validation failed: {e}")
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
        logger.error(f"Error uploading image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload image"
        )


@router.get("/images/{file_id}", response_class=RedirectResponse)
async def serve_image(
    file_id: str,
    current_user: User = Depends(get_current_verified_user)
):
    """
    Serve full-size image
    Redirects to MinIO URL for direct serving
    """
    logger.info(f"Serving image {file_id} for user {current_user.user_id}")
    
    try:
        # TODO: Validate user ownership of the image
        # For now, we'll generate the URL based on file_id pattern
        
        # Generate MinIO URL (this is a simplified approach)
        # In production, you'd want to validate the file exists and user has access
        minio_url = f"{settings.S3_ENDPOINT_URL}/{settings.S3_BUCKET_NAME}/images/*/{file_id}.*"
        
        # For now, return a simple response
        # TODO: Implement proper file lookup and access control
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Image serving not yet implemented - use display URL from upload response"
        )
        
    except Exception as e:
        logger.error(f"Error serving image {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to serve image"
        )


@router.get("/images/{file_id}/metadata", response_model=ImageMetadataResponse)
async def get_image_metadata(
    file_id: str,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
) -> ImageMetadataResponse:
    """
    Get image metadata without file content
    """
    logger.info(f"Getting metadata for image {file_id}")
    
    try:
        # TODO: Implement metadata lookup from database
        # For now, return a placeholder
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Image metadata lookup not yet implemented"
        )
        
    except Exception as e:
        logger.error(f"Error getting image metadata {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get image metadata"
        )


@router.delete("/images/{file_id}", response_model=BaseResponse)
async def delete_image(
    file_id: str,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
) -> BaseResponse:
    """
    Delete an uploaded image
    """
    logger.info(f"Deleting image {file_id} for user {current_user.user_id}")
    
    try:
        # TODO: Implement image deletion
        # 1. Validate user ownership
        # 2. Delete from MinIO
        # 3. Update database records
        
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Image deletion not yet implemented"
        )
        
    except Exception as e:
        logger.error(f"Error deleting image {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete image"
        )


@router.get("/images", response_model=ImageListResponse)
async def list_user_images(
    limit: int = Query(20, ge=1, le=100, description="Number of images to return"),
    offset: int = Query(0, ge=0, description="Number of images to skip"),
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
) -> ImageListResponse:
    """
    List user's uploaded images with pagination
    """
    logger.info(f"Listing images for user {current_user.user_id}")
    
    try:
        # TODO: Implement image listing from database
        # For now, return empty list
        return ImageListResponse(
            success=True,
            message="Images retrieved successfully",
            images=[],
            total=0,
            page=(offset // limit) + 1,
            size=limit,
            has_next=False,
            has_prev=offset > 0
        )
        
    except Exception as e:
        logger.error(f"Error listing images: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list images"
        ) 