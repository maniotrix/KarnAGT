"""
Memory Management API Endpoints
"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_memory_status():
    """Get memory service status"""
    return {"status": "Memory service ready", "version": "1.0.0"}

# TODO: Implement memory endpoints
# - GET /search - Search memories
# - GET /preferences - Get user memory preferences
# - PUT /preferences - Update memory preferences
# - DELETE /clear - Clear user memories 