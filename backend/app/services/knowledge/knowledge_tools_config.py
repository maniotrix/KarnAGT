#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Knowledge Tools Configuration Helper
Provides easy configuration of knowledge tools for AI agents
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge.knowledge_service import KnowledgeService
from app.services.knowledge.llm_knowledge_tools import (
    create_knowledge_search_tool,
    create_knowledge_discovery_tool,
    create_knowledge_service_from_config
)
from aicore.logger import get_logger

logger = get_logger(__name__)


def create_knowledge_tools_config(
    user_uuid: str, 
    conversation_id: str,
    db_session: AsyncSession,
    rag_config_type: str = "chat_application"
) -> List[Dict[str, Any]]:
    """
    Create knowledge tools configuration for a specific user and conversation.
    
    This function returns the configuration that should be added to the 
    agent's custom_tools configuration.
    
    Args:
        user_id: User ID for file access validation
        conversation_id: Current conversation ID
        db_session: Database session for knowledge operations
        rag_config_type: Type of RAG configuration to use (default: "chat_application")
        
    Returns:
        List of tool configurations ready for agent config
    """
    
    # Create knowledge service instance (matches memory tools pattern)
    knowledge_service = create_knowledge_service_from_config(db_session, rag_config_type)
    
    # Configure knowledge search tool
    knowledge_search_config = {
        "name": "knowledge_search",
        "params": {
            "knowledge_service": knowledge_service,
            "user_id": user_uuid,
            "conversation_id": conversation_id
        }
    }
    
    # Configure knowledge discovery tool
    knowledge_discovery_config = {
        "name": "knowledge_discovery",
        "params": {
            "knowledge_service": knowledge_service,
            "user_id": user_uuid,
            "conversation_id": conversation_id
        }
    }
    
    logger.info(f"Created knowledge tools config for user {user_uuid}, conversation {conversation_id} with {rag_config_type} configuration")
    
    return [knowledge_search_config, knowledge_discovery_config]


def create_knowledge_tools_config_with_service(
    user_uuid: str,
    conversation_id: str,
    knowledge_service: KnowledgeService
) -> List[Dict[str, Any]]:
    """
    Create knowledge tools configuration with an existing KnowledgeService.
    
    This is useful when you want to reuse an existing service instance
    or have custom service configuration.
    
    Args:
        user_id: User ID for file access validation
        conversation_id: Current conversation ID
        knowledge_service: Pre-configured KnowledgeService instance
        
    Returns:
        List of tool configurations ready for agent config
    """
    
    # Configure knowledge search tool
    knowledge_search_config = {
        "name": "knowledge_search",
        "params": {
            "knowledge_service": knowledge_service,
            "user_id": user_uuid,
            "conversation_id": conversation_id
        }
    }
    
    # Configure knowledge discovery tool
    knowledge_discovery_config = {
        "name": "knowledge_discovery",
        "params": {
            "knowledge_service": knowledge_service,
            "user_id": user_uuid,
            "conversation_id": conversation_id
        }
    }
    
    logger.info(f"Created knowledge tools config with existing service for user {user_uuid}, conversation {conversation_id}")
    
    return [knowledge_search_config, knowledge_discovery_config]


async def get_knowledge_enhanced_agent_config(
    base_config: Dict[str, Any],
    user_uuid: str,
    conversation_id: str,   
    db_session: AsyncSession,
    rag_config_type: str = "chat_application"
) -> Dict[str, Any]:
    """
    Enhance an agent configuration with knowledge tools.
    
    Args:
        base_config: Base agent configuration
        user_id: User ID for file access validation
        conversation_id: Current conversation ID  
        db_session: Database session for knowledge operations
        rag_config_type: Type of RAG configuration to use
        
    Returns:
        Enhanced configuration with knowledge tools added
    """
    
    # Make a copy of the base config
    enhanced_config = base_config.copy()
    
    # Get knowledge tools configuration
    knowledge_tools = create_knowledge_tools_config(
        user_uuid, conversation_id, db_session, rag_config_type
    )
    
    # Add to custom_tools in agent section
    if "agent" not in enhanced_config:
        enhanced_config["agent"] = {}
    
    if "custom_tools" not in enhanced_config["agent"]:
        enhanced_config["agent"]["custom_tools"] = []
    
    # Add knowledge tools to existing custom tools
    enhanced_config["agent"]["custom_tools"].extend(knowledge_tools)
    
    logger.info(f"Enhanced agent config with {len(knowledge_tools)} knowledge tools")
    
    return enhanced_config


def get_knowledge_enabled_override_config(
    user_uuid: str,
    conversation_id: str, 
    db_session: AsyncSession,
    rag_config_type: str = "chat_application"
) -> Dict[str, Any]:
    """
    Get a configuration override that adds knowledge tools.
    
    This can be used as the config_overrides parameter when creating
    an assistant client.
    
    Args:
        user_id: User ID for file access validation
        conversation_id: Current conversation ID
        db_session: Database session for knowledge operations
        rag_config_type: Type of RAG configuration to use
        
    Returns:
        Configuration override dict
    """
    
    knowledge_tools = create_knowledge_tools_config(
        user_uuid, conversation_id, db_session, rag_config_type
    )
    
    return {
        "agent": {
            "custom_tools": knowledge_tools
        }
    }


def get_unified_tools_override_config(
    user_id: int,
    user_uuid: str,
    conversation_id: str,
    db_session: AsyncSession,
    rag_config_type: str = "chat_application"
) -> Dict[str, Any]:
    """
    Get a configuration override that adds both memory and knowledge tools.
    
    This unified approach provides both memory and knowledge capabilities
    to the AI assistant.
    
    Args:
        user_id: User ID for operations
        conversation_id: Current conversation ID
        db_session: Database session for operations
        rag_config_type: Type of RAG configuration to use for knowledge tools
        
    Returns:
        Configuration override dict with both tool types
    """
    
    # Import memory tools config
    from app.services.memory.memory_tools_config import create_memory_tools_config
    
    # Get both tool configurations
    memory_tools = create_memory_tools_config(user_id, conversation_id, db_session)
    knowledge_tools = create_knowledge_tools_config(
        user_uuid, conversation_id, db_session, rag_config_type
    )
    
    # Combine all tools
    all_tools = memory_tools + knowledge_tools
    
    logger.info(f"Created unified tools config: {len(memory_tools)} memory + {len(knowledge_tools)} knowledge = {len(all_tools)} total tools")
    
    return {
        "agent": {
            "custom_tools": all_tools
        }
    }


# =============================================================================
# UTILITY FUNCTIONS FOR ADVANCED CONFIGURATIONS
# =============================================================================

def create_specialized_knowledge_tools_config(
    user_uuid: str,
    conversation_id: str,
    db_session: AsyncSession,
    optimization_target: str = "balanced"
) -> List[Dict[str, Any]]:
    """
    Create knowledge tools configuration optimized for specific use cases.
    
    Args:
        user_id: User ID for file access validation
        conversation_id: Current conversation ID
        db_session: Database session for knowledge operations
        optimization_target: One of "speed", "accuracy", "cost", "balanced"
        
    Returns:
        List of tool configurations optimized for the target
    """
    
    # Map optimization targets to RAG config types
    optimization_mapping = {
        "speed": "fast_processing",
        "accuracy": "precise_retrieval", 
        "cost": "cost_optimized",
        "balanced": "chat_application",
        "comprehensive": "robust_retrieval"
    }
    
    rag_config_type = optimization_mapping.get(optimization_target, "chat_application")
    
    logger.info(f"Creating specialized knowledge tools config optimized for: {optimization_target}")
    
    return create_knowledge_tools_config(
        user_uuid, conversation_id, db_session, rag_config_type
    )


def get_knowledge_service_from_config(
    db_session: AsyncSession,
    rag_config_type: str = "chat_application"
) -> KnowledgeService:
    """
    Create a standalone KnowledgeService instance.
    
    This is useful when you need to use the service outside of tool configuration.
    
    Args:
        db_session: Database session
        rag_config_type: Type of RAG configuration to use
        
    Returns:
        KnowledgeService instance
    """
    return create_knowledge_service_from_config(db_session, rag_config_type)


def validate_knowledge_tools_config(tools_config: List[Dict[str, Any]]) -> bool:
    """
    Validate that knowledge tools configuration is properly structured.
    
    Args:
        tools_config: List of tool configurations
        
    Returns:
        True if configuration is valid, False otherwise
    """
    
    required_tools = {"knowledge_search", "knowledge_discovery"}
    found_tools = set()
    
    for tool_config in tools_config:
        tool_name = tool_config.get("name")
        if tool_name in required_tools:
            found_tools.add(tool_name)
            
            # Check required parameters
            params = tool_config.get("params", {})
            required_params = {"knowledge_service", "user_id", "conversation_id"}
            
            if not all(param in params for param in required_params):
                logger.error(f"Missing required parameters for {tool_name}: {required_params}")
                return False
    
    if found_tools != required_tools:
        missing_tools = required_tools - found_tools
        logger.error(f"Missing required tools: {missing_tools}")
        return False
    
    logger.info("Knowledge tools configuration is valid")
    return True 