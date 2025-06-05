"""Memory preference model for user-specific memory settings"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class MemoryPreference(Base):
    __tablename__ = "memory_preferences"
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    preference_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    # User relationship
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Topic/context specification
    topic = Column(String(200), nullable=False, index=True)  # e.g., "work", "personal", "programming"
    context_pattern = Column(String(500), nullable=True)  # Pattern matching for automatic detection
    
    # Memory behavior settings
    memory_enabled = Column(Boolean, default=True)
    importance_threshold = Column(Float, default=0.6)  # 0.0-1.0, minimum importance to store
    retention_days = Column(Integer, default=365)  # How long to keep memories
    decay_rate = Column(Float, default=0.1)  # How fast memories decay in importance
    
    # Automatic processing settings
    auto_categorization = Column(Boolean, default=True)
    auto_importance_scoring = Column(Boolean, default=True)
    auto_topic_detection = Column(Boolean, default=True)
    
    # Memory types to capture
    capture_entities = Column(Boolean, default=True)  # People, places, organizations
    capture_facts = Column(Boolean, default=True)     # Factual information
    capture_preferences = Column(Boolean, default=True)  # User likes/dislikes
    capture_goals = Column(Boolean, default=True)     # User objectives
    capture_experiences = Column(Boolean, default=True)  # Past events/experiences
    
    # Privacy and sharing settings
    is_private = Column(Boolean, default=True)
    allow_ai_learning = Column(Boolean, default=False)  # Allow AI to learn from memories
    share_with_team = Column(Boolean, default=False)   # For enterprise users
    
    # Memory retrieval settings
    max_memories_per_query = Column(Integer, default=10)
    similarity_threshold = Column(Float, default=0.7)  # For semantic search
    temporal_weight = Column(Float, default=0.3)       # How much to weight recent memories
    
    # Notification settings
    notify_on_memory_creation = Column(Boolean, default=False)
    notify_on_memory_retrieval = Column(Boolean, default=False)
    notify_on_memory_decay = Column(Boolean, default=False)
    
    # Priority and weighting
    priority = Column(Integer, default=5)  # 1-10, how important this topic is
    memory_weight = Column(Float, default=1.0)  # Multiplier for memory importance
    
    # Advanced settings
    custom_prompts = Column(JSON, default=dict)  # Custom system prompts for this topic
    blacklist_keywords = Column(JSON, default=list)  # Keywords to never store
    whitelist_keywords = Column(JSON, default=list)  # Keywords to always store
    
    # Status and metadata
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)
    
    # Extra metadata
    extra_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="memory_preferences")
    
    def __repr__(self):
        return f"<MemoryPreference(id={self.id}, topic='{self.topic}', threshold={self.importance_threshold})>"
    
    @property
    def is_default_topic(self) -> bool:
        """Check if this is a default/general topic preference"""
        return self.topic.lower() in ["default", "general", "all"]
    
    @property
    def is_expired(self) -> bool:
        """Check if preference has expired based on retention settings"""
        if not self.last_used_at:
            return False
        from datetime import datetime, timedelta
        expiry_date = self.last_used_at + timedelta(days=self.retention_days)
        return datetime.utcnow() > expiry_date
    
    def matches_context(self, text: str) -> bool:
        """Check if given text matches this preference's context pattern"""
        if not self.context_pattern:
            return False
        
        import re
        try:
            pattern = re.compile(self.context_pattern, re.IGNORECASE)
            return bool(pattern.search(text))
        except re.error:
            return False
    
    def should_store_memory(self, importance: float) -> bool:
        """Determine if a memory should be stored based on importance"""
        if not self.memory_enabled:
            return False
        return importance >= self.importance_threshold
    
    def calculate_decay_factor(self, days_old: int) -> float:
        """Calculate importance decay factor based on age"""
        return max(0.1, 1.0 - (self.decay_rate * days_old / 30))  # Decay over 30-day periods
    
    def add_blacklist_keyword(self, keyword: str):
        """Add a keyword to the blacklist"""
        if not self.blacklist_keywords:
            self.blacklist_keywords = []
        if keyword.lower() not in [k.lower() for k in self.blacklist_keywords]:
            self.blacklist_keywords.append(keyword.lower())
    
    def add_whitelist_keyword(self, keyword: str):
        """Add a keyword to the whitelist"""
        if not self.whitelist_keywords:
            self.whitelist_keywords = []
        if keyword.lower() not in [k.lower() for k in self.whitelist_keywords]:
            self.whitelist_keywords.append(keyword.lower())
    
    def contains_blacklisted_content(self, text: str) -> bool:
        """Check if text contains blacklisted keywords"""
        if not self.blacklist_keywords:
            return False
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.blacklist_keywords)
    
    def contains_whitelisted_content(self, text: str) -> bool:
        """Check if text contains whitelisted keywords"""
        if not self.whitelist_keywords:
            return False
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.whitelist_keywords)
    
    def update_usage(self):
        """Update usage statistics"""
        self.usage_count += 1
        self.last_used_at = func.now() 