"""Conversation model for chat sessions"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, JSON, ForeignKey, and_, cast
from sqlalchemy.orm import relationship, foreign
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Conversation(Base):
    __tablename__ = "conversations"
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    # User relationship
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Conversation metadata
    title = Column(String(500), nullable=True)  # Auto-generated or user-set
    description = Column(Text, nullable=True)
    status = Column(String(50), default="active")  # active, archived, deleted
    
    # AI model settings (can override user defaults)
    model_name = Column(String(100), nullable=True)
    temperature = Column(Float, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    system_prompt = Column(Text, nullable=True)
    
    # Memory and context settings
    memory_enabled = Column(Boolean, default=True)
    context_window_size = Column(Integer, default=10)  # Number of recent messages to include
    auto_title_generation = Column(Boolean, default=True)
    
    # Analytics and tracking
    message_count = Column(Integer, default=0)
    total_tokens_used = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)
    
    # Session information
    is_pinned = Column(Boolean, default=False)
    is_shared = Column(Boolean, default=False)
    share_token = Column(String(100), nullable=True, unique=True)
    
    # Conversation topics/tags for organization
    topics = Column(JSON, default=list)  # ["programming", "python", "debugging"]
    tags = Column(JSON, default=list)    # ["work", "important", "learning"]
    
    # Quality metrics
    user_rating = Column(Float, nullable=True)  # 1-5 stars
    quality_score = Column(Float, nullable=True)  # Calculated quality metric
    
    # Extra metadata
    extra_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_message_at = Column(DateTime, nullable=True, index=True)
    archived_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    vector_collection = relationship("VectorCollection", 
                                   primaryjoin="and_(foreign(VectorCollection.scope) == 'conversation', foreign(VectorCollection.scope_id) == cast(Conversation.id, String))",
                                   viewonly=True, uselist=False)
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, title='{self.title}', messages={self.message_count})>"
    
    @property
    def average_cost_per_message(self) -> float:
        """Calculate average cost per message"""
        if self.message_count <= 0:
            return 0.0
        return self.total_cost_usd / self.message_count
    
    @property
    def is_recent(self) -> bool:
        """Check if conversation has recent activity (last 24 hours)"""
        if not self.last_message_at:
            return False
        from datetime import datetime, timedelta
        return self.last_message_at > (datetime.utcnow() - timedelta(hours=24))
    
    def generate_share_token(self) -> str:
        """Generate a unique share token for public sharing"""
        if not self.share_token:
            self.share_token = str(uuid.uuid4())
        return self.share_token
    
    def add_topic(self, topic: str):
        """Add a topic to the conversation"""
        if not self.topics:
            self.topics = []
        if topic not in self.topics:
            self.topics.append(topic)
    
    def add_tag(self, tag: str):
        """Add a tag to the conversation"""
        if not self.tags:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)
    
    def update_stats(self, tokens_used: int, cost_usd: float):
        """Update conversation statistics"""
        self.total_tokens_used += tokens_used
        self.total_cost_usd += cost_usd
        self.last_message_at = func.now() 