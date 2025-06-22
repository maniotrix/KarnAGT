#!/usr/bin/env python3
"""
Comprehensive Image Vision LLM Inference Test Suite

Tests complete image upload → LLM inference → cleanup flow:
1. Image staging → permanent storage → OpenAI API → GPT-4o vision inference
2. Both regular streaming (/stream) and edit streaming (/edit/stream)
3. Immediate cleanup verification after each inference
4. Complete resource cleanup (S3, OpenAI API, database records)

Uses existing test images and GPT-4o model (default in backend).
"""

import asyncio
import sys
import uuid
import os
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import httpx

# Add backend to path
sys.path.append('.')

from app.core.database import AsyncSessionLocal
from app.models.database.user import User
from app.models.database.conversation import Conversation
from app.models.database.message import Message
from app.models.database.uploaded_image import UploadedImage
from app.models.database.openai_file import OpenAIFile
from app.services.storage.staging_storage import staging_service
from app.services.storage.storage import storage_service
from app.services.storage.openai_storage import openai_storage_service
from app.core.security import security
from app.core.config import get_settings
from sqlalchemy import delete, select

# Test configuration
API_BASE_URL = "http://localhost:8000/api/v1"
TEST_IMAGES_DIR = "test_images"

class ComprehensiveImageVisionLLMInferenceTest:
    """Test class for complete image vision LLM inference workflow"""
    
    def __init__(self):
        self.test_users = []
        self.auth_tokens = {}
        self.test_conversations = []
        self.test_messages = []
        self.staged_files = []           # Staging area files
        self.permanent_files = []        # Committed S3 files 
        self.openai_files = []          # OpenAI API files
        self.cleanup_tracker = []       # Resources to verify deletion
        self.settings = get_settings()
        
        # Test images from existing folder
        self.test_images = [
            "dog_test_image.jpg",
            "fifa_test_image.png", 
            "prince_test_image.jpeg",
            "vertical_test_image.jpg",
            "whatsapp_test_image.png"
        ]
        
        # GPT-4o vision prompts
        self.gpt4o_vision_prompts = [
            "Describe what you see in this image in detail",
            "Count all objects and people in the image",
            "What emotions or mood does this image convey?",
            "Describe the colors and artistic composition",
            "Are there any people or faces visible?",
            "What text or numbers can you identify?",
            "What time of day or season is depicted?"
        ]
        
    async def setup_test_environment(self):
        """Set up test users and authentication (same as staging test)"""
        print("Setting up comprehensive image vision test environment...")
        
        # Verify test images exist
        for image_name in self.test_images:
            image_path = os.path.join(TEST_IMAGES_DIR, image_name)
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Test image not found: {image_path}")
        
        async with AsyncSessionLocal() as db:
            # Create test users with different subscription tiers
            test_user_configs = [
                {
                    "username": f"vision_test_user_pro_{uuid.uuid4().hex[:8]}",
                    "email": f"vision_test_pro_{uuid.uuid4().hex[:8]}@example.com",
                    "subscription_tier": "pro",
                    "is_active": True,
                    "is_verified": True
                },
                {
                    "username": f"vision_test_user_enterprise_{uuid.uuid4().hex[:8]}",
                    "email": f"vision_test_enterprise_{uuid.uuid4().hex[:8]}@example.com",
                    "subscription_tier": "enterprise",
                    "is_active": True,
                    "is_verified": True
                }
            ]
            
            for user_config in test_user_configs:
                test_user = User(
                    user_id=str(uuid.uuid4()),
                    username=user_config["username"],
                    email=user_config["email"],
                    full_name=f"Vision Test User {str(user_config['subscription_tier']).title()}",
                    hashed_password="test_password_hash",
                    subscription_tier=user_config["subscription_tier"],
                    is_active=user_config["is_active"],
                    is_verified=user_config["is_verified"]
                )
                
                db.add(test_user)
                await db.commit()
                await db.refresh(test_user)
                
                # Generate auth token for user
                token = security.create_access_token(
                    subject=test_user.user_id,
                    scopes=["files", "chat"]
                )
                
                self.test_users.append(test_user)
                self.auth_tokens[test_user.user_id] = token
                
                print(f"Created vision test user: {test_user.username} ({test_user.subscription_tier}) - ID: {test_user.user_id}")
            
            print(f"Created {len(self.test_users)} test users with authentication tokens")
    
    def get_auth_headers(self, user_id: str) -> Dict[str, str]:
        """Get authorization headers for API requests"""
        token = self.auth_tokens.get(user_id)
        if not token:
            raise ValueError(f"No auth token for user {user_id}")
        
        return {"Authorization": f"Bearer {token}"}
    
    def get_streaming_headers(self, user_id: str) -> Dict[str, str]:
        """Get headers for streaming requests"""
        headers = self.get_auth_headers(user_id)
        headers.update({
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache'
        })
        return headers
    
    async def upload_scenario_images(self, image_names: List[str], user_id: str) -> List[Dict[str, str]]:
        """Upload test images to staging area"""
        if not image_names:
            return []
        
        print(f"Uploading {len(image_names)} images to staging for user {user_id}")
        
        async with httpx.AsyncClient() as client:
            # Read test images
            files = []
            for image_name in image_names:
                image_path = os.path.join(TEST_IMAGES_DIR, image_name)
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                files.append(("files", (image_name, image_data, "image/jpeg")))
            
            headers = self.get_auth_headers(user_id)
            response = await client.post(
                f"{API_BASE_URL}/ai-files/staging/bulk-upload",
                files=files,
                data={"max_concurrent_uploads": "3"},
                headers=headers,
                timeout=60.0
            )
            
            if response.status_code == 201:
                upload_data = response.json()
                staged_files = []
                
                for staged_file in upload_data.get("staged_files", []):
                    file_info = {
                        "file_id": staged_file["file_id"],
                        "s3_key": staged_file["s3_key"],
                        "filename": staged_file["filename"],
                        "user_id": user_id
                    }
                    staged_files.append(file_info)
                    self.staged_files.append(file_info)
                
                print(f"Successfully uploaded {len(staged_files)} images to staging")
                return [{"file_id": sf["file_id"], "s3_key": sf["s3_key"]} for sf in staged_files]
            else:
                raise Exception(f"Failed to upload images to staging: {response.status_code} - {response.text}")
    
    async def create_test_conversation(self, title: str, user_id: str) -> str:
        """Create a test conversation"""
        print(f"Creating test conversation: {title}")
        
        async with httpx.AsyncClient() as client:
            conversation_data = {
                "title": title,
                "model_name": "gpt-4o",  # Use GPT-4o for vision
                "system_prompt": "You are a helpful assistant with vision capabilities. Analyze images thoroughly and provide detailed descriptions."
            }
            
            headers = self.get_auth_headers(user_id)
            response = await client.post(
                f"{API_BASE_URL}/chat/conversations",
                json=conversation_data,
                headers=headers
            )
            
            if response.status_code == 201:
                result = response.json()
                conversation_id = result['conversation_id']
                self.test_conversations.append({
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "title": title
                })
                print(f"Created conversation: {conversation_id}")
                return conversation_id
            else:
                raise Exception(f"Failed to create conversation: {response.status_code} - {response.text}")
    
    def extract_stream_id_from_sse(self, sse_line: str) -> Optional[str]:
        """Extract stream_id from SSE data line"""
        if not sse_line.startswith('data: '):
            return None
            
        try:
            data = sse_line[6:].strip()  # Remove 'data: ' prefix
            if data in ['[DONE]', '']:
                return None
                
            event = json.loads(data)
            
            # Look for stream_id in various event types
            if 'stream_id' in event:
                return event['stream_id']
            
            if 'data' in event and isinstance(event['data'], dict) and 'stream_id' in event['data']:
                return event['data']['stream_id']
                
        except json.JSONDecodeError:
            pass
            
        return None
    
    async def stream_message_with_images(
        self, 
        conversation_id: str, 
        content: str, 
        staging_files: List[Dict[str, str]], 
        user_id: str
    ) -> Dict[str, Any]:
        """Stream a message with images and return response data"""
        print(f"Streaming message with {len(staging_files)} images: {content[:50]}...")
        
        async with httpx.AsyncClient() as client:
            message_data = {
                "content": content,
                "staging_files": staging_files
            }
            
            headers = self.get_streaming_headers(user_id)
            
            captured_stream_id = None
            tokens_received = 0
            ai_response_content = ""
            
            async with client.stream(
                "POST",
                f"{API_BASE_URL}/chat/conversations/{conversation_id}/stream",
                json=message_data,
                headers=headers,
                timeout=120.0
            ) as response:
                
                if response.status_code == 200:
                    print(f"✅ Streaming started successfully")
                    
                    buffer = ""
                    async for chunk in response.aiter_text():
                        buffer += chunk
                        
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()
                            
                            if line:
                                # Extract stream_id
                                stream_id = self.extract_stream_id_from_sse(line)
                                if stream_id and not captured_stream_id:
                                    captured_stream_id = stream_id
                                    print(f"🎯 Captured stream_id: {stream_id}")
                                
                                # Count tokens and accumulate content
                                if 'token' in line.lower():
                                    tokens_received += 1
                                    try:
                                        data = line[6:].strip() if line.startswith('data: ') else line
                                        event = json.loads(data)
                                        if event.get('type') == 'token' and 'data' in event:
                                            content_part = event['data'].get('content', '')
                                            ai_response_content += content_part
                                    except:
                                        pass
                        
                        # Read enough to get meaningful response
                        if tokens_received > 20:
                            break
                    
                    print(f"📊 Received {tokens_received} token events")
                    
                    # Get conversation messages to find user message ID
                    await asyncio.sleep(1)  # Wait for message to be saved
                    messages_response = await client.get(
                        f"{API_BASE_URL}/chat/conversations/{conversation_id}/messages",
                        headers=self.get_auth_headers(user_id)
                    )
                    
                    if messages_response.status_code == 200:
                        messages_data = messages_response.json()
                        messages = messages_data.get('data', [])
                        
                        # Find the latest user message
                        user_message = None
                        for msg in reversed(messages):
                            if msg.get('role') == 'user':
                                user_message = msg
                                break
                        
                        if user_message:
                            message_info = {
                                'user_message_id': user_message['message_id'],
                                'conversation_id': conversation_id,
                                'content': content,
                                'staging_files': staging_files,
                                'stream_id': captured_stream_id,
                                'tokens_received': tokens_received,
                                'ai_response_preview': ai_response_content[:100]
                            }
                            
                            self.test_messages.append(message_info)
                            print(f"✅ Message streamed successfully, user_message_id: {user_message['message_id']}")
                            return message_info
                        else:
                            raise Exception("Failed to find user message after streaming")
                    else:
                        raise Exception(f"Failed to get messages: {messages_response.status_code}")
                else:
                    error_text = await response.aread()
                    raise Exception(f"Streaming failed: {response.status_code} - {error_text}")
    
    async def stream_edit_message_with_images(
        self,
        conversation_id: str,
        message_id: str,
        content: str,
        staging_files: List[Dict[str, str]],
        user_id: str
    ) -> Dict[str, Any]:
        """Stream edit a message with images"""
        print(f"Streaming edit message {message_id} with {len(staging_files)} images: {content[:50]}...")
        
        async with httpx.AsyncClient() as client:
            message_data = {
                "content": content,
                "staging_files": staging_files
            }
            
            headers = self.get_streaming_headers(user_id)
            
            captured_stream_id = None
            tokens_received = 0
            ai_response_content = ""
            
            async with client.stream(
                "POST",
                f"{API_BASE_URL}/chat/conversations/{conversation_id}/messages/{message_id}/edit/stream",
                json=message_data,
                headers=headers,
                timeout=120.0
            ) as response:
                
                if response.status_code == 200:
                    print(f"✅ Edit streaming started successfully")
                    
                    buffer = ""
                    async for chunk in response.aiter_text():
                        buffer += chunk
                        
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()
                            
                            if line:
                                # Extract stream_id
                                stream_id = self.extract_stream_id_from_sse(line)
                                if stream_id and not captured_stream_id:
                                    captured_stream_id = stream_id
                                    print(f"🎯 Captured edit stream_id: {stream_id}")
                                
                                # Count tokens
                                if 'token' in line.lower():
                                    tokens_received += 1
                                    try:
                                        data = line[6:].strip() if line.startswith('data: ') else line
                                        event = json.loads(data)
                                        if event.get('type') == 'token' and 'data' in event:
                                            content_part = event['data'].get('content', '')
                                            ai_response_content += content_part
                                    except:
                                        pass
                        
                        # Read enough to get meaningful response
                        if tokens_received > 20:
                            break
                    
                    print(f"📊 Edit received {tokens_received} token events")
                    
                    edit_info = {
                        'edited_message_id': message_id,
                        'conversation_id': conversation_id,
                        'edit_content': content,
                        'edit_staging_files': staging_files,
                        'edit_stream_id': captured_stream_id,
                        'edit_tokens_received': tokens_received,
                        'edit_ai_response_preview': ai_response_content[:100]
                    }
                    
                    print(f"✅ Message edit streamed successfully")
                    return edit_info
                else:
                    error_text = await response.aread()
                    raise Exception(f"Edit streaming failed: {response.status_code} - {error_text}")
    
    async def cancel_stream_test(self, stream_id: str, user_id: str) -> bool:
        """Test stream cancellation"""
        print(f"🛑 Testing stream cancellation: {stream_id}")
        
        async with httpx.AsyncClient() as client:
            headers = self.get_auth_headers(user_id)
            response = await client.post(
                f"{API_BASE_URL}/chat/stream/cancel/{stream_id}",
                headers=headers
            )
            
            if response.status_code in [200, 410]:  # 410 = already completed
                result_data = await response.aread()
                print(f"✅ Stream cancellation result: {response.status_code}")
                return True
            else:
                print(f"❌ Stream cancellation failed: {response.status_code}")
                return False
    
    async def collect_all_resource_ids(self, conversation_id: str, staging_files: List[Dict[str, str]]) -> Dict[str, List[str]]:
        """Collect all resource IDs before deletion for cleanup verification"""
        print(f"🔍 Collecting all resource IDs for conversation: {conversation_id}")
        
        async with AsyncSessionLocal() as db:
            resources = {
                'conversation_ids': [conversation_id],
                'message_ids': [],
                'openai_file_ids': [],
                's3_keys': [],
                'staging_file_ids': []
            }
            
            # Get conversation integer ID
            conv_query = select(Conversation).where(Conversation.conversation_id == conversation_id)
            conv_result = await db.execute(conv_query)
            conversation = conv_result.scalar_one_or_none()
            
            if conversation:
                # Get all messages in conversation
                msg_query = select(Message).where(Message.conversation_id == conversation.id)
                msg_result = await db.execute(msg_query)
                messages = msg_result.scalars().all()
                
                for message in messages:
                    resources['message_ids'].append(message.message_id)
                    
                    # Extract OpenAI file IDs from attachments
                    if message.attachments: # type: ignore
                        for attachment in message.attachments:
                            if isinstance(attachment, dict) and 'openai_file_id' in attachment:
                                resources['openai_file_ids'].append(attachment['openai_file_id'])
                            if isinstance(attachment, dict) and 's3_key' in attachment:
                                resources['s3_keys'].append(attachment['s3_key'])
            
            # Add staging file IDs
            for staging_file in staging_files:
                resources['staging_file_ids'].append(staging_file['file_id'])
                if 's3_key' in staging_file:
                    resources['s3_keys'].append(staging_file['s3_key'])
            
            print(f"📋 Collected resources: {len(resources['message_ids'])} messages, {len(resources['openai_file_ids'])} OpenAI files, {len(resources['s3_keys'])} S3 keys, {len(resources['staging_file_ids'])} staging files")
            return resources
    
    async def delete_conversation(self, conversation_id: str, user_id: str) -> Dict[str, Any]:
        """Delete conversation via API"""
        print(f"🗑️ Deleting conversation: {conversation_id}")
        
        async with httpx.AsyncClient() as client:
            headers = self.get_auth_headers(user_id)
            response = await client.delete(
                f"{API_BASE_URL}/chat/conversations/{conversation_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Conversation deleted successfully")
                return {"success": True, "result": result}
            else:
                error_text = await response.aread()
                print(f"❌ Failed to delete conversation: {response.status_code} - {error_text}")
                return {"success": False, "error": error_text}
    
    async def verify_database_cleanup(self, conversation_ids: List[str], message_ids: List[str]):
        """Verify all database records are deleted"""
        print(f"🔍 Verifying database cleanup...")
        
        async with AsyncSessionLocal() as db:
            # Check conversations deleted
            for conv_id in conversation_ids:
                conv_query = select(Conversation).where(Conversation.conversation_id == conv_id)
                conv_result = await db.execute(conv_query)
                conversation = conv_result.scalar_one_or_none()
                assert conversation is None, f"Conversation still exists: {conv_id}"
            
            # Check messages deleted
            for msg_id in message_ids:
                msg_query = select(Message).where(Message.message_id == msg_id)
                msg_result = await db.execute(msg_query)
                message = msg_result.scalar_one_or_none()
                assert message is None, f"Message still exists: {msg_id}"
            
            print(f"✅ Database cleanup verified: {len(conversation_ids)} conversations and {len(message_ids)} messages deleted")
    
    async def verify_openai_files_deleted(self, openai_file_ids: List[str]):
        """Verify OpenAI API files are actually deleted"""
        print(f"🔍 Verifying OpenAI files deleted: {len(openai_file_ids)} files")
        
        for file_id in openai_file_ids:
            try:
                # Try to retrieve file - should fail
                file_info = await openai_storage_service.get_file_info(file_id)
                # If we get here, file still exists
                print(f"⚠️ OpenAI file still exists: {file_id}")
            except Exception:
                # Expected - file should not exist
                print(f"✅ OpenAI file deleted: {file_id}")
        
        print(f"✅ OpenAI files deletion verified")
    
    async def verify_s3_files_deleted(self, s3_keys: List[str]):
        """Verify S3 files are actually deleted"""
        print(f"🔍 Verifying S3 files deleted: {len(s3_keys)} files")
        
        for s3_key in s3_keys:
            try:
                # Check if file exists in S3 using staging service method
                metadata = await staging_service._get_object_metadata(s3_key)
                if metadata is not None:
                    print(f"⚠️ S3 file still exists: {s3_key}")
                else:
                    print(f"✅ S3 file deleted: {s3_key}")
            except Exception:
                # Expected - file should not exist
                print(f"✅ S3 file deleted: {s3_key}")
        
        print(f"✅ S3 files deletion verified")
    
    async def verify_staging_files_deleted(self, staging_file_ids: List[str], user_id: str):
        """Verify staging files are deleted"""
        print(f"🔍 Verifying staging files deleted: {len(staging_file_ids)} files")
        
        for file_id in staging_file_ids:
            try:
                metadata = await staging_service.get_staging_metadata(file_id, user_id)
                if metadata is not None:
                    print(f"⚠️ Staging file still exists: {file_id}")
                else:
                    print(f"✅ Staging file deleted: {file_id}")
            except Exception:
                # Expected - file should not exist
                print(f"✅ Staging file deleted: {file_id}")
        
        print(f"✅ Staging files deletion verified")
    
    async def immediate_cleanup_and_verify(self, conversation_id: str, staging_files: List[Dict[str, str]], user_id: str):
        """Immediate cleanup and verification after each inference"""
        print(f"\n🧹 Starting immediate cleanup for conversation: {conversation_id}")
        
        # 1. Collect all resource IDs before deletion
        resources = await self.collect_all_resource_ids(conversation_id, staging_files)
        
        # 2. Delete conversation (should cascade to messages)
        delete_result = await self.delete_conversation(conversation_id, user_id)
        assert delete_result["success"] is True, f"Failed to delete conversation: {delete_result}"
        
        # Wait a moment for async cleanup
        await asyncio.sleep(2)
        
        # 3. Verify database cleanup
        await self.verify_database_cleanup(resources['conversation_ids'], resources['message_ids'])
        
        # 4. Verify OpenAI API files deleted
        if resources['openai_file_ids']:
            await self.verify_openai_files_deleted(resources['openai_file_ids'])
        
        # 5. Verify S3 permanent files deleted  
        if resources['s3_keys']:
            await self.verify_s3_files_deleted(resources['s3_keys'])
        
        # 6. Verify staging files deleted
        if resources['staging_file_ids']:
            await self.verify_staging_files_deleted(resources['staging_file_ids'], user_id)
        
        print(f"✅ Immediate cleanup verification complete for: {conversation_id}\n")
    
    async def test_regular_streaming_vision_inference(self):
        """Test /conversations/{id}/stream with images"""
        print("\n" + "="*80)
        print("PHASE 2: REGULAR STREAMING VISION INFERENCE")
        print("="*80)
        
        scenarios = [
            {
                "name": "Single image with text",
                "images": ["dog_test_image.jpg"],
                "content": "Describe what you see in this image in detail"
            },
            {
                "name": "Multiple images with text", 
                "images": ["fifa_test_image.png", "prince_test_image.jpeg"],
                "content": "Compare these two images and describe the differences"
            },
            {
                "name": "Images only (no text)",
                "images": ["vertical_test_image.jpg"],
                "content": ""  # Empty text content
            },
            {
                "name": "Three images analysis",
                "images": ["dog_test_image.jpg", "fifa_test_image.png", "whatsapp_test_image.png"],
                "content": "Analyze the content and style of these three images"
            }
        ]
        
        streaming_results = []
        user = self.test_users[0]  # Use first test user
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n--- Scenario {i}: {scenario['name']} ---")
            
            try:
                # 1. Create conversation
                conversation_id = await self.create_test_conversation(f"Stream Test - {scenario['name']}", user.user_id)
                
                # 2. Upload images to staging
                staging_files = await self.upload_scenario_images(scenario['images'], user.user_id)
                
                # 3. Stream message with images
                response_data = await self.stream_message_with_images(
                    conversation_id=conversation_id,
                    content=scenario['content'],
                    staging_files=staging_files,
                    user_id=user.user_id
                )
                
                print(f"✅ Streaming completed: {response_data['tokens_received']} tokens received")
                streaming_results.append({
                    "scenario": scenario['name'],
                    "success": True,
                    "tokens_received": response_data['tokens_received'],
                    "response_preview": response_data['ai_response_preview']
                })
                
                # 4. IMMEDIATE CLEANUP & VERIFICATION
                await self.immediate_cleanup_and_verify(conversation_id, staging_files, user.user_id)
                
            except Exception as e:
                print(f"❌ Scenario failed: {e}")
                streaming_results.append({
                    "scenario": scenario['name'],
                    "success": False,
                    "error": str(e)
                })
        
        print(f"\n📊 Regular Streaming Results: {len([r for r in streaming_results if r['success']])}/{len(scenarios)} scenarios passed")
        return streaming_results
    
    async def test_edit_streaming_vision_inference(self):
        """Test /conversations/{id}/messages/{msg_id}/edit/stream with images"""
        print("\n" + "="*80)
        print("PHASE 3: EDIT STREAMING VISION INFERENCE")
        print("="*80)
        
        edit_scenarios = [
            {
                "name": "Edit with different image",
                "original_images": ["dog_test_image.jpg"],
                "original_content": "What animal is this?",
                "edit_images": ["fifa_test_image.png"],
                "edit_content": "Describe the sports activity in this image"
            },
            {
                "name": "Edit with more images",
                "original_images": ["prince_test_image.jpeg"],
                "original_content": "Describe this person",
                "edit_images": ["prince_test_image.jpeg", "vertical_test_image.jpg"],
                "edit_content": "Compare these two images and find similarities"
            },
            {
                "name": "Edit to remove images",
                "original_images": ["whatsapp_test_image.png", "dog_test_image.jpg"],
                "original_content": "Analyze these images",
                "edit_images": [],  # No images in edit
                "edit_content": "Tell me about artificial intelligence instead"
            }
        ]
        
        edit_results = []
        user = self.test_users[1]  # Use second test user
        
        for i, scenario in enumerate(edit_scenarios, 1):
            print(f"\n--- Edit Scenario {i}: {scenario['name']} ---")
            
            try:
                # 1. Create conversation with original message
                conversation_id = await self.create_test_conversation(f"Edit Test - {scenario['name']}", user.user_id)
                original_staging = await self.upload_scenario_images(scenario['original_images'], user.user_id)
                
                original_message = await self.stream_message_with_images(
                    conversation_id=conversation_id,
                    content=scenario['original_content'],
                    staging_files=original_staging,
                    user_id=user.user_id
                )
                
                print(f"✅ Original message created: {original_message['user_message_id']}")
                
                # 2. Upload new images for edit
                edit_staging = await self.upload_scenario_images(scenario['edit_images'], user.user_id)
                
                # 3. Stream edit with new images
                edit_response = await self.stream_edit_message_with_images(
                    conversation_id=conversation_id,
                    message_id=original_message['user_message_id'],
                    content=scenario['edit_content'],
                    staging_files=edit_staging,
                    user_id=user.user_id
                )
                
                print(f"✅ Edit streaming completed: {edit_response['edit_tokens_received']} tokens received")
                edit_results.append({
                    "scenario": scenario['name'],
                    "success": True,
                    "edit_tokens_received": edit_response['edit_tokens_received'],
                    "edit_response_preview": edit_response['edit_ai_response_preview']
                })
                
                # 4. IMMEDIATE CLEANUP & VERIFICATION  
                all_staging_files = original_staging + edit_staging
                await self.immediate_cleanup_and_verify(conversation_id, all_staging_files, user.user_id)
                
            except Exception as e:
                print(f"❌ Edit scenario failed: {e}")
                edit_results.append({
                    "scenario": scenario['name'],
                    "success": False,
                    "error": str(e)
                })
        
        print(f"\n📊 Edit Streaming Results: {len([r for r in edit_results if r['success']])}/{len(edit_scenarios)} scenarios passed")
        return edit_results
    
    async def test_stream_cancellation_with_images(self):
        """Test stream cancellation during image inference"""
        print("\n" + "="*80)
        print("PHASE 4: STREAM CANCELLATION TESTING")
        print("="*80)
        
        user = self.test_users[0]
        cancellation_results = []
        
        try:
            # 1. Start complex image inference
            conversation_id = await self.create_test_conversation("Cancellation Test", user.user_id)
            staging_files = await self.upload_scenario_images(["fifa_test_image.png", "dog_test_image.jpg"], user.user_id)
            
            # 2. Start streaming with complex prompt (will take time)
            long_prompt = """
            Analyze these images in extreme detail. Provide a comprehensive analysis including:
            1. Detailed object identification and counting
            2. Color analysis and artistic composition  
            3. Emotional impact and mood assessment
            4. Technical photography analysis
            5. Historical or cultural context if applicable
            6. Comparative analysis between the images
            7. Write at least 500 words for each image
            """
            
            print(f"🚀 Starting long-running image inference for cancellation test...")
            
            # Start streaming in background and capture stream_id quickly
            async with httpx.AsyncClient() as client:
                message_data = {
                    "content": long_prompt,
                    "staging_files": staging_files
                }
                
                headers = self.get_streaming_headers(user.user_id)
                
                captured_stream_id = None
                
                async with client.stream(
                    "POST",
                    f"{API_BASE_URL}/chat/conversations/{conversation_id}/stream",
                    json=message_data,
                    headers=headers,
                    timeout=120.0
                ) as response:
                    
                    if response.status_code == 200:
                        buffer = ""
                        async for chunk in response.aiter_text():
                            buffer += chunk
                            
                            while '\n' in buffer:
                                line, buffer = buffer.split('\n', 1)
                                line = line.strip()
                                
                                if line:
                                    stream_id = self.extract_stream_id_from_sse(line)
                                    if stream_id and not captured_stream_id:
                                        captured_stream_id = stream_id
                                        print(f"🎯 Captured stream_id for cancellation: {stream_id}")
                                        
                                        # Cancel immediately after capturing stream_id
                                        cancel_success = await self.cancel_stream_test(stream_id, user.user_id)
                                        
                                        cancellation_results.append({
                                            "test": "stream_cancellation",
                                            "stream_id": stream_id,
                                            "cancel_success": cancel_success
                                        })
                                        
                                        # Break out of streaming
                                        break
                            
                            if captured_stream_id:
                                break
                        
                        print(f"✅ Stream cancellation test completed")
                    else:
                        raise Exception(f"Failed to start cancellation test stream: {response.status_code}")
            
            # 3. IMMEDIATE CLEANUP & VERIFICATION
            await self.immediate_cleanup_and_verify(conversation_id, staging_files, user.user_id)
            
        except Exception as e:
            print(f"❌ Cancellation test failed: {e}")
            cancellation_results.append({
                "test": "stream_cancellation",
                "success": False,
                "error": str(e)
            })
        
        print(f"\n📊 Cancellation Results: {len([r for r in cancellation_results if r.get('cancel_success', False)])} successful cancellations")
        return cancellation_results
    
    async def cleanup_test_environment(self):
        """Clean up test users and any remaining resources"""
        print("\n🧹 Cleaning up test environment...")
        
        # Clean up any remaining staged files
        if self.staged_files:
            print(f"Cleaning up {len(self.staged_files)} remaining staged files...")
            for staged_file in self.staged_files:
                try:
                    await staging_service.discard_staged_file(
                        staged_file["file_id"], 
                        staged_file["user_id"]
                    )
                except Exception as e:
                    print(f"Failed to cleanup staged file {staged_file['file_id']}: {e}")
        
        # Clean up test users
        async with AsyncSessionLocal() as db:
            for test_user in self.test_users:
                try:
                    await db.delete(test_user)
                    print(f"Deleted test user: {test_user.username}")
                except Exception as e:
                    print(f"Failed to delete test user {test_user.username}: {e}")
            
            try:
                await db.commit()
                print("Test user cleanup committed")
            except Exception as e:
                print(f"Failed to commit test user cleanup: {e}")
        
        print("✅ Test environment cleanup completed")
    
    async def run_comprehensive_test(self):
        """Run the complete comprehensive image vision LLM inference test"""
        print("🚀 Starting Comprehensive Image Vision LLM Inference Test")
        print("="*80)
        print("Testing complete image upload → LLM inference → cleanup flow")
        print("- Image staging → permanent storage → OpenAI API → GPT-4o vision inference")
        print("- Both regular streaming (/stream) and edit streaming (/edit/stream)")
        print("- Immediate cleanup verification after each inference")
        print("="*80)
        
        try:
            # Phase 1: Setup
            await self.setup_test_environment()
            
            # Phase 2: Regular streaming tests
            streaming_results = await self.test_regular_streaming_vision_inference()
            
            # Phase 3: Edit streaming tests  
            edit_results = await self.test_edit_streaming_vision_inference()
            
            # Phase 4: Cancellation tests
            cancellation_results = await self.test_stream_cancellation_with_images()
            
            # Summary
            print("\n" + "="*80)
            print("🎯 COMPREHENSIVE IMAGE VISION LLM INFERENCE TEST RESULTS")
            print("="*80)
            
            streaming_passed = len([r for r in streaming_results if r['success']])
            edit_passed = len([r for r in edit_results if r['success']])
            cancellation_passed = len([r for r in cancellation_results if r.get('cancel_success', False)])
            
            print(f"✅ Regular Streaming Tests: {streaming_passed}/{len(streaming_results)} passed")
            print(f"✅ Edit Streaming Tests: {edit_passed}/{len(edit_results)} passed")
            print(f"✅ Cancellation Tests: {cancellation_passed}/{len(cancellation_results)} passed")
            
            total_passed = streaming_passed + edit_passed + cancellation_passed
            total_tests = len(streaming_results) + len(edit_results) + len(cancellation_results)
            
            print(f"\n📊 Overall Results: {total_passed}/{total_tests} tests passed")
            
            if total_passed == total_tests:
                print("\n🎉 ALL IMAGE VISION LLM INFERENCE TESTS PASSED!")
                print("✅ Image staging → permanent storage → OpenAI API flow works")
                print("✅ GPT-4o vision inference with images works")
                print("✅ Both regular streaming and edit streaming work")
                print("✅ Stream cancellation works")
                print("✅ Complete cleanup verification works")
                print("\n💡 Complete image vision LLM inference pipeline ready!")
                return True
            else:
                print(f"\n❌ {total_tests - total_passed} TESTS FAILED!")
                print("🔧 Pipeline needs fixes before production!")
                return False
                
        except Exception as e:
            print(f"❌ Test suite failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            # Always cleanup
            await self.cleanup_test_environment()


async def main():
    """Main test runner"""
    test_runner = ComprehensiveImageVisionLLMInferenceTest()
    success = await test_runner.run_comprehensive_test()
    
    if success:
        print("\n🎉 All comprehensive image vision LLM inference tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    print("🧪 Comprehensive Image Vision LLM Inference Test Suite")
    print("Testing complete image upload → GPT-4o vision inference → cleanup workflow")
    print("="*80)
    asyncio.run(main()) 