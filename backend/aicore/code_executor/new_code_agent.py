import os
import uuid
from typing import Dict, List
from agents import Agent, RunContextWrapper, WebSearchTool
from aicore.code_executor.new_code_tool import execute_code, execute_system_command
from aicore.code_executor.logger import get_logger
from aicore.prompt_utils import get_instructions_template, INITIAL_CORE_PROMPT

# Get logger
logger = get_logger()

class HTTPCodeExecutorAgent(Agent):
    """
    HTTP-based Code Executor Agent for FastAPI server execution.
    
    This agent uses HTTP-based code execution with automatic file downloading.
    No local file management - all files are handled via HTTP API calls.
    """
    
    def __init__(self, name: str, core_prompt: str = INITIAL_CORE_PROMPT, model: str = "gpt-4o-mini-2024-07-18"):
        """
        Initialize the HTTP Code Executor Agent.
        
        Args:
            name: The name of the agent
            core_prompt: Core prompt for the agent
            model: Model to use for the agent
        """
        self.core_prompt = core_prompt
        
        # Track downloaded files from HTTP executions by message ID
        self.downloaded_files_by_message: Dict[str, Dict[str, bytes]] = {}
        
        # Current message ID for the agent
        self.current_message_id = str(uuid.uuid4())[:8]
        
        # Get instructions template for HTTP-based execution
        self.instructions_template = get_instructions_template("outputs", core_prompt=self.core_prompt)
        
        # Initialize web search tool
        websearch_tool = WebSearchTool(user_location={"type": "approximate", "city": "New Delhi"})
        
        # Initialize the parent Agent class with HTTP-based tools
        super().__init__(
            name=name,
            instructions=self._get_dynamic_instructions,
            tools=[execute_code, execute_system_command, websearch_tool],
            model=model
        )
    
    def _get_dynamic_instructions(self, run_context: RunContextWrapper, agent: Agent) -> str:
        """
        Dynamically generate instructions with the current message ID.
        
        Args:
            run_context: The current run context
            agent: The agent instance
            
        Returns:
            str: Instructions with the message ID injected
        """
        return self.instructions_template.replace("{message_id}", self.current_message_id)
    
    def set_message_id(self, message_id=None):
        """
        Set the message ID for the next execution.
        
        Args:
            message_id: Custom message ID to use, or None to generate a new one
            
        Returns:
            str: The message ID that was set
        """
        if message_id is None:
            message_id = str(uuid.uuid4())[:8]
        
        self.current_message_id = message_id
        logger.info(f"Set message ID: {message_id}")
        return message_id
        
    def add_downloaded_files(self, message_id: str, downloaded_files: Dict[str, bytes]):
        """
        Add downloaded files from HTTP execution results.
        
        Args:
            message_id: Message ID associated with the files
            downloaded_files: Dictionary mapping filename -> file content (bytes)
        """
        if message_id not in self.downloaded_files_by_message:
            self.downloaded_files_by_message[message_id] = {}
        
        self.downloaded_files_by_message[message_id].update(downloaded_files)
        logger.info(f"Added {len(downloaded_files)} downloaded files for message {message_id}")
        
    def get_all_plots_with_message_id(self) -> Dict[str, List[str]]:
        """
        Extract all message IDs from downloaded files along with plot filenames.
        Returns a dictionary mapping each message ID to a list of its associated plot filenames.
        
        Returns:
            Dict mapping message_id -> list of plot filenames
        """
        data: Dict[str, List[str]] = {}
        
        for message_id, files in self.downloaded_files_by_message.items():
            # Filter for image/plot files
            plot_files = [filename for filename in files.keys() 
                         if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.svg', '.pdf', '.gif'))]
            if plot_files:
                data[message_id] = sorted(plot_files)
                
        logger.info(f"Found plots for {len(data)} messages")
        return data
    
    def get_downloaded_files_for_message(self, message_id: str) -> Dict[str, bytes]:
        """
        Get all downloaded files for a specific message.
        
        Args:
            message_id: The message ID to get files for
            
        Returns:
            Dictionary mapping filename -> file content (bytes)
        """
        return self.downloaded_files_by_message.get(message_id, {})
    
    def get_all_downloaded_files(self) -> Dict[str, Dict[str, bytes]]:
        """
        Get all downloaded files across all messages.
        
        Returns:
            Dictionary mapping message_id -> {filename -> file content}
        """
        return self.downloaded_files_by_message.copy()
        
    def get_current_message_id(self) -> str:
        """
        Get the current message ID.
        
        Returns:
            str: The current message ID
        """
        return self.current_message_id
    
    def clear_downloaded_files(self, message_id: str = None):
        """
        Clear downloaded files for a specific message or all messages.
        
        Args:
            message_id: Specific message ID to clear, or None to clear all
        """
        if message_id is None:
            self.downloaded_files_by_message.clear()
            logger.info("Cleared all downloaded files")
        elif message_id in self.downloaded_files_by_message:
            del self.downloaded_files_by_message[message_id]
            logger.info(f"Cleared downloaded files for message {message_id}")
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about downloaded files.
        
        Returns:
            Dictionary with statistics
        """
        total_files = sum(len(files) for files in self.downloaded_files_by_message.values())
        total_size = sum(
            len(content) for files in self.downloaded_files_by_message.values() 
            for content in files.values()
        )
        
        return {
            "total_messages": len(self.downloaded_files_by_message),
            "total_files": total_files,
            "total_size_bytes": total_size,
            "messages_with_plots": len(self.get_all_plots_with_message_id())
        }
