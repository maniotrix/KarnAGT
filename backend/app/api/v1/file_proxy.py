"""
File Proxy API Endpoints
Secure proxy endpoints for serving files to code execution sessions
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, Union

from fastapi import APIRouter, Depends, HTTPException, Request, Query, Response
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_404_NOT_FOUND, HTTP_403_FORBIDDEN, HTTP_400_BAD_REQUEST

from app.core.database import get_db
from app.api.v1.dependencies.auth import get_current_user, get_current_user_or_service, ServiceAuth
from app.core.file_proxy_constants import (
    FileProxyEndpoints,
    FileProxyParams,
    FileProxyHeaders,
    FileProxyConfig,
    FileProxyErrors,
    FileProxyType,
    validate_file_proxy_params,
    get_file_proxy_metadata
)
from app.models.database.user import User
from app.services.storage.storage import image_storage_service
from app.logging.logger import get_logger

logger = get_logger(__name__)

# Create router with file proxy endpoints
router = APIRouter(
    prefix="",  # No prefix since paths are defined in constants
    tags=["file-proxy"],
    responses={
        404: {"description": "File not found"},
        403: {"description": "Access denied"},
        400: {"description": "Invalid request"}
    }
)

# =============================================================================
# IMAGE PROXY ENDPOINT
# =============================================================================

@router.get(FileProxyEndpoints.IMAGE_PROXY_ROUTE)
async def proxy_image_file(
    file_id: str,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    auth: Union[User, ServiceAuth] = Depends(get_current_user_or_service),
    download: Optional[bool] = Query(False, description="Force download vs inline display"),
    filename: Optional[str] = Query(None, description="Override filename for download"),
    cache: Optional[int] = Query(FileProxyConfig.DEFAULT_CACHE_DURATION, description="Cache duration in seconds")
) -> RedirectResponse:
    """
    Proxy endpoint for image files with ownership validation
    
    Validates user ownership and returns a redirect to presigned S3/MinIO URL
    for secure file access by code execution sessions.
    
    Args:
        file_id: Image file ID (e.g., img_abc123)
        download: Whether to force download vs inline display
        filename: Override filename for Content-Disposition header
        cache: Cache duration in seconds (max 24 hours)
        
    Returns:
        Redirect to presigned URL for file access
    """
    # Service-to-service authentication working! Debug completed.
    
    start_time = datetime.utcnow()
    
    try:
        # Validate parameters
        params = validate_file_proxy_params(
            FileProxyType.IMAGE,
            file_id=file_id,
            download=download,
            filename=filename,
            cache=cache
        )
        
        # Handle service vs user authentication differently
        if isinstance(auth, ServiceAuth):
            # Service token - skip ownership validation, direct file access
            logger.info(f"[PROXY-DEBUG] Image proxy request: file_id={file_id}, service={auth.service_name}")
            
            # Get file record directly without ownership check (service access)
            image_record = await image_storage_service.get_file_record_by_id(file_id, db)
            
            if not image_record:
                logger.warning(f"Image not found: file_id={file_id}, service={auth.service_name}")
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND,
                    detail=FileProxyErrors.FILE_NOT_FOUND
                )
        else:
            # User token - validate ownership as before
            logger.info(f"Image proxy request: file_id={file_id}, user={auth.user_id}")
            
            image_record = await image_storage_service.validate_file_ownership(
                file_id, str(auth.user_id), db
            )
            
            if not image_record:
                logger.warning(f"Image access denied: file_id={file_id}, user={auth.user_id}")
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND,
                    detail=FileProxyErrors.FILE_NOT_FOUND
                )
        
        # Generate short-lived presigned URL for proxy access
        try:
            # Use internal URL for service calls, external URL for browser requests
            if isinstance(auth, ServiceAuth):
                presigned_url = await image_storage_service.get_internal_presigned_url(
                    str(image_record.s3_key),  # Ensure it's a string value
                    expire_seconds=min(cache or FileProxyConfig.DEFAULT_PRESIGNED_EXPIRY, 
                                     FileProxyConfig.MAX_PRESIGNED_EXPIRY)
                )
            else:
                presigned_url = await image_storage_service.get_presigned_url(
                    str(image_record.s3_key),  # Ensure it's a string value
                    expire_seconds=min(cache or FileProxyConfig.DEFAULT_PRESIGNED_EXPIRY, 
                                     FileProxyConfig.MAX_PRESIGNED_EXPIRY)
                )
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {file_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=FileProxyErrors.PROCESSING_ERROR
            )
        
        # Set response headers for tracking and caching
        response.headers[FileProxyHeaders.X_FILE_ID] = str(file_id)
        response.headers[FileProxyHeaders.X_FILE_TYPE] = FileProxyType.IMAGE.value
        
        if isinstance(auth, ServiceAuth):
            response.headers[FileProxyHeaders.X_USER_ID] = f"service:{auth.service_name}"
        else:
            response.headers[FileProxyHeaders.X_USER_ID] = str(auth.user_id)
            
        response.headers[FileProxyHeaders.CACHE_CONTROL] = f"private, max-age={min(cache or FileProxyConfig.DEFAULT_CACHE_DURATION, FileProxyConfig.MAX_CACHE_DURATION)}"
        
        # Log successful access
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        if isinstance(auth, ServiceAuth):
            logger.info(f"Image proxy success: file_id={file_id}, service={auth.service_name}, time={processing_time:.3f}s")
        else:
            logger.info(f"Image proxy success: file_id={file_id}, user={auth.user_id}, time={processing_time:.3f}s")
        
        # Return redirect to presigned URL
        return RedirectResponse(
            url=presigned_url,
            status_code=302  # Temporary redirect
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid image proxy request: file_id={file_id}, error={e}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in image proxy: file_id={file_id}, error={e}")
        raise HTTPException(
            status_code=500,
            detail=FileProxyErrors.PROCESSING_ERROR
        )

# =============================================================================
# KNOWLEDGE FILE PROXY ENDPOINT  
# =============================================================================

@router.get(FileProxyEndpoints.KNOWLEDGE_PROXY_ROUTE)
async def proxy_knowledge_file(
    knowledge_file_id: str,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    auth: Union[User, ServiceAuth] = Depends(get_current_user_or_service),
    download: Optional[bool] = Query(False, description="Force download vs inline display"),
    filename: Optional[str] = Query(None, description="Override filename for download"),
    cache: Optional[int] = Query(FileProxyConfig.DEFAULT_CACHE_DURATION, description="Cache duration in seconds")
) -> RedirectResponse:
    """
    Proxy endpoint for knowledge files with ownership validation
    
    Validates user ownership through conversation/collection access and returns
    a redirect to presigned S3/MinIO URL for secure file access.
    
    Args:
        knowledge_file_id: Knowledge file database ID
        download: Whether to force download vs inline display
        filename: Override filename for Content-Disposition header
        cache: Cache duration in seconds (max 24 hours)
        
    Returns:
        Redirect to presigned URL for file access
    """
    start_time = datetime.utcnow()
    
    try:
        # Validate parameters
        params = validate_file_proxy_params(
            FileProxyType.KNOWLEDGE,
            knowledge_file_id=knowledge_file_id,
            download=download,
            filename=filename,
            cache=cache
        )
        
        # Handle service vs user authentication differently
        from sqlalchemy import select
        from app.models.database.knowledge_file import KnowledgeFile
        
        if isinstance(auth, ServiceAuth):
            # Service token - skip ownership validation, direct file access
            logger.info(f"Knowledge proxy request: knowledge_file_id={knowledge_file_id}, service={auth.service_name}")
            
            # Get knowledge file record directly without ownership check (service access)
            query = select(KnowledgeFile).where(KnowledgeFile.id == knowledge_file_id)
            result = await db.execute(query)
            knowledge_file = result.scalar_one_or_none()
            
            if not knowledge_file:
                logger.warning(f"Knowledge file not found: knowledge_file_id={knowledge_file_id}, service={auth.service_name}")
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND,
                    detail=FileProxyErrors.FILE_NOT_FOUND
                )
        else:
            # User token - validate ownership as before
            logger.info(f"Knowledge proxy request: knowledge_file_id={knowledge_file_id}, user={auth.user_id}")
            
            # Query knowledge file directly using user_id (ownership validation)
            query = select(KnowledgeFile).where(
                KnowledgeFile.id == knowledge_file_id,
                KnowledgeFile.user_id == auth.user_id  # Use UUID user_id field
            )
            result = await db.execute(query)
            knowledge_file = result.scalar_one_or_none()
            
            if not knowledge_file:
                logger.warning(f"Knowledge file access denied: knowledge_file_id={knowledge_file_id}, user={auth.user_id}")
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND,
                    detail=FileProxyErrors.FILE_NOT_FOUND
                )
        
        # Generate presigned URL using storage service
        try:
            # Get S3 key from knowledge file
            s3_key = str(knowledge_file.file_path)
            
            # Use internal URL for service calls, external URL for browser requests
            if isinstance(auth, ServiceAuth):
                presigned_url = await image_storage_service.get_internal_presigned_url(
                    s3_key,
                    expire_seconds=min(cache or FileProxyConfig.DEFAULT_PRESIGNED_EXPIRY,
                                     FileProxyConfig.MAX_PRESIGNED_EXPIRY)
                )
            else:
                presigned_url = await image_storage_service.get_presigned_url(
                    s3_key,
                    expire_seconds=min(cache or FileProxyConfig.DEFAULT_PRESIGNED_EXPIRY,
                                     FileProxyConfig.MAX_PRESIGNED_EXPIRY)
                )
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for knowledge_file_id={knowledge_file_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=FileProxyErrors.PROCESSING_ERROR
            )
        
        # Set response headers for tracking and caching
        response.headers[FileProxyHeaders.X_FILE_ID] = str(knowledge_file_id)
        response.headers[FileProxyHeaders.X_FILE_TYPE] = FileProxyType.KNOWLEDGE.value
        
        if isinstance(auth, ServiceAuth):
            response.headers[FileProxyHeaders.X_USER_ID] = f"service:{auth.service_name}"
        else:
            response.headers[FileProxyHeaders.X_USER_ID] = str(auth.user_id)
            
        response.headers[FileProxyHeaders.CACHE_CONTROL] = f"private, max-age={min(cache or FileProxyConfig.DEFAULT_CACHE_DURATION, FileProxyConfig.MAX_CACHE_DURATION)}"
        
        # Log successful access
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        if isinstance(auth, ServiceAuth):
            logger.info(f"Knowledge proxy success: knowledge_file_id={knowledge_file_id}, service={auth.service_name}, time={processing_time:.3f}s")
        else:
            logger.info(f"Knowledge proxy success: knowledge_file_id={knowledge_file_id}, user={auth.user_id}, time={processing_time:.3f}s")
        
        # Return redirect to presigned URL
        return RedirectResponse(
            url=presigned_url,
            status_code=302  # Temporary redirect
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid knowledge proxy request: knowledge_file_id={knowledge_file_id}, error={e}")
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in knowledge proxy: knowledge_file_id={knowledge_file_id}, error={e}")
        raise HTTPException(
            status_code=500,
            detail=FileProxyErrors.PROCESSING_ERROR
        )

# =============================================================================
# CODE GENERATED FILE PROXY ENDPOINT
# =============================================================================

@router.get(FileProxyEndpoints.CODE_GENERATED_PROXY_ROUTE)
async def proxy_code_generated_file(
    file_id: str,
    request: Request,
    response: Response,
    auth: Union[User, ServiceAuth] = Depends(get_current_user_or_service)
) -> RedirectResponse:
    """
    Proxy endpoint for code-generated files - simple auth check, no ownership validation
    
    Validates user authentication and returns a redirect to presigned S3/MinIO URL
    for secure file access.
    
    Args:
        file_id: Code-generated file ID with CODE_GENERATED_FILE_PREFIX (e.g., "code_generated_2024_01_15_abc12345_myfile.png")
        
    Returns:
        Redirect to presigned URL for file access
    """
    start_time = datetime.utcnow()
    
    try:
        # Validate file ID format
        expected_prefix = f"{FileProxyConfig.CODE_GENERATED_FILE_PREFIX}_"
        
        if not file_id.startswith(expected_prefix):
            logger.warning(f"Invalid code-generated file ID format: {file_id}")
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Invalid file ID format"
            )
        
        # Construct S3 key from file ID
        s3_key = f"{FileProxyConfig.CODE_SANDBOX_GENERATED_PREFIX}/{file_id}"
        
        # Generate presigned URL directly (no ownership checks for code-generated files)
        try:
            # Use internal URL for service calls, external URL for browser requests
            if isinstance(auth, ServiceAuth):
                presigned_url = await image_storage_service.get_internal_presigned_url(
                    s3_key,
                    expire_seconds=FileProxyConfig.DEFAULT_PRESIGNED_EXPIRY
                )
            else:
                presigned_url = await image_storage_service.get_presigned_url(
                    s3_key,
                    expire_seconds=FileProxyConfig.DEFAULT_PRESIGNED_EXPIRY
                )
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for code-generated file {file_id}: {e}")
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=FileProxyErrors.FILE_NOT_FOUND
            )
        
        # Set response headers for tracking and caching
        response.headers[FileProxyHeaders.X_FILE_ID] = str(file_id)
        response.headers[FileProxyHeaders.X_FILE_TYPE] = FileProxyType.CODE_GENERATED.value
        
        if isinstance(auth, ServiceAuth):
            response.headers[FileProxyHeaders.X_USER_ID] = f"service:{auth.service_name}"
        else:
            response.headers[FileProxyHeaders.X_USER_ID] = str(auth.user_id)
            
        response.headers[FileProxyHeaders.CACHE_CONTROL] = f"private, max-age={FileProxyConfig.DEFAULT_CACHE_DURATION}"
        
        # Log successful access
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        if isinstance(auth, ServiceAuth):
            logger.info(f"Code-generated file proxy success: file_id={file_id}, service={auth.service_name}, time={processing_time:.3f}s")
        else:
            logger.info(f"Code-generated file proxy success: file_id={file_id}, user={auth.user_id}, time={processing_time:.3f}s")
        
        # Return redirect to presigned URL
        return RedirectResponse(
            url=presigned_url,
            status_code=302  # Temporary redirect
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in code-generated file proxy: file_id={file_id}, error={e}")
        raise HTTPException(
            status_code=500,
            detail=FileProxyErrors.PROCESSING_ERROR
        )

# =============================================================================
# HEALTH CHECK ENDPOINT
# =============================================================================

@router.get(f"{FileProxyEndpoints.BASE_PATH}/health")
async def file_proxy_health() -> Dict[str, Any]:
    """
    Health check endpoint for file proxy system
    
    Returns:
        System health status and configuration
    """  
    return {
        "status": "healthy",
        "service": "file-proxy",
        "version": "1.0",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "image_proxy": FileProxyEndpoints.IMAGE_PROXY,
            "knowledge_proxy": FileProxyEndpoints.KNOWLEDGE_PROXY,
            "code_generated_proxy": FileProxyEndpoints.CODE_GENERATED_PROXY
        },
        "config": {
            "max_file_size_mb": FileProxyConfig.MAX_FILE_SIZE_MB,
            "default_cache_duration": FileProxyConfig.DEFAULT_CACHE_DURATION,
            "max_cache_duration": FileProxyConfig.MAX_CACHE_DURATION,
            "default_presigned_expiry": FileProxyConfig.DEFAULT_PRESIGNED_EXPIRY
        }
    }