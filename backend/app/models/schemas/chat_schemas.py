"""Chat and conversation Pydantic schemas"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import Field, validator, model_validator

from .common_schemas import (
    BaseSchema, 
    BaseResponse, 
    PaginatedResponse,
    ConversationStatus, 
    MessageRole, 
    ModelName,
    SearchParams
)
from app.models.schemas.staging_schemas import StagingFileCollection


class ConversationCreate(BaseSchema):
    """Create conversation request schema"""
    title: Optional[str] = Field(None, max_length=500, description="Conversation title")
    description: Optional[str] = Field(None, max_length=1000, description="Conversation description")
    model_name: Optional[ModelName] = Field(None, description="AI model to use")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Response creativity")
    max_tokens: Optional[int] = Field(None, ge=100, le=8000, description="Max response length")
    system_prompt: Optional[str] = Field(None, max_length=2000, description="System prompt")
    memory_enabled: Optional[bool] = Field(None, description="Enable memory for this conversation")
    auto_title_generation: Optional[bool] = Field(None, description="Auto-generate title")
    tags: Optional[List[str]] = Field(None, description="Conversation tags")


class ConversationUpdate(BaseSchema):
    """Update conversation request schema"""
    title: Optional[str] = Field(None, max_length=500, description="Conversation title")
    description: Optional[str] = Field(None, max_length=1000, description="Conversation description")
    model_name: Optional[ModelName] = Field(None, description="AI model to use")
    status: Optional[ConversationStatus] = Field(None, description="Conversation status")
    is_pinned: Optional[bool] = Field(None, description="Pin conversation")
    tags: Optional[List[str]] = Field(None, description="Conversation tags")
    user_rating: Optional[float] = Field(None, ge=1.0, le=5.0, description="User rating (1-5 stars)")


class ConversationResponse(BaseSchema):
    """Conversation response schema"""
    id: int
    conversation_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    status: ConversationStatus
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    memory_enabled: bool
    message_count: int
    total_tokens_used: int
    total_cost_usd: float
    is_pinned: bool
    is_shared: bool
    topics: List[str] = []
    tags: List[str] = []
    user_rating: Optional[float] = None
    quality_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ConversationListResponse(PaginatedResponse[ConversationResponse]):
    """Paginated conversation list response"""
    pass


class ConversationDetailResponse(BaseResponse):
    """Detailed conversation response with messages"""
    conversation: ConversationResponse
    recent_messages: List["MessageResponse"]
    message_count: int
    can_continue: bool


class MessageCreate(BaseSchema):
    """Create message request schema"""
    content: str = Field(..., max_length=32000, description="Message content")
    role: MessageRole = Field(MessageRole.USER, description="Message role")
    parent_message_id: Optional[int] = Field(None, description="Parent message for threading")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="File attachments")
    vector_file_references: Optional[Dict[str, Any]] = Field(None, description="References to knowledge files processed for RAG")
    
    # Status field (for internal use)
    status: Optional[str] = Field("completed", description="Message status")
    
    # Staging files as dict (will be converted to object at API boundary)
    staging_files: Optional[Dict[str, Any]] = Field(
        None, 
        description="Staging files organized by type from StagingFileCollection.to_dict()"
    )
    
    @model_validator(mode='after')
    def validate_message_and_staging_files(self):
        """Validate message content and staging files"""
        content = getattr(self, 'content', '')
        staging_files_dict = getattr(self, 'staging_files', None)
        
        has_text = content and content.strip()
        has_files = False
        
        if staging_files_dict:
            # Convert to object for validation
            staging_collection = StagingFileCollection.from_dict(staging_files_dict)
            has_files = not staging_collection.is_empty
        
        if not has_text and not has_files:
            raise ValueError('Message must have either text content or files')
        
        return self


class MessageUpdate(BaseSchema):
    """Update message request schema"""
    content: Optional[str] = Field(None, max_length=32000, description="Message content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Message metadata")


class MessageResponse(BaseSchema):
    """Message response schema"""
    id: int
    message_id: str
    conversation_id: int  # Changed to int to match database foreign key
    role: MessageRole
    content: str
    total_tokens: int  # Changed from tokens_used to match database field
    cost_usd: float
    model_name: Optional[str] = None  # Changed from model_used to match database field
    finish_reason: Optional[str] = None
    parent_message_id: Optional[int] = None
    has_children: bool = False
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="Message attachments")
    vector_file_references: Optional[Dict[str, Any]] = Field(None, description="References to knowledge files processed for RAG")
    extra_metadata: Dict[str, Any] = {}  # Changed from metadata to match database field
    created_at: datetime
    
    class Config:
        from_attributes = True


class MessageStreamResponse(BaseSchema):
    """Streaming message response schema (for SSE, not DB storage)"""
    message_id: str
    conversation_id: str
    content: str
    role: MessageRole
    tokens_used: int
    cost_usd: float
    model_used: str
    finish_reason: Optional[str] = None
    metadata: Dict[str, Any] = {}
    created_at: datetime


class MessageListResponse(PaginatedResponse[MessageResponse]):
    """Paginated message list response"""
    pass


class ChatStreamRequest(BaseSchema):
    """Chat streaming request schema"""
    message: str = Field(..., min_length=1, max_length=32000, description="User message")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")
    model: Optional[ModelName] = Field(None, description="AI model to use")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Response creativity")
    max_tokens: Optional[int] = Field(None, ge=100, le=8000, description="Max response length")
    system_prompt: Optional[str] = Field(None, max_length=2000, description="System prompt")
    memory_enabled: Optional[bool] = Field(None, description="Use conversation memory")
    include_context: bool = Field(True, description="Include conversation context")
    stream: bool = Field(True, description="Stream response")


class ChatStreamChunk(BaseSchema):
    """Individual streaming response chunk"""
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[Dict[str, Any]]


class ChatStreamResponse(BaseSchema):
    """Complete streaming response"""
    conversation_id: str
    message_id: str
    content: str
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    finish_reason: str
    model_used: str
    created_at: datetime


class ConversationShareRequest(BaseSchema):
    """Share conversation request schema"""
    is_public: bool = Field(True, description="Make conversation public")
    allow_comments: bool = Field(False, description="Allow public comments")
    expiry_hours: Optional[int] = Field(None, ge=1, le=8760, description="Link expiry in hours")


class ConversationShareResponse(BaseResponse):
    """Share conversation response schema"""
    share_token: str
    share_url: str
    is_public: bool
    expires_at: Optional[datetime] = None


class ConversationSearchRequest(SearchParams):
    """Search conversations request schema"""
    status: Optional[ConversationStatus] = Field(None, description="Filter by status")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    model_name: Optional[str] = Field(None, description="Filter by AI model")
    date_from: Optional[datetime] = Field(None, description="Filter from date")
    date_to: Optional[datetime] = Field(None, description="Filter to date")
    min_rating: Optional[float] = Field(None, ge=1.0, le=5.0, description="Minimum rating")
    has_files: Optional[bool] = Field(None, description="Has file attachments")


class ConversationBulkAction(BaseSchema):
    """Bulk action on conversations"""
    conversation_ids: List[str] = Field(..., min_length=1, max_length=100, description="Conversation IDs")
    action: str = Field(..., description="Action to perform")
    
    @validator('action')  
    def validate_action(cls, v):
        valid_actions = ['delete', 'archive', 'unarchive', 'pin', 'unpin', 'export']
        if v not in valid_actions:
            raise ValueError(f'Action must be one of: {valid_actions}')
        return v


class ConversationBulkResponse(BaseResponse):
    """Bulk action response"""
    processed_count: int
    successful_ids: List[str]
    failed_ids: List[str]
    errors: Dict[str, str] = {}


class ConversationExportRequest(BaseSchema):
    """Export conversation request"""
    conversation_ids: Optional[List[str]] = Field(None, description="Specific conversation IDs")
    format: str = Field("json", description="Export format")
    include_metadata: bool = Field(True, description="Include metadata")
    include_attachments: bool = Field(False, description="Include file attachments")
    
    @validator('format')
    def validate_format(cls, v):
        valid_formats = ['json', 'markdown', 'pdf', 'txt']
        if v not in valid_formats:
            raise ValueError(f'Format must be one of: {valid_formats}')
        return v


class ConversationStats(BaseSchema):
    """Conversation statistics"""
    total_conversations: int
    active_conversations: int
    archived_conversations: int
    total_messages: int
    total_tokens: int
    total_cost_usd: float
    average_messages_per_conversation: float
    most_used_model: Optional[str] = None
    favorite_topics: List[str] = []


class ConversationAnalytics(BaseResponse):
    """Conversation analytics response"""
    stats: ConversationStats
    daily_activity: List[Dict[str, Union[str, int, float]]]
    model_usage: Dict[str, int]
    topic_distribution: Dict[str, int]


# Forward reference imports
MessageResponse.model_rebuild()
ConversationDetailResponse.model_rebuild() 