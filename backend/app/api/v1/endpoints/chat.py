"""
Chat API Endpoints
"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_chat_status():
    """Get chat service status"""
    return {"status": "Chat service ready", "version": "1.0.0"}

# TODO: Implement actual chat endpoints
# - POST /start - Start new conversation
# - POST /message - Send message and get response
# - GET /conversations - List user conversations
# - GET /conversations/{id} - Get conversation details
# - DELETE /conversations/{id} - Delete conversation 