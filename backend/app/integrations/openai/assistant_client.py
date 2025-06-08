"""
OpenAI Assistant Client - FastAPI Integration

This module provides a FastAPI-compatible wrapper around the aicore OpenAIAssistant,
adding database integration, user context, and async support.
"""

import asyncio
import uuid
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
import sys
import os

# Add aicore to path for import
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../aicore"))

from aicore.openai_assistant import OpenAIAssistant
from aicore.logger import get_logger

from app.core.config import settings
from app.models.database.user import User
from app.models.database.conversation import Conversation
from app.models.database.message import Message
from app.models.schemas.chat_schemas import MessageCreate, MessageResponse

# Set up logger
logger = get_logger(__name__)


class OpenAIAssistantClient:
    """
    FastAPI-compatible wrapper for aicore OpenAIAssistant
    
    Features:
    - User context management
    - Database integration for conversation persistence
    - Async streaming support
    - Cost tracking integration
    - Error handling and retry logic
    """
    
    def __init__(self, user_id: str, conversation_id: Optional[str] = None):
        """
        Initialize the assistant client for a specific user
        
        Args:
            user_id: The user ID for context and permissions
            conversation_id: Optional conversation ID for context
        """
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.assistant = None
        self.streaming_callback = None
        self.cost_tracker = None
        
        # Initialize the aicore assistant
        self._initialize_assistant()
        
        logger.info(f"OpenAIAssistantClient initialized for user {user_id}")
    
    def _initialize_assistant(self):
        """Initialize the underlying aicore OpenAIAssistant"""
        try:
            # Ensure OpenAI API key is available in environment for aicore
            # The aicore assistant expects os.environ['OPENAI_API_KEY'] to be set
            if not os.environ.get('OPENAI_API_KEY'):
                if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip():
                    os.environ['OPENAI_API_KEY'] = settings.OPENAI_API_KEY
                    logger.debug("Set OPENAI_API_KEY environment variable for aicore from settings")
                else:
                    raise ValueError("OPENAI_API_KEY not found in settings or environment")
            
            # Set streaming callback if needed
            self.assistant = OpenAIAssistant(streaming_callback=self._handle_streaming_token)
            logger.debug("aicore OpenAIAssistant initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAIAssistant: {e}")
            raise
    
    def set_streaming_callback(self, callback: Callable[[str], None]):
        """
        Set a callback function for streaming responses
        
        Args:
            callback: Function to call with each streaming token
        """
        self.streaming_callback = callback
        logger.debug("Streaming callback set")
    
    def _handle_streaming_token(self, token: str):
        """
        Internal handler for streaming tokens from aicore
        
        Args:
            token: The streaming token from OpenAI
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
            # Process the message through aicore - now returns dict with cancellation info
            ai_response_data = await self.assistant._async_process_message(message)
            
            # Extract plots if any were generated
            plots = []
            if hasattr(self.assistant.agent, 'get_all_plots_with_message_id'):
                plots_data = self.assistant.agent.get_all_plots_with_message_id()
                current_msg_id = self.assistant.agent.get_current_message_id()
                if current_msg_id in plots_data:
                    plots = plots_data[current_msg_id]
            
            # Prepare response data
            response_data = {
                "content": ai_response_data["content"],  # Extract content from dict
                "was_cancelled": ai_response_data.get("was_cancelled", False),
                "partial_response": ai_response_data.get("partial_response", False),
                "type": "text",
                "plots": plots,
                "metadata": {
                    "user_id": self.user_id,
                    "conversation_id": self.conversation_id,
                    "message_id": getattr(self.assistant.agent, 'current_message_id', str(uuid.uuid4())[:8]),
                    "timestamp": datetime.utcnow().isoformat(),
                    "model": "gpt-4",  # Default model, could be dynamic
                    **(metadata or {})
                }
            }
            
            logger.info(f"AI response generated successfully for user {self.user_id}")
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
        
        try:
            # Process the message with streaming - now returns dict with cancellation info
            ai_response_data = await self.assistant._async_process_message(message)
            
            # Extract plots if any were generated
            plots = []
            if hasattr(self.assistant.agent, 'get_all_plots_with_message_id'):
                plots_data = self.assistant.agent.get_all_plots_with_message_id()
                current_msg_id = self.assistant.agent.get_current_message_id()
                if current_msg_id in plots_data:
                    plots = plots_data[current_msg_id]
            
            # Prepare response data with cancellation status
            response_data = {
                "content": ai_response_data["content"],  # Extract content from dict
                "was_cancelled": ai_response_data.get("was_cancelled", False),  # Pass through cancellation status
                "partial_response": ai_response_data.get("partial_response", False),
                "type": "text",
                "plots": plots,
                "metadata": {
                    "user_id": self.user_id,
                    "conversation_id": self.conversation_id,
                    "message_id": getattr(self.assistant.agent, 'current_message_id', str(uuid.uuid4())[:8]),
                    "timestamp": datetime.utcnow().isoformat(),
                    "model": "gpt-4",
                    "streaming": True,
                    **(metadata or {})
                }
            }
            
            logger.info(f"Streaming AI response completed for user {self.user_id}, cancelled: {ai_response_data.get('was_cancelled', False)}")
            return response_data
            
        except Exception as e:
            logger.error(f"Error processing streaming message for user {self.user_id}: {e}")
            raise
        finally:
            # Clear the streaming callback
            self.streaming_callback = None
    
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
    
    def add_tool(self, tool_name: str, tool_function: Callable):
        """
        Add a custom tool to the assistant
        
        Args:
            tool_name: Name of the tool
            tool_function: The tool function to add
        """
        if self.assistant:
            self.assistant.add_tool(tool_name, tool_function)
            logger.info(f"Tool '{tool_name}' added for user {self.user_id}")
    
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
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        # Cleanup if needed
        pass


class AssistantManager:
    """
    Manager class for handling multiple assistant clients
    """
    
    def __init__(self):
        self.clients: Dict[str, OpenAIAssistantClient] = {}
        logger.info("AssistantManager initialized")
    
    def get_client(self, user_id: str, conversation_id: Optional[str] = None) -> OpenAIAssistantClient:
        """
        Get or create an assistant client for a user
        
        Args:
            user_id: The user ID
            conversation_id: Optional conversation ID
            
        Returns:
            OpenAIAssistantClient instance
        """
        client_key = f"{user_id}_{conversation_id or 'default'}"
        
        if client_key not in self.clients:
            self.clients[client_key] = OpenAIAssistantClient(user_id, conversation_id)
            logger.info(f"Created new assistant client for user {user_id}")
        
        return self.clients[client_key]
    
    def remove_client(self, user_id: str, conversation_id: Optional[str] = None):
        """
        Remove an assistant client
        
        Args:
            user_id: The user ID
            conversation_id: Optional conversation ID
        """
        client_key = f"{user_id}_{conversation_id or 'default'}"
        
        if client_key in self.clients:
            del self.clients[client_key]
            logger.info(f"Removed assistant client for user {user_id}")
    
    def clear_all_clients(self):
        """Clear all assistant clients"""
        self.clients.clear()
        logger.info("All assistant clients cleared")


# Global assistant manager instance
assistant_manager = AssistantManager() 