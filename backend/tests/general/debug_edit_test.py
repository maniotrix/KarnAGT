#!/usr/bin/env python3
"""Debug script to check message role retrieval"""

import asyncio
import aiohttp
import time

async def debug_message_role():
    """Debug the message role issue"""
    
    async with aiohttp.ClientSession() as session:
        # Register user with unique email
        timestamp = int(time.time())
        user_data = {
            "email": f"debug{timestamp}@test.com",
            "password": "Test123!",
            "confirm_password": "Test123!",
            "full_name": "Debug User"
        }
        
        async with session.post(
            "http://localhost:8000/api/v1/auth/register",
            json=user_data
        ) as response:
            if response.status == 201:
                result = await response.json()
                token = result["access_token"]
                print(f"✅ Registered user, token: {token[:20]}...")
            else:
                print(f"❌ Registration failed: {response.status}")
                return

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        
        # Create conversation
        async with session.post(
            "http://localhost:8000/api/v1/chat/conversations",
            json={"title": "Debug Test", "model_name": "gpt-3.5-turbo"},
            headers=headers
        ) as response:
            if response.status == 201:
                conv_result = await response.json()
                conv_id = conv_result["conversation_id"]
                print(f"✅ Created conversation: {conv_id}")
            else:
                print(f"❌ Conversation creation failed: {response.status}")
                return

        # Send message (this returns the AI response, not the user message)
        async with session.post(
            f"http://localhost:8000/api/v1/chat/conversations/{conv_id}/messages",
            json={
                "content": "Test message",
                "role": "user",
                "parent_message_id": None,
                "attachments": None,
                "status": "completed"
            },
            headers=headers
        ) as response:
            if response.status == 200:
                msg_result = await response.json()
                ai_msg_id = msg_result["message_id"]
                ai_role = msg_result["role"]
                print(f"✅ Sent message, got AI response: {ai_msg_id}, role: '{ai_role}' (type: {type(ai_role)})")
            else:
                print(f"❌ Message sending failed: {response.status}")
                return

        # Get messages to find the user message
        async with session.get(
            f"http://localhost:8000/api/v1/chat/conversations/{conv_id}/messages",
            headers=headers
        ) as response:
            if response.status == 200:
                messages_result = await response.json()
                messages = messages_result.get("data", [])
                
                user_message = None
                for msg in messages:
                    if msg["role"] == "user":
                        user_message = msg
                        print(f"📋 Found user message: {msg['message_id']}, role: '{msg['role']}' (type: {type(msg['role'])})")
                        print(f"   Content: {msg['content']}")
                        break
                
                if not user_message:
                    print("❌ No user message found in conversation!")
                    return
                    
                user_msg_id = user_message["message_id"]
            else:
                print(f"❌ Get messages failed: {response.status}")
                return

        # Try to edit the user message
        async with session.post(
            f"http://localhost:8000/api/v1/chat/conversations/{conv_id}/messages/{user_msg_id}/edit",
            json={"content": "Edited content"},
            headers=headers
        ) as response:
            print(f"📝 Edit result: {response.status}")
            if response.status != 200:
                error_text = await response.text()
                print(f"   Error: {error_text}")
            else:
                edit_result = await response.json()
                print("✅ Edit successful!")
                print(f"   New AI response: {edit_result['content'][:100]}...")

if __name__ == "__main__":
    asyncio.run(debug_message_role()) 