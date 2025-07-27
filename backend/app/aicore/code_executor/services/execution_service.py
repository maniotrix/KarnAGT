#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Execution Service

Core business logic for code execution in workspaces.
Separated from tool decorators for flexibility and reusability.
"""

from typing import Optional
from app.logging.logger import get_logger
from app.aicore.code_executor.clients import (
    SandboxClient,
    WorkspaceNotFoundError,
    ExecutionError,
    ExecutionTimeoutError
)
from app.aicore.code_executor.models import (
    ExecutionOperationResult,
    ExecutionGetResult,
    ExecutionSummary,
    ExecutionHistoryResult
)

# Get logger
logger = get_logger(__name__)


class ExecutionService:
    """
    Service class for code execution in workspaces.
    
    Provides clean methods that can be used directly or wrapped with decorators.
    All methods return proper Pydantic result models.
    """
    
    def __init__(self, sandbox_client: Optional[SandboxClient] = None):
        """
        Initialize the execution service.
        
        Args:
            sandbox_client: Optional pre-configured client. If None, creates new clients per operation.
        """
        self.sandbox_client = sandbox_client
    
    async def execute_code(
        self, 
        workspace_id: str, 
        code: str, 
        timeout: int = 60
    ) -> ExecutionOperationResult:
        """
        Execute Python code in a workspace.
        
        Args:
            workspace_id: Target workspace identifier
            code: Python code to execute
            timeout: Execution timeout in seconds (default: 60)
            
        Returns:
            ExecutionOperationResult with success/error status and execution details
        """
        try:
            logger.info(f"Executing code in workspace {workspace_id} (timeout: {timeout}s)")
            logger.debug(f"Code to execute:\n{code}")
            
            if self.sandbox_client:
                client_execution_result = await self.sandbox_client.execute_code(workspace_id, code, timeout)
            else:
                async with SandboxClient() as client:
                    client_execution_result = await client.execute_code(workspace_id, code, timeout)
            
            logger.info(f"Code execution completed successfully in {client_execution_result.execution_time_ms}ms")
            if client_execution_result.generated_files:
                logger.info(f"Generated {len(client_execution_result.generated_files)} files")
            if client_execution_result.status != "completed":
                logger.warning(f"Code execution failed with status: {client_execution_result.status}")
                
            return ExecutionOperationResult.success_result(client_execution_result)
            
        except WorkspaceNotFoundError as e:
            logger.warning(f"Workspace {workspace_id} not found for code execution: {e}")
            return ExecutionOperationResult.error_result(f"Workspace not found: {e}")
        except ExecutionTimeoutError as e:
            logger.warning(f"Code execution timed out in workspace {workspace_id}: {e}")
            return ExecutionOperationResult.error_result(f"Code execution timed out: {e}")
        except ExecutionError as e:
            logger.error(f"Code execution failed in workspace {workspace_id}: {e}")
            return ExecutionOperationResult.error_result(f"Code execution failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during code execution in workspace {workspace_id}: {e}")
            return ExecutionOperationResult.error_result(f"Unexpected error: {e}")
    
    async def get_execution_result(self, execution_id: str) -> ExecutionGetResult:
        """
        Get the result of a previous code execution by its ID.
        
        Args:
            execution_id: Unique execution identifier
            
        Returns:
            ExecutionResult with success/error status and execution details
        """
        try:
            logger.debug(f"Getting execution result for {execution_id}")
            
            if self.sandbox_client:
                client_execution_result = await self.sandbox_client.get_execution_result(execution_id)
            else:
                async with SandboxClient() as client:
                    client_execution_result = await client.get_execution_result(execution_id)
            
            workspace_id = client_execution_result.workspace_id if client_execution_result else "unknown"
            logger.info(f"Successfully retrieved execution result {execution_id} for workspace {workspace_id}")
            return ExecutionGetResult.success_result(client_execution_result)
            
        except ExecutionError as e:
            logger.warning(f"Execution result {execution_id} not found: {e}")
            return ExecutionGetResult.error_result(f"Execution result not found: {e}")
        except Exception as e:
            logger.error(f"Failed to get execution result {execution_id}: {e}")
            return ExecutionGetResult.error_result(f"Unexpected error: {e}")
    
    async def list_workspace_executions(
        self, 
        workspace_id: str, 
        limit: int = 10
    ) -> ExecutionHistoryResult:
        """
        List recent code executions in a workspace.
        
        Args:
            workspace_id: Workspace to list executions from
            limit: Maximum number of executions to return (default: 10)
            
        Returns:
            ExecutionHistoryResult with success/error status and execution list
        """
        try:
            logger.debug(f"Listing executions for workspace {workspace_id} (limit: {limit})")
            
            if self.sandbox_client:
                client_executions = await self.sandbox_client.list_workspace_executions(workspace_id, limit)
            else:
                async with SandboxClient() as client:
                    client_executions = await client.list_workspace_executions(workspace_id, limit)
            
            # Convert to our models
            executions = []
            for client_execution in client_executions:
                exec_summary = ExecutionSummary(
                    execution_id=client_execution.execution_id,
                    workspace_id=workspace_id,
                    status=client_execution.status,
                    started_at=client_execution.started_at,
                    completed_at=client_execution.completed_at,
                    execution_time_ms=client_execution.execution_time_ms,
                    has_result_data=client_execution.result_data is not None,
                    generated_files_count=len(client_execution.generated_files),
                    has_stdout=bool(client_execution.stdout.strip()),
                    has_stderr=bool(client_execution.stderr.strip())
                )
                executions.append(exec_summary)
            
            logger.info(f"Successfully listed {len(executions)} executions for workspace {workspace_id}")
            return ExecutionHistoryResult.success_result(workspace_id, executions)
            
        except WorkspaceNotFoundError as e:
            logger.warning(f"Workspace {workspace_id} not found for execution listing: {e}")
            return ExecutionHistoryResult.error_result(workspace_id, f"Workspace not found: {e}")
        except Exception as e:
            logger.error(f"Failed to list executions for workspace {workspace_id}: {e}")
            return ExecutionHistoryResult.error_result(workspace_id, str(e)) 