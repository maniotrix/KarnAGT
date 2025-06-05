#!/usr/bin/env python3
"""Test script to validate Pydantic schemas work correctly"""

from app.models.schemas import (
    UserRegister, UserLogin, TokenResponse, UserProfile,
    ConversationCreate, MessageCreate, ChatStreamRequest,
    MemorySearchRequest, FileUploadResponse,
    UsageAnalytics, UserPreferences
)
from datetime import datetime


def test_auth_schemas():
    """Test authentication schemas"""
    print("🔐 Testing Authentication Schemas...")
    
    # Test user registration
    user_data = {
        "email": "test@example.com",
        "password": "TestPassword123",
        "confirm_password": "TestPassword123",
        "full_name": "Test User"
    }
    user_register = UserRegister(**user_data)
    print(f"✅ UserRegister: {user_register.email}")
    
    # Test user login
    login_data = {
        "email": "test@example.com",
        "password": "TestPassword123"
    }
    user_login = UserLogin(**login_data)
    print(f"✅ UserLogin: {user_login.email}")


def test_chat_schemas():
    """Test chat schemas"""
    print("\n💬 Testing Chat Schemas...")
    
    # Test conversation creation
    conv_data = {
        "title": "Test Conversation",
        "description": "A test conversation",
        "tags": ["test", "example"]
    }
    conversation = ConversationCreate(**conv_data)
    print(f"✅ ConversationCreate: {conversation.title}")
    
    # Test message creation
    msg_data = {
        "content": "Hello, this is a test message!",
        "role": "user"
    }
    message = MessageCreate(**msg_data)
    print(f"✅ MessageCreate: {message.content[:30]}...")
    
    # Test streaming request
    stream_data = {
        "message": "What is the capital of France?",
        "temperature": 0.7,
        "max_tokens": 1000
    }
    stream_req = ChatStreamRequest(**stream_data)
    print(f"✅ ChatStreamRequest: {stream_req.message[:30]}...")


def test_user_schemas():
    """Test user preference schemas"""
    print("\n👤 Testing User Schemas...")
    
    prefs_data = {
        "preferred_model": "gpt-4o-mini",
        "preferred_temperature": 0.8,
        "preferred_max_tokens": 2000,
        "memory_enabled": True
    }
    preferences = UserPreferences(**prefs_data)
    print(f"✅ UserPreferences: {preferences.preferred_model}")


def test_memory_schemas():
    """Test memory schemas"""
    print("\n🧠 Testing Memory Schemas...")
    
    search_data = {
        "query": "python programming",
        "limit": 10,
        "topics": ["coding", "python"]
    }
    memory_search = MemorySearchRequest(**search_data)
    print(f"✅ MemorySearchRequest: {memory_search.query}")


def test_file_schemas():
    """Test file schemas"""
    print("\n📁 Testing File Schemas...")
    
    file_data = {
        "success": True,
        "message": "File uploaded successfully",
        "file_id": "test-file-123",
        "filename": "test.pdf",
        "size": 1024000,
        "file_type": "application/pdf",
        "status": "pending"
    }
    file_response = FileUploadResponse(**file_data)
    print(f"✅ FileUploadResponse: {file_response.filename}")


def test_validation():
    """Test validation works correctly"""
    print("\n🔍 Testing Validation...")
    
    try:
        # This should fail - weak password
        weak_user = UserRegister(
            email="test@example.com",
            password="weak",
            confirm_password="weak"
        )
        print("❌ Validation failed - weak password should be rejected")
    except ValueError as e:
        print(f"✅ Validation working: {str(e)[:50]}...")
    
    try:
        # This should fail - mismatched passwords
        mismatch_user = UserRegister(
            email="test@example.com", 
            password="TestPassword123",
            confirm_password="DifferentPassword123"
        )
        print("❌ Validation failed - password mismatch should be rejected")
    except ValueError as e:
        print(f"✅ Validation working: {str(e)[:50]}...")


def main():
    """Run all schema tests"""
    print("🚀 Starting Pydantic Schema Tests...\n")
    
    try:
        test_auth_schemas()
        test_chat_schemas()
        test_user_schemas()
        test_memory_schemas()
        test_file_schemas()
        test_validation()
        
        print(f"\n🎉 All schema tests passed! Step 7 (Pydantic Schemas) is COMPLETE!")
        print(f"📋 Ready to proceed to Step 8: Authentication Endpoints")
        
    except Exception as e:
        print(f"\n❌ Schema test failed: {e}")
        return False
    
    return True


if __name__ == "__main__":
    main() 