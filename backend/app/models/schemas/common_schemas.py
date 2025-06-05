"""Common Pydantic schemas used across the application"""

from typing import Any, Dict, List, Optional, Union, Generic, TypeVar
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

# Generic type for paginated responses
T = TypeVar('T')


class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )


class BaseResponse(BaseSchema):
    """Base response schema"""
    success: bool = True
    message: str = "Operation completed successfully"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseSchema):
    """Error response schema"""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StatusResponse(BaseResponse):
    """Simple status response"""
    pass


class ValidationErrorDetail(BaseSchema):
    """Validation error detail"""
    field: str
    message: str
    input_value: Any


class ValidationErrorResponse(ErrorResponse):
    """Validation error response with field details"""
    validation_errors: List[ValidationErrorDetail]


# Pagination schemas
class PaginationParams(BaseSchema):
    """Pagination parameters"""
    page: int = Field(1, ge=1, description="Page number (starts from 1)")
    size: int = Field(20, ge=1, le=100, description="Number of items per page")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries"""
        return (self.page - 1) * self.size


class PaginationMeta(BaseSchema):
    """Pagination metadata"""
    page: int
    size: int
    total: int
    pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseResponse, Generic[T]):
    """Generic paginated response"""
    data: List[T]
    pagination: PaginationMeta


# Sorting and filtering
class SortOrder(str, Enum):
    """Sort order options"""
    ASC = "asc"
    DESC = "desc"


class SortParams(BaseSchema):
    """Sorting parameters"""
    sort_by: str = "created_at"
    sort_order: SortOrder = SortOrder.DESC


class DateRangeFilter(BaseSchema):
    """Date range filter"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# Search schemas
class SearchParams(BaseSchema):
    """Search parameters"""
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(10, ge=1, le=50)


class SearchResult(BaseSchema):
    """Generic search result"""
    id: Union[int, str]
    title: str
    content: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


# File handling schemas
class FileMetadata(BaseSchema):
    """File metadata"""
    size: int = Field(ge=0)
    type: str
    encoding: Optional[str] = None
    checksum: Optional[str] = None


# Common enums
class SubscriptionTier(str, Enum):
    """User subscription tiers"""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class ConversationStatus(str, Enum):
    """Conversation status options"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class MessageRole(str, Enum):
    """Message role types"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ProcessingStatus(str, Enum):
    """Processing status for async operations"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ModelName(str, Enum):
    """Available AI models"""
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_3_5_TURBO = "gpt-3.5-turbo"


# ID schemas for relationships
class IDSchema(BaseSchema):
    """Schema for ID-only responses"""
    id: int


class UUIDSchema(BaseSchema):
    """Schema for UUID-only responses"""
    id: str


# Health check schema
class HealthCheck(BaseSchema):
    """Health check response"""
    status: str = "healthy"
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: Dict[str, str] = Field(default_factory=dict)


# Batch operation schemas
class BatchRequest(BaseSchema, Generic[T]):
    """Generic batch request"""
    items: List[T] = Field(..., min_length=1, max_length=100)


class BatchResponse(BaseSchema, Generic[T]):
    """Generic batch response"""
    successful: List[T]
    failed: List[Dict[str, Any]]
    total_processed: int
    success_count: int
    failure_count: int 