"""
Conversation Locking Dependencies for FastAPI

This module provides distributed locking for conversation-level streaming operations
to prevent concurrent stream/edit requests on the same conversation.
"""

import asyncio
from typing import Optional
import redis  # Sync Redis client for deterministic cleanup
from fastapi import Depends, HTTPException, status, Path
from app.core.database import redis_client
from app.core.worker_id import get_worker_id
from app.models.database.user import User
from app.api.v1.dependencies.auth import get_current_verified_user
from app.logging.logger import get_logger
from app.core.config import settings

logger = get_logger(__name__)


async def acquire_conversation_lock(
    conversation_id: str = Path(..., description="Conversation ID to lock"),
    user: User = Depends(get_current_verified_user)
) -> str:
    """
    Acquire distributed lock for conversation streaming operations.
    
    This dependency ensures only one streaming operation (send message or edit message)
    can run per conversation across all workers/pods.
    
    The lock has a 5-minute TTL to prevent permanent deadlocks if workers die.
    
    Note: Conversation ownership validation is handled by ResourceAuthorizationMiddleware
    before this dependency executes. This dependency focuses purely on distributed locking.
    
    Args:
        conversation_id: The conversation ID to lock  
        user: Current authenticated user (already resolved from endpoint)
        
    Returns:
        str: Lock key for cleanup in ConversationLockContext
        
    Raises:
        HTTPException: 429 if conversation is already locked by another operation
    """
    worker_id = get_worker_id()
    lock_key = f"conv_lock:{conversation_id}"
    lock_value = f"user:{user.user_id}:worker:{worker_id}:ts:{int(__import__('time').time())}"
    
    try:
        # Try to acquire lock atomically with 5-minute TTL for dead worker protection
        acquired = await redis_client.set(lock_key, lock_value, nx=True, ex=300)  # 5 minutes TTL
        
        if not acquired:
            # Check who owns the lock for better error messaging
            current_owner = await redis_client.get(lock_key)
            # Handle both bytes and string responses (depends on decode_responses setting)
            if current_owner:
                current_owner_str = current_owner.decode() if isinstance(current_owner, bytes) else str(current_owner)
            else:
                current_owner_str = "unknown"
            
            logger.warning(f"Conversation {conversation_id} lock acquisition failed - already locked by {current_owner_str}")
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "conversation_locked",
                    "message": f"Another streaming operation is in progress for this conversation",
                    "conversation_id": conversation_id,
                    "locked_by": current_owner_str,
                    "retry_after": "Please wait for the current operation to complete (locks auto-expire after 5 minutes)"
                }
            )
        
        logger.info(f"[SUCCESS] Acquired conversation lock for {conversation_id} by user {user.user_id} on worker {worker_id}")
        return lock_key
        
    except HTTPException:
        # Re-raise HTTP exceptions (lock acquisition failure)
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to acquire conversation lock for {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "lock_system_error",
                "message": "Failed to acquire conversation lock due to system error"
            }
        )


def _sync_release_conversation_lock(lock_key: str, sync_redis_client, context: str = "MANUAL") -> bool:
    """
    Synchronous deterministic conversation lock release.
    
    This is the core lock release logic used by both context manager 
    and manual release operations.
    
    Args:
        lock_key: The lock key to release
        sync_redis_client: Synchronous Redis client instance
        context: Context string for logging (e.g., "MANUAL", "CONTEXT-MGR")
        
    Returns:
        bool: True if lock was released successfully, False otherwise
    """
    if not lock_key:
        logger.warning(f"[{context}] No lock key provided")
        return False
    
    try:
        logger.info(f"[{context}] Deterministic lock release: {lock_key}")
        
        # Sync Redis operation - cannot be cancelled by asyncio
        result = sync_redis_client.delete(lock_key)  # type: ignore
        released = bool(result)
        
        if released:
            logger.info(f"[{context}] [SUCCESS] Lock released deterministically: {lock_key}")
        else:
            logger.warning(f"[{context}] [WARNING] Lock not found (may have expired): {lock_key}")
        
        return released
        
    except Exception as e:
        logger.error(f"[{context}] [ERROR] Deterministic cleanup failed: {e}")
        logger.info(f"[{context}] [TTL-FALLBACK] Lock will auto-expire in ≤5 minutes: {lock_key}")
        return False


async def release_conversation_lock(lock_key: str) -> bool:
    """
    Release conversation lock (async wrapper for manual use).
    
    Uses deterministic sync Redis operations for guaranteed results.
    
    Args:
        lock_key: The lock key to release
        
    Returns:
        bool: True if lock was released successfully
    """
    if not lock_key:
        return False
    
    # Create sync Redis client for deterministic operation
    sync_redis = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5
    )
    
    try:
        return _sync_release_conversation_lock(lock_key, sync_redis, "MANUAL")
    finally:
        # Cleanup sync client connection
        try:
            sync_redis.close()
        except:
            pass  # Ignore cleanup errors


class ConversationLockContext:
    """
    Context manager for conversation locks to ensure deterministic release.
    Uses synchronous Redis operations for guaranteed deterministic cleanup.
    """
    
    def __init__(self, lock_key: Optional[str]):
        self.lock_key = lock_key
        self.released = False
        # Create sync Redis client for deterministic cleanup operations
        self._sync_redis = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=5,  # 5 second timeout for cleanup
            socket_connect_timeout=5
        )
        
    async def __aenter__(self):
        if self.lock_key:
            logger.info(f"[LOCK] Entering conversation lock context: {self.lock_key}")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Deterministic cleanup using shared synchronous lock release logic.
        
        Sync operations cannot be cancelled by asyncio, providing guaranteed
        deterministic results when context manager exits.
        
        Returns:
            False: Never suppress exceptions - let them propagate normally
        """
        if self.lock_key and not self.released:
            # Use shared deterministic lock release logic
            self.released = _sync_release_conversation_lock(
                self.lock_key, 
                self._sync_redis, 
                "CONTEXT-MGR"
            )
            
            # Log the completion reason for context
            if self.released:
                if exc_type:
                    exc_name = getattr(exc_type, '__name__', str(exc_type))
                    logger.info(f"[COMPLETION] Lock released due to exception: {exc_name}")
                else:
                    logger.info(f"[COMPLETION] Lock released on normal completion")
                    
        elif not self.lock_key:
            logger.debug("[SKIP] No lock key provided - nothing to release")
        else:
            logger.debug(f"[SKIP] Lock already released: {self.lock_key}")
            
        # Never suppress exceptions - let them propagate normally
        return False
