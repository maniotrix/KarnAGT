#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Default LLM-exposed Code-Execution Tools

Only **three** capabilities are exposed to language-model agents:
1. create_workspace – provision a brand-new, isolated sandbox
2. upload_file      – push a resource into that sandbox
3. execute_code     – run Python code inside that sandbox (synchronous)

Everything else (file download, workspace deletion/TTL, listing helpers, etc.)
is handled by background subsystems or other privileged processes – **not**
made visible to the LLM.  This keeps the public tool surface minimal and
prevents the model from exfiltrating raw file bytes while still letting it
reference generated download URLs.

Implementation details:
• Thin wrappers around WorkspaceService, FileService, ExecutionService
• Uses the same @function_tool decorator interface as memory tools so the
  agent framework can auto-register them with rich metadata.
"""
from typing import Optional
from agents import function_tool

from app.aicore.code_executor.services import (
    WorkspaceService,
    FileService,
    ExecutionService,
)
from app.aicore.code_executor.models import (
    WorkspaceCreateResult,
    FileUploadResult,
    ExecutionOperationResult,
)

# Single shared service instances (no state kept between calls except
# what the backend sandbox server maintains for each workspace).
_workspace_service = WorkspaceService()
_file_service = FileService()
_execution_service = ExecutionService()


@function_tool(
    name_override="create_workspace",
    description_override="""
    Create a new isolated workspace for Python code execution.
    
    HOW IT WORKS:
    - Creates a fresh Python environment with Jupyter kernel
    - Workspace automatically expires after 2 hours (system managed)
    - Variables and imports persist across multiple code executions
    
    WHEN TO USE:
    - At the start of any coding task or data analysis
    - When you need a clean environment for Python execution
    - Before uploading files or running any code
    
    WHAT YOU GET BACK:
    - workspace_id: Use this for all subsequent upload_file and execute_code calls
    - status: "ready" when workspace is available for use
    - expires_at: When the workspace will be automatically cleaned up
    """,
    strict_mode=True,
)
async def create_workspace() -> WorkspaceCreateResult:
    """Create a new isolated workspace for code execution."""
    return await _workspace_service.create_workspace()


@function_tool(
    name_override="upload_file",
    description_override="""
    Upload a file to a a given workspace with a workspace_id so it can be accessed by Python code.
    
    ## CRITICAL FILE UPLOAD INSTRUCTIONS:
    File must be a valid Full HTTP URL and the maximum file size allowed is 20MB.
    You must provide a file_name to be used for the file in the workspace.
    
    ## REQUIRED PARAMETERS:
    - workspace_id: Valid workspace ID from create_workspace()
    - file_url: Valid Full HTTP URL
    - file_name: Name of the file
    
    ## RETURN VALUE STRUCTURE:
    The tool returns a FileUploadResult containing:
    - **success**: boolean indicating if upload completed successfully
    - **file_info**: FileInfo object with details about the uploaded file
    - **error**: Optional error message if upload failed
    
    HOW IT WORKS:
    - Uploads file to the workspace's root directory
    - Files become immediately available for code execution
    
    WHEN TO USE:
    - Upload datasets, images, or any input files needed for analysis
    - Provide configuration files, scripts, or resources
    - Before running code that needs to read specific files
    
    WHAT YOU GET BACK:
    - Confirmation of successful upload or specific error message
    - File size and location information along with a download URL
    - Ready for use in execute_code calls with the workspace_id
    """,
    strict_mode=True,
)
async def upload_file(
    workspace_id: str,
    file_url: str,
    file_name: str,
) -> FileUploadResult:
    """Upload a file to a workspace for code execution access.
    
    Args:
        workspace_id: Target workspace identifier
        file_url: Valid Full HTTP URL
        file_name: Name of the file
        
    Returns:
        FileUploadResult with success/error status and file info
    """
    return await _file_service.download_and_upload_file_to_workspace(workspace_id, file_url, file_name)


@function_tool(
    name_override="execute_code",
    description_override="""
    Execute Python code in a isolated workspace with a valid workspace_id with persistent state and file generation capabilities.
    
    ## REQUIRED PARAMETERS:
    - workspace_id: Valid workspace ID from create_workspace()
    - code: Python code string

    ## RETURN VALUE STRUCTURE:
    The tool returns an ExecutionOperationResult containing:
    - **success**: boolean indicating if execution completed successfully
    - **standard output**: text that was printed during execution  
    - **error messages**: any error messages that occurred
    - **generated files**: list of files created during execution with full HTTP download URLs
    - **result data**: the final computed result (if any)
    
    ## CRITICAL REQUIREMENT FOR CODE EXECUTION: 
    - You MUST have a valid workspace_id before calling this function
    - If you don't have one, call create_workspace() FIRST to get a workspace_id
    - NEVER use arbitrary workspace IDs like "1", "test", etc.
    - ALWAYS use the exact workspace_id returned by create_workspace()
    - If a piece of code times-out, do not run **the same code** again.
    - DO NOT make up or estimate results for failed or timed out code executions
    - ALWAYS check if the execution succeeded before using any outputs
    
    
    ## CODE EXECUTION ENVIRONMENT:
    - Jupyter kernel with persistent variables/imports across calls
    - Working directory: workspace root (contains uploaded files)
    - Full Python standard library + common packages (numpy, pandas, matplotlib, etc.)
    - Output capture: stdout, stderr, and execution results
    - Your code will be executed with a timeout of 30 seconds.
    
    ## FILE OPERATIONS:
    - **Read files**: open('filename.txt', 'r') - access uploaded files directly
    - **Create files**: open('output.csv', 'w') - any file you create gets tracked
    - **Generate plots**: plt.savefig('chart.png') - saved plots are automatically detected

    ## EXAMPLES:
    ```python
    # Data analysis with CSV output
    df.to_csv('analysis_results.csv', index=False)
    
    # Visualization with plot file
    plt.figure(figsize=(10,6))
    plt.plot(data)
    plt.savefig('visualization.png', dpi=300, bbox_inches='tight')
    
    # Generate reports or documents  
    with open('report.txt', 'w') as f:
        f.write(f"Analysis completed: {results}")
    ```

    ## BEST PRACTICES and DATA VISUALIZATION INSTRUCTIONS:
    - DO NOT use plt.show() as it will cause errors in the execution environment.
    - Always close plt figures: plt.close() after plt.savefig()
    - Use descriptive filenames with extensions
    - Save files you want users to access (they get full HTTP download URLs automatically)
    - Use result = your_final_value to return computed results
    """,
    strict_mode=True,
)
async def execute_code(
    workspace_id: str,
    code: str,
) -> ExecutionOperationResult:
    """Execute Python code in a workspace with persistent state."""
    return await _execution_service.execute_code(workspace_id, code)


# What gets imported when using `from default_llm_code_tools import *`
__all__ = [
    "create_workspace",
    "upload_file",
    "execute_code",
]
