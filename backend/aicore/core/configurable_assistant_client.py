#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configurable Assistant Client - Integration with centralized configuration system
"""

import asyncio
import uuid
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime

from aicore.config import AIConfig, ConfigManager, config_manager
from aicore.core.configurable_openai_assistant import ConfigurableOpenAIAssistant
from aicore.logger import get_logger

# Set up logger
logger = get_logger(__name__)


class ConfigurableAssistantClient:
    """
    Configurable assistant client with full configuration management.
    
    Features:
    - Centralized configuration system
    - User-specific configurations
    - Environment-based settings
    - Runtime configuration updates
    - Cost tracking integration
    - Advanced error handling
    """
    
    def __init__(
        self, 
        user_id: str, 
        conversation_id: Optional[str] = None,
        environment: Optional[str] = None,
        config_name: str = "default",
        config_overrides: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the configurable assistant client
        
        Args:
            user_id: The user ID for context and permissions
            conversation_id: Optional conversation ID for context
            environment: Environment name (dev, prod, test)
            config_name: Named configuration to load
            config_overrides: Runtime configuration overrides
        """
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.environment = environment
        self.config_name = config_name
        
        # Load configuration
        self.config = config_manager.load_config(
            config_name=config_name,
            environment=environment,
            user_id=user_id,
            overrides=config_overrides
        )
        
        # Initialize the configurable assistant
        self.assistant = None
        self.streaming_callback = None
        self.cost_tracker = None
        
        self._initialize_assistant()
        
        logger.info(f"ConfigurableAssistantClient initialized for user {user_id} with environment {environment}")
    
    def _initialize_assistant(self):
        """Initialize the underlying configurable assistant"""
        try:
            # Create the configurable assistant with our configuration
            self.assistant = ConfigurableOpenAIAssistant(
                config=self.config,
                user_id=self.user_id,
                environment=self.environment,
                streaming_callback=self._handle_streaming_token
            )
            
            logger.debug("ConfigurableOpenAIAssistant initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ConfigurableOpenAIAssistant: {e}")
            raise
    
    def set_streaming_callback(self, callback: Callable[[str], None]):
        """
        Set a callback function for streaming responses
        
        Args:
            callback: Function to call with each streaming token
        """
        self.streaming_callback = callback
        if self.assistant:
            self.assistant.streaming_callback = self._handle_streaming_token
        logger.debug("Streaming callback set")
    
    def _handle_streaming_token(self, token: str):
        """
        Internal handler for streaming tokens
        
        Args:
            token: The streaming token from the AI model
        """
        if self.streaming_callback:
            self.streaming_callback(token)
    
    async def send_message(
        self,
        message: str,
        message_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a message to the AI assistant and get a response
        
        Args:
            message: The user message content
            message_type: Type of message (text, image, etc.)
            metadata: Optional metadata for the message
            
        Returns:
            Dict containing the response and metadata
        """
        logger.info(f"Processing message for user {self.user_id}")
        
        try:
            # Process the message through the configurable assistant
            ai_response_data = await self.assistant._async_process_message(message)
            
            # Extract plots from response metadata
            response_metadata = ai_response_data.get("metadata", {})
            plots = ai_response_data.get("plots", [])
            
            # Enhance response data with client-specific metadata
            enhanced_metadata = self._create_enhanced_metadata(
                base_metadata=response_metadata,
                message_type=message_type,
                user_metadata=metadata
            )
            
            # Prepare final response
            response_data = {
                "content": ai_response_data["content"],
                "was_cancelled": ai_response_data.get("was_cancelled", False),
                "partial_response": ai_response_data.get("partial_response", False),
                "type": message_type,
                "plots": plots,
                "metadata": enhanced_metadata
            }
            
            logger.info(f"Message processed successfully for user {self.user_id}")
            return response_data
            
        except Exception as e:
            logger.error(f"Error processing message for user {self.user_id}: {e}")
            raise
    
    async def send_message_streaming(
        self,
        message: str,
        callback: Callable[[str], None],
        message_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a message with streaming response
        
        Args:
            message: The user message content
            callback: Callback function for streaming tokens
            message_type: Type of message
            metadata: Optional metadata
            
        Returns:
            Dict containing the final response and metadata
        """
        logger.info(f"Processing streaming message for user {self.user_id}")
        
        # Set the streaming callback
        self.set_streaming_callback(callback)
        
        # Temporarily enable streaming in configuration if not enabled
        original_streaming_mode = self.config.runner.streaming.mode
        if not self.config.runner.is_streaming_enabled():
            logger.info("Temporarily enabling streaming for this request")
            self.update_configuration(overrides={
                "runner": {"streaming": {"mode": "text_only"}}
            })
        
        try:
            # Process the message with streaming
            result = await self.send_message(message, message_type, metadata)
            
            # Restore original streaming configuration
            if original_streaming_mode != self.config.runner.streaming.mode:
                self.update_configuration(overrides={
                    "runner": {"streaming": {"mode": original_streaming_mode.value}}
                })
            
            # Add streaming-specific metadata
            result["metadata"]["streaming"] = True
            result["metadata"]["original_streaming_mode"] = original_streaming_mode.value
            
            logger.info(f"Streaming message processed for user {self.user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing streaming message for user {self.user_id}: {e}")
            # Restore configuration on error
            if original_streaming_mode != self.config.runner.streaming.mode:
                self.update_configuration(overrides={
                    "runner": {"streaming": {"mode": original_streaming_mode.value}}
                })
            raise
        finally:
            # Clear the streaming callback
            self.streaming_callback = None
    
    def _create_enhanced_metadata(
        self, 
        base_metadata: Dict[str, Any], 
        message_type: str,
        user_metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create enhanced metadata combining all sources"""
        enhanced = {
            **base_metadata,
            "conversation_id": self.conversation_id,
            "message_type": message_type,
            "timestamp": datetime.utcnow().isoformat(),
            "client_version": "2.0",  # Version of the configurable client
            "config_name": self.config_name,
        }
        
        # Add user-provided metadata
        if user_metadata:
            enhanced["user_metadata"] = user_metadata
        
        return enhanced
    
    def update_configuration(
        self, 
        config: Optional[AIConfig] = None,
        overrides: Optional[Dict[str, Any]] = None,
        persist: bool = False
    ):
        """
        Update configuration at runtime
        
        Args:
            config: Complete new configuration
            overrides: Specific configuration overrides
            persist: Whether to persist changes to user config file
        """
        if config:
            self.config = config
        elif overrides:
            # Apply overrides to current config
            self.config = config_manager.load_config(
                config_name=self.config_name,
                environment=self.environment,
                user_id=self.user_id,
                overrides=overrides
            )
        
        # Update the assistant with new configuration
        if self.assistant:
            self.assistant.update_configuration(new_config=self.config)
        
        # Optionally persist the configuration
        if persist:
            config_manager.save_config(
                self.config, 
                f"user_{self.user_id}_{self.config_name}"
            )
        
        logger.info(f"Configuration updated for user {self.user_id}")
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration"""
        base_summary = config_manager.get_config_summary(self.config)
        base_summary.update({
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "environment": self.environment,
            "config_name": self.config_name,
        })
        return base_summary
    
    def clear_conversation_memory(self):
        """Clear the conversation memory"""
        if self.assistant:
            self.assistant.clear_memory()
            logger.info(f"Conversation memory cleared for user {self.user_id}")
    
    def cancel_streaming(self):
        """Cancel any active streaming operation"""
        logger.info(f"Cancelling streaming for user {self.user_id}")
        if self.assistant:
            self.assistant.cancel_current_stream()
        else:
            logger.warning("No assistant instance to cancel")
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Get the current conversation history
        
        Returns:
            List of message dictionaries
        """
        if self.assistant and hasattr(self.assistant, 'messages'):
            return self.assistant.messages
        return []
    
    def set_conversation_context(self, messages: List[Dict[str, Any]]):
        """
        Set conversation context from existing messages
        
        Args:
            messages: List of message dictionaries to set as context
        """
        if self.assistant:
            self.assistant.messages = messages
            logger.info(f"Conversation context set with {len(messages)} messages for user {self.user_id}")
    
    def get_model_capabilities(self) -> Dict[str, Any]:
        """Get current model capabilities"""
        return {
            "model_name": self.config.model.name,
            "supports_streaming": self.config.model.capabilities.supports_streaming,
            "supports_functions": self.config.model.capabilities.supports_functions,
            "supports_vision": self.config.model.capabilities.supports_vision,
            "max_context_tokens": self.config.model.capabilities.context_window,
            "max_output_tokens": self.config.model.capabilities.max_output_tokens,
        }
    
    def validate_configuration(self) -> List[str]:
        """Validate current configuration and return any errors"""
        return config_manager.validate_config(self.config)
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        # Cleanup if needed
        pass


class ConfigurableAssistantManager:
    """
    Manager class for handling multiple configurable assistant clients
    """
    
    def __init__(self):
        self.clients: Dict[str, ConfigurableAssistantClient] = {}
        logger.info("ConfigurableAssistantManager initialized")
    
    def get_client(
        self, 
        user_id: str, 
        conversation_id: Optional[str] = None,
        environment: Optional[str] = None,
        config_name: str = "default",
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> ConfigurableAssistantClient:
        """
        Get or create a configurable assistant client for a user
        
        Args:
            user_id: The user ID
            conversation_id: Optional conversation ID
            environment: Environment name
            config_name: Configuration name to use
            config_overrides: Runtime configuration overrides
            
        Returns:
            ConfigurableAssistantClient instance
        """
        client_key = f"{user_id}_{conversation_id or 'default'}_{environment or 'default'}_{config_name}"
        
        if client_key not in self.clients:
            self.clients[client_key] = ConfigurableAssistantClient(
                user_id=user_id,
                conversation_id=conversation_id,
                environment=environment,
                config_name=config_name,
                config_overrides=config_overrides
            )
            logger.info(f"Created new configurable assistant client for user {user_id}")
        
        return self.clients[client_key]
    
    def remove_client(
        self, 
        user_id: str, 
        conversation_id: Optional[str] = None,
        environment: Optional[str] = None,
        config_name: str = "default"
    ):
        """Remove a configurable assistant client"""
        client_key = f"{user_id}_{conversation_id or 'default'}_{environment or 'default'}_{config_name}"
        
        if client_key in self.clients:
            del self.clients[client_key]
            logger.info(f"Removed configurable assistant client for user {user_id}")
    
    def clear_all_clients(self):
        """Clear all assistant clients"""
        self.clients.clear()
        logger.info("All configurable assistant clients cleared")
    
    def get_client_summary(self) -> Dict[str, Any]:
        """Get summary of all active clients"""
        return {
            "total_clients": len(self.clients),
            "client_keys": list(self.clients.keys()),
            "configurations": [
                client.get_configuration_summary() 
                for client in self.clients.values()
            ]
        }


# Global configurable assistant manager instance
configurable_assistant_manager = ConfigurableAssistantManager() 