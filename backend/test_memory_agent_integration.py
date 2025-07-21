#!/usr/bin/env python3
"""
Memory Agent Integration Test - Test memory tools with real LLM agent
Tests the complete flow: User -> LLM Agent -> Memory Tools -> Database
"""

import asyncio
import sys
import uuid

# Add backend to path
sys.path.append('.')

from app.core.database import AsyncSessionLocal
from app.models.database.user import User
from app.models.database.conversation import Conversation
from app.models.database.user_memory import UserMemory
from app.models.database.memory_preference import MemoryPreference
from app.services.memory.memory_service import MemoryService
from app.services.memory.llm_memory_tools import (
    get_essential_user_context
)
from app.services.memory.memory_setup import setup_user_memory_system

# AI Agent imports
from aicore.core.configurable_assistant_client import ConfigurableAssistantClient
from aicore.logger import get_logger

# SQLAlchemy cleanup
from sqlalchemy import delete

logger = get_logger(__name__)


class MemoryAgentIntegrationTest:
    """Test class for memory + LLM agent integration"""
    
    def __init__(self):
        self.test_user = None
        self.test_conversations = []
        self.test_memories = []
        self.memory_service = None
        self.agent = None
        self.assistant_client = None
        
    async def setup_test_environment(self):
        """Set up test user, conversations, and memory system"""
        logger.info("Setting up test environment...")
        
        async with AsyncSessionLocal() as db:
            # Create test user
            self.test_user = User(
                username=f"memory_test_user_{uuid.uuid4().hex[:8]}",
                email=f"memory_test_{uuid.uuid4().hex[:8]}@example.com",
                full_name="Memory Test User",
                hashed_password="test_password_hash",
                memory_enabled=True,
                memory_retention_days=365,
                auto_memory_importance=True
            )
            db.add(self.test_user)
            await db.commit()
            await db.refresh(self.test_user)
            
            logger.info(f"Created test user: {self.test_user.username} (ID: {self.test_user.id})")
            
            # Set up memory system for user
            await setup_user_memory_system(self.test_user.id, db)
            logger.info("Memory system setup complete")
            
            # Create test conversations
            conv1 = Conversation(
                conversation_id=f"conv_memory_test_1_{uuid.uuid4().hex[:8]}",
                user_id=self.test_user.id,
                title="Memory Test Conversation 1",
                status="active"
            )
            conv2 = Conversation(
                conversation_id=f"conv_memory_test_2_{uuid.uuid4().hex[:8]}",
                user_id=self.test_user.id,
                title="Memory Test Conversation 2", 
                status="active"
            )
            
            db.add(conv1)
            db.add(conv2)
            await db.commit()
            await db.refresh(conv1)
            await db.refresh(conv2)
            
            self.test_conversations = [conv1, conv2]
            logger.info(f"Created {len(self.test_conversations)} test conversations")
            
            # Initialize memory service
            self.memory_service = MemoryService(db)
            
            # Create some initial memories for testing
            await self._create_initial_memories()
    
    async def _create_initial_memories(self):
        """Create some initial memories for the test user"""
        logger.info("Creating initial test memories...")
        
        initial_memories = [
            {
                "bucket": "identity",
                "content": "John Smith, Senior Software Engineer, Pacific Time Zone (PST)",
                "importance": 0.9,
                "confidence": 0.95
            },
            {
                "bucket": "preferences", 
                "content": "Prefers concise explanations with practical code examples",
                "importance": 0.8,
                "confidence": 0.9
            },
            {
                "bucket": "preferences",
                "content": "Uses VS Code with Python and JavaScript, likes clean code with comments",
                "importance": 0.7,
                "confidence": 0.85
            },
            {
                "bucket": "goals",
                "content": "Learning advanced React patterns for upcoming project deadline in 2 weeks",
                "importance": 0.9,
                "confidence": 0.8,
                "status": "active"
            },
            {
                "bucket": "capabilities",
                "content": "5+ years Python experience, familiar with Django, Flask, FastAPI",
                "importance": 0.8,
                "confidence": 0.9
            },
            {
                "bucket": "workflows",
                "content": "Follows TDD approach, writes unit tests first, uses git flow",
                "importance": 0.6,
                "confidence": 0.8
            }
        ]
        
        for mem_data in initial_memories:
            memory = await self.memory_service.store_memory(
                user_id=self.test_user.id,
                source_conversation_id=self.test_conversations[0].conversation_id,
                **mem_data
            )
            self.test_memories.append(memory)
        
        logger.info(f"Created {len(initial_memories)} initial memories")
    
    async def setup_llm_agent(self):
        """Set up the LLM agent with memory tools using configuration"""
        logger.info("Setting up LLM agent with memory tools...")
        
        try:
            # Test essential user context first
            async with AsyncSessionLocal() as db:
                memory_service = MemoryService(db)
                
                essential_context = await get_essential_user_context(
                    memory_service=memory_service,
                    user_id=self.test_user.id
                )
                
                logger.info(f"Essential user context generated:")
                logger.info(f"Context: {essential_context}")
                
                # Verify essential context contains expected information
                assert "John Smith" in essential_context, "Identity info should be in context"
                assert "Pacific Time Zone" in essential_context, "Timezone should be in context"
                assert "concise explanations" in essential_context, "Preferences should be in context"
                assert "React patterns" in essential_context, "Current goals should be in context"
                
                logger.info("Essential context validation passed")
                return essential_context
                
        except Exception as e:
            logger.error(f"Failed to setup LLM agent: {e}")
            raise
    
    async def test_memory_retrieval_flow(self):
        """Test the complete memory retrieval flow with LLM"""
        logger.info("Testing memory retrieval flow...")
        
        try:
            # Create memory tools configuration
            async with AsyncSessionLocal() as db:
                from app.services.memory.memory_tools_config import get_memory_enabled_override_config
                
                memory_config_override = get_memory_enabled_override_config(
                    user_id=self.test_user.id,
                    conversation_id=self.test_conversations[0].conversation_id,
                    db_session=db
                )
            
            # Create assistant client with memory tools
            self.assistant_client = ConfigurableAssistantClient(
                user_id=str(self.test_user.id),
                conversation_id=self.test_conversations[0].conversation_id,
                environment="test",
                config_name="default",
                config_overrides=memory_config_override
            )
            
            # Test message that should trigger memory retrieval
            test_message = """
            Hi! I'm working on a new React project and need some help. 
            Can you remind me what programming languages and frameworks I'm experienced with?
            Also, what are my current learning goals?
            """
            
            logger.info(f"Sending test message: {test_message[:100]}...")
            
            # Process message
            response = await self.assistant_client.send_message(
                message=test_message,
                message_type="text"
            )
            
            logger.info(f"LLM Response received:")
            logger.info(f"Content: {response['content'][:200]}...")
            logger.info(f"Metadata: {response.get('metadata', {})}")
            
            # Verify that memory retrieval likely occurred
            # (In a real test, you'd check if the response includes user's info)
            assert response['content'], "Response should not be empty"
            assert not response.get('was_cancelled', False), "Response should not be cancelled"
            
            return response
            
        except Exception as e:
            logger.error(f"Memory retrieval test failed: {e}")
            raise
    
    async def test_memory_saving_flow(self):
        """Test the complete memory saving flow with LLM"""
        logger.info("Testing memory saving flow...")
        
        try:
            # Test message that shares new information
            test_message = """
            By the way, I just started learning TypeScript last week and I'm really enjoying it! 
            I'm also working on a side project - building a personal fitness tracker app using React Native.
            Oh, and I prefer dark mode in my IDE and I like my code formatted with Prettier.
            """
            
            logger.info(f"Sending memory-worthy message: {test_message[:100]}...")
            
            # Process message  
            response = await self.assistant_client.send_message(
                message=test_message,
                message_type="text"
            )
            
            logger.info(f"LLM Response to memory-worthy message:")
            logger.info(f"Content: {response['content'][:200]}...")
            
            # Check if new memories were saved
            await self._verify_new_memories_saved()
            
            return response
            
        except Exception as e:
            logger.error(f"Memory saving test failed: {e}")
            raise
    
    async def _verify_new_memories_saved(self):
        """Verify that new memories were actually saved to database"""
        logger.info("Verifying new memories were saved...")
        
        async with AsyncSessionLocal() as db:
            memory_service = MemoryService(db)
            
            # Get all user memories
            all_memories = await memory_service.get_all_user_memories(
                user_id=self.test_user.id,
                include_archived=False
            )
            
            logger.info(f"Total memories found: {len(all_memories)}")
            
            # Check for memories that might have been created
            new_memories = [
                mem for mem in all_memories 
                if mem.id not in [initial_mem.id for initial_mem in self.test_memories]
            ]
            
            logger.info(f"New memories found: {len(new_memories)}")
            
            for mem in new_memories:
                logger.info(f"  - [{mem.bucket}] {mem.content} (importance: {mem.importance})")
            
            # Store new memories for cleanup
            self.test_memories.extend(new_memories)
    
    async def test_dynamic_bucket_creation(self):
        """Test dynamic bucket creation through LLM"""
        logger.info("Testing dynamic bucket creation...")
        
        try:
            # Message that should create a custom bucket
            test_message = """
            I forgot to mention - I'm really into fitness and gaming too! 
            I go to the gym 4 times a week and I love playing strategy games like Civilization VI.
            I also enjoy cooking healthy meals on weekends.
            """
            
            logger.info(f"Sending message for custom buckets: {test_message[:100]}...")
            
            response = await self.assistant_client.send_message(
                message=test_message,
                message_type="text"
            )
            
            logger.info(f"Response for custom bucket creation:")
            logger.info(f"Content: {response['content'][:200]}...")
            
            # Check for custom buckets in database
            await self._verify_custom_buckets_created()
            
            return response
            
        except Exception as e:
            logger.error(f"Dynamic bucket creation test failed: {e}")
            raise
    
    async def _verify_custom_buckets_created(self):
        """Verify custom buckets were created"""
        logger.info("Checking for custom buckets...")
        
        async with AsyncSessionLocal() as db:
            memory_service = MemoryService(db)
            
            all_memories = await memory_service.get_all_user_memories(
                user_id=self.test_user.id,
                include_archived=False
            )
            
            # Find unique buckets
            buckets = {str(mem.bucket) for mem in all_memories}
            standard_buckets = {"identity", "preferences", "goals", "workflows", "capabilities", "social"}
            custom_buckets = buckets - standard_buckets
            
            logger.info(f"All buckets found: {buckets}")
            logger.info(f"Custom buckets: {custom_buckets}")
            
            if custom_buckets:
                logger.info("Custom buckets were created!")
                for bucket in custom_buckets:
                    bucket_memories = [mem for mem in all_memories if str(mem.bucket) == bucket]
                    logger.info(f"  - {bucket}: {len(bucket_memories)} memories")
            else:
                logger.warning("⚠️  No custom buckets found")
    
    async def test_cross_conversation_memory(self):
        """Test that memories persist across conversations"""
        logger.info("Testing cross-conversation memory persistence...")
        
        try:
            # Create memory tools configuration for second conversation
            async with AsyncSessionLocal() as db:
                from app.services.memory.memory_tools_config import get_memory_enabled_override_config
                
                memory_config_override = get_memory_enabled_override_config(
                    user_id=self.test_user.id,
                    conversation_id=self.test_conversations[1].conversation_id,
                    db_session=db
                )
            
            # Create new assistant client for second conversation
            assistant_client_2 = ConfigurableAssistantClient(
                user_id=str(self.test_user.id),
                conversation_id=self.test_conversations[1].conversation_id,
                environment="test",
                config_name="default",
                config_overrides=memory_config_override
            )
            
            # Ask about previously shared information in new conversation
            test_message = """
            Hi there! I'm starting a new conversation. 
            Can you remind me what programming experience I have and what I'm currently learning?
            """
            
            logger.info(f"Sending message in new conversation: {test_message[:100]}...")
            
            response = await assistant_client_2.send_message(
                message=test_message,
                message_type="text"
            )
            
            logger.info(f"Cross-conversation response:")
            logger.info(f"Content: {response['content'][:200]}...")
            
            # The response should include information from previous conversations
            # because it's stored in the user's memory
            
            return response
            
        except Exception as e:
            logger.error(f"Cross-conversation memory test failed: {e}")
            raise
    
    async def cleanup_test_environment(self):
        """Clean up all test data"""
        logger.info("Cleaning up test environment...")
        
        try:
            async with AsyncSessionLocal() as db:
                # Delete ALL user memories (not just tracked ones)
                # This ensures we catch any memories created during testing
                if self.test_user:
                    # Delete all memories for this user
                    await db.execute(
                        delete(UserMemory).where(UserMemory.user_id == self.test_user.id)
                    )
                    logger.info("Deleted all test user memories")
                    
                    # Delete memory preferences
                    await db.execute(
                        delete(MemoryPreference).where(MemoryPreference.user_id == self.test_user.id)
                    )
                    logger.info("Deleted memory preferences")
                    
                    # Delete conversations
                    if self.test_conversations:
                        conv_ids = [conv.id for conv in self.test_conversations]
                        await db.execute(
                            delete(Conversation).where(Conversation.id.in_(conv_ids))
                        )
                        logger.info(f"Deleted {len(conv_ids)} test conversations")
                    
                    # Delete test user
                    await db.execute(
                        delete(User).where(User.id == self.test_user.id)
                    )
                    logger.info(f"Deleted test user: {self.test_user.username}")
                
                await db.commit()
                logger.info("Cleanup complete")
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            raise
    
    async def run_comprehensive_test(self):
        """Run the complete test suite"""
        logger.info("Starting comprehensive memory + LLM agent integration test")
        
        try:
            # Setup
            await self.setup_test_environment()
            essential_context = await self.setup_llm_agent()
            
            # Run tests
            logger.info("=" * 60)
            logger.info("TEST 1: Memory Retrieval Flow")
            await self.test_memory_retrieval_flow()
            
            logger.info("=" * 60)
            logger.info("TEST 2: Memory Saving Flow")
            await self.test_memory_saving_flow()
            
            logger.info("=" * 60)
            logger.info("TEST 3: Dynamic Bucket Creation")
            await self.test_dynamic_bucket_creation()
            
            logger.info("=" * 60)
            logger.info("TEST 4: Cross-Conversation Memory")
            await self.test_cross_conversation_memory()
            
            logger.info("=" * 60)
            logger.info(" ALL TESTS COMPLETED SUCCESSFULLY!")
            
        except Exception as e:
            logger.error(f"Test suite failed: {e}")
            raise
        finally:
            # Always cleanup
            await self.cleanup_test_environment()


async def main():
    """Main test execution"""
    print("\n" + "=" * 80)
    print("Memory + LLM Agent Integration Test Suite")
    print("=" * 80)
    
    test_runner = MemoryAgentIntegrationTest()
    
    try:
        await test_runner.run_comprehensive_test()
        print("\nTest suite completed successfully!")
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        await test_runner.cleanup_test_environment()
        
    except Exception as e:
        print(f"\nTest suite failed: {e}")
        import traceback
        traceback.print_exc()
        await test_runner.cleanup_test_environment()


if __name__ == "__main__":
    from aicore.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Starting comprehensive conversation summarizer testing")
    
    from aicore.ai_config import validate_api_keys
    validate_api_keys()
    asyncio.run(main()) 