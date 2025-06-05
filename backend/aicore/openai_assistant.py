#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
OpenAI assistant agent implementation using OpenAI Agents SDK
"""

import os
import asyncio
from typing import Optional, List, Any, Callable, Dict
import glob
from agents import Agent, Runner, ModelSettings, function_tool, WebSearchTool
from pydantic import BaseModel
from openai.types.responses import ResponseTextDeltaEvent

# Use absolute imports instead of relative
from aicore.code_executor.utils import execution_cleanup
from aicore.logger import get_logger

from aicore.code_executor.code_agent import CodeExecutorAgent
from aicore.path_config import PLOTS_DIR

# Define a fixed directory for plot outputs
os.makedirs(PLOTS_DIR, exist_ok=True)


# Get logger

# Set up logger
logger = get_logger(__name__)

# System prompt for the OpenAI assistant
ASSISTANT_PROMPT = """You are an intelligent and helpful AI assistant powered by OpenAI.
You excel at providing clear, accurate, and thoughtful responses to a wide range of inquiries.

Your capabilities include:
- Answering questions with accurate, up-to-date information
- Problem-solving and strategic thinking
- Creative ideation and brainstorming
- Explaining complex concepts in accessible ways

You aim to be helpful, harmless, and honest in all your interactions. You acknowledge when you don't know something rather than making up information.

Respond in a conversational and friendly tone while maintaining professionalism. Focus on providing value in each response.
"""


class OpenAIAssistant:
    """Manager class for the OpenAI assistant agent using the Agents SDK"""
    agent: CodeExecutorAgent
    def __init__(self, streaming_callback=None):
        """Initialize the agent with OpenAI Agents SDK"""
        logger.info("Initializing OpenAIAssistant with Agents SDK")
        
        # Set up streaming configuration if a callback is provided
        self.streaming_callback = streaming_callback
        
        # Initialize the agent with system instructions
        self.agent = CodeExecutorAgent(
                name="OpenAI Assistant",
                root_plots_dir=PLOTS_DIR
            )
        
        # Store conversation history and last_response_id for continuity
        self.messages = []
        self.last_response_id = None
        logger.debug("OpenAIAssistant initialized with Agents SDK")
    
    async def _async_process_message(self, user_message: str) -> str:
        """Process a user message asynchronously and return the agent's response"""
        logger.info(f"Processing user message: {user_message[:50]}...")
        
        try:
            # Store the user message in history
            self.messages.append({"role": "user", "content": user_message})
            
            # Check if streaming is enabled
            if self.streaming_callback:
                return await self._stream_response(user_message)
            else:
                # Run the agent with standard execution, using last_response_id if available
                _message_id = self.agent.set_message_id()
                custom_result = {}
                with execution_cleanup():
                    result = await Runner.run(
                        self.agent,
                        input=user_message,
                        previous_response_id=self.last_response_id
                    )
                    
                custom_result = {
                    'message_id': _message_id,
                    'response': result.final_output,
                    'plots': glob.glob(f"{self.agent.unique_plots_dir}/{_message_id}_*.png")
                }
                
                # print result usage
                raw_responses = result.raw_responses
                for response in raw_responses:
                    logger.debug(f"Response usage: {response.usage}")
                
                # Get the response
                response = result.final_output
                logger.debug(f"AI response generated: {response[:50]}...")
                
                # Store the response ID for the next interaction
                self.last_response_id = result.last_response_id
                logger.debug(f"Stored response ID: {self.last_response_id}")
                
                # Store the AI response in history
                self.messages.append({"role": "assistant", "content": response})
                
                return response
        except Exception as e:
            logger.error(f"Error during agent execution: {e}")
            raise
    
    async def _stream_response(self, user_message: str) -> str:
        """Process a user message with streaming enabled"""
        logger.info("Using streaming response mode")
        
        try:
            # Run the agent with streaming, using last_response_id if available
            _message_id = self.agent.set_message_id()
            custom_result = {}
            with execution_cleanup():
                result = Runner.run_streamed(
                    self.agent,
                    input=user_message,
                    previous_response_id=self.last_response_id
                )
            
            # Collect the full response while streaming
            full_response = ""
            
            # Process streaming events
            async for event in result.stream_events():
                if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                    # Get the text delta
                    text_delta = event.data.delta
                    
                    # Add to the full response
                    full_response += text_delta
                    
                    # Call the streaming callback with the delta
                    if self.streaming_callback:
                        self.streaming_callback(text_delta)
            
            logger.debug(f"Streaming AI response completed: {full_response[:50]}...")
            
            custom_result = {
                'message_id': _message_id,
                'response': full_response,
                'plots': glob.glob(f"{self.agent.unique_plots_dir}/{_message_id}_*.png")
            }
            
        # print result usage
            raw_responses = result.raw_responses
            for response in raw_responses:
                logger.debug(f"Response usage: {response.usage}")
            
            # Store the response ID for the next interaction
            self.last_response_id = result.last_response_id
            logger.debug(f"Stored streamed response ID: {self.last_response_id}")
            
            # Store the AI response in history
            self.messages.append({"role": "assistant", "content": full_response})
            
            return full_response
        except Exception as e:
            logger.error(f"Error during streaming agent execution: {e}")
            raise
    
    def process_message(self, user_message: str) -> str:
        """Process a user message and return the agent's response (synchronous wrapper)"""
        return asyncio.run(self._async_process_message(user_message))
    
    def clear_memory(self) -> None:
        """Clear the agent's memory"""
        logger.info("Clearing agent memory")
        self.messages = []
        self.last_response_id = None
        logger.debug("Agent memory and response ID cleared")
    
    def add_tool(self, tool_name: str, tool_function: Callable) -> None:
        """Add a tool to the agent"""
        logger.info(f"Adding tool to agent: {tool_name}")
        
        @function_tool
        def wrapped_tool(*args, **kwargs):
            """Wrapper for the tool function with error handling and logging"""
            logger.debug(f"Executing tool {tool_name}")
            try:
                result = tool_function(*args, **kwargs)
                logger.debug(f"Tool {tool_name} execution completed")
                return result
            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {e}")
                raise
        
        # Add the wrapped tool to the agent
        if self.agent:
            logger.debug(f"Adding tool {tool_name} to agent")
            self.agent.tools.append(wrapped_tool) 