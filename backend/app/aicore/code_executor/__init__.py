#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Code Executor Module

Provides isolated workspace execution with automatic resource management.
"""

# Export workspace session functionality
from .workspace_session import (
    WorkspaceExecutionSession,
    create_session_aware_code_tools
)

# Export auto workspace session functionality (NEW - RECOMMENDED)
from .auto_workspace_session import (
    AutoWorkspaceSession,
    AutoWorkspaceToolsInfo,
    create_auto_workspace_tools
)

from .workspace_session_config import (
    create_workspace_session_tools_config,
    create_workspace_session_tools_config_simple,
    get_workspace_session_enhanced_agent_config,
    get_workspace_session_override_config,
    get_unified_tools_with_session_config,
    create_managed_workspace_session,
    create_auto_session_code_tools  # NEW contextvars-based approach
)

__all__ = [
    # Core session management (legacy)
    "WorkspaceExecutionSession",
    "create_session_aware_code_tools",
    
    # Auto workspace session (NEW - RECOMMENDED)
    "AutoWorkspaceSession",
    "AutoWorkspaceToolsInfo", 
    "create_auto_workspace_tools",
    
    # Configuration helpers
    "create_workspace_session_tools_config",
    "create_workspace_session_tools_config_simple", 
    "get_workspace_session_enhanced_agent_config",
    "get_workspace_session_override_config",
    "get_unified_tools_with_session_config",
    "create_managed_workspace_session",
    "create_auto_session_code_tools",  # NEW contextvars-based approach
]
