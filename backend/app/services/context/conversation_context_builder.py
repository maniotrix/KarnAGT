from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.context.ai_context_agent import ConversationSummarizerAgent, summarize_conversation_async
from app.services.context.utils import count_tokens
from app.models.database.conversation import Conversation
from app.models.database.message import Message
from aicore.logger import get_logger
import json

logger = get_logger(__name__)

# TODO : optimissation strategy for context builder, maybe use redis to store the context and update it when needed
# instead of building the context from scratch every time

@dataclass
class ConversationContextConfig:
    """Configuration for conversation context building"""
    summary_length: str = "comprehensive"
    summary_max_tokens: int = 1000
    fixed_llm_conversation_tokens: int = 40000
    
    
    
def get_default_conversation_context_config() -> ConversationContextConfig:
    return ConversationContextConfig(
        summary_length="comprehensive",
        summary_max_tokens=1000,
        fixed_llm_conversation_tokens=40000
    )
    
    
class ConversationContextBuilder:
    def __init__(self, config: ConversationContextConfig, db_session: AsyncSession, conversation_id: str):
        self.config = config
        self.db_session = db_session
        self.conversation_id = conversation_id
        self.summarizer = ConversationSummarizerAgent()
        

    async def build_context(self, latest_user_message: str, openai_file_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Build conversation context with intelligent summarization when needed.
        
        Returns a list of messages formatted for LLM consumption:
        [
            {summary of conversation history if needed},
            {user-assistant message pairs within token limit},
            {"role": "user", "content": "latest user message" or multimodal content}
        ]
        """
        logger.info(f"Building context for conversation {self.conversation_id}")
        
        # Step 1: Get all previous messages from database (excluding the current message)
        previous_messages = await self._get_conversation_history()
        
        if not previous_messages:
            logger.info("No previous messages found, returning only latest user message")
            # Build final user message with images if provided
            final_message = self._build_user_message_with_images(latest_user_message, openai_file_ids or [])
            return [final_message]
        
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
        
        # Step 3: Add the latest user message with images
        final_message = self._build_user_message_with_images(latest_user_message, openai_file_ids or [])
        context_messages.append(final_message)
        
        # Log final context statistics
        total_context_tokens = sum(count_tokens(msg["content"] if isinstance(msg["content"], str) else latest_user_message) for msg in context_messages)
        logger.info(f"Final context built: {len(context_messages)} messages, {total_context_tokens} total tokens")
        
        return context_messages
    
    def _build_user_message_with_images(self, text_content: str, openai_file_ids: List[str]) -> Dict[str, Any]:
        """Build user message with optional image attachments"""
        if not openai_file_ids:
            # Text-only message
            return {
                "role": "user",
                "content": text_content
            }
        
        # Multimodal message with images
        content_parts = []
        
        # Add text content only if it's not empty
        if text_content and text_content.strip():
            content_parts.append({"type": "text", "text": text_content})
        
        # Add images
        for file_id in openai_file_ids:
            content_parts.append({
                "type": "image_file", 
                "image_file": {"file_id": file_id}
            })
        
        logger.info(f"Built multimodal message with {len(openai_file_ids)} images and {'text' if text_content.strip() else 'no text'}")
        return {
            "role": "user",
            "content": content_parts
        }

    async def build_context_dict(self, latest_user_message: str) -> Dict[str, Any]:
        """
        Build conversation context as a structured dictionary with separate components.
        
        Args:
            latest_user_message: The latest user message to include in context
            
        Returns:
            Dictionary with structured context components:
            {
                "summary_old_messages": str or None,
                "recent_conversation_history": List[Dict[str, str]],
                "user_input": str,
                "overflow": bool
            }
        """
        logger.info(f"Building structured context dict for conversation {self.conversation_id}")
        
        # Step 1: Get all previous messages from database (excluding the current message)
        previous_messages = await self._get_conversation_history()
        
        # Initialize context structure
        context_dict = {
            "summary_old_messages": None,
            "recent_conversation_history": [],
            "user_input": latest_user_message,
            "overflow": False
        }
        
        if not previous_messages:
            logger.info("No previous messages found, returning empty history")
            return context_dict
        
        # Step 2: Check if we need summarization
        overflow_index = self._get_overflow_index(previous_messages)
        
        if overflow_index == -1:
            # No overflow, include all messages as recent history
            logger.info("No overflow detected, including all previous messages as recent history")
            context_dict["overflow"] = False
            
            for message in reversed(previous_messages):  # Reverse to chronological order
                context_dict["recent_conversation_history"].append({
                    "role": message.role,
                    "content": message.content
                })
        else:
            # Overflow detected, need summarization
            logger.info(f"Overflow detected, summarizing messages from index {overflow_index} onwards")
            context_dict["overflow"] = True
            
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
                context_dict["summary_old_messages"] = summary
                logger.info(f"Added conversation summary ({count_tokens(summary)} tokens)")
            
            # Add recent messages as history (in chronological order)
            for message in reversed(recent_messages):
                context_dict["recent_conversation_history"].append({
                    "role": message.role,
                    "content": message.content
                })
        
        # Log final context statistics
        history_count = len(context_dict["recent_conversation_history"])
        has_summary = context_dict["summary_old_messages"] is not None
        total_tokens = (
            count_tokens(context_dict["summary_old_messages"] or "") +
            sum(count_tokens(msg["content"]) for msg in context_dict["recent_conversation_history"]) +
            count_tokens(context_dict["user_input"])
        )
        
        logger.info(f"Context dict built: {history_count} recent messages, summary={has_summary}, overflow={context_dict['overflow']}, total_tokens={total_tokens}")
        
        return context_dict
    
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
        

async def get_context_dict_for_conversation(conversation_id: str, db_session: AsyncSession, latest_user_message: str) -> Dict[str, Any]:
    """
    Get the structured context dictionary for a conversation.
    
    Returns:
        Dictionary with structured context components:
        {
            "summary_old_messages": str or None,
            "recent_conversation_history": List[Dict[str, str]],
            "user_input": str,
            "overflow": bool
        }
    """
    context_builder = ConversationContextBuilder(get_default_conversation_context_config(), db_session, conversation_id)
    context_dict = await context_builder.build_context_dict(latest_user_message)
    return context_dict


async def get_context_for_conversation(
    conversation_id: str, 
    db_session: AsyncSession, 
    latest_user_message: str,
    openai_file_ids: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Get context for conversation with optional images as list of message dictionaries
    """
    builder = ConversationContextBuilder(
        get_default_conversation_context_config(), 
        db_session, 
        conversation_id
    )
    
    return await builder.build_context(latest_user_message, openai_file_ids)
