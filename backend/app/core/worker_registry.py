"""
Worker Registry for Multi-Worker Coordination

This module handles worker registration, health monitoring, and graceful shutdowns
in a Redis-backed distributed environment.
"""

import os
from datetime import datetime
from typing import Dict, List

from app.logging.logger import get_logger
from app.core.database import redis_client
from app.core.worker_id import get_worker_id

logger = get_logger(__name__)


class WorkerRegistry:
    """
    Manages worker lifecycle, health monitoring, and graceful shutdowns
    """
    
    def __init__(self):
        self.worker_id = get_worker_id()  # ✅ Use shared worker ID
        self.redis_client = redis_client
        self.is_registered = False
        
        logger.info(f"WorkerRegistry initialized for worker {self.worker_id}")
    
    async def register_worker(self):
        """Register this worker on FastAPI startup"""
        try:
            # Register worker with metadata
            worker_data = {
                "worker_id": str(self.worker_id),
                "pid": str(os.getpid()),
                "started_at": datetime.utcnow().isoformat(),
                "last_heartbeat": datetime.utcnow().isoformat(),
                "active_streams": "0",
                "status": "healthy"
            }
            
            await self.redis_client.hset(f"worker:{self.worker_id}", mapping=worker_data)
            await self.redis_client.sadd("workers:active", self.worker_id)
            
            # ✅ NO heartbeat task - workers manage their own lifecycle
            self.is_registered = True
            
            # Use print during startup to match main.py pattern (logger has encoding issues during uvicorn startup)
            print(f"✅ Worker {self.worker_id} registered successfully")
            
        except Exception as e:
            print(f"❌ Failed to register worker {self.worker_id}: {e}")
            logger.error(f"Failed to register worker {self.worker_id}: {e}")
    
    async def deregister_worker(self):
        """Clean shutdown - deregister worker"""
        if not self.is_registered:
            return
            
        try:
            # ✅ NO heartbeat task to cancel
            
            # Remove from active workers
            await self.redis_client.srem("workers:active", self.worker_id)
            await self.redis_client.delete(f"worker:{self.worker_id}")
            
            self.is_registered = False
            print(f"✅ Worker {self.worker_id} deregistered successfully")
            
        except Exception as e:
            print(f"❌ Error deregistering worker {self.worker_id}: {e}")
            logger.error(f"Error deregistering worker {self.worker_id}: {e}")
    
    async def _heartbeat_loop(self):
        """
        ✅ REMOVED: No heartbeat needed
        
        Workers manage their own lifecycle:
        - Register on startup  
        - Deregister on graceful shutdown
        - Zombie entries from crashes are harmless (just orphaned Redis keys)
        
        Future: Could add crash detection with 30+ minute timeout if needed.
        """
        pass  # No heartbeat loop
    
    async def _cleanup_dead_workers(self):
        """
        ✅ DISABLED: No automatic worker cleanup based on time
        
        Workers manage their own lifecycle:
        - Register on startup
        - Deregister on shutdown  
        - No TTL or time-based removal
        
        AI processing can take hours - workers should never be marked dead automatically.
        """
        pass  # No automatic cleanup
    
    async def _cleanup_dead_worker_streams(self, dead_worker_id: str):
        """Clean up streams from a dead worker"""
        try:
            # Find all streams owned by the dead worker
            all_stream_keys = await self.redis_client.keys("stream:*")
            
            for stream_key in all_stream_keys:
                stream_data = await self.redis_client.hgetall(stream_key)
                if stream_data.get("worker_id") == dead_worker_id:
                    stream_id = stream_data.get("stream_id")
                    user_id = stream_data.get("user_id")
                    
                    # Remove orphaned stream
                    await self.redis_client.delete(stream_key)
                    if user_id and stream_id:
                        await self.redis_client.srem(f"user:{user_id}:streams", stream_id)
                    
                    logger.info(f"Cleaned up orphaned stream {stream_id} from dead worker {dead_worker_id}")
                    
        except Exception as e:
            logger.error(f"Error cleaning up streams for dead worker {dead_worker_id}: {e}")
    
    async def _cleanup_dead_worker_conversation_locks(self, dead_worker_id: str):
        """Clean up conversation locks from a dead worker"""
        try:
            # Find all conversation locks owned by the dead worker
            all_lock_keys = await self.redis_client.keys("conv_lock:*")
            cleaned_locks = 0
            
            for lock_key in all_lock_keys:
                lock_value = await self.redis_client.get(lock_key)
                if lock_value:
                    lock_value_str = lock_value.decode() if isinstance(lock_value, bytes) else str(lock_value)
                    
                    # Check if this lock belongs to the dead worker
                    if f"worker:{dead_worker_id}" in lock_value_str:
                        # Extract conversation ID from key for logging
                        conversation_id = lock_key.decode().replace("conv_lock:", "") if isinstance(lock_key, bytes) else lock_key.replace("conv_lock:", "")
                        
                        # Remove orphaned conversation lock
                        deleted = await self.redis_client.delete(lock_key)
                        if deleted:
                            cleaned_locks += 1
                            logger.info(f"🔒 Cleaned up orphaned conversation lock for conversation {conversation_id} from dead worker {dead_worker_id}")
            
            if cleaned_locks > 0:
                logger.info(f"✅ Cleaned up {cleaned_locks} orphaned conversation locks from dead worker {dead_worker_id}")
            else:
                logger.info(f"ℹ️ No orphaned conversation locks found for dead worker {dead_worker_id}")
                    
        except Exception as e:
            logger.error(f"❌ Error cleaning up conversation locks for dead worker {dead_worker_id}: {e}")
    
    async def cleanup_dead_worker_resources(self, dead_worker_id: str):
        """
        Clean up all resources (streams, locks, etc.) from a dead worker
        
        This method can be called manually when a worker is known to be dead,
        or integrated with future dead worker detection mechanisms.
        
        Args:
            dead_worker_id: The worker ID to clean up resources for
        """
        logger.info(f"🧹 Starting cleanup for dead worker: {dead_worker_id}")
        
        try:
            # Clean up streams
            await self._cleanup_dead_worker_streams(dead_worker_id)
            
            # Clean up conversation locks  
            await self._cleanup_dead_worker_conversation_locks(dead_worker_id)
            
            # Remove from active workers set (if still present)
            await self.redis_client.srem("workers:active", dead_worker_id)
            await self.redis_client.delete(f"worker:{dead_worker_id}")
            
            logger.info(f"✅ Completed cleanup for dead worker: {dead_worker_id}")
            
        except Exception as e:
            logger.error(f"❌ Error during cleanup for dead worker {dead_worker_id}: {e}")
            raise
    
    async def get_active_workers(self) -> List[str]:
        """Get list of active workers"""
        try:
            return list(await self.redis_client.smembers("workers:active"))
        except Exception as e:
            logger.error(f"Error getting active workers: {e}")
            return []
    
    async def get_worker_stats(self) -> Dict[str, Dict]:
        """Get stats for all workers"""
        try:
            active_workers = await self.get_active_workers()
            stats = {}
            
            for worker_id in active_workers:
                worker_data = await self.redis_client.hgetall(f"worker:{worker_id}")
                if worker_data:
                    stats[worker_id] = worker_data
                    
            return stats
            
        except Exception as e:
            logger.error(f"Error getting worker stats: {e}")
            return {}
    
    @property 
    def current_worker_id(self) -> str:
        """Get current worker ID"""
        return self.worker_id


# Global worker registry instance
worker_registry = WorkerRegistry()
