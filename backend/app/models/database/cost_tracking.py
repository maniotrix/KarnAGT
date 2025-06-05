"""Cost tracking model for API usage and billing"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class CostTracking(Base):
    __tablename__ = "cost_tracking"
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tracking_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    # User relationship
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Request identification
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True, index=True)
    request_id = Column(String(100), nullable=True, index=True)  # External request ID
    
    # Service and operation details
    service_name = Column(String(100), nullable=False, index=True)  # openai, qdrant, graphiti, etc.
    operation_type = Column(String(100), nullable=False)  # chat_completion, embedding, search, etc.
    model_name = Column(String(100), nullable=True)
    
    # Usage metrics
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    # Cost breakdown
    input_cost_usd = Column(Float, default=0.0)
    output_cost_usd = Column(Float, default=0.0)
    total_cost_usd = Column(Float, default=0.0)
    
    # Pricing information
    input_price_per_token = Column(Float, nullable=True)
    output_price_per_token = Column(Float, nullable=True)
    pricing_model = Column(String(50), default="token_based")  # token_based, request_based, time_based
    
    # Performance metrics
    processing_time_ms = Column(Float, nullable=True)
    queue_time_ms = Column(Float, nullable=True)
    total_duration_ms = Column(Float, nullable=True)
    
    # Request details
    request_size_bytes = Column(Integer, nullable=True)
    response_size_bytes = Column(Integer, nullable=True)
    is_cached = Column(Boolean, default=False)
    cache_hit = Column(Boolean, default=False)
    
    # Quality and status
    status = Column(String(50), default="completed")  # pending, completed, failed, cancelled
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    quality_score = Column(Float, nullable=True)  # 0.0-1.0
    
    # Billing and quota management
    billing_period = Column(String(20), nullable=False, index=True)  # daily, weekly, monthly
    quota_type = Column(String(50), default="monthly")
    is_billable = Column(Boolean, default=True)
    is_over_quota = Column(Boolean, default=False)
    
    # Feature and usage categorization
    feature_category = Column(String(100), nullable=True)  # chat, memory, search, file_processing
    usage_tier = Column(String(50), nullable=True)  # free, pro, enterprise
    is_premium_feature = Column(Boolean, default=False)
    
    # Geographic and client information
    region = Column(String(50), nullable=True)
    client_ip = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Aggregation helpers
    hourly_bucket = Column(DateTime, nullable=True, index=True)  # Rounded to hour for aggregation
    daily_bucket = Column(DateTime, nullable=True, index=True)   # Rounded to day for aggregation
    weekly_bucket = Column(DateTime, nullable=True, index=True)  # Rounded to week for aggregation
    monthly_bucket = Column(DateTime, nullable=True, index=True) # Rounded to month for aggregation
    
    # Extra metadata and audit
    extra_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="cost_tracking")
    conversation = relationship("Conversation")
    message = relationship("Message")
    
    def __repr__(self):
        return f"<CostTracking(id={self.id}, service='{self.service_name}', cost=${self.total_cost_usd:.4f})>"
    
    @property
    def cost_per_token(self) -> float:
        """Calculate cost per token"""
        if self.total_tokens <= 0:
            return 0.0
        return self.total_cost_usd / self.total_tokens
    
    @property
    def efficiency_score(self) -> float:
        """Calculate efficiency score based on cost and quality"""
        if self.total_cost_usd <= 0:
            return 1.0
        quality = self.quality_score or 0.5
        # Higher quality per dollar = better efficiency
        return quality / max(self.total_cost_usd, 0.001)
    
    @property
    def is_expensive(self) -> bool:
        """Check if this operation was expensive (top 10% of costs)"""
        # This would typically be calculated against user's historical data
        return self.total_cost_usd > 0.10  # Placeholder threshold
    
    @property
    def is_recent(self) -> bool:
        """Check if tracking record is from last 24 hours"""
        from datetime import datetime, timedelta
        return self.created_at > (datetime.utcnow() - timedelta(hours=24))
    
    @property
    def duration_seconds(self) -> float:
        """Get total duration in seconds"""
        if not self.total_duration_ms:
            return 0.0
        return self.total_duration_ms / 1000.0
    
    def set_billing_buckets(self):
        """Set time buckets for aggregation queries"""
        from datetime import datetime
        created = self.created_at or datetime.utcnow()
        
        # Round to hour
        self.hourly_bucket = created.replace(minute=0, second=0, microsecond=0)
        
        # Round to day
        self.daily_bucket = created.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Round to week (Monday as start of week)
        from datetime import timedelta
        days_since_monday = created.weekday()
        week_start = created.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = week_start - timedelta(days=days_since_monday)
        self.weekly_bucket = week_start
        
        # Round to month
        self.monthly_bucket = created.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    def calculate_cost(self, input_price: float = None, output_price: float = None):
        """Calculate costs based on token usage and pricing"""
        if input_price is not None:
            self.input_price_per_token = input_price
            self.input_cost_usd = self.input_tokens * input_price
        
        if output_price is not None:
            self.output_price_per_token = output_price
            self.output_cost_usd = self.output_tokens * output_price
        
        self.total_cost_usd = self.input_cost_usd + self.output_cost_usd
    
    def set_tokens(self, input_tokens: int, output_tokens: int):
        """Set token usage"""
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = input_tokens + output_tokens
    
    def set_timing(self, processing_time_ms: float, queue_time_ms: float = None):
        """Set timing information"""
        self.processing_time_ms = processing_time_ms
        if queue_time_ms is not None:
            self.queue_time_ms = queue_time_ms
            self.total_duration_ms = processing_time_ms + queue_time_ms
        else:
            self.total_duration_ms = processing_time_ms
    
    def set_error(self, error_code: str, error_message: str):
        """Set error information"""
        self.status = "failed"
        self.error_code = error_code
        self.error_message = error_message
        self.is_billable = False  # Don't bill for failed requests
    
    def mark_as_cached(self, cache_hit: bool = True):
        """Mark request as using cache"""
        self.is_cached = True
        self.cache_hit = cache_hit
        if cache_hit:
            # Cached responses are typically free or very low cost
            self.total_cost_usd = 0.0
            self.input_cost_usd = 0.0
            self.output_cost_usd = 0.0
    
    @classmethod
    def create_tracking_record(
        cls,
        user_id: int,
        service_name: str,
        operation_type: str,
        model_name: str = None,
        conversation_id: int = None,
        message_id: int = None,
    ):
        """Factory method to create a new tracking record"""
        record = cls(
            user_id=user_id,
            service_name=service_name,
            operation_type=operation_type,
            model_name=model_name,
            conversation_id=conversation_id,
            message_id=message_id,
        )
        record.set_billing_buckets()
        return record 