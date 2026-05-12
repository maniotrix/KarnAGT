"""Analytics and cost tracking Pydantic schemas"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from pydantic import Field

from .common_schemas import BaseSchema, BaseResponse, SubscriptionTier, ModelName


class UsageMetrics(BaseSchema):
    """Usage metrics schema"""
    date: date
    total_requests: int = 0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost_usd: float = 0.0
    unique_conversations: int = 0
    average_response_time_ms: float = 0.0
    error_count: int = 0
    error_rate_percentage: float = 0.0


class ModelUsageBreakdown(BaseSchema):
    """Model usage breakdown schema"""
    model_name: str
    request_count: int
    token_count: int
    cost_usd: float
    average_tokens_per_request: float
    percentage_of_total_usage: float


class CostBreakdown(BaseSchema):
    """Cost breakdown schema"""
    total_cost_usd: float
    prompt_cost_usd: float
    completion_cost_usd: float
    model_breakdown: List[ModelUsageBreakdown]
    daily_costs: List[Dict[str, Union[str, float]]]
    period_start: date
    period_end: date


class QuotaStatus(BaseSchema):
    """Quota status schema"""
    subscription_tier: SubscriptionTier
    monthly_limit_usd: float
    current_usage_usd: float
    remaining_usd: float
    usage_percentage: float = Field(ge=0.0, le=100.0)
    days_remaining: int
    projected_usage_usd: float
    is_over_quota: bool
    quota_reset_date: date
    last_updated: datetime


class UsageAnalytics(BaseResponse):
    """Usage analytics response schema"""
    current_period: UsageMetrics
    previous_period: UsageMetrics
    growth_percentage: float
    cost_breakdown: CostBreakdown
    quota_status: QuotaStatus
    top_models: List[ModelUsageBreakdown]
    daily_usage: List[UsageMetrics]


class UserActivityInsight(BaseSchema):
    """User activity insight schema"""
    most_active_hour: int = Field(ge=0, le=23)
    most_active_day: str
    average_session_length_minutes: float
    preferred_conversation_length: int
    conversation_completion_rate: float = Field(ge=0.0, le=1.0)
    memory_utilization_rate: float = Field(ge=0.0, le=1.0)
    file_usage_frequency: str


class ConversationQualityMetrics(BaseSchema):
    """Conversation quality metrics schema"""
    average_user_rating: float = Field(ge=1.0, le=5.0)
    completion_rate: float = Field(ge=0.0, le=1.0)
    average_conversation_length: float
    user_satisfaction_score: float = Field(ge=0.0, le=1.0)
    common_topics: List[str]
    engagement_patterns: Dict[str, Any]


class CostOptimizationInsight(BaseSchema):
    """Cost optimization insight schema"""
    potential_savings_usd: float
    model_recommendations: List[Dict[str, Any]]
    usage_patterns: List[str]
    optimization_suggestions: List[str]
    cost_efficiency_score: float = Field(ge=0.0, le=1.0)


class AnalyticsInsights(BaseResponse):
    """Analytics insights response schema"""
    user_activity: UserActivityInsight
    conversation_quality: ConversationQualityMetrics
    cost_optimization: CostOptimizationInsight
    trends: Dict[str, Any]
    recommendations: List[str]
    insight_score: float = Field(ge=0.0, le=1.0)


class SystemHealthMetrics(BaseSchema):
    """System health metrics schema"""
    total_users: int
    active_users_24h: int
    total_conversations: int
    total_messages: int
    average_response_time_ms: float
    error_rate: float = Field(ge=0.0, le=1.0)
    uptime_percentage: float = Field(ge=0.0, le=100.0)
    database_performance_score: float = Field(ge=0.0, le=1.0)


class RevenueMetrics(BaseSchema):
    """Revenue metrics schema"""
    total_revenue_usd: float
    monthly_recurring_revenue: float
    average_revenue_per_user: float
    subscription_distribution: Dict[SubscriptionTier, int]
    churn_rate: float = Field(ge=0.0, le=1.0)
    growth_rate: float


class AdminAnalytics(BaseResponse):
    """Admin analytics response schema"""
    system_health: SystemHealthMetrics
    revenue_metrics: RevenueMetrics
    user_growth: List[Dict[str, Union[str, int]]]
    cost_analysis: Dict[str, float]
    feature_usage: Dict[str, int]
    performance_trends: List[Dict[str, Any]]


class ExportAnalyticsRequest(BaseSchema):
    """Export analytics request schema"""
    date_from: date
    date_to: date
    include_user_data: bool = Field(False, description="Include individual user data")
    include_conversations: bool = Field(False, description="Include conversation details")
    include_costs: bool = Field(True, description="Include cost breakdown")
    format: str = Field("csv", description="Export format")
    
    def validate_format(cls, v):
        valid_formats = ['csv', 'json', 'excel']
        if v not in valid_formats:
            raise ValueError(f'Format must be one of: {valid_formats}')
        return v


class ExportAnalyticsResponse(BaseResponse):
    """Export analytics response schema"""
    export_id: str
    download_url: str
    file_size_mb: float
    expires_at: datetime
    format: str


class AlertThreshold(BaseSchema):
    """Alert threshold schema"""
    metric_name: str
    threshold_value: float
    comparison_operator: str = Field(description="gt, lt, eq, gte, lte")
    alert_frequency: str = Field(description="immediate, hourly, daily")
    is_active: bool = True


class AlertConfiguration(BaseSchema):
    """Alert configuration schema"""
    cost_threshold_usd: float = 100.0
    quota_usage_threshold: float = 80.0
    error_rate_threshold: float = 5.0
    response_time_threshold_ms: float = 5000.0
    custom_thresholds: List[AlertThreshold] = []


class PerformanceBenchmark(BaseSchema):
    """Performance benchmark schema"""
    metric_name: str
    current_value: float
    benchmark_value: float
    performance_score: float = Field(ge=0.0, le=1.0)
    trend: str = Field(description="improving, declining, stable")
    recommendation: Optional[str] = None 