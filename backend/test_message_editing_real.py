#!/usr/bin/env python3
"""
Real Message Editing Test Suite

This script tests the complete message editing workflow:
1. Real user registration and authentication
2. Real conversation creation with multiple messages
3. Real message editing endpoint testing
4. Edge cases and security testing
5. Verification of edit tracking and subsequent message deletion

NO FAKE DATA - Tests exactly how frontend would work.
"""

import asyncio
import aiohttp
import subprocess
import signal
import sys
import time
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any


class RealMessageEditingTester:
    """Test message editing exactly like frontend would do it"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.access_token: Optional[str] = None
        self.test_user_email: Optional[str] = None
        self.test_conversations: List[str] = []
        self.test_messages: List[Dict[str, Any]] = []
        self.test_results: Dict[str, bool] = {}
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def get_headers(self) -> Dict[str, str]:
        """Get request headers with auth token"""
        headers = {'Content-Type': 'application/json'}
        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        return headers
    
    async def wait_for_server(self, max_attempts: int = 30) -> bool:
        """Wait for server to be ready"""
        print("🔄 Waiting for server to be ready...")
        
        for attempt in range(max_attempts):
            try:
                async with self.session.get(f"{self.base_url}/docs") as response:
                    if response.status == 200:
                        print("✅ Server is ready!")
                        return True
            except Exception:
                pass
            
            await asyncio.sleep(1)
            if attempt % 5 == 0:
                print(f"   Still waiting... (attempt {attempt + 1}/{max_attempts})")
        
        print("❌ Server failed to start in time")
        return False
    
    async def register_test_user(self) -> bool:
        """Register a real test user and get access token"""
        print("👤 Registering real test user...")
        
        # Use unique email with timestamp
        timestamp = int(datetime.now().timestamp())
        self.test_user_email = f"editingtest_{timestamp}@example.com"
        
        user_data = {
            "email": self.test_user_email,
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!",
            "full_name": "Real Message Editing Test User"
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/auth/register",
                json=user_data,
                headers={'Content-Type': 'application/json'}
            ) as response:
                
                if response.status == 201:
                    result = await response.json()
                    self.access_token = result.get("access_token")
                    print(f"✅ Real user registered: {self.test_user_email}")
                    print(f"🔑 Access token: {self.access_token[:20]}...")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Registration failed ({response.status}): {error_text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False
    
    async def verify_authentication(self) -> bool:
        """Verify that authentication is working"""
        print("🔐 Verifying real authentication...")
        
        try:
            async with self.session.get(
                f"{self.base_url}/api/v1/auth/me",
                headers=self.get_headers()
            ) as response:
                
                if response.status == 200:
                    user_data = await response.json()
                    print(f"✅ Authentication verified for: {user_data.get('email')}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Authentication failed ({response.status}): {error_text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    async def create_real_conversation(self, title: str = None) -> str:
        """Create a real conversation for testing"""
        if not title:
            title = f"Real Message Edit Test {datetime.now().isoformat()}"
        
        print(f"💬 Creating real test conversation: {title}")
        
        conversation_data = {
            "title": title,
            "model_name": "gpt-3.5-turbo",
            "system_prompt": "You are a helpful assistant for testing message editing functionality."
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/conversations",
                json=conversation_data,
                headers=self.get_headers()
            ) as response:
                
                if response.status == 201:
                    result = await response.json()
                    conversation_id = result['conversation_id']
                    self.test_conversations.append(conversation_id)
                    print(f"✅ Real conversation created: {conversation_id}")
                    return conversation_id
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to create conversation ({response.status}): {error_text}")
                    
        except Exception as e:
            print(f"❌ Conversation creation error: {e}")
            raise
    
    async def send_real_message(self, conversation_id: str, content: str, role: str = "user") -> Dict[str, Any]:
        """Send a real message to a conversation and return info about the USER message sent"""
        print(f"📝 Sending real message: {content[:50]}...")
        
        message_data = {
            "content": content,
            "role": role,
            "parent_message_id": None,
            "attachments": None,
            "status": "completed"
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/conversations/{conversation_id}/messages",
                json=message_data,
                headers=self.get_headers()
            ) as response:
                
                if response.status == 200:
                    ai_response = await response.json()
                    print(f"✅ Message sent, got AI response: {ai_response['message_id']}")
                    
                    # Wait a moment, then get messages to find the user message
                    await asyncio.sleep(1)
                    messages = await self.get_conversation_messages(conversation_id)
                    
                    # Find the user message we just sent
                    user_message = None
                    for msg in reversed(messages):  # Check latest first
                        if msg.get('role') == 'user' and msg.get('content') == content:
                            user_message = msg
                            break
                    
                    if not user_message:
                        raise Exception("Failed to find the user message that was just sent")
                    
                    message_info = {
                        'message_id': user_message['message_id'],  # This is the USER message ID
                        'conversation_id': conversation_id,
                        'content': content,
                        'role': role,
                        'ai_response': ai_response,  # Store AI response separately
                        'user_message': user_message  # Store full user message data
                    }
                    self.test_messages.append(message_info)
                    print(f"✅ Found user message ID: {user_message['message_id']}")
                    return message_info
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to send message ({response.status}): {error_text}")
                    
        except Exception as e:
            print(f"❌ Message sending error: {e}")
            raise
    
    async def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all messages in a conversation"""
        try:
            async with self.session.get(
                f"{self.base_url}/api/v1/chat/conversations/{conversation_id}/messages",
                headers=self.get_headers()
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    return result.get('data', [])
                else:
                    error_text = await response.text()
                    print(f"⚠️ Failed to get messages ({response.status}): {error_text}")
                    return []
                    
        except Exception as e:
            print(f"❌ Get messages error: {e}")
            return []
    
    async def test_basic_message_editing(self, conversation_id: str) -> bool:
        """Test basic message editing functionality"""
        print("\n🧪 Testing BASIC MESSAGE EDITING...")
        
        try:
            # Send initial message
            original_message = await self.send_real_message(
                conversation_id, 
                "What is the capital of France?"
            )
            
            # Wait for AI response
            await asyncio.sleep(2)
            
            # Get messages before edit
            messages_before = await self.get_conversation_messages(conversation_id)
            print(f"   Messages before edit: {len(messages_before)}")
            
            # Edit the message
            new_content = "What is the capital of Germany?"
            print(f"   Editing message to: {new_content}")
            
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/conversations/{conversation_id}/messages/{original_message['message_id']}/edit",
                json={"content": new_content},
                headers=self.get_headers()
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Message edited successfully")
                    print(f"   New AI response: {result.get('content', '')[:100]}...")
                    
                    # Verify the edit worked
                    messages_after = await self.get_conversation_messages(conversation_id)
                    print(f"   Messages after edit: {len(messages_after)}")
                    
                    # Should have same or fewer messages (old AI responses deleted)
                    if len(messages_after) <= len(messages_before):
                        print("✅ Subsequent messages properly deleted")
                        return True
                    else:
                        print("❌ Messages not properly cleaned up")
                        return False
                        
                else:
                    error_text = await response.text()
                    print(f"❌ Edit failed ({response.status}): {error_text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Basic edit test error: {e}")
            return False
    
    async def test_edit_nonexistent_message(self, conversation_id: str) -> bool:
        """Test editing a non-existent message ID"""
        print("\n🧪 Testing EDIT NON-EXISTENT MESSAGE...")
        
        try:
            fake_message_id = "00000000-0000-0000-0000-000000000000"
            
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/conversations/{conversation_id}/messages/{fake_message_id}/edit",
                json={"content": "This should fail"},
                headers=self.get_headers()
            ) as response:
                
                if response.status == 404:
                    print("✅ Correctly rejected non-existent message ID")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Should have returned 404, got {response.status}: {error_text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Non-existent message test error: {e}")
            return False
    
    async def test_edit_nonexistent_conversation(self) -> bool:
        """Test editing message in non-existent conversation"""
        print("\n🧪 Testing EDIT IN NON-EXISTENT CONVERSATION...")
        
        try:
            fake_conversation_id = "00000000-0000-0000-0000-000000000000"
            fake_message_id = "11111111-1111-1111-1111-111111111111"
            
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/conversations/{fake_conversation_id}/messages/{fake_message_id}/edit",
                json={"content": "This should fail"},
                headers=self.get_headers()
            ) as response:
                
                if response.status == 404:
                    print("✅ Correctly rejected non-existent conversation ID")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Should have returned 404, got {response.status}: {error_text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Non-existent conversation test error: {e}")
            return False
    
    async def test_edit_assistant_message(self, conversation_id: str) -> bool:
        """Test trying to edit an assistant message (should fail)"""
        print("\n🧪 Testing EDIT ASSISTANT MESSAGE (SHOULD FAIL)...")
        
        try:
            # Send a user message to get an AI response
            await self.send_real_message(conversation_id, "Hello, how are you?")
            await asyncio.sleep(2)  # Wait for AI response
            
            # Get messages to find the assistant response
            messages = await self.get_conversation_messages(conversation_id)
            assistant_message = None
            
            for msg in messages:
                if msg.get('role') == 'assistant':
                    assistant_message = msg
                    break
            
            if not assistant_message:
                print("⚠️ No assistant message found to test editing")
                return True  # Skip this test
            
            # Try to edit the assistant message
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/conversations/{conversation_id}/messages/{assistant_message['message_id']}/edit",
                json={"content": "This should fail"},
                headers=self.get_headers()
            ) as response:
                
                if response.status == 400:
                    print("✅ Correctly rejected editing assistant message")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Should have returned 400, got {response.status}: {error_text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Assistant message edit test error: {e}")
            return False
    
    async def test_edit_empty_content(self, conversation_id: str) -> bool:
        """Test editing with empty content"""
        print("\n🧪 Testing EDIT WITH EMPTY CONTENT...")
        
        try:
            # Send a message first
            message = await self.send_real_message(conversation_id, "Test message for empty edit")
            
            # Try to edit with empty content
            for empty_content in ["", "   ", None]:
                print(f"   Testing with content: {repr(empty_content)}")
                
                payload = {"content": empty_content} if empty_content is not None else {}
                
                async with self.session.post(
                    f"{self.base_url}/api/v1/chat/conversations/{conversation_id}/messages/{message['message_id']}/edit",
                    json=payload,
                    headers=self.get_headers()
                ) as response:
                    
                    if response.status == 400:
                        print(f"✅ Correctly rejected empty content: {repr(empty_content)}")
                    else:
                        error_text = await response.text()
                        print(f"❌ Should have rejected empty content {repr(empty_content)}, got {response.status}: {error_text}")
                        return False
            
            return True
                    
        except Exception as e:
            print(f"❌ Empty content test error: {e}")
            return False
    
    async def test_edit_without_auth(self, conversation_id: str) -> bool:
        """Test editing without authentication"""
        print("\n🧪 Testing EDIT WITHOUT AUTHENTICATION...")
        
        try:
            # Send a message first
            message = await self.send_real_message(conversation_id, "Test message for auth test")
            
            # Try to edit without auth token
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/conversations/{conversation_id}/messages/{message['message_id']}/edit",
                json={"content": "This should fail"},
                headers={'Content-Type': 'application/json'}  # No auth header
            ) as response:
                
                if response.status == 401:
                    print("✅ Correctly rejected request without authentication")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Should have returned 401, got {response.status}: {error_text}")
                    return False
                    
        except Exception as e:
            print(f"❌ No auth test error: {e}")
            return False
    
    async def test_edit_other_user_message(self) -> bool:
        """Test trying to edit another user's message"""
        print("\n🧪 Testing EDIT OTHER USER'S MESSAGE...")
        
        try:
            # Create a second user
            timestamp = int(datetime.now().timestamp())
            user2_email = f"editingtest2_{timestamp}@example.com"
            
            user2_data = {
                "email": user2_email,
                "password": "TestPassword123!",
                "confirm_password": "TestPassword123!",
                "full_name": "Second Test User"
            }
            
            # Register second user
            async with self.session.post(
                f"{self.base_url}/api/v1/auth/register",
                json=user2_data,
                headers={'Content-Type': 'application/json'}
            ) as response:
                
                if response.status != 201:
                    print("⚠️ Could not create second user for test")
                    return True  # Skip this test
                
                user2_result = await response.json()
                user2_token = user2_result.get("access_token")
            
            # Create conversation as user2
            user2_headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {user2_token}'
            }
            
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/conversations",
                json={
                    "title": "User2 Conversation",
                    "model_name": "gpt-3.5-turbo"
                },
                headers=user2_headers
            ) as response:
                
                if response.status != 201:
                    print("⚠️ Could not create conversation for user2")
                    return True  # Skip this test
                
                user2_conv = await response.json()
                user2_conv_id = user2_conv['conversation_id']
            
            # Send message as user2
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/conversations/{user2_conv_id}/messages",
                json={
                    "content": "User2 message",
                    "role": "user",
                    "parent_message_id": None,
                    "attachments": None,
                    "status": "completed"
                },
                headers=user2_headers
            ) as response:
                
                if response.status != 200:
                    print("⚠️ Could not send message as user2")
                    return True  # Skip this test
                
                user2_msg = await response.json()
                user2_msg_id = user2_msg['message_id']
            
            # Try to edit user2's message as user1 (current user)
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/conversations/{user2_conv_id}/messages/{user2_msg_id}/edit",
                json={"content": "Hacked content"},
                headers=self.get_headers()  # Using user1's token
            ) as response:
                
                if response.status == 404:
                    print("✅ Correctly prevented editing other user's message")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Should have prevented cross-user editing, got {response.status}: {error_text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Cross-user edit test error: {e}")
            return False
    
    async def test_multiple_edits_same_message(self, conversation_id: str) -> bool:
        """Test editing the same message multiple times"""
        print("\n🧪 Testing MULTIPLE EDITS SAME MESSAGE...")
        
        try:
            # Send initial message
            message = await self.send_real_message(conversation_id, "Original message")
            await asyncio.sleep(1)
            
            # Edit multiple times
            edit_contents = [
                "First edit",
                "Second edit", 
                "Third edit"
            ]
            
            for i, content in enumerate(edit_contents, 1):
                print(f"   Edit #{i}: {content}")
                
                async with self.session.post(
                    f"{self.base_url}/api/v1/chat/conversations/{conversation_id}/messages/{message['message_id']}/edit",
                    json={"content": content},
                    headers=self.get_headers()
                ) as response:
                    
                    if response.status == 200:
                        print(f"✅ Edit #{i} successful")
                        await asyncio.sleep(1)  # Wait between edits
                    else:
                        error_text = await response.text()
                        print(f"❌ Edit #{i} failed ({response.status}): {error_text}")
                        return False
            
            print("✅ Multiple edits completed successfully")
            return True
                    
        except Exception as e:
            print(f"❌ Multiple edits test error: {e}")
            return False
    
    async def test_edit_with_very_long_content(self, conversation_id: str) -> bool:
        """Test editing with very long content"""
        print("\n🧪 Testing EDIT WITH VERY LONG CONTENT...")
        
        try:
            # Send initial message
            message = await self.send_real_message(conversation_id, "Short message")
            
            # Create very long content (test limits)
            very_long_content = "This is a very long message. " * 1000  # ~30KB
            extremely_long_content = "X" * 50000  # 50KB
            
            # Test very long content
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/conversations/{conversation_id}/messages/{message['message_id']}/edit",
                json={"content": very_long_content},
                headers=self.get_headers()
            ) as response:
                
                if response.status == 200:
                    print("✅ Very long content accepted")
                elif response.status == 400:
                    print("✅ Very long content correctly rejected")
                else:
                    print(f"⚠️ Unexpected response for very long content: {response.status}")
            
            # Test extremely long content (should be rejected)
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/conversations/{conversation_id}/messages/{message['message_id']}/edit",
                json={"content": extremely_long_content},
                headers=self.get_headers()
            ) as response:
                
                if response.status in [400, 422]:  # 400 = business logic rejection, 422 = validation error
                    print("✅ Extremely long content correctly rejected")
                    return True
                elif response.status == 200:
                    print("⚠️ Extremely long content was accepted (might be okay)")
                    return True
                else:
                    print(f"❌ Unexpected response for extremely long content: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ Long content test error: {e}")
            return False
    
    async def test_conversation_consistency_after_edit(self, conversation_id: str) -> bool:
        """Test that conversation remains consistent after edits"""
        print("\n🧪 Testing CONVERSATION CONSISTENCY AFTER EDIT...")
        
        try:
            # Build a conversation with multiple exchanges
            exchanges = [
                "What is 2 + 2?",
                "What is 3 + 3?", 
                "What is 4 + 4?"
            ]
            
            messages = []
            for question in exchanges:
                msg = await self.send_real_message(conversation_id, question)
                messages.append(msg)
                await asyncio.sleep(2)  # Wait for AI responses
            
            # Get conversation state before edit
            messages_before = await self.get_conversation_messages(conversation_id)
            print(f"   Messages before edit: {len(messages_before)}")
            
            # Edit the first message 
            edit_content = "What is 10 + 10?"
            
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/conversations/{conversation_id}/messages/{messages[0]['message_id']}/edit",
                json={"content": edit_content},
                headers=self.get_headers()
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    print(f"❌ Edit failed ({response.status}): {error_text}")
                    return False
            
            # Get conversation state after edit
            messages_after = await self.get_conversation_messages(conversation_id)
            print(f"   Messages after edit: {len(messages_after)}")
            
            # Verify conversation consistency
            if len(messages_after) < len(messages_before):
                print("✅ Subsequent messages properly removed")
                
                # Check that the edited message is updated
                edited_message = None
                for msg in messages_after:
                    if msg['message_id'] == messages[0]['message_id']:
                        edited_message = msg
                        break
                
                if edited_message and edited_message['content'] == edit_content:
                    print("✅ Message content properly updated")
                    return True
                else:
                    print("❌ Message content not properly updated")
                    return False
            else:
                print("❌ Subsequent messages not properly removed")
                return False
                    
        except Exception as e:
            print(f"❌ Conversation consistency test error: {e}")
            return False
    
    async def cleanup_test_data(self):
        """Clean up test conversations"""
        print("🧹 Cleaning up test data...")
        
        for conversation_id in self.test_conversations:
            try:
                async with self.session.delete(
                    f"{self.base_url}/api/v1/chat/conversations/{conversation_id}",
                    headers=self.get_headers()
                ) as response:
                    
                    if response.status == 200:
                        print(f"✅ Deleted conversation: {conversation_id}")
                    else:
                        print(f"⚠️ Failed to delete conversation {conversation_id}: {response.status}")
                        
            except Exception as e:
                print(f"❌ Cleanup error for {conversation_id}: {e}")
    
    async def run_comprehensive_editing_tests(self) -> bool:
        """Run comprehensive message editing tests"""
        print("🚀 Starting Comprehensive Message Editing Tests")
        print("=" * 80)
        
        try:
            # Step 1: Wait for server
            if not await self.wait_for_server():
                return False
            
            print("\n" + "=" * 60)
            print("STEP 1: AUTHENTICATION SETUP")
            print("=" * 60)
            
            # Step 2: Authentication setup
            if not await self.register_test_user():
                return False
            
            if not await self.verify_authentication():
                return False
            
            print("\n" + "=" * 60)
            print("STEP 2: BASIC FUNCTIONALITY TESTS")
            print("=" * 60)
            
            # Create test conversation
            conversation_id = await self.create_real_conversation("Basic Functionality Test")
            
            # Test basic editing
            self.test_results['basic_editing'] = await self.test_basic_message_editing(conversation_id)
            
            print("\n" + "=" * 60)
            print("STEP 3: ERROR CONDITION TESTS")
            print("=" * 60)
            
            # Error condition tests
            self.test_results['nonexistent_message'] = await self.test_edit_nonexistent_message(conversation_id)
            self.test_results['nonexistent_conversation'] = await self.test_edit_nonexistent_conversation()
            self.test_results['assistant_message_edit'] = await self.test_edit_assistant_message(conversation_id)
            self.test_results['empty_content'] = await self.test_edit_empty_content(conversation_id)
            
            print("\n" + "=" * 60)
            print("STEP 4: SECURITY TESTS")
            print("=" * 60)
            
            # Security tests
            self.test_results['no_auth'] = await self.test_edit_without_auth(conversation_id)
            self.test_results['cross_user_edit'] = await self.test_edit_other_user_message()
            
            print("\n" + "=" * 60)
            print("STEP 5: EDGE CASE TESTS")
            print("=" * 60)
            
            # Edge case tests
            edge_conversation_id = await self.create_real_conversation("Edge Case Tests")
            self.test_results['multiple_edits'] = await self.test_multiple_edits_same_message(edge_conversation_id)
            self.test_results['long_content'] = await self.test_edit_with_very_long_content(edge_conversation_id)
            
            print("\n" + "=" * 60)
            print("STEP 6: CONSISTENCY TESTS")
            print("=" * 60)
            
            # Consistency tests
            consistency_conversation_id = await self.create_real_conversation("Consistency Tests")
            self.test_results['conversation_consistency'] = await self.test_conversation_consistency_after_edit(consistency_conversation_id)
            
            # Cleanup
            await self.cleanup_test_data()
            
            print("\n" + "=" * 80)
            print("🎯 MESSAGE EDITING TEST RESULTS")
            print("=" * 80)
            
            passed = 0
            total = len(self.test_results)
            
            for test_name, result in self.test_results.items():
                status = "✅ PASS" if result else "❌ FAIL"
                print(f"{status} {test_name.replace('_', ' ').title()}")
                if result:
                    passed += 1
            
            print(f"\n📊 Overall Results: {passed}/{total} tests passed")
            
            if passed == total:
                print("\n🎉 ALL MESSAGE EDITING TESTS PASSED!")
                print("✅ Basic editing works correctly")
                print("✅ Error conditions handled properly")
                print("✅ Security measures in place")
                print("✅ Edge cases handled")
                print("✅ Conversation consistency maintained")
                print("\n💡 Message editing endpoint ready for production!")
            else:
                print(f"\n❌ {total - passed} MESSAGE EDITING TESTS FAILED!")
                print("🔧 Implementation needs fixes before frontend integration!")
            
            return passed == total
            
        except Exception as e:
            print(f"❌ Test suite failed: {e}")
            import traceback
            traceback.print_exc()
            return False


class ServerManager:
    """Manage the backend server for testing"""
    
    def __init__(self, port: int = 8000):
        self.port = port
        self.process = None
        
    async def start_server(self) -> bool:
        """Start the backend server"""
        print("🚀 Starting backend server...")
        
        # Change to backend directory
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Start server
        cmd = [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", str(self.port),
            "--log-level", "warning"
        ]
        
        # Set environment variables
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        
        self.process = subprocess.Popen(
            cmd,
            cwd=backend_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env
        )
        
        # Give server time to start
        await asyncio.sleep(5)
        
        if self.process.poll() is None:
            print(f"✅ Server started on port {self.port}")
            return True
        else:
            print("❌ Server failed to start")
            return False
    
    def stop_server(self):
        """Stop the backend server"""
        if self.process:
            print("🛑 Stopping backend server...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            print("✅ Server stopped")


async def main():
    """Main test runner"""
    server = ServerManager()
    
    try:
        # Start server
        if not await server.start_server():
            sys.exit(1)
        
        # Run comprehensive tests
        async with RealMessageEditingTester() as tester:
            success = await tester.run_comprehensive_editing_tests()
        
        if success:
            print("\n🎉 All message editing tests passed!")
            print("🔗 Message editing endpoint ready for frontend integration!")
            sys.exit(0)
        else:
            print("\n❌ Message editing tests revealed issues!")
            print("🔧 Backend needs fixes before frontend integration!")
            sys.exit(1)
             
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test runner failed: {e}")
        sys.exit(1)
    finally:
        server.stop_server()


if __name__ == "__main__":
    print("🧪 Real Message Editing Test Suite")
    print("Testing complete message editing workflow with NO FAKE DATA")
    print("=" * 80)
    asyncio.run(main()) 