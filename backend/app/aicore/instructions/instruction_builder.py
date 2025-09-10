#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Instruction Builder - Dynamic instruction generation with built-in memory support
"""

from typing import Optional
from dataclasses import dataclass

# Use absolute imports to avoid circular import issues
from app.aicore.config.agent_config import AgentConfig
from app.aicore.instructions.prompt_utils import get_default_core_prompt, get_default_all_tools_enabled_system_prompt, ModelVersion
from app.logging.logger import get_logger

# Set up logger
logger = get_logger(__name__)


@dataclass
class InstructionContext:
    """Context information for instruction generation"""
    message_id: str
    os_type: str = "Windows"
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class InstructionBuilder:
    """Builds dynamic instructions with built-in memory support
    
    TODO: Add proper instruct context caching as well as memory context caching
        
    """
    
    def __init__(self, config: AgentConfig, model_version: ModelVersion = ModelVersion.GPT_5):
        """
        Initialize the instruction builder
        
        Args:
            config: Agent configuration to use for instruction generation
            model_version: Model version to use for prompt selection
        """
        self.config = config
        self.model_version = model_version
        
    async def build_instructions(self, context: InstructionContext) -> str:
        """
        Build complete instructions with automatic memory context
        
        Args:
            context: Context information for instruction generation
            
        Returns:
            Complete instruction string with memory context
        """
        # Start with core prompt
        instructions = self._get_core_prompt()
        memory_context = None
        
        # Add memory context if user_id is available (simplified approach)
        if context.user_id:
            memory_context = await self._get_memory_context(context.user_id)
            if memory_context:
                logger.info(f"Adding memory context: {memory_context}")
            else:
                logger.warning(f"No memory context found for user {context.user_id}")
        
        # Add the template
        instructions += self._get_original_template(context, memory_context)
        
        logger.info(f"Instructions built for model {self.model_version}")
        
        return instructions
    
    async def _get_memory_context(self, user_uuid: str) -> str:
        """
        Get essential user memory context - simplified approach
        
        Args:
            user_uuid: User UUID string for memory lookup
            
        Returns:
            Formatted memory context string or empty string
        """
        try:
            # Import here to avoid circular imports
            from app.core.database import AsyncSessionLocal
            from app.services.memory.memory_service import MemoryService
            from app.services.memory.llm_memory_tools import get_essential_user_context
            from app.models.database.user import User
            from sqlalchemy import select
            
            # Create fresh database session and memory service
            async with AsyncSessionLocal() as db_session:
                # Look up the integer user_id from the UUID
                query = select(User.id).where(User.user_id == user_uuid)
                result = await db_session.execute(query)
                user_id = result.scalar_one_or_none()
                
                if not user_id:
                    logger.warning(f"User not found for UUID {user_uuid}")
                    return ""
                
                memory_service = MemoryService(db_session)
                
                # Get essential context using integer user_id
                essential_context = await get_essential_user_context(
                    memory_service=memory_service,
                    user_id=user_id
                )
                
                return essential_context
            
        except Exception as e:
            # Log error but don't fail instruction building
            logger.warning(f"Failed to get memory context for user {user_uuid}: {e}")
            return ""
    
    def _get_core_prompt(self) -> str:
        """Get the core prompt for the agent"""
        # if self.config.core_prompt:
        #     return self.config.core_prompt
        return get_default_core_prompt(self.model_version)
    
    def _get_original_template(self, context: InstructionContext, memory_context: Optional[str]) -> str:
        """Get the template from prompt_utils.py and append memory context"""
        
        # Start with the system prompt from prompt_utils.py
        formatted_template = get_default_all_tools_enabled_system_prompt(self.model_version)
        
        # Add memory context if available
        if memory_context and memory_context.strip():
            formatted_template += f"\n\n{memory_context}"
        
        return formatted_template
    
    def update_config(self, new_config: AgentConfig):
        """Update the agent configuration"""
        self.config = new_config
    
    def update_model_version(self, model_version: ModelVersion):
        """Update the model version for prompt selection"""
        self.model_version = model_version 