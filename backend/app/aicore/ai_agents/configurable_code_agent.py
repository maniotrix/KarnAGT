#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configurable Code Executor Agent - Uses centralized configuration system with workspace session management
"""

import uuid
from typing import Dict, List, Optional, Any
from agents import Agent, RunContextWrapper, WebSearchTool, function_tool, ModelSettings
from openai.types.shared import Reasoning, ReasoningEffort

# Import configuration classes
from app.aicore.config import AgentConfig, ModelConfig
from app.aicore.instructions import InstructionBuilder, InstructionContext
from app.logging.logger import get_logger

# Import auto workspace session functionality (replaces deprecated workspace session tools)
from app.aicore.code_executor.models import ExecutionOperationResult, FileInfo
from app.aicore.ai_agents.agent_models import DownloadedFilesTracker
from app.aicore.code_executor.auto_workspace_session import create_auto_workspace_tools


# Get logger
logger = get_logger(__name__)


class ConfigurableCodeExecutorAgent(Agent):
    """
    A configurable Agent subclass for executing code with centralized configuration and workspace session management.
    
    This agent uses the centralized configuration system to determine:
    - Model selection and parameters
    - Tool availability and settings
    - Instruction generation
    - Execution behavior
    
    Code execution is handled through workspace session tools that provide:
    - Automatic workspace creation and cleanup (via context manager at higher level)
    - File tracking and download URL generation
    - Isolated execution environments
    - Persistent state across multiple code executions within the same workspace
    
    The agent automatically tracks generated files from code execution and makes them
    available through the file tracker for downstream processing.
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
        
        # Track downloaded files with metadata from HTTP executions by message ID
        self.file_tracker = DownloadedFilesTracker()
        
        # Build tools based on configuration
        self.tools = self._build_tools()
        
        # Get model name from configuration
        model_name = model_config.get_full_model_name()
        
        # Create model settings with reasoning configuration
        # This includes verbosity="low" by default to minimize reasoning overhead
        # for o1 and other reasoning models while still benefiting from their capabilities
        model_settings = ModelSettings(
            verbosity="low",
            reasoning=Reasoning(effort="low"),
        )
        
        # Initialize the parent Agent class
        super().__init__(
            name=agent_name,
            instructions=self._sdk_instructions_wrapper,
            tools=self.tools,
            model=model_name,
            model_settings=model_settings,
            # tool_use_behavior=agent_config.tool_use_strategy.value,
            # reset_tool_choice=agent_config.reset_tool_choice,
            # output_type=agent_config.output_type if agent_config.output_type != "str" else None
        )
        
        logger.info(f"ConfigurableCodeExecutorAgent '{agent_name}' initialized with model '{model_name}'")
    
    def _build_tools(self) -> List:
        """Build tools list based on agent configuration"""
        tools = []
        
        # Add workspace session tools if enabled (with automatic file tracking)
        if self.agent_config.code_execution.enabled:
            # Get workspace session tools with contextvars support
            session_tools = create_auto_workspace_tools()
            
            # Wrap tools with file tracking for the agent
            wrapped_tools = self._wrap_session_tools_with_tracking(session_tools)
            tools.extend(wrapped_tools)
            
            logger.info(f"Added {len(wrapped_tools)} workspace session tools with file tracking")
        
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
    
    def _wrap_session_tools_with_tracking(self, session_tools: List) -> List:
        """
        Wrap workspace session tools with file tracking functionality.
        
        This maintains the same file tracking behavior as the deprecated new_code_tool
        approach, but works with the new workspace session tools.
        
        Args:
            session_tools: List of auto workspace tools from create_auto_workspace_tools()
            
        Returns:
            List of wrapped tools with file tracking
        """
        wrapped_tools = []
        
        for tool in session_tools:
            tool_name = getattr(tool, 'name', str(tool))
            
            # Only wrap execute_code tool for file tracking
            if tool_name == 'execute_code':
                wrapped_tool = self._create_execute_code_session_wrapper(tool)
                wrapped_tools.append(wrapped_tool)
                logger.debug(f"Wrapped {tool_name} with file tracking")
            else:
                # Other tools (create_workspace, upload_file) don't need file tracking
                wrapped_tools.append(tool)
                logger.debug(f"Added {tool_name} without wrapping")
        
        return wrapped_tools
    
    def _create_execute_code_session_wrapper(self, original_execute_code):
        """
        Create a wrapper for the workspace session execute_code tool that captures files.
        
        This replaces the deprecated _create_execute_code_wrapper method and works
        with ExecutionOperationResult instead of CodeExecutionResult.
        """
        
        # Get the raw callable function from the workspace tools registry
        from app.aicore.code_executor.auto_workspace_session import get_auto_workspace_callables
        workspace_callables = get_auto_workspace_callables()
        execute_code_func = workspace_callables['execute_code']
        
        # Capture reference to self for the closure
        _agent = self
        
        @function_tool(
            name_override="execute_code",
            description_override=getattr(original_execute_code, 'description', None),
            strict_mode=getattr(original_execute_code, 'strict_mode', False)
        )
        async def execute_code_with_tracking(
            code: str
        ) -> ExecutionOperationResult:
            """
            Execute Python code in workspace with automatic file tracking.
            
            This tool automatically captures any generated files and adds them to the
            agent's tracking system using the current message ID.
            
            Args:
                code: Python code to execute
                
            Returns:
                ExecutionOperationResult with execution results and file tracking
            """
            logger.info(f"Agent executing code with auto file tracking (message: {_agent.current_message_id})")
            
            # Call the underlying function directly (uses context variables internally)
            try:
                result: ExecutionOperationResult = await execute_code_func(code)
            except Exception as e:
                logger.error(f"Error executing code: {e}")
                return ExecutionOperationResult.error_result(str(e))
            
            # Handle file tracking based on what we got back
            if result.success and result.execution_result and result.execution_result.generated_files:
                # Convert FileInfo objects to the format expected by file_tracker
                output_files : list[dict[str, Any]] = []
                for file_info in result.execution_result.generated_files:
                    if isinstance(file_info, FileInfo):
                        output_files.append({
                            "name": file_info.filename,
                            "download_url": file_info.download_url or "",
                            "size": file_info.size,
                            "mime_type": file_info.mime_type,
                            "created_at": ""  # FileInfo doesn't have created_at, use empty string
                        })
                
                if output_files:
                    _agent.file_tracker.add_output_files(_agent.current_message_id, output_files)
                    logger.info(f"Auto-captured {len(output_files)} files for message {_agent.current_message_id}")
            else:
                logger.info(f"No files generated for message {_agent.current_message_id}")
            
            return result
        
        return execute_code_with_tracking
    

    
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
            "file_tracking_stats": self.file_tracker.get_overall_stats(),
        } 