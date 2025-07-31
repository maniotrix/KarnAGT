#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Instruction Builder - Dynamic instruction generation with built-in memory support
"""

from typing import Optional
from dataclasses import dataclass

# Use absolute imports to avoid circular import issues
from app.aicore.config.agent_config import AgentConfig
from app.aicore.instructions.prompt_utils import INITIAL_CORE_PROMPT
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
    
    def __init__(self, config: AgentConfig):
        """
        Initialize the instruction builder
        
        Args:
            config: Agent configuration to use for instruction generation
        """
        self.config = config
        
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
        if self.config.core_prompt:
            return self.config.core_prompt
        return INITIAL_CORE_PROMPT
    
    def _get_original_template(self, context: InstructionContext, memory_context: str) -> str:
        """Get the exact template from original prompt_utils.py"""
        
        # This is the EXACT template from prompt_utils.py
        INSTRUCTIONS_TEMPLATE = """    
    Additional capabilities include:
    - Searching user uploaded documents and files for information
    - Executing Python code in a workspace
    - Searching the web for latest and up to date information
    - MUST use web search tool when current or recent information is required
    - If uncertain whether information is current, always search the web first
    
    You have access to the following tools (running on a '{os_type}' host):
    1. A set of tools to create , upload files and execute code in a workspace.
    2. A tool that searches the web for latest and up to date information.
    3. A tool that searches user uploaded documents and files for information.
    
    **CRITICAL: ALWAYS CHECK UPLOADED DOCUMENTS FIRST**
    Before providing any answer, check if the user has uploaded files that might contain the answer.
    Users expect answers from their uploaded documents, not generic knowledge.
    
    ** Do not provide vague answers, always check for relevant information from user uploaded documents, and if required,
    combined with your own knowledge and web search results.

    **KNOWLEDGE SEARCH INSTRUCTIONS:**
    1. **Always search uploaded documents first** before giving generic answers
    2. Use search_user_uploaded_documents with search_all_files=true for most queries
    3. Only use specific file IDs if you have them from message attachments
    4. If no relevant information found in documents, then proceed with other tools
    
    {memory_context}
    """
        
        # Format exactly like the original
        formatted_template = INSTRUCTIONS_TEMPLATE.replace("{os_type}", context.os_type)  
        formatted_template = formatted_template.replace("{message_id}", context.message_id)
        
        try:
            if memory_context and memory_context != "":
                formatted_template = formatted_template.replace("{memory_context}", memory_context)
            else:
                formatted_template = formatted_template.replace("{memory_context}", "")
        except Exception as e:
            logger.error(f"Error replacing memory context: {e}")
            formatted_template = formatted_template.replace("{memory_context}", "")
        
        return formatted_template
    
    def update_config(self, new_config: AgentConfig):
        """Update the agent configuration"""
        self.config = new_config 