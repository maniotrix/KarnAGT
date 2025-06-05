"""User profile and preferences Pydantic schemas"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import Field, EmailStr, validator

from .common_schemas import BaseSchema, BaseResponse, SubscriptionTier, ModelName


class UserProfileUpdate(BaseSchema):
    """User profile update request schema"""
    full_name: Optional[str] = Field(None, max_length=255, description="User full name")
    username: Optional[str] = Field(None, min_length=3, max_length=100, description="Unique username")
    bio: Optional[str] = Field(None, max_length=500, description="User biography")
    avatar_url: Optional[str] = Field(None, max_length=500, description="Avatar image URL")
    timezone: Optional[str] = Field(None, max_length=50, description="User timezone")
    language: Optional[str] = Field(None, max_length=10, description="Preferred language")
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format"""
        if v is not None:
            import re
            if not re.match(r'^[a-zA-Z0-9_-]+$', v):
                raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v


class UserPreferences(BaseSchema):
    """User AI preferences schema"""
    preferred_model: ModelName = Field(ModelName.GPT_4O_MINI, description="Preferred AI model")
    preferred_temperature: float = Field(0.7, ge=0.0, le=2.0, description="Response creativity (0.0-2.0)")
    preferred_max_tokens: int = Field(4000, ge=100, le=8000, description="Maximum response length")
    memory_enabled: bool = Field(True, description="Enable conversation memory")
    memory_retention_days: int = Field(365, ge=1, le=3650, description="Memory retention period")
    auto_memory_importance: bool = Field(True, description="Auto-calculate memory importance")
    data_retention_enabled: bool = Field(True, description="Enable data retention")
    analytics_enabled: bool = Field(True, description="Enable usage analytics")


class UserPreferencesUpdate(BaseSchema):
    """User preferences update request schema"""
    preferred_model: Optional[ModelName] = Field(None, description="Preferred AI model")
    preferred_temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Response creativity")
    preferred_max_tokens: Optional[int] = Field(None, ge=100, le=8000, description="Maximum response length")
    memory_enabled: Optional[bool] = Field(None, description="Enable conversation memory")
    memory_retention_days: Optional[int] = Field(None, ge=1, le=3650, description="Memory retention period")
    auto_memory_importance: Optional[bool] = Field(None, description="Auto-calculate memory importance")
    data_retention_enabled: Optional[bool] = Field(None, description="Enable data retention")
    analytics_enabled: Optional[bool] = Field(None, description="Enable usage analytics")


class UserQuotaInfo(BaseSchema):
    """User quota information schema"""
    subscription_tier: SubscriptionTier
    monthly_quota_usd: float = Field(ge=0, description="Monthly spending limit in USD")
    current_usage_usd: float = Field(ge=0, description="Current month usage in USD")
    quota_reset_date: datetime = Field(description="Date when quota resets")
    usage_percentage: float = Field(ge=0, le=100, description="Percentage of quota used")
    is_quota_exceeded: bool = Field(description="Whether quota is exceeded")
    days_until_reset: int = Field(ge=0, description="Days until quota reset")


class UserQuotaUpdate(BaseSchema):
    """User quota update request schema (admin only)"""
    monthly_quota_usd: float = Field(ge=0, description="New monthly spending limit")
    subscription_tier: Optional[SubscriptionTier] = Field(None, description="New subscription tier")


class UserStats(BaseSchema):
    """User statistics schema"""
    total_conversations: int = Field(ge=0, description="Total number of conversations")
    total_messages: int = Field(ge=0, description="Total number of messages")
    total_tokens_used: int = Field(ge=0, description="Total tokens consumed")
    total_cost_usd: float = Field(ge=0, description="Total cost in USD")
    average_conversation_length: float = Field(ge=0, description="Average messages per conversation")
    favorite_model: Optional[str] = Field(None, description="Most used AI model")
    account_age_days: int = Field(ge=0, description="Account age in days")
    last_active_days_ago: int = Field(ge=0, description="Days since last activity")


class UserActivity(BaseSchema):
    """User activity schema"""
    date: datetime
    conversations_created: int = Field(ge=0)
    messages_sent: int = Field(ge=0)
    tokens_used: int = Field(ge=0)
    cost_usd: float = Field(ge=0)


class UserActivityHistory(BaseResponse):
    """User activity history response schema"""
    activities: List[UserActivity]
    total_days: int
    summary: UserStats


class UserProfileResponse(BaseResponse):
    """Complete user profile response schema"""
    profile: "UserProfile"
    preferences: UserPreferences
    quota_info: UserQuotaInfo
    stats: UserStats


class UserFeatureAccess(BaseSchema):
    """User feature access schema"""
    basic_chat: bool
    memory_management: bool
    file_upload: bool
    advanced_tools: bool
    api_access: bool
    priority_support: bool
    custom_models: bool
    higher_quotas: bool


class UserAccountSettings(BaseSchema):
    """User account settings schema"""
    email_notifications: bool = Field(True, description="Enable email notifications")
    push_notifications: bool = Field(True, description="Enable push notifications")
    marketing_emails: bool = Field(False, description="Enable marketing emails")
    data_export_enabled: bool = Field(True, description="Allow data export")
    account_deletion_enabled: bool = Field(True, description="Allow account deletion")
    two_factor_enabled: bool = Field(False, description="Enable 2FA")


class UserAccountSettingsUpdate(BaseSchema):
    """User account settings update schema"""
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    marketing_emails: Optional[bool] = None
    data_export_enabled: Optional[bool] = None
    account_deletion_enabled: Optional[bool] = None


class UserDataExportRequest(BaseSchema):
    """User data export request schema"""
    include_conversations: bool = Field(True, description="Include conversation data")
    include_files: bool = Field(True, description="Include uploaded files")
    include_analytics: bool = Field(False, description="Include usage analytics")
    format: str = Field("json", description="Export format (json, csv)")


class UserDataExportResponse(BaseResponse):
    """User data export response schema"""
    export_id: str
    status: str
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    file_size_mb: Optional[float] = None


class UserDeletionRequest(BaseSchema):
    """User account deletion request schema"""
    password: str = Field(..., description="User password for confirmation")
    reason: Optional[str] = Field(None, max_length=500, description="Deletion reason")
    feedback: Optional[str] = Field(None, max_length=1000, description="User feedback")


# Import for forward reference
from .auth_schemas import UserProfile 