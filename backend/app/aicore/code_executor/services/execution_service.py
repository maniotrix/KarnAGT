#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Execution Service

Core business logic for code execution in workspaces.
Separated from tool decorators for flexibility and reusability.
"""

from typing import Optional
from pydantic import ValidationError
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
from app.aicore.code_executor.config import enhance_execution_result_with_full_urls

# Get logger
logger = get_logger(__name__)


class ExecutionService:
    """
    Service class for code execution in workspaces.
    
    Provides clean methods that can be used directly or wrapped with decorators.
    All methods return proper Pydantic result models with full download URLs.
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
            ExecutionOperationResult with success/error status and execution details.
            Generated files will have full HTTP download URLs.
        """
        # Input validation - prevent server call for invalid inputs
        if not workspace_id or not workspace_id.strip():
            logger.warning("Attempted to execute code with empty workspace ID")
            return ExecutionOperationResult.error_result("Workspace ID cannot be empty")
            
        if not code or not code.strip():
            logger.warning("Attempted to execute empty code")
            return ExecutionOperationResult.error_result("Code cannot be empty")
            
        if timeout <= 0 or timeout > 300:  # Reasonable bounds
            logger.warning(f"Invalid timeout value: {timeout}")
            return ExecutionOperationResult.error_result("Timeout must be between 1 and 300 seconds")
        
        try:
            logger.info(f"Executing code in workspace {workspace_id} (timeout: {timeout}s)")
            logger.debug(f"Code to execute:\n{code}")
            
            if self.sandbox_client:
                client_execution_result = await self.sandbox_client.execute_code(workspace_id, code, timeout)
            else:
                async with SandboxClient() as client:
                    client_execution_result = await client.execute_code(workspace_id, code, timeout)
            
            # Enhance execution result with full download URLs
            enhance_execution_result_with_full_urls(client_execution_result, workspace_id)
            
            logger.info(f"Code execution completed successfully in {client_execution_result.execution_time_ms}ms")
            if client_execution_result.generated_files:
                logger.info(f"Generated {len(client_execution_result.generated_files)} files with full download URLs")
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
        except ValidationError as e:
            logger.warning(f"Server returned invalid execution result structure: {e}")
            return ExecutionOperationResult.error_result("Invalid execution result format received from server")
        except Exception as e:
            logger.error(f"Unexpected error during code execution in workspace {workspace_id}: {e}")
            return ExecutionOperationResult.error_result(f"Unexpected error: {e}")
    
    async def get_execution_result(self, execution_id: str) -> ExecutionGetResult:
        """
        Get the result of a previous code execution by its ID.
        
        Args:
            execution_id: Unique execution identifier
            
        Returns:
            ExecutionGetResult with success/error status and execution details.
            Generated files will have full HTTP download URLs.
        """
        # Input validation
        if not execution_id or not execution_id.strip():
            logger.warning("Attempted to get execution result with empty execution ID")
            return ExecutionGetResult.error_result("Execution ID cannot be empty")
        
        try:
            logger.debug(f"Getting execution result for {execution_id}")
            
            if self.sandbox_client:
                client_execution_result = await self.sandbox_client.get_execution_result(execution_id)
            else:
                async with SandboxClient() as client:
                    client_execution_result = await client.get_execution_result(execution_id)
            
            # Enhance execution result with full download URLs
            enhance_execution_result_with_full_urls(client_execution_result, client_execution_result.workspace_id)
            
            logger.info(f"Successfully retrieved execution result {execution_id}")
            return ExecutionGetResult.success_result(client_execution_result)
            
        except WorkspaceNotFoundError as e:
            logger.warning(f"Execution {execution_id} not found: {e}")
            return ExecutionGetResult.error_result(f"Execution not found: {e}")
        except ValidationError as e:
            logger.warning(f"Server returned invalid execution result structure for {execution_id}: {e}")
            return ExecutionGetResult.error_result("Invalid execution result format received from server")
        except Exception as e:
            logger.error(f"Failed to get execution result {execution_id}: {e}")
            return ExecutionGetResult.error_result(f"Failed to get execution result: {e}")
    
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
            ExecutionHistoryResult with success/error status and execution list.
            Generated files in execution summaries will have full HTTP download URLs.
        """
        # Input validation
        if not workspace_id or not workspace_id.strip():
            logger.warning("Attempted to list executions with empty workspace ID")
            return ExecutionHistoryResult.error_result(workspace_id, "Workspace ID cannot be empty")
            
        # Normalize limit to reasonable bounds
        if limit <= 0:
            limit = 10
        elif limit > 100:
            limit = 100
            logger.info(f"Execution list limit capped at 100 for workspace {workspace_id}")
        
        try:
            logger.debug(f"Listing executions for workspace {workspace_id} (limit: {limit})")
            
            if self.sandbox_client:
                client_executions = await self.sandbox_client.list_workspace_executions(workspace_id, limit)
            else:
                async with SandboxClient() as client:
                    client_executions = await client.list_workspace_executions(workspace_id, limit)
            
            # Enhance all execution results with full download URLs
            for client_execution in client_executions:
                enhance_execution_result_with_full_urls(client_execution, workspace_id)
            
            # Convert to our models with safe handling
            executions = []
            for client_execution in client_executions:
                try:
                    exec_summary = ExecutionSummary(
                        execution_id=client_execution.execution_id,
                        workspace_id=workspace_id,
                        status=client_execution.status,
                        started_at=client_execution.started_at,
                        completed_at=client_execution.completed_at,
                        execution_time_ms=client_execution.execution_time_ms,
                        has_result_data=client_execution.result_data is not None,
                        generated_files_count=len(client_execution.generated_files) if client_execution.generated_files else 0,
                        has_stdout=bool(client_execution.stdout.strip()) if client_execution.stdout else False,
                        has_stderr=bool(client_execution.stderr.strip()) if client_execution.stderr else False
                    )
                    executions.append(exec_summary)
                except Exception as e:
                    logger.warning(f"Skipping invalid execution result in list: {e}")
                    continue
            
            logger.info(f"Successfully listed {len(executions)} executions for workspace {workspace_id}")
            return ExecutionHistoryResult.success_result(workspace_id, executions)
            
        except WorkspaceNotFoundError as e:
            logger.info(f"Workspace {workspace_id} not found for execution listing - returning empty list")
            # Server behavior: return empty list for non-existent workspace
            return ExecutionHistoryResult.success_result(workspace_id, [])
        except ValidationError as e:
            logger.warning(f"Server returned invalid execution list structure for workspace {workspace_id}: {e}")
            return ExecutionHistoryResult.error_result(workspace_id, "Invalid execution list format received from server")
        except Exception as e:
            logger.error(f"Failed to list executions for workspace {workspace_id}: {e}")
            return ExecutionHistoryResult.error_result(workspace_id, f"Failed to list executions: {e}") 