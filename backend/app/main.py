"""
ChatGPT Clone Backend - FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.core.config import settings
from app.api.router import api_router

from app.utils import validate_api_keys
validate_api_keys()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("[STARTUP] ChatGPT Clone Backend starting up...")
    print(f"[CONFIG] Environment: {settings.ENVIRONMENT}")
    print(f"[CONFIG] Debug mode: {settings.DEBUG}")
    
    yield
    
    # Shutdown
    print("[SHUTDOWN] ChatGPT Clone Backend shutting down...")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Advanced ChatGPT Clone with Memory Management and Knowledge Integration",
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=settings.get_allowed_hosts()
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware (order matters - applied in reverse order)
from app.api.v1.middleware.auth import (
    AuthenticationMiddleware,
    SecurityHeadersMiddleware,
    UserContextMiddleware
)
from app.api.v1.middleware.rate_limit import RateLimitMiddleware

# Add custom middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(UserContextMiddleware) 
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(RateLimitMiddleware)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ChatGPT Clone Backend API",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if settings.DEBUG else "disabled",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
    ) 