#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Health Service

Core business logic for system health checking and monitoring.
Provides centralized health check functionality for the code executor system.
"""

from typing import Dict, Any, Optional
from app.logging.logger import get_logger
from app.aicore.code_executor.clients import SandboxClient
from app.aicore.code_executor.models import (
    HealthCheck,
    HealthCheckResult,
    SystemStatsResult,
    SystemConfigResult
)

# Get logger
logger = get_logger(__name__)


class HealthService:
    """
    Service for system health checking and monitoring.
    Provides centralized health check functionality.
    """
    
    def __init__(self, sandbox_client: Optional[SandboxClient] = None):
        """
        Initialize the health service
        
        Args:
            sandbox_client: Optional shared SandboxClient instance
        """
        self.sandbox_client = sandbox_client
        logger.debug("HealthService initialized")
    
    async def check_system_health(self) -> HealthCheckResult:
        """
        Check overall system health including CodeSandbox server
        
        Returns:
            HealthCheckResult with health status and details
        """
        logger.info("Performing comprehensive system health check")
        
        try:
            if self.sandbox_client:
                health_check = await self.sandbox_client.health_check()
            else:
                async with SandboxClient() as client:
                    health_check = await client.health_check()
            
            # Create detailed codesandbox info
            codesandbox_details = {
                "healthy": health_check.status == "healthy",
                "status": health_check.status,
                "jupyter_server_status": health_check.jupyter_server_status,
                "active_workspaces": health_check.active_workspaces,
                "url": self.sandbox_client.base_url if self.sandbox_client else SandboxClient().base_url
            }
            
            if health_check.status == "healthy":
                logger.info("CodeSandbox server is healthy")
                return HealthCheckResult.success_result(health_check, codesandbox_details)
            else:
                logger.warning(f"CodeSandbox server is unhealthy: {health_check.status}")
                return HealthCheckResult.error_result(f"CodeSandbox server is unhealthy: {health_check.status}", codesandbox_details)
                
        except Exception as e:
            logger.error(f"CodeSandbox health check failed: {e}")
            codesandbox_details = {
                "healthy": False,
                "status": "error",
                "error": str(e),
                "url": self.sandbox_client.base_url if self.sandbox_client else SandboxClient().base_url
            }
            return HealthCheckResult.error_result(f"Health check failed: {e}", codesandbox_details)
    
    async def check_codesandbox_health(self) -> Dict[str, Any]:
        """
        Check CodeSandbox server health
        
        Returns:
            Dictionary with CodeSandbox server health details
        """
        try:
            logger.debug("Checking CodeSandbox server health")
            
            if self.sandbox_client:
                health_check = await self.sandbox_client.health_check()
            else:
                async with SandboxClient() as client:
                    health_check = await client.health_check()
            
            is_healthy = health_check.status == "healthy"
            
            if is_healthy:
                logger.info("CodeSandbox server is healthy")
            else:
                logger.warning(f"CodeSandbox server is unhealthy: {health_check.status}")
                
            return {
                "healthy": is_healthy,
                "status": health_check.status,
                "jupyter_server_status": health_check.jupyter_server_status,
                "active_workspaces": health_check.active_workspaces,
                "url": self.sandbox_client.base_url if self.sandbox_client else SandboxClient().base_url
            }
            
        except Exception as e:
            logger.error(f"CodeSandbox health check failed: {e}")
            return {
                "healthy": False,
                "status": "error",
                "error": str(e),
                "url": self.sandbox_client.base_url if self.sandbox_client else SandboxClient().base_url
            }
    
    async def get_system_stats(self) -> SystemStatsResult:
        """
        Get comprehensive system statistics
        
        Returns:
            SystemStatsResult with system statistics or error
        """
        try:
            logger.debug("Fetching system statistics")
            
            if self.sandbox_client:
                stats = await self.sandbox_client.get_stats()
            else:
                async with SandboxClient() as client:
                    stats = await client.get_stats()
                    
            logger.info("Successfully retrieved system statistics")
            return SystemStatsResult.success_result(stats)
            
        except Exception as e:
            logger.error(f"Failed to get system stats: {e}")
            return SystemStatsResult.error_result(f"Failed to get system stats: {e}")
    
    async def get_system_config(self) -> SystemConfigResult:
        """
        Get system configuration
        
        Returns:
            SystemConfigResult with system configuration or error
        """
        try:
            logger.debug("Fetching system configuration")
            
            if self.sandbox_client:
                config = await self.sandbox_client.get_config()
            else:
                async with SandboxClient() as client:
                    config = await client.get_config()
                    
            logger.info("Successfully retrieved system configuration")
            return SystemConfigResult.success_result(config)
            
        except Exception as e:
            logger.error(f"Failed to get system config: {e}")
            return SystemConfigResult.error_result(f"Failed to get system config: {e}")
    
    def get_startup_instructions(self) -> Dict[str, Any]:
        """
        Get instructions for starting the CodeSandbox server
        
        Returns:
            Dictionary with startup instructions
        """
        return {
            "title": "To start the CodeSandbox server:",
            "steps": [
                "1. Navigate to the CodeSandbox directory:",
                "   cd CodeSandbox",
                "2. Start the server:",
                "   python -m app.main",
                "   # or",
                "   uvicorn app.main:app --reload --port 8080"
            ],
            "note": "The examples will fail without the server running."
        } 