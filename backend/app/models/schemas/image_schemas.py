"""Image handling Pydantic schemas"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import Field, ConfigDict, validator

from .common_schemas import BaseSchema, BaseResponse
from .file_schemas import FileUploadResponse


class ImageUploadResponse(BaseResponse):
    """Image upload response schema"""
    file_id: str
    filename: str
    original_filename: str
    content_type: str
    size: int
    dimensions: Optional[Dict[str, int]] = None  # {"width": 1920, "height": 1080}
    urls: Dict[str, str] = {}  # {"display": "...", "thumbnail": "...", "api": "..."}
    s3_key: str
    uploaded_at: datetime
    
    # OpenAI integration (for vision API)
    openai_file_id: Optional[str] = None
    openai_expires_at: Optional[datetime] = None


class ImageMetadataResponse(BaseResponse):
    """Image metadata response schema"""
    file_id: str
    filename: str
    original_filename: str
    content_type: str
    size: int
    dimensions: Optional[Dict[str, int]] = None
    s3_key: str
    urls: Dict[str, str] = {}
    uploaded_at: datetime
    is_deleted: bool = False


class ImageListResponse(BaseResponse):
    """Image list response schema"""
    images: List[ImageMetadataResponse]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool


class ImageValidationError(BaseResponse):
    """Image validation error response"""
    success: bool = False
    error_code: str
    error_details: Dict[str, Any] = {}


# Image attachment format for Message.attachments field
class ImageAttachment(BaseSchema):
    """Image attachment schema for message attachments"""
    type: str = Field(default="image", description="Attachment type")
    file_id: str
    openai_file_id: Optional[str] = None
    filename: str
    original_filename: str
    content_type: str
    size: int
    dimensions: Optional[Dict[str, int]] = None
    urls: Dict[str, str]
    s3_key: str
    openai_expires_at: Optional[datetime] = None
    detail_level: str = Field("high", description="OpenAI Vision API detail level")
    uploaded_at: datetime
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "image",
                "file_id": "img_7f9e2b4c",
                "openai_file_id": "file-abc123xyz",
                "filename": "diagram.png",
                "original_filename": "my_diagram.png",
                "content_type": "image/png",
                "size": 1024000,
                "dimensions": {"width": 1920, "height": 1080},
                "urls": {
                    "display": "http://localhost:9000/minio-files/images/2024/01/15/img_7f9e2b4c.png",
                    "thumbnail": "http://localhost:8000/api/v1/images/img_7f9e2b4c/thumbnail",
                    "api": "http://localhost:8000/api/v1/images/img_7f9e2b4c"
                },
                "s3_key": "images/2024/01/15/img_7f9e2b4c.png",
                "detail_level": "high",
                "uploaded_at": "2024-01-15T12:00:00Z"
            }
        }
    )


# Bulk Operations Schemas
class BulkImageUploadRequest(BaseSchema):
    """Bulk image upload request schema"""
    conversation_id: Optional[str] = Field(None, description="Associated conversation ID")
    max_concurrent_uploads: int = Field(5, ge=1, le=10, description="Max concurrent uploads")
    generate_thumbnails: bool = Field(True, description="Generate thumbnails for uploaded images")
    
    @validator('max_concurrent_uploads')
    def validate_max_concurrent(cls, v):
        if v > 10:
            raise ValueError("Maximum 10 concurrent uploads allowed")
        return v


class BulkImageUploadResponse(BaseResponse):
    """Bulk image upload response schema"""
    total_requested: int
    successfully_uploaded: int
    failed_uploads: int
    uploaded_images: List[ImageUploadResponse]
    failed_images: List[Dict[str, Any]]  # {"filename": "error.jpg", "error": "File too large"}
    total_size_bytes: int
    upload_duration_seconds: float
    quota_consumed_usd: float


class BulkImageDeleteRequest(BaseSchema):
    """Bulk image delete request schema"""
    file_ids: List[str] = Field(..., min_length=1, max_length=100, description="List of file IDs to delete")
    confirm_deletion: bool = Field(False, description="Must be True to confirm bulk deletion")
    
    @validator('confirm_deletion')
    def validate_confirmation(cls, v):
        if not v:
            raise ValueError("Must confirm bulk deletion by setting confirm_deletion=True")
        return v


class BulkImageDeleteResponse(BaseResponse):
    """Bulk image delete response schema"""
    total_requested: int
    successfully_deleted: int
    failed_deletions: int
    deleted_file_ids: List[str]
    failed_file_ids: List[Dict[str, str]]  # {"file_id": "img_123", "error": "Not found"}
    freed_storage_bytes: int


class BulkImageMetadataRequest(BaseSchema):
    """Bulk image metadata request schema"""
    file_ids: List[str] = Field(..., min_length=1, max_length=200, description="List of file IDs")
    include_urls: bool = Field(True, description="Include access URLs in response")
    include_thumbnails: bool = Field(True, description="Include thumbnail URLs")


class BulkImageMetadataResponse(BaseResponse):
    """Bulk image metadata response schema"""
    total_requested: int
    found_images: int
    missing_images: int
    images_metadata: List[ImageMetadataResponse]
    missing_file_ids: List[str]


class BulkImageOperationRequest(BaseSchema):
    """Bulk image operation request schema"""
    file_ids: List[str] = Field(..., min_length=1, max_length=100, description="List of file IDs")
    operation: str = Field(..., description="Operation to perform")
    operation_params: Dict[str, Any] = Field(default_factory=dict, description="Operation-specific parameters")
    
    @validator('operation')
    def validate_operation(cls, v):
        valid_operations = [
            'regenerate_thumbnails',
            'update_metadata',
            'change_permissions',
            'compress_images',
            'convert_format',
            'create_zip_archive'
        ]
        if v not in valid_operations:
            raise ValueError(f'Operation must be one of: {valid_operations}')
        return v


class BulkImageOperationResponse(BaseResponse):
    """Bulk image operation response schema"""
    operation: str
    total_requested: int
    successfully_processed: int
    failed_operations: int
    processed_file_ids: List[str]
    failed_operations_details: List[Dict[str, str]]
    operation_results: Dict[str, Any] = Field(default_factory=dict)  # Operation-specific results


class ImageSearchRequest(BaseSchema):
    """Image search request schema"""
    query: Optional[str] = Field(None, description="Search query for filename or metadata")
    content_type: Optional[str] = Field(None, description="Filter by content type")
    size_min: Optional[int] = Field(None, ge=0, description="Minimum file size in bytes")
    size_max: Optional[int] = Field(None, ge=0, description="Maximum file size in bytes")
    uploaded_after: Optional[datetime] = Field(None, description="Filter images uploaded after this date")
    uploaded_before: Optional[datetime] = Field(None, description="Filter images uploaded before this date")
    has_thumbnails: Optional[bool] = Field(None, description="Filter images with/without thumbnails")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    limit: int = Field(20, ge=1, le=100, description="Number of results per page")
    offset: int = Field(0, ge=0, description="Number of results to skip")
    sort_by: str = Field("uploaded_at", description="Sort field")
    sort_order: str = Field("desc", description="Sort order: asc or desc")
    
    @validator('sort_by')
    def validate_sort_by(cls, v):
        valid_fields = ['uploaded_at', 'filename', 'file_size', 'content_type']
        if v not in valid_fields:
            raise ValueError(f'sort_by must be one of: {valid_fields}')
        return v
    
    @validator('sort_order')
    def validate_sort_order(cls, v):
        if v not in ['asc', 'desc']:
            raise ValueError('sort_order must be "asc" or "desc"')
        return v


class ImageSearchResponse(BaseResponse):
    """Image search response schema"""
    query_summary: Dict[str, Any]
    images: List[ImageMetadataResponse]
    total_found: int
    page: int
    size: int
    has_next: bool
    has_prev: bool
    search_duration_ms: int


class ImageStatisticsResponse(BaseResponse):
    """Image statistics response schema"""
    total_images: int
    total_storage_bytes: int
    total_thumbnails: int
    images_by_type: Dict[str, int]  # {"image/png": 45, "image/jpeg": 23}
    images_by_month: Dict[str, int]  # {"2024-01": 12, "2024-02": 8}
    average_file_size: int
    largest_file_size: int
    smallest_file_size: int
    quota_used_percentage: float
    storage_used_mb: float 