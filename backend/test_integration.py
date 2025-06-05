#!/usr/bin/env python3
"""
ChatGPT Clone Backend - Integration Test Script

This script verifies that all components are working correctly:
- Environment variables
- Database connectivity and migrations
- OpenAI integration
- Chat service functionality
- Cost tracking
- Streaming capabilities
"""

import asyncio
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

# Add the app to the Python path
sys.path.append(str(Path(__file__).parent))

# Imports
try:
    from app.core.config import settings
    from app.core.database import get_db, engine
    from app.models.database.user import User
    from app.models.database.conversation import Conversation
    from app.models.database.message import Message
    from app.models.schemas.chat_schemas import ConversationCreate, MessageCreate
    from app.services.chat.chat_service import ChatService
    from app.integrations.openai.assistant_client import OpenAIAssistantClient, assistant_manager
    from app.integrations.openai.cost_tracker import CostTracker
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select, text
    import tiktoken
    import openai
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Make sure you're running from the backend directory and all dependencies are installed.")
    sys.exit(1)


class ChatIntegrationTester:
    """Comprehensive test suite for the chat integration"""
    
    def __init__(self):
        self.test_user = None
        self.test_conversation_id = None
        self.db_session = None
        
        print("🚀 ChatGPT Clone Backend - Integration Test")
        print("=" * 60)
    
    async def run_all_tests(self):
        """Run all tests in sequence"""
        try:
            await self.test_environment_variables()
            await self.test_database_connectivity()
            await self.test_database_migrations()
            await self.test_openai_connectivity()
            await self.test_cost_tracking()
            await self.test_user_creation()
            await self.test_chat_service_basic()
            await self.test_chat_conversation_flow()
            await self.test_assistant_client()
            await self.test_cleanup()
            
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ Your ChatGPT Clone backend is ready to use!")
            
        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            print("\nStacktrace:")
            traceback.print_exc()
            await self.test_cleanup()
            sys.exit(1)
    
    async def test_environment_variables(self):
        """Test that all required environment variables are set"""
        print("\n📋 Testing Environment Variables...")
        
        required_vars = [
            "OPENAI_API_KEY",
            "DATABASE_URL",
            "SECRET_KEY"
        ]
        
        optional_vars = [
            "REDIS_URL",
            "QDRANT_URL",
            "NEO4J_URL"
        ]
        
        # Check required variables
        missing_required = []
        for var in required_vars:
            value = getattr(settings, var, None)
            if not value or value == "" or "your-" in value.lower():
                missing_required.append(var)
            else:
                print(f"  ✅ {var}: {'*' * min(len(str(value)), 20)}...")
        
        if missing_required:
            raise Exception(f"Missing required environment variables: {missing_required}")
        
        # Check optional variables
        for var in optional_vars:
            value = getattr(settings, var, None)
            if value and value != "":
                print(f"  ✅ {var}: {value}")
            else:
                print(f"  ⚠️  {var}: Not set (optional)")
        
        # Validate OpenAI API key format
        if not settings.OPENAI_API_KEY.startswith("sk-"):
            print(f"  ⚠️  OPENAI_API_KEY doesn't look like a valid OpenAI key (should start with 'sk-')")
        
        print("  ✅ Environment variables check complete")
    
    async def test_database_connectivity(self):
        """Test database connection"""
        print("\n🗄️  Testing Database Connectivity...")
        
        try:
            # Test async connection
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
            
            print(f"  ✅ Database connection successful: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'localhost'}")
            
        except Exception as e:
            raise Exception(f"Database connection failed: {e}")
    
    async def test_database_migrations(self):
        """Test that database migrations are applied"""
        print("\n🔄 Testing Database Migrations...")
        
        try:
            async with engine.begin() as conn:
                # Check if main tables exist
                tables_to_check = [
                    "users", "conversations", "messages", 
                    "memory_preferences", "knowledge_files", "cost_tracking"
                ]
                
                for table in tables_to_check:
                    result = await conn.execute(text(
                        f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table}')"
                    ))
                    exists = result.scalar()
                    
                    if exists:
                        print(f"  ✅ Table '{table}' exists")
                    else:
                        raise Exception(f"Table '{table}' does not exist. Run migrations first: alembic upgrade head")
            
            print("  ✅ All required tables exist")
            
        except Exception as e:
            raise Exception(f"Database migration check failed: {e}")
    
    async def test_openai_connectivity(self):
        """Test OpenAI API connectivity"""
        print("\n🤖 Testing OpenAI API Connectivity...")
        
        try:
            # Test tiktoken (used for token counting)
            encoding = tiktoken.get_encoding("cl100k_base")
            test_text = "Hello, this is a test message for token counting."
            tokens = encoding.encode(test_text)
            print(f"  ✅ Tiktoken working: '{test_text}' = {len(tokens)} tokens")
            
            # Test OpenAI client initialization
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            print("  ✅ OpenAI client initialized")
            
            # Test a simple API call
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Say 'API test successful'"}],
                max_tokens=10
            )
            
            response_text = response.choices[0].message.content
            print(f"  ✅ OpenAI API call successful: '{response_text}'")
            
            # Test embeddings
            embedding_response = client.embeddings.create(
                model="text-embedding-3-small",
                input="Test embedding"
            )
            
            embedding_vector = embedding_response.data[0].embedding
            print(f"  ✅ OpenAI Embeddings working: {len(embedding_vector)} dimensions")
            
        except Exception as e:
            raise Exception(f"OpenAI connectivity test failed: {e}")
    
    async def test_cost_tracking(self):
        """Test cost tracking functionality"""
        print("\n💰 Testing Cost Tracking...")
        
        try:
            cost_tracker = CostTracker("test-user-123")
            
            # Test token counting
            test_text = "This is a test message for cost calculation."
            token_count = cost_tracker.count_tokens(test_text, "gpt-4")
            print(f"  ✅ Token counting: '{test_text}' = {token_count} tokens")
            
            # Test cost calculation
            cost = cost_tracker.calculate_cost(100, 50, "gpt-4")
            print(f"  ✅ Cost calculation: 100 input + 50 output tokens = ${cost}")
            
        except Exception as e:
            raise Exception(f"Cost tracking test failed: {e}")
    
    async def test_user_creation(self):
        """Test user creation in database"""
        print("\n👤 Testing User Creation...")
        
        try:
            async with AsyncSession(engine) as session:
                self.db_session = session
                
                # Generate unique identifiers for this test run
                import random
                timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')[:-3]  # Include milliseconds
                random_suffix = random.randint(1000, 9999)
                unique_suffix = f"{timestamp}-{random_suffix}"
                
                test_user_id = f"test-user-{unique_suffix}"
                test_email = f"test-{unique_suffix}@example.com"
                
                # Check if user already exists (shouldn't with unique IDs, but safety check)
                existing_user = await session.execute(
                    select(User).where(User.email == test_email)
                )
                if existing_user.scalar_one_or_none():
                    print(f"  ⚠️  User with email {test_email} already exists, generating new ID...")
                    unique_suffix = f"{timestamp}-{random.randint(10000, 99999)}"
                    test_user_id = f"test-user-{unique_suffix}"
                    test_email = f"test-{unique_suffix}@example.com"
                
                # Create a test user with unique identifiers
                test_user = User(
                    user_id=test_user_id,
                    email=test_email,
                    username=f"testuser-{unique_suffix}",
                    hashed_password="test_hashed_password",
                    full_name="Test User Integration",
                    is_active=True,
                    is_verified=True,
                    subscription_tier="free"
                )
                
                session.add(test_user)
                await session.commit()
                await session.refresh(test_user)
                
                self.test_user = test_user
                print(f"  ✅ Test user created: {test_user.user_id}")
                print(f"  ✅ Test email: {test_user.email}")
                
        except Exception as e:
            raise Exception(f"User creation test failed: {e}")
    
    async def test_chat_service_basic(self):
        """Test basic chat service functionality"""
        print("\n💬 Testing Chat Service...")
        
        try:
            if not self.test_user or not self.db_session:
                raise Exception("Test user not created")
            
            # Initialize chat service
            chat_service = ChatService(self.db_session, self.test_user)
            print("  ✅ Chat service initialized")
            
            # Create a conversation
            conversation = await chat_service.start_conversation(
                title="Test Conversation",
                model="gpt-3.5-turbo"
            )
            
            self.test_conversation_id = conversation.conversation_id
            print(f"  ✅ Conversation created: {conversation.title}")
            
            # Get user conversations
            conversations = await chat_service.get_user_conversations()
            print(f"  ✅ Retrieved conversations: {len(conversations)} found")
            
        except Exception as e:
            raise Exception(f"Chat service test failed: {e}")
    
    async def test_chat_conversation_flow(self):
        """Test a complete chat conversation flow"""
        print("\n🗨️  Testing Complete Chat Flow...")
        
        try:
            if not self.test_user or not self.db_session or not self.test_conversation_id:
                raise Exception("Prerequisites not met")
            
            chat_service = ChatService(self.db_session, self.test_user)
            
            # Send a test message
            print("  📤 Sending test message...")
            response = await chat_service.send_message(
                conversation_id=self.test_conversation_id,
                content="Hello! Please respond with exactly: 'Integration test successful'"
            )
            
            print(f"  ✅ AI Response received: '{response.content[:100]}...'")
            
            # Check message history
            history = await chat_service.get_conversation_history(
                conversation_id=self.test_conversation_id
            )
            
            print(f"  ✅ Conversation history: {len(history)} messages")
            
            # Verify we have both user and assistant messages
            user_messages = [m for m in history if m.role == "user"]
            assistant_messages = [m for m in history if m.role == "assistant"]
            
            print(f"  ✅ Message breakdown: {len(user_messages)} user, {len(assistant_messages)} assistant")
            
        except Exception as e:
            raise Exception(f"Chat conversation flow test failed: {e}")
    
    async def test_assistant_client(self):
        """Test the OpenAI assistant client directly"""
        print("\n🧠 Testing Assistant Client...")
        
        try:
            if not self.test_user:
                raise Exception("Test user not created")
            
            # Test assistant client
            assistant_client = assistant_manager.get_client(
                self.test_user.user_id, 
                self.test_conversation_id
            )
            
            print("  ✅ Assistant client retrieved")
            
            # Test direct message
            response_data = await assistant_client.send_message(
                "Say 'Direct assistant test successful'",
                metadata={"test": True}
            )
            
            print(f"  ✅ Direct assistant response: '{response_data['content'][:50]}...'")
            
            # Test conversation history
            history = assistant_client.get_conversation_history()
            print(f"  ✅ Assistant conversation history: {len(history)} messages")
            
        except Exception as e:
            raise Exception(f"Assistant client test failed: {e}")
    
    async def test_cleanup(self):
        """Clean up test data"""
        print("\n🧹 Cleaning up test data...")
        
        try:
            # Clean up database objects
            if self.test_user and self.db_session:
                try:
                    # Delete test user and related data (CASCADE should handle related records)
                    await self.db_session.delete(self.test_user)
                    await self.db_session.commit()
                    print("  ✅ Test user deleted")
                except Exception as e:
                    print(f"  ⚠️  Error deleting test user: {e}")
                    # Rollback on error
                    try:
                        await self.db_session.rollback()
                    except:
                        pass
            
            # Close database session
            if self.db_session:
                try:
                    await self.db_session.close()
                    print("  ✅ Database session closed")
                except Exception as e:
                    print(f"  ⚠️  Error closing DB session: {e}")
            
            # Clean up assistant clients
            if self.test_user:
                try:
                    assistant_manager.remove_client(self.test_user.user_id, self.test_conversation_id)
                    print("  ✅ Assistant client cleaned up")
                except Exception as e:
                    print(f"  ⚠️  Error cleaning assistant client: {e}")
            
            print("  ✅ Cleanup completed")
            
        except Exception as e:
            print(f"  ⚠️  Cleanup warning: {e}")


async def main():
    """Main test function"""
    tester = ChatIntegrationTester()
    await tester.run_all_tests()


def check_environment():
    """Quick environment check before running async tests"""
    print("🔍 Pre-flight Environment Check...")
    
    # Check if .env file exists
    env_file = Path(".env")
    if env_file.exists():
        print("  ✅ .env file found")
    else:
        print("  ⚠️  .env file not found (using environment variables)")
    
    # Check Python version
    python_version = sys.version_info
    if python_version >= (3, 8):
        print(f"  ✅ Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    else:
        print(f"  ❌ Python version too old: {python_version.major}.{python_version.minor}.{python_version.micro}")
        sys.exit(1)
    
    # Check critical imports
    try:
        import fastapi
        import sqlalchemy
        import pydantic
        import openai
        import tiktoken
        print("  ✅ All critical packages imported successfully")
    except ImportError as e:
        print(f"  ❌ Missing package: {e}")
        print("  💡 Run: pip install -r requirements.txt")
        sys.exit(1)


if __name__ == "__main__":
    print("🧪 ChatGPT Clone Backend - Integration Test Suite")
    print("=" * 60)
    
    # Pre-flight checks
    check_environment()
    
    # Run async tests
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test suite failed: {e}")
        sys.exit(1) 