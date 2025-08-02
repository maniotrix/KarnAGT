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
from app.aicore.code_executor.prompts.tools_prompts import CREATE_WORKSPACE_TOOL_DESCRIPTION
from app.aicore.code_executor.prompts.tools_prompts import UPLOAD_FILE_TOOL_DESCRIPTION
from app.aicore.code_executor.prompts.tools_prompts import EXECUTE_CODE_TOOL_DESCRIPTION


# Single shared service instances (no state kept between calls except
# what the backend sandbox server maintains for each workspace).
_workspace_service = WorkspaceService()
_file_service = FileService()
_execution_service = ExecutionService()


@function_tool(
    name_override="create_workspace",
    description_override=CREATE_WORKSPACE_TOOL_DESCRIPTION,
    strict_mode=True,
)
async def create_workspace() -> WorkspaceCreateResult:
    """Create a new isolated workspace for code execution."""
    return await _workspace_service.create_workspace()


@function_tool(
    name_override="upload_file",
    description_override=UPLOAD_FILE_TOOL_DESCRIPTION,
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
    description_override=EXECUTE_CODE_TOOL_DESCRIPTION,
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
