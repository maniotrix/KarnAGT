"""
Streaming Handler for FastAPI SSE Integration

This module handles real-time streaming of AI responses using Server-Sent Events (SSE),
integrating with the aicore streaming capabilities.
"""

from typing import Dict, Optional, List

from app.logging.logger import get_logger
from app.services.streaming.streaming_handler import StreamingHandler

# Set up logger
logger = get_logger(__name__)

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