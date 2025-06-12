from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.context.ai_context_agent import ConversationSummarizerAgent, summarize_conversation_async
from app.services.context.utils import count_tokens
from app.models.database.conversation import Conversation
from app.models.database.message import Message
from aicore.logger import get_logger

logger = get_logger(__name__)

@dataclass
class ConversationContextConfig:
    """Configuration for conversation context building"""
    summary_length: str = "comprehensive"
    summary_max_tokens: int = 1000
    fixed_llm_conversation_tokens: int = 40000
    
    
class ConversationContextBuilder:
    def __init__(self, config: ConversationContextConfig, db_session: AsyncSession, conversation_id: str):
        self.config = config
        self.db_session = db_session
        self.conversation_id = conversation_id
        self.summarizer = ConversationSummarizerAgent()
        
        
    async def build_context(self, latest_user_message: str) -> List[Dict[str, str]]:
        """
        Build conversation context with intelligent summarization when needed.
        
        Returns a list of messages formatted for LLM consumption:
        [
            {summary of conversation history if needed},
            {user-assistant message pairs within token limit},
            {"role": "user", "content": "latest user message"}
        ]
        """
        logger.info(f"Building context for conversation {self.conversation_id}")
        
        # Step 1: Get all previous messages from database (excluding the current message)
        previous_messages = await self._get_conversation_history()
        
        if not previous_messages:
            logger.info("No previous messages found, returning only latest user message")
            return [{"role": "user", "content": latest_user_message}]
        
        # Step 2: Check if we need summarization
        overflow_index = self._get_overflow_index(previous_messages)
        
        context_messages = []
        
        if overflow_index == -1:
            # No overflow, include all messages
            logger.info("No overflow detected, including all previous messages")
            for message in reversed(previous_messages):  # Reverse to chronological order
                context_messages.append({
                    "role": message.role,
                    "content": message.content
                })
        else:
            # Overflow detected, need summarization
            logger.info(f"Overflow detected, summarizing messages from index {overflow_index} onwards")
            
            # Messages that need summarization (from overflow_index to end)
            messages_to_summarize = previous_messages[overflow_index:]
            
            # Messages to keep as-is (recent messages within token limit)
            recent_messages = previous_messages[:overflow_index]
            
            logger.info(f"Summarizing {len(messages_to_summarize)} messages, keeping {len(recent_messages)} recent messages")
            
            # Create conversation history for summarization (in chronological order)
            conversation_history = []
            for message in reversed(messages_to_summarize):
                conversation_history.append({
                    "role": message.role,
                    "content": message.content
                })
            
            # Generate summary
            if conversation_history:
                summary = await self._summarize_old_messages([conversation_history])
                context_messages.append({
                    "role": "system",
                    "content": f"Previous conversation summary: {summary}"
                })
                logger.info(f"Added conversation summary ({count_tokens(summary)} tokens)")
            
            # Add recent messages in chronological order
            for message in reversed(recent_messages):
                context_messages.append({
                    "role": message.role,
                    "content": message.content
                })
        
        # Step 3: Add the latest user message
        context_messages.append({
            "role": "user",
            "content": latest_user_message
        })
        
        # Log final context statistics
        total_context_tokens = sum(count_tokens(msg["content"]) for msg in context_messages)
        logger.info(f"Final context built: {len(context_messages)} messages, {total_context_tokens} total tokens")
        
        return context_messages

    
    def _get_overflow_index(self, messages: List[Message]) -> int:
        """
        Return the index in conversation from where summarization starts.
        
        Args:
            messages: List of messages in reverse chronological order (most recent first)
            
        Returns:
            int: Index where overflow occurs, or -1 if no overflow.
        """
        if not messages:
            logger.debug("No messages provided, returning -1")
            return -1
            
        total_tokens = 0
        token_limit = self.config.fixed_llm_conversation_tokens
        
        logger.info(f"Checking for token overflow with limit: {token_limit} tokens")
        
        # Iterate through messages (they are in reverse chronological order)
        for i, message in enumerate(messages):
            # Count tokens for this message
            message_tokens = count_tokens(message.content)
            total_tokens += message_tokens
            
            logger.debug(f"Message {i}: role={message.role}, tokens={message_tokens}, total_tokens={total_tokens}")
            
            # Check if we've exceeded the token limit
            if total_tokens > token_limit:
                logger.info(f"Token overflow detected at index {i}: total_tokens={total_tokens} > limit={token_limit}")
                logger.info(f"Messages from index {i} onwards will need summarization")
                return i
        
        # No overflow occurred
        logger.info("No token overflow detected, returning -1")
        return -1
    
    async def _get_conversation_history(self) -> List[Message]:
        """Retrieve all messages for the conversation from database, sorted by creation time."""
        try:
            # First get the conversation by conversation_id string
            query = select(Conversation).where(
                Conversation.conversation_id == self.conversation_id
            )
            result = await self.db_session.execute(query)
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                logger.warning(f"Conversation {self.conversation_id} not found")
                return []
            
            # Then get messages by the integer ID
            messages_query = select(Message).where(
                Message.conversation_id == conversation.id
            ).order_by(Message.created_at.desc())
            
            messages_result = await self.db_session.execute(messages_query)
            # Convert Sequence to List to fix linter error
            return list(messages_result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            return []
    
    async def _summarize_old_messages(self, old_pairs: List[List[Dict[str, str]]]) -> str:
        """Summarize old message pairs that exceed the token limit."""
        # Flatten pairs into conversation history format
        conversation_history = []
        for pair in reversed(old_pairs):  # Process in chronological order
            conversation_history.extend(pair)
        
        # Use the summarizer agent
        summary = await summarize_conversation_async(
            conversation_history=conversation_history,
            summary_length=self.config.summary_length,
            max_tokens=self.config.summary_max_tokens
        )
        
        return summary
        
    