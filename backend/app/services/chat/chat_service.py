"""
Chat Service - Main Orchestration

This service coordinates all chat functionality, integrating with the OpenAI assistant,
database operations, cost tracking, and streaming responses.
"""

import uuid
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from sqlalchemy.orm import selectinload

from app.integrations.openai.assistant_client import assistant_manager, OpenAIAssistantClient
from app.integrations.openai.cost_tracker import CostTracker
from app.integrations.openai.error_handler import handle_openai_errors
from app.services.chat.conversation_service import ConversationService
from app.services.chat.message_service import MessageService
from app.models.database.user import User
from app.models.database.conversation import Conversation
from app.models.database.message import Message
from app.models.schemas.chat_schemas import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse
)
from app.core.exceptions import (
    ConversationNotFoundException,
    MessageProcessingException,
    QuotaExceededException
)

from aicore.logger import get_logger

# Set up logger
logger = get_logger(__name__)


class ChatService:
    """
    Main chat service that orchestrates all chat functionality
    
    Features:
    - Chat conversation management
    - AI response generation
    - Streaming support
    - Cost tracking and quota management
    - Message persistence
    - Context management
    """
    
    def __init__(self, db: AsyncSession, user: User):
        """
        Initialize the chat service for a user
        
        Args:
            db: Database session
            user: User instance
        """
        self.db = db
        self.user = user
        self.user_id = user.id
        self.user_uuid = user.user_id
        
        # Initialize service dependencies
        self.conversation_service = ConversationService(db, user)
        self.message_service = MessageService(db, user)
        self.cost_tracker = CostTracker(self.user_uuid)
        
        logger.info(f"ChatService initialized for user {self.user_uuid}")
    
    async def start_conversation(
        self,
        title: Optional[str] = None,
        model: str = "gpt-4",
        system_prompt: Optional[str] = None
    ) -> ConversationResponse:
        """
        Start a new conversation
        
        Args:
            title: Optional conversation title
            model: AI model to use
            system_prompt: Optional system prompt
            
        Returns:
            ConversationResponse with conversation details
        """
        logger.info(f"Starting new conversation for user {self.user_uuid}")
        
        try:
            # Check user quota before starting
            quota_status = await self.cost_tracker.check_user_quota(self.db)
            if not quota_status["allowed"]:
                raise QuotaExceededException(
                    f"Quota exceeded: {quota_status.get('reason', 'Unknown reason')}"
                )
            
            # Create conversation in database
            conversation_data = ConversationCreate(
                title=title or f"Chat {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
                model=model,
                system_prompt=system_prompt
            )
            
            conversation = await self.conversation_service.create_conversation(conversation_data)
            
            # Initialize assistant client for this conversation
            assistant_client = assistant_manager.get_client(
                self.user_uuid, 
                conversation.conversation_id
            )
            
            logger.info(f"Started conversation {conversation.conversation_id} for user {self.user_uuid}")
            
            return ConversationResponse(
                id=conversation.id,
                conversation_id=conversation.conversation_id,
                title=conversation.title,
                description=conversation.description,
                status=conversation.status,
                model_name=conversation.model_name,
                temperature=conversation.temperature,
                max_tokens=conversation.max_tokens,
                memory_enabled=conversation.memory_enabled,
                message_count=conversation.message_count,
                total_tokens_used=conversation.total_tokens_used,
                total_cost_usd=conversation.total_cost_usd,
                is_pinned=conversation.is_pinned,
                is_shared=conversation.is_shared,
                topics=conversation.topics or [],
                tags=conversation.tags or [],
                user_rating=conversation.user_rating,
                quality_score=conversation.quality_score,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
                last_message_at=conversation.last_message_at
            )
            
        except Exception as e:
            logger.error(f"Error starting conversation for user {self.user_uuid}: {e}")
            raise MessageProcessingException(f"Failed to start conversation: {str(e)}")
    
    @handle_openai_errors(max_retries=3)
    async def send_message(
        self,
        conversation_id: str,
        content: str,
        message_type: str = "text",
        model: Optional[str] = None
    ) -> MessageResponse:
        """
        Send a message and get AI response
        
        Args:
            conversation_id: The conversation ID
            content: Message content
            message_type: Type of message
            model: Optional model override
            
        Returns:
            MessageResponse with AI response
        """
        logger.info(f"Processing message for conversation {conversation_id}")
        
        try:
            # Verify conversation exists and belongs to user
            conversation = await self.conversation_service.get_conversation(conversation_id)
            if not conversation:
                raise ConversationNotFoundException(f"Conversation {conversation_id} not found")
            
            # Store model name to avoid accessing detached SQLAlchemy object later
            model_name = model or conversation.model_name or "gpt-4"
            
            # Check quota before processing
            estimated_tokens = self.cost_tracker.count_tokens(content, model_name)
            quota_status = await self.cost_tracker.check_user_quota(self.db, estimated_tokens)
            
            if not quota_status["allowed"]:
                raise QuotaExceededException(
                    f"Quota exceeded: {quota_status.get('reason', 'Unknown reason')}"
                )
            
            # Save user message
            user_message_data = MessageCreate(
                content=content,
                role="user"
            )
            
            user_message = await self.message_service.create_message(conversation_id, user_message_data)
            # Capture message ID immediately to avoid lazy loading later
            user_message_id = user_message.message_id
            
            # Get conversation context
            conversation_history = await self.message_service.get_conversation_messages(
                conversation_id, 
                limit=20  # Last 20 messages for context
            )
            
            # Get assistant client
            assistant_client = assistant_manager.get_client(self.user_uuid, conversation_id)
            
            # Set conversation context if this is not the first message
            if len(conversation_history) > 1:
                context_messages = [
                    {"role": msg.role, "content": msg.content} 
                    for msg in conversation_history[:-1]  # Exclude the message we just added
                ]
                assistant_client.set_conversation_context(context_messages)
            
            # Process message with AI
            ai_response_data = await assistant_client.send_message(
                content,
                message_type=message_type,
                metadata={
                    "conversation_id": conversation_id,
                    "user_message_id": user_message_id,
                    "model": model_name
                }
            )
            
            # Save AI response message
            ai_message_data = MessageCreate(
                content=ai_response_data["content"],
                role="assistant"
            )
            
            ai_message = await self.message_service.create_message(conversation_id, ai_message_data)
            # Capture all needed values immediately to avoid lazy loading later
            ai_message_db_id = ai_message.id
            ai_message_id = ai_message.message_id
            ai_message_conversation_id = ai_message.conversation_id
            ai_message_role = ai_message.role
            ai_message_content = ai_message.content
            ai_message_extra_metadata = ai_message.extra_metadata or {}
            ai_message_created_at = ai_message.created_at
            
            # Track costs (temporarily disabled to test other functionality)
            try:
                await self.cost_tracker.track_usage(
                    db=self.db,
                    operation_type="chat",
                    model=model_name,
                    input_text=content,
                    output_text=ai_response_data["content"],
                    conversation_id=conversation_id,
                    additional_metadata={
                        "user_message_id": user_message_id,
                        "ai_message_id": ai_message_id,
                        "plots": ai_response_data.get("plots", [])
                    }
                )
            except Exception as cost_error:
                logger.warning(f"Cost tracking failed (non-critical): {cost_error}")
                # Continue without failing the entire operation
            
            # Update conversation
            await self.conversation_service.update_conversation_activity(conversation_id)
            
            logger.info(f"Message processed successfully for conversation {conversation_id}")
            
            return MessageResponse(
                id=ai_message_db_id,
                message_id=ai_message_id,
                conversation_id=ai_message_conversation_id,
                role=ai_message_role,
                content=ai_message_content,
                total_tokens=ai_response_data.get("total_tokens", 0),
                cost_usd=ai_response_data.get("cost_usd", 0.0),
                model_name=model_name,
                finish_reason=ai_response_data.get("finish_reason"),
                extra_metadata=ai_message_extra_metadata,
                created_at=ai_message_created_at
            )
            
        except Exception as e:
            logger.error(f"Error processing message for conversation {conversation_id}: {e}")
            raise MessageProcessingException(f"Failed to process message: {str(e)}")
    
    async def send_message_streaming(
        self,
        conversation_id: str,
        content: str,
        streaming_callback: Callable[[str], None],
        message_type: str = "text",
        model: Optional[str] = None
    ) -> MessageResponse:
        """
        Send a message with streaming response
        
        Args:
            conversation_id: The conversation ID
            content: Message content
            streaming_callback: Callback for streaming tokens
            message_type: Type of message
            model: Optional model override
            
        Returns:
            MessageResponse with final AI response
        """
        logger.info(f"Processing streaming message for conversation {conversation_id}")
        
        try:
            # Verify conversation and quota (same as regular message)
            conversation = await self.conversation_service.get_conversation(conversation_id)
            if not conversation:
                raise ConversationNotFoundException(f"Conversation {conversation_id} not found")
            
            estimated_tokens = self.cost_tracker.count_tokens(content, model or conversation.model_name)
            quota_status = await self.cost_tracker.check_user_quota(self.db, estimated_tokens)
            
            if not quota_status["allowed"]:
                raise QuotaExceededException(
                    f"Quota exceeded: {quota_status.get('reason', 'Unknown reason')}"
                )
            
            # Save user message
            user_message_data = MessageCreate(
                content=content,
                role="user"
            )
            
            user_message = await self.message_service.create_message(conversation_id, user_message_data)
            # Capture message ID immediately to avoid lazy loading later
            user_message_id = user_message.message_id
            
            # Get conversation context
            conversation_history = await self.message_service.get_conversation_messages(
                conversation_id, 
                limit=20
            )
            
            # Get assistant client
            assistant_client = assistant_manager.get_client(self.user_uuid, conversation_id)
            
            # Set conversation context
            if len(conversation_history) > 1:
                context_messages = [
                    {"role": msg.role, "content": msg.content} 
                    for msg in conversation_history[:-1]
                ]
                assistant_client.set_conversation_context(context_messages)
            
            # Process message with streaming
            ai_response_data = await assistant_client.send_message_streaming(
                content,
                streaming_callback,
                message_type=message_type,
                metadata={
                    "conversation_id": conversation_id,
                    "user_message_id": user_message_id,
                    "model": model or conversation.model_name
                }
            )
            
            # Save AI response message with appropriate status based on cancellation
            ai_message_data = MessageCreate(
                content=ai_response_data["content"],
                role="assistant",
                status="cancelled" if ai_response_data.get("was_cancelled", False) else "completed"
            )
            
            ai_message = await self.message_service.create_message(conversation_id, ai_message_data)
            # Capture all needed values immediately to avoid lazy loading later
            ai_message_db_id = ai_message.id
            ai_message_id = ai_message.message_id
            ai_message_conversation_id = ai_message.conversation_id
            ai_message_role = ai_message.role
            ai_message_content = ai_message.content
            ai_message_extra_metadata = ai_message.extra_metadata or {}
            ai_message_created_at = ai_message.created_at
            
            # Log cancellation if it occurred
            if ai_response_data.get("was_cancelled", False):
                logger.info(f"Message {ai_message.message_id} created with cancelled status due to stream cancellation")
            
            # Track costs
            await self.cost_tracker.track_usage(
                db=self.db,
                operation_type="chat_streaming",
                model=model or conversation.model_name,
                input_text=content,
                output_text=ai_response_data["content"],
                conversation_id=conversation_id,
                additional_metadata={
                    "user_message_id": user_message_id,
                    "ai_message_id": ai_message_id,
                    "streaming": True,
                    "was_cancelled": ai_response_data.get("was_cancelled", False),
                    "plots": ai_response_data.get("plots", [])
                }
            )
            
            # Update conversation
            await self.conversation_service.update_conversation_activity(conversation_id)
            
            logger.info(f"Streaming message processed successfully for conversation {conversation_id}")
            
            return MessageResponse(
                id=ai_message_db_id,
                message_id=ai_message_id,
                conversation_id=ai_message_conversation_id,
                role=ai_message_role,
                content=ai_message_content,
                total_tokens=ai_response_data.get("total_tokens", 0),
                cost_usd=ai_response_data.get("cost_usd", 0.0),
                model_name=model or conversation.model_name,
                finish_reason=ai_response_data.get("finish_reason"),
                extra_metadata=ai_message_extra_metadata,
                created_at=ai_message_created_at
            )
            
        except Exception as e:
            logger.error(f"Error processing streaming message for conversation {conversation_id}: {e}")
            raise MessageProcessingException(f"Failed to process streaming message: {str(e)}")
    
    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[MessageResponse]:
        """
        Get conversation message history
        
        Args:
            conversation_id: The conversation ID
            limit: Number of messages to retrieve
            offset: Offset for pagination
            
        Returns:
            List of MessageResponse objects
        """
        try:
            # Verify conversation belongs to user
            conversation = await self.conversation_service.get_conversation(conversation_id)
            if not conversation:
                raise ConversationNotFoundException(f"Conversation {conversation_id} not found")
            
            messages = await self.message_service.get_conversation_messages(
                conversation_id, 
                limit=limit, 
                offset=offset
            )
            
            return [
                MessageResponse(
                    id=msg.id,
                    message_id=msg.message_id,
                    conversation_id=msg.conversation_id,
                    role=msg.role,
                    content=msg.content,
                    total_tokens=msg.total_tokens or 0,
                    cost_usd=msg.cost_usd or 0.0,
                    model_name=msg.model_name,
                    finish_reason=None,  # Not stored in database
                    extra_metadata=msg.extra_metadata or {},
                    created_at=msg.created_at
                )
                for msg in messages
            ]
            
        except Exception as e:
            logger.error(f"Error getting conversation history for {conversation_id}: {e}")
            raise
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation and all its messages
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            True if deleted successfully
        """
        try:
            # Verify conversation belongs to user
            conversation = await self.conversation_service.get_conversation(conversation_id)
            if not conversation:
                raise ConversationNotFoundException(f"Conversation {conversation_id} not found")
            
            # Delete messages first
            await self.message_service.delete_conversation_messages(conversation_id)
            
            # Delete conversation
            success = await self.conversation_service.delete_conversation(conversation_id)
            
            # Clean up assistant client
            assistant_manager.remove_client(self.user_uuid, conversation_id)
            
            logger.info(f"Deleted conversation {conversation_id} for user {self.user_uuid}")
            return success
            
        except Exception as e:
            logger.error(f"Error deleting conversation {conversation_id}: {e}")
            raise
    
    async def get_user_conversations(
        self,
        limit: int = 20,
        offset: int = 0
    ) -> List[ConversationResponse]:
        """
        Get user's conversations
        
        Args:
            limit: Number of conversations to retrieve
            offset: Offset for pagination
            
        Returns:
            List of ConversationResponse objects
        """
        try:
            conversations = await self.conversation_service.get_user_conversations(
                limit=limit, 
                offset=offset
            )
            
            return [
                ConversationResponse(
                    id=conv.id,
                    conversation_id=conv.conversation_id,
                    title=conv.title,
                    description=conv.description,
                    status=conv.status,
                    model_name=conv.model_name,
                    temperature=conv.temperature,
                    max_tokens=conv.max_tokens,
                    memory_enabled=conv.memory_enabled,
                    message_count=conv.message_count or 0,
                    total_tokens_used=conv.total_tokens_used,
                    total_cost_usd=conv.total_cost_usd,
                    is_pinned=conv.is_pinned,
                    is_shared=conv.is_shared,
                    topics=conv.topics or [],
                    tags=conv.tags or [],
                    user_rating=conv.user_rating,
                    quality_score=conv.quality_score,
                    created_at=conv.created_at,
                    updated_at=conv.updated_at,
                    last_message_at=conv.last_message_at
                )
                for conv in conversations
            ]
            
        except Exception as e:
            logger.error(f"Error getting conversations for user {self.user_uuid}: {e}")
            raise
    
    async def clear_conversation_memory(self, conversation_id: str) -> bool:
        """
        Clear the AI assistant's memory for a conversation
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            True if cleared successfully
        """
        try:
            assistant_client = assistant_manager.get_client(self.user_uuid, conversation_id)
            assistant_client.clear_conversation_memory()
            
            logger.info(f"Cleared memory for conversation {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing memory for conversation {conversation_id}: {e}")
            return False
    
    @handle_openai_errors(max_retries=3)
    async def generate_ai_response_only(
        self,
        conversation_id: str,
        content: str,
        message_type: str = "text",
        model: Optional[str] = None
    ) -> MessageResponse:
        """
        Generate an AI response only (for message editing scenarios)
        
        This method generates an AI response without creating a new user message.
        Used when editing existing user messages where we don't want to duplicate
        the user message in the conversation.
        
        Args:
            conversation_id: The conversation ID
            content: The user message content to respond to
            message_type: Type of message
            model: Optional model override
            
        Returns:
            MessageResponse with AI response only
        """
        logger.info(f"Generating AI response only for conversation {conversation_id}")
        
        try:
            # Verify conversation exists and belongs to user
            conversation = await self.conversation_service.get_conversation(conversation_id)
            if not conversation:
                raise ConversationNotFoundException(f"Conversation {conversation_id} not found")
            
            # Store model name to avoid accessing detached SQLAlchemy object later
            model_name = model or conversation.model_name or "gpt-4"
            
            # Check quota before processing
            estimated_tokens = self.cost_tracker.count_tokens(content, model_name)
            quota_status = await self.cost_tracker.check_user_quota(self.db, estimated_tokens)
            
            if not quota_status["allowed"]:
                raise QuotaExceededException(
                    f"Quota exceeded: {quota_status.get('reason', 'Unknown reason')}"
                )
            
            # Get conversation context (all existing messages)
            conversation_history = await self.message_service.get_conversation_messages(
                conversation_id, 
                limit=20  # Last 20 messages for context
            )
            
            # Get assistant client
            assistant_client = assistant_manager.get_client(self.user_uuid, conversation_id)
            
            # Set conversation context with all existing messages
            if conversation_history:
                context_messages = [
                    {"role": msg.role, "content": msg.content} 
                    for msg in conversation_history
                ]
                assistant_client.set_conversation_context(context_messages)
            
            # Process message with AI (using the edited content)
            ai_response_data = await assistant_client.send_message(
                content,
                message_type=message_type,
                metadata={
                    "conversation_id": conversation_id,
                    "model": model_name,
                    "edit_response": True  # Mark this as an edit response
                }
            )
            
            # Save AI response message only
            ai_message_data = MessageCreate(
                content=ai_response_data["content"],
                role="assistant"
            )
            
            ai_message = await self.message_service.create_message(conversation_id, ai_message_data)
            # Capture all needed values immediately to avoid lazy loading later
            ai_message_db_id = ai_message.id
            ai_message_id = ai_message.message_id
            ai_message_conversation_id = ai_message.conversation_id
            ai_message_role = ai_message.role
            ai_message_content = ai_message.content
            ai_message_extra_metadata = ai_message.extra_metadata or {}
            ai_message_created_at = ai_message.created_at
            
            # Track costs
            try:
                await self.cost_tracker.track_usage(
                    db=self.db,
                    operation_type="chat_edit",
                    model=model_name,
                    input_text=content,
                    output_text=ai_response_data["content"],
                    conversation_id=conversation_id,
                    additional_metadata={
                        "ai_message_id": ai_message_id,
                        "plots": ai_response_data.get("plots", []),
                        "is_edit_response": True
                    }
                )
            except Exception as cost_error:
                logger.warning(f"Cost tracking failed (non-critical): {cost_error}")
                # Continue without failing the entire operation
            
            # Update conversation
            await self.conversation_service.update_conversation_activity(conversation_id)
            
            logger.info(f"AI response generated successfully for conversation {conversation_id}")
            
            return MessageResponse(
                id=ai_message_db_id,
                message_id=ai_message_id,
                conversation_id=ai_message_conversation_id,
                role=ai_message_role,
                content=ai_message_content,
                total_tokens=ai_response_data.get("total_tokens", 0),
                cost_usd=ai_response_data.get("cost_usd", 0.0),
                model_name=model_name,
                finish_reason=ai_response_data.get("finish_reason"),
                extra_metadata=ai_message_extra_metadata,
                created_at=ai_message_created_at
            )
            
        except Exception as e:
            logger.error(f"Error generating AI response for conversation {conversation_id}: {e}")
            raise MessageProcessingException(f"Failed to generate AI response: {str(e)}")

    @handle_openai_errors(max_retries=3)
    async def generate_ai_response_only_streaming(
        self,
        conversation_id: str,
        content: str,
        streaming_callback: Callable[[str], None],
        message_type: str = "text",
        model: Optional[str] = None
    ) -> MessageResponse:
        """
        Generate an AI response only with streaming (for message editing scenarios with streaming)
        
        This method generates an AI response with streaming without creating a new user message.
        Used when editing existing user messages and wanting real-time streaming response.
        
        Args:
            conversation_id: The conversation ID
            content: The user message content to respond to
            streaming_callback: Callback for streaming tokens
            message_type: Type of message
            model: Optional model override
            
        Returns:
            MessageResponse with AI response only
        """
        logger.info(f"Generating streaming AI response only for conversation {conversation_id}")
        
        try:
            # Verify conversation exists and belongs to user
            conversation = await self.conversation_service.get_conversation(conversation_id)
            if not conversation:
                raise ConversationNotFoundException(f"Conversation {conversation_id} not found")
            
            # Store model name to avoid accessing detached SQLAlchemy object later
            model_name = model or conversation.model_name or "gpt-4"
            
            # Check quota before processing
            estimated_tokens = self.cost_tracker.count_tokens(content, model_name)
            quota_status = await self.cost_tracker.check_user_quota(self.db, estimated_tokens)
            
            if not quota_status["allowed"]:
                raise QuotaExceededException(
                    f"Quota exceeded: {quota_status.get('reason', 'Unknown reason')}"
                )
            
            # Get conversation context (all existing messages)
            conversation_history = await self.message_service.get_conversation_messages(
                conversation_id, 
                limit=20  # Last 20 messages for context
            )
            
            # Get assistant client
            assistant_client = assistant_manager.get_client(self.user_uuid, conversation_id)
            
            # Set conversation context with all existing messages
            if conversation_history:
                context_messages = [
                    {"role": msg.role, "content": msg.content} 
                    for msg in conversation_history
                ]
                assistant_client.set_conversation_context(context_messages)
            
            # Process message with AI using streaming (using the edited content)
            ai_response_data = await assistant_client.send_message_streaming(
                content,
                streaming_callback,
                message_type=message_type,
                metadata={
                    "conversation_id": conversation_id,
                    "model": model_name,
                    "edit_response": True  # Mark this as an edit response
                }
            )
            
            # Save AI response message only with appropriate status based on cancellation
            ai_message_data = MessageCreate(
                content=ai_response_data["content"],
                role="assistant",
                status="cancelled" if ai_response_data.get("was_cancelled", False) else "completed"
            )
            
            ai_message = await self.message_service.create_message(conversation_id, ai_message_data)
            # Capture all needed values immediately to avoid lazy loading later
            ai_message_db_id = ai_message.id
            ai_message_id = ai_message.message_id
            ai_message_conversation_id = ai_message.conversation_id
            ai_message_role = ai_message.role
            ai_message_content = ai_message.content
            ai_message_extra_metadata = ai_message.extra_metadata or {}
            ai_message_created_at = ai_message.created_at
            
            # Log cancellation if it occurred
            if ai_response_data.get("was_cancelled", False):
                logger.info(f"Edit message {ai_message.message_id} created with cancelled status due to stream cancellation")
            
            # Track costs
            try:
                await self.cost_tracker.track_usage(
                    db=self.db,
                    operation_type="chat_edit_streaming",
                    model=model_name,
                    input_text=content,
                    output_text=ai_response_data["content"],
                    conversation_id=conversation_id,
                    additional_metadata={
                        "ai_message_id": ai_message_id,
                        "plots": ai_response_data.get("plots", []),
                        "is_edit_response": True,
                        "streaming": True,
                        "was_cancelled": ai_response_data.get("was_cancelled", False)
                    }
                )
            except Exception as cost_error:
                logger.warning(f"Cost tracking failed (non-critical): {cost_error}")
                # Continue without failing the entire operation
            
            # Update conversation
            await self.conversation_service.update_conversation_activity(conversation_id)
            
            logger.info(f"Streaming AI response generated successfully for conversation {conversation_id}")
            
            return MessageResponse(
                id=ai_message_db_id,
                message_id=ai_message_id,
                conversation_id=ai_message_conversation_id,
                role=ai_message_role,
                content=ai_message_content,
                total_tokens=ai_response_data.get("total_tokens", 0),
                cost_usd=ai_response_data.get("cost_usd", 0.0),
                model_name=model_name,
                finish_reason=ai_response_data.get("finish_reason"),
                extra_metadata=ai_message_extra_metadata,
                created_at=ai_message_created_at
            )
            
        except Exception as e:
            logger.error(f"Error generating streaming AI response for conversation {conversation_id}: {e}")
            raise MessageProcessingException(f"Failed to generate streaming AI response: {str(e)}") 