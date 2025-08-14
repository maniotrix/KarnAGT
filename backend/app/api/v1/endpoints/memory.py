"""Memory Management API Routes"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.services.memory.memory_service import MemoryService
from app.services.memory.memory_setup import (
    create_default_memory_preferences, 
    get_user_memory_configuration,
    setup_user_memory_system,
    MEMORY_BUCKET_CONFIGS
)
from app.models.database.user_memory import UserMemory, MEMORY_BUCKETS
from app.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# Pydantic schemas
class MemoryResponse(BaseModel):
    memory_id: str
    bucket: str
    memory_type: str
    content: str
    importance: float
    confidence: float
    created_at: str
    last_accessed: str
    expires_at: Optional[str] = None
    is_active: bool
    status: Optional[str] = None
    access_count: int

class MemoryStatsResponse(BaseModel):
    total_memories: int
    memories_by_bucket: Dict[str, int]
    recent_memories_7_days: int
    buckets_info: Dict[str, Any]

class CreateMemoryRequest(BaseModel):
    bucket: str
    content: str
    memory_type: Optional[str] = None
    importance: Optional[float] = None
    confidence: float = 1.0


# Routes

@router.get("/")
async def get_memory_status():
    """Get memory service status"""
    return {"status": "Memory service ready", "version": "1.0.0"}


@router.get("/stats", response_model=MemoryStatsResponse)
async def get_memory_stats(
    user_id: int = 1,  # TODO: Replace with proper auth
    db: AsyncSession = Depends(get_db)
):
    """Get memory statistics for the current user"""
    
    memory_service = MemoryService(db)
    
    try:
        stats = await memory_service.get_user_memory_stats(user_id)
        return MemoryStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Failed to get memory stats for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve memory statistics"
        )


@router.post("/setup")
async def setup_memory_system(
    user_id: int = 1,  # TODO: Replace with proper auth
    db: AsyncSession = Depends(get_db)
):
    """Initialize memory system for the current user"""
    
    try:
        success = await setup_user_memory_system(user_id, db)
        
        if success:
            return {"message": "Memory system setup completed successfully", "user_id": user_id}
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to setup memory system"
            )
            
    except Exception as e:
        logger.error(f"Failed to setup memory system for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to setup memory system"
        )


@router.get("/buckets")
async def get_memory_buckets():
    """Get information about available memory buckets"""
    
    return {
        "buckets": MEMORY_BUCKETS,
        "bucket_configs": MEMORY_BUCKET_CONFIGS
    }


@router.get("/all", response_model=List[MemoryResponse])
async def get_all_memories(
    limit: int = 50,
    include_archived: bool = False,
    user_id: int = 1,  # TODO: Replace with proper auth
    db: AsyncSession = Depends(get_db)
):
    """Get all memories for the current user"""
    
    memory_service = MemoryService(db)
    
    try:
        memories = await memory_service.get_all_user_memories(
            user_id, 
            # limit=limit, 
            include_archived=include_archived
        )
        
        return [
            MemoryResponse(
                memory_id=memory.memory_id,
                bucket=memory.bucket,
                memory_type=memory.memory_type,
                content=memory.content,
                importance=memory.importance,
                confidence=memory.confidence,
                created_at=memory.created_at.isoformat(),
                last_accessed=memory.last_accessed.isoformat(),
                expires_at=memory.expires_at.isoformat() if memory.expires_at else None,
                is_active=memory.is_active,
                status=memory.status,
                access_count=memory.access_count
            )
            for memory in memories
        ]
        
    except Exception as e:
        logger.error(f"Failed to get memories for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve memories"
        )


@router.post("/create", response_model=MemoryResponse)
async def create_memory(
    memory_request: CreateMemoryRequest,
    user_id: int = 1,  # TODO: Replace with proper auth
    db: AsyncSession = Depends(get_db)
):
    """Create a new memory manually"""
    
    if memory_request.bucket not in MEMORY_BUCKETS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid bucket name. Must be one of: {list(MEMORY_BUCKETS.keys())}"
        )
    
    memory_service = MemoryService(db)
    
    try:
        memory = await memory_service.store_memory(
            user_id=user_id,
            bucket=memory_request.bucket,
            content=memory_request.content,
            memory_type=memory_request.memory_type,
            importance=memory_request.importance,
            confidence=memory_request.confidence,
            extraction_method="manual"
        )
        
        return MemoryResponse(
            memory_id=memory.memory_id,
            bucket=memory.bucket,
            memory_type=memory.memory_type,
            content=memory.content,
            importance=memory.importance,
            confidence=memory.confidence,
            created_at=memory.created_at.isoformat(),
            last_accessed=memory.last_accessed.isoformat(),
            expires_at=memory.expires_at.isoformat() if memory.expires_at else None,
            is_active=memory.is_active,
            status=memory.status,
            access_count=memory.access_count
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create memory for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create memory"
        ) 