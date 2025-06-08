"""
Message Service

This service handles all message-related database operations including
creation, retrieval, updates, and deletion of messages.
"""

import uuid
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete, desc
from sqlalchemy.orm import selectinload

from app.models.database.message import Message
from app.models.database.conversation import Conversation
from app.models.database.user import User
from app.models.schemas.chat_schemas import MessageCreate, MessageUpdate
from app.core.exceptions import MessageNotFoundException

from aicore.logger import get_logger

# Set up logger
logger = get_logger(__name__)


class MessageService:
    """
    Service for managing message operations
    
    Features:
    - Message CRUD operations
    - Conversation message management
    - Message history and pagination
    - Database transaction handling
    """
    
    def __init__(self, db: AsyncSession, user: User):
        """
        Initialize the message service
        
        Args:
            db: Database session
            user: User instance
        """
        self.db = db
        self.user = user
        self.user_id = user.id
        self.user_uuid = user.user_id
        
        logger.info(f"MessageService initialized for user {self.user_uuid}")
    
    async def create_message(self, conversation_id: str, message_data: MessageCreate) -> Message:
        """
        Create a new message
        
        Args:
            conversation_id: The conversation ID (UUID string)
            message_data: Message creation data
            
        Returns:
            Created Message instance
        """
        logger.info(f"Creating message for conversation {conversation_id}")
        
        try:
            # Get the conversation's integer ID
            conv_query = select(Conversation.id).where(
                Conversation.conversation_id == conversation_id,
                Conversation.user_id == self.user.id
            )
            conv_result = await self.db.execute(conv_query)
            conv_int_id = conv_result.scalar_one_or_none()
            
            if not conv_int_id:
                raise ValueError(f"Conversation {conversation_id} not found")
            
            # Create message instance
            message = Message(
                message_id=str(uuid.uuid4()),
                conversation_id=conv_int_id,
                content=message_data.content,
                role=message_data.role,
                message_type=getattr(message_data, 'message_type', 'text'),
                status=getattr(message_data, 'status', 'completed'),
                extra_metadata=getattr(message_data, 'metadata', {})
            )
            
            self.db.add(message)
            await self.db.commit()
            await self.db.refresh(message)
            
            logger.info(f"Created message {message.message_id} for conversation {conversation_id}")
            return message
            
        except Exception as e:
            logger.error(f"Error creating message for conversation {conversation_id}: {e}")
            await self.db.rollback()
            raise
    
    async def get_message(self, message_id: str) -> Optional[Message]:
        """
        Get a message by ID (must belong to the user)
        
        Args:
            message_id: The message ID
            
        Returns:
            Message instance or None
        """
        try:
            query = select(Message).join(Conversation).where(
                Message.message_id == message_id,
                Conversation.user_id == self.user.id
            )
            
            result = await self.db.execute(query)
            message = result.scalar_one_or_none()
            
            if message:
                logger.debug(f"Retrieved message {message_id} for user {self.user_uuid}")
            else:
                logger.warning(f"Message {message_id} not found for user {self.user_uuid}")
            
            return message
            
        except Exception as e:
            logger.error(f"Error retrieving message {message_id}: {e}")
            raise
    
    async def get_conversation_messages(
        self,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0,
        role_filter: Optional[str] = None
    ) -> List[Message]:
        """
        Get messages for a conversation with pagination
        
        For initial load (offset=0): Returns the latest messages in chronological order
        For pagination (offset>0): Returns older messages in chronological order
        
        Args:
            conversation_id: The conversation ID (UUID string)
            limit: Number of messages to retrieve
            offset: Offset for pagination (0 = latest messages)
            role_filter: Optional role filter (user, assistant, system)
            
        Returns:
            List of Message instances in chronological order (oldest to newest)
        """
        try:
            # Get the conversation's integer ID
            conv_query = select(Conversation.id).where(
                Conversation.conversation_id == conversation_id,
                Conversation.user_id == self.user.id
            )
            conv_result = await self.db.execute(conv_query)
            conv_int_id = conv_result.scalar_one_or_none()
            
            if not conv_int_id:
                return []
            
            query = select(Message).where(
                Message.conversation_id == conv_int_id
            )
            
            if role_filter:
                query = query.where(Message.role == role_filter)
            
            # For pagination: Order by newest first, apply offset/limit, then reverse
            # This ensures we get the correct "page" of older messages
            query = query.order_by(desc(Message.created_at))
            query = query.limit(limit).offset(offset)
            
            result = await self.db.execute(query)
            messages = result.scalars().all()
            
            # Always reverse to get chronological order (oldest to newest within the page)
            messages = list(reversed(list(messages)))
            
            logger.info(f"Retrieved {len(messages)} messages for conversation {conversation_id} (offset={offset}, limit={limit})")
            return messages
            
        except Exception as e:
            logger.error(f"Error retrieving messages for conversation {conversation_id}: {e}")
            raise
    
    async def get_recent_messages(
        self,
        conversation_id: str,
        limit: int = 10
    ) -> List[Message]:
        """
        Get the most recent messages for a conversation
        
        Args:
            conversation_id: The conversation ID (UUID string)
            limit: Number of recent messages to retrieve
            
        Returns:
            List of Message instances ordered by creation time (newest first)
        """
        try:
            # Get the conversation's integer ID
            conv_query = select(Conversation.id).where(
                Conversation.conversation_id == conversation_id,
                Conversation.user_id == self.user.id
            )
            conv_result = await self.db.execute(conv_query)
            conv_int_id = conv_result.scalar_one_or_none()
            
            if not conv_int_id:
                return []
            
            query = select(Message).where(
                Message.conversation_id == conv_int_id
            ).order_by(desc(Message.created_at)).limit(limit)
            
            result = await self.db.execute(query)
            messages = result.scalars().all()
            
            # Reverse to get chronological order
            messages = list(reversed(list(messages)))
            
            logger.debug(f"Retrieved {len(messages)} recent messages for conversation {conversation_id}")
            return messages
            
        except Exception as e:
            logger.error(f"Error retrieving recent messages for conversation {conversation_id}: {e}")
            raise
    
    async def update_message(
        self,
        message_id: str,
        message_data: MessageUpdate
    ) -> Optional[Message]:
        """
        Update a message
        
        Args:
            message_id: The message ID
            message_data: Updated message data
            
        Returns:
            Updated Message instance or None
        """
        logger.info(f"Updating message {message_id}")
        
        try:
            # Verify message exists and belongs to user
            message = await self.get_message(message_id)
            if not message:
                raise MessageNotFoundException(f"Message {message_id} not found")
            
            # Update fields that are provided
            update_data = {}
            if message_data.content is not None:
                update_data['content'] = message_data.content
            if message_data.metadata is not None:
                update_data['metadata'] = message_data.metadata
            
            if update_data:
                update_data['updated_at'] = datetime.utcnow()
                
                query = update(Message).where(
                    Message.message_id == message_id,
                    Message.conversation_id.in_(
                        select(Conversation.id).where(Conversation.user_id == self.user.id)
                    )
                ).values(**update_data)
                
                await self.db.execute(query)
                await self.db.commit()
                
                # Refresh message
                await self.db.refresh(message)
            
            logger.info(f"Updated message {message_id}")
            return message
            
        except Exception as e:
            logger.error(f"Error updating message {message_id}: {e}")
            await self.db.rollback()
            raise
    
    async def delete_message(self, message_id: str) -> bool:
        """
        Delete a message
        
        Args:
            message_id: The message ID
            
        Returns:
            True if deleted successfully
        """
        logger.info(f"Deleting message {message_id}")
        
        try:
            # Verify message exists and belongs to user
            message = await self.get_message(message_id)
            if not message:
                raise MessageNotFoundException(f"Message {message_id} not found")
            
            # Delete the message
            query = delete(Message).where(
                Message.message_id == message_id,
                Message.conversation_id.in_(
                    select(Conversation.id).where(Conversation.user_id == self.user.id)
                )
            )
            
            result = await self.db.execute(query)
            await self.db.commit()
            
            success = result.rowcount > 0
            if success:
                logger.info(f"Deleted message {message_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting message {message_id}: {e}")
            await self.db.rollback()
            raise
    
    async def delete_conversation_messages(self, conversation_id: str) -> int:
        """
        Delete all messages for a conversation
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            Number of messages deleted
        """
        logger.info(f"Deleting all messages for conversation {conversation_id}")
        
        try:
            # Get the conversation's integer ID
            conv_query = select(Conversation.id).where(
                Conversation.conversation_id == conversation_id,
                Conversation.user_id == self.user.id
            )
            conv_result = await self.db.execute(conv_query)
            conv_int_id = conv_result.scalar_one_or_none()
            
            if not conv_int_id:
                return 0
            
            query = delete(Message).where(
                Message.conversation_id == conv_int_id
            )
            
            result = await self.db.execute(query)
            await self.db.commit()
            
            deleted_count = result.rowcount
            logger.info(f"Deleted {deleted_count} messages for conversation {conversation_id}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting messages for conversation {conversation_id}: {e}")
            await self.db.rollback()
            raise
    
    async def get_message_count(self, conversation_id: str) -> int:
        """
        Get the total number of messages in a conversation
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            Number of messages
        """
        try:
            # Get the conversation's integer ID
            conv_query = select(Conversation.id).where(
                Conversation.conversation_id == conversation_id,
                Conversation.user_id == self.user.id
            )
            conv_result = await self.db.execute(conv_query)
            conv_int_id = conv_result.scalar_one_or_none()
            
            if not conv_int_id:
                return 0
            
            query = select(func.count(Message.id)).where(
                Message.conversation_id == conv_int_id
            )
            
            result = await self.db.execute(query)
            count = result.scalar()
            
            logger.debug(f"Conversation {conversation_id} has {count} messages")
            return count or 0
            
        except Exception as e:
            logger.error(f"Error getting message count for conversation {conversation_id}: {e}")
            return 0
    
    async def get_user_message_stats(self) -> dict:
        """
        Get message statistics for the user
        
        Returns:
            Dictionary with message statistics
        """
        try:
            # Total messages
            total_query = select(func.count(Message.id)).where(
                Message.conversation_id.in_(
                    select(Conversation.id).where(Conversation.user_id == self.user.id)
                )
            )
            total_result = await self.db.execute(total_query)
            total_messages = total_result.scalar()
            
            # Messages by role
            role_query = select(
                Message.role,
                func.count(Message.id)
            ).where(
                Message.conversation_id.in_(
                    select(Conversation.id).where(Conversation.user_id == self.user.id)
                )
            ).group_by(Message.role)
            
            role_result = await self.db.execute(role_query)
            role_stats = {role: count for role, count in role_result.fetchall()}
            
            # Recent messages (last 7 days)
            from datetime import timedelta
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_query = select(func.count(Message.id)).where(
                Message.conversation_id.in_(
                    select(Conversation.id).where(Conversation.user_id == self.user.id)
                ),
                Message.created_at >= week_ago
            )
            recent_result = await self.db.execute(recent_query)
            recent_messages = recent_result.scalar()
            
            stats = {
                "total_messages": total_messages or 0,
                "recent_messages": recent_messages or 0,
                "by_role": role_stats,
                "user_messages": role_stats.get("user", 0),
                "assistant_messages": role_stats.get("assistant", 0)
            }
            
            logger.info(f"Retrieved message stats for user {self.user_uuid}: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting message stats for user {self.user_uuid}: {e}")
            return {
                "total_messages": 0,
                "recent_messages": 0,
                "by_role": {},
                "user_messages": 0,
                "assistant_messages": 0
            }
    
    async def search_messages(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Message]:
        """
        Search messages by content
        
        Args:
            query: Search query
            conversation_id: Optional conversation ID to limit search
            limit: Maximum number of results
            
        Returns:
            List of matching Message instances
        """
        try:
            search_query = select(Message).where(
                Message.conversation_id.in_(
                    select(Conversation.id).where(Conversation.user_id == self.user.id)
                ),
                Message.content.ilike(f"%{query}%")
            )
            
            if conversation_id:
                # Get the conversation's integer ID
                conv_query = select(Conversation.id).where(
                    Conversation.conversation_id == conversation_id,
                    Conversation.user_id == self.user.id
                )
                conv_result = await self.db.execute(conv_query)
                conv_int_id = conv_result.scalar_one_or_none()
                
                if conv_int_id:
                    search_query = search_query.where(Message.conversation_id == conv_int_id)
            
            search_query = search_query.order_by(desc(Message.created_at)).limit(limit)
            
            result = await self.db.execute(search_query)
            messages = result.scalars().all()
            
            logger.info(f"Found {len(messages)} messages matching query '{query}'")
            return list(messages)
            
        except Exception as e:
            logger.error(f"Error searching messages with query '{query}': {e}")
            raise
    
    async def get_conversation_context(
        self,
        conversation_id: str,
        max_tokens: int = 4000
    ) -> List[Message]:
        """
        Get conversation context that fits within token limit
        
        Args:
            conversation_id: The conversation ID
            max_tokens: Maximum tokens for context
            
        Returns:
            List of recent Message instances that fit in token limit
        """
        try:
            # Get recent messages in reverse order
            # Get the conversation's integer ID
            conv_query = select(Conversation.id).where(
                Conversation.conversation_id == conversation_id,
                Conversation.user_id == self.user.id
            )
            conv_result = await self.db.execute(conv_query)
            conv_int_id = conv_result.scalar_one_or_none()
            
            if not conv_int_id:
                return []
            
            query = select(Message).where(
                Message.conversation_id == conv_int_id
            ).order_by(desc(Message.created_at))
            
            result = await self.db.execute(query)
            all_messages = list(result.scalars().all())
            
            # Build context from most recent messages
            context_messages = []
            total_tokens = 0
            
            for message in all_messages:
                # Rough token estimation (1 token ≈ 4 characters)
                message_tokens = len(message.content) // 4
                
                if total_tokens + message_tokens > max_tokens:
                    break
                
                context_messages.append(message)
                total_tokens += message_tokens
            
            # Return in chronological order
            context_messages.reverse()
            
            logger.debug(f"Built context with {len(context_messages)} messages (~{total_tokens} tokens)")
            return context_messages
            
        except Exception as e:
            logger.error(f"Error building conversation context for {conversation_id}: {e}")
            return [] 