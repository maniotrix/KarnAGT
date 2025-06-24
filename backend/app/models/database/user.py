"""User model for authentication and account management"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    # Authentication
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Profile information
    full_name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    
    # Subscription and limits
    subscription_tier = Column(String(50), default="free")  # free, pro, enterprise
    monthly_quota_usd = Column(Float, default=10.0)
    current_usage_usd = Column(Float, default=0.0)
    quota_reset_date = Column(DateTime, default=func.now())
    
    # User preferences
    preferred_model = Column(String(100), default="gpt-4o-mini")
    preferred_temperature = Column(Float, default=0.7)
    preferred_max_tokens = Column(Integer, default=4000)
    timezone = Column(String(50), default="UTC")
    language = Column(String(10), default="en")
    
    # Memory settings
    memory_enabled = Column(Boolean, default=True)
    memory_retention_days = Column(Integer, default=365)
    auto_memory_importance = Column(Boolean, default=True)
    
    # Privacy settings
    data_retention_enabled = Column(Boolean, default=True)
    analytics_enabled = Column(Boolean, default=True)
    
    # Extra metadata
    extra_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    memory_preferences = relationship("MemoryPreference", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("UserMemory", back_populates="user", cascade="all, delete-orphan")
    knowledge_files = relationship("KnowledgeFile", back_populates="user", cascade="all, delete-orphan")
    cost_tracking = relationship("CostTracking", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', subscription='{self.subscription_tier}')>"
    
    @property
    def is_quota_exceeded(self) -> bool:
        """Check if user has exceeded their monthly quota"""
        return self.current_usage_usd >= self.monthly_quota_usd
    
    @property
    def quota_usage_percentage(self) -> float:
        """Get quota usage as percentage"""
        if self.monthly_quota_usd <= 0:
            return 0.0
        return min((self.current_usage_usd / self.monthly_quota_usd) * 100, 100.0)
    
    def can_use_feature(self, feature: str) -> bool:
        """Check if user can access a feature based on subscription tier"""
        feature_tiers = {
            "basic_chat": ["free", "pro", "enterprise"],
            "memory_management": ["free", "pro", "enterprise"],  # Allow free users
            "file_upload": ["free", "pro", "enterprise"],  # Allow free users
            "advanced_tools": ["enterprise"],
            "api_access": ["enterprise"],
            "priority_support": ["pro", "enterprise"],
        }
        return self.subscription_tier in feature_tiers.get(feature, []) 