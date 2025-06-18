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
from sqlalchemy.orm import Session
from PIL import Image
import io
import json

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

# TODO : Bulk image upload and management


@router.get("/files_status")
async def get_files_status():
    """Get files service status"""
    return {
        "status": "Files service ready", 
        "version": "1.1.0",  # Updated version for thumbnail support
        "features": ["image_upload", "image_serving", "thumbnails"],
        "max_image_size_mb": settings.MAX_IMAGE_SIZE / (1024 * 1024),
        "allowed_types": settings.get_allowed_image_types(),
        "thumbnail_sizes": settings.get_thumbnail_sizes(),
        "thumbnail_format": settings.THUMBNAIL_FORMAT
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
        
        # Upload using storage service with database tracking
        upload_result = await storage_service.upload_image(
            file_data=file_data,
            filename=file.filename,
            content_type=file.content_type or "image/jpeg",
            user_id=current_user.user_id,
            db=db
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
        
        # Build URLs dict with thumbnails
        urls = {
            "display": upload_result["url"], 
            "api": upload_result["url"]
        }

        # Add thumbnail URLs if thumbnails were generated
        if upload_result.get("thumbnail_s3_keys"):
            for size in upload_result["thumbnail_s3_keys"].keys():
                urls[f"thumbnail_{size}"] = f"{storage_service.image_base_url}/{upload_result['file_id']}/thumbnail?size={size}"

        response = ImageUploadResponse(
            success=True,
            message="Image uploaded successfully",
            file_id=upload_result["file_id"],
            filename=upload_result["filename"],
            original_filename=file.filename,
            content_type=upload_result["content_type"],
            size=upload_result["size"],
            dimensions=dimensions,
            urls=urls,
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
    except ValueError as e:
        # Handle file validation errors (size, type, etc.) from storage service
        logger.warning(f"File validation failed: {e}")
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
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Serve full-size image with proper ownership validation
    Uses database-driven access control (industry best practice)
    """
    logger.info(f"Serving image {file_id} for user {current_user.user_id}")
    
    try:
        # SECURITY: Validate file ownership using database lookup
        presigned_url = await storage_service.serve_image_securely(
            file_id=file_id, 
            user_id=current_user.user_id,
            db=db
        )
        
        if not presigned_url:
            logger.warning(f"Access denied for file {file_id} by user {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You don't own this file or file not found"
            )
        
        # Redirect to presigned URL for secure access
        logger.info(f"Redirecting to presigned URL for {file_id}")
        return RedirectResponse(url=presigned_url, status_code=302)
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 403) without converting to 500
        raise
    except Exception as e:
        logger.error(f"Error serving image {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to serve image"
        )


@router.get("/images/{file_id}/thumbnail", response_class=RedirectResponse)
async def serve_image_thumbnail(
    file_id: str,
    size: Optional[str] = Query(None, description="Thumbnail size (e.g., '150x150', '300x300')"),
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Serve image thumbnail with proper ownership validation
    
    - **file_id**: The image file ID
    - **size**: Thumbnail size in format "WxH" (defaults to first configured size)
    - Available sizes are configured in server settings
    
    Uses database-driven access control (industry best practice)
    """
    # Use first configured thumbnail size as default if none provided
    if not size:
        thumbnail_sizes = settings.get_thumbnail_sizes()
        if thumbnail_sizes:
            width, height = thumbnail_sizes[0]
            size = f"{width}x{height}"
        else:
            size = "150x150"  # Fallback if no sizes configured
    
    logger.info(f"Serving thumbnail {size} for image {file_id} for user {current_user.user_id}")
    
    try:
        # SECURITY: Validate file ownership and get thumbnail URL
        presigned_url = await storage_service.serve_thumbnail_securely(
            file_id=file_id,
            size=size,
            user_id=current_user.user_id,
            db=db
        )
        
        if not presigned_url:
            logger.warning(f"Access denied or thumbnail not found for {file_id} ({size}) by user {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thumbnail not found or access denied"
            )
        
        # Redirect to presigned URL for secure access
        logger.info(f"Redirecting to thumbnail presigned URL for {file_id} ({size})")
        return RedirectResponse(url=presigned_url, status_code=302)
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404, 403) without converting to 500
        raise
    except Exception as e:
        logger.error(f"Error serving thumbnail {file_id} ({size}): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to serve thumbnail"
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
        # Validate ownership and get metadata
        image_record = await storage_service.validate_file_ownership(
            file_id=file_id,
            user_id=current_user.user_id, 
            db=db
        )
        
        if not image_record:
            logger.warning(f"Access denied for metadata {file_id} by user {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You don't own this file or file not found"
            )
        
        # Build URLs dict with thumbnails
        urls = {"api": f"{storage_service.image_base_url}/{image_record.file_id}"}

        # Add thumbnail URLs if available
        if image_record.thumbnail_s3_keys:
            try:
                thumbnail_keys = json.loads(image_record.thumbnail_s3_keys)
                for size in thumbnail_keys.keys():
                    urls[f"thumbnail_{size}"] = f"{storage_service.image_base_url}/{image_record.file_id}/thumbnail?size={size}"
            except Exception as e:
                logger.warning(f"Failed to parse thumbnail keys for {file_id}: {e}")

        return ImageMetadataResponse(
            success=True,
            message="Image metadata retrieved successfully",
            file_id=image_record.file_id,
            filename=image_record.filename,
            original_filename=image_record.filename,
            content_type=image_record.content_type,
            size=image_record.file_size,
            dimensions=None,  # Could extract from image_record.tags if stored
            s3_key=image_record.s3_key,
            uploaded_at=image_record.uploaded_at,
            urls=urls,
            is_deleted=False
        )
        
    except HTTPException:
        raise
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
    Delete an uploaded image with proper ownership validation
    
    Security Features:
    - Validates file ownership via database lookup
    - Deletes from both S3/MinIO storage and database
    - Prevents unauthorized deletion attempts
    """
    logger.info(f"Deleting image {file_id} for user {current_user.user_id}")
    
    try:
        # SECURITY: Delete with ownership validation
        deletion_successful = await storage_service.delete_image_securely(
            file_id=file_id,
            user_id=current_user.user_id,
            db=db
        )
        
        if not deletion_successful:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You don't own this file or file not found"
            )
        
        return BaseResponse(
            success=True,
            message=f"Image {file_id} deleted successfully"
        )
        
    except HTTPException:
        raise
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
        # Get images from database with ownership validation
        images = await storage_service.get_user_images(
            user_id=current_user.user_id,
            db=db,
            limit=limit + 1,  # Get one extra to check if there's a next page
            offset=offset
        )
        
        # Check if there's a next page
        has_next = len(images) > limit
        if has_next:
            images = images[:limit]  # Remove the extra item
        
        # Convert to response format
        image_metadata = []
        for img in images:
            # Build URLs dict with thumbnails
            urls = {"api": f"{storage_service.image_base_url}/{img.file_id}"}
            
            # Add thumbnail URLs if available
            if img.thumbnail_s3_keys:
                try:
                    thumbnail_keys = json.loads(img.thumbnail_s3_keys)
                    for size in thumbnail_keys.keys():
                        urls[f"thumbnail_{size}"] = f"{storage_service.image_base_url}/{img.file_id}/thumbnail?size={size}"
                except Exception as e:
                    logger.warning(f"Failed to parse thumbnail keys for {img.file_id}: {e}")
            
            image_metadata.append(ImageMetadataResponse(
                success=True,
                message="",
                file_id=img.file_id,
                filename=img.filename,
                original_filename=img.filename,
                content_type=img.content_type,
                size=img.file_size,
                dimensions=None,
                s3_key=img.s3_key,
                uploaded_at=img.uploaded_at,
                urls=urls,
                is_deleted=False
            ))
        
        return ImageListResponse(
            success=True,
            message=f"Retrieved {len(image_metadata)} images",
            images=image_metadata,
            total=len(image_metadata),  # TODO: Get actual total count from separate query
            page=(offset // limit) + 1,
            size=limit,
            has_next=has_next,
            has_prev=offset > 0
        )
        
    except Exception as e:
        logger.error(f"Error listing images: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list images"
        ) 