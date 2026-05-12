#!/usr/bin/env python3
"""
Conversation Context Builder - Export Analysis Test

This script:
1. Exports all original messages from a conversation (oldest to latest)
2. Builds context using small token limit (forces summarization)  
3. Exports the final built context
4. Creates readable comparison files for analysis

Usage: python test_context_builder_export.py [conversation_id]
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the app to the Python path
sys.path.append(str(Path(__file__).parent))

# Environment and imports
from tests.ai_config import validate_api_keys
from app.logging.logger import get_logger

try:
    from app.core.config import settings
    from app.core.database import AsyncSessionLocal
    from app.models.database.conversation import Conversation
    from app.models.database.message import Message
    from app.services.context.conversation_context_builder import ConversationContextBuilder, ConversationContextConfig
    from app.services.context.utils import count_tokens
    from sqlalchemy import select
    import traceback
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Make sure you're running from the backend directory and all dependencies are installed")
    sys.exit(1)

logger = get_logger(__name__)

class ContextBuilderExportAnalyzer:
    def __init__(self):
        self.db_session = None
        self.output_dir = Path("context_analysis_output")
        self.output_dir.mkdir(exist_ok=True)
        
    async def analyze_conversation(self, conversation_id: str = None):
        """Main analysis workflow"""
        print("🔍 Conversation Context Builder - Export Analysis")
        print("=" * 60)
        
        try:
            # Setup database
            await self.setup_database()
            
            # Use provided conversation_id or find one
            if not conversation_id:
                conversation_id = await self.find_test_conversation()
                if not conversation_id:
                    print("❌ No conversation found for analysis")
                    return
                    
            print(f"\n📋 Analyzing conversation: {conversation_id}")
            
            # Step 1: Export all original messages
            original_messages = await self.export_original_messages(conversation_id)
            
            if not original_messages:
                print("❌ No messages found in conversation")
                return
                
            # Step 2: Build context with small token limit
            built_context = await self.build_and_export_context(conversation_id)
            
            # Step 3: Create analysis report
            await self.create_analysis_report(conversation_id, original_messages, built_context)
            
            print(f"\n✅ Analysis complete! Check the '{self.output_dir}' directory:")
            print(f"   📄 {self.output_dir}/original_messages.json")
            print(f"   📄 {self.output_dir}/built_context.json") 
            print(f"   📄 {self.output_dir}/analysis_report.txt")
            
        except Exception as e:
            print(f"❌ Error during analysis: {e}")
            traceback.print_exc()
        finally:
            await self.cleanup()
    
    async def setup_database(self):
        """Setup database connection"""
        print("\n🗄️  Setting up database connection...")
        self.db_session = AsyncSessionLocal()
        print("  ✅ Database session created")
        
    async def find_test_conversation(self):
        """Find a conversation with messages for testing"""
        print("🔍 Finding test conversation...")
        
        # Find conversation with messages
        query = select(Conversation).join(Message).limit(1)
        result = await self.db_session.execute(query)
        conversation = result.scalar_one_or_none()
        
        if conversation:
            print(f"  ✅ Found conversation: {conversation.conversation_id}")
            print(f"     Title: {conversation.title or 'Untitled'}")
            return conversation.conversation_id
        return None
    
    async def export_original_messages(self, conversation_id: str):
        """Export all original messages in chronological order"""
        print(f"\n📤 Exporting original messages...")
        
        # Get conversation
        conv_query = select(Conversation).where(
            Conversation.conversation_id == conversation_id
        )
        conv_result = await self.db_session.execute(conv_query)
        conversation = conv_result.scalar_one_or_none()
        
        if not conversation:
            print("  ❌ Conversation not found")
            return []
        
        # Get messages in chronological order (oldest first)
        messages_query = select(Message).where(
            Message.conversation_id == conversation.id
        ).order_by(Message.created_at.asc())  # Oldest first for export
        
        messages_result = await self.db_session.execute(messages_query)
        messages = list(messages_result.scalars().all())
        
        print(f"  ✅ Found {len(messages)} messages")
        
        # Convert to exportable format
        exported_messages = []
        total_tokens = 0
        
        for i, msg in enumerate(messages, 1):
            tokens = count_tokens(msg.content)
            total_tokens += tokens
            
            message_data = {
                "sequence": i,
                "role": msg.role,
                "content": msg.content,
                "tokens": tokens,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
                "message_id": str(msg.message_id) if msg.message_id else None
            }
            exported_messages.append(message_data)
        
        # Save to JSON file
        export_data = {
            "conversation_id": conversation_id,
            "conversation_title": conversation.title,
            "total_messages": len(messages),
            "total_tokens": total_tokens,
            "exported_at": datetime.now().isoformat(),
            "messages": exported_messages
        }
        
        output_file = self.output_dir / "original_messages.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"  ✅ Exported to: {output_file}")
        print(f"     Total messages: {len(messages)}")
        print(f"     Total tokens: {total_tokens}")
        
        # Also create a readable text version
        text_file = self.output_dir / "original_messages.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(f"Original Messages - Conversation: {conversation_id}\n")
            f.write(f"Title: {conversation.title or 'Untitled'}\n")
            f.write(f"Total Messages: {len(messages)}\n")
            f.write(f"Total Tokens: {total_tokens}\n")
            f.write("=" * 80 + "\n\n")
            
            for i, msg in enumerate(messages, 1):
                tokens = count_tokens(msg.content)
                f.write(f"Message {i:2d} | {msg.role:9s} | {tokens:4d} tokens | {msg.created_at}\n")
                f.write("-" * 80 + "\n")
                f.write(f"{msg.content}\n")
                f.write("\n" + "=" * 80 + "\n\n")
        
        print(f"  ✅ Readable version: {text_file}")
        
        return exported_messages
    
    async def build_and_export_context(self, conversation_id: str):
        """Build context and export the result"""
        print(f"\n🏗️  Building context with small token limit...")
        
        # Use small token limit to force summarization
        config = ConversationContextConfig(
            summary_length="brief",
            summary_max_tokens=200,
            fixed_llm_conversation_tokens=1500  # Small limit to force summarization
        )
        
        builder = ConversationContextBuilder(config, self.db_session, conversation_id)
        
        # Build context
        test_message = "Can you help me with one more Python question about decorators?"
        context = await builder.build_context(test_message)
        
        print(f"  ✅ Context built with {len(context)} messages")
        
        # Calculate tokens for each message
        total_tokens = 0
        context_with_tokens = []
        
        for i, msg in enumerate(context, 1):
            tokens = count_tokens(msg['content'])
            total_tokens += tokens
            
            context_msg = {
                "sequence": i,
                "role": msg['role'],
                "content": msg['content'],
                "tokens": tokens,
                "is_summary": msg.get('role') == 'system' and 'summary' in msg.get('content', '').lower()
            }
            context_with_tokens.append(context_msg)
        
        # Export to JSON
        export_data = {
            "conversation_id": conversation_id,
            "config": {
                "summary_length": config.summary_length,
                "summary_max_tokens": config.summary_max_tokens,
                "fixed_llm_conversation_tokens": config.fixed_llm_conversation_tokens
            },
            "test_message": test_message,
            "built_at": datetime.now().isoformat(),
            "total_context_messages": len(context),
            "total_context_tokens": total_tokens,
            "has_summary": any(msg.get('is_summary', False) for msg in context_with_tokens),
            "context": context_with_tokens
        }
        
        output_file = self.output_dir / "built_context.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"  ✅ Exported to: {output_file}")
        print(f"     Context messages: {len(context)}")
        print(f"     Context tokens: {total_tokens}")
        print(f"     Has summary: {'Yes' if export_data['has_summary'] else 'No'}")
        
        # Create readable text version
        text_file = self.output_dir / "built_context.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(f"Built Context - Conversation: {conversation_id}\n")
            f.write(f"Token Limit: {config.fixed_llm_conversation_tokens}\n")
            f.write(f"Test Message: {test_message}\n")
            f.write(f"Total Context Messages: {len(context)}\n")
            f.write(f"Total Context Tokens: {total_tokens}\n")
            f.write(f"Has Summary: {'Yes' if export_data['has_summary'] else 'No'}\n")
            f.write("=" * 80 + "\n\n")
            
            for msg in context_with_tokens:
                role_icon = "🤖" if msg['role'] == 'assistant' else "👤" if msg['role'] == 'user' else "⚙️"
                f.write(f"Context {msg['sequence']:2d} | {role_icon} {msg['role']:9s} | {msg['tokens']:4d} tokens")
                if msg.get('is_summary'):
                    f.write(" | 📝 SUMMARY")
                f.write("\n")
                f.write("-" * 80 + "\n")
                f.write(f"{msg['content']}\n")
                f.write("\n" + "=" * 80 + "\n\n")
        
        print(f"  ✅ Readable version: {text_file}")
        
        return context_with_tokens
    
    async def create_analysis_report(self, conversation_id: str, original_messages, built_context):
        """Create a comparison analysis report"""
        print(f"\n📊 Creating analysis report...")
        
        # Calculate statistics
        original_count = len(original_messages)
        original_tokens = sum(msg['tokens'] for msg in original_messages)
        
        context_count = len(built_context)
        context_tokens = sum(msg['tokens'] for msg in built_context)
        
        has_summary = any(msg.get('is_summary', False) for msg in built_context)
        summary_msg = next((msg for msg in built_context if msg.get('is_summary', False)), None)
        
        # Count message pairs in original
        user_messages = [msg for msg in original_messages if msg['role'] == 'user']
        assistant_messages = [msg for msg in original_messages if msg['role'] == 'assistant']
        
        # Create report
        report_file = self.output_dir / "analysis_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("CONVERSATION CONTEXT BUILDER - ANALYSIS REPORT\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Conversation ID: {conversation_id}\n")
            f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Token Limit Used: 1500 tokens\n\n")
            
            f.write("ORIGINAL CONVERSATION STATISTICS\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total Messages: {original_count}\n")
            f.write(f"User Messages: {len(user_messages)}\n")
            f.write(f"Assistant Messages: {len(assistant_messages)}\n")
            f.write(f"Total Tokens: {original_tokens:,}\n\n")
            
            f.write("BUILT CONTEXT STATISTICS\n")
            f.write("-" * 40 + "\n")
            f.write(f"Context Messages: {context_count}\n")
            f.write(f"Context Tokens: {context_tokens:,}\n")
            f.write(f"Has Summary: {'Yes' if has_summary else 'No'}\n")
            if summary_msg:
                f.write(f"Summary Tokens: {summary_msg['tokens']}\n")
            f.write("\n")
            
            f.write("TRANSFORMATION ANALYSIS\n")
            f.write("-" * 40 + "\n")
            f.write(f"Messages Reduced: {original_count} → {context_count} ({original_count - context_count} removed)\n")
            f.write(f"Tokens Reduced: {original_tokens:,} → {context_tokens:,} ({original_tokens - context_tokens:,} saved)\n")
            f.write(f"Compression Ratio: {(context_tokens / original_tokens * 100):.1f}%\n")
            f.write(f"Token Limit Respected: {'✅' if context_tokens <= 1500 else '❌'}\n\n")
            
            if has_summary:
                f.write("SUMMARIZATION ANALYSIS\n")
                f.write("-" * 40 + "\n")
                f.write("✅ Summarization was triggered\n")
                f.write(f"Summary Length: {summary_msg['tokens']} tokens\n")
                f.write("Summary Preview:\n")
                f.write(summary_msg['content'][:200] + "...\n\n")
            else:
                f.write("NO SUMMARIZATION NEEDED\n")
                f.write("-" * 40 + "\n")
                f.write("✅ All messages fit within token limit\n\n")
            
            f.write("MESSAGE INCLUSION BREAKDOWN\n")
            f.write("-" * 40 + "\n")
            
            # Analyze which messages were included/excluded
            if has_summary:
                f.write("Summarized messages: (old messages beyond token limit)\n")
                # Calculate how many were summarized vs included
                non_summary_context = [msg for msg in built_context if not msg.get('is_summary', False)]
                messages_in_context = len(non_summary_context) - 1  # Subtract test message
                messages_summarized = original_count - messages_in_context
                f.write(f"  - {messages_summarized} messages summarized\n")
                f.write(f"  - {messages_in_context} recent messages included directly\n")
            else:
                f.write("All messages included directly (no summarization)\n")
            
            f.write("\nFILES GENERATED\n")
            f.write("-" * 40 + "\n")
            f.write("📄 original_messages.json - Complete original conversation\n")
            f.write("📄 original_messages.txt  - Human-readable original messages\n")
            f.write("📄 built_context.json     - Final context sent to LLM\n")
            f.write("📄 built_context.txt      - Human-readable context\n")
            f.write("📄 analysis_report.txt    - This analysis report\n")
        
        print(f"  ✅ Report created: {report_file}")
        
    async def cleanup(self):
        """Cleanup database session"""
        if self.db_session:
            await self.db_session.close()
            print("\n🧹 Database session closed")

async def main():
    """Main function"""
    conversation_id = None
    if len(sys.argv) > 1:
        conversation_id = sys.argv[1]
        print(f"Using provided conversation ID: {conversation_id}")
    
    analyzer = ContextBuilderExportAnalyzer()
    await analyzer.analyze_conversation(conversation_id)

if __name__ == "__main__":
    logger.info("Starting conversation context builder export analysis")
    
    # Validate API keys and environment
    validate_api_keys()
    
    # Run analysis
    asyncio.run(main()) 