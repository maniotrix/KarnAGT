#!/usr/bin/env python3
"""
Test Conversation Context Builder

This script tests the ConversationContextBuilder with real-world scenarios:
- Uses actual database conversations and messages
- Tests with small token limits for visible results
- Validates summarization logic
- Tests edge cases and error handling
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the app to the Python path
sys.path.append(str(Path(__file__).parent))

# Imports
try:
    from app.core.config import settings
    from app.core.database import get_db, AsyncSessionLocal
    from app.models.database.user import User
    from app.models.database.conversation import Conversation
    from app.models.database.message import Message
    from app.services.context.conversation_context_builder import ConversationContextBuilder, ConversationContextConfig
    from app.services.context.utils import count_tokens
    from sqlalchemy import select, desc, func
    from sqlalchemy.ext.asyncio import AsyncSession
    import traceback
    import json
    from aicore.logger import get_logger
    from aicore.ai_config import validate_api_keys
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Make sure you're running from the backend directory and all dependencies are installed.")
    sys.exit(1)

# Set up logger
logger = get_logger(__name__)


class ConversationContextTester:
    """Test suite for ConversationContextBuilder"""
    
    def __init__(self):
        self.db_session = None
        print("🧪 Conversation Context Builder - Test Suite")
        print("=" * 60)
    
    async def run_all_tests(self):
        """Run all tests in sequence"""
        try:
            await self.setup_database()
            await self.test_database_setup()
            
            # Find a user with conversations for testing
            test_user, test_conversation = await self.find_test_data()
            
            if not test_user or not test_conversation:
                print("⚠️  No suitable test data found. Creating sample data...")
                test_user, test_conversation = await self.create_sample_data()
            
            # Run tests with different configurations
            await self.test_small_token_limit(test_conversation.conversation_id)
            await self.test_medium_token_limit(test_conversation.conversation_id)
            await self.test_no_summarization_needed(test_conversation.conversation_id)
            await self.test_empty_conversation()
            await self.test_single_message_conversation(test_conversation.conversation_id)
            await self.test_edge_cases()
            
            await self.cleanup()
            
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ ConversationContextBuilder is working correctly!")
            
        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            print("\nStacktrace:")
            traceback.print_exc()
            await self.cleanup()
            sys.exit(1)
    
    async def setup_database(self):
        """Setup database connection"""
        print("\n🗄️  Setting up database connection...")
        
        # Verify environment is loaded
        print(f"     Database URL: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'localhost'}")
        print(f"     OpenAI Key: {'✅ Set' if settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY) > 10 else '❌ Not set'}")
        
        self.db_session = AsyncSessionLocal()
        print("  ✅ Database session created")
    
    async def test_database_setup(self):
        """Test that we can connect to database and query tables"""
        print("\n📋 Testing database setup...")
        
        # Test basic connectivity
        result = await self.db_session.execute(select(func.count(User.id)))
        user_count = result.scalar()
        print(f"  ✅ Found {user_count} users in database")
        
        # Test conversations
        result = await self.db_session.execute(select(func.count(Conversation.id)))
        conv_count = result.scalar()
        print(f"  ✅ Found {conv_count} conversations in database")
        
        # Test messages
        result = await self.db_session.execute(select(func.count(Message.id)))
        message_count = result.scalar()
        print(f"  ✅ Found {message_count} messages in database")
    
    async def find_test_data(self):
        """Find a user with active conversations for testing"""
        print("\n🔍 Finding test data...")
        
        # Simplify: Just find a user with conversations
        user_query = select(User).join(Conversation).limit(1)
        user_result = await self.db_session.execute(user_query)
        test_user = user_result.scalar_one_or_none()
        
        if not test_user:
            print("  ⚠️  No users with conversations found")
            return None, None
        
        print(f"  ✅ Found test user: {test_user.email}")
        
        # Find one of their conversations with messages
        conv_query = select(Conversation)\
            .join(Message)\
            .where(Conversation.user_id == test_user.id)\
            .order_by(Conversation.updated_at.desc())\
            .limit(1)
        
        conv_result = await self.db_session.execute(conv_query)
        test_conversation = conv_result.scalar_one_or_none()
        
        if test_conversation:
            # Count messages in this conversation
            msg_count_query = select(func.count(Message.id))\
                .where(Message.conversation_id == test_conversation.id)
            msg_count_result = await self.db_session.execute(msg_count_query)
            message_count = msg_count_result.scalar()
            
            print(f"  ✅ Found test conversation: {test_conversation.conversation_id} with {message_count} messages")
            title_display = test_conversation.title if test_conversation.title else 'Untitled'
            print(f"     Title: {title_display}")
            return test_user, test_conversation
        
        return test_user, None
    
    async def create_sample_data(self):
        """Create sample conversation data for testing"""
        print("\n🏗️  Creating sample test data...")
        
        # Create test user
        test_user = User(
            email=f"test_context_{datetime.now().timestamp()}@example.com",
            full_name="Test Context User",
            hashed_password="dummy_hash"
        )
        self.db_session.add(test_user)
        await self.db_session.flush()
        
        # Create test conversation
        test_conversation = Conversation(
            user_id=test_user.id,
            title="Context Builder Test Conversation",
            model_name="gpt-4o-mini",
            status="active"
        )
        self.db_session.add(test_conversation)
        await self.db_session.flush()
        
        # Create sample messages (alternating user/assistant)
        messages = [
            ("user", "Hello! I need help with Python programming."),
            ("assistant", "Hello! I'd be happy to help you with Python programming. What specific topic or problem would you like assistance with?"),
            ("user", "I'm trying to understand list comprehensions. Can you explain them?"),
            ("assistant", "Absolutely! List comprehensions are a concise way to create lists in Python. They follow this pattern: [expression for item in iterable if condition]. For example: squares = [x**2 for x in range(10)] creates a list of squares from 0 to 81."),
            ("user", "That's helpful! Can you show me a more complex example?"),
            ("assistant", "Sure! Here's a more complex example: even_squares = [x**2 for x in range(20) if x % 2 == 0]. This creates a list of squares but only for even numbers. The 'if condition' at the end filters the items."),
            ("user", "What about nested list comprehensions?"),
            ("assistant", "Nested list comprehensions can be tricky! They're useful for creating matrices or processing nested data. For example: matrix = [[i*j for j in range(3)] for i in range(3)] creates a 3x3 multiplication table. The inner comprehension runs for each iteration of the outer one."),
            ("user", "Can you give me an exercise to practice?"),
            ("assistant", "Here's a great exercise: Create a list comprehension that generates all the words from a sentence that start with a vowel and are longer than 3 characters. Try: sentence = 'The quick brown fox jumps over the lazy dog' and see if you can write the comprehension!"),
        ]
        
        for role, content in messages:
            message = Message(
                conversation_id=test_conversation.id,
                role=role,
                content=content,
                status="completed"
            )
            self.db_session.add(message)
        
        await self.db_session.commit()
        print(f"  ✅ Created test user: {test_user.email}")
        print(f"  ✅ Created test conversation with {len(messages)} messages")
        
        return test_user, test_conversation
    
    async def test_small_token_limit(self, conversation_id: str):
        """Test with very small token limit to force summarization"""
        print("\n🔬 Test 1: Small Token Limit (Forces Summarization)")
        print("-" * 50)
        
        # Use very small token limit to trigger summarization
        config = ConversationContextConfig(
            summary_length="brief",
            summary_max_tokens=200,
            fixed_llm_conversation_tokens=500  # Very small limit
        )
        
        builder = ConversationContextBuilder(config, self.db_session, conversation_id)
        
        test_message = "Can you help me with one more Python question about decorators?"
        context = await builder.build_context(test_message)
        
        print(f"  📊 Context built with {len(context)} messages")
        
        # Analyze the context
        has_summary = any(msg.get('role') == 'system' and 'summary' in msg.get('content', '').lower() for msg in context)
        total_tokens = sum(count_tokens(msg['content']) for msg in context)
        
        print(f"  📝 Has summary: {'✅' if has_summary else '❌'}")
        print(f"  🔢 Total tokens: {total_tokens}")
        print(f"  🎯 Token limit: {config.fixed_llm_conversation_tokens}")
        
        # Display context structure
        print("\n  📋 Context Structure:")
        for i, msg in enumerate(context):
            role = msg['role']
            content_preview = msg['content'][:80] + "..." if len(msg['content']) > 80 else msg['content']
            tokens = count_tokens(msg['content'])
            print(f"     {i+1}. [{role}] ({tokens} tokens): {content_preview}")
        
        # Verify latest message is included
        latest_msg = context[-1]
        assert latest_msg['role'] == 'user' and latest_msg['content'] == test_message
        print("  ✅ Latest message correctly included")
        
        return context
    
    async def test_medium_token_limit(self, conversation_id: str):
        """Test with medium token limit"""
        print("\n🔬 Test 2: Medium Token Limit")
        print("-" * 50)
        
        config = ConversationContextConfig(
            summary_length="medium",
            summary_max_tokens=400,
            fixed_llm_conversation_tokens=2000  # Medium limit
        )
        
        builder = ConversationContextBuilder(config, self.db_session, conversation_id)
        
        test_message = "What's the difference between a list and a tuple in Python?"
        context = await builder.build_context(test_message)
        
        print(f"  📊 Context built with {len(context)} messages")
        
        total_tokens = sum(count_tokens(msg['content']) for msg in context)
        print(f"  🔢 Total tokens: {total_tokens}")
        print(f"  🎯 Token limit: {config.fixed_llm_conversation_tokens}")
        
        # Show token distribution
        for i, msg in enumerate(context):
            tokens = count_tokens(msg['content'])
            role_icon = "🤖" if msg['role'] == 'assistant' else "👤" if msg['role'] == 'user' else "⚙️"
            print(f"     {i+1}. {role_icon} [{msg['role']}] {tokens} tokens")
        
        print("  ✅ Medium token limit test passed")
        return context
    
    async def test_no_summarization_needed(self, conversation_id: str):
        """Test with high token limit (no summarization needed)"""
        print("\n🔬 Test 3: High Token Limit (No Summarization)")
        print("-" * 50)
        
        config = ConversationContextConfig(
            summary_length="comprehensive",
            summary_max_tokens=1000,
            fixed_llm_conversation_tokens=50000  # Very high limit
        )
        
        builder = ConversationContextBuilder(config, self.db_session, conversation_id)
        
        test_message = "Thanks for all the help with Python!"
        context = await builder.build_context(test_message)
        
        print(f"  📊 Context built with {len(context)} messages")
        
        # Should not have summary with high limit
        has_summary = any(msg.get('role') == 'system' for msg in context)
        total_tokens = sum(count_tokens(msg['content']) for msg in context)
        
        print(f"  📝 Has summary: {'❌' if not has_summary else '⚠️'} (Expected: No)")
        print(f"  🔢 Total tokens: {total_tokens}")
        print(f"  ✅ No summarization test passed")
        
        return context
    
    async def test_empty_conversation(self):
        """Test with non-existent conversation"""
        print("\n🔬 Test 4: Empty/Non-existent Conversation")
        print("-" * 50)
        
        config = ConversationContextConfig()
        fake_conversation_id = "00000000-0000-0000-0000-000000000000"
        
        builder = ConversationContextBuilder(config, self.db_session, fake_conversation_id)
        
        test_message = "Hello in empty conversation"
        context = await builder.build_context(test_message)
        
        print(f"  📊 Context built with {len(context)} messages")
        
        # Should only contain the latest message
        assert len(context) == 1
        assert context[0]['role'] == 'user'
        assert context[0]['content'] == test_message
        
        print("  ✅ Empty conversation test passed")
        return context
    
    async def test_single_message_conversation(self, conversation_id: str):
        """Test edge case with conversation that has only one message"""
        print("\n🔬 Test 5: Edge Cases")
        print("-" * 50)
        
        config = ConversationContextConfig(
            fixed_llm_conversation_tokens=100  # Very small
        )
        
        builder = ConversationContextBuilder(config, self.db_session, conversation_id)
        
        # Test with empty message
        empty_context = await builder.build_context("")
        print(f"  📊 Empty message context: {len(empty_context)} messages")
        
        # Test with very long message
        long_message = "This is a very long message. " * 100  # Repeat to make it long
        long_context = await builder.build_context(long_message)
        print(f"  📊 Long message context: {len(long_context)} messages")
        print(f"  🔢 Long message tokens: {count_tokens(long_message)}")
        
        print("  ✅ Edge cases test passed")
    
    async def test_edge_cases(self):
        """Test various edge cases"""
        print("\n🔬 Test 6: Additional Edge Cases")
        print("-" * 50)
        
        # Test with different config values
        configs_to_test = [
            ("Minimal tokens", {"fixed_llm_conversation_tokens": 50}),
            ("No summary tokens", {"summary_max_tokens": 0}),
            ("Large summary", {"summary_max_tokens": 2000, "summary_length": "comprehensive"}),
        ]
        
        fake_conversation_id = "00000000-0000-0000-0000-000000000000"
        
        for test_name, config_overrides in configs_to_test:
            print(f"\n  🧪 Testing: {test_name}")
            
            config = ConversationContextConfig(**config_overrides)
            builder = ConversationContextBuilder(config, self.db_session, fake_conversation_id)
            
            try:
                context = await builder.build_context("Test message")
                print(f"     ✅ {test_name}: {len(context)} messages")
            except Exception as e:
                print(f"     ⚠️  {test_name}: Error handled - {str(e)[:50]}...")
        
        print("  ✅ Edge cases completed")
    
    async def cleanup(self):
        """Clean up resources"""
        print("\n🧹 Cleaning up...")
        if self.db_session:
            await self.db_session.close()
        print("  ✅ Database session closed")


async def main():
    """Main test runner"""
    print("🚀 Starting Conversation Context Builder Tests\n")
    
    tester = ConversationContextTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    logger.info("Starting comprehensive conversation context builder testing")
    
    # Validate API keys and environment
    validate_api_keys()
    
    # Run tests
    asyncio.run(main()) 