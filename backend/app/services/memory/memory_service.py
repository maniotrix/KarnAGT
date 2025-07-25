"""Core Memory Service for managing user memories across 6 buckets"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta

from app.models.database.user_memory import UserMemory
from app.models.database.memory_preference import MemoryPreference
from app.models.database.user import User
from app.services.memory.memory_setup import MEMORY_BUCKET_CONFIGS
from app.logging.logger import get_logger

logger = get_logger(__name__)


class MemoryService:
    """Service for managing user memories with 6-bucket system"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    # Core CRUD Operations
    
    async def store_memory(
        self, 
        user_id: int, 
        bucket: str, 
        content: str,
        memory_type: Optional[str] = None,
        importance: Optional[float] = None,
        confidence: float = 1.0,
        structured_data: Optional[Dict] = None,
        source_conversation_id: Optional[str] = None,
        **kwargs
    ) -> UserMemory:
        """Store a new memory for a user"""
        
        # Auto-create bucket if it doesn't exist
        if bucket not in MEMORY_BUCKET_CONFIGS:
            logger.info(f"Creating new custom bucket: {bucket}")
            MEMORY_BUCKET_CONFIGS[bucket] = {
                "description": f"Custom bucket: {bucket}",
                "retention_days": 365,  # 1 year default
                "importance_threshold": 0.3,
                "capture_enabled": True
            }
        
        # Set defaults based on bucket
        if memory_type is None:
            memory_type = self._infer_memory_type_from_bucket(bucket)
        
        if importance is None:
            importance = MEMORY_BUCKET_CONFIGS[bucket]["importance_threshold"]
        
        # Check if user has memory preferences for this bucket
        should_store = await self._should_store_memory(user_id, bucket, importance)
        if not should_store:
            logger.info(f"Memory not stored for user {user_id}, bucket {bucket} - below importance threshold")
            raise ValueError("Memory below importance threshold")
        
        # Create memory
        memory = UserMemory(
            user_id=user_id,
            bucket=bucket,
            memory_type=memory_type,
            content=content,
            importance=importance,
            confidence=confidence,
            structured_data=structured_data or {},
            source_conversation_id=source_conversation_id,
            **kwargs
        )
        
        # Set expiration based on bucket
        memory.set_expiration_by_bucket()
        
        # Save to database
        self.db.add(memory)
        await self.db.commit()
        await self.db.refresh(memory)
        
        logger.info(f"Stored memory {memory.memory_id} for user {user_id} in bucket {bucket}")
        return memory
    
    async def get_memories_by_bucket(
        self, 
        user_id: int, 
        bucket: str, 
        limit: int = 10,
        include_archived: bool = False,
        status: Optional[str] = None
    ) -> List[UserMemory]:
        """Get memories for a specific bucket"""
        
        query = select(UserMemory).where(
            and_(
                UserMemory.user_id == user_id,
                UserMemory.bucket == bucket,
                UserMemory.is_active == True
            )
        )
        
        if not include_archived:
            query = query.where(UserMemory.is_archived == False)
        
        if status:
            query = query.where(UserMemory.status == status)
        
        # Order by importance and recency
        query = query.order_by(
            desc(UserMemory.importance),
            desc(UserMemory.last_accessed)
        ).limit(limit)
        
        result = await self.db.execute(query)
        memories = list(result.scalars().all())
        
        # Update access tracking
        for memory in memories:
            memory.update_access()
        
        await self.db.commit()
        
        return memories
    
    async def get_relevant_memories(
        self, 
        user_id: int, 
        query_text: str, 
        limit: int = 5,
        bucket: Optional[str] = None,
        min_importance: float = 0.3
    ) -> List[UserMemory]:
        """Get memories relevant to a query (simple text matching for MVP)"""
        
        # Build base query
        base_query = select(UserMemory).where(
            and_(
                UserMemory.user_id == user_id,
                UserMemory.is_active == True,
                UserMemory.is_archived == False,
                UserMemory.importance >= min_importance
            )
        )
        
        if bucket:
            base_query = base_query.where(UserMemory.bucket == bucket)
        
        # Simple text matching (can be enhanced with vector search later)
        query_words = query_text.lower().split()
        if query_words:
            # Match any word in the query against memory content
            content_conditions = []
            for word in query_words[:5]:  # Limit to first 5 words
                content_conditions.append(UserMemory.content.ilike(f"%{word}%"))
            
            base_query = base_query.where(or_(*content_conditions))
        
        # Order by importance and recency
        base_query = base_query.order_by(
            desc(UserMemory.importance),
            desc(UserMemory.last_accessed)
        ).limit(limit)
        
        result = await self.db.execute(base_query)
        memories = list(result.scalars().all())
        
        # Update access tracking
        for memory in memories:
            memory.update_access()
        
        await self.db.commit()
        
        return memories
    
    async def get_all_user_memories(
        self, 
        user_id: int, 
        include_archived: bool = False
    ) -> List[UserMemory]:
        """Get ALL memories for a user - no limit"""
        
        query = select(UserMemory).where(
            and_(
                UserMemory.user_id == user_id,
                UserMemory.is_active == True
            )
        )
        
        if not include_archived:
            query = query.where(UserMemory.is_archived == False)
        
        query = query.order_by(
            desc(UserMemory.importance),
            desc(UserMemory.created_at)
        )
        # NO LIMIT - get everything
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_user_memories(
        self, 
        user_id: int, 
        limit: int,
        include_archived: bool = False
    ) -> List[UserMemory]:
        """Get limited number of user memories"""
        
        query = select(UserMemory).where(
            and_(
                UserMemory.user_id == user_id,
                UserMemory.is_active == True
            )
        )
        
        if not include_archived:
            query = query.where(UserMemory.is_archived == False)
        
        query = query.order_by(
            desc(UserMemory.importance),
            desc(UserMemory.created_at)
        ).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update_memory(
        self, 
        memory_id: str, 
        **updates
    ) -> Optional[UserMemory]:
        """Update a specific memory"""
        
        query = select(UserMemory).where(UserMemory.memory_id == memory_id)
        result = await self.db.execute(query)
        memory = result.scalar_one_or_none()
        
        if not memory:
            return None
        
        # Update fields
        for field, value in updates.items():
            if hasattr(memory, field):
                setattr(memory, field, value)
        
        memory.updated_at = datetime.utcnow()
        memory.last_updated_by = "user"
        
        await self.db.commit()
        await self.db.refresh(memory)
        
        logger.info(f"Updated memory {memory_id}")
        return memory
    
    async def archive_memory(self, memory_id: str) -> bool:
        """Archive (soft delete) a memory"""
        
        query = select(UserMemory).where(UserMemory.memory_id == memory_id)
        result = await self.db.execute(query)
        memory = result.scalar_one_or_none()
        
        if not memory:
            return False
        
        memory.is_archived = True
        memory.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        logger.info(f"Archived memory {memory_id}")
        return True
    
    async def delete_memory(self, memory_id: str) -> bool:
        """Permanently delete a memory"""
        
        query = select(UserMemory).where(UserMemory.memory_id == memory_id)
        result = await self.db.execute(query)
        memory = result.scalar_one_or_none()
        
        if not memory:
            return False
        
        await self.db.delete(memory)
        await self.db.commit()
        
        logger.info(f"Deleted memory {memory_id}")
        return True
    
    # Analytics and Stats
    
    async def get_user_memory_stats(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive memory statistics for a user"""
        
        # Total memories
        total_query = select(func.count(UserMemory.id)).where(
            and_(
                UserMemory.user_id == user_id,
                UserMemory.is_active == True,
                UserMemory.is_archived == False
            )
        )
        total_result = await self.db.execute(total_query)
        total_memories = total_result.scalar() or 0
        
        # Memories by bucket
        bucket_query = select(
            UserMemory.bucket,
            func.count(UserMemory.id).label('count')
        ).where(
            and_(
                UserMemory.user_id == user_id,
                UserMemory.is_active == True,
                UserMemory.is_archived == False
            )
        ).group_by(UserMemory.bucket)
        
        bucket_result = await self.db.execute(bucket_query)
        memories_by_bucket = {row.bucket: row.count for row in bucket_result}
        
        # Recent activity (memories created in last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_query = select(func.count(UserMemory.id)).where(
            and_(
                UserMemory.user_id == user_id,
                UserMemory.created_at >= week_ago,
                UserMemory.is_active == True
            )
        )
        recent_result = await self.db.execute(recent_query)
        recent_memories = recent_result.scalar() or 0
        
        return {
            "total_memories": total_memories,
            "memories_by_bucket": memories_by_bucket,
            "recent_memories_7_days": recent_memories,
            "buckets_info": MEMORY_BUCKET_CONFIGS
        }
    
    # Helper Methods
    
    def _infer_memory_type_from_bucket(self, bucket: str) -> str:
        """Infer memory type from bucket"""
        type_mapping = {
            "identity": "fact",
            "preferences": "preference", 
            "goals": "goal",
            "workflows": "workflow",
            "capabilities": "capability",
            "social": "contact"
        }
        return type_mapping.get(bucket, "fact")
    
    async def _should_store_memory(
        self, 
        user_id: int, 
        bucket: str, 
        importance: float
    ) -> bool:
        """Check if memory should be stored based on user preferences"""
        
        # Get user's memory preference for this bucket
        pref_query = select(MemoryPreference).where(
            and_(
                MemoryPreference.user_id == user_id,
                MemoryPreference.topic == bucket
            )
        )
        pref_result = await self.db.execute(pref_query)
        preference = pref_result.scalar_one_or_none()
        
        if not preference:
            # No specific preference, use default
            return importance >= 0.5
        
        # Use preference settings
        return preference.should_store_memory(importance)
    
    async def cleanup_expired_memories(self) -> int:
        """Clean up expired memories (maintenance task)"""
        
        # Find expired memories
        now = datetime.utcnow()
        expired_query = select(UserMemory).where(
            and_(
                UserMemory.expires_at != None,
                UserMemory.expires_at < now,
                UserMemory.is_active == True
            )
        )
        
        expired_result = await self.db.execute(expired_query)
        expired_memories = list(expired_result.scalars().all())
        
        # Archive expired memories
        count = 0
        for memory in expired_memories:
            memory.is_archived = True
            memory.updated_at = now
            count += 1
        
        if count > 0:
            await self.db.commit()
            logger.info(f"Archived {count} expired memories")
        
        return count
    
    async def get_memories_for_context(
        self, 
        user_id: int, 
        current_query: str,
        max_memories: int = 10
    ) -> Dict[str, List[UserMemory]]:
        """Get memories organized for context building"""
        
        context_memories = {}
        
        # Always include identity if available (max 2)
        identity_memories = await self.get_memories_by_bucket(
            user_id, "identity", limit=2
        )
        if identity_memories:
            context_memories["identity"] = identity_memories
        
        # Get relevant preferences (max 2)
        relevant_preferences = await self.get_relevant_memories(
            user_id, current_query, bucket="preferences", limit=2
        )
        if relevant_preferences:
            context_memories["preferences"] = relevant_preferences
        
        # Get active goals if query seems goal-related (max 2)
        if self._is_goal_related_query(current_query):
            active_goals = await self.get_memories_by_bucket(
                user_id, "goals", status="active", limit=2
            )
            if active_goals:
                context_memories["goals"] = active_goals
        
        # Get relevant workflows/capabilities if space allows
        remaining_slots = max_memories - sum(len(memories) for memories in context_memories.values())
        if remaining_slots > 0:
            other_memories = await self.get_relevant_memories(
                user_id, current_query, limit=remaining_slots, min_importance=0.6
            )
            if other_memories:
                context_memories["other"] = other_memories
        
        return context_memories
    
    def _is_goal_related_query(self, query: str) -> bool:
        """Simple heuristic to detect goal-related queries"""
        goal_keywords = [
            "goal", "project", "plan", "objective", "target", 
            "working on", "building", "learning", "studying"
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in goal_keywords) 