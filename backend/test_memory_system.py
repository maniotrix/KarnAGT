#!/usr/bin/env python3
"""
Memory System MVP Demo
Demonstrates the complete memory system functionality using existing backend infrastructure
"""

import asyncio
import sys

# Add backend to path
sys.path.append('.')

from app.core.database import AsyncSessionLocal, engine
from app.services.memory.memory_service import MemoryService
from app.services.memory.memory_setup import setup_user_memory_system
from app.services.memory.memory_extractor import MemoryExtractor
from app.services.context.memory_aware_context_builder import get_memory_enhanced_llm_context
from aicore.logger import get_logger

logger = get_logger(__name__)


async def create_test_user(db):
    """Create a dedicated test user for the demo"""
    try:
        from app.models.database.user import User
        from sqlalchemy import select
        import uuid
        
        # Create a test user with a unique email
        test_email = f"test_memory_demo_{uuid.uuid4().hex[:8]}@example.com"
        test_user = User(
            email=test_email,
            username=f"test_user_{uuid.uuid4().hex[:8]}",
            full_name="Memory Test User",
            is_active=True,
            is_verified=True,
            hashed_password="dummy_hash_for_test"  # Not used in demo
        )
        
        db.add(test_user)
        await db.commit()
        await db.refresh(test_user)
        
        print(f"   👤 Created test user: {test_user.email} (ID: {test_user.id})")
        return test_user.id
        
    except Exception as e:
        await db.rollback()
        print(f"   ❌ Failed to create test user: {e}")
        raise


async def cleanup_test_data(db, user_id: int):
    """Clean up test data created during the demo"""
    try:
        from sqlalchemy import delete
        from app.models.database.user_memory import UserMemory
        from app.models.database.memory_preference import MemoryPreference
        from app.models.database.user import User
        
        # Delete test memories
        await db.execute(
            delete(UserMemory).where(UserMemory.user_id == user_id)
        )
        
        # Delete test memory preferences
        await db.execute(
            delete(MemoryPreference).where(MemoryPreference.user_id == user_id)
        )
        
        # Delete the test user itself
        await db.execute(
            delete(User).where(User.id == user_id)
        )
        
        await db.commit()
        print(f"   🧹 Test data and user (ID: {user_id}) cleaned up successfully")
        
    except Exception as e:
        await db.rollback()
        print(f"   ⚠️ Cleanup failed: {e}")


async def demo_memory_system(skip_cleanup: bool = False):
    """Demonstrate the complete memory system"""
    
    print("🧠 Memory System MVP Demo")
    print("=" * 50)
    
    # Use existing database connection
    print("1. Connecting to existing database...")
    
    async with AsyncSessionLocal() as db:
        # Create a dedicated test user
        print("2. Creating dedicated test user...")
        user_id = await create_test_user(db)
        
        # Create memory service
        memory_service = MemoryService(db)
        
        conversation_id = "demo-conv-123"
        
        print(f"3. Setting up memory system for user {user_id}...")
        
        # Setup memory system
        success = await setup_user_memory_system(user_id, db)
        if success:
            print("   ✅ Memory system initialized")
        else:
            print("   ❌ Failed to initialize memory system")
            return
        
        print("\n4. Storing sample memories...")
        
        # Store sample memories in different buckets
        sample_memories = [
            {
                "bucket": "identity",
                "content": "User prefers to be called Prince",
                "importance": 0.9,
                "confidence": 0.95
            },
            {
                "bucket": "preferences", 
                "content": "Prefers detailed technical explanations",
                "importance": 0.7,
                "confidence": 0.8
            },
            {
                "bucket": "goals",
                "content": "Building a ChatGPT clone with memory system",
                "importance": 0.9,
                "confidence": 0.9,
                "status": "active"
            },
            {
                "bucket": "capabilities",
                "content": "Experienced with Python, FastAPI, and SQLAlchemy",
                "importance": 0.8,
                "confidence": 0.85
            },
            {
                "bucket": "workflows",
                "content": "Prefers to implement MVP first, then add features",
                "importance": 0.6,
                "confidence": 0.7
            }
        ]
        
        stored_memories = []
        for memory_data in sample_memories:
            try:
                memory = await memory_service.store_memory(
                    user_id=user_id,
                    source_conversation_id=conversation_id,
                    **memory_data
                )
                stored_memories.append(memory)
                print(f"   ✅ Stored: {memory_data['content'][:40]}...")
            except Exception as e:
                print(f"   ❌ Failed to store: {memory_data['content'][:40]}... - {e}")
        
        print(f"\n5. Memory Statistics:")
        stats = await memory_service.get_user_memory_stats(user_id)
        print(f"   📊 Total memories: {stats.get('total_memories', 0)}")
        print(f"   📊 Recent memories (7 days): {stats.get('recent_memories_7_days', 0)}")
        print(f"   📊 Memories by bucket:")
        for bucket, count in stats.get('memories_by_bucket', {}).items():
            print(f"      - {bucket}: {count}")
        
        print(f"\n6. Testing memory retrieval...")
        
        # Test bucket retrieval
        identity_memories = await memory_service.get_memories_by_bucket(user_id, "identity")
        print(f"   🔍 Identity memories: {len(identity_memories)}")
        for memory in identity_memories:
            print(f"      - {memory.content}")
        
        # Test relevant memory search
        query = "What are my current goals?"
        relevant_memories = await memory_service.get_relevant_memories(user_id, query)
        print(f"\n   🔍 Memories relevant to '{query}': {len(relevant_memories)}")
        for memory in relevant_memories:
            print(f"      - [{memory.bucket}] {memory.content}")
        
        print(f"\n7. Testing memory-aware context building...")
        
        # Test memory-enhanced context
        try:
            context = await get_memory_enhanced_llm_context(
                conversation_id, user_id, db, query
            )
            print(f"   🧠 Generated context ({len(context)} characters):")
            print("   " + "─" * 60)
            # Show first 500 characters of context
            context_preview = context[:500] + "..." if len(context) > 500 else context
            print("   " + context_preview.replace("\n", "\n   "))
            print("   " + "─" * 60)
        except Exception as e:
            print(f"   ❌ Context building failed: {e}")
        
        print(f"\n8. Testing memory extraction (simulated)...")
        
        # Test memory extraction with sample conversation
        extractor = MemoryExtractor(memory_service)
        sample_conversation = [
            {"role": "user", "content": "Hi, I'm working on scaling my startup Trykaa"},
            {"role": "assistant", "content": "That's great! What kind of scaling challenges are you facing?"},
            {"role": "user", "content": "I prefer to use microservices architecture and I'm good with Go and Python"},
            {"role": "assistant", "content": "Excellent choice! Microservices work well for scaling."}
        ]
        
        try:
            extracted = await extractor.extract_memories_from_conversation(
                sample_conversation, user_id, conversation_id + "-2"
            )
            
            total_extracted = sum(len(memories) for memories in extracted.values())
            print(f"   🔬 Extracted {total_extracted} memories from conversation")
            
            for bucket, memories in extracted.items():
                if memories:
                    print(f"      - {bucket}: {len(memories)} memories")
                    for memory in memories:
                        print(f"        * {memory.content}")
                        
        except Exception as e:
            print(f"   ❌ Memory extraction failed: {e}")
        
        print(f"\n9. Final Statistics:")
        final_stats = await memory_service.get_user_memory_stats(user_id)
        print(f"   📊 Total memories: {final_stats.get('total_memories', 0)}")
        print(f"   📊 Memories by bucket:")
        for bucket, count in final_stats.get('memories_by_bucket', {}).items():
            print(f"      - {bucket}: {count}")
        
        # Clean up test data at the end (unless skipped)
        if not skip_cleanup:
            print(f"\n10. Cleaning up test data and user...")
            await cleanup_test_data(db, user_id)
        else:
            print(f"\n10. Skipping cleanup (--no-cleanup flag) - Test user ID: {user_id}")
        
    print(f"\n🎉 Memory System Demo Complete!")
    print("=" * 50)
    print("Key Features Demonstrated:")
    print("✅ Memory storage across 6 buckets")
    print("✅ Memory retrieval and search")
    print("✅ Memory-aware context building")
    print("✅ Automatic memory extraction (simulated)")
    print("✅ Memory statistics and analytics")


async def quick_api_demo():
    """Quick demo of the API endpoints"""
    
    print("\n🌐 API Endpoints Available:")
    print("=" * 30)
    print("GET  /api/v1/memory/          - Service status")
    print("POST /api/v1/memory/setup     - Initialize memory system")
    print("GET  /api/v1/memory/stats     - Memory statistics")
    print("GET  /api/v1/memory/buckets   - Available memory buckets")
    print("GET  /api/v1/memory/all       - All user memories")
    print("POST /api/v1/memory/create    - Create new memory")
    print()
    print("📖 Example API Usage:")
    print("curl -X POST http://localhost:8000/api/v1/memory/setup")
    print("curl http://localhost:8000/api/v1/memory/stats")
    print("curl http://localhost:8000/api/v1/memory/buckets")


if __name__ == "__main__":
    import sys
    
    # Check for --no-cleanup flag
    skip_cleanup = "--no-cleanup" in sys.argv
    if skip_cleanup:
        print("⚠️  Running with --no-cleanup flag (test data will persist)")
    
    print("🚀 Starting Memory System MVP Demo...")
    
    try:
        # Run the main demo
        asyncio.run(demo_memory_system(skip_cleanup))
        
        # Show API info
        asyncio.run(quick_api_demo())
        
    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n👋 Thanks for trying the Memory System MVP!") 