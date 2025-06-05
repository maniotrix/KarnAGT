"""File handling Pydantic schemas"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import Field, validator

from .common_schemas import (
    BaseSchema, 
    BaseResponse, 
    PaginatedResponse, 
    ProcessingStatus,
    SearchParams,
    FileMetadata
)


class FileUploadResponse(BaseResponse):
    """File upload response schema"""
    file_id: str
    filename: str
    size: int
    file_type: str
    status: ProcessingStatus
    upload_url: Optional[str] = None  # For direct S3 uploads
    processing_eta_seconds: Optional[int] = None


class FileProcessingStatus(BaseSchema):
    """File processing status schema"""
    file_id: str
    filename: str
    status: ProcessingStatus
    progress_percentage: float = Field(ge=0.0, le=100.0)
    chunks_processed: int = 0
    total_chunks: int = 0
    embeddings_generated: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None


class FileResponse(BaseSchema):
    """File response schema"""
    id: int
    file_id: str
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    processing_status: ProcessingStatus
    chunks_count: int = 0
    embeddings_count: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}
    created_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class FileListResponse(PaginatedResponse[FileResponse]):
    """Paginated file list response"""
    pass


class FileSearchRequest(SearchParams):
    """File search request schema"""
    file_types: Optional[List[str]] = Field(None, description="Filter by file types")
    status: Optional[ProcessingStatus] = Field(None, description="Filter by processing status")
    min_size: Optional[int] = Field(None, ge=0, description="Minimum file size")
    max_size: Optional[int] = Field(None, ge=0, description="Maximum file size")
    date_from: Optional[datetime] = Field(None, description="Uploaded from date")
    date_to: Optional[datetime] = Field(None, description="Uploaded to date")


class FileSearchResult(BaseSchema):
    """File search result schema"""
    file_id: str
    filename: str
    chunk_content: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    chunk_index: int
    page_number: Optional[int] = None
    highlighted_content: Optional[str] = None


class FileSearchResponse(BaseResponse):
    """File search response schema"""
    results: List[FileSearchResult]
    total_results: int
    search_time_ms: int
    files_searched: int


class FileContentRequest(BaseSchema):
    """File content request schema"""
    page: Optional[int] = Field(None, ge=1, description="Page number for PDFs")
    chunk_index: Optional[int] = Field(None, ge=0, description="Specific chunk index")
    format: str = Field("text", description="Response format")
    
    @validator('format')
    def validate_format(cls, v):
        valid_formats = ['text', 'markdown', 'html', 'json']
        if v not in valid_formats:
            raise ValueError(f'Format must be one of: {valid_formats}')
        return v


class FileContentResponse(BaseResponse):
    """File content response schema"""
    file_id: str
    content: str
    format: str
    total_pages: Optional[int] = None
    current_page: Optional[int] = None
    total_chunks: int
    chunk_index: Optional[int] = None


class FileReprocessRequest(BaseSchema):
    """File reprocess request schema"""
    chunk_size: Optional[int] = Field(None, ge=100, le=8000, description="New chunk size")
    overlap_size: Optional[int] = Field(None, ge=0, le=1000, description="Chunk overlap size")
    force_reprocess: bool = Field(False, description="Force reprocessing even if already processed")


class FileBulkAction(BaseSchema):
    """Bulk file action schema"""
    file_ids: List[str] = Field(..., min_length=1, max_length=50, description="File IDs")
    action: str = Field(..., description="Action to perform")
    
    @validator('action')
    def validate_action(cls, v):
        valid_actions = ['delete', 'reprocess', 'archive', 'download']
        if v not in valid_actions:
            raise ValueError(f'Action must be one of: {valid_actions}')
        return v


class FileBulkResponse(BaseResponse):
    """Bulk file action response"""
    processed_count: int
    successful_ids: List[str]
    failed_ids: List[str]
    errors: Dict[str, str] = {}
    download_url: Optional[str] = None  # For bulk download


class FileStats(BaseSchema):
    """File statistics schema"""
    total_files: int
    total_size_mb: float
    processing_count: int
    completed_count: int
    failed_count: int
    file_types: Dict[str, int]
    average_processing_time_seconds: float
    storage_quota_used_mb: float
    storage_quota_limit_mb: float


class FileAnalytics(BaseResponse):
    """File analytics response"""
    stats: FileStats
    recent_uploads: List[FileResponse]
    processing_queue_length: int
    estimated_processing_time_minutes: float


class FileShareRequest(BaseSchema):
    """File sharing request schema"""
    is_public: bool = Field(False, description="Make file publicly accessible")
    expiry_hours: Optional[int] = Field(None, ge=1, le=8760, description="Share link expiry")
    password_protected: bool = Field(False, description="Require password")
    download_limit: Optional[int] = Field(None, ge=1, le=1000, description="Download limit")


class FileShareResponse(BaseResponse):
    """File sharing response schema"""
    share_token: str
    share_url: str
    expires_at: Optional[datetime] = None
    password: Optional[str] = None  # Generated password if protected
    download_limit: Optional[int] = None 