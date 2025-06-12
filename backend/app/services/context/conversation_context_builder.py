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
        
        # Step 2: Create user-assistant message pairs
        message_pairs = self._create_message_pairs(previous_messages)
        
        # Step 3: Find token cutoff point
        recent_pairs, old_pairs = self._find_token_cutoff(message_pairs, latest_user_message)
        
        # Step 4: Build final context
        context_messages = []
        
        # Add summary if we have old messages that exceed token limit
        if old_pairs:
            logger.info(f"Summarizing {len(old_pairs)} message pairs that exceed token limit")
            summary = await self._summarize_old_messages(old_pairs)
            context_messages.append({
                "role": "system",
                "content": f"Previous conversation summary: {summary}"
            })
        
        # Add recent message pairs (within token limit)
        for pair in reversed(recent_pairs):  # Add in chronological order
            context_messages.extend(pair)
        
        # Add the latest user message
        context_messages.append({
            "role": "user", 
            "content": latest_user_message
        })
        
        logger.info(f"Built context with {len(context_messages)} messages")
        return context_messages
    
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
            return messages_result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            return []
    
    def _create_message_pairs(self, messages: List[Message]) -> List[List[Dict[str, str]]]:
        """
        Group messages into user-assistant pairs.
        Returns list of pairs, where each pair is [user_msg, assistant_msg].
        """
        pairs = []
        current_pair = []
        
        # Process messages from newest to oldest
        for message in messages:
            message_dict = {
                "role": message.role,
                "content": message.content
            }
            
            if message.role == "user":
                # Start a new pair with user message
                if len(current_pair) > 0:
                    # If we have incomplete pair, add it first
                    pairs.append(current_pair)
                current_pair = [message_dict]
            elif message.role == "assistant" and len(current_pair) > 0:
                # Complete the current pair
                current_pair.append(message_dict)
                pairs.append(current_pair)
                current_pair = []
        
        # Add any remaining incomplete pair
        if len(current_pair) > 0:
            pairs.append(current_pair)
        
        return pairs
    
    def _find_token_cutoff(self, message_pairs: List[List[Dict[str, str]]], 
                          latest_user_message: str) -> Tuple[List[List[Dict[str, str]]], List[List[Dict[str, str]]]]:
        """
        Find where to cut off the conversation based on token limits.
        Returns (recent_pairs_within_limit, old_pairs_beyond_limit).
        """
        # Count tokens for the latest user message
        running_token_count = count_tokens(latest_user_message)
        
        recent_pairs = []
        old_pairs = []
        
        # Process pairs from newest to oldest
        for pair in message_pairs:
            # Calculate tokens for this pair
            pair_content = " ".join([msg["content"] for msg in pair])
            pair_tokens = count_tokens(pair_content)
            
            # Check if adding this pair would exceed the limit
            if running_token_count + pair_tokens <= self.config.fixed_llm_conversation_tokens:
                recent_pairs.append(pair)
                running_token_count += pair_tokens
            else:
                # This pair and all remaining pairs are old
                old_pairs.extend(message_pairs[len(recent_pairs):])
                break
        
        logger.info(f"Token cutoff: {len(recent_pairs)} recent pairs ({running_token_count} tokens), "
                   f"{len(old_pairs)} old pairs")
        
        return recent_pairs, old_pairs
    
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
        
    