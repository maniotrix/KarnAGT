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
    Response,
    BackgroundTasks
)
from fastapi.responses import StreamingResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from PIL import Image
import io
import json
import asyncio
import time
from datetime import datetime, timedelta

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
    ImageValidationError,
    BulkImageUploadRequest,
    BulkImageUploadResponse,
    BulkImageDeleteRequest,
    BulkImageDeleteResponse,
    BulkImageMetadataRequest,
    BulkImageMetadataResponse,
    BulkImageOperationRequest,
    BulkImageOperationResponse,
    ImageSearchRequest,
    ImageSearchResponse,
    ImageStatisticsResponse
)
from app.models.schemas.common_schemas import BaseResponse
from app.api.v1.dependencies.auth import (
    get_current_verified_user,
    check_image_quota
)
from app.services.storage.storage import image_storage_service

from aicore.logger import get_logger

# Set up logger
logger = get_logger(__name__)

router = APIRouter()

settings = get_settings()

# Maximum files for bulk operations
MAX_BULK_UPLOAD_FILES = 20
MAX_BULK_DELETE_FILES = 100
MAX_BULK_METADATA_FILES = 200


@router.get("/files_status")
async def get_files_status():
    """Get files service status"""
    return {
        "status": "Files service ready", 
        "version": "2.0.0",  # Updated version for bulk operations
        "features": [
            "image_upload", 
            "image_serving", 
            "thumbnails", 
            "bulk_upload", 
            "bulk_delete",
            "bulk_metadata",
            "image_search",
            "image_statistics"
        ],
        "max_image_size_mb": settings.MAX_IMAGE_SIZE / (1024 * 1024),
        "allowed_types": settings.get_allowed_image_types(),
        "thumbnail_sizes": settings.get_thumbnail_sizes(),
        "thumbnail_format": settings.THUMBNAIL_FORMAT,
        "bulk_limits": {
            "max_bulk_upload": MAX_BULK_UPLOAD_FILES,
            "max_bulk_delete": MAX_BULK_DELETE_FILES,
            "max_bulk_metadata": MAX_BULK_METADATA_FILES
        }
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
        upload_result = await image_storage_service.upload_image(
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
                urls[f"thumbnail_{size}"] = f"{image_storage_service.image_base_url}/{upload_result['file_id']}/thumbnail?size={size}"

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


# BULK OPERATIONS
@router.post("/images/bulk-upload", response_model=BulkImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def bulk_upload_images(
    files: List[UploadFile] = File(..., description="List of image files to upload"),
    conversation_id: Optional[str] = Form(None, description="Associated conversation ID"),
    max_concurrent_uploads: int = Form(5, ge=1, le=10, description="Max concurrent uploads"),
    generate_thumbnails: bool = Form(True, description="Generate thumbnails for uploaded images"),
    current_user: User = Depends(check_image_quota),
    db: AsyncSession = Depends(get_db)
) -> BulkImageUploadResponse:
    """
    Bulk upload multiple images with concurrency control
    
    - **files**: List of image files (PNG, JPEG, GIF, WebP, max 20MB each)
    - **conversation_id**: Optional conversation context
    - **max_concurrent_uploads**: Control upload concurrency (1-10)
    - **generate_thumbnails**: Whether to generate thumbnails
    - Returns: Bulk upload results with success/failure details
    
    **Limits:**
    - Maximum 20 files per request
    - Pro or Enterprise subscription required
    - Consumes quota based on file size and processing
    """
    logger.info(f"Bulk upload request from user {current_user.user_id}, {len(files)} files")
    
    # Validate bulk upload limits
    if len(files) > MAX_BULK_UPLOAD_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files. Maximum {MAX_BULK_UPLOAD_FILES} files allowed per bulk upload"
        )
    
    if len(files) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )
    
    try:
        # Prepare files data
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
        
        # Perform bulk upload
        result = await image_storage_service.bulk_upload_images(
            files_data=files_data,
            user_id=current_user.user_id,
            db=db,
            conversation_id=conversation_id,
            max_concurrent=max_concurrent_uploads,
            generate_thumbnails=generate_thumbnails
        )
        
        # Convert uploaded_images to proper response format
        uploaded_images_response = []
        for upload_result in result["uploaded_images"]:
            # Extract dimensions if possible
            dimensions = None
            try:
                # Get original file data to extract dimensions
                original_file_data = next(
                    (fd[0] for fd in files_data if fd[1] == upload_result["filename"]), 
                    None
                )
                if original_file_data:
                    with Image.open(io.BytesIO(original_file_data)) as img:
                        dimensions = {"width": img.width, "height": img.height}
            except Exception as e:
                logger.warning(f"Could not extract image dimensions: {e}")
            
            # Build URLs dict with thumbnails
            urls = {
                "display": upload_result["url"], 
                "api": upload_result["url"]
            }

            # Add thumbnail URLs if thumbnails were generated
            if upload_result.get("thumbnail_s3_keys"):
                for size in upload_result["thumbnail_s3_keys"].keys():
                    urls[f"thumbnail_{size}"] = f"{image_storage_service.image_base_url}/{upload_result['file_id']}/thumbnail?size={size}"

            uploaded_images_response.append(ImageUploadResponse(
                success=True,
                message="Image uploaded successfully",
                file_id=upload_result["file_id"],
                filename=upload_result["filename"],
                original_filename=upload_result["filename"],
                content_type=upload_result["content_type"],
                size=upload_result["size"],
                dimensions=dimensions,
                urls=urls,
                s3_key=upload_result["s3_key"],
                uploaded_at=upload_result["uploaded_at"],
                openai_file_id=None,
                openai_expires_at=None
            ))
        
        response = BulkImageUploadResponse(
            success=True,
            message=f"Bulk upload completed: {result['successfully_uploaded']} successful, {result['failed_uploads']} failed",
            total_requested=result["total_requested"],
            successfully_uploaded=result["successfully_uploaded"],
            failed_uploads=result["failed_uploads"],
            uploaded_images=uploaded_images_response,
            failed_images=result["failed_images"],
            total_size_bytes=result["total_size_bytes"],
            upload_duration_seconds=result["upload_duration_seconds"],
            quota_consumed_usd=result["quota_consumed_usd"]
        )
        
        logger.info(f"Bulk upload completed for user {current_user.user_id}: {result['successfully_uploaded']} successful")
        return response
        
    except ValidationException as e:
        logger.warning(f"Bulk upload validation failed: {e}")
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
        logger.error(f"Error in bulk upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process bulk upload"
        )


@router.delete("/images/bulk-delete", response_model=BulkImageDeleteResponse)
async def bulk_delete_images(
    request: BulkImageDeleteRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
) -> BulkImageDeleteResponse:
    """
    Bulk delete multiple images with ownership validation
    
    - **file_ids**: List of file IDs to delete (max 100)
    - **confirm_deletion**: Must be True to confirm bulk deletion
    - Returns: Bulk deletion results with success/failure details
    
    **Security:**
    - Only deletes images owned by the authenticated user
    - Requires explicit confirmation via confirm_deletion=True
    """
    logger.info(f"Bulk delete request from user {current_user.user_id}, {len(request.file_ids)} files")
    
    # Validate bulk delete limits
    if len(request.file_ids) > MAX_BULK_DELETE_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files. Maximum {MAX_BULK_DELETE_FILES} files allowed per bulk delete"
        )
    
    try:
        # Perform bulk deletion
        result = await image_storage_service.bulk_delete_images(
            file_ids=request.file_ids,
            user_id=current_user.user_id,
            db=db
        )
        
        response = BulkImageDeleteResponse(
            success=True,
            message=f"Bulk deletion completed: {result['successfully_deleted']} successful, {result['failed_deletions']} failed",
            total_requested=result["total_requested"],
            successfully_deleted=result["successfully_deleted"],
            failed_deletions=result["failed_deletions"],
            deleted_file_ids=result["deleted_file_ids"],
            failed_file_ids=result["failed_file_ids"],
            freed_storage_bytes=result["freed_storage_bytes"]
        )
        
        logger.info(f"Bulk deletion completed for user {current_user.user_id}: {result['successfully_deleted']} successful")
        return response
        
    except Exception as e:
        logger.error(f"Error in bulk deletion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process bulk deletion"
        )


@router.post("/images/bulk-metadata", response_model=BulkImageMetadataResponse)
async def bulk_get_metadata(
    request: BulkImageMetadataRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
) -> BulkImageMetadataResponse:
    """
    Bulk retrieve metadata for multiple images
    
    - **file_ids**: List of file IDs to get metadata for (max 200)
    - **include_urls**: Include access URLs in response
    - **include_thumbnails**: Include thumbnail URLs
    - Returns: Bulk metadata results with found/missing details
    
    **Security:**
    - Only returns metadata for images owned by the authenticated user
    """
    logger.info(f"Bulk metadata request from user {current_user.user_id}, {len(request.file_ids)} files")
    
    # Validate bulk metadata limits
    if len(request.file_ids) > MAX_BULK_METADATA_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files. Maximum {MAX_BULK_METADATA_FILES} files allowed per bulk metadata request"
        )
    
    try:
        # Perform bulk metadata retrieval
        result = await image_storage_service.bulk_get_metadata(
            file_ids=request.file_ids,
            user_id=current_user.user_id,
            db=db,
            include_urls=request.include_urls,
            include_thumbnails=request.include_thumbnails
        )
        
        # Convert to response format
        images_metadata_response = []
        for metadata in result["images_metadata"]:
            images_metadata_response.append(ImageMetadataResponse(
                success=True,
                message="",
                file_id=metadata["file_id"],
                filename=metadata["filename"],
                original_filename=metadata["original_filename"],
                content_type=metadata["content_type"],
                size=metadata["size"],
                dimensions=metadata["dimensions"],
                s3_key=metadata["s3_key"],
                urls=metadata["urls"],
                uploaded_at=metadata["uploaded_at"],
                is_deleted=metadata["is_deleted"]
            ))
        
        response = BulkImageMetadataResponse(
            success=True,
            message=f"Bulk metadata retrieval completed: {result['found_images']} found, {result['missing_images']} missing",
            total_requested=result["total_requested"],
            found_images=result["found_images"],
            missing_images=result["missing_images"],
            images_metadata=images_metadata_response,
            missing_file_ids=result["missing_file_ids"]
        )
        
        logger.info(f"Bulk metadata completed for user {current_user.user_id}: {result['found_images']} found")
        return response
        
    except Exception as e:
        logger.error(f"Error in bulk metadata retrieval: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process bulk metadata request"
        )


@router.post("/images/search", response_model=ImageSearchResponse)
async def search_images(
    request: ImageSearchRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
) -> ImageSearchResponse:
    """
    Search user's images with advanced filtering
    
    - **query**: Text search in filename
    - **content_type**: Filter by content type
    - **size_min/size_max**: File size range filters
    - **uploaded_after/uploaded_before**: Date range filters
    - **has_thumbnails**: Filter by thumbnail presence
    - **tags**: Filter by tags (if implemented)
    - **limit/offset**: Pagination
    - **sort_by/sort_order**: Sorting options
    - Returns: Search results with metadata
    
    **Security:**
    - Only searches images owned by the authenticated user
    """
    logger.info(f"Image search request from user {current_user.user_id}")
    
    try:
        # Perform image search
        result = await image_storage_service.search_images(
            user_id=current_user.user_id,
            db=db,
            query=request.query,
            content_type=request.content_type,
            size_min=request.size_min,
            size_max=request.size_max,
            uploaded_after=request.uploaded_after,
            uploaded_before=request.uploaded_before,
            has_thumbnails=request.has_thumbnails,
            tags=request.tags,
            limit=request.limit,
            offset=request.offset,
            sort_by=request.sort_by,
            sort_order=request.sort_order
        )
        
        # Convert to response format
        images_response = []
        for metadata in result["images"]:
            images_response.append(ImageMetadataResponse(
                success=True,
                message="",
                file_id=metadata["file_id"],
                filename=metadata["filename"],
                original_filename=metadata["original_filename"],
                content_type=metadata["content_type"],
                size=metadata["size"],
                dimensions=metadata["dimensions"],
                s3_key=metadata["s3_key"],
                urls=metadata["urls"],
                uploaded_at=metadata["uploaded_at"],
                is_deleted=metadata["is_deleted"]
            ))
        
        response = ImageSearchResponse(
            success=True,
            message=f"Search completed: {result['total_found']} images found",
            query_summary=result["query_summary"],
            images=images_response,
            total_found=result["total_found"],
            page=result["page"],
            size=result["size"],
            has_next=result["has_next"],
            has_prev=result["has_prev"],
            search_duration_ms=result["search_duration_ms"]
        )
        
        logger.info(f"Image search completed for user {current_user.user_id}: {result['total_found']} found")
        return response
        
    except Exception as e:
        logger.error(f"Error in image search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process image search"
        )


@router.get("/images/statistics", response_model=ImageStatisticsResponse)
async def get_image_statistics(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
) -> ImageStatisticsResponse:
    """
    Get comprehensive statistics about user's images
    
    - Returns: Various image statistics including storage usage, file types, etc.
    
    **Security:**
    - Only returns statistics for images owned by the authenticated user
    """
    logger.info(f"Image statistics request from user {current_user.user_id}")
    
    try:
        # Get image statistics
        result = await image_storage_service.get_user_image_statistics(
            user_id=current_user.user_id,
            db=db
        )
        
        response = ImageStatisticsResponse(
            success=True,
            message="Image statistics retrieved successfully",
            total_images=result["total_images"],
            total_storage_bytes=result["total_storage_bytes"],
            total_thumbnails=result["total_thumbnails"],
            images_by_type=result["images_by_type"],
            images_by_month=result["images_by_month"],
            average_file_size=result["average_file_size"],
            largest_file_size=result["largest_file_size"],
            smallest_file_size=result["smallest_file_size"],
            quota_used_percentage=result["quota_used_percentage"],
            storage_used_mb=result["storage_used_mb"]
        )
        
        logger.info(f"Image statistics completed for user {current_user.user_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error getting image statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get image statistics"
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
        presigned_url = await image_storage_service.serve_image_securely(
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
        presigned_url = await image_storage_service.serve_thumbnail_securely(
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
        image_record = await image_storage_service.validate_file_ownership(
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
        urls = {"api": f"{image_storage_service.image_base_url}/{image_record.file_id}"}

        # Add thumbnail URLs if available
        if image_record.thumbnail_s3_keys is not None:
            try:
                thumbnail_keys = json.loads(image_record.thumbnail_s3_keys)
                for size in thumbnail_keys.keys():
                    urls[f"thumbnail_{size}"] = f"{image_storage_service.image_base_url}/{image_record.file_id}/thumbnail?size={size}"
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
        deletion_successful = await image_storage_service.delete_image_securely(
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
        images = await image_storage_service.get_user_images(
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
            urls = {"api": f"{image_storage_service.image_base_url}/{img.file_id}"}
            
            # Add thumbnail URLs if available
            if img.thumbnail_s3_keys is not None:
                try:
                    thumbnail_keys = json.loads(img.thumbnail_s3_keys)
                    for size in thumbnail_keys.keys():
                        urls[f"thumbnail_{size}"] = f"{image_storage_service.image_base_url}/{img.file_id}/thumbnail?size={size}"
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


@router.post("/images/bulk-presigned-urls")
async def bulk_generate_presigned_urls(
    request: BulkImageMetadataRequest,  # Reuse existing request model
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk generate presigned URLs for image attachments (2025 Industry Standard)
    
    This follows the modern approach: generate URLs only when needed for display.
    - **file_ids**: List of file IDs to generate URLs for (max 200)
    - Validates file ownership through database lookup
    - Generates secure presigned URLs (24-hour expiration) 
    - Returns URLs that work without authentication in HTML img tags
    - Can be cached on frontend to avoid repeated calls
    
    **Security:**
    - Only generates URLs for images owned by the authenticated user
    """
    logger.info(f"Bulk presigned URL request from user {current_user.user_id}, {len(request.file_ids)} files")
    
    # Validate bulk URL limits (same as metadata)
    if len(request.file_ids) > MAX_BULK_METADATA_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files. Maximum {MAX_BULK_METADATA_FILES} files allowed per bulk URL request"
        )
    
    try:
        url_results = {}
        
        # Process each file ID with ownership validation
        for file_id in request.file_ids:
            try:
                # Validate ownership and generate presigned URL
                presigned_url = await image_storage_service.serve_image_securely(
                    file_id=file_id,
                    user_id=current_user.user_id, 
                    db=db
                )
                
                if presigned_url:
                    url_results[file_id] = {
                        "display": presigned_url,
                        "thumbnail": presigned_url,  # Use same URL for now
                        "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
                        "success": True
                    }
                    logger.debug(f"Generated presigned URL for {file_id}")
                else:
                    url_results[file_id] = {
                        "error": "Access denied or file not found",
                        "success": False
                    }
                    logger.warning(f"Access denied for file {file_id}")
                    
            except Exception as e:
                logger.error(f"Error generating URL for {file_id}: {e}")
                url_results[file_id] = {
                    "error": f"Failed to generate URL: {str(e)}",
                    "success": False
                }
        
        successful_urls = len([r for r in url_results.values() if r.get('success')])
        
        return {
            "success": True,
            "message": f"Generated presigned URLs for {successful_urls}/{len(request.file_ids)} files",
            "total_requested": len(request.file_ids),
            "successful_urls": successful_urls,
            "failed_urls": len(request.file_ids) - successful_urls,
            "urls": url_results
        }
        
    except Exception as e:
        logger.error(f"Error in bulk presigned URL generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate presigned URLs"
        ) 