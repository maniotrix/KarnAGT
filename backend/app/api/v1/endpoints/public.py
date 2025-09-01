"""
Public API endpoints (no authentication required)
"""
from fastapi import APIRouter
from datetime import datetime

from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """API v1 health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "api_version": "v1",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/status")
async def api_status():
    """API v1 status endpoint"""
    return {
        "api": "App Backend API",
        "version": settings.VERSION,
        "api_version": "v1",
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "timestamp": datetime.utcnow().isoformat(),
    }
