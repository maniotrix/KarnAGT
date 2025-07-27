#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Workspace Service

Core business logic for workspace lifecycle management.
Separated from tool decorators for flexibility and reusability.
"""

from typing import Optional
from app.logging.logger import get_logger
from app.aicore.code_executor.clients import (
    SandboxClient, 
    WorkspaceError, 
    WorkspaceNotFoundError
)
from app.aicore.code_executor.models import (
    WorkspaceGetResult,
    WorkspaceCreateResult,
    WorkspaceDeleteResult,
    WorkspaceTTLExtendResult
)

# Get logger
logger = get_logger(__name__)


class WorkspaceService:
    """
    Service class for workspace lifecycle management.
    
    Provides clean methods that can be used directly or wrapped with decorators.
    All methods return proper Pydantic result models.
    """
    
    def __init__(self, sandbox_client: Optional[SandboxClient] = None):
        """
        Initialize the workspace service.
        
        Args:
            sandbox_client: Optional pre-configured client. If None, creates new clients per operation.
        """
        self.sandbox_client = sandbox_client
        
    async def create_workspace(self, ttl_hours: int = 2) -> WorkspaceCreateResult:
        """
        Create a new isolated workspace for code execution.
        
        Args:
            ttl_hours: Workspace lifetime in hours (default: 2, max: 24)
            
        Returns:
            WorkspaceCreateResult with success/error status and workspace info
        """
        try:
            logger.info(f"Creating workspace with TTL {ttl_hours} hours")
            
            if self.sandbox_client:
                client_workspace_info = await self.sandbox_client.create_workspace(ttl_hours=ttl_hours)
            else:
                async with SandboxClient() as client:
                    client_workspace_info = await client.create_workspace(ttl_hours=ttl_hours)
            
            # Convert to our model
            workspace_info = client_workspace_info
            
            logger.info(f"Successfully created workspace {workspace_info.workspace_id} with TTL {ttl_hours}h")
            return WorkspaceCreateResult.success_result(workspace_info)
            
        except WorkspaceError as e:
            logger.error(f"Failed to create workspace: {e}")
            return WorkspaceCreateResult.error_result(str(e))
        except Exception as e:
            logger.error(f"Unexpected error creating workspace: {e}")
            return WorkspaceCreateResult.error_result(f"Unexpected error: {e}")
    
    async def get_workspace(self, workspace_id: str) -> WorkspaceGetResult:
        """
        Get information about an existing workspace.
        
        Args:
            workspace_id: Workspace identifier
            
        Returns:
            WorkspaceGetResult with workspace details or error
        """
        try:
            logger.debug(f"Getting workspace info for {workspace_id}")
            
            if self.sandbox_client:
                client_workspace_info = await self.sandbox_client.get_workspace(workspace_id)
            else:
                async with SandboxClient() as client:
                    client_workspace_info = await client.get_workspace(workspace_id)
            
            logger.info(f"Successfully retrieved workspace {workspace_id}")
            return WorkspaceGetResult.success_result(client_workspace_info)
            
        except WorkspaceNotFoundError as e:
            logger.warning(f"Workspace {workspace_id} not found: {e}")
            return WorkspaceGetResult.error_result(f"Workspace {workspace_id} not found: {e}")
        except Exception as e:
            logger.error(f"Failed to get workspace {workspace_id}: {e}")
            return WorkspaceGetResult.error_result(f"Failed to get workspace {workspace_id}: {e}")
    
    async def delete_workspace(self, workspace_id: str) -> WorkspaceDeleteResult:
        """
        Delete a workspace and clean up all its resources.
        
        Args:
            workspace_id: Workspace to delete
            
        Returns:
            WorkspaceDeleteResult with success/error status
        """
        try:
            logger.info(f"Deleting workspace {workspace_id}")
            
            if self.sandbox_client:
                success = await self.sandbox_client.delete_workspace(workspace_id)
            else:
                async with SandboxClient() as client:
                    success = await client.delete_workspace(workspace_id)
            
            if success:
                logger.info(f"Successfully deleted workspace {workspace_id}")
                return WorkspaceDeleteResult.success_result(workspace_id)
            else:
                return WorkspaceDeleteResult.error_result(workspace_id, "Failed to delete workspace")
                
        except WorkspaceNotFoundError as e:
            logger.warning(f"Workspace {workspace_id} not found for deletion: {e}")
            return WorkspaceDeleteResult.error_result(workspace_id, f"Workspace not found: {e}")
        except Exception as e:
            logger.error(f"Failed to delete workspace {workspace_id}: {e}")
            return WorkspaceDeleteResult.error_result(workspace_id, str(e))
    
    async def extend_workspace_ttl(self, workspace_id: str, additional_hours: int) -> WorkspaceTTLExtendResult:
        """
        Extend the time-to-live (TTL) of a workspace.
        
        Args:
            workspace_id: Workspace to extend
            additional_hours: Hours to add to the current TTL
            
        Returns:
            WorkspaceTTLExtendResult with success/error status
        """
        try:
            logger.info(f"Extending workspace {workspace_id} TTL by {additional_hours} hours")
            
            if self.sandbox_client:
                workspace_info = await self.sandbox_client.extend_workspace_ttl(workspace_id, additional_hours)
            else:
                async with SandboxClient() as client:
                    workspace_info = await client.extend_workspace_ttl(workspace_id, additional_hours)
            
            logger.info(f"Successfully extended workspace {workspace_id} TTL by {additional_hours}h (expires: {workspace_info.expires_at})")
            return WorkspaceTTLExtendResult.success_result(workspace_info)
            
        except WorkspaceNotFoundError as e:
            logger.warning(f"Workspace {workspace_id} not found for TTL extension: {e}")
            return WorkspaceTTLExtendResult.error_result(f"Workspace {workspace_id} not found: {e}")
        except Exception as e:
            logger.error(f"Failed to extend workspace {workspace_id} TTL by {additional_hours}h: {e}")
            return WorkspaceTTLExtendResult.error_result(f"Failed to extend workspace {workspace_id} TTL: {e}")
    
# Conversion method removed - client and service now use same models 