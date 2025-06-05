"""
Cost Tracker for OpenAI API Usage

This module tracks token usage, costs, and provides analytics for OpenAI API calls,
integrating with the database cost tracking models.
"""

import tiktoken
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal

from app.models.database.cost_tracking import CostTracking
from app.models.database.user import User
from app.models.database.conversation import Conversation
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from aicore.logger import get_logger

# Set up logger
logger = get_logger(__name__)

# OpenAI pricing (as of 2024 - should be configurable)
PRICING_PER_1K_TOKENS = {
    "gpt-4": {
        "input": 0.03,
        "output": 0.06
    },
    "gpt-4-turbo": {
        "input": 0.01,
        "output": 0.03
    },
    "gpt-3.5-turbo": {
        "input": 0.0015,
        "output": 0.002
    },
    "text-embedding-ada-002": {
        "input": 0.0001,
        "output": 0.0001
    },
    "text-embedding-3-small": {
        "input": 0.00002,
        "output": 0.00002
    },
    "text-embedding-3-large": {
        "input": 0.00013,
        "output": 0.00013
    }
}


class CostTracker:
    """
    Tracks costs and token usage for OpenAI API calls
    
    Features:
    - Token counting with tiktoken
    - Cost calculation based on current pricing
    - Database integration for cost tracking
    - User quota management
    - Usage analytics
    """
    
    def __init__(self, user_id: str):
        """
        Initialize the cost tracker for a user
        
        Args:
            user_id: The user ID for cost tracking
        """
        self.user_id = user_id
        self.encoding = tiktoken.get_encoding("cl100k_base")  # Default encoding for GPT-4
        
        logger.info(f"CostTracker initialized for user {user_id}")
    
    def count_tokens(self, text: str, model: str = "gpt-4") -> int:
        """
        Count tokens in text using tiktoken
        
        Args:
            text: The text to count tokens for
            model: The model name for appropriate encoding
            
        Returns:
            Number of tokens
        """
        try:
            # Get appropriate encoding for model
            if model.startswith("gpt-4"):
                encoding = tiktoken.get_encoding("cl100k_base")
            elif model.startswith("gpt-3.5"):
                encoding = tiktoken.get_encoding("cl100k_base")
            else:
                encoding = self.encoding
            
            tokens = len(encoding.encode(text))
            logger.debug(f"Counted {tokens} tokens for text length {len(text)}")
            return tokens
            
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            # Fallback estimation: roughly 4 characters per token
            return len(text) // 4
    
    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "gpt-4"
    ) -> Decimal:
        """
        Calculate cost for token usage
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: The model used
            
        Returns:
            Total cost as Decimal
        """
        try:
            pricing = PRICING_PER_1K_TOKENS.get(model, PRICING_PER_1K_TOKENS["gpt-4"])
            
            input_cost = Decimal(str(input_tokens / 1000 * pricing["input"]))
            output_cost = Decimal(str(output_tokens / 1000 * pricing["output"]))
            total_cost = input_cost + output_cost
            
            logger.debug(f"Calculated cost: ${total_cost:.6f} ({input_tokens} input + {output_tokens} output tokens)")
            return total_cost
            
        except Exception as e:
            logger.error(f"Error calculating cost: {e}")
            return Decimal("0.00")
    
    async def track_usage(
        self,
        db: AsyncSession,
        operation_type: str,
        model: str,
        input_text: str,
        output_text: str,
        conversation_id: Optional[str] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> CostTracking:
        """
        Track API usage in the database
        
        Args:
            db: Database session
            operation_type: Type of operation (chat, embedding, etc.)
            model: Model used
            input_text: Input text
            output_text: Output text
            conversation_id: Optional conversation ID
            additional_metadata: Additional metadata
            
        Returns:
            CostTracking record
        """
        try:
            # Count tokens
            input_tokens = self.count_tokens(input_text, model)
            output_tokens = self.count_tokens(output_text, model)
            total_tokens = input_tokens + output_tokens
            
            # Calculate cost
            cost = self.calculate_cost(input_tokens, output_tokens, model)
            
            # Get conversation integer ID if provided
            conv_int_id = None
            if conversation_id:
                # Convert UUID conversation_id to integer ID
                conv_query = select(Conversation.id).where(Conversation.conversation_id == conversation_id)
                conv_result = await db.execute(conv_query)
                conv_int_id = conv_result.scalar_one_or_none()
            
            # Get user integer ID
            user_query = select(User.id).where(User.user_id == self.user_id)
            user_result = await db.execute(user_query)
            user_int_id = user_result.scalar_one_or_none()
            
            if not user_int_id:
                raise ValueError(f"User {self.user_id} not found")
            
            # Create cost tracking record
            cost_record = CostTracking(
                user_id=user_int_id,  # Use integer user ID
                conversation_id=conv_int_id,  # Use integer conversation ID
                service_name="openai",
                operation_type=operation_type,
                model_name=model,  # Use model_name field
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                total_cost_usd=float(cost),  # Use total_cost_usd field
                billing_period="monthly",
                extra_metadata={  # Use extra_metadata field
                    "input_length": len(input_text),
                    "output_length": len(output_text),
                    "timestamp": datetime.utcnow().isoformat(),
                    **(additional_metadata or {})
                }
            )
            
            db.add(cost_record)
            await db.commit()
            await db.refresh(cost_record)
            
            logger.info(f"Tracked usage: {total_tokens} tokens, ${cost:.6f} for user {self.user_id}")
            return cost_record
            
        except Exception as e:
            logger.error(f"Error tracking usage: {e}")
            await db.rollback()
            raise
    
    async def get_user_usage_stats(
        self,
        db: AsyncSession,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get usage statistics for a user
        
        Args:
            db: Database session
            days: Number of days to look back
            
        Returns:
            Dictionary with usage statistics
        """
        try:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get user integer ID
            user_query = select(User.id).where(User.user_id == self.user_id)
            user_result = await db.execute(user_query)
            user_int_id = user_result.scalar_one_or_none()
            
            if not user_int_id:
                raise ValueError(f"User {self.user_id} not found")
            
            # Query usage stats
            query = select(
                func.count(CostTracking.id).label("total_requests"),
                func.sum(CostTracking.total_tokens).label("total_tokens"),
                func.sum(CostTracking.total_cost_usd).label("total_cost"),
                func.avg(CostTracking.total_tokens).label("avg_tokens_per_request")
            ).where(
                CostTracking.user_id == user_int_id,
                CostTracking.created_at >= start_date,
                CostTracking.created_at <= end_date
            )
            
            result = await db.execute(query)
            stats = result.first()
            
            # Query by model
            model_query = select(
                CostTracking.model_name,
                func.count(CostTracking.id).label("requests"),
                func.sum(CostTracking.total_tokens).label("tokens"),
                func.sum(CostTracking.total_cost_usd).label("cost")
            ).where(
                CostTracking.user_id == user_int_id,
                CostTracking.created_at >= start_date,
                CostTracking.created_at <= end_date
            ).group_by(CostTracking.model_name)
            
            model_result = await db.execute(model_query)
            model_stats = model_result.fetchall()
            
            usage_stats = {
                "period_days": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_requests": stats.total_requests or 0,
                "total_tokens": stats.total_tokens or 0,
                "total_cost": float(stats.total_cost or 0),
                "avg_tokens_per_request": float(stats.avg_tokens_per_request or 0),
                "by_model": [
                    {
                        "model": model_stat.model_name,
                        "requests": model_stat.requests,
                        "tokens": model_stat.tokens,
                        "cost": float(model_stat.cost)
                    }
                    for model_stat in model_stats
                ]
            }
            
            logger.info(f"Retrieved usage stats for user {self.user_id}: {usage_stats['total_requests']} requests")
            return usage_stats
            
        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            return {
                "period_days": days,
                "total_requests": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "avg_tokens_per_request": 0.0,
                "by_model": []
            }
    
    async def check_user_quota(
        self,
        db: AsyncSession,
        requested_tokens: int = 0
    ) -> Dict[str, Any]:
        """
        Check if user is within their quota limits
        
        Args:
            db: Database session
            requested_tokens: Additional tokens being requested
            
        Returns:
            Dictionary with quota status
        """
        try:
            # Get user subscription tier
            user_query = select(User).where(User.user_id == self.user_id)
            user_result = await db.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                return {"allowed": False, "reason": "User not found"}
            
            # Define quota limits by subscription tier
            quotas = {
                "free": {"monthly_tokens": 100000, "daily_cost": 5.00},
                "basic": {"monthly_tokens": 1000000, "daily_cost": 25.00},
                "premium": {"monthly_tokens": 5000000, "daily_cost": 100.00},
                "enterprise": {"monthly_tokens": -1, "daily_cost": -1}  # Unlimited
            }
            
            user_quota = quotas.get(user.subscription_tier, quotas["free"])
            
            # Check if unlimited
            if user_quota["monthly_tokens"] == -1:
                return {"allowed": True, "quota_type": "unlimited"}
            
            # Get current month usage
            now = datetime.utcnow()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            monthly_query = select(
                func.sum(CostTracking.total_tokens).label("monthly_tokens"),
                func.sum(CostTracking.total_cost_usd).label("monthly_cost")
            ).where(
                CostTracking.user_id == user.id,  # Use the user.id from the user query above
                CostTracking.created_at >= month_start
            )
            
            monthly_result = await db.execute(monthly_query)
            monthly_stats = monthly_result.first()
            
            current_monthly_tokens = monthly_stats.monthly_tokens or 0
            current_monthly_cost = float(monthly_stats.monthly_cost or 0)
            
            # Check daily cost (last 24 hours)
            day_start = now - timedelta(days=1)
            daily_query = select(
                func.sum(CostTracking.total_cost_usd).label("daily_cost")
            ).where(
                CostTracking.user_id == user.id,  # Use the user.id from the user query above
                CostTracking.created_at >= day_start
            )
            
            daily_result = await db.execute(daily_query)
            daily_stats = daily_result.first()
            current_daily_cost = float(daily_stats.daily_cost or 0)
            
            # Check quotas
            quota_status = {
                "allowed": True,
                "subscription_tier": user.subscription_tier,
                "monthly_tokens": {
                    "used": current_monthly_tokens,
                    "limit": user_quota["monthly_tokens"],
                    "remaining": user_quota["monthly_tokens"] - current_monthly_tokens,
                    "percentage": (current_monthly_tokens / user_quota["monthly_tokens"]) * 100
                },
                "daily_cost": {
                    "used": current_daily_cost,
                    "limit": user_quota["daily_cost"],
                    "remaining": user_quota["daily_cost"] - current_daily_cost,
                    "percentage": (current_daily_cost / user_quota["daily_cost"]) * 100
                }
            }
            
            # Check if over limits
            if current_monthly_tokens + requested_tokens > user_quota["monthly_tokens"]:
                quota_status["allowed"] = False
                quota_status["reason"] = "Monthly token limit exceeded"
            elif current_daily_cost > user_quota["daily_cost"]:
                quota_status["allowed"] = False
                quota_status["reason"] = "Daily cost limit exceeded"
            
            logger.info(f"Quota check for user {self.user_id}: allowed={quota_status['allowed']}")
            return quota_status
            
        except Exception as e:
            logger.error(f"Error checking user quota: {e}")
            return {"allowed": False, "reason": f"Error checking quota: {str(e)}"}


class CostAnalytics:
    """
    Provides analytics and insights for cost tracking
    """
    
    @staticmethod
    async def get_system_wide_stats(db: AsyncSession, days: int = 30) -> Dict[str, Any]:
        """
        Get system-wide cost statistics
        
        Args:
            db: Database session
            days: Number of days to analyze
            
        Returns:
            System-wide statistics
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Overall stats
            overall_query = select(
                func.count(CostTracking.id).label("total_requests"),
                func.sum(CostTracking.total_tokens).label("total_tokens"),
                func.sum(CostTracking.total_cost_usd).label("total_cost"),
                func.count(func.distinct(CostTracking.user_id)).label("active_users")
            ).where(
                CostTracking.created_at >= start_date,
                CostTracking.created_at <= end_date
            )
            
            overall_result = await db.execute(overall_query)
            overall_stats = overall_result.first()
            
            return {
                "period_days": days,
                "total_requests": overall_stats.total_requests or 0,
                "total_tokens": overall_stats.total_tokens or 0,
                "total_cost": float(overall_stats.total_cost or 0),
                "active_users": overall_stats.active_users or 0,
                "avg_cost_per_user": float(overall_stats.total_cost or 0) / max(overall_stats.active_users or 1, 1)
            }
            
        except Exception as e:
            logger.error(f"Error getting system-wide stats: {e}")
            return {
                "period_days": days,
                "total_requests": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "active_users": 0,
                "avg_cost_per_user": 0.0
            } 