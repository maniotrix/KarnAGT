"""
Main API Router Configuration
"""
from fastapi import APIRouter

from app.api.v1.endpoints import chat, memory, files, tools, auth, analytics, ai_files

# Create main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(memory.router, prefix="/memory", tags=["Memory"])
api_router.include_router(files.router, prefix="/files", tags=["Files"])
api_router.include_router(ai_files.router, prefix="/ai-files", tags=["AI Files"])
api_router.include_router(tools.router, prefix="/tools", tags=["Tools"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"]) 