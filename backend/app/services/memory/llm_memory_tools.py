#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
LLM Memory Tools - Functions for AI agents to interact with user memory system
"""

from typing import Dict, List, Optional, Any
from agents import function_tool
from app.services.memory.memory_service import MemoryService
from app.logging.logger import get_logger

logger = get_logger(__name__)

# ANSI color codes for memory tool logs
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    END = '\033[0m'
    BOLD = '\033[1m'
    
class MemoryToolNames:
    MEMORY_RETRIEVAL = "retrieve_user_memory"
    MEMORY_UPDATE = "save_user_memory"
    
class MemoryToolsInfo():
    """
    Information about the memory tools configuration
    """
    TOOL_TYPE: str = "memory_tools"
    TOOL_NAMES: List[str] = [MemoryToolNames.MEMORY_RETRIEVAL, MemoryToolNames.MEMORY_UPDATE]

def memory_log(level, message, tool_name=None):
    """Helper to log memory tool messages with color coding"""
    tool_prefix = f"[{tool_name}]" if tool_name else ""
    colored_prefix = f"{Colors.CYAN}[MEMORY-TOOLS]{tool_prefix}{Colors.END}"
    if level == "info":
        logger.info(f"{colored_prefix} {message}")
    elif level == "error":
        logger.error(f"{colored_prefix} {Colors.RED}{message}{Colors.END}")
    elif level == "success":
        logger.info(f"{colored_prefix} {Colors.GREEN}{message}{Colors.END}")


async def get_essential_user_context(
    memory_service: MemoryService, 
    user_id: int
) -> str:
    """
    Get essential user memories formatted as a string for system prompt context.
    
    Args:
        memory_service: The memory service instance
        user_id: User ID to get memories for
        
    Returns:
        Formatted string with essential user context
    """
    try:
        memory_log("info", f"Getting essential context for user {user_id}", "ESSENTIAL")
        
        context_parts = []
        
        # Get top memories from key buckets (only high importance)
        key_buckets = ["identity", "preferences", "goals"]
        
        for bucket in key_buckets:
            memories = await memory_service.get_memories_by_bucket(
                user_id=user_id,
                bucket=bucket,
                limit=5
            )
            
            # Filter high importance memories (fix SQLAlchemy comparison)
            important_memories = []
            for mem in memories:
                # Convert to float for comparison to avoid SQLAlchemy type issues
                if float(mem.importance) >= 0.7:
                    important_memories.append(mem.content)
            
            if important_memories:
                bucket_name = bucket.upper().replace("_", " ")
                context_parts.append(f"{bucket_name}: {' | '.join(important_memories[:3])}")
        
        # Format final context with clear scope and guidance
        if context_parts:
            header = (
                "\n## BASIC USER PROFILE DATA (selected)\n"
                "- The following are key user details from the full user memory and profile data.\n"
                "- This is only basic profile information, not full user memory or details.\n\n"
                "<user_profile_data>\n"
            )
            body = "\n".join(context_parts)
            footer = (
                "\n</user_profile_data>\n\n"
                "Note: To access more data or info about user or its profile, use relevant memory tool to retrieve more user data.\n"
            )
            
            formatted_context = f"{header}{body}{footer}"
            memory_log("success", f"Generated essential context with {len(context_parts)} sections", "ESSENTIAL")
            return formatted_context
        else:
            memory_log("info", "No essential context found for user", "ESSENTIAL")
            return ""
            
    except Exception as e:
        memory_log("error", f"Error getting essential user context: {e}", "ESSENTIAL")
        return ""


def create_memory_retrieval_tool(memory_service: MemoryService, user_id: int):
    """
    Create a configured memory retrieval tool for a specific user.
    
    Args:
        memory_service: Memory service instance
        user_id: User ID for memory retrieval
        
    Returns:
        Configured function tool ready for agent use
    """
    
    @function_tool(
        name_override=MemoryToolNames.MEMORY_RETRIEVAL,
        description_override="""
        Get ALL user memories to understand their background, preferences, and context.
        
        HOW IT WORKS:
        - Returns ALL user memories from their entire history
        - You get a numbered list of [BUCKET] memory content
        - YOU decide which memories are relevant to your query
        - Use this whenever you need to know something about the user
        
        WHEN TO USE:
        - User asks about preferences, goals, or background
        - You need context about their skills, tools, or workflow  
        - Before making recommendations or suggestions
        - When personalizing your response
        
        WHAT YOU GET BACK:
        A complete list like:
        1. [IDENTITY] John, software engineer, Pacific timezone
        2. [PREFERENCES] Prefers concise explanations with code examples
        3. [GOALS] Learning React for project deadline next month
        """,
        strict_mode=True
    )
    async def user_memory_retrieval_tool(
        query: str
    ) -> str:
        """
        Search user memories for relevant information.
        
        Args:
            query: What you want to know about the user
            
        Returns:
            Formatted string with all user memories for LLM to filter
        """
        try:
            memory_log("info", f"Memory retrieval query for user {user_id}: '{query}'", "RETRIEVAL")
            
            # Get ALL user memories (let LLM decide what's relevant)
            all_memories = await memory_service.get_all_user_memories(
                user_id=user_id,
                include_archived=False
            )
            
            if not all_memories:
                memory_log("info", f"No memories found for user {user_id}", "RETRIEVAL")
                return "No user memories found."
            
            # Format all memories for LLM to choose from
            memory_list = []
            for i, memory in enumerate(all_memories, 1):
                memory_list.append(f"{i}. [{memory.bucket.upper()}] {memory.content}")
            
            # Return formatted list - LLM will determine relevance
            result = f"User memories (showing {len(all_memories)} total memories):\n\n"
            result += "\n".join(memory_list)
            
            memory_log("success", f"Retrieved {len(all_memories)} memories for LLM to filter", "RETRIEVAL")
            return result
            
        except Exception as e:
            memory_log("error", f"Error retrieving user memories: {e}", "RETRIEVAL")
            return f"Error retrieving memories: {str(e)}"
    
    return user_memory_retrieval_tool


def create_memory_update_tool(memory_service: MemoryService, user_id: int, conversation_id: str):
    """
    Create a tool for the agent to save new user memories.
    
    Args:
        memory_service: Memory service instance
        user_id: User ID for memory storage
        conversation_id: Current conversation ID
        
    Returns:
        Configured function tool ready for agent use
    """
    
    @function_tool(
        name_override=MemoryToolNames.MEMORY_UPDATE,
        description_override="""
        Save important information about the user for future conversations.
        
        REQUIRED PARAMETERS (always provide these 3):
        - content: The exact information to remember (be specific and clear)
        - bucket: Category name (see buckets below, or create your own)
        - importance: 0.0-1.0 score (0.8-1.0 = critical, 0.6-0.7 = important, 0.3-0.5 = useful)
        
        STANDARD BUCKETS:
        - identity: name, role, location, personal info
        - preferences: communication style, tools, formats they like
        - goals: current projects, learning objectives, targets
        - workflows: habits, routines, processes they follow  
        - capabilities: skills, experience, hardware, constraints
        - social: team members, colleagues, relationships
        
        CUSTOM BUCKETS:
        - You can create ANY bucket name (gaming, cooking, health, etc.)
        - New buckets are automatically created if they don't exist
        - Use descriptive names like "fitness_goals" or "coding_style"
        
        WHEN TO SAVE:
        - User shares personal details, preferences, or background
        - They mention goals, projects, or what they're working on
        - They state likes/dislikes about tools, formats, or communication
        - Any detail that would help future conversations be more personalized
        
        IMPORTANCE GUIDE:
        - 0.9-1.0: Core identity (name, role, critical preferences)
        - 0.7-0.8: Important preferences, active goals
        - 0.5-0.6: Useful context, secondary preferences  
        - 0.3-0.4: Minor details, temporary info
        """,
        strict_mode=True
    )
    async def memory_update_tool(
        content: str,
        bucket: str,
        importance: float,
        confidence: float = 0.8
    ) -> str:
        """
        Save new user memory.
        
        Args:
            content: The EXACT information to remember (be specific, e.g. "Prefers Python over JavaScript for backend development")
            bucket: Category name - use standard buckets (identity, preferences, goals, workflows, capabilities, social) or create custom ones (gaming, cooking, fitness_goals, etc.)
            importance: Importance score 0.0-1.0 (REQUIRED: 0.9-1.0=critical, 0.7-0.8=important, 0.5-0.6=useful, 0.3-0.4=minor)
            confidence: How confident you are in this info (0.0-1.0, default: 0.8)
            
        Returns:
            Confirmation message with bucket and importance
        """
        try:
            memory_log("info", f"Saving memory for user {user_id} in bucket '{bucket}': {content[:50]}...", "UPDATE")
            
            memory = await memory_service.store_memory(
                user_id=user_id,
                bucket=bucket,
                content=content,
                importance=importance,
                confidence=confidence,
                source_conversation_id=conversation_id
            )
            
            memory_log("success", f"Saved memory for user {user_id}: {content[:50]}...", "UPDATE")
            return f"Memory saved to {bucket} bucket: '{content[:50]}...' (importance: {importance:.2f})"
            
        except Exception as e:
            memory_log("error", f"Error saving memory: {e}", "UPDATE")
            return f"Failed to save memory: {str(e)}"
    
    return memory_update_tool
