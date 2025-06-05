"""Message model for individual chat messages"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Message(Base):
    __tablename__ = "messages"
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    message_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    # Relationships
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    
    # Message content
    role = Column(String(20), nullable=False, index=True)  # user, assistant, system, tool
    content = Column(Text, nullable=False)
    original_content = Column(Text, nullable=True)  # Before any processing/filtering
    
    # Message type and format
    message_type = Column(String(50), default="text")  # text, image, file, tool_call, tool_result
    content_format = Column(String(20), default="markdown")  # markdown, plain, html
    
    # AI model information
    model_name = Column(String(100), nullable=True)
    model_temperature = Column(Float, nullable=True)
    
    # Token and cost tracking
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    
    # Message quality and feedback
    user_rating = Column(Float, nullable=True)  # 1-5 stars
    quality_score = Column(Float, nullable=True)  # Calculated quality metric
    is_flagged = Column(Boolean, default=False)
    flag_reason = Column(String(100), nullable=True)
    
    # Processing metadata
    processing_time_ms = Column(Float, nullable=True)
    is_streaming = Column(Boolean, default=False)
    stream_completed = Column(Boolean, default=True)
    
    # Tool usage (for function calls)
    tool_calls = Column(JSON, nullable=True)  # Function calls made
    tool_results = Column(JSON, nullable=True)  # Results from tools
    
    # Memory and importance
    importance_score = Column(Float, default=0.5)  # 0.0-1.0
    memory_stored = Column(Boolean, default=False)
    memory_id = Column(String(100), nullable=True)  # Reference to memory system
    
    # Attachments and references
    attachments = Column(JSON, default=list)  # File attachments
    references = Column(JSON, default=list)   # References to knowledge base
    
    # Message status
    status = Column(String(50), default="completed")  # pending, streaming, completed, error, cancelled
    error_message = Column(Text, nullable=True)
    
    # Edit history
    is_edited = Column(Boolean, default=False)
    edit_count = Column(Integer, default=0)
    parent_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    
    # Extra metadata
    extra_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    parent_message = relationship("Message", remote_side=[id], backref="child_messages")
    
    def __repr__(self):
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message(id={self.id}, role='{self.role}', content='{content_preview}')>"
    
    @property
    def cost_per_token(self) -> float:
        """Calculate cost per token"""
        if self.total_tokens <= 0:
            return 0.0
        return self.cost_usd / self.total_tokens
    
    @property
    def is_user_message(self) -> bool:
        """Check if message is from user"""
        return self.role == "user"
    
    @property
    def is_assistant_message(self) -> bool:
        """Check if message is from assistant"""
        return self.role == "assistant"
    
    @property
    def is_system_message(self) -> bool:
        """Check if message is a system message"""
        return self.role == "system"
    
    @property
    def is_tool_message(self) -> bool:
        """Check if message involves tool usage"""
        return self.role in ["tool", "tool_call", "tool_result"]
    
    @property
    def word_count(self) -> int:
        """Get approximate word count of the message"""
        return len(self.content.split()) if self.content else 0
    
    @property
    def character_count(self) -> int:
        """Get character count of the message"""
        return len(self.content) if self.content else 0
    
    def add_attachment(self, attachment_data: dict):
        """Add an attachment to the message"""
        if not self.attachments:
            self.attachments = []
        self.attachments.append(attachment_data)
    
    def add_reference(self, reference_data: dict):
        """Add a knowledge base reference"""
        if not self.references:
            self.references = []
        self.references.append(reference_data)
    
    def set_tool_call(self, tool_name: str, tool_args: dict, tool_id: str = None):
        """Set tool call information"""
        if not self.tool_calls:
            self.tool_calls = []
        tool_call = {
            "id": tool_id or str(uuid.uuid4()),
            "name": tool_name,
            "arguments": tool_args,
            "timestamp": func.now().isoformat()
        }
        self.tool_calls.append(tool_call)
    
    def set_tool_result(self, tool_id: str, result: dict):
        """Set tool execution result"""
        if not self.tool_results:
            self.tool_results = []
        tool_result = {
            "tool_id": tool_id,
            "result": result,
            "timestamp": func.now().isoformat()
        }
        self.tool_results.append(tool_result)
    
    def update_tokens_and_cost(self, prompt_tokens: int, completion_tokens: int, cost_usd: float):
        """Update token usage and cost"""
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens
        self.cost_usd = cost_usd 