#!/usr/bin/env python3
"""
Dynamic Memory Bucket Addition Demo
Shows how to add custom memory buckets at runtime
"""

import asyncio
import sys
from typing import Dict, Any

# Add backend to path
sys.path.append('.')

from app.core.database import AsyncSessionLocal
from app.services.memory.memory_setup import MEMORY_BUCKET_CONFIGS, create_default_memory_preferences
from app.services.memory.memory_service import MemoryService
from app.models.database.user import User
from app.logging.logger import get_logger

logger = get_logger(__name__)


def add_custom_bucket(bucket_name: str, config: Dict[str, Any]):
    """
    Add a custom bucket to the system configuration
    
    Args:
        bucket_name: Name of the new bucket
        config: Configuration dictionary for the bucket
    """
    MEMORY_BUCKET_CONFIGS[bucket_name] = config
    print(f"✅ Added custom bucket '{bucket_name}' to configuration")


async def demo_custom_buckets():
    """Demonstrate adding custom memory buckets"""
    
    print("🎯 Dynamic Memory Bucket Addition Demo")
    print("=" * 50)
    
    # Show current buckets
    print(f"📊 Current buckets: {len(MEMORY_BUCKET_CONFIGS)}")
    for bucket in MEMORY_BUCKET_CONFIGS.keys():
        print(f"   - {bucket}")
    
    # Add custom buckets
    print(f"\n🔧 Adding custom buckets...")
    
    # Gaming bucket
    add_custom_bucket("gaming", {
        "description": "Gaming preferences, achievements, favorite games, gaming schedule",
        "retention_days": 365,  # 1 year
        "importance_threshold": 0.4,
        "auto_categorization": True,
        "capture_enabled": True,
        "capture_entities": True,
        "capture_facts": False,
        "capture_preferences": True,
        "capture_goals": False,
        "capture_experiences": True,
        "max_memories_per_query": 4,
        "priority": 2
    })
    
    # Cooking bucket
    add_custom_bucket("cooking", {
        "description": "Recipes, dietary restrictions, cooking skills, favorite cuisines",
        "retention_days": 730,  # 2 years
        "importance_threshold": 0.5,
        "auto_categorization": True,
        "capture_enabled": True,
        "capture_entities": True,
        "capture_facts": True,
        "capture_preferences": True,
        "capture_goals": False,
        "capture_experiences": True,
        "max_memories_per_query": 3,
        "priority": 3
    })
    
    # Fitness bucket
    add_custom_bucket("fitness", {
        "description": "Workout routines, fitness goals, exercise preferences, health metrics",
        "retention_days": 365,  # 1 year
        "importance_threshold": 0.7,
        "auto_categorization": True,
        "capture_enabled": True,
        "capture_entities": False,
        "capture_facts": True,
        "capture_preferences": True,
        "capture_goals": True,
        "capture_experiences": True,
        "max_memories_per_query": 4,
        "priority": 6
    })
    
    # Music bucket
    add_custom_bucket("music", {
        "description": "Music preferences, favorite artists, playlists, instruments played",
        "retention_days": 1095,  # 3 years
        "importance_threshold": 0.3,
        "auto_categorization": True,
        "capture_enabled": True,
        "capture_entities": True,
        "capture_facts": False,
        "capture_preferences": True,
        "capture_goals": False,
        "capture_experiences": True,
        "max_memories_per_query": 5,
        "priority": 2
    })
    
    print(f"📊 Updated buckets: {len(MEMORY_BUCKET_CONFIGS)}")
    for bucket in MEMORY_BUCKET_CONFIGS.keys():
        print(f"   - {bucket}")
    
    # Test with a user
    print(f"\n👤 Testing with a user...")
    
    async with AsyncSessionLocal() as db:
        # Create test user
        test_user = User(
            username=f"bucket_test_user",
            email=f"bucket_test@example.com",
            full_name="Bucket Test User",
            hashed_password="dummy_password_for_test"  # Required field
        )
        db.add(test_user)
        await db.commit()
        await db.refresh(test_user)
        
        user_id = test_user.id
        print(f"   Created test user with ID: {user_id}")
        
        # Setup memory system with ALL buckets (including new ones)
        print(f"   Setting up memory system with {len(MEMORY_BUCKET_CONFIGS)} buckets...")
        preferences = await create_default_memory_preferences(user_id, db)
        
        print(f"   ✅ Created preferences for {len(preferences)} buckets:")
        for bucket_name in preferences.keys():
            print(f"      - {bucket_name}")
        
        # Test storing memories in new buckets
        memory_service = MemoryService(db)
        
        # Gaming memory
        gaming_memory = await memory_service.store_memory(
            user_id=user_id,
            bucket="gaming",
            content="Loves playing strategy games, especially Civilization VI",
            memory_type="preference",
            importance=0.6,
            confidence=0.8,
            source_conversation_id="demo-gaming"
        )
        print(f"   🎮 Stored gaming memory: {gaming_memory.content[:50]}...")
        
        # Cooking memory
        cooking_memory = await memory_service.store_memory(
            user_id=user_id,
            bucket="cooking",
            content="Vegetarian, allergic to nuts, loves Italian cuisine",
            memory_type="fact",
            importance=0.8,
            confidence=0.9,
            source_conversation_id="demo-cooking"
        )
        print(f"   🍳 Stored cooking memory: {cooking_memory.content[:50]}...")
        
        # Fitness memory
        fitness_memory = await memory_service.store_memory(
            user_id=user_id,
            bucket="fitness",
            content="Goal: Run a marathon by end of year, currently runs 5K daily",
            memory_type="goal",
            importance=0.9,
            confidence=0.85,
            source_conversation_id="demo-fitness"
        )
        print(f"   🏃 Stored fitness memory: {fitness_memory.content[:50]}...")
        
        # Music memory
        music_memory = await memory_service.store_memory(
            user_id=user_id,
            bucket="music",
            content="Plays guitar, loves jazz and blues, favorite artist is B.B. King",
            memory_type="preference",
            importance=0.5,
            confidence=0.7,
            source_conversation_id="demo-music"
        )
        print(f"   🎵 Stored music memory: {music_memory.content[:50]}...")
        
        # Show final statistics
        print(f"\n📈 Final Statistics:")
        stats = await memory_service.get_user_memory_stats(user_id)
        print(f"   📊 Total memories: {stats.get('total_memories', 0)}")
        print(f"   📊 Memories by bucket:")
        for bucket, count in stats.get('memories_by_bucket', {}).items():
            print(f"      - {bucket}: {count}")
        
        # Test retrieval from new buckets
        print(f"\n🔍 Testing retrieval from new buckets:")
        
        gaming_memories = await memory_service.get_memories_by_bucket(user_id, "gaming")
        print(f"   🎮 Gaming memories: {len(gaming_memories)}")
        
        cooking_memories = await memory_service.get_memories_by_bucket(user_id, "cooking")
        print(f"   🍳 Cooking memories: {len(cooking_memories)}")
        
        fitness_memories = await memory_service.get_memories_by_bucket(user_id, "fitness")
        print(f"   🏃 Fitness memories: {len(fitness_memories)}")
        
        music_memories = await memory_service.get_memories_by_bucket(user_id, "music")
        print(f"   🎵 Music memories: {len(music_memories)}")
        
        # Cleanup
        print(f"\n🧹 Cleaning up test data...")
        from sqlalchemy import delete
        from app.models.database.user_memory import UserMemory
        from app.models.database.memory_preference import MemoryPreference
        
        await db.execute(delete(UserMemory).where(UserMemory.user_id == user_id))
        await db.execute(delete(MemoryPreference).where(MemoryPreference.user_id == user_id))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()
        print(f"   ✅ Cleanup complete")


if __name__ == "__main__":
    print("🚀 Starting Dynamic Bucket Demo...")
    
    try:
        asyncio.run(demo_custom_buckets())
    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎉 Dynamic Bucket Demo Complete!")
    print("\n💡 Key Takeaways:")
    print("   • Buckets are completely configurable")
    print("   • Add any number of buckets at runtime")
    print("   • Each bucket has independent settings")
    print("   • No database schema changes needed")
    print("   • Full CRUD operations on all buckets") 