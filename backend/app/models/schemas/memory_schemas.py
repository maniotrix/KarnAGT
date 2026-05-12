"""Memory management Pydantic schemas"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import Field, validator

from .common_schemas import BaseSchema, BaseResponse, PaginatedResponse, SearchParams


class MemoryPreferencesResponse(BaseSchema):
    """Memory preferences response schema"""
    topic: str
    importance_threshold: float = Field(ge=0.0, le=1.0)
    retention_days: int = Field(ge=1, le=3650)
    auto_categorization: bool
    include_in_context: bool
    created_at: datetime
    updated_at: datetime


class MemoryPreferencesUpdate(BaseSchema):
    """Memory preferences update schema"""
    topic: str = Field(..., max_length=100, description="Memory topic")
    importance_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Importance threshold")
    retention_days: Optional[int] = Field(None, ge=1, le=3650, description="Retention period")
    auto_categorization: Optional[bool] = Field(None, description="Auto-categorize memories")
    include_in_context: Optional[bool] = Field(None, description="Include in conversation context")


class MemorySearchRequest(SearchParams):
    """Memory search request schema"""
    topics: Optional[List[str]] = Field(None, description="Filter by topics")
    min_importance: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum importance")
    date_from: Optional[datetime] = Field(None, description="From date")
    date_to: Optional[datetime] = Field(None, description="To date")
    conversation_id: Optional[str] = Field(None, description="From specific conversation")
    memory_type: Optional[str] = Field(None, description="Memory type filter")


class MemoryItem(BaseSchema):
    """Individual memory item schema"""
    id: str
    content: str
    topic: str
    importance_score: float = Field(ge=0.0, le=1.0)
    memory_type: str
    conversation_id: Optional[str] = None
    created_at: datetime
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    metadata: Dict[str, Any] = {}


class MemorySearchResponse(PaginatedResponse[MemoryItem]):
    """Memory search response schema"""
    pass


class MemoryInsight(BaseSchema):
    """Memory insights schema"""
    total_memories: int
    active_topics: List[str]
    top_memories: List[MemoryItem]
    memory_trends: Dict[str, Any]
    recommendation: str


class MemoryClearRequest(BaseSchema):
    """Clear memories request schema"""
    topics: Optional[List[str]] = Field(None, description="Clear specific topics")
    older_than_days: Optional[int] = Field(None, ge=1, description="Clear memories older than X days")
    importance_below: Optional[float] = Field(None, ge=0.0, le=1.0, description="Clear below importance")
    confirm: bool = Field(False, description="Confirmation required")


class MemoryClearResponse(BaseResponse):
    """Clear memories response schema"""
    cleared_count: int
    topics_affected: List[str]
    space_freed_mb: float 