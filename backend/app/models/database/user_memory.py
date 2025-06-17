"""User Memory model for storing user-specific memories across 6 buckets"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from typing import Optional
import uuid

from app.core.database import Base


class UserMemory(Base):
    __tablename__ = "user_memories"
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    memory_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    # User relationship
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Memory categorization (6-bucket system)
    bucket = Column(String(50), nullable=False, index=True)  # identity, preferences, goals, workflows, capabilities, social
    memory_type = Column(String(50), nullable=False)  # fact, preference, goal, workflow, capability, contact
    
    # Core content
    content = Column(Text, nullable=False)
    structured_data = Column(JSON, default=dict)  # For complex/structured memory data
    
    # Scoring and confidence
    importance = Column(Float, default=0.5, index=True)  # 0.0-1.0 importance score
    confidence = Column(Float, default=1.0)  # How confident we are in this memory
    
    # Lifecycle management
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_accessed = Column(DateTime, server_default=func.now(), index=True)
    expires_at = Column(DateTime, nullable=True, index=True)  # NULL = permanent
    
    # Status and metadata
    is_active = Column(Boolean, default=True, index=True)
    is_archived = Column(Boolean, default=False)
    
    # Bucket-specific fields
    status = Column(String(50), nullable=True)  # For goals: "active", "completed", "paused"
    last_activity = Column(DateTime, nullable=True)  # For workflows/habits tracking
    relationship_strength = Column(String(20), nullable=True)  # For social: "close", "professional", "casual"
    
    # Source tracking
    source_conversation_id = Column(String(36), nullable=True, index=True)
    source_message_id = Column(String(36), nullable=True)
    extraction_method = Column(String(50), default="auto")  # "auto", "manual", "inferred"
    
    # Usage analytics
    access_count = Column(Integer, default=0)
    last_updated_by = Column(String(50), default="system")  # "system", "user", "ai"
    
    # Relationships
    user = relationship("User", back_populates="memories")
    
    def __repr__(self):
        return f"<UserMemory(id={self.id}, bucket='{self.bucket}', type='{self.memory_type}', importance={self.importance})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if memory has expired based on expires_at"""
        if not self.expires_at:
            return False  # Permanent memories don't expire
        return datetime.utcnow() > self.expires_at
    
    @property
    def age_in_days(self) -> int:
        """Get age of memory in days"""
        return (datetime.utcnow() - self.created_at).days
    
    @property
    def days_since_last_access(self) -> int:
        """Get days since last access"""
        return (datetime.utcnow() - self.last_accessed).days
    
    def calculate_decay_factor(self, decay_rate: float = 0.1) -> float:
        """Calculate importance decay factor based on age and access patterns"""
        age_factor = max(0.1, 1.0 - (decay_rate * self.age_in_days / 30))
        access_factor = max(0.5, 1.0 - (self.days_since_last_access / 90))
        return age_factor * access_factor
    
    def update_access(self):
        """Update access tracking"""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1
    
    def set_expiration_by_bucket(self):
        """Set expiration date based on bucket type"""
        bucket_ttl_days = {
            "identity": None,      # Permanent
            "preferences": None,   # Permanent  
            "goals": 730,         # 2 years
            "workflows": 120,     # 4 months
            "capabilities": 365,  # 1 year
            "social": 180         # 6 months
        }
        
        ttl_days = bucket_ttl_days.get(self.bucket)
        if ttl_days:
            self.expires_at = datetime.utcnow() + timedelta(days=ttl_days)
        else:
            self.expires_at = None  # Permanent
    
    def is_bucket_type(self, bucket: str) -> bool:
        """Check if memory belongs to specific bucket"""
        return self.bucket == bucket
    
    def has_high_importance(self, threshold: float = 0.7) -> bool:
        """Check if memory has high importance"""
        return self.importance >= threshold
    
    def is_recently_accessed(self, days: int = 7) -> bool:
        """Check if memory was accessed recently"""
        return self.days_since_last_access <= days
    
    def get_memory_summary(self) -> dict:
        """Get a summary of memory for API responses"""
        return {
            "memory_id": self.memory_id,
            "bucket": self.bucket,
            "memory_type": self.memory_type,
            "content": self.content,
            "importance": self.importance,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "status": self.status,
            "access_count": self.access_count
        }


# Memory bucket constants for validation
MEMORY_BUCKETS = {
    "identity": {
        "description": "Name, pronouns, timezone, bio, device info",
        "ttl_days": None,  # Permanent
        "default_importance": 0.8
    },
    "preferences": {
        "description": "Communication style, tool preferences, format preferences",
        "ttl_days": None,  # Permanent until changed
        "default_importance": 0.7
    },
    "goals": {
        "description": "Projects, learning goals, objectives",
        "ttl_days": 730,  # 2 years
        "default_importance": 0.8
    },
    "workflows": {
        "description": "Daily routines, coding patterns, schedules",
        "ttl_days": 120,  # 4 months
        "default_importance": 0.6
    },
    "capabilities": {
        "description": "Hardware specs, budgets, skill levels",
        "ttl_days": 365,  # 1 year
        "default_importance": 0.7
    },
    "social": {
        "description": "Colleagues, collaborators, relationships",
        "ttl_days": 180,  # 6 months
        "default_importance": 0.5
    }
}

MEMORY_TYPES = {
    "fact": "Factual information about the user",
    "preference": "User preferences and choices", 
    "goal": "User goals and objectives",
    "workflow": "User patterns and habits",
    "capability": "User skills and constraints",
    "contact": "People and relationships"
} 