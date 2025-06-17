#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Memory Tools Configuration Helper
Provides easy configuration of memory tools for AI agents
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.memory.memory_service import MemoryService
from aicore.logger import get_logger

logger = get_logger(__name__)


def create_memory_tools_config(
    user_id: int, 
    conversation_id: str,
    db_session: AsyncSession
) -> List[Dict[str, Any]]:
    """
    Create memory tools configuration for a specific user and conversation.
    
    This function returns the configuration that should be added to the 
    agent's custom_tools configuration.
    
    Args:
        user_id: User ID for memory operations
        conversation_id: Current conversation ID
        db_session: Database session for memory operations
        
    Returns:
        List of tool configurations ready for agent config
    """
    
    # Create memory service instance
    memory_service = MemoryService(db_session)
    
    # Configure memory retrieval tool
    memory_retrieval_config = {
        "name": "memory_retrieval",
        "params": {
            "memory_service": memory_service,
            "user_id": user_id
        }
    }
    
    # Configure memory update tool  
    memory_update_config = {
        "name": "memory_update",
        "params": {
            "memory_service": memory_service,
            "user_id": user_id,
            "conversation_id": conversation_id
        }
    }
    
    logger.info(f"Created memory tools config for user {user_id}, conversation {conversation_id}")
    
    return [memory_retrieval_config, memory_update_config]


async def get_memory_enhanced_agent_config(
    base_config: Dict[str, Any],
    user_id: int,
    conversation_id: str,
    db_session: AsyncSession
) -> Dict[str, Any]:
    """
    Enhance an agent configuration with memory tools.
    
    Args:
        base_config: Base agent configuration
        user_id: User ID for memory operations
        conversation_id: Current conversation ID  
        db_session: Database session for memory operations
        
    Returns:
        Enhanced configuration with memory tools added
    """
    
    # Make a copy of the base config
    enhanced_config = base_config.copy()
    
    # Get memory tools configuration
    memory_tools = create_memory_tools_config(user_id, conversation_id, db_session)
    
    # Add to custom_tools in agent section
    if "agent" not in enhanced_config:
        enhanced_config["agent"] = {}
    
    if "custom_tools" not in enhanced_config["agent"]:
        enhanced_config["agent"]["custom_tools"] = []
    
    # Add memory tools to existing custom tools
    enhanced_config["agent"]["custom_tools"].extend(memory_tools)
    
    logger.info(f"Enhanced agent config with {len(memory_tools)} memory tools")
    
    return enhanced_config


def get_memory_enabled_override_config(
    user_id: int,
    conversation_id: str, 
    db_session: AsyncSession
) -> Dict[str, Any]:
    """
    Get a configuration override that adds memory tools.
    
    This can be used as the config_overrides parameter when creating
    an assistant client.
    
    Args:
        user_id: User ID for memory operations
        conversation_id: Current conversation ID
        db_session: Database session for memory operations
        
    Returns:
        Configuration override dict
    """
    
    memory_tools = create_memory_tools_config(user_id, conversation_id, db_session)
    
    return {
        "agent": {
            "custom_tools": memory_tools
        }
    } 