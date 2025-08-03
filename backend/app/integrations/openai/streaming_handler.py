"""
Streaming Handler for FastAPI SSE Integration

This module handles real-time streaming of AI responses using Server-Sent Events (SSE),
integrating with the aicore streaming capabilities.
"""

import asyncio
import json
import uuid
from typing import AsyncGenerator, Dict, Any, Optional, List
from datetime import datetime
import queue
import threading

from fastapi import Request
from sse_starlette.sse import EventSourceResponse

from app.logging.logger import get_logger
from app.aicore.core.stream_events import (
    StreamEventUnion, 
    TextTokenEvent,
    ToolCallStartEvent,
    ToolCallOutputEvent,
    ToolCallProgressEvent,
    ToolCallErrorEvent,
    CompletionEvent,
    EventType,
    create_completion_event
)

# Set up logger
logger = get_logger(__name__)


class StreamingHandler:
    """
    Handles streaming responses for FastAPI using Server-Sent Events
    
    Features:
    - Async streaming support
    - Event formatting for SSE
    - Error handling and connection management
    - Integration with aicore streaming callbacks
    - Cancellation support with client disconnection detection
    """
    
    def __init__(self, user_id: str, conversation_id: Optional[str] = None):
        """
        Initialize the streaming handler
        
        Args:
            user_id: The user ID for context
            conversation_id: Optional conversation ID
        """
        self.user_id = user_id
        self.conversation_id = conversation_id
        # 🎯 SINGLE QUEUE for all event types (StreamEventUnion)  
        self.event_queue = asyncio.Queue()
        self.is_streaming = False
        self.is_cancelled = False
        self.stream_id = str(uuid.uuid4())
        self.accumulated_content = ""  # Track partial content for cancellation
        self.client_disconnected = False
        
        # Store assistant client reference for cancellation
        self.assistant_client = None
        
        # Store message IDs for completion event
        self.user_message_id = None
        self.ai_message_id = None
        
        logger.info(f"StreamingHandler initialized for user {user_id}, stream {self.stream_id}")
    
    def set_assistant_client(self, assistant_client):
        """Set the assistant client reference for cancellation"""
        self.assistant_client = assistant_client
    
    def set_user_message_id(self, user_message_id: str):
        """Set the user message ID before streaming starts"""
        self.user_message_id = user_message_id
        logger.info(f"Set user message ID {user_message_id} for stream {self.stream_id}")
    
    def set_ai_message_id(self, ai_message_id: str):
        """Set the AI message ID when response is complete"""
        self.ai_message_id = ai_message_id
        logger.info(f"Set AI message ID {ai_message_id} for stream {self.stream_id}")
    
    def _build_cancel_data(self, reason: str) -> Dict[str, Any]:
        """
        Build cancellation event data with consistent structure
        
        Args:
            reason: Reason for cancellation
            
        Returns:
            Dictionary with cancellation event data
        """
        cancel_data = {
            "stream_id": self.stream_id,
            "partial_content": self.accumulated_content,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Include user_message_id if available
        if self.user_message_id:
            cancel_data["user_message_id"] = self.user_message_id
            logger.info(f"Including user_message_id {self.user_message_id} in {reason} cancellation event for stream {self.stream_id}")
        
        else:
            logger.info(f"No user_message_id added to {reason} cancellation event data for stream {self.stream_id}")
        
        return cancel_data
    
    def streaming_callback(self, event: StreamEventUnion):
        """
        🎯 GENERIC callback function for receiving ALL streaming events from aicore
        
        Args:
            event: StreamEventUnion (TextTokenEvent, ToolCallStartEvent, etc.)
        """
        if self.is_streaming and not self.is_cancelled:
            # Accumulate content for text tokens (for cancellation handling)
            if isinstance(event, TextTokenEvent):
                self.accumulated_content += event.token
                
            # Put event in queue for async processing
            try:
                # Use a thread-safe method to put the event
                asyncio.create_task(self.event_queue.put(event))
            except RuntimeError:
                # If no event loop is running, try sync approach
                try:
                    loop = asyncio.get_event_loop()
                    loop.call_soon_threadsafe(self.event_queue.put_nowait, event)
                except Exception as e:
                    logger.error(f"Failed to queue streaming event: {e}")
    
    async def start_streaming(self) -> AsyncGenerator[str, None]:
        """
        Start the streaming generator for SSE
        
        Yields:
            Formatted SSE events with streaming tokens
        """
        self.is_streaming = True
        logger.info(f"Starting stream for user {self.user_id}, stream {self.stream_id}")
        
        try:
            # Send initial connection event
            yield self._format_sse_event("stream_start", {
                "stream_id": self.stream_id,
                "user_id": self.user_id,
                "conversation_id": self.conversation_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # 🎯 SINGLE EVENT QUEUE CONSUMER WITH TYPE-BASED ROUTING
            while self.is_streaming and not self.is_cancelled:
                try:
                    # Wait for events with a timeout to allow for graceful shutdown
                    event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                    
                    # Check if we were cancelled while waiting
                    if self.is_cancelled:
                        logger.info(f"Stream {self.stream_id} was cancelled, stopping event processing")
                        yield self._format_sse_event("cancelled", self._build_cancel_data("user_cancelled"))
                        break
                    
                    # Check for client disconnection
                    if self.client_disconnected:
                        logger.info(f"Client disconnected for stream {self.stream_id}")
                        self.is_cancelled = True
                        yield self._format_sse_event("cancelled", self._build_cancel_data("client_disconnected"))
                        break
                    
                    # 🚀 TYPE-BASED EVENT ROUTING  
                    if isinstance(event, TextTokenEvent):
                        # Text token streaming (existing behavior)
                        yield self._format_text_sse_event(event)
                        
                    elif isinstance(event, ToolCallStartEvent):
                        # Tool call started
                        yield self._format_tool_start_sse_event(event)
                        
                    elif isinstance(event, ToolCallOutputEvent):
                        # Tool call completed with output
                        yield self._format_tool_output_sse_event(event)
                        
                    elif isinstance(event, ToolCallProgressEvent):
                        # Tool call progress update
                        yield self._format_tool_progress_sse_event(event)
                        
                    elif isinstance(event, ToolCallErrorEvent):
                        # Tool call error
                        yield self._format_tool_error_sse_event(event)
                    
                    else:
                        logger.warning(f"Unknown event type: {type(event)}")
                    
                    # Mark task as done
                    self.event_queue.task_done()
                    
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield self._format_sse_event("heartbeat", {
                        "stream_id": self.stream_id,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    continue
                    
                except Exception as e:
                    logger.error(f"Error processing streaming token: {e}")
                    yield self._format_sse_event("error", {
                        "error": str(e),
                        "stream_id": self.stream_id,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    break
            
        except Exception as e:
            logger.error(f"Error in streaming generator: {e}")
            yield self._format_sse_event("error", {
                "error": str(e),
                "stream_id": self.stream_id,
                "timestamp": datetime.utcnow().isoformat()
            })
        finally:
            # Send appropriate end event
            if self.is_cancelled:
                yield self._format_sse_event("stream_cancelled", self._build_cancel_data("stream_cancelled"))
            else:
                # Include message IDs in stream_end event if available
                stream_end_data = {
                    "stream_id": self.stream_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Add message IDs if available
                if self.user_message_id:
                    stream_end_data["user_message_id"] = self.user_message_id
                    logger.info(f"Including user_message_id {self.user_message_id} in stream_end event for stream {self.stream_id}")
                if self.ai_message_id:
                    stream_end_data["message_id"] = self.ai_message_id
                    logger.info(f"Including ai_message_id {self.ai_message_id} in stream_end event for stream {self.stream_id}")
                
                yield self._format_sse_event("stream_end", stream_end_data)
            
            logger.info(f"Stream ended for user {self.user_id}, stream {self.stream_id}, cancelled: {self.is_cancelled}")
    
    def stop_streaming(self):
        """Stop the streaming process"""
        self.is_streaming = False
        logger.info(f"Stopping stream for user {self.user_id}, stream {self.stream_id}")
    
    def cancel_streaming(self, reason: str = "user_requested"):
        """Cancel the streaming process with a reason"""
        self.is_cancelled = True
        self.is_streaming = False
        logger.info(f"Cancelling stream for user {self.user_id}, stream {self.stream_id}, reason: {reason}")
        
        # Cancel the actual aicore streaming
        if self.assistant_client:
            try:
                self.assistant_client.cancel_streaming()
                logger.info(f"[SUCCESS] Cancelled aicore streaming for stream {self.stream_id}")
            except Exception as e:
                logger.error(f"[ERROR] Error cancelling aicore streaming: {e}")
        else:
            logger.warning(f"No assistant client to cancel for stream {self.stream_id}")
    
    def mark_client_disconnected(self):
        """Mark that the client has disconnected"""
        self.client_disconnected = True
        self.is_cancelled = True
        logger.info(f"Client disconnected for stream {self.stream_id}")
    
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
    
    def _format_text_sse_event(self, event: TextTokenEvent) -> str:
        """Format text token event as SSE"""
        return self._format_sse_event("token", {
            "content": event.token,
            "stream_id": self.stream_id,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def _format_tool_start_sse_event(self, event: ToolCallStartEvent) -> str:
        """Format tool start event as SSE"""
        # Use Pydantic's built-in JSON-safe serialization
        event_data = event.model_dump(mode='json')
        event_data.update({
            "stream_id": self.stream_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        return self._format_sse_event("tool_call_start", event_data)
    
    def _format_tool_output_sse_event(self, event: ToolCallOutputEvent) -> str:
        """Format tool output event as SSE"""
        # 🎯 BULLETPROOF: Use Pydantic's JSON-safe serialization
        # This automatically handles complex objects like WorkspaceCreateResult
        event_data = event.model_dump(mode='json')
        event_data.update({
            "stream_id": self.stream_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        return self._format_sse_event("tool_call_output", event_data)
    
    def _format_tool_progress_sse_event(self, event: ToolCallProgressEvent) -> str:
        """Format tool progress event as SSE"""
        # Use Pydantic's built-in JSON-safe serialization
        event_data = event.model_dump(mode='json')
        event_data.update({
            "stream_id": self.stream_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        return self._format_sse_event("tool_call_progress", event_data)
    
    def _format_tool_error_sse_event(self, event: ToolCallErrorEvent) -> str:
        """Format tool error event as SSE"""
        # Use Pydantic's built-in JSON-safe serialization
        event_data = event.model_dump(mode='json')
        event_data.update({
            "stream_id": self.stream_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        return self._format_sse_event("tool_call_error", event_data)
    
    async def send_completion_event(self, response_data: Dict[str, Any]):
        """
        Send a completion event with the final response
        
        Args:
            response_data: The complete response data
        """
        if self.is_streaming and not self.is_cancelled:
            # Create completion event
            completion_event = create_completion_event(response_data=response_data)
            
            # Queue the completion event
            try:
                asyncio.create_task(self.event_queue.put(completion_event))
            except RuntimeError:
                try:
                    loop = asyncio.get_event_loop()
                    loop.call_soon_threadsafe(self.event_queue.put_nowait, completion_event)
                except Exception as e:
                    logger.error(f"Failed to queue completion event: {e}")
            
            logger.info(f"Completion event queued for stream {self.stream_id}")


class StreamingManager:
    """
    Manager class for handling multiple streaming sessions
    """
    
    def __init__(self):
        self.streams: Dict[str, StreamingHandler] = {}
        logger.info("StreamingManager initialized")
    
    def create_stream(self, user_id: str, conversation_id: Optional[str] = None) -> StreamingHandler:
        """
        Create a new streaming handler
        
        Args:
            user_id: The user ID
            conversation_id: Optional conversation ID
            
        Returns:
            StreamingHandler instance
        """
        handler = StreamingHandler(user_id, conversation_id)
        self.streams[handler.stream_id] = handler
        
        logger.info(f"Created streaming handler {handler.stream_id} for user {user_id}")
        return handler
    
    def get_stream(self, stream_id: str) -> Optional[StreamingHandler]:
        """
        Get a streaming handler by ID
        
        Args:
            stream_id: The stream ID
            
        Returns:
            StreamingHandler instance or None
        """
        return self.streams.get(stream_id)
    
    def remove_stream(self, stream_id: str):
        """
        Remove a streaming handler
        
        Args:
            stream_id: The stream ID to remove
        """
        if stream_id in self.streams:
            self.streams[stream_id].stop_streaming()
            del self.streams[stream_id]
            logger.info(f"Removed streaming handler {stream_id}")
    
    def cancel_stream(self, stream_id: str, reason: str = "user_requested") -> bool:
        """
        Cancel a specific stream
        
        Args:
            stream_id: The stream ID to cancel
            reason: Reason for cancellation
            
        Returns:
            True if stream was found and cancelled, False otherwise
        """
        if stream_id in self.streams:
            self.streams[stream_id].cancel_streaming(reason)
            logger.info(f"Cancelled streaming handler {stream_id}, reason: {reason}")
            return True
        else:
            logger.warning(f"Stream {stream_id} not found for cancellation")
            return False
    
    def cancel_user_streams(self, user_id: str, reason: str = "user_requested") -> int:
        """
        Cancel all streams for a specific user
        
        Args:
            user_id: The user ID
            reason: Reason for cancellation
            
        Returns:
            Number of streams cancelled
        """
        user_streams = [
            (stream_id, handler) for stream_id, handler in self.streams.items()
            if handler.user_id == user_id and handler.is_streaming
        ]
        
        for stream_id, handler in user_streams:
            handler.cancel_streaming(reason)
        
        cancelled_count = len(user_streams)
        if cancelled_count > 0:
            logger.info(f"Cancelled {cancelled_count} streams for user {user_id}, reason: {reason}")
        
        return cancelled_count
    
    def get_user_active_streams(self, user_id: str) -> List[str]:
        """
        Get all active stream IDs for a user
        
        Args:
            user_id: The user ID
            
        Returns:
            List of active stream IDs
        """
        return [
            stream_id for stream_id, handler in self.streams.items()
            if handler.user_id == user_id and handler.is_streaming and not handler.is_cancelled
        ]
    
    def cleanup_inactive_streams(self):
        """Clean up inactive streaming handlers"""
        inactive_streams = [
            stream_id for stream_id, handler in self.streams.items()
            if not handler.is_streaming
        ]
        
        for stream_id in inactive_streams:
            self.remove_stream(stream_id)
        
        if inactive_streams:
            logger.info(f"Cleaned up {len(inactive_streams)} inactive streams")


# Global streaming manager instance
streaming_manager = StreamingManager()


def create_sse_response(generator: AsyncGenerator[str, None], request: Request) -> EventSourceResponse:
    """
    Create an SSE response from an async generator
    
    Args:
        generator: The async generator yielding SSE events
        request: The FastAPI request object
        
    Returns:
        EventSourceResponse for SSE
    """
    return EventSourceResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    ) 