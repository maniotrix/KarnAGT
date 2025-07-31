#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configurable OpenAI Assistant - Uses centralized configuration system
"""

# Standard Library / Typing
import asyncio
import contextvars
from typing import Optional, Dict, Any, Callable, List

# Third-party
from agents import Runner, RunConfig, ModelSettings, OpenAIProvider

# OpenAI types for safe isinstance checks
from openai.types.responses import ResponseTextDeltaEvent

# Import configuration classes
from app.aicore.config import AIConfig, config_manager
from app.aicore.ai_agents.configurable_code_agent import ConfigurableCodeExecutorAgent
from app.aicore.code_executor import WorkspaceExecutionSession
from app.logging.logger import get_logger

# Set up logger
logger = get_logger(__name__)


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
            name=config.agent.name
        )
        
        # Store conversation history and state
        self.messages = []
        self.last_response_id = None
        
        # Store the current streaming result for cancellation
        self.current_streaming_result = None
        self.is_stream_cancelled = False

        # Task that wraps consumption of the SDK stream iterator
        self._stream_task = None
        
        logger.info(f"ConfigurableOpenAIAssistant initialized with configuration: {config_manager.get_config_summary(config)}")
    
    async def _async_process_message(self, user_message: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a user message asynchronously and return the agent's response.
        
        This method integrates workspace session management for automatic cleanup
        of any workspaces created during agent execution. The session context manager
        guarantees cleanup even if exceptions occur during agent execution.
        
        Exception Safety:
        - Workspace session cleanup is guaranteed via context manager
        - All workspaces created during execution are automatically cleaned up
        - Context variables are properly reset even on exceptions
        - Session objects are released for garbage collection
        """
        logger.info(f"Processing user message context with {len(user_message)} messages")
        
        try:
            # Store the user message in history
            if self.config.agent.maintain_conversation_history:
                self.messages.append(user_message)
                self._manage_conversation_history()
            
            logger.info(f"ConfigurableOpenAIAssistant: Agent model: {self.agent.model}")
            
            # 🚀 WORKSPACE SESSION INTEGRATION - INSIDE TRY-CATCH FOR GUARANTEED CLEANUP
            async with WorkspaceExecutionSession() as session:
                logger.info(f"Created workspace session {session.session_id} for message processing")
                
                # Check if streaming is enabled
                if self.config.runner.is_streaming_enabled():
                    return await self._stream_response(user_message)
                else:
                    return await self._standard_response(user_message)
            
            # Session automatically cleaned up here (even if there are exceptions)
            # You'll see logs like: "Session {session_id}: Cleanup completed - X/X workspaces cleaned"
                
        except Exception as e:
            logger.error(f"Error during agent execution: {e}")
            # Session cleanup happens automatically even with exceptions
            raise
    
    async def _standard_response(self, user_message: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process message with standard (non-streaming) execution"""
        logger.info("Using standard response mode")
        
        # Set message ID
        message_id = self.agent.set_message_id()
        
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
        
        # Store AI response in history if maintaining conversation history
        if self.config.agent.maintain_conversation_history:
            self.messages.append({"role": "assistant", "content": response_content})
        
        return {
            "content": response_content,
            "was_cancelled": False,
            "partial_response": False,
            "plots": plots,
            "metadata": self._create_response_metadata(message_id, result)
        }
    
    async def _stream_response(self, user_message: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process message with streaming enabled"""
        logger.info("Using streaming response mode")
        
        try:
            # Setup streaming
            message_id, result = await self._setup_streaming(user_message)
            
            # Holder for response chunks that persists across all error scenarios
            full_chunks: List[str] = []
            
            try:
                # Process events with wrapper task
                event_count = await self._process_streaming_events(result, full_chunks)
                
                # Handle successful completion
                return self._build_final_response(message_id, result, full_chunks, was_error=False)
                
            except asyncio.CancelledError:
                # User-requested cancellation or task-level cancellation
                logger.info("[CANCEL] Stream cancelled via asyncio.CancelledError")
                self.is_stream_cancelled = True
                return self._build_final_response(message_id, None, full_chunks, was_error=False)
                
            except Exception as e:
                # Any streaming-related SDK error (ContextVar, network, etc.)
                logger.error(f"Streaming failed during event processing: {e}")
                self.is_stream_cancelled = True
                return self._build_final_response(message_id, None, full_chunks, was_error=True, error=e)
            
        except Exception as e:
            logger.error(f"Error during streaming agent execution: {e}")
            self.current_streaming_result = None
            raise
    
    async def _setup_streaming(self, user_message: List[Dict[str, Any]]) -> tuple[str, Any]:
        """Setup streaming components and return message_id and result"""
        # Reset cancellation flag
        self.is_stream_cancelled = False
        logger.info(f"[DEBUG] Reset cancellation flag to False")
        
        # Set message ID
        message_id = self.agent.set_message_id()
        
        # Create streaming result
        result = Runner.run_streamed(
            self.agent,
            input=user_message,
            # previous_response_id=self.last_response_id
        )
        
        # Store the streaming result for cancellation
        self.current_streaming_result = result
        logger.info(f"[DEBUG] Stored streaming result, task: {result._run_impl_task}")
        
        return message_id, result
    
    async def _process_streaming_events(self, result, full_chunks: List[str]) -> int:
        """Process streaming events using wrapper task with context preservation"""
        event_count = 0

        async def _consume_events():
            nonlocal event_count
            logger.info("[DEBUG] Starting event loop processing (wrapper task)")
            try:
                async for event in result.stream_events():
                    event_count += 1
                    logger.debug(f"[DEBUG] Processing event #{event_count}, cancelled flag: {self.is_stream_cancelled}")

                    # Early exit if cancellation requested
                    if self.is_stream_cancelled:
                        logger.info(f"[CANCEL] Stream cancelled by user - breaking consume loop after {event_count} events")
                        break

                    # Handle text deltas safely with isinstance
                    if (event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent)):
                        delta = event.data.delta
                        if delta:
                            full_chunks.append(delta)
                            if self.streaming_callback:
                                logger.debug(f"[DEBUG] Calling streaming callback with token: '{delta[:20]}...'")
                                self.streaming_callback(delta)

            except asyncio.CancelledError:
                logger.info(f"[CANCEL] Consume task cancelled after {event_count} events")
                raise

        # Launch wrapper task and store reference for cancellation
        # Preserve the current context so agents SDK tracing variables remain accessible
        current_context = contextvars.copy_context()
        self._stream_task = current_context.run(asyncio.create_task, _consume_events())

        try:
            await self._stream_task
            logger.info(f"[DEBUG] Event loop completed normally. Total events: {event_count}, cancelled flag: {self.is_stream_cancelled}")
        except asyncio.CancelledError:
            # Propagate cancellation state
            self.is_stream_cancelled = True
            logger.info(f"[CANCEL] Stream task CancelledError after {event_count} events")
            raise
        finally:
            # Always cleanup, regardless of how the task ended
            self._cleanup_streaming_state()
        
        return event_count
    
    def _cleanup_streaming_state(self):
        """Clean up streaming state after completion or error"""
        self.cancel_current_stream("automatic_cleanup")
        
        # Clear references
        self.current_streaming_result = None
        self._stream_task = None
    
    def _build_final_response(self, message_id: str, result: Any, full_chunks: List[str], *, was_error: bool = False, error: Exception = None) -> Dict[str, Any]:
        """Build the final streaming response for both success and error cases"""
        content = "".join(full_chunks)
        
        # Handle cancelled or error scenarios
        if self.is_stream_cancelled or was_error:
            metadata = self._create_response_metadata(message_id, None, cancelled=True)
            if was_error and error:
                metadata["stream_error"] = str(error)
                metadata["error_type"] = type(error).__name__
            
            logger.info(f"Stream {'cancelled' if self.is_stream_cancelled else 'failed'}, returning partial response: {len(content)} chars")
            return {
                "content": content,
                "was_cancelled": True,
                "partial_response": True,
                "plots": [],
                "metadata": metadata
            }
        
        # Handle successful completion
        logger.info(f"[DEBUG] Stream completed normally with {len(content)} chars")
        
        # Process completed response
        plots = self._get_plots_for_message(message_id)
        
        # Log usage information
        self._log_usage_info(result.raw_responses)
        
        # Update state
        self.last_response_id = getattr(result, 'last_response_id', None)
        
        # Store AI response in history
        if self.config.agent.maintain_conversation_history:
            self.messages.append({"role": "assistant", "content": content})
        
        return {
            "content": content,
            "was_cancelled": False,
            "partial_response": False,
            "plots": plots,
            "metadata": self._create_response_metadata(message_id, result)
        }
    
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
    
    def cancel_current_stream(self, reason: str = "user_requested"):
        """Cancel the current streaming operation"""
        logger.info("[START CANCEL CURRENT STREAM LOG: --------------------------------]")
        if reason == "user_requested":
            logger.info("[USER-INITIATED] Cancelling current stream - user requested stop")
        else:
            logger.info(f"[INTERNAL] Cancelling current stream - {reason}")
        
        logger.info(f"[DEBUG] Setting is_stream_cancelled from {self.is_stream_cancelled} to True")
        self.is_stream_cancelled = True

        # Cancel wrapper task first (if running)
        if getattr(self, "_stream_task", None) and not self._stream_task.done():
            logger.info("[CANCEL] Cancelling wrapper _stream_task")
            self._stream_task.cancel()
        
        if (self.current_streaming_result and 
            hasattr(self.current_streaming_result, '_run_impl_task') and
            self.current_streaming_result._run_impl_task and 
            not self.current_streaming_result._run_impl_task.done()):
            logger.info("[CANCEL] Cancelling SDK _run_impl_task")
            logger.info(f"[DEBUG] Task before cancel - done: {self.current_streaming_result._run_impl_task.done()}, cancelled: {self.current_streaming_result._run_impl_task.cancelled()}")
            self.current_streaming_result._run_impl_task.cancel()
            logger.info(f"[DEBUG] Task after cancel - done: {self.current_streaming_result._run_impl_task.done()}, cancelled: {self.current_streaming_result._run_impl_task.cancelled()}")
        else:
            logger.info("[DEBUG] No task to cancel or task already done")
            if self.current_streaming_result:
                if hasattr(self.current_streaming_result, '_run_impl_task'):
                    if self.current_streaming_result._run_impl_task:
                        logger.info(f"[DEBUG] Task is already done: {self.current_streaming_result._run_impl_task.done()}")
                    else:
                        logger.info("[DEBUG] _run_impl_task is None")
                else:
                    logger.info("[DEBUG] No _run_impl_task attribute")
            else:
                logger.info("[DEBUG] No current_streaming_result")
        
        if reason == "user_requested":
            logger.info("[SUCCESS] User-initiated stream cancellation completed")
        else:
            logger.info(f"[SUCCESS] Cleanup stream cancellation completed - {reason}")
            
        logger.info("[END CANCEL CURRENT STREAM LOG: --------------------------------]")
    
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
    
    def process_message(self, user_message: List[Dict[str, Any]]) -> str:
        """Process a user message and return the agent's response (synchronous wrapper)"""
        result = asyncio.run(self._async_process_message(user_message))
        return result.get("content", "") 