"""
Shared Worker ID for Distributed Components

This module provides a single, consistent worker ID that is shared across
all distributed components (StreamingManager, WorkerRegistry, etc.) to ensure
proper cross-worker communication and stream management.

The worker ID is generated once per process and reused across all components.
"""

import os
import uuid
from typing import Optional

# Global variable to store the worker ID for this process
_WORKER_ID: Optional[str] = None

def get_worker_id() -> str:
    """
    Get the shared worker ID for this process.
    
    The worker ID is generated once per process and consists of:
    - A UUID for uniqueness across multiple processes
    - The process ID (PID) for easy identification
    
    Returns:
        str: The unique worker ID for this process
    """
    global _WORKER_ID
    
    if _WORKER_ID is None:
        _WORKER_ID = f"worker_{uuid.uuid4()}_{os.getpid()}"
    
    return _WORKER_ID

def reset_worker_id() -> None:
    """
    Reset the worker ID (mainly for testing purposes).
    
    Warning: This should only be used in tests or special circumstances
    where you need to regenerate the worker ID within the same process.
    """
    global _WORKER_ID
    _WORKER_ID = None
