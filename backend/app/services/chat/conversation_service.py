"""
Conversation Service

This service handles all conversation-related database operations including
creation, retrieval, updates, and deletion of conversations.
"""

import uuid
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from sqlalchemy.orm import selectinload

from app.models.database.conversation import Conversation
from app.models.database.user import User
from app.models.schemas.chat_schemas import ConversationCreate, ConversationUpdate
from app.core.exceptions import ConversationNotFoundException

from aicore.logger import get_logger

# Set up logger
logger = get_logger(__name__)


class ConversationService:
    """
    Service for managing conversation operations
    
    Features:
    - Conversation CRUD operations
    - User conversation management
    - Conversation activity tracking
    - Database transaction handling
    """
    
    def __init__(self, db: AsyncSession, user: User):
        """
        Initialize the conversation service
        
        Args:
            db: Database session
            user: User instance
        """
        self.db = db
        self.user = user
        self.user_id = user.id  # Use integer ID for database operations
        self.user_uuid = user.user_id  # Keep UUID for logging
        
        logger.info(f"ConversationService initialized for user {self.user_uuid}")
    
    async def create_conversation(self, conversation_data: ConversationCreate) -> Conversation:
        """
        Create a new conversation
        
        Args:
            conversation_data: Conversation creation data
            
        Returns:
            Created Conversation instance
        """
        logger.info(f"Creating conversation for user {self.user_uuid}")
        
        try:
            # Create conversation instance
            conversation = Conversation(
                conversation_id=str(uuid.uuid4()),
                user_id=self.user_id,
                title=conversation_data.title,
                model_name=conversation_data.model_name,
                system_prompt=conversation_data.system_prompt,
                status="active"
            )
            
            self.db.add(conversation)
            await self.db.commit()
            await self.db.refresh(conversation)
            
            logger.info(f"Created conversation {conversation.conversation_id} for user {self.user_uuid}")
            return conversation
            
        except Exception as e:
            logger.error(f"Error creating conversation for user {self.user_uuid}: {e}")
            await self.db.rollback()
            raise
    
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Get a conversation by ID (must belong to the user)
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            Conversation instance or None
        """
        try:
            query = select(Conversation).where(
                Conversation.conversation_id == conversation_id,
                Conversation.user_id == self.user_id,
                Conversation.status == "active"
            )
            
            result = await self.db.execute(query)
            conversation = result.scalar_one_or_none()
            
            if conversation:
                logger.debug(f"Retrieved conversation {conversation_id} for user {self.user_id}")
            else:
                logger.warning(f"Conversation {conversation_id} not found for user {self.user_id}")
            
            return conversation
            
        except Exception as e:
            logger.error(f"Error retrieving conversation {conversation_id}: {e}")
            raise
    
    async def get_user_conversations(
        self,
        limit: int = 20,
        offset: int = 0,
        include_inactive: bool = False
    ) -> List[Conversation]:
        """
        Get user's conversations with pagination
        
        Args:
            limit: Number of conversations to retrieve
            offset: Offset for pagination
            include_inactive: Whether to include inactive conversations
            
        Returns:
            List of Conversation instances
        """
        try:
            query = select(Conversation).where(
                Conversation.user_id == self.user_id
            )
            
            if not include_inactive:
                query = query.where(Conversation.status == "active")
            
            # Add message count as a calculated field
            from app.models.database.message import Message
            query = query.outerjoin(Message).group_by(Conversation.id).add_columns(
                func.count(Message.id).label('message_count')
            )
            
            query = query.order_by(Conversation.updated_at.desc())
            query = query.limit(limit).offset(offset)
            
            result = await self.db.execute(query)
            conversations_with_counts = result.fetchall()
            
            # Extract conversations and set message count
            conversations = []
            for conv, message_count in conversations_with_counts:
                conv.message_count = message_count
                conversations.append(conv)
            
            logger.info(f"Retrieved {len(conversations)} conversations for user {self.user_id}")
            return conversations
            
        except Exception as e:
            logger.error(f"Error retrieving conversations for user {self.user_id}: {e}")
            raise
    
    async def count_user_conversations(
        self,
        include_inactive: bool = False
    ) -> int:
        """
        Count user's conversations
        
        Args:
            include_inactive: Whether to include inactive conversations
            
        Returns:
            Total count of conversations
        """
        try:
            query = select(func.count(Conversation.id)).where(
                Conversation.user_id == self.user_id
            )
            
            if not include_inactive:
                query = query.where(Conversation.status == "active")
            
            result = await self.db.execute(query)
            count = result.scalar() or 0
            
            logger.info(f"Found {count} conversations for user {self.user_id}")
            return count
            
        except Exception as e:
            logger.error(f"Error counting conversations for user {self.user_id}: {e}")
            raise

    
    async def update_conversation(
        self,
        conversation_id: str,
        conversation_data: ConversationUpdate
    ) -> Optional[Conversation]:
        """
        Update a conversation
        
        Args:
            conversation_id: The conversation ID
            conversation_data: Updated conversation data
            
        Returns:
            Updated Conversation instance or None
        """
        logger.info(f"Updating conversation {conversation_id}")
        
        try:
            # Verify conversation exists and belongs to user
            conversation = await self.get_conversation(conversation_id)
            if not conversation:
                raise ConversationNotFoundException(f"Conversation {conversation_id} not found")
            
            # Update fields that are provided
            update_data = {}
            if conversation_data.title is not None:
                update_data['title'] = conversation_data.title
            if conversation_data.model_name is not None:
                update_data['model_name'] = conversation_data.model_name
            if conversation_data.system_prompt is not None:
                update_data['system_prompt'] = conversation_data.system_prompt
            
            if update_data:
                update_data['updated_at'] = datetime.utcnow()
                
                query = update(Conversation).where(
                    Conversation.conversation_id == conversation_id,
                    Conversation.user_id == self.user_id
                ).values(**update_data)
                
                await self.db.execute(query)
                await self.db.commit()
                
                # Refresh conversation
                await self.db.refresh(conversation)
            
            logger.info(f"Updated conversation {conversation_id}")
            return conversation
            
        except Exception as e:
            logger.error(f"Error updating conversation {conversation_id}: {e}")
            await self.db.rollback()
            raise
    
    async def update_conversation_activity(self, conversation_id: str) -> bool:
        """
        Update conversation's updated_at timestamp
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            True if updated successfully
        """
        try:
            query = update(Conversation).where(
                Conversation.conversation_id == conversation_id,
                Conversation.user_id == self.user_id
            ).values(updated_at=datetime.utcnow())
            
            result = await self.db.execute(query)
            await self.db.commit()
            
            success = result.rowcount > 0
            if success:
                logger.debug(f"Updated activity for conversation {conversation_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating activity for conversation {conversation_id}: {e}")
            await self.db.rollback()
            return False
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """
        Soft delete a conversation (mark as inactive)
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            True if deleted successfully
        """
        logger.info(f"Deleting conversation {conversation_id}")
        
        try:
            # Verify conversation exists and belongs to user
            conversation = await self.get_conversation(conversation_id)
            if not conversation:
                raise ConversationNotFoundException(f"Conversation {conversation_id} not found")
            
            # Soft delete by marking as inactive
            query = update(Conversation).where(
                Conversation.conversation_id == conversation_id,
                Conversation.user_id == self.user_id
            ).values(
                is_active=False,
                updated_at=datetime.utcnow()
            )
            
            result = await self.db.execute(query)
            await self.db.commit()
            
            success = result.rowcount > 0
            if success:
                logger.info(f"Deleted conversation {conversation_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting conversation {conversation_id}: {e}")
            await self.db.rollback()
            raise
    
    async def hard_delete_conversation(self, conversation_id: str) -> bool:
        """
        Permanently delete a conversation from database
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            True if deleted successfully
        """
        logger.warning(f"Hard deleting conversation {conversation_id}")
        
        try:
            # Verify conversation exists and belongs to user
            conversation = await self.get_conversation(conversation_id)
            if not conversation:
                return True  # Already deleted
            
            # Hard delete
            query = delete(Conversation).where(
                Conversation.conversation_id == conversation_id,
                Conversation.user_id == self.user_id
            )
            
            result = await self.db.execute(query)
            await self.db.commit()
            
            success = result.rowcount > 0
            if success:
                logger.warning(f"Hard deleted conversation {conversation_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error hard deleting conversation {conversation_id}: {e}")
            await self.db.rollback()
            raise
    
    async def get_conversation_stats(self) -> dict:
        """
        Get conversation statistics for the user
        
        Returns:
            Dictionary with conversation statistics
        """
        try:
            # Total conversations
            total_query = select(func.count(Conversation.id)).where(
                Conversation.user_id == self.user_id,
                Conversation.is_active == True
            )
            total_result = await self.db.execute(total_query)
            total_conversations = total_result.scalar()
            
            # Recent conversations (last 7 days)
            from datetime import timedelta
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_query = select(func.count(Conversation.id)).where(
                Conversation.user_id == self.user_id,
                Conversation.is_active == True,
                Conversation.created_at >= week_ago
            )
            recent_result = await self.db.execute(recent_query)
            recent_conversations = recent_result.scalar()
            
            # Average messages per conversation
            from app.models.database.message import Message
            avg_query = select(
                func.avg(func.count(Message.id))
            ).select_from(
                Conversation
            ).outerjoin(Message).where(
                Conversation.user_id == self.user_id,
                Conversation.is_active == True
            ).group_by(Conversation.id)
            
            avg_result = await self.db.execute(avg_query)
            avg_messages = avg_result.scalar() or 0
            
            stats = {
                "total_conversations": total_conversations or 0,
                "recent_conversations": recent_conversations or 0,
                "average_messages_per_conversation": float(avg_messages)
            }
            
            logger.info(f"Retrieved conversation stats for user {self.user_id}: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting conversation stats for user {self.user_id}: {e}")
            return {
                "total_conversations": 0,
                "recent_conversations": 0,
                "average_messages_per_conversation": 0.0
            } 