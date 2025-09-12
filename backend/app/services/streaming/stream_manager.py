"""
Streaming Handler for FastAPI SSE Integration

This module handles real-time streaming of AI responses using Server-Sent Events (SSE),
integrating with the aicore streaming capabilities.
"""

import os
import json
import uuid
import asyncio
from typing import Dict, Optional, List
from datetime import datetime

from app.logging.logger import get_logger
from app.services.streaming.streaming_handler import StreamingHandler
from app.core.database import redis_client
from app.core.worker_id import get_worker_id

# Set up logger
logger = get_logger(__name__)

class StreamingManager:
    """
    Manager class for handling multiple streaming sessions
    """
    
    def __init__(self):
        self.streams: Dict[str, StreamingHandler] = {}
        self.worker_id = get_worker_id()  # ✅ Use shared worker ID
        self.redis_client = redis_client
        self.pubsub_task = None
        logger.info(f"StreamingManager initialized for worker {self.worker_id}")
    
    async def initialize(self):
        """Initialize Redis pub/sub listener"""
        self.pubsub_task = asyncio.create_task(self._listen_for_commands())
        logger.info(f"StreamingManager Redis listener started for worker {self.worker_id}")
    
    async def create_stream(self, user_id: str, conversation_id: Optional[str] = None) -> StreamingHandler:
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
        
        # Save to Redis for cross-worker access
        await self._save_to_redis(handler.stream_id, user_id, conversation_id)
        
        logger.info(f"Created streaming handler {handler.stream_id} for user {user_id} in worker {self.worker_id}")
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
    
    async def remove_stream(self, stream_id: str):
        """
        Remove a streaming handler and clean up Redis after natural completion
        
        Args:
            stream_id: The stream ID to remove
        
        Note: This is for cleanup after natural completion, not cancellation.
        For active cancellation, use cancel_stream() instead.
        """
        if stream_id in self.streams:
            # ✅ FIX: Don't call cancel_streaming - stream completed naturally!
            # The AI streaming is already finished, just cleanup references
            
            self.streams[stream_id].stop_streaming()
            
            # ✅ Mark as completed in Redis before cleanup to help with race conditions
            try:
                await self.redis_client.hset(f"stream:{stream_id}", "status", "completed")
                await self.redis_client.hset(f"stream:{stream_id}", "completed_at", datetime.utcnow().isoformat())
            except Exception as e:
                logger.error(f"Failed to mark stream {stream_id} as completed in Redis: {e}")
            
            # Clean up Redis data immediately
            try:
                await self._remove_from_redis(stream_id)
            except Exception as e:
                logger.error(f"Failed to remove stream {stream_id} from Redis: {e}")
            
            del self.streams[stream_id]
            logger.info(f"Removed streaming handler {stream_id} after natural completion and cleaned up Redis")
        else:
            logger.warning(f"Streaming handler {stream_id} not found in local memory or already cleaned up, skipping cleanup")
    
    async def cancel_stream(self, stream_id: str, reason: str = "user_requested") -> tuple[bool, str]:
        """
        Cancel a specific stream (works across all workers)
        
        Args:
            stream_id: The stream ID to cancel
            reason: Reason for cancellation
            
        Returns:
            Tuple of (success: bool, cancel_reason: str)
            - success: True if stream was found and cancelled, False otherwise
            - cancel_reason: Detailed reason for the result
        """
        # Try local cancellation first
        if stream_id in self.streams:
            self.streams[stream_id].cancel_streaming(reason)
            await self._remove_from_redis(stream_id)
            del self.streams[stream_id]
            logger.info(f"Cancelled streaming handler {stream_id}, reason: {reason}")
            return True, "cancelled_locally"
        
        # Try cross-worker cancellation
        return await self._cancel_cross_worker(stream_id, reason)
    
    async def cancel_user_streams(self, user_id: str, reason: str = "user_requested") -> int:
        """
        Cancel all streams for a specific user
        
        Args:
            user_id: The user ID
            reason: Reason for cancellation
            
        Returns:
            Number of streams cancelled
        """
        # Cancel local streams
        user_streams = [
            (stream_id, handler) for stream_id, handler in self.streams.items()
            if handler.user_id == user_id and handler.is_streaming
        ]
        
        for stream_id, handler in user_streams:
            handler.cancel_streaming(reason)
            await self._remove_from_redis(stream_id)
            del self.streams[stream_id]
        
        # Cancel cross-worker streams
        cross_worker_count = await self._cancel_user_cross_worker(user_id, reason)
        
        total_cancelled = len(user_streams) + cross_worker_count
        if total_cancelled > 0:
            logger.info(f"Cancelled {total_cancelled} streams for user {user_id}, reason: {reason}")
        
        return total_cancelled
    
    async def get_user_active_streams(self, user_id: str) -> List[str]:
        """
        Get all active stream IDs for a user (across all workers)
        
        Args:
            user_id: The user ID
            
        Returns:
            List of active stream IDs
        """
        try:
            # ✅ FIX: Get all streams from Redis first (source of truth)
            redis_streams = await self.redis_client.smembers(f"user:{user_id}:streams")
            active_streams = []
            
            for stream_id in redis_streams:
                stream_data = await self.redis_client.hgetall(f"stream:{stream_id}")
                if not stream_data:
                    # Stream key missing but ID in user set - cleanup inconsistency
                    await self.redis_client.srem(f"user:{user_id}:streams", stream_id)
                    continue
                
                status = stream_data.get("status", "active")
                if status in ["active", "cancelling"]:  # Include cancelling streams
                    active_streams.append(stream_id)
                elif status == "completed":
                    # Cleanup completed streams that weren't removed
                    await self.redis_client.srem(f"user:{user_id}:streams", stream_id)
                    await self.redis_client.delete(f"stream:{stream_id}")
            
            return active_streams
            
        except Exception as e:
            logger.error(f"Error getting streams from Redis: {e}")
            # ✅ FIX: Fallback to local streams only
            local_streams = [
                stream_id for stream_id, handler in self.streams.items()
                if handler.user_id == user_id and handler.is_streaming and not handler.is_cancelled
            ]
            return local_streams
    
    async def cleanup_inactive_streams(self):
        """Clean up inactive streaming handlers"""
        inactive_streams = [
            stream_id for stream_id, handler in self.streams.items()
            if not handler.is_streaming
        ]
        
        for stream_id in inactive_streams:
            await self.remove_stream(stream_id)
        
        if inactive_streams:
            logger.info(f"Cleaned up {len(inactive_streams)} inactive streams")

    # ========== REDIS HELPER METHODS ==========
    
    async def _save_to_redis(self, stream_id: str, user_id: str, conversation_id: Optional[str]):
        """Save stream to Redis"""
        try:
            stream_data = {
                "stream_id": stream_id,
                "user_id": user_id,
                "conversation_id": conversation_id or "",
                "worker_id": self.worker_id,
                "status": "active",
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Use pipeline for atomic operations
            async with self.redis_client.pipeline(transaction=True) as pipe:
                # Save stream data
                await pipe.hset(f"stream:{stream_id}", mapping=stream_data)
                # Add to user's streams
                await pipe.sadd(f"user:{user_id}:streams", stream_id)
                # ✅ FIX: Set TTL on both stream data and user set
                await pipe.expire(f"stream:{stream_id}", 1800)  # 30 minutes
                await pipe.expire(f"user:{user_id}:streams", 1800)  # 30 minutes
                
                await pipe.execute()
            logger.info(f"Saved stream {stream_id} to Redis")
                
        except Exception as e:
            logger.error(f"Failed to save stream {stream_id} to Redis: {e}")
    
    async def _remove_from_redis(self, stream_id: str):
        """Remove stream from Redis (safe for multiple calls)"""
        try:
            # Get user_id before deletion
            stream_data = await self.redis_client.hgetall(f"stream:{stream_id}")
            user_id = stream_data.get("user_id")
            
            # Use pipeline for atomic operations
            async with self.redis_client.pipeline(transaction=True) as pipe:
                # Remove stream data
                await pipe.delete(f"stream:{stream_id}")
                
                # Always try to remove from user's streams (even if user_id is empty)
                # This handles cases where stream_id might be dangling in sets
                if user_id:
                    await pipe.srem(f"user:{user_id}:streams", stream_id)
                else:
                    # If no user_id found, we might have a dangling reference
                    # Try to find and clean it up from all possible user sets
                    logger.warning(f"Stream {stream_id} has no user_id, checking for dangling references")
                
                await pipe.execute()
            logger.info(f"Removed stream {stream_id} from Redis")
                
        except Exception as e:
            logger.error(f"Failed to remove stream {stream_id} from Redis: {e}")
            # ✅ Fallback: Try to remove from user sets without scanning (simpler approach)
            try:
                # If we don't have user_id, can't clean up user set - but that's OK
                # TTL will eventually clean up any dangling data
                pass
            except Exception as cleanup_error:
                logger.error(f"Fallback cleanup failed for stream {stream_id}: {cleanup_error}")
    
    async def _cancel_cross_worker(self, stream_id: str, reason: str) -> tuple[bool, str]:
        """
        Cancel stream on another worker with proper verification and race condition protection
        
        Returns:
            Tuple of (success: bool, cancel_reason: str)
        """
        try:
            # ✅ FIX: Atomic check-and-set to prevent race conditions
            async with self.redis_client.pipeline(transaction=True) as pipe:
                # Watch the stream key for changes during transaction
                await pipe.watch(f"stream:{stream_id}")
                
                # Get current stream data
                stream_data = await self.redis_client.hgetall(f"stream:{stream_id}")
                if not stream_data:
                    logger.warning(f"Stream {stream_id} not found in Redis")
                    await pipe.unwatch()  # Clean up watch
                    return False, "not_found"
                
                # Check current status to prevent duplicate cancellations
                current_status = stream_data.get("status", "active")
                if current_status == "cancelling":
                    logger.info(f"Stream {stream_id} already being cancelled by another worker")
                    await pipe.unwatch()
                    return True, "already_cancelling"  # Consider this success
                elif current_status == "completed":
                    logger.info(f"Stream {stream_id} already completed naturally")
                    await pipe.unwatch()
                    return True, "already_completed"  # Consider this success
                
                owning_worker = stream_data.get("worker_id")
                if not owning_worker:
                    logger.warning(f"Stream {stream_id} has no owning worker")
                    await pipe.unwatch()
                    return False, "no_owner"
                
                # Check if target worker is still registered (may have gracefully shut down)
                worker_exists = await self.redis_client.sismember("workers:active", owning_worker)
                if not worker_exists:
                    logger.info(f"Target worker {owning_worker} has deregistered, cleaning up stream {stream_id}")
                    await pipe.unwatch()
                    await self._remove_from_redis(stream_id)
                    return True, "worker_shutdown_cleanup"
                
                # ✅ ATOMIC: Mark as cancelling only if still active
                pipe.multi()  # Start transaction (synchronous!)
                pipe.hset(f"stream:{stream_id}", "status", "cancelling")
                pipe.hset(f"stream:{stream_id}", "cancelled_by", self.worker_id)
                pipe.hset(f"stream:{stream_id}", "cancel_timestamp", datetime.utcnow().isoformat())
                
                try:
                    await pipe.execute()  # Execute atomic transaction
                except Exception as e:
                    logger.warning(f"Failed to mark stream {stream_id} as cancelling (race condition): {e}")
                    return True, "race_condition_handled"  # Another worker likely got there first - that's OK
            
            # Send cancel command to owning worker
            cancel_cmd = {
                "action": "cancel_stream",
                "stream_id": stream_id,
                "reason": reason,
                "from_worker": self.worker_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.redis_client.publish(f"worker:{owning_worker}:commands", json.dumps(cancel_cmd))
            
            logger.info(f"Sent cancel command for stream {stream_id} to worker {owning_worker}")
            return True, "command_sent"
            
        except Exception as e:
            logger.error(f"Error in cross-worker cancellation: {e}")
            return False, "cross_worker_error"
    
    async def _cancel_user_cross_worker(self, user_id: str, reason: str) -> int:
        """Cancel all user streams across workers with better verification"""
        try:
            # Get all user streams from Redis
            stream_ids = await self.redis_client.smembers(f"user:{user_id}:streams")
            cancelled_count = 0
            
            for stream_id in stream_ids:
                # Skip local streams - they were already handled by cancel_user_streams()
                if stream_id in self.streams:
                    # This should not happen if cancel_user_streams() worked correctly
                    handler = self.streams[stream_id]
                    if not (handler.is_cancelled or not handler.is_streaming):
                        # Local cancellation failed, try again but NO Redis cleanup (already done)
                        logger.warning(f"Local stream {stream_id} should be cancelled but isn't, retrying")
                        handler.cancel_streaming(reason)
                        del self.streams[stream_id]
                        cancelled_count += 1
                    continue  # Skip to next stream
                
                # Cancel cross-worker stream
                success, cancel_reason = await self._cancel_cross_worker(stream_id, reason)
                if success:
                    cancelled_count += 1
                    logger.debug(f"Cross-worker cancellation of stream {stream_id}: {cancel_reason}")
            
            return cancelled_count
            
        except Exception as e:
            logger.error(f"Error cancelling cross-worker streams for user {user_id}: {e}")
            return 0
    
    async def _listen_for_commands(self):
        """Listen for cross-worker commands"""
        try:
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(f"worker:{self.worker_id}:commands")
            
            logger.info(f"Worker {self.worker_id} listening for commands")
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        command = json.loads(message['data'])
                        await self._handle_command(command)
                    except Exception as e:
                        logger.error(f"Error processing command: {e}")
                        
        except Exception as e:
            logger.error(f"Error in command listener: {e}")
    
    async def _handle_command(self, command: Dict):
        """Handle cross-worker commands with robust error handling and race condition protection"""
        action = command.get("action")
        
        if action == "cancel_stream":
            stream_id = command.get("stream_id")
            reason = command.get("reason", "cross_worker_cancel")
            from_worker = command.get("from_worker", "unknown")
            
            logger.info(f"Received cancel command for stream {stream_id} from worker {from_worker}")
            
            if stream_id in self.streams:
                success = True
                cleanup_errors = []
                
                try:
                    # Cancel the local stream (AI + local state)
                    self.streams[stream_id].cancel_streaming(reason)
                    logger.info(f"Successfully cancelled local AI streaming for {stream_id}")
                except Exception as e:
                    logger.error(f"Failed to cancel local AI streaming for {stream_id}: {e}")
                    cleanup_errors.append(f"AI cancel: {e}")
                    success = False
                
                # Always try Redis cleanup, even if AI cancellation failed
                try:
                    await self._remove_from_redis(stream_id)
                    logger.info(f"Successfully cleaned up Redis for stream {stream_id}")
                except Exception as e:
                    logger.error(f"Failed to clean up Redis for stream {stream_id}: {e}")
                    cleanup_errors.append(f"Redis cleanup: {e}")
                    success = False
                
                # Always try memory cleanup, even if other steps failed
                try:
                    del self.streams[stream_id]
                    logger.info(f"Successfully cleaned up memory for stream {stream_id}")
                except Exception as e:
                    logger.error(f"Failed to clean up memory for stream {stream_id}: {e}")
                    cleanup_errors.append(f"Memory cleanup: {e}")
                    success = False
                
                if success:
                    logger.info(f"✅ Successfully cancelled stream {stream_id} via cross-worker command")
                else:
                    logger.error(f"❌ Partial failure cancelling stream {stream_id}: {'; '.join(cleanup_errors)}")
                    
                    # ✅ FUTURE: Could publish failure notification back to initiating worker
                    # This would require implementing acknowledgment system
                    
            else:
                # Stream not found locally - this is normal if it completed naturally
                logger.info(f"Stream {stream_id} not found in local memory (likely completed naturally or already cancelled)")
                
                # ✅ Still try Redis cleanup in case of race condition leftovers
                try:
                    stream_data = await self.redis_client.hgetall(f"stream:{stream_id}")
                    if stream_data and stream_data.get("worker_id") == self.worker_id:
                        # This worker owns the stream in Redis but not in memory - cleanup orphaned data
                        await self._remove_from_redis(stream_id)
                        logger.info(f"Cleaned up orphaned Redis data for stream {stream_id}")
                except Exception as e:
                    logger.error(f"Failed to check/cleanup orphaned Redis data for stream {stream_id}: {e}")


# Global streaming manager instance
streaming_manager = StreamingManager()