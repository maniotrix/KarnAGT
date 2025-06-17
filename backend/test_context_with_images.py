#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test file demonstrating context building with image inputs for LLM calls.
This file shows how to use build_context for LLM calls with image input support, combining the functionality from conversation_context_builder.py, image_input_example.py, and configurable_openai_assistant.py.
"""

import asyncio
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from openai import OpenAI

# Import from our project
from aicore.core.configurable_openai_assistant import ConfigurableOpenAIAssistant
from aicore.config import AIConfig, config_manager
from aicore.logger import get_logger

logger = get_logger(__name__)

@dataclass
class MockMessage:
    """Mock message class for testing"""
    role: str
    content: str
    created_at: str = "2024-01-01T00:00:00Z"

@dataclass 
class MockContextConfig:
    """Mock context configuration for testing"""
    summary_length: str = "comprehensive"
    summary_max_tokens: int = 1000
    fixed_llm_conversation_tokens: int = 40000

class MockContextBuilder:
    """
    Mock context builder that simulates the build_context functionality
    without requiring database connections. This demonstrates why build_context
    is cleaner for LLM calls than build_context_dict.
    """
    
    def __init__(self, config: MockContextConfig, conversation_id: str):
        self.config = config
        self.conversation_id = conversation_id
        # Mock conversation history
        self.mock_messages = [
            MockMessage("user", "Hello! Can you help me analyze some images?"),
            MockMessage("assistant", "Of course! I'd be happy to help you analyze images. Please share the images you'd like me to look at."),
            MockMessage("user", "Here's a photo of a landmark, what can you tell me about it?"),
            MockMessage("assistant", "I can see this is a beautiful architectural structure. This is italian architecture."),
        ]
        
    async def build_context(self, latest_user_message: str, file_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Build conversation context optimized for LLM consumption.
        This demonstrates why build_context is cleaner than build_context_dict.
        
        Returns a list ready for direct LLM input:
        [
            {"role": "system", "content": "previous conversation summary"},
            {"role": "user", "content": "user message"},  
            {"role": "assistant", "content": "assistant response"},
            {"role": "user", "content": [text and/or image content]}
        ]
        """
        logger.info(f"Building context for conversation {self.conversation_id}")
        
        context_messages = []
        
        summary = await self._create_mock_summary()
        context_messages.append({
                "role": "system",
                "content": f"Previous conversation summary: {summary}"
            })
        
        # Add conversation history in chronological order
        for message in self.mock_messages:
            context_messages.append({
                "role": message.role,
                "content": message.content
            })
            
        # Build the latest user message (with image)
        if file_id:
            # Create multimodal message with image
            latest_message = {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": latest_user_message},
                    {"type": "input_image", "file_id": file_id,}
                ]
            }
        else:
            # Text-only message
            latest_message = {
                "role": "user", 
                "content": latest_user_message
            }
            
        context_messages.append(latest_message)
        
        logger.info(f"Context built: {len(context_messages)} messages, image_included={file_id is not None}")
        logger.info(f"Context messages: {context_messages}")
        return context_messages
    
    async def _create_mock_summary(self) -> str:
        """Create a mock conversation summary"""
        return """The user asked for travel location in India. I suggested delhi. 
    Then user asked for weather update for the location, which I responded with a weather as rainy now."""

class ImageContextTestSuite:
    """Test suite demonstrating image handling with context building"""
    
    def __init__(self):
        self.client = OpenAI()
        self.context_builder = MockContextBuilder(
            MockContextConfig(), 
            conversation_id="test-conv-123"
        )
        
    async def create_image_file(self, image_path: str) -> str:
        """Create a file using OpenAI Files API for vision"""
        try:
            with open(image_path, "rb") as file_content:
                result = self.client.files.create(
                    file=file_content,
                    purpose="vision"
                )
                logger.info(f"Created file with ID: {result.id}")
                return result.id
        except Exception as e:
            logger.error(f"Failed to create file: {e}")
            # Return mock file ID for testing
            return "file-mock-123456"
        
        
    async def create_and_run_agent_with_image(self, image_path: str, user_message: str):
        """Create an agent with an image and run it with a user message"""
        # file_id = await self.create_image_file(image_path)
        file_id = "file-G8QUc26PtNin7iDmCcpAqp"
        context = await self.context_builder.build_context(user_message, file_id)
        
        from agents import Agent, Runner
        
        agent = Agent(
            name="Test Assistant",
            #model="gpt-4o-mini-2024-07-18",
            instructions="You are a helpful assistant.",
        )
        
        result = await Runner.run(
            agent, context
        )
        
        print(f"Result: {result.final_output}")
    
async def main():
    """Main test runner"""
    print("🚀 Starting Context Building with Images Test Suite")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, "fifa_test_image.png")
    
    # check if image exists
    if not os.path.exists(image_path):
        print(f"Image file does not exist: {image_path}")
        return
    
    # check if image is a valid image
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            img.verify()  # This will raise an exception if invalid
        print(f"✅ Image validation passed: {image_path}")
    except Exception as e:
        print(f"❌ Invalid image file: {image_path} - Error: {e}")
        return
    
    from aicore.ai_config import validate_api_keys
    validate_api_keys()

    test_suite = ImageContextTestSuite()
    
    # Test 1: Compare build_context vs build_context_dict
    await test_suite.create_and_run_agent_with_image(
        image_path=image_path,
        user_message="tell me what we have discussed so far, from start to end. and also tell me what you see in the image."
    )
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(main()) 