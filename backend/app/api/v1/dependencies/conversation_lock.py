"""
Conversation Locking Dependencies for FastAPI

This module provides distributed locking for conversation-level streaming operations
to prevent concurrent stream/edit requests on the same conversation.
"""

import asyncio
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


async def release_conversation_lock(lock_key: str) -> bool:
    """
    Release conversation lock with multi-layer shielded protection.
    
    Args:
        lock_key: The lock key to release
        
    Returns:
        bool: True if lock was released successfully
    """
    if not lock_key:
        return False
    
    released = False
    
    # 🛡️ LAYER 1: Normal shielded cleanup
    try:
        logger.info(f"[LAYER-1] [DEBUG] release_conversation_lock() called with lock_key: {lock_key}")
        # 🛡️ Shield the Redis operation from cancellation
        result = await asyncio.shield(redis_client.delete(lock_key))
        released = bool(result)
        logger.info(f"[LAYER-1] [DEBUG] release_conversation_lock() returned: {released}")
        
        if released:
            logger.info(f"[LAYER-1] [SUCCESS] Released conversation lock: {lock_key}")
        else:
            logger.warning(f"[LAYER-1] [WARN] Lock key {lock_key} was not found (may have been auto-released)")
        
        return released
        
    except Exception as e:
        # 🛡️ LAYER 2: Exception recovery with shield  
        if not released:
            try:
                logger.info(f"[LAYER-2] Exception recovery cleanup: {lock_key}")
                result = await asyncio.shield(redis_client.delete(lock_key))
                released = bool(result)
                logger.info(f"[LAYER-2] Exception recovery result: {released}")
            except Exception as e2:
                logger.error(f"[LAYER-2] Exception recovery failed: {e2}")
        
        logger.error(f"[ERROR] Layer-1 failed to release conversation lock {lock_key}: {e}")
        
    except BaseException as e:
        # 🛡️ LAYER 3: BaseException (CancelledError) recovery with shield
        if not released:
            try:
                logger.info(f"[LAYER-3] BaseException recovery cleanup: {lock_key}")
                result = await asyncio.shield(redis_client.delete(lock_key))
                released = bool(result)
                logger.info(f"[LAYER-3] BaseException recovery result: {released}")
            except BaseException as be2:
                logger.error(f"[LAYER-3] BaseException recovery failed: {be2}")
        
        logger.error(f"[ERROR] BaseException: Failed to release conversation lock {lock_key}: {e}")
        
    finally:
        # 🛡️ LAYER 4: Final safety net with shield
        if not released:
            try:
                logger.info(f"[LAYER-4] Final safety net cleanup: {lock_key}")
                result = await asyncio.shield(redis_client.delete(lock_key))
                released = bool(result)
                logger.info(f"[LAYER-4] Final safety net result: {released}")
            except Exception as fe:
                logger.error(f"[LAYER-4] Final cleanup failed (Exception): {fe}")
            except BaseException as fe:
                logger.error(f"[LAYER-4] Final cleanup failed (BaseException): {fe}")
                logger.error(f"[TTL-FALLBACK] All layers failed - TTL will handle: {lock_key}")
    
    return released


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
            logger.info(f"[LOCK] Entering conversation lock context: {self.lock_key}")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Clean, simple cleanup with shield protection.
        
        Handles all exit scenarios including:
        - Normal completion
        - Client disconnections  
        - Early generator termination
        - AsyncIO cancellation
        
        Uses finally block for guaranteed cleanup attempt.
        """
        if self.lock_key and not self.released:
            try:
                # Attempt shielded cleanup - let exceptions bubble up naturally
                logger.info(f"[INITIAL-CLEANUP] Attempting shielded cleanup: {self.lock_key}")
                await asyncio.shield(self._redis_delete("INITIAL-CLEANUP"))
            except Exception as ce:
                logger.error(f"[INITIAL-CLEANUP] Cleanup Exception: {ce}")
            except BaseException as cbe:
                logger.error(f"[INITIAL-CLEANUP] Cleanup BaseException: {cbe}")
            finally:
                # ALWAYS attempt cleanup if not already released
                # This handles any case where the shielded attempt failed/was cancelled
                if not self.released:
                    try:
                        logger.info(f"[FINALLY-CLEANUP] Final cleanup attempt: {self.lock_key}")
                        await asyncio.shield(self._redis_delete("FINALLY-CLEANUP"))
                    except Exception as fe:
                        logger.error(f"[FINALLY-CLEANUP] Cleanup Exception: {fe}")
                        logger.info(f"[TTL-FALLBACK] Relying on TTL auto-expiry: {self.lock_key}")
                    except BaseException as fbe:
                        logger.error(f"[FINALLY-CLEANUP] Cleanup BaseException: {fbe}")
                        logger.info(f"[TTL-FALLBACK] Relying on TTL auto-expiry: {self.lock_key}")
                
                # Final status log
                if self.released:
                    logger.info(f"[SUCCESS] Lock {self.lock_key} successfully released")
                    # Log the exit reason for debugging
                    if exc_type:
                        exc_name = getattr(exc_type, '__name__', str(exc_type))
                        logger.info(f"[LOCK] Lock released due to exception: {exc_name}: {exc_val}")
                    else:
                        logger.info(f"[LOCK] Lock released successfully on normal completion")
                else:
                    logger.error(f"[FAILURE] Lock {self.lock_key} not released - relying on TTL")
                    logger.info(f"[TTL] Lock will auto-expire in ≤5 minutes due to TTL protection")
                    
        # Don't suppress the original exception (return None/False)
        return False
    
    async def _redis_delete(self, layer: str) -> bool:
        """Redis delete with comprehensive logging (shield protection handled at caller level)"""
        if not self.lock_key:
            logger.warning(f"[{layer}] [WARN] _redis_delete() No lock key to release")
            return False
            
        try:
            logger.info(f"[{layer}] [DEBUG] _redis_delete() called with lock_key: {self.lock_key}")
            
            # Direct Redis operation - shield protection handled by caller
            result = await redis_client.delete(self.lock_key)
            released = bool(result)
            
            logger.info(f"[{layer}] [DEBUG] _redis_delete() returned: {released}")
            
            if released:
                self.released = True
                logger.info(f"[{layer}] [SUCCESS] _redis_delete() Released conversation lock: {self.lock_key}")
            else:
                logger.warning(f"[{layer}] [WARN] _redis_delete() Lock {self.lock_key} was not found (may have expired or been released)")
                # Consider it "released" if Redis says it doesn't exist
                self.released = True
                
            return released
            
        except Exception as e:
            logger.error(f"[{layer}] [ERROR] _redis_delete() Redis operation failed: {e}")
            return False
