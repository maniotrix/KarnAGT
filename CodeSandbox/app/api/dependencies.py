#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FastAPI Dependencies

Dependency injection setup for services and configuration.
"""

from functools import lru_cache
from typing import AsyncGenerator

from app.core.config import Settings, get_settings
from app.infrastructure.jupyter_kernel_client import JupyterServerClient
from app.services.workspace_service import WorkspaceService
from app.services.execution_service import ExecutionService
from app.services.file_service import FileService
from app.services.cleanup_service import CleanupService
from app.utils.logger import Loggers


# Global service instances
_jupyter_client = None
_workspace_service = None
_execution_service = None
_file_service = None
_cleanup_service = None


@lru_cache()
def get_settings_cached() -> Settings:
    """Get cached settings instance"""
    return get_settings()


async def get_jupyter_client() -> JupyterServerClient:
    """Get Jupyter client instance (singleton)"""
    global _jupyter_client
    if _jupyter_client is None:
        settings = get_settings_cached()
        _jupyter_client = JupyterServerClient(settings)
        # Initialize required directories during startup
        await _jupyter_client.initialize_workspace_directory()
        
        Loggers.api_dependencies.info("Jupyter client initialized",
                                    jupyter_url=settings.jupyter_url)
    return _jupyter_client


async def get_workspace_service() -> WorkspaceService:
    """Get workspace service instance (singleton)"""
    global _workspace_service
    if _workspace_service is None:
        settings = get_settings_cached()
        jupyter_client = await get_jupyter_client()
        _workspace_service = WorkspaceService(settings, jupyter_client)
        Loggers.api_dependencies.info("Workspace service created (cleanup managed by CleanupService)")
    return _workspace_service


async def get_execution_service() -> ExecutionService:
    """Get execution service instance (singleton)"""
    global _execution_service
    if _execution_service is None:
        settings = get_settings_cached()
        jupyter_client = await get_jupyter_client()
        workspace_service = await get_workspace_service()
        _execution_service = ExecutionService(settings, jupyter_client, workspace_service)
        
        # ✅ CLEAN: No manual service coordination needed - event bus handles it
        Loggers.api_dependencies.info("Execution service initialized (cleanup managed by CleanupService)")
    return _execution_service


async def get_file_service() -> FileService:
    """Get file service instance (singleton)"""
    global _file_service
    if _file_service is None:
        settings = get_settings_cached()
        jupyter_client = await get_jupyter_client()
        workspace_service = await get_workspace_service()
        _file_service = FileService(settings, jupyter_client, workspace_service)
    return _file_service


async def get_cleanup_service() -> CleanupService:
    """Get centralized cleanup service instance (singleton)"""
    global _cleanup_service
    if _cleanup_service is None:
        settings = get_settings_cached()
        
        # Get all services that need cleanup
        workspace_service = await get_workspace_service()
        execution_service = await get_execution_service()
        jupyter_client = await get_jupyter_client()
        
        # Create and register cleanup service
        _cleanup_service = CleanupService(settings)
        _cleanup_service.register_components(
            workspace_service=workspace_service,
            execution_service=execution_service,
            jupyter_client=jupyter_client,
            concurrency_manager=execution_service._concurrency_manager
        )
        
        # Start the centralized cleanup
        await _cleanup_service.start()
        
        Loggers.api_dependencies.info("✅ Centralized cleanup service started")
    return _cleanup_service


async def cleanup_services():
    """Cleanup all services on shutdown using centralized CleanupService"""
    global _jupyter_client, _workspace_service, _execution_service, _file_service, _cleanup_service
    
    # Use centralized cleanup service if available
    if _cleanup_service:
        await _cleanup_service.stop()  # This handles all cleanup
    else:
        # Fallback to direct cleanup if cleanup service wasn't initialized
        if _jupyter_client:
            await _jupyter_client.close()
    
    # Reset instances
    _jupyter_client = None
    _workspace_service = None
    _execution_service = None
    _file_service = None
    _cleanup_service = None 