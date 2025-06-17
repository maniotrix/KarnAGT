#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configurable OpenAI Assistant - Uses centralized configuration system
"""

import os
import asyncio
import glob
from typing import Optional, Dict, Any, Callable

from agents import Runner, RunConfig, ModelSettings, ModelProvider, OpenAIProvider

# Import configuration classes
from aicore.config import AIConfig, ConfigManager, config_manager
from aicore.ai_agents.configurable_code_agent import ConfigurableCodeExecutorAgent
from aicore.code_executor.utils import execution_cleanup
from aicore.logger import get_logger
from aicore.path_config import PLOTS_DIR

# Set up logger
logger = get_logger(__name__)

# Ensure plots directory exists
os.makedirs(PLOTS_DIR, exist_ok=True)


class ConfigurableOpenAIAssistant:
    """
    Configurable OpenAI assistant using centralized configuration system.
    
    This class manages the complete AI assistant workflow with full configurability:
    - Model selection and parameters
    - Agent behavior and tools
    - Runner execution settings
    - Streaming and cancellation
    - Input/output handling
    """
    
    def __init__(
        self,
        config: Optional[AIConfig] = None,
        user_id: Optional[str] = None,
        environment: Optional[str] = None,
        streaming_callback: Optional[Callable[[str], None]] = None,
        config_overrides: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the configurable assistant
        
        Args:
            config: Complete AI configuration (if None, loads from config manager)
            user_id: User ID for user-specific configuration
            environment: Environment name (dev, prod, test)
            streaming_callback: Callback for streaming responses
            config_overrides: Runtime configuration overrides
        """
        logger.info("Initializing ConfigurableOpenAIAssistant")
        
        # Load configuration if not provided
        if config is None:
            config = config_manager.load_config(
                config_name="default",
                environment=environment,
                user_id=user_id,
                overrides=config_overrides
            )
        
        # Set user_id in agent config for instruction building
        if user_id and not config.agent.user_id:
            config.agent.user_id = user_id
        
        self.config = config
        self.user_id = user_id
        self.environment = environment
        
        # Validate configuration
        validation_errors = config_manager.validate_config(config)
        if validation_errors:
            logger.error(f"Configuration validation errors: {validation_errors}")
            raise ValueError(f"Invalid configuration: {'; '.join(validation_errors)}")
        
        # Set up streaming
        self.streaming_callback = streaming_callback
        
        # Initialize the configurable agent
        self.agent = ConfigurableCodeExecutorAgent(
            agent_config=config.agent,
            model_config=config.model,
            root_plots_dir=PLOTS_DIR,
            name=config.agent.name
        )
        
        # Store conversation history and state
        self.messages = []
        self.last_response_id = None
        
        # Store the current streaming result for cancellation
        self.current_streaming_result = None
        self.is_stream_cancelled = False
        
        logger.info(f"ConfigurableOpenAIAssistant initialized with configuration: {config_manager.get_config_summary(config)}")
    
    async def _async_process_message(self, user_message: str) -> Dict[str, Any]:
        """Process a user message asynchronously and return the agent's response"""
        logger.info(f"Processing user message: {user_message[:50]}...")
        
        try:
            # Store the user message in history
            if self.config.agent.maintain_conversation_history:
                self.messages.append({"role": "user", "content": user_message})
                self._manage_conversation_history()
            
            logger.info(f"ConfigurableOpenAIAssistant: Agent model: {self.agent.model}")
            # Check if streaming is enabled
            if self.config.runner.is_streaming_enabled():
                return await self._stream_response(user_message)
            else:
                return await self._standard_response(user_message)
                
        except Exception as e:
            logger.error(f"Error during agent execution: {e}")
            raise
    
    async def _standard_response(self, user_message: str) -> Dict[str, Any]:
        """Process message with standard (non-streaming) execution"""
        logger.info("Using standard response mode")
        
        # Set message ID
        message_id = self.agent.set_message_id()
        
        # Execute with cleanup
        with execution_cleanup():
            result = await Runner.run(
                self.agent,
                input=user_message,
                # previous_response_id=self.last_response_id
            )
        
        # Process result
        response_content = result.final_output
        plots = self._get_plots_for_message(message_id)
        
        # Log usage information
        self._log_usage_info(result.raw_responses)
        
        # Update state
        self.last_response_id = getattr(result, 'last_response_id', None)
        
        # Store AI response in history
        if self.config.agent.maintain_conversation_history:
            self.messages.append({"role": "assistant", "content": response_content})
        
        return {
            "content": response_content,
            "was_cancelled": False,
            "partial_response": False,
            "plots": plots,
            "metadata": self._create_response_metadata(message_id, result)
        }
    
    async def _stream_response(self, user_message: str) -> Dict[str, Any]:
        """Process message with streaming enabled"""
        logger.info("Using streaming response mode")
        
        try:
            # Reset cancellation flag
            self.is_stream_cancelled = False
            
            # Set message ID
            message_id = self.agent.set_message_id()
            
            # Execute with streaming and cleanup
            with execution_cleanup():
                result = Runner.run_streamed(
                    self.agent,
                    input=user_message,
                    # previous_response_id=self.last_response_id
                )
            
            # Store the streaming result for cancellation
            self.current_streaming_result = result
            
            # Collect the full response while streaming
            full_response = ""
            
            try:
                # Process streaming events with cancellation check
                async for event in result.stream_events():
                    # Check if we were cancelled
                    if self.is_stream_cancelled:
                        logger.info("🛑 Stream cancelled by user - stopping event processing")
                        break
                    
                    # Handle text delta events (check for ResponseTextDeltaEvent specifically)
                    if (event.type == "raw_response_event" and 
                        event.data.__class__.__name__ == "ResponseTextDeltaEvent" and
                        hasattr(event.data, 'delta')):
                        text_delta = getattr(event.data, 'delta', '')
                        if text_delta:
                            full_response += text_delta
                            
                            # Call the streaming callback
                            if self.streaming_callback:
                                self.streaming_callback(text_delta)
                            
            except asyncio.CancelledError:
                logger.info("🛑 Stream cancelled via asyncio.CancelledError")
                self.is_stream_cancelled = True
            
            # Cancel the underlying task if we were cancelled
            if self.is_stream_cancelled:
                logger.info("🛑 Cancelling underlying task after event loop exit")
                self.cancel_current_stream()
            
            # Clear the streaming result reference
            self.current_streaming_result = None
            
            # Handle cancelled streams
            if self.is_stream_cancelled:
                logger.info(f"Stream was cancelled, returning partial response: {len(full_response)} chars")
                return {
                    "content": full_response,
                    "was_cancelled": True,
                    "partial_response": True,
                    "plots": [],
                    "metadata": self._create_response_metadata(message_id, None, cancelled=True)
                }
            
            # Process completed response
            plots = self._get_plots_for_message(message_id)
            
            # Log usage information
            self._log_usage_info(result.raw_responses)
            
            # Update state
            self.last_response_id = getattr(result, 'last_response_id', None)
            
            # Store AI response in history
            if self.config.agent.maintain_conversation_history:
                self.messages.append({"role": "assistant", "content": full_response})
            
            return {
                "content": full_response,
                "was_cancelled": False,
                "partial_response": False,
                "plots": plots,
                "metadata": self._create_response_metadata(message_id, result)
            }
            
        except Exception as e:
            logger.error(f"Error during streaming agent execution: {e}")
            self.current_streaming_result = None
            raise
    
    def _create_run_config(self) -> RunConfig:
        """Create RunConfig from our configuration"""
        runner_config = self.config.runner
        model_config = self.config.model
        
        # Create model provider
        if model_config.provider.provider.value == "openai":
            model_provider = OpenAIProvider()
        else:
            # Future: support other providers
            model_provider = OpenAIProvider()
        
        # Create model settings
        model_settings = ModelSettings(
            **model_config.get_model_parameters_dict()
        )
        
        # Create and return run config
        return RunConfig(
            model=model_config.get_full_model_name(),
            model_provider=model_provider,
            model_settings=model_settings,
            **runner_config.get_sdk_run_config()
        )
    
    def _get_plots_for_message(self, message_id: str) -> list:
        """Get plots generated for a specific message"""
        plots_data = self.agent.get_all_plots_with_message_id()
        return plots_data.get(message_id, [])
    
    def _log_usage_info(self, raw_responses):
        """Log usage information from responses"""
        for response in raw_responses:
            if hasattr(response, 'usage') and response.usage:
                logger.debug(f"Response usage: {response.usage}")
    
    def _create_response_metadata(self, message_id: str, result=None, cancelled: bool = False) -> Dict[str, Any]:
        """Create response metadata"""
        metadata = {
            "user_id": self.user_id,
            "message_id": message_id,
            "model_name": self.config.model.name,
            "provider": self.config.model.provider.provider.value,
            "streaming_enabled": self.config.runner.is_streaming_enabled(),
            "was_cancelled": cancelled,
            "environment": self.environment,
            "config_version": self.config.config_version
        }
        
        if result:
            additional_metadata = {
                "total_turns": len(result.raw_responses) if hasattr(result, 'raw_responses') else 0,
                "response_id": getattr(result, 'last_response_id', None)
            }
            for key, value in additional_metadata.items():
                metadata[key] = value
        
        return metadata
    
    def _manage_conversation_history(self):
        """Manage conversation history based on configuration"""
        agent_config = self.config.agent
        
        if len(self.messages) > agent_config.max_context_messages:
            if agent_config.context_window_strategy == "sliding":
                # Keep the most recent messages
                excess = len(self.messages) - agent_config.max_context_messages
                self.messages = self.messages[excess:]
            elif agent_config.context_window_strategy == "truncate":
                # Truncate to max
                self.messages = self.messages[:agent_config.max_context_messages]
            # Note: "summarize" strategy would require additional implementation
    
    def cancel_current_stream(self):
        """Cancel the current streaming operation"""
        logger.info("Cancelling current stream")
        self.is_stream_cancelled = True
        
        if (self.current_streaming_result and 
            hasattr(self.current_streaming_result, '_run_impl_task') and
            self.current_streaming_result._run_impl_task and 
            not self.current_streaming_result._run_impl_task.done()):
            logger.info("🛑 Cancelling SDK _run_impl_task")
            self.current_streaming_result._run_impl_task.cancel()
        
        logger.info("✅ Stream cancellation initiated")
    
    def clear_memory(self) -> None:
        """Clear the agent's memory"""
        logger.info("Clearing agent memory")
        self.messages = []
        self.last_response_id = None
        logger.debug("Agent memory cleared")
    
    def update_configuration(self, new_config: Optional[AIConfig] = None, **kwargs):
        """
        Update configuration at runtime
        
        Args:
            new_config: Complete new configuration
            **kwargs: Specific configuration overrides
        """
        if new_config:
            self.config = new_config
        elif kwargs:
            # Apply overrides to current config
            self.config = config_manager.load_config(
                config_name="default",
                environment=self.environment,
                user_id=self.user_id,
                overrides=kwargs
            )
        
        # Update agent configuration
        self.agent.update_configuration(
            agent_config=self.config.agent,
            model_config=self.config.model
        )
        
        logger.info("Assistant configuration updated")
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration"""
        return config_manager.get_config_summary(self.config)
    
    def process_message(self, user_message: str) -> str:
        """Process a user message and return the agent's response (synchronous wrapper)"""
        result = asyncio.run(self._async_process_message(user_message))
        return result.get("content", "") 