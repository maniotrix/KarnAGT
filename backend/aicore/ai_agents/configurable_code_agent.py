#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configurable Code Executor Agent - Uses centralized configuration system
"""

import os
import glob
import uuid
from typing import Dict, List, Optional, Any
from agents import Agent, RunContextWrapper, WebSearchTool

# Import configuration classes
from aicore.config import AgentConfig, ModelConfig
from aicore.instructions import InstructionBuilder, InstructionContext
from aicore.code_executor.code_tool import execute_code, execute_system_command
from aicore.code_executor.logger import get_logger

# Get logger
logger = get_logger()


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
        root_plots_dir: str,
        name: Optional[str] = None
    ):
        """
        Initialize the ConfigurableCodeExecutorAgent.
        
        Args:
            agent_config: Agent configuration object
            model_config: Model configuration object
            root_plots_dir: Directory where plots will be saved
            name: Optional name override for the agent
        """
        self.agent_config = agent_config
        self.model_config = model_config
        
        # Set agent name
        agent_name = name or agent_config.name
        
        # Create unique plots directory
        unique_id = str(uuid.uuid4())[:8]
        self.unique_plots_dir = os.path.join(root_plots_dir, unique_id)
        os.makedirs(self.unique_plots_dir, exist_ok=True)
        
        # Verify directory creation
        if not os.path.exists(self.unique_plots_dir):
            raise ValueError(f"Plots directory {self.unique_plots_dir} could not be created")
        else:
            logger.info(f"Plots directory {self.unique_plots_dir} created successfully")
        
        # Initialize instruction builder
        self.instruction_builder = InstructionBuilder(agent_config)
        
        # Current message ID for the agent
        self.current_message_id = str(uuid.uuid4())[:8]
        
        # Build tools based on configuration
        tools = self._build_tools()
        
        # Get model name from configuration
        model_name = model_config.get_full_model_name()
        
        # Initialize the parent Agent class
        super().__init__(
            name=agent_name,
            instructions=self._sdk_instructions_wrapper,
            tools=tools,
            model=model_name,
            # tool_use_behavior=agent_config.tool_use_strategy.value,
            # reset_tool_choice=agent_config.reset_tool_choice,
            # output_type=agent_config.output_type if agent_config.output_type != "str" else None
        )
        
        logger.info(f"ConfigurableCodeExecutorAgent '{agent_name}' initialized with model '{model_name}'")
    
    def _build_tools(self) -> List:
        """Build tools list based on agent configuration"""
        tools = []
        
        # Add code execution tools if enabled
        if self.agent_config.code_execution.enabled:
            tools.append(execute_code)
            
            if self.agent_config.code_execution.system_commands_enabled:
                tools.append(execute_system_command)
        
        # Add web search tool if enabled
        if self.agent_config.web_search.enabled:
            websearch_tool = WebSearchTool(
                user_location=self.agent_config.web_search.location
            )
            tools.append(websearch_tool)
        
        # Add any custom tools specified in configuration
        from aicore.tool_registry import get_tool_registry
        
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
        return tools
    
    def _get_dynamic_instructions(self) -> str:
        """
        Dynamically generate instructions with the current message ID and configuration.
            
        Returns:
            str: Instructions with the message ID and configuration injected
        """
        # Create instruction context using only agent config and instance data
        # Ignore run_context since it will be removed from SDK soon
        context = InstructionContext(
            message_id=self.current_message_id,
            plots_directory=self.unique_plots_dir,
            os_type=getattr(self.agent_config, 'os_type', 'Windows'),
            user_id=self.agent_config.user_id,
            session_id=None,  # Not needed for now
            metadata=None     # Not needed for now
        )
        
        # Generate instructions using the instruction builder
        return self.instruction_builder.build_instructions(context)
    
    def _sdk_instructions_wrapper(self, run_context: RunContextWrapper, agent: Agent) -> str:
        """
        SDK-compatible wrapper that ignores parameters and calls our simplified method
        
        Args:
            run_context: Ignored (SDK requirement)
            agent: Ignored (SDK requirement)
            
        Returns:
            str: Instructions from _get_dynamic_instructions
        """
        return self._get_dynamic_instructions()
    
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
        Extract all message IDs from generated plot filenames along with the plots.
        Returns a dictionary mapping each message ID to a list of its associated plot file paths.
        """
        data: Dict[str, List[str]] = {}
        plots = glob.glob(f"{self.unique_plots_dir}/*_*.png")
        if not plots:
            return {}
            
        # Sort plots by creation time (newest first)
        plots.sort(key=lambda x: os.path.getctime(x), reverse=True)
        
        for plot in plots:
            msg_id = os.path.basename(plot).split('_')[0]
            if msg_id not in data:
                data[msg_id] = []
            data[msg_id].append(plot)
        return data
    
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
            "unique_plots_dir": self.unique_plots_dir,
            "current_message_id": self.current_message_id,
            "tools_enabled": self.agent_config.get_enabled_tools(),
            "code_execution_enabled": self.agent_config.code_execution.enabled,
            "web_search_enabled": self.agent_config.web_search.enabled,
            "tool_use_strategy": self.agent_config.tool_use_strategy.value,
        } 