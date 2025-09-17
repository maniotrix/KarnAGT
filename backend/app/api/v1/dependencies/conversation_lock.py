"""
Conversation Locking Dependencies for FastAPI

This module provides distributed locking for conversation-level streaming operations
to prevent concurrent stream/edit requests on the same conversation.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Path
from app.core.database import redis_client
from app.core.worker_id import get_worker_id
from app.models.database.user import User
from app.api.v1.dependencies.auth import get_current_verified_user
from app.logging.logger import get_logger

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
            current_owner_str = current_owner.decode() if current_owner else "unknown"
            
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
        
        logger.info(f"✅ Acquired conversation lock for {conversation_id} by user {user.user_id} on worker {worker_id}")
        return lock_key
        
    except HTTPException:
        # Re-raise HTTP exceptions (lock acquisition failure)
        raise
    except Exception as e:
        logger.error(f"❌ Failed to acquire conversation lock for {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "lock_system_error",
                "message": "Failed to acquire conversation lock due to system error"
            }
        )


async def release_conversation_lock(lock_key: str) -> bool:
    """
    Release conversation lock.
    
    Args:
        lock_key: The lock key to release
        
    Returns:
        bool: True if lock was released successfully
    """
    if not lock_key:
        return False
        
    try:
        # Delete the lock key
        result = await redis_client.delete(lock_key)
        released = bool(result)
        
        if released:
            logger.info(f"✅ Released conversation lock: {lock_key}")
        else:
            logger.warning(f"⚠️ Lock key {lock_key} was not found (may have been auto-released)")
            
        return released
        
    except Exception as e:
        logger.error(f"❌ Failed to release conversation lock {lock_key}: {e}")
        return False


class ConversationLockContext:
    """
    Context manager for conversation locks to ensure deterministic release.
    Used internally by streaming services with enhanced cleanup handling.
    """
    
    def __init__(self, lock_key: Optional[str]):
        self.lock_key = lock_key
        self.released = False
        
    async def __aenter__(self):
        if self.lock_key:
            logger.info(f"🔒 Entering conversation lock context: {self.lock_key}")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Guaranteed cleanup - handles all exit scenarios including:
        - Normal completion
        - Python exceptions  
        - Client disconnections
        - Early generator termination
        """
        if self.lock_key and not self.released:
            try:
                await self.release()
                
                # Log the exit reason for debugging
                if exc_type:
                    exc_name = getattr(exc_type, '__name__', str(exc_type))
                    logger.info(f"🔒 Lock released due to exception: {exc_name}: {exc_val}")
                else:
                    logger.info(f"🔒 Lock released successfully on normal completion")
                    
            except Exception as cleanup_error:
                # Even if cleanup fails, don't propagate the error
                # The TTL will handle orphaned locks from dead workers
                logger.error(f"❌ Failed to release lock {self.lock_key} during cleanup: {cleanup_error}")
                logger.info(f"⏰ Lock will auto-expire in ≤5 minutes due to TTL protection")
                
        # Don't suppress the original exception (return None/False)
        return False
            
    async def release(self):
        """Manual release of the lock with enhanced error handling"""
        if not self.lock_key or self.released:
            return False
            
        try:
            self.released = await release_conversation_lock(self.lock_key)
            if self.released:
                logger.info(f"✅ Successfully released conversation lock: {self.lock_key}")
            else:
                logger.warning(f"⚠️ Lock {self.lock_key} was not found (may have expired or been released)")
            return self.released
            
        except Exception as e:
            logger.error(f"❌ Error during manual lock release for {self.lock_key}: {e}")
            # Mark as released to prevent retry in __aexit__
            self.released = True  
            return False
