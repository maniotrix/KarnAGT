#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Workspace Session Configuration Helper

Provides easy configuration of workspace session tools for AI agents.
Follows the same pattern as memory and knowledge tools configuration.
"""

from typing import Dict, Any, List, Optional
from app.aicore.code_executor.workspace_session import (
    WorkspaceExecutionSession,
    create_session_aware_code_tools
)
from app.logging.logger import get_logger

logger = get_logger(__name__)


def create_workspace_session_tools_config(
    workspace_session: WorkspaceExecutionSession
) -> List[Dict[str, Any]]:
    """
    Create workspace session tools configuration for an agent.
    
    This function returns the configuration that should be added to the 
    agent's custom_tools configuration, following the same pattern as
    memory and knowledge tools.
    
    Args:
        workspace_session: WorkspaceExecutionSession instance to use for tools
        
    Returns:
        List of tool configurations ready for agent config
    """
    
    # Get the session-aware tools
    session_tools = create_session_aware_code_tools(workspace_session)
    
    # Convert to configuration format expected by tool registry
    tool_configs = []
    for tool in session_tools:
        tool_name = getattr(tool, 'name', str(tool))
        tool_configs.append({
            "name": tool_name,
            "params": {
                "tool_function": tool,
                "workspace_session": workspace_session
            }
        })
    
    logger.info(f"Created workspace session tools config with {len(tool_configs)} tools for session {workspace_session.session_id}")
    
    return tool_configs


def create_workspace_session_tools_config_simple(
    workspace_session: WorkspaceExecutionSession
) -> List:
    """
    Create workspace session tools as a simple list (for direct use).
    
    This is a simpler version that returns the tools directly without
    the configuration wrapper, useful when you want to add them
    directly to an agent's tools list.
    
    Args:
        workspace_session: WorkspaceExecutionSession instance to use for tools
        
    Returns:
        List of function tools ready for agent use
    """
    session_tools = create_session_aware_code_tools(workspace_session)
    
    logger.info(f"Created {len(session_tools)} workspace session tools for session {workspace_session.session_id}")
    
    return session_tools


def get_workspace_session_enhanced_agent_config(
    base_config: Dict[str, Any],
    workspace_session: WorkspaceExecutionSession
) -> Dict[str, Any]:
    """
    Enhance an agent configuration with workspace session tools.
    
    This follows the same pattern as memory and knowledge tools enhancement.
    
    Args:
        base_config: Base agent configuration
        workspace_session: WorkspaceExecutionSession instance
        
    Returns:
        Enhanced configuration with workspace session tools added
    """
    
    # Make a copy of the base config
    enhanced_config = base_config.copy()
    
    # Get workspace session tools configuration  
    session_tools = create_workspace_session_tools_config(workspace_session)
    
    # Add to custom_tools in agent section
    if "agent" not in enhanced_config:
        enhanced_config["agent"] = {}
    
    if "custom_tools" not in enhanced_config["agent"]:
        enhanced_config["agent"]["custom_tools"] = []
    
    # Add session tools to existing custom tools
    enhanced_config["agent"]["custom_tools"].extend(session_tools)
    
    logger.info(f"Enhanced agent config with {len(session_tools)} workspace session tools")
    
    return enhanced_config


def get_workspace_session_override_config(
    workspace_session: WorkspaceExecutionSession
) -> Dict[str, Any]:
    """
    Get a configuration override that adds workspace session tools.
    
    This can be used as the config_overrides parameter when creating
    an assistant client, following the same pattern as knowledge tools.
    
    Args:
        workspace_session: WorkspaceExecutionSession instance
        
    Returns:
        Configuration override dict
    """
    
    session_tools = create_workspace_session_tools_config(workspace_session)
    
    return {
        "agent": {
            "custom_tools": session_tools
        }
    }


def get_unified_tools_with_session_config(
    workspace_session: WorkspaceExecutionSession,
    user_id: Optional[int] = None,
    user_uuid: Optional[str] = None,
    conversation_id: Optional[str] = None,
    db_session: Optional[Any] = None,
    include_memory_tools: bool = False,
    include_knowledge_tools: bool = False,
    rag_config_type: str = "chat_application"
) -> Dict[str, Any]:
    """
    Get a configuration override that adds workspace session tools
    along with optional memory and knowledge tools.
    
    This provides a unified approach for agents that need multiple
    types of tools with automatic resource management.
    
    Args:
        workspace_session: WorkspaceExecutionSession instance
        user_id: User ID for memory/knowledge operations
        user_uuid: User UUID for knowledge operations
        conversation_id: Current conversation ID
        db_session: Database session for memory/knowledge operations
        include_memory_tools: Whether to include memory tools
        include_knowledge_tools: Whether to include knowledge tools
        rag_config_type: Type of RAG configuration for knowledge tools
        
    Returns:
        Configuration override dict with combined tools
    """
    
    all_tools = []
    
    # Add workspace session tools
    session_tools = create_workspace_session_tools_config(workspace_session)
    all_tools.extend(session_tools)
    
    # Add memory tools if requested
    if include_memory_tools and user_id and conversation_id and db_session:
        try:
            from app.services.memory.memory_tools_config import create_memory_tools_config
            memory_tools = create_memory_tools_config(user_id, conversation_id, db_session)
            all_tools.extend(memory_tools)
            logger.info(f"Added {len(memory_tools)} memory tools")
        except ImportError:
            logger.warning("Memory tools requested but memory_tools_config not available")
    
    # Add knowledge tools if requested  
    if include_knowledge_tools and user_uuid and conversation_id and db_session:
        try:
            from app.services.knowledge.knowledge_tools_config import create_knowledge_tools_config
            knowledge_tools = create_knowledge_tools_config(
                user_uuid, conversation_id, db_session, rag_config_type
            )
            all_tools.extend(knowledge_tools)
            logger.info(f"Added {len(knowledge_tools)} knowledge tools")
        except ImportError:
            logger.warning("Knowledge tools requested but knowledge_tools_config not available")
    
    logger.info(f"Created unified tools config with {len(all_tools)} total tools (session: {workspace_session.session_id})")
    
    return {
        "agent": {
            "custom_tools": all_tools
        }
    }


# =============================================================================
# UTILITY FUNCTIONS FOR SESSION MANAGEMENT
# =============================================================================

def create_managed_workspace_session(session_id: Optional[str] = None) -> WorkspaceExecutionSession:
    """
    Create a workspace session instance.
    
    This is a convenience function for creating sessions, useful when you
    want to inject the session creation logic into other systems.
    
    Args:
        session_id: Optional custom session ID
        
    Returns:
        WorkspaceExecutionSession instance
    """
    session = WorkspaceExecutionSession(session_id=session_id)
    logger.info(f"Created managed workspace session: {session.session_id}")
    return session


def validate_workspace_session_config(tools_config: List[Dict[str, Any]]) -> bool:
    """
    Validate that workspace session tools configuration is properly structured.
    
    Args:
        tools_config: List of tool configurations
        
    Returns:
        True if configuration is valid, False otherwise
    """
    
    required_tools = {"create_workspace", "upload_file", "execute_code"}
    found_tools = set()
    
    for tool_config in tools_config:
        tool_name = tool_config.get("name")
        if tool_name in required_tools:
            found_tools.add(tool_name)
            
            # Check required parameters
            params = tool_config.get("params", {})
            if "workspace_session" not in params:
                logger.error(f"Missing workspace_session parameter for {tool_name}")
                return False
    
    if found_tools != required_tools:
        missing_tools = required_tools - found_tools
        logger.error(f"Missing required workspace session tools: {missing_tools}")
        return False
    
    logger.info("Workspace session tools configuration is valid")
    return True


def get_session_info_from_config(tools_config: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Extract session information from tools configuration.
    
    Args:
        tools_config: List of tool configurations
        
    Returns:
        Session info dict or None if no session found
    """
    
    for tool_config in tools_config:
        params = tool_config.get("params", {})
        workspace_session = params.get("workspace_session")
        
        if workspace_session and hasattr(workspace_session, 'get_session_info'):
            return workspace_session.get_session_info()
    
    return None


# =============================================================================
# EXPORT LIST
# =============================================================================

__all__ = [
    "create_workspace_session_tools_config",
    "create_workspace_session_tools_config_simple", 
    "get_workspace_session_enhanced_agent_config",
    "get_workspace_session_override_config",
    "get_unified_tools_with_session_config",
    "create_managed_workspace_session",
    "validate_workspace_session_config",
    "get_session_info_from_config",
]