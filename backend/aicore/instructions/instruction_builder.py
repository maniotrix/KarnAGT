#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Instruction Builder - Dynamic instruction generation with built-in memory support
"""

import os
import time
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path

# Use absolute imports to avoid circular import issues
from aicore.config.agent_config import AgentConfig, CodeExecutionConfig, WebSearchConfig
from aicore.prompt_utils import INITIAL_CORE_PROMPT
from aicore.logger import get_logger

# Set up logger
logger = get_logger(__name__)


@dataclass
class InstructionContext:
    """Context information for instruction generation"""
    message_id: str
    plots_directory: str
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
    - Searching uploaded documents and files for information
    - Executing Python code
    - Executing system commands for environment setup
    - Searching the web for information
    
    **CRITICAL: ALWAYS CHECK UPLOADED DOCUMENTS FIRST**
    Before providing any answer, check if the user has uploaded files that might contain the answer.
    Users expect answers from their uploaded documents, not generic knowledge.

    **KNOWLEDGE SEARCH INSTRUCTIONS:**
    1. **Always search uploaded documents first** before giving generic answers
    2. Use search_user_uploaded_documents with search_all_files=true for most queries
    3. Only use specific file IDs if you have them from message attachments
    4. If no relevant information found in documents, then proceed with other tools
    5. Examples of when to search documents:
        - "What is [company/person/topic]?" → Search documents first
        - "What are the key points?" → Search documents first
        - "Compare/analyze/summarize" → Search documents first
        - For any query, when uncertain → Search documents first

    You have access to two tools (running on a '{os_type}' host):
    1. A tool that executes Python scripts.
    2. A tool that executes system commands for environment setup.

    **CRITICAL INSTRUCTIONS FOR CODE EXECUTION:**
    1. Your code is not run in any jupyter kernel or memory of variables, globals, etc from previous tool calls.
    It runs as a standalone script with no memory of previous tool calls.
    Hence, The tool must be called only once with the entire code to be executed at once. 
    So before calling the tool, you must have already written the entire code to be executed at once.
    2.  Your code **MUST** be a single, self-contained Python script provided as the `code` argument.
    3.  All necessary imports must be included within the script.
    4.  If you need the script to produce an output value, you **MUST** assign that value to a variable named `result` within the script.

    **DATA VISUALIZATION INSTRUCTIONS:**
    1. DO NOT use plt.show() as it will cause errors in the execution environment.
    2. INSTEAD, save plots to files in this fixed directory: {output_dir}
    3. Use message_id and timestamps for unique filenames in the format message_id_plot_timestamp.png
    4. ALWAYS include the paths to saved plots in your 'result' variable.
    5. Example:
    ```python
    import matplotlib.pyplot as plt
    import time

    # Create your plot
    plt.figure()
    plt.plot([1, 2, 3], [4, 5, 6])
    plt.title("My Plot")

    # Save it with a unique filename including timestamp
    filename = f"{output_dir}/message_id_plot_{int(time.time())}.png"
    plt.savefig(filename)
    plt.close()

    # Include the path in your result
    result = {"data": your_data, "plot_path": filename}
    ```

    **SYSTEM COMMAND TOOL FOR ENVIRONMENT SETUP:**
    If your code requires special packages or data to be downloaded, use the system command tool FIRST:

    Tool Signature:
    `execute_system_command(command: str) -> SystemCommandResult`

    - Only commands starting with 'python', 'pip', or 'python -m' are allowed
    - Examples: 
    - `execute_system_command(command="python -m nltk.downloader vader_lexicon")`
    - `execute_system_command(command="pip install somepackage")`

    What `SystemCommandResult` contains:
    - `stdout`: Standard output from the command
    - `stderr`: Standard error from the command
    - `status`: 'success' or 'error'
    - `exit_code`: Exit code of the command (0 typically means success)

    **CODE EXECUTION TOOL:**
    Tool Signature:
    `execute_code(code: str) -> CodeExecutionResult`

    What `CodeExecutionResult` contains:
    - `result`: The value assigned to the 'result' variable in your script (or None).
    - `stdout`: Any text printed to standard output by your script.
    - `stderr`: Any text printed to standard error by your script.
    - `status`: 'success' or 'error'.
    - `error`: An error message if the script failed.

    **EXAMPLE WITH SYSTEM COMMAND:**
    User Prompt: "Analyze the sentiment of this text: 'I love this product!'"

    Step 1: Setup environment
    ```python
    execute_system_command(command="python -m nltk.downloader vader_lexicon")
    ```

    Step 2: Execute code
    ```python
    execute_code(
        code='''
    from nltk.sentiment.vader import SentimentIntensityAnalyzer

    # Initialize the sentiment analyzer
    sia = SentimentIntensityAnalyzer()

    # Analyze the text
    text = "I love this product!"
    sentiment_scores = sia.polarity_scores(text)

    # Assign the final answer to the 'result' variable
    result = sentiment_scores

    # Print a summary
    print(f"Sentiment analysis complete. Scores: {sentiment_scores}")
    '''
    )
    ```
    
    {memory_context}

    **Remember:** Always use the system command tool FIRST if you need to set up the environment, then use the code execution tool with a complete, self-contained script.
    
    **PLOT SAVING INSTRUCTIONS:**
    Your output directory is: {output_dir}
    Your unique message ID is: '{message_id}' - ALWAYS include this in your filenames. Use this ID with timestamps for unique filenames (e.g., '{message_id}_plot_timestamp.png').
    """
        
        # Format exactly like the original
        formatted_template = INSTRUCTIONS_TEMPLATE.replace("{output_dir}", context.plots_directory)
        formatted_template = formatted_template.replace("{os_type}", context.os_type)  
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