#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test file demonstrating context building with image inputs for LLM calls.
This file shows how to use build_context for LLM calls with image input support, combining the functionality from conversation_context_builder.py, image_input_example.py, and configurable_openai_assistant.py.
"""

import asyncio
import os
import json
import hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from openai import OpenAI

# Import from our project
from app.aicore.core.configurable_openai_assistant import ConfigurableOpenAIAssistant
from app.aicore.config import AIConfig, config_manager
from app.logging.logger import get_logger

logger = get_logger(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))
test_image_folder = os.path.join(current_dir, "test_images")
file_cache_path = os.path.join(test_image_folder, "openai_file_cache.json")

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

class OpenAIFileCache:
    """
    Manages caching of OpenAI file IDs to avoid re-uploading the same images.
    Stores mappings in a JSON file and validates existing file IDs.
    """
    
    def __init__(self, cache_path: str, openai_client: OpenAI):
        self.cache_path = cache_path
        self.client = openai_client
        self.cache_data = self._load_cache()
    
    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        """Load the file cache from JSON file"""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load cache file: {e}. Starting with empty cache.")
        return {}
    
    def _save_cache(self):
        """Save the file cache to JSON file"""
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, 'w') as f:
                json.dump(self.cache_data, f, indent=2)
            logger.info(f"Cache saved to {self.cache_path}")
        except IOError as e:
            logger.error(f"Failed to save cache: {e}")
    
    def _get_file_hash(self, file_path: str) -> str:
        """Generate a hash for the file to detect changes"""
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
                return hashlib.md5(file_content).hexdigest()
        except IOError as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return ""
    
    def _validate_file_id(self, file_id: str) -> bool:
        """Validate that a file ID still exists on OpenAI"""
        try:
            file_obj = self.client.files.retrieve(file_id)
            # Check if file is in a valid state
            return file_obj.status in ['uploaded', 'processed'] and not getattr(file_obj, 'deleted', False)
        except Exception as e:
            logger.warning(f"File ID {file_id} validation failed: {e}")
            return False
    
    def get_cached_file_id(self, file_path: str) -> Optional[str]:
        """Get cached file ID for an image if it exists and is valid"""
        file_key = os.path.basename(file_path)
        
        if file_key not in self.cache_data:
            return None
        
        cached_entry = self.cache_data[file_key]
        current_hash = self._get_file_hash(file_path)
        
        # Check if file has changed
        if cached_entry.get('file_hash') != current_hash:
            logger.info(f"File {file_key} has changed, cache invalidated")
            return None
        
        file_id = cached_entry.get('file_id')
        if not file_id:
            return None
        
        # Validate the file ID still exists on OpenAI
        if self._validate_file_id(file_id):
            logger.info(f"Using cached file ID {file_id} for {file_key}")
            return file_id
        else:
            logger.info(f"Cached file ID {file_id} for {file_key} is no longer valid")
            # Remove invalid entry
            del self.cache_data[file_key]
            self._save_cache()
            return None
    
    def cache_file_id(self, file_path: str, file_id: str):
        """Cache a file ID for future use"""
        file_key = os.path.basename(file_path)
        file_hash = self._get_file_hash(file_path)
        
        self.cache_data[file_key] = {
            'file_id': file_id,
            'file_hash': file_hash,
            'file_path': file_path,
            'created_at': str(asyncio.get_event_loop().time())
        }
        self._save_cache()
        logger.info(f"Cached file ID {file_id} for {file_key}")

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
            MockMessage("user", "Hello! how are you?"),
            MockMessage("assistant", "I am good, thank you! How can I help you today?"),
            MockMessage("user", "I am looking for a good sci-fi movie to watch. Can you help me with that?"),
            MockMessage("assistant", "Sure, I can help you with that. What is your budget and what type of movie do you prefer?"),
            MockMessage("user", "I am looking for a budget movie to watch. I prefer a movie with a lot of action and adventure."),
            MockMessage("assistant", "I suggest you watch The Dark Knight. It is a great movie with a lot of action and adventure."),
        ]
        
    async def build_context(self, latest_user_message: str, file_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
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
            
        # Build the latest user message (with images)
        if file_ids and len(file_ids) > 0:
            # Create multimodal message with multiple images
            content_parts = [{"type": "input_text", "text": latest_user_message}]
            
            # Add multiple image entries
            for file_id in file_ids:
                content_parts.append({"type": "input_image", "file_id": file_id})
            
            latest_message = {
                "role": "user",
                "content": content_parts
            }
        else:
            # Text-only message
            latest_message = {
                "role": "user", 
                "content": latest_user_message
            }
            
        context_messages.append(latest_message)
        
        logger.info(f"Context built: {len(context_messages)} messages, images_included={len(file_ids) if file_ids else 0}")
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
        self.file_cache = OpenAIFileCache(file_cache_path, self.client)
        self.context_builder = MockContextBuilder(
            MockContextConfig(), 
            conversation_id="test-conv-123"
        )
        
    async def create_image_file(self, image_path: str) -> str:
        """Create a file using OpenAI Files API for vision, with caching"""
        # Check cache first
        cached_file_id = self.file_cache.get_cached_file_id(image_path)
        if cached_file_id:
            return cached_file_id
        
        # Upload new file
        try:
            with open(image_path, "rb") as file_content:
                result = self.client.files.create(
                    file=file_content,
                    purpose="vision"
                )
                file_id = result.id
                logger.info(f"Created new file with ID: {file_id} for {image_path}")
                
                # Cache the new file ID
                self.file_cache.cache_file_id(image_path, file_id)
                return file_id
        except Exception as e:
            logger.error(f"Failed to create file for {image_path}: {e}")
            raise e
        
    async def create_multiple_image_files(self, image_paths: List[str]) -> List[str]:
        """Create multiple files using OpenAI Files API for vision with caching"""
        file_ids = []
        cached_count = 0
        uploaded_count = 0
        
        for image_path in image_paths:
            try:
                # Check if we have a cached file ID first
                cached_file_id = self.file_cache.get_cached_file_id(image_path)
                if cached_file_id:
                    file_ids.append(cached_file_id)
                    cached_count += 1
                    logger.info(f"Using cached file ID for {os.path.basename(image_path)}")
                else:
                    # Upload new file
                    file_id = await self.create_image_file(image_path)
                    file_ids.append(file_id)
                    uploaded_count += 1
                    logger.info(f"Uploaded new file for {os.path.basename(image_path)}")
            except Exception as e:
                logger.error(f"Failed to process file {image_path}: {e}")
                # Continue with other images even if one fails
                continue
        
        logger.info(f"File processing complete: {cached_count} cached, {uploaded_count} uploaded, {len(file_ids)} total ready")
        return file_ids
        
    async def create_and_run_agent_with_images(self, image_paths: List[str], user_message: str):
        """Create an agent with multiple images and run it with a user message"""
        file_ids = await self.create_multiple_image_files(image_paths)
        
        if not file_ids:
            logger.error("No files were successfully processed")
            return
            
        context = await self.context_builder.build_context(user_message, file_ids)
        
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
        
    def cleanup_cache(self):
        """Clean up invalid entries from cache"""
        logger.info("Starting cache cleanup...")
        invalid_entries = []
        
        for file_key, entry in self.file_cache.cache_data.items():
            file_id = entry.get('file_id')
            if file_id and not self.file_cache._validate_file_id(file_id):
                invalid_entries.append(file_key)
        
        for file_key in invalid_entries:
            del self.file_cache.cache_data[file_key]
            logger.info(f"Removed invalid cache entry: {file_key}")
        
        if invalid_entries:
            self.file_cache._save_cache()
            logger.info(f"Cache cleanup complete: removed {len(invalid_entries)} invalid entries")
        else:
            logger.info("Cache cleanup complete: no invalid entries found")
    
async def main():
    """Main test runner"""
    print("🚀 Starting Context Building with Multiple Images Test Suite (with caching)")
    
    # Get available test images from test_images folder
    test_images = []
    if os.path.exists(test_image_folder):
        for filename in os.listdir(test_image_folder):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_path = os.path.join(test_image_folder, filename)
                test_images.append(image_path)
                print(f"Found test image: {filename}")
    
    if not test_images:
        print(f"❌ No test images found in {test_image_folder}")
        return
    
    # Validate images
    valid_images = []
    try:
        from PIL import Image
        for image_path in test_images:
            try:
                with Image.open(image_path) as img:
                    img.verify()  # This will raise an exception if invalid
                valid_images.append(image_path)
                print(f"✅ Image validation passed: {os.path.basename(image_path)}")
            except Exception as e:
                print(f"❌ Invalid image file: {os.path.basename(image_path)} - Error: {e}")
    except ImportError:
        print("⚠️  PIL not available, skipping image validation")
        valid_images = test_images
    
    if not valid_images:
        print("❌ No valid images found")
        return
    
    from tests.ai_config import validate_api_keys
    validate_api_keys()

    test_suite = ImageContextTestSuite()
    
    # Clean up any invalid cache entries first
    test_suite.cleanup_cache()
    
    # Test with multiple images (limit to first 3 to avoid too many API calls)
    selected_images = valid_images[:3]
    print(f"\n🖼️  Testing with {len(selected_images)} images: {[os.path.basename(img) for img in selected_images]}")
    print(f"📁 Cache file location: {file_cache_path}")
    
    # Test: Context building with multiple images
    await test_suite.create_and_run_agent_with_images(
        image_paths=selected_images,
        user_message="Tell me everything we have discussed so far. Also, what do you see in these images? Please describe each image in detail."
    )
    
    print("\n✅ All tests completed!")
    print(f"💾 File cache saved at: {file_cache_path}")

if __name__ == "__main__":
    asyncio.run(main()) 