#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configurable Code Executor Agent - Uses centralized configuration system
"""

import uuid
from typing import Dict, List, Optional, Any
from agents import Agent, RunContextWrapper, WebSearchTool, function_tool

# Import configuration classes
from app.aicore.config import AgentConfig, ModelConfig
from app.aicore.instructions import InstructionBuilder, InstructionContext
from app.logging.logger import get_logger

# Import HTTP code execution functionality
from app.aicore.code_executor.new_code_tool import execute_code_func, execute_system_command_func, CodeExecutionResult, SystemCommandResult, DEFAULT_TIMEOUT
from app.aicore.code_executor.models.data_models import DownloadedFilesTracker


# Get logger
logger = get_logger(__name__)


class ConfigurableCodeExecutorAgent(Agent):
    """
    A configurable Agent subclass for executing code with centralized configuration.
    
    This agent uses the centralized configuration system to determine:
    - Model selection and parameters
    - Tool availability and settings
    - Instruction generation
    - Execution behavior
    """
    
    def __init__(
        self, 
        agent_config: AgentConfig,
        model_config: ModelConfig,
        name: Optional[str] = None
    ):
        """
        Initialize the ConfigurableCodeExecutorAgent.
        
        Args:
            agent_config: Agent configuration object
            model_config: Model configuration object
            name: Optional name override for the agent
        """
        self.agent_config = agent_config
        self.model_config = model_config
        
        # Set agent name
        agent_name = name or agent_config.name
        
        # Initialize instruction builder
        self.instruction_builder = InstructionBuilder(agent_config)
        
        # Current message ID for the agent
        self.current_message_id = str(uuid.uuid4())[:8]
        
        # Determine if we should download files from configuration
        self.should_download_files = agent_config.should_download_files
        
        # Track downloaded files with metadata from HTTP executions by message ID
        self.file_tracker = DownloadedFilesTracker()
        
        # Build tools based on configuration
        self.tools = self._build_tools()
        
        # Get model name from configuration
        model_name = model_config.get_full_model_name()
        
        # Initialize the parent Agent class
        super().__init__(
            name=agent_name,
            instructions=self._sdk_instructions_wrapper,
            tools=self.tools,
            model=model_name,
            # tool_use_behavior=agent_config.tool_use_strategy.value,
            # reset_tool_choice=agent_config.reset_tool_choice,
            # output_type=agent_config.output_type if agent_config.output_type != "str" else None
        )
        
        logger.info(f"ConfigurableCodeExecutorAgent '{agent_name}' initialized with model '{model_name}'")
    
    def _build_tools(self) -> List:
        """Build tools list based on agent configuration"""
        tools = []
        
        # Add code execution tools if enabled (use wrapped tools with file tracking)
        if self.agent_config.code_execution.enabled:
            execute_code_wrapper = self._create_execute_code_wrapper()
            tools.append(execute_code_wrapper)
            
            if self.agent_config.code_execution.system_commands_enabled:
                execute_system_command_wrapper = self._create_execute_system_command_wrapper()
                tools.append(execute_system_command_wrapper)
        
        # Add web search tool if enabled
        if self.agent_config.web_search.enabled:
            websearch_tool = WebSearchTool(
                user_location=self.agent_config.web_search.location
            )
            tools.append(websearch_tool)
        
        # Add any custom tools specified in configuration
        from app.aicore.tools.tool_registry import get_tool_registry
        
        tool_registry = get_tool_registry()
        for tool_name in self.agent_config.custom_tools:
            # Extract tool name and parameters
            if isinstance(tool_name, str):
                name = tool_name
                params = {}
            elif isinstance(tool_name, dict):
                name = tool_name.get('name')
                params = tool_name.get('params', {})
            else:
                logger.warning(f"Invalid tool configuration: {tool_name}")
                continue
            
            # Get tool from registry
            tool = tool_registry.get_tool(name, **params)
            if tool:
                tools.append(tool)
                logger.info(f"Added custom tool: {name}")
            else:
                logger.warning(f"Custom tool '{name}' not found in registry")
        
        logger.debug(f"Built {len(tools)} tools for agent")
        logger.debug(f"Tool names: {[getattr(tool, 'name', str(tool)) for tool in tools]}")
        return tools
    
    def _create_execute_code_wrapper(self):
        """Create a wrapper function for execute_code that captures downloaded files with metadata."""
        
        # Capture reference to self for the closure
        _agent = self
        _download_files = _agent.should_download_files
        
        @function_tool(strict_mode=False)
        async def execute_code_with_tracking(
            code: str, 
            files: Optional[List[tuple]] = None, 
            timeout: int = DEFAULT_TIMEOUT,  # Agent explicitly enables file downloading for tracking
            *args: Any, 
            **kwargs: Any
        ) -> CodeExecutionResult:
            """
            Execute Python code via secure HTTP FastAPI server with automatic file tracking.
            
            This tool automatically captures any downloaded files and adds them to the
            agent's tracking system using the current message ID, preserving full metadata
            including download URLs.
            
            Args:
                code: Python code to execute
                files: Optional list of (filename, content) tuples to upload
                timeout: Execution timeout in seconds
                download_files: Whether to download generated files (default: True for agent tracking)
                *args: Additional args passed to execute_code
                **kwargs: Additional kwargs passed to execute_code
                
            Returns:
                CodeExecutionResult with execution results and downloaded files
            """
            logger.info(f"Agent executing code with auto file tracking (message: {_agent.current_message_id})")
            logger.info(f"Download mode: {'ENABLED' if _download_files else 'DISABLED'} (URLs only)")
            
            # Call the original execute_code tool from new_code_tool with explicit download_files=True
            result = await execute_code_func(code, files, timeout, _download_files, *args, **kwargs)
            
            # Handle file tracking based on what we got back
            if result.downloaded_files:
                # Files were downloaded with content
                _agent.file_tracker.add_message_files(_agent.current_message_id, result.downloaded_files)
                logger.info(f"Auto-captured {len(result.downloaded_files)} files with content for message {_agent.current_message_id}")
            elif result.output_files:
                # Files exist but weren't downloaded (URLs only)
                _agent.file_tracker.add_output_files(_agent.current_message_id, result.output_files)
                logger.info(f"Auto-captured {len(result.output_files)} files (URLs only) for message {_agent.current_message_id}")
            else:
                logger.info(f"No files generated for message {_agent.current_message_id}")
            
            return result
        
        return execute_code_with_tracking
    
    def _create_execute_system_command_wrapper(self):
        """Create a wrapper function for execute_system_command for consistency."""
        
        @function_tool(strict_mode=False)
        async def execute_system_command_with_tracking(
            command: str, 
            allowed_prefixes: Optional[List[str]] = None
        ) -> SystemCommandResult:
            """
            Execute system command via secure HTTP FastAPI server.
            
            Args:
                command: System command to execute
                allowed_prefixes: List of allowed command prefixes for security
                
            Returns:
                SystemCommandResult with command execution results
            """
            logger.info(f"Agent executing system command: {command}")
            
            # Call the original execute_system_command tool from new_code_tool
            result = await execute_system_command_func(command, allowed_prefixes)
            
            # System commands don't generate downloadable files, but log for completeness
            logger.info(f"System command completed with status: {result.status}")
            
            return result
        
        return execute_system_command_with_tracking
    
    async def _get_dynamic_instructions(self) -> str:
        """
        Dynamically generate instructions with the current message ID and configuration.
            
        Returns:
            str: Instructions with the message ID and configuration injected
        """
        # Create instruction context using only agent config and instance data
        # Ignore run_context since it will be removed from SDK soon
        context = InstructionContext(
            message_id=self.current_message_id,
            os_type=getattr(self.agent_config, 'os_type', 'Windows'),
            user_id=self.agent_config.user_id,
            session_id=None,  # Not needed for now
        )   
        
        # Generate instructions using the instruction builder
        return await self.instruction_builder.build_instructions(context)
    
    async def _sdk_instructions_wrapper(self, run_context: RunContextWrapper, agent: Agent) -> str:
        """
        SDK-compatible wrapper that ignores parameters and calls our simplified method
        
        Args:
            run_context: Ignored (SDK requirement)
            agent: Ignored (SDK requirement)
            
        Returns:
            str: Instructions from _get_dynamic_instructions
        """
        return await self._get_dynamic_instructions()
    
    def set_message_id(self, message_id: Optional[str] = None) -> str:
        """
        Set the message ID for the next execution.
        
        Args:
            message_id: Custom message ID to use, or None to generate a new one
            
        Returns:
            str: The message ID that was set
        """
        if message_id is None:
            # Generate a new message ID if none provided
            message_id = str(uuid.uuid4())[:8]
        
        self.current_message_id = message_id
        logger.debug(f"Set message ID to: {message_id}")
        return message_id
    
    def get_current_message_id(self) -> str:
        """
        Get the current message ID.
        
        Returns:
            str: The current message ID
        """
        return self.current_message_id
    
    def get_all_plots_with_message_id(self) -> Dict[str, List[str]]:
        """
        Extract all message IDs from downloaded files along with plot filenames.
        Returns a dictionary mapping each message ID to a list of its associated plot filenames.
        
        Returns:
            Dict mapping message_id -> list of plot filenames
        """
        return self.file_tracker.get_plots_by_message()
    
    def get_downloaded_files_for_message(self, message_id: str) -> Dict[str, bytes]:
        """
        Get all downloaded file contents for a specific message.
        Only returns files that have actual content (excludes URL-only files).
        
        Args:
            message_id: The message ID to get files for
            
        Returns:
            Dictionary mapping filename -> file content (bytes)
        """
        return self.file_tracker.get_file_contents_for_message(message_id)
    
    def get_file_metadata_for_message(self, message_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all file metadata for a specific message.
        Includes both downloaded and URL-only files.
        
        Args:
            message_id: The message ID to get files for
            
        Returns:
            Dictionary mapping filename -> file metadata dict
        """
        return self.file_tracker.get_file_metadata_for_message(message_id)
    
    def get_download_urls_for_message(self, message_id: str) -> Dict[str, str]:
        """
        Get download URLs for all files in a specific message.
        
        Args:
            message_id: The message ID to get URLs for
            
        Returns:
            Dictionary mapping filename -> download URL
        """
        return self.file_tracker.get_download_urls_for_message(message_id)
    
    def get_all_downloaded_files(self) -> Dict[str, Dict[str, bytes]]:
        """
        Get all downloaded file contents across all messages.
        Only returns files that have actual content (excludes URL-only files).
        
        Returns:
            Dictionary mapping message_id -> {filename -> file content}
        """
        return self.file_tracker.get_all_file_contents()
        
    def has_files_with_content(self, message_id: str = None) -> bool:
        """
        Check if files have actual content (not just URLs).
        
        Args:
            message_id: Check specific message, or None to check all messages
            
        Returns:
            True if there are files with content, False otherwise
        """
        return self.file_tracker.has_files_with_content(message_id)
    
    def get_file_counts(self, message_id: str = None) -> Dict[str, int]:
        """
        Get counts of files with content vs URL-only files.
        
        Args:
            message_id: Check specific message, or None for all messages
            
        Returns:
            Dict with 'with_content' and 'url_only' counts
        """
        return self.file_tracker.get_file_counts(message_id)
    
    def clear_downloaded_files(self, message_id: str = None):
        """
        Clear downloaded files for a specific message or all messages.
        
        Args:
            message_id: Specific message ID to clear, or None to clear all
        """
        self.file_tracker.clear_message(message_id)
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about downloaded files.
        
        Returns:
            Dictionary with statistics
        """
        return self.file_tracker.get_overall_stats()
    
    def update_configuration(self, agent_config: Optional[AgentConfig] = None, model_config: Optional[ModelConfig] = None):
        """
        Update the agent configuration at runtime
        
        Args:
            agent_config: New agent configuration (optional)
            model_config: New model configuration (optional)
        """
        if agent_config:
            self.agent_config = agent_config
            # Update instruction builder with new config
            self.instruction_builder.update_config(agent_config)
            # Rebuild tools if needed
            new_tools = self._build_tools()
            self.tools = new_tools
            logger.info("Agent configuration updated")
        
        if model_config:
            self.model_config = model_config
            # Note: Changing the model at runtime would require re-initializing the Agent
            # This is a limitation of the current SDK structure
            logger.info("Model configuration updated (requires agent restart to take effect)")
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration"""
        return {
            "agent_name": self.name,
            "model_name": self.model_config.name,
            "current_message_id": self.current_message_id,
            "tools_enabled": self.agent_config.get_enabled_tools(),
            "code_execution_enabled": self.agent_config.code_execution.enabled,
            "web_search_enabled": self.agent_config.web_search.enabled,
            "tool_use_strategy": self.agent_config.tool_use_strategy.value,
            "should_download_files": self.should_download_files,
            "file_tracking_stats": self.file_tracker.get_overall_stats(),
        } 