#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Code Executor Tools

Atomic function tools for workspace management, file operations, and code execution.

Architecture:
- services/ - Core business logic classes (WorkspaceService, FileService, ExecutionService)
- *_tools.py - Thin @function_tool wrappers around services for LLM usage

This design allows flexible usage:
- Direct service usage: WorkspaceService().create_workspace(ttl_hours=4)
- LLM tool usage: create_workspace(ttl_hours=4)

All tools return proper Pydantic result models instead of raw dictionaries.
"""

# Import tools for LLM usage
from .workspace_tools import (
    create_workspace,
    get_workspace,
    delete_workspace,
    extend_workspace_ttl
)

from .file_tools import (
    upload_file,
    download_file,
    list_workspace_files
)

from .execution_tools import (
    execute_code,
    get_execution_result,
    list_workspace_executions
)

__all__ = [
    # Workspace tools (for LLM usage)
    "create_workspace",
    "get_workspace", 
    "delete_workspace",
    "extend_workspace_ttl",
    
    # File tools (for LLM usage)
    "upload_file",
    "download_file",
    "list_workspace_files",
    
    # Execution tools (for LLM usage)
    "execute_code",
    "get_execution_result",
    "list_workspace_executions"
] 