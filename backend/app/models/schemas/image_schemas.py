"""Image handling Pydantic schemas"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import Field, validator

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
    
    class Config:
        schema_extra = {
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
                    "display": "http://localhost:9000/chatgpt-files/images/2024/01/15/img_7f9e2b4c.png",
                    "thumbnail": "http://localhost:8000/api/v1/images/img_7f9e2b4c/thumbnail",
                    "api": "http://localhost:8000/api/v1/images/img_7f9e2b4c"
                },
                "s3_key": "images/2024/01/15/img_7f9e2b4c.png",
                "detail_level": "high",
                "uploaded_at": "2024-01-15T12:00:00Z"
            }
        } 