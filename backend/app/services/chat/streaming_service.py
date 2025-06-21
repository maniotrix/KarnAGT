"""
Streaming Service

This service handles real-time streaming of chat responses using Server-Sent Events (SSE),
integrating with the FastAPI streaming handler and aicore streaming capabilities.
"""

import asyncio
import json
from typing import AsyncGenerator, Dict, Any, Optional, Callable, List
from datetime import datetime

from app.integrations.openai.streaming_handler import streaming_manager, StreamingHandler
from app.services.chat.chat_service import ChatService
from app.models.database.user import User
from app.models.schemas.chat_schemas import MessageStreamResponse, MessageCreate

from aicore.logger import get_logger

# Set up logger
logger = get_logger(__name__)


class StreamingService:
    """
    Service for managing streaming chat responses
    
    Features:
    - Real-time streaming using SSE
    - Integration with chat service
    - Stream lifecycle management
    - Error handling for streaming
    - Cancellation support with partial message saving
    """
    
    def __init__(self, chat_service: ChatService, user: User):
        """
        Initialize the streaming service
        
        Args:
            chat_service: ChatService instance
            user: User instance
        """
        self.chat_service = chat_service
        self.user = user
        self.user_id = user.id
        self.user_uuid = user.user_id
        
        logger.info(f"StreamingService initialized for user {self.user_uuid}")
    
    async def stream_message_response(
        self,
        conversation_id: str,
        content: str,
        message_type: str = "text",
        model: Optional[str] = None,
        staging_files: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream a message response using Server-Sent Events
        
        Args:
            conversation_id: The conversation ID
            content: Message content
            message_type: Type of message
            model: Optional model override
            
        Yields:
            SSE-formatted streaming events
        """
        logger.info(f"Starting message stream for conversation {conversation_id}")
        
        # Create streaming handler
        stream_handler = streaming_manager.create_stream(self.user_id, conversation_id)
        
        try:
            # Start the streaming generator
            stream_generator = stream_handler.start_streaming()
            
            # Create a task to process the message in the background
            message_task = asyncio.create_task(
                self._process_streaming_message(
                    stream_handler,
                    conversation_id,
                    content,
                    message_type,
                    model,
                    staging_files
                )
            )
            
            # Yield streaming events
            async for event in stream_generator:
                yield event
                
                # Note: Partial message saving removed - now handled in chat service
                # based on cancellation status from AI core
            
            # Wait for message processing to complete and get the result
            try:
                final_response = await message_task
                logger.info(f"Message task completed with response: {type(final_response)}")
                
            except Exception as e:
                logger.error(f"Error in message processing task: {e}")
                error_event = stream_handler._format_sse_event("error", {
                    "error": str(e),
                    "stream_id": stream_handler.stream_id,
                    "timestamp": datetime.utcnow().isoformat()
                })
                yield error_event
            
        except Exception as e:
            logger.error(f"Error in streaming response: {e}")
            
            # Send error event
            error_event = stream_handler._format_sse_event("error", {
                "error": str(e),
                "stream_id": stream_handler.stream_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            yield error_event
            
        finally:
            # Clean up the stream
            streaming_manager.remove_stream(stream_handler.stream_id)
            logger.info(f"Completed message stream for conversation {conversation_id}")
    
    async def _process_streaming_message(
        self,
        stream_handler: StreamingHandler,
        conversation_id: str,
        content: str,
        message_type: str,
        model: Optional[str],
        staging_files: Optional[List[Dict[str, str]]] = None
    ):
        """
        Process the message with streaming in the background
        
        Args:
            stream_handler: The streaming handler
            conversation_id: The conversation ID
            content: Message content
            message_type: Type of message
            model: Optional model override
            
        Returns:
            MessageResponse or None
        """
        try:
            # Get assistant client and set it on the streaming handler for cancellation
            from app.integrations.openai.assistant_client import assistant_manager
            assistant_client = assistant_manager.get_client(self.user.user_id, conversation_id)
            stream_handler.set_assistant_client(assistant_client)
            
            # Use the chat service to send message with streaming
            response = await self.chat_service.send_message_streaming(
                conversation_id=conversation_id,
                content=content,
                streaming_callback=stream_handler.streaming_callback,
                message_type=message_type,
                model=model,
                staging_files=staging_files
            )
            
            logger.info(f"Streaming message processing completed for conversation {conversation_id}")
            
            # Only stop streaming if not cancelled (let cancellation handling do its work)
            if not stream_handler.is_cancelled:
                stream_handler.stop_streaming()
                logger.info(f"Streaming stopped normally for conversation {conversation_id}")
            else:
                logger.info(f"Streaming was cancelled for conversation {conversation_id}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing streaming message: {e}")
            # Stop streaming on error
            stream_handler.stop_streaming()
            raise
    
    async def cancel_stream(self, stream_id: str, reason: str = "user_requested") -> bool:
        """
        Cancel a specific stream
        
        Args:
            stream_id: The stream ID to cancel
            reason: Reason for cancellation
            
        Returns:
            True if stream was cancelled, False if not found
        """
        result = streaming_manager.cancel_stream(stream_id, reason)
        if result:
            logger.info(f"Stream {stream_id} cancelled successfully, reason: {reason}")
        else:
            logger.warning(f"Stream {stream_id} not found for cancellation")
        return result
    
    async def cancel_user_streams(self, reason: str = "user_requested") -> int:
        """
        Cancel all active streams for the current user
        
        Args:
            reason: Reason for cancellation
            
        Returns:
            Number of streams cancelled
        """
        cancelled_count = streaming_manager.cancel_user_streams(self.user_id, reason)
        logger.info(f"Cancelled {cancelled_count} streams for user {self.user_uuid}, reason: {reason}")
        return cancelled_count
    
    async def get_user_active_streams(self) -> list[str]:
        """
        Get all active stream IDs for the current user
        
        Returns:
            List of active stream IDs
        """
        active_streams = streaming_manager.get_user_active_streams(self.user_id)
        logger.debug(f"User {self.user_uuid} has {len(active_streams)} active streams")
        return active_streams
    
    async def stream_conversation_history(
        self,
        conversation_id: str,
        limit: int = 50
    ) -> AsyncGenerator[str, None]:
        """
        Stream conversation history as SSE events
        
        Args:
            conversation_id: The conversation ID
            limit: Number of messages to stream
            
        Yields:
            SSE-formatted events with message history
        """
        logger.info(f"Streaming conversation history for {conversation_id}")
        
        try:
            # Get conversation history
            messages = await self.chat_service.get_conversation_history(
                conversation_id, 
                limit=limit
            )
            
            # Send initial event
            yield self._format_sse_event("history_start", {
                "conversation_id": conversation_id,
                "total_messages": len(messages),
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Stream each message
            for i, message in enumerate(messages):
                message_data = {
                    "message": {
                        "id": message.id,
                        "message_id": message.message_id,
                        "conversation_id": message.conversation_id,
                        "content": message.content,
                        "role": message.role,
                        "message_type": getattr(message, 'message_type', 'text'),
                        "status": getattr(message, 'status', 'completed'),
                        "created_at": message.created_at.isoformat(),
                        "metadata": message.extra_metadata or {}
                    },
                    "index": i,
                    "total": len(messages)
                }
                
                yield self._format_sse_event("message", message_data)
                
                # Add small delay to prevent overwhelming the client
                await asyncio.sleep(0.01)
            
            # Send completion event
            yield self._format_sse_event("history_complete", {
                "conversation_id": conversation_id,
                "messages_streamed": len(messages),
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error streaming conversation history: {e}")
            
            yield self._format_sse_event("error", {
                "error": str(e),
                "conversation_id": conversation_id,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def stream_user_conversations(
        self,
        limit: int = 20
    ) -> AsyncGenerator[str, None]:
        """
        Stream user's conversations as SSE events
        
        Args:
            limit: Number of conversations to stream
            
        Yields:
            SSE-formatted events with conversations
        """
        logger.info(f"Streaming conversations for user {self.user_uuid}")
        
        try:
            # Get user conversations
            conversations = await self.chat_service.get_user_conversations(limit=limit)
            
            # Send initial event
            yield self._format_sse_event("conversations_start", {
                "user_id": self.user_uuid,
                "total_conversations": len(conversations),
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Stream each conversation
            for i, conversation in enumerate(conversations):
                conversation_data = {
                    "conversation": {
                        "id": conversation.id,
                        "conversation_id": conversation.conversation_id,
                        "title": conversation.title,
                        "model": conversation.model_name,
                        "created_at": conversation.created_at.isoformat(),
                        "updated_at": conversation.updated_at.isoformat(),
                        "message_count": conversation.message_count,
                        "status": conversation.status
                    },
                    "index": i,
                    "total": len(conversations)
                }
                
                yield self._format_sse_event("conversation", conversation_data)
                
                # Add small delay
                await asyncio.sleep(0.01)
            
            # Send completion event
            yield self._format_sse_event("conversations_complete", {
                "user_id": self.user_uuid,
                "conversations_streamed": len(conversations),
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error streaming conversations: {e}")
            
            yield self._format_sse_event("error", {
                "error": str(e),
                "user_id": self.user_uuid,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    def _format_sse_event(self, event_type: str, data: Dict[str, Any]) -> str:
        """
        Format data as an SSE event
        
        Args:
            event_type: The type of event
            data: The event data
            
        Returns:
            Formatted SSE event string
        """
        event_data = {
            "type": event_type,
            "data": data
        }
        
        return f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"
    
    async def get_active_streams_count(self) -> int:
        """
        Get the number of active streams for the user
        
        Returns:
            Number of active streams
        """
        active_count = sum(
            1 for handler in streaming_manager.streams.values()
            if handler.user_id == self.user_id and handler.is_streaming
        )
        
        logger.debug(f"User {self.user_uuid} has {active_count} active streams")
        return active_count
    
    async def cleanup_user_streams(self):
        """Clean up all streams for the user"""
        user_streams = [
            stream_id for stream_id, handler in streaming_manager.streams.items()
            if handler.user_id == self.user_id
        ]
        
        for stream_id in user_streams:
            streaming_manager.remove_stream(stream_id)
        
        logger.info(f"Cleaned up {len(user_streams)} streams for user {self.user_uuid}")
    
    async def stream_edit_message_response(
        self,
        conversation_id: str,
        message_id: str,
        content: str,
        message_type: str = "text",
        model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream an edit message response using Server-Sent Events
        
        This method handles editing a user message and streaming the new AI response.
        It performs the same edit operations as the non-streaming version but with real-time streaming.
        
        Args:
            conversation_id: The conversation ID
            message_id: The message ID to edit
            content: New message content
            message_type: Type of message
            model: Optional model override
            
        Yields:
            SSE-formatted streaming events
        """
        logger.info(f"Starting edit message stream for message {message_id} in conversation {conversation_id}")
        
        # Create streaming handler
        stream_handler = streaming_manager.create_stream(self.user_id, conversation_id)
        
        try:
            # Start the streaming generator
            stream_generator = stream_handler.start_streaming()
            
            # Create a task to process the edit in the background
            edit_task = asyncio.create_task(
                self._process_streaming_edit_message(
                    stream_handler,
                    conversation_id,
                    message_id,
                    content,
                    message_type,
                    model
                )
            )
            
            # Yield streaming events
            async for event in stream_generator:
                yield event
            
            # Wait for edit processing to complete and get the result
            try:
                final_response = await edit_task
                logger.info(f"Edit message task completed with response: {type(final_response)}")
                
            except Exception as e:
                logger.error(f"Error in edit message processing task: {e}")
                error_event = stream_handler._format_sse_event("error", {
                    "error": str(e),
                    "stream_id": stream_handler.stream_id,
                    "timestamp": datetime.utcnow().isoformat()
                })
                yield error_event
            
        except Exception as e:
            logger.error(f"Error in streaming edit response: {e}")
            
            # Send error event
            error_event = stream_handler._format_sse_event("error", {
                "error": str(e),
                "stream_id": stream_handler.stream_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            yield error_event
            
        finally:
            # Clean up the stream
            streaming_manager.remove_stream(stream_handler.stream_id)
            logger.info(f"Completed edit message stream for conversation {conversation_id}")
    
    async def _process_streaming_edit_message(
        self,
        stream_handler: StreamingHandler,
        conversation_id: str,
        message_id: str,
        content: str,
        message_type: str,
        model: Optional[str]
    ):
        """
        Process the edit message with streaming in the background
        
        Args:
            stream_handler: The streaming handler
            conversation_id: The conversation ID
            message_id: The message ID to edit
            content: New message content
            message_type: Type of message
            model: Optional model override
            
        Returns:
            MessageResponse or None
        """
        try:
            # Get assistant client and set it on the streaming handler for cancellation
            from app.integrations.openai.assistant_client import assistant_manager
            assistant_client = assistant_manager.get_client(self.user.user_id, conversation_id)
            stream_handler.set_assistant_client(assistant_client)
            
            # Import necessary services and modules for edit operations
            from app.services.chat.message_service import MessageService
            from app.models.schemas.chat_schemas import MessageUpdate
            from sqlalchemy import update
            from sqlalchemy.sql import func
            from app.models.database.message import Message
            
            # Step 1: Update the message content (validation already done at endpoint level)
            message_service = MessageService(self.chat_service.db, self.user)
            
            # Update the message content
            update_data = MessageUpdate(content=content, metadata={})
            updated_message = await message_service.update_message(message_id, update_data)
            
            # Mark as edited
            edit_query = update(Message).where(
                Message.message_id == message_id
            ).values(
                is_edited=True,
                edit_count=Message.edit_count + 1,
                updated_at=func.now()
            )
            await self.chat_service.db.execute(edit_query)
            await self.chat_service.db.commit()
            
            # Step 2: Delete all subsequent messages
            deleted_count = await message_service.delete_messages_after(message_id)
            logger.info(f"Deleted {deleted_count} subsequent messages")
            
            # Step 3: Extract existing OpenAI file IDs from the edited message
            openai_file_ids = []
            if updated_message.attachments:
                for attachment in updated_message.attachments:
                    if isinstance(attachment, dict) and 'openai_file_id' in attachment:
                        openai_file_ids.append(attachment['openai_file_id'])
                    
            logger.info(f"Extracted {len(openai_file_ids)} existing OpenAI file IDs for message editing")
            
            # Step 4: Generate new AI response with streaming (passing existing file IDs)
            response = await self.chat_service.generate_ai_response_only_streaming(
                conversation_id=conversation_id,
                content=content,
                streaming_callback=stream_handler.streaming_callback,
                message_type=message_type,
                model=model,
                openai_file_ids=openai_file_ids  # Pass existing file IDs
            )
            
            logger.info(f"Streaming edit message processing completed for conversation {conversation_id}")
            
            # Only stop streaming if not cancelled (let cancellation handling do its work)
            if not stream_handler.is_cancelled:
                stream_handler.stop_streaming()
                logger.info(f"Edit streaming stopped normally for conversation {conversation_id}")
            else:
                logger.info(f"Edit streaming was cancelled for conversation {conversation_id}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing streaming edit message: {e}")
            # Stop streaming on error
            stream_handler.stop_streaming()
            raise


# Utility functions for creating streaming responses
async def create_message_stream(
    chat_service: ChatService,
    user: User,
    conversation_id: str,
    content: str,
    message_type: str = "text",
    model: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Utility function to create a message streaming response
    
    Args:
        chat_service: ChatService instance
        user: User instance
        conversation_id: The conversation ID
        content: Message content
        message_type: Type of message
        model: Optional model override
        
    Yields:
        SSE-formatted streaming events
    """
    streaming_service = StreamingService(chat_service, user)
    
    async for event in streaming_service.stream_message_response(
        conversation_id, content, message_type, model
    ):
        yield event


async def create_history_stream(
    chat_service: ChatService,
    user: User,
    conversation_id: str,
    limit: int = 50
) -> AsyncGenerator[str, None]:
    """
    Utility function to create a conversation history streaming response
    
    Args:
        chat_service: ChatService instance
        user: User instance
        conversation_id: The conversation ID
        limit: Number of messages to stream
        
    Yields:
        SSE-formatted events with message history
    """
    streaming_service = StreamingService(chat_service, user)
    
    async for event in streaming_service.stream_conversation_history(conversation_id, limit):
        yield event


async def create_edit_message_stream(
    chat_service: ChatService,
    user: User,
    conversation_id: str,
    message_id: str,
    content: str,
    message_type: str = "text",
    model: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Utility function to create an edit message streaming response
    
    Args:
        chat_service: ChatService instance
        user: User instance
        conversation_id: The conversation ID
        message_id: The message ID to edit
        content: New message content
        message_type: Type of message
        model: Optional model override
        
    Yields:
        SSE-formatted streaming events
    """
    streaming_service = StreamingService(chat_service, user)
    
    async for event in streaming_service.stream_edit_message_response(
        conversation_id, message_id, content, message_type, model
    ):
        yield event 