#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Code Execution Tools

Atomic function tools for code execution in workspaces.
Thin wrappers around ExecutionService for LLM tool usage.
"""

from agents import function_tool

from app.aicore.code_executor.models import (
    ExecutionOperationResult,
    ExecutionGetResult,
    ExecutionHistoryResult
)
from app.aicore.code_executor.services import ExecutionService

# Shared service instance
_execution_service = ExecutionService()


@function_tool(strict_mode=False)
async def execute_code(
    workspace_id: str, 
    code: str, 
    timeout: int = 60
) -> ExecutionOperationResult:
    """
    Execute Python code in a workspace.
    
    The code runs in a persistent Jupyter kernel environment where:
    - Variables and imports persist across executions in the same workspace
    - Files uploaded to the workspace are accessible
    - Generated files are saved to the workspace
    - Standard output/error is captured
    
    Args:
        workspace_id: Target workspace identifier
        code: Python code to execute
        timeout: Execution timeout in seconds (default: 60)
        
    Returns:
        ExecutionResult containing:
        - success: True if execution completed without errors
        - execution_id: Unique execution identifier if successful
        - workspace_id: The workspace identifier
        - status: Execution status ("completed", "failed", "timeout")
        - stdout: Standard output from code execution
        - stderr: Standard error from code execution
        - result_data: Value of 'result' variable if set in code
        - outputs: List of rich outputs (plots, dataframes, etc.)
        - generated_files: List of files created during execution
        - execution_time_ms: Execution time in milliseconds
        - error: Error message if failed
        
    Example:
        # Basic code execution
        result = await execute_code("ws_abc123", '''
import pandas as pd
import matplotlib.pyplot as plt

# Create sample data
data = {'x': [1, 2, 3, 4], 'y': [2, 4, 1, 3]}
df = pd.DataFrame(data)

# Create plot
plt.figure(figsize=(8, 6))
plt.plot(df['x'], df['y'], 'bo-')
plt.title('Sample Plot')
plt.savefig('outputs/plot.png')
plt.close()

# Set result variable
result = {"rows": len(df), "plot_saved": True}
        ''')
        
        if result.success:
            print(f"Execution completed in {result.execution_time_ms}ms")
            print(f"Generated {len(result.generated_files)} files")
            if result.result_data:
                print(f"Result: {result.result_data}")
        else:
            print(f"Execution failed: {result.error}")
    """
    return await _execution_service.execute_code(workspace_id, code, timeout)


@function_tool(strict_mode=False)
async def get_execution_result(execution_id: str) -> ExecutionGetResult:
    """
    Get the result of a previous code execution by its ID.
    
    Useful for retrieving execution results after the fact,
    or for checking the status of long-running executions.
    
    Args:
        execution_id: Unique execution identifier
        
    Returns:
        ExecutionResult containing:
        - success: True if execution result was found
        - execution_id: The execution identifier
        - workspace_id: Workspace where execution occurred
        - status: Execution status
        - stdout: Standard output
        - stderr: Standard error  
        - result_data: Result data if available
        - outputs: Rich outputs
        - generated_files: Generated files
        - execution_time_ms: Execution time
        - error: Error message if failed
        
    Example:
        result = await get_execution_result("exec_xyz789")
        if result.success:
            print(f"Execution {result.execution_id} status: {result.status}")
            if result.result_data:
                print(f"Result: {result.result_data}")
        else:
            print(f"Failed to get result: {result.error}")
    """
    return await _execution_service.get_execution_result(execution_id)


@function_tool(strict_mode=False)
async def list_workspace_executions(
    workspace_id: str, 
    limit: int = 10
) -> ExecutionHistoryResult:
    """
    List recent code executions in a workspace.
    
    Shows the execution history for a workspace, useful for:
    - Debugging execution issues
    - Reviewing what code was run
    - Finding execution IDs for detailed results
    
    Args:
        workspace_id: Workspace to list executions from
        limit: Maximum number of executions to return (default: 10)
        
    Returns:
        ExecutionHistoryResult containing:
        - success: True if executions were listed successfully
        - workspace_id: The workspace identifier
        - executions: List of ExecutionSummary objects if successful
        - total_executions: Number of executions returned if successful
        - error: Error message if failed
        
    Example:
        result = await list_workspace_executions("ws_abc123", limit=5)
        if result.success:
            print(f"Found {result.total_executions} recent executions:")
            for exec in result.executions:
                status = exec.status
                duration = exec.execution_time_ms
                print(f"  {exec.execution_id}: {status} ({duration}ms)")
        else:
            print(f"Failed to list executions: {result.error}")
    """
    return await _execution_service.list_workspace_executions(workspace_id, limit) 