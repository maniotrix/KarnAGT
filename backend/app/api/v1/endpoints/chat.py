"""
Chat API Endpoints

This module provides REST API endpoints for chat functionality including:
- Creating and managing conversations
- Sending messages and receiving AI responses
- Real-time streaming of AI responses
- Streaming cancellation and management
- Conversation history and search
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.core.database import get_db
from app.core.exceptions import (
    ConversationNotFoundException,
    MessageProcessingException,
    QuotaExceededException
)
from app.models.database.user import User
from app.models.schemas.chat_schemas import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationListResponse,
    ConversationDetailResponse,
    MessageCreate,
    MessageResponse,
    MessageListResponse,
    ChatStreamRequest,
    ConversationShareRequest,
    ConversationShareResponse,
    ConversationSearchRequest,
    ConversationBulkAction,
    ConversationBulkResponse,
    MessageUpdate
)
from app.models.schemas.common_schemas import BaseResponse
from app.api.v1.dependencies.auth import (
    get_current_verified_user,
    check_chat_quota
)
from app.services.chat.chat_service import ChatService
from app.services.chat.streaming_service import StreamingService

from aicore.logger import get_logger

# Set up logger
logger = get_logger(__name__)

router = APIRouter()


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
) -> ConversationResponse:
    """
    Create a new conversation
    
    - **title**: Optional conversation title (auto-generated if not provided)
    - **model_name**: AI model to use (gpt-4, gpt-3.5-turbo)
    - **system_prompt**: Optional system prompt for the conversation
    - **memory_enabled**: Enable memory features for this conversation
    """
    logger.info(f"Creating new conversation for user {current_user.user_id}")
    
    try:
        chat_service = ChatService(db, current_user)
        conversation = await chat_service.start_conversation(
            title=conversation_data.title,
            model=conversation_data.model_name or "gpt-4",
            system_prompt=conversation_data.system_prompt
        )
        return conversation
        
    except QuotaExceededException as e:
        logger.warning(f"Quota exceeded for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create conversation"
        )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = Query(20, ge=1, le=100, description="Number of conversations to return"),
    offset: int = Query(0, ge=0, description="Number of conversations to skip"),
    search: Optional[str] = Query(None, description="Search in conversation titles"),
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
) -> ConversationListResponse:
    """
    List user's conversations with pagination
    
    Returns conversations sorted by last activity (most recent first)
    """
    logger.info(f"Listing conversations for user {current_user.user_id}")
    
    try:
        chat_service = ChatService(db, current_user)
        conversations = await chat_service.get_user_conversations(limit=limit, offset=offset)
        
        # Count total conversations for pagination
        from app.services.chat.conversation_service import ConversationService
        conversation_service = ConversationService(db, current_user)
        total = await conversation_service.count_user_conversations()
        
        # Calculate pagination metadata
        from app.models.schemas.common_schemas import PaginationMeta
        import math
        
        pages = math.ceil(total / limit) if total > 0 else 0
        current_page = (offset // limit) + 1
        
        pagination = PaginationMeta(
            page=current_page,
            size=limit,
            total=total,
            pages=pages,
            has_next=offset + limit < total,
            has_prev=offset > 0
        )
        
        return ConversationListResponse(
            success=True,
            message="Conversations retrieved successfully",
            data=conversations,
            pagination=pagination
        )
        
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversations"
        )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    include_messages: bool = Query(True, description="Include recent messages"),
    message_limit: int = Query(20, ge=1, le=100, description="Number of messages to include"),
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
) -> ConversationDetailResponse:
    """
    Get conversation details with optional message history
    """
    logger.info(f"Getting conversation {conversation_id} for user {current_user.user_id}")
    
    try:
        chat_service = ChatService(db, current_user)
        
        # Get conversation details
        from app.services.chat.conversation_service import ConversationService
        conversation_service = ConversationService(db, current_user)
        conversation = await conversation_service.get_conversation(conversation_id)
        
        if not conversation:
            raise ConversationNotFoundException(f"Conversation {conversation_id} not found")
        
        # Convert to response model
        conversation_response = ConversationResponse(
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
        
        # Get recent messages if requested
        recent_messages = []
        if include_messages:
            messages = await chat_service.get_conversation_history(
                conversation_id, 
                limit=message_limit
            )
            recent_messages = messages
        
        return ConversationDetailResponse(
            success=True,
            message="Conversation retrieved successfully",
            conversation=conversation_response,
            recent_messages=recent_messages,
            message_count=conversation.message_count,
            can_continue=conversation.status == "active"
        )
        
    except ConversationNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation"
        )


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: str,
    message_data: MessageCreate,
    current_user: User = Depends(check_chat_quota),  # Includes quota check
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Send a message to the conversation and get AI response
    
    This endpoint processes the message synchronously and returns the complete AI response.
    For real-time streaming responses, use the /stream endpoint instead.
    """
    logger.info(f"Sending message to conversation {conversation_id} for user {current_user.user_id}")
    
    try:
        chat_service = ChatService(db, current_user)
        
        # Send message and get AI response
        response = await chat_service.send_message(
            conversation_id=conversation_id,
            content=message_data.content,
            message_type="text"
        )
        
        return response
        
    except ConversationNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except QuotaExceededException as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )
    except MessageProcessingException as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error sending message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message"
        )


@router.post("/conversations/{conversation_id}/stream")
async def stream_message(
    conversation_id: str,
    message_data: MessageCreate,
    current_user: User = Depends(check_chat_quota),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """
    Send a message and stream the AI response in real-time
    
    This endpoint uses Server-Sent Events (SSE) to stream the AI response token by token.
    Perfect for providing a ChatGPT-like experience with real-time feedback.
    
    The response will be a stream of SSE events:
    - `token`: Individual tokens as they're generated
    - `completion`: Final message with metadata
    - `error`: Any errors that occur during streaming
    - `cancelled`: Stream was cancelled due to client disconnection
    """
    logger.info(f"Starting streaming response for conversation {conversation_id}")
    
    try:
        chat_service = ChatService(db, current_user)
        streaming_service = StreamingService(chat_service, current_user)
        
        # Create the streaming generator with client disconnection detection
        async def stream_with_disconnection_detection():
            """Wrapper generator that detects client disconnection"""
            stream_generator = streaming_service.stream_message_response(
                conversation_id=conversation_id,
                content=message_data.content,
                message_type="text"
            )
            
            try:
                async for event in stream_generator:
                    # Check if client is still connected
                    if request and hasattr(request, 'is_disconnected') and await request.is_disconnected():
                        logger.info(f"Client disconnected for conversation {conversation_id}")
                        # Cancel any active streams for this user
                        await streaming_service.cancel_user_streams("client_disconnected")
                        break
                    
                    yield event
                    
            except Exception as e:
                logger.error(f"Error in stream with disconnection detection: {e}")
                # Try to cancel streams on error
                try:
                    await streaming_service.cancel_user_streams("stream_error")
                except:
                    pass
                raise
        
        # Return as Server-Sent Events stream
        return StreamingResponse(
            stream_with_disconnection_detection(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable Nginx buffering
            }
        )
        
    except ConversationNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error starting stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start streaming"
        )


@router.post("/stream/cancel/{stream_id}")
async def cancel_stream(
    stream_id: str,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a specific active stream
    
    This endpoint allows users to stop an active stream by its stream ID.
    When cancelled, any partial response will be saved with "cancelled" status.
    
    Args:
        stream_id: The ID of the stream to cancel
        
    Returns:
        Success response indicating whether the stream was cancelled
    """
    logger.info(f"Cancelling stream {stream_id} for user {current_user.user_id}")
    
    try:
        chat_service = ChatService(db, current_user)
        streaming_service = StreamingService(chat_service, current_user)
        
        # Cancel the specific stream
        cancelled = await streaming_service.cancel_stream(stream_id, "user_requested")
        
        if cancelled:
            return {
                "success": True,
                "message": f"Stream {stream_id} cancelled successfully",
                "stream_id": stream_id,
                "cancelled": True
            }
        else:
            # Stream not found - client tried to cancel but action failed
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=f"Stream {stream_id} has already completed and cannot be cancelled"
            )
            
    except Exception as e:
        logger.error(f"Error cancelling stream {stream_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel stream"
        )


@router.post("/stream/cancel-all")
async def cancel_all_user_streams(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel all active streams for the current user
    
    This endpoint allows users to stop all their active streams at once.
    Useful for cleanup or when switching contexts.
    
    Returns:
        Success response with count of cancelled streams
    """
    logger.info(f"Cancelling all streams for user {current_user.user_id}")
    
    try:
        chat_service = ChatService(db, current_user)
        streaming_service = StreamingService(chat_service, current_user)
        
        # Cancel all user streams
        cancelled_count = await streaming_service.cancel_user_streams("user_requested_all")
        
        return {
            "success": True,
            "message": f"Cancelled {cancelled_count} active streams",
            "cancelled_count": cancelled_count
        }
        
    except Exception as e:
        logger.error(f"Error cancelling all streams for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel streams"
        )


@router.get("/stream/active")
async def get_active_streams(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all active streams for the current user
    
    This endpoint returns information about all currently active streams
    for the authenticated user.
    
    Returns:
        List of active stream IDs and their status
    """
    logger.info(f"Getting active streams for user {current_user.user_id}")
    
    try:
        chat_service = ChatService(db, current_user)
        streaming_service = StreamingService(chat_service, current_user)
        
        # Get active streams
        active_streams = await streaming_service.get_user_active_streams()
        
        return {
            "success": True,
            "message": f"Found {len(active_streams)} active streams",
            "active_streams": active_streams,
            "count": len(active_streams)
        }
        
    except Exception as e:
        logger.error(f"Error getting active streams for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get active streams"
        )


@router.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse)
async def get_conversation_messages(
    conversation_id: str,
    limit: int = Query(50, ge=1, le=200, description="Number of messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
) -> MessageListResponse:
    """
    Get paginated message history for a conversation
    
    Messages are returned in chronological order (oldest first)
    """
    logger.info(f"Getting messages for conversation {conversation_id}")
    
    try:
        chat_service = ChatService(db, current_user)
        
        # Verify conversation exists and belongs to user
        from app.services.chat.conversation_service import ConversationService
        conversation_service = ConversationService(db, current_user)
        conversation = await conversation_service.get_conversation(conversation_id)
        
        if not conversation:
            raise ConversationNotFoundException(f"Conversation {conversation_id} not found")
        
        # Get messages
        messages = await chat_service.get_conversation_history(
            conversation_id,
            limit=limit,
            offset=offset
        )
        
        # Calculate pagination metadata for messages
        import math
        from app.models.schemas.common_schemas import PaginationMeta
        
        pages = math.ceil(conversation.message_count / limit) if conversation.message_count > 0 else 0
        current_page = (offset // limit) + 1
        
        pagination = PaginationMeta(
            page=current_page,
            size=limit,
            total=conversation.message_count,
            pages=pages,
            has_next=offset + limit < conversation.message_count,
            has_prev=offset > 0
        )
        
        return MessageListResponse(
            success=True,
            message="Messages retrieved successfully",
            data=messages,
            pagination=pagination
        )
        
    except ConversationNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve messages"
        )


@router.post("/conversations/{conversation_id}/messages/{message_id}/edit", response_model=MessageResponse)
async def edit_and_resend_message(
    conversation_id: str,
    message_id: str,
    update_data: MessageUpdate,
    current_user: User = Depends(check_chat_quota),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Edit a user message and generate a new AI response
    
    This endpoint:
    1. Updates the user message content
    2. Deletes all subsequent messages in the conversation  
    3. Generates a new AI response based on the edited message
    
    Only user messages can be edited and resent.
    """
    logger.info(f"Edit and resend message {message_id} in conversation {conversation_id}")
    
    try:
        from app.services.chat.message_service import MessageService
        message_service = MessageService(db, current_user)
        
        # Verify conversation exists and belongs to user
        from app.services.chat.conversation_service import ConversationService
        conversation_service = ConversationService(db, current_user)
        conversation = await conversation_service.get_conversation(conversation_id)
        
        if not conversation:
            raise ConversationNotFoundException(f"Conversation {conversation_id} not found")
        
        # Get the original message and verify it's a user message
        original_message = await message_service.get_message(message_id)
        if not original_message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Message {message_id} not found"
            )
        
        if original_message.role != "user":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only edit and resend user messages"
            )
        
        if not update_data.content or not update_data.content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content is required for edit and resend"
            )
        
        # Step 1: Update the message content
        updated_message = await message_service.update_message(message_id, update_data)
        
        # Mark as edited
        from sqlalchemy import update, delete, select
        from app.models.database.message import Message
        
        edit_query = update(Message).where(
            Message.message_id == message_id
        ).values(
            is_edited=True,
            edit_count=Message.edit_count + 1,
            updated_at=func.now()
        )
        await db.execute(edit_query)
        await db.commit()
        
        # Step 2: Delete all subsequent messages using the service method
        deleted_count = await message_service.delete_messages_after(message_id)
        logger.info(f"Deleted {deleted_count} subsequent messages")
        
        # Step 3: Extract existing OpenAI file IDs from the edited message
        openai_file_ids = []
        if updated_message.attachments:
            for attachment in updated_message.attachments:
                if isinstance(attachment, dict) and 'openai_file_id' in attachment:
                    openai_file_ids.append(attachment['openai_file_id'])
                    
        logger.info(f"Extracted {len(openai_file_ids)} existing OpenAI file IDs for message editing")
        
        # Step 4: Generate new AI response
        chat_service = ChatService(db, current_user)
        
        # Generate AI response with the edited content and existing file IDs
        ai_response = await chat_service.generate_ai_response_only(
            conversation_id=conversation_id,
            content=update_data.content,
            message_type="text",
            openai_file_ids=openai_file_ids  # Pass existing file IDs
        )
        
        logger.info(f"Successfully edited message {message_id} and generated new AI response")
        return ai_response
        
    except ConversationNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error in edit and resend for message {message_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to edit and resend message"
        )


@router.post("/conversations/{conversation_id}/messages/{message_id}/edit/stream")
async def edit_and_resend_message_streaming(
    conversation_id: str,
    message_id: str,
    update_data: MessageUpdate,
    current_user: User = Depends(check_chat_quota),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """
    Edit a user message and stream the new AI response in real-time
    
    This endpoint:
    1. Updates the user message content
    2. Deletes all subsequent messages in the conversation  
    3. Streams a new AI response based on the edited message
    
    Only user messages can be edited and resent.
    
    The response will be a stream of SSE events:
    - `token`: Individual tokens as they're generated
    - `completion`: Final message with metadata
    - `error`: Any errors that occur during streaming
    - `cancelled`: Stream was cancelled due to client disconnection
    """
    logger.info(f"Edit and stream message {message_id} in conversation {conversation_id}")
    
    try:
        chat_service = ChatService(db, current_user)
        
        # VALIDATION: Verify conversation and message exist before starting stream
        from app.services.chat.conversation_service import ConversationService
        from app.services.chat.message_service import MessageService
        
        conversation_service = ConversationService(db, current_user)
        message_service = MessageService(db, current_user)
        
        # Verify conversation exists and belongs to user
        conversation = await conversation_service.get_conversation(conversation_id)
        if not conversation:
            raise ConversationNotFoundException(f"Conversation {conversation_id} not found")
        
        # Get the original message and verify it exists
        original_message = await message_service.get_message(message_id)
        if not original_message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Message {message_id} not found"
            )
        
        # Verify it's a user message (convert to string to avoid SQLAlchemy issues)
        original_role = str(original_message.role) if hasattr(original_message.role, '__str__') else original_message.role
        if str(original_role) != "user":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only edit and resend user messages"
            )
        
        # Verify content is provided
        if not update_data.content or not update_data.content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content is required for edit and resend"
            )
        
        # All validations passed, now start streaming
        streaming_service = StreamingService(chat_service, current_user)
        
        # Create the streaming generator with client disconnection detection
        async def stream_edit_with_disconnection_detection():
            """Wrapper generator that detects client disconnection for edit streaming"""
            stream_generator = streaming_service.stream_edit_message_response(
                conversation_id=conversation_id,
                message_id=message_id,
                content=update_data.content,
                message_type="text"
            )
            
            try:
                async for event in stream_generator:
                    # Check if client is still connected
                    if request and hasattr(request, 'is_disconnected') and await request.is_disconnected():
                        logger.info(f"Client disconnected for edit stream in conversation {conversation_id}")
                        # Cancel any active streams for this user
                        await streaming_service.cancel_user_streams("client_disconnected")
                        break
                    
                    yield event
                    
            except Exception as e:
                logger.error(f"Error in edit stream with disconnection detection: {e}")
                # Try to cancel streams on error
                try:
                    await streaming_service.cancel_user_streams("stream_error")
                except:
                    pass
                raise
        
        # Return as Server-Sent Events stream
        return StreamingResponse(
            stream_edit_with_disconnection_detection(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable Nginx buffering
            }
        )
        
    except ConversationNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is (including 404 for message not found)
        raise
    except Exception as e:
        logger.error(f"Error starting edit stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start edit streaming"
        )


@router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    update_data: ConversationUpdate,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
) -> ConversationResponse:
    """
    Update conversation properties
    
    Allows updating title, description, tags, pinned status, etc.
    """
    logger.info(f"Updating conversation {conversation_id} for user {current_user.user_id}")
    
    try:
        from app.services.chat.conversation_service import ConversationService
        conversation_service = ConversationService(db, current_user)
        
        # Update conversation
        updated_conversation = await conversation_service.update_conversation(
            conversation_id,
            update_data
        )
        
        if not updated_conversation:
            raise ConversationNotFoundException(f"Conversation {conversation_id} not found")
        
        # Convert to response model
        return ConversationResponse(
            id=updated_conversation.id,
            conversation_id=updated_conversation.conversation_id,
            title=updated_conversation.title,
            description=updated_conversation.description,
            status=updated_conversation.status,
            model_name=updated_conversation.model_name,
            temperature=updated_conversation.temperature,
            max_tokens=updated_conversation.max_tokens,
            memory_enabled=updated_conversation.memory_enabled,
            message_count=updated_conversation.message_count,
            total_tokens_used=updated_conversation.total_tokens_used,
            total_cost_usd=updated_conversation.total_cost_usd,
            is_pinned=updated_conversation.is_pinned,
            is_shared=updated_conversation.is_shared,
            topics=updated_conversation.topics or [],
            tags=updated_conversation.tags or [],
            user_rating=updated_conversation.user_rating,
            quality_score=updated_conversation.quality_score,
            created_at=updated_conversation.created_at,
            updated_at=updated_conversation.updated_at,
            last_message_at=updated_conversation.last_message_at
        )
        
    except ConversationNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update conversation"
        )


@router.delete("/conversations/{conversation_id}", response_model=BaseResponse)
async def delete_conversation(
    conversation_id: str,
    permanent: bool = Query(False, description="Permanently delete (no soft delete)"),
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
) -> BaseResponse:
    """
    Delete a conversation
    
    By default performs a soft delete. Set permanent=true for hard delete.
    """
    logger.info(f"Deleting conversation {conversation_id} for user {current_user.user_id}")
    
    try:
        chat_service = ChatService(db, current_user)
        
        # Delete conversation
        success = await chat_service.delete_conversation(conversation_id)
        
        if not success:
            raise ConversationNotFoundException(f"Conversation {conversation_id} not found")
        
        return BaseResponse(
            success=True,
            message="Conversation deleted successfully"
        )
        
    except ConversationNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete conversation"
        )


@router.post("/conversations/{conversation_id}/share", response_model=ConversationShareResponse)
async def share_conversation(
    conversation_id: str,
    share_data: ConversationShareRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
) -> ConversationShareResponse:
    """
    Share a conversation publicly
    
    Generates a shareable link for the conversation
    """
    logger.info(f"Sharing conversation {conversation_id} for user {current_user.user_id}")
    
    try:
        # TODO: Implement conversation sharing logic
        # For now, return a mock response
        import uuid
        from datetime import datetime, timedelta
        
        share_token = str(uuid.uuid4())
        share_url = f"https://chatgpt-clone.com/shared/{share_token}"
        
        expires_at = None
        if share_data.expiry_hours:
            expires_at = datetime.utcnow() + timedelta(hours=share_data.expiry_hours)
        
        return ConversationShareResponse(
            success=True,
            message="Conversation shared successfully",
            share_token=share_token,
            share_url=share_url,
            is_public=share_data.is_public,
            expires_at=expires_at
        )
        
    except Exception as e:
        logger.error(f"Error sharing conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to share conversation"
        )


@router.post("/conversations/bulk", response_model=ConversationBulkResponse)
async def bulk_conversation_action(
    bulk_data: ConversationBulkAction,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
) -> ConversationBulkResponse:
    """
    Perform bulk actions on multiple conversations
    
    Supported actions: delete, archive, unarchive, pin, unpin
    """
    logger.info(f"Performing bulk action {bulk_data.action} for user {current_user.user_id}")
    
    try:
        # TODO: Implement bulk actions
        # For now, return a mock response
        return ConversationBulkResponse(
            success=True,
            message=f"Bulk {bulk_data.action} completed",
            processed_count=len(bulk_data.conversation_ids),
            successful_ids=bulk_data.conversation_ids,
            failed_ids=[],
            errors={}
        )
        
    except Exception as e:
        logger.error(f"Error in bulk action: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform bulk action"
        )


@router.post("/stream/test")
async def test_streaming(
    current_user: User = Depends(get_current_verified_user)
):
    """
    Test endpoint for SSE streaming
    
    Useful for testing client-side SSE implementation
    """
    async def generate():
        import asyncio
        import json
        
        # Send initial event
        yield f"data: {json.dumps({'type': 'start', 'message': 'Starting stream test'})}\n\n"
        
        # Send some test tokens
        test_message = "Hello! This is a test of the streaming system. Each word will appear one at a time."
        words = test_message.split()
        
        for word in words:
            await asyncio.sleep(0.1)  # Simulate delay
            yield f"data: {json.dumps({'type': 'token', 'content': word + ' '})}\n\n"
        
        # Send completion event
        yield f"data: {json.dumps({'type': 'completion', 'message': 'Stream test completed'})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/stream/test-edit")
async def test_edit_streaming(
    current_user: User = Depends(get_current_verified_user)
):
    """
    Test endpoint for edit SSE streaming
    
    Useful for testing client-side edit streaming implementation
    """
    async def generate_edit_test():
        import asyncio
        import json
        
        # Send initial event
        yield f"data: {json.dumps({'type': 'edit_start', 'message': 'Starting edit stream test'})}\n\n"
        
        # Send edit update event
        yield f"data: {json.dumps({'type': 'edit_update', 'message': 'Message edited successfully'})}\n\n"
        
        # Send some test tokens for the AI response
        test_response = "This is the new AI response after editing. It appears token by token."
        words = test_response.split()
        
        for word in words:
            await asyncio.sleep(0.1)  # Simulate delay
            yield f"data: {json.dumps({'type': 'token', 'content': word + ' '})}\n\n"
        
        # Send completion event
        yield f"data: {json.dumps({'type': 'completion', 'message': 'Edit stream test completed'})}\n\n"
    
    return StreamingResponse(
        generate_edit_test(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    ) 