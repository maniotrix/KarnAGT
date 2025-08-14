#!/usr/bin/env python3
"""
Conversation Context Builder - Validation Test

This script tests the context builder with multiple token limits and validates:
1. Which messages get summarized vs included
2. String comparison of preserved messages
3. Token counting accuracy
4. Pair integrity validation

No file exports - direct in-memory validation with detailed output.
"""

import asyncio
import sys
from pathlib import Path

# Add the app to the Python path
sys.path.append(str(Path(__file__).parent))

# Environment and imports
from tests.ai_config import validate_api_keys
from app.logging.logger import get_logger

try:
    from app.core.database import AsyncSessionLocal
    from app.models.database.conversation import Conversation
    from app.models.database.message import Message
    from app.services.context.conversation_context_builder import ConversationContextBuilder, ConversationContextConfig
    from app.services.context.utils import count_tokens
    from sqlalchemy import select
    import traceback
except ImportError as e:
    print(f"❌ Import Error: {e}")
    sys.exit(1)

logger = get_logger(__name__)

class ContextValidationTester:
    def __init__(self):
        self.db_session = None
        self.test_conversation_id = "ac70e87f-6f96-40d0-bfac-f5d71e45b67a"
        
    async def run_validation_tests(self):
        """Run comprehensive validation tests"""
        print("🧪 Context Builder Validation Tests")
        print("=" * 60)
        
        try:
            await self.setup_database()
            
            # Get original messages for comparison
            original_messages = await self.get_original_messages()
            if not original_messages:
                print("❌ No messages found for testing")
                return
                
            print(f"📋 Testing with {len(original_messages)} original messages")
            print(f"    Total original tokens: {sum(count_tokens(str(msg.content)) for msg in original_messages):,}")
            
            # Test scenarios with different token limits
            test_scenarios = [
                ("Tiny Limit", 100, "Forces immediate summarization"),
                ("Small Limit", 500, "Forces summarization of most content"),
                ("Medium Limit", 1500, "May include some recent messages"),
                ("Large Limit", 3000, "Should include most/all messages"),
                ("Huge Limit", 10000, "Should include everything"),
            ]
            
            test_message = "Can you help me with one more Python question about decorators?"
            
            for name, token_limit, description in test_scenarios:
                print(f"\n{'='*60}")
                print(f"🔬 {name}: {token_limit} tokens")
                print(f"   {description}")
                print("-" * 60)
                
                await self.validate_scenario(original_messages, test_message, token_limit)
                
        except Exception as e:
            print(f"❌ Error during validation: {e}")
            traceback.print_exc()
        finally:
            await self.cleanup()
    
    async def setup_database(self):
        """Setup database connection"""
        self.db_session = AsyncSessionLocal()
        
    async def get_original_messages(self):
        """Get original messages for comparison"""
        conv_query = select(Conversation).where(
            Conversation.conversation_id == self.test_conversation_id
        )
        conv_result = await self.db_session.execute(conv_query)
        conversation = conv_result.scalar_one_or_none()
        
        if not conversation:
            return []
        
        # Get messages in reverse chronological order (newest first, like the algorithm)
        messages_query = select(Message).where(
            Message.conversation_id == conversation.id
        ).order_by(Message.created_at.desc())
        
        messages_result = await self.db_session.execute(messages_query)
        return list(messages_result.scalars().all())
    
    async def validate_scenario(self, original_messages, test_message, token_limit):
        """Validate a specific token limit scenario"""
        
        # Configure and build context
        config = ConversationContextConfig(
            summary_length="brief",
            summary_max_tokens=200,
            fixed_llm_conversation_tokens=token_limit
        )
        
        builder = ConversationContextBuilder(config, self.db_session, self.test_conversation_id)
        built_context = await builder.build_context(test_message)
        
        # Analyze results
        total_context_tokens = sum(count_tokens(msg['content']) for msg in built_context)
        has_summary = any(msg.get('role') == 'system' and 'summary' in msg.get('content', '').lower() 
                         for msg in built_context)
        
        print(f"📊 Results:")
        print(f"   Context messages: {len(built_context)}")
        print(f"   Context tokens: {total_context_tokens:,}")
        print(f"   Token limit: {token_limit:,}")
        print(f"   Within limit: {'✅' if total_context_tokens <= token_limit else '❌'}")
        print(f"   Has summary: {'✅' if has_summary else '❌'}")
        
        if has_summary:
            await self.validate_summarization_scenario(original_messages, built_context, test_message)
        else:
            await self.validate_no_summarization_scenario(original_messages, built_context, test_message)
    
    async def validate_summarization_scenario(self, original_messages, built_context, test_message):
        """Validate when summarization occurred"""
        print(f"\n📝 Summarization Analysis:")
        
        # Find the summary message
        summary_msg = next((msg for msg in built_context if msg.get('role') == 'system'), None)
        if summary_msg:
            summary_tokens = count_tokens(summary_msg['content'])
            print(f"   Summary tokens: {summary_tokens}")
            print(f"   Summary preview: {summary_msg['content'][:100]}...")
        
        # Find included messages (exclude summary and test message)
        included_messages = [msg for msg in built_context[1:-1]]  # Skip summary and test message
        
        print(f"   Original messages: {len(original_messages)}")
        print(f"   Included messages: {len(included_messages)}")
        print(f"   Summarized messages: {len(original_messages) - len(included_messages)}")
        
        # Validate included messages match original (in reverse order)
        if included_messages:
            print(f"\n🔍 Validating included messages:")
            for i, context_msg in enumerate(included_messages):
                # Context messages are in chronological order (oldest first)
                # But original_messages are in reverse chronological order (newest first)
                # So we need to map: context_msg[i] should match original_messages[len(included_messages)-1-i]
                original_index = len(included_messages) - 1 - i
                original_msg = original_messages[original_index]
                
                role_match = context_msg['role'] == str(original_msg.role)
                content_match = context_msg['content'] == str(original_msg.content)
                
                status = "✅" if (role_match and content_match) else "❌"
                print(f"   {i+1:2d}. {status} {context_msg['role']:9s} | {count_tokens(context_msg['content']):4d} tokens")
                
                if not role_match:
                    print(f"        ❌ Role mismatch: '{context_msg['role']}' vs '{original_msg.role}'")
                if not content_match:
                    print(f"        ❌ Content mismatch")
                    print(f"           Expected: {str(original_msg.content)[:50]}...")
                    print(f"           Got:      {context_msg['content'][:50]}...")
        else:
            print(f"   ✅ All messages were summarized (expected for very small token limits)")
    
    async def validate_no_summarization_scenario(self, original_messages, built_context, test_message):
        """Validate when no summarization occurred"""
        print(f"\n📋 No Summarization Analysis:")
        
        # All messages except the test message should match original messages
        included_messages = built_context[:-1]  # Exclude test message
        
        print(f"   Original messages: {len(original_messages)}")
        print(f"   Included messages: {len(included_messages)}")
        
        if len(included_messages) != len(original_messages):
            print(f"   ❌ Message count mismatch!")
            return
        
        print(f"\n🔍 Validating all messages included correctly:")
        all_match = True
        
        for i, context_msg in enumerate(included_messages):
            original_msg = original_messages[len(original_messages) - 1 - i]  # Reverse order
            
            role_match = context_msg['role'] == str(original_msg.role)
            content_match = context_msg['content'] == str(original_msg.content)
            
            status = "✅" if (role_match and content_match) else "❌"
            print(f"   {i+1:2d}. {status} {context_msg['role']:9s} | {count_tokens(context_msg['content']):4d} tokens")
            
            if not (role_match and content_match):
                all_match = False
                if not role_match:
                    print(f"        ❌ Role mismatch: '{context_msg['role']}' vs '{original_msg.role}'")
                if not content_match:
                    print(f"        ❌ Content mismatch")
        
        if all_match:
            print(f"   ✅ All messages match perfectly!")
        
        # Validate pair integrity
        await self.validate_pair_integrity(included_messages)
    
    async def validate_pair_integrity(self, messages):
        """Validate that messages form proper user-assistant pairs"""
        print(f"\n👥 Pair Integrity Analysis:")
        
        pairs = []
        current_pair = []
        
        # Group into pairs (reverse order, so start from oldest)
        for msg in reversed(messages):
            if msg['role'] == 'user':
                if current_pair:
                    pairs.append(current_pair)
                current_pair = [msg]
            elif msg['role'] == 'assistant':
                if current_pair:
                    current_pair.append(msg)
                    pairs.append(current_pair)
                    current_pair = []
                else:
                    # Standalone assistant message
                    pairs.append([msg])
        
        if current_pair:
            pairs.append(current_pair)
        
        print(f"   Total pairs: {len(pairs)}")
        
        for i, pair in enumerate(pairs, 1):
            if len(pair) == 2:
                print(f"   {i:2d}. ✅ Complete pair: {pair[0]['role']} → {pair[1]['role']}")
            elif len(pair) == 1:
                print(f"   {i:2d}. ⚠️  Incomplete: {pair[0]['role']} only")
            else:
                print(f"   {i:2d}. ❌ Invalid pair length: {len(pair)}")
    
    async def cleanup(self):
        """Cleanup database session"""
        if self.db_session:
            await self.db_session.close()
            print(f"\n🧹 Database session closed")

async def main():
    """Main function"""
    tester = ContextValidationTester()
    await tester.run_validation_tests()
    print(f"\n🎉 Validation tests completed!")

if __name__ == "__main__":
    logger.info("Starting context builder validation tests")
    validate_api_keys()
    asyncio.run(main()) 