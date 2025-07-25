"""Memory setup service for creating default memory preferences"""

from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database.memory_preference import MemoryPreference
from app.logging.logger import get_logger

logger = get_logger(__name__)

# Memory bucket configurations
MEMORY_BUCKET_CONFIGS = {
    "identity": {
        "description": "Name, pronouns, timezone, bio, device info",
        "retention_days": None,  # Permanent
        "importance_threshold": 0.8,
        "auto_categorization": True,
        "capture_enabled": True,
        "capture_entities": True,
        "capture_facts": True,
        "capture_preferences": False,
        "capture_goals": False,
        "capture_experiences": False,
        "max_memories_per_query": 3,
        "priority": 9
    },
    "preferences": {
        "description": "Communication style, tool preferences, format preferences",
        "retention_days": None,  # Permanent until changed
        "importance_threshold": 0.7,
        "auto_categorization": True,
        "capture_enabled": True,
        "capture_entities": False,
        "capture_facts": False,
        "capture_preferences": True,
        "capture_goals": False,
        "capture_experiences": False,
        "max_memories_per_query": 5,
        "priority": 8
    },
    "goals": {
        "description": "Projects, learning goals, objectives",
        "retention_days": 730,  # 2 years
        "importance_threshold": 0.8,
        "auto_categorization": True,
        "capture_enabled": True,
        "capture_entities": False,
        "capture_facts": False,
        "capture_preferences": False,
        "capture_goals": True,
        "capture_experiences": False,
        "max_memories_per_query": 5,
        "priority": 7
    },
    "workflows": {
        "description": "Daily routines, coding patterns, schedules",
        "retention_days": 120,  # 4 months
        "importance_threshold": 0.6,
        "auto_categorization": True,
        "capture_enabled": True,
        "capture_entities": False,
        "capture_facts": False,
        "capture_preferences": False,
        "capture_goals": False,
        "capture_experiences": True,
        "max_memories_per_query": 3,
        "priority": 6
    },
    "capabilities": {
        "description": "Hardware specs, budgets, skill levels",
        "retention_days": 365,  # 1 year
        "importance_threshold": 0.7,
        "auto_categorization": True,
        "capture_enabled": True,
        "capture_entities": False,
        "capture_facts": True,
        "capture_preferences": False,
        "capture_goals": False,
        "capture_experiences": False,
        "max_memories_per_query": 2,
        "priority": 5
    },
    "social": {
        "description": "Colleagues, collaborators, relationships",
        "retention_days": 180,  # 6 months
        "importance_threshold": 0.5,
        "auto_categorization": True,
        "capture_enabled": True,
        "capture_entities": True,
        "capture_facts": False,
        "capture_preferences": False,
        "capture_goals": False,
        "capture_experiences": False,
        "max_memories_per_query": 3,
        "priority": 4
    },
    # NEW BUCKETS - Demonstrating flexibility
    "health": {
        "description": "Health conditions, medications, fitness goals, dietary restrictions",
        "retention_days": 1095,  # 3 years
        "importance_threshold": 0.9,  # High importance for health
        "auto_categorization": True,
        "capture_enabled": True,
        "capture_entities": True,
        "capture_facts": True,
        "capture_preferences": True,
        "capture_goals": True,
        "capture_experiences": False,
        "max_memories_per_query": 4,
        "priority": 10  # Highest priority
    },
    "financial": {
        "description": "Budget constraints, investment preferences, financial goals",
        "retention_days": 1825,  # 5 years
        "importance_threshold": 0.8,
        "auto_categorization": True,
        "capture_enabled": True,
        "capture_entities": False,
        "capture_facts": True,
        "capture_preferences": True,
        "capture_goals": True,
        "capture_experiences": False,
        "max_memories_per_query": 3,
        "priority": 8
    },
    "learning": {
        "description": "Study methods, learning pace, educational background, courses",
        "retention_days": 730,  # 2 years
        "importance_threshold": 0.7,
        "auto_categorization": True,
        "capture_enabled": True,
        "capture_entities": True,
        "capture_facts": True,
        "capture_preferences": True,
        "capture_goals": True,
        "capture_experiences": True,
        "max_memories_per_query": 5,
        "priority": 7
    },
    "entertainment": {
        "description": "Movies, books, games, hobbies, interests",
        "retention_days": 365,  # 1 year
        "importance_threshold": 0.5,
        "auto_categorization": True,
        "capture_enabled": True,
        "capture_entities": True,
        "capture_facts": False,
        "capture_preferences": True,
        "capture_goals": False,
        "capture_experiences": True,
        "max_memories_per_query": 4,
        "priority": 3
    },
    "travel": {
        "description": "Travel preferences, past trips, future plans, accessibility needs",
        "retention_days": 1095,  # 3 years
        "importance_threshold": 0.6,
        "auto_categorization": True,
        "capture_enabled": True,
        "capture_entities": True,
        "capture_facts": True,
        "capture_preferences": True,
        "capture_goals": True,
        "capture_experiences": True,
        "max_memories_per_query": 3,
        "priority": 4
    },
    "communication": {
        "description": "Language preferences, communication style, accessibility needs",
        "retention_days": None,  # Permanent
        "importance_threshold": 0.8,
        "auto_categorization": True,
        "capture_enabled": True,
        "capture_entities": False,
        "capture_facts": True,
        "capture_preferences": True,
        "capture_goals": False,
        "capture_experiences": False,
        "max_memories_per_query": 3,
        "priority": 9
    },
    "projects": {
        "description": "Active projects, deadlines, collaborators, project history",
        "retention_days": 1095,  # 3 years
        "importance_threshold": 0.8,
        "auto_categorization": True,
        "capture_enabled": True,
        "capture_entities": True,
        "capture_facts": True,
        "capture_preferences": False,
        "capture_goals": True,
        "capture_experiences": True,
        "max_memories_per_query": 6,
        "priority": 8
    },
    "mistakes": {
        "description": "Past errors, lessons learned, things to avoid",
        "retention_days": 730,  # 2 years
        "importance_threshold": 0.9,  # High importance to avoid repeating
        "auto_categorization": True,
        "capture_enabled": True,
        "capture_entities": False,
        "capture_facts": True,
        "capture_preferences": False,
        "capture_goals": False,
        "capture_experiences": True,
        "max_memories_per_query": 3,
        "priority": 9
    }
}


async def create_default_memory_preferences(
    user_id: int, 
    db_session: AsyncSession,
    override_existing: bool = False
) -> Dict[str, MemoryPreference]:
    """
    Create default memory preferences for all buckets for a user
    
    Args:
        user_id: User ID to create preferences for
        db_session: Database session
        override_existing: Whether to override existing preferences
        
    Returns:
        Dict mapping bucket name to created MemoryPreference
    """
    
    created_preferences = {}
    
    for bucket, config in MEMORY_BUCKET_CONFIGS.items():
        # Check if preference already exists
        existing_query = select(MemoryPreference).where(
            MemoryPreference.user_id == user_id,
            MemoryPreference.topic == bucket
        )
        existing_result = await db_session.execute(existing_query)
        existing_pref = existing_result.scalar_one_or_none()
        
        if existing_pref and not override_existing:
            logger.info(f"Memory preference for bucket '{bucket}' already exists for user {user_id}")
            created_preferences[bucket] = existing_pref
            continue
        
        # Create new preference
        memory_pref = MemoryPreference(
            user_id=user_id,
            topic=bucket,
            memory_enabled=config["capture_enabled"],
            importance_threshold=config["importance_threshold"],
            retention_days=config["retention_days"],
            auto_categorization=config["auto_categorization"],
            auto_importance_scoring=True,
            auto_topic_detection=True,
            
            # Capture settings
            capture_entities=config["capture_entities"],
            capture_facts=config["capture_facts"],
            capture_preferences=config["capture_preferences"],
            capture_goals=config["capture_goals"],
            capture_experiences=config["capture_experiences"],
            
            # Retrieval settings
            max_memories_per_query=config["max_memories_per_query"],
            similarity_threshold=0.7,
            temporal_weight=0.3,
            
            # Priority
            priority=config["priority"],
            
            # Privacy settings
            is_private=True,
            allow_ai_learning=False,
            
            # Status
            is_active=True
        )
        
        if override_existing and existing_pref:
            # Update existing preference
            for field, value in memory_pref.__dict__.items():
                if not field.startswith('_') and field != 'id':
                    setattr(existing_pref, field, value)
            created_preferences[bucket] = existing_pref
        else:
            # Add new preference
            db_session.add(memory_pref)
            created_preferences[bucket] = memory_pref
    
    # Commit all changes
    await db_session.commit()
    
    # Refresh all objects
    for pref in created_preferences.values():
        await db_session.refresh(pref)
    
    logger.info(f"Created/updated {len(created_preferences)} memory preferences for user {user_id}")
    return created_preferences


async def setup_user_memory_system(
    user_id: int,
    db_session: AsyncSession
) -> bool:
    """
    Complete setup of memory system for a new user
    
    Args:
        user_id: User ID to setup memory for
        db_session: Database session
        
    Returns:
        True if setup was successful
    """
    
    try:
        # Create default memory preferences
        preferences = await create_default_memory_preferences(user_id, db_session)
        
        logger.info(f"Memory system setup completed for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to setup memory system for user {user_id}: {e}")
        await db_session.rollback()
        return False


async def get_user_memory_configuration(
    user_id: int,
    db_session: AsyncSession
) -> Dict[str, Any]:
    """
    Get the current memory configuration for a user
    
    Args:
        user_id: User ID
        db_session: Database session
        
    Returns:
        Dictionary with user's memory configuration
    """
    
    # Get all memory preferences for user
    prefs_query = select(MemoryPreference).where(
        MemoryPreference.user_id == user_id
    )
    prefs_result = await db_session.execute(prefs_query)
    preferences = list(prefs_result.scalars().all())
    
    # Build configuration dict
    config = {
        "user_id": user_id,
        "buckets": {},
        "global_settings": {
            "memory_enabled": any(pref.memory_enabled for pref in preferences),
            "total_buckets": len(preferences),
            "active_buckets": len([p for p in preferences if p.memory_enabled])
        }
    }
    
    # Add bucket-specific configurations
    for pref in preferences:
        config["buckets"][pref.topic] = {
            "enabled": pref.memory_enabled,
            "importance_threshold": pref.importance_threshold,
            "retention_days": pref.retention_days,
            "max_memories_per_query": pref.max_memories_per_query,
            "priority": pref.priority,
            "last_used": pref.last_used_at.isoformat() if pref.last_used_at else None,
            "usage_count": pref.usage_count
        }
    
    return config


async def update_memory_bucket_settings(
    user_id: int,
    bucket: str,
    settings: Dict[str, Any],
    db_session: AsyncSession
) -> bool:
    """
    Update settings for a specific memory bucket
    
    Args:
        user_id: User ID
        bucket: Bucket name to update
        settings: Dictionary of settings to update
        db_session: Database session
        
    Returns:
        True if update was successful
    """
    
    if bucket not in MEMORY_BUCKET_CONFIGS:
        logger.error(f"Invalid bucket name: {bucket}")
        return False
    
    try:
        # Get existing preference
        pref_query = select(MemoryPreference).where(
            MemoryPreference.user_id == user_id,
            MemoryPreference.topic == bucket
        )
        pref_result = await db_session.execute(pref_query)
        preference = pref_result.scalar_one_or_none()
        
        if not preference:
            logger.error(f"No memory preference found for user {user_id}, bucket {bucket}")
            return False
        
        # Update settings
        for field, value in settings.items():
            if hasattr(preference, field):
                setattr(preference, field, value)
                logger.info(f"Updated {field} = {value} for user {user_id}, bucket {bucket}")
        
        await db_session.commit()
        return True
        
    except Exception as e:
        logger.error(f"Failed to update memory bucket settings: {e}")
        await db_session.rollback()
        return False 