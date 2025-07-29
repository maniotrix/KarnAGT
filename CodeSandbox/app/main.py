#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FastAPI Application

Main FastAPI application for CodeSandbox workspace management.
"""

# Load environment variables first
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, use system environment variables

# Initialize logging EARLY
from app.core.logging_config import setup_logging
setup_logging()

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.api.routes import router
from app.api.dependencies import cleanup_services, get_cleanup_service
from app.middleware.logging_middleware import RequestLoggingMiddleware, PerformanceLoggingMiddleware
from app.utils.logger import Loggers


# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    Loggers.app.info("Starting application", 
                    app_name=settings.app_name,
                    app_version=settings.app_version,
                    environment=settings.environment,
                    jupyter_url=settings.jupyter_url,
                    log_level=settings.log_level)
    
    # ✅ Initialize centralized cleanup service early
    try:
        cleanup_service = await get_cleanup_service()
        Loggers.app.info("✅ Application startup complete with centralized cleanup")
    except Exception as e:
        Loggers.app.error("Failed to initialize cleanup service", exc=e)
        raise
    
    yield
    
    # Shutdown
    Loggers.app.info("Shutting down application")
    try:
        await cleanup_services()
        Loggers.app.info("Application shutdown complete")
    except Exception as e:
        Loggers.app.error("Error during shutdown", exc=e)


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Production-ready workspace management system with Jupyter Server integration",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)


# Add logging middleware first (order matters!)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(PerformanceLoggingMiddleware, slow_request_threshold_ms=settings.log_performance_threshold_ms)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routes
app.include_router(router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    Loggers.app.error("Unhandled exception in global handler",
                     exc=exc,
                     request_method=request.method,
                     request_url=str(request.url),
                     client_host=request.client.host if request.client else "unknown")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An error occurred"
        }
    ) 