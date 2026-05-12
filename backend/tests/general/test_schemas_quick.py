#!/usr/bin/env python3
"""Quick test for validation edge cases"""

from app.models.schemas import (
    UserRegister, ChatStreamRequest, PaginationParams, 
    ConversationBulkAction, SubscriptionTier, ModelName
)
from pydantic import ValidationError

def test_validation():
    print("🔍 Testing Validation Edge Cases...")
    
    test_count = 0
    
    # Test weak password
    try:
        UserRegister(
            email="test@example.com",
            password="weak",
            confirm_password="weak"
        )
        print("❌ Weak password validation failed")
    except ValidationError:
        test_count += 1
        print("✅ Weak password correctly rejected")
    
    # Test invalid temperature
    try:
        ChatStreamRequest(
            message="test",
            temperature=3.0  # Should be <= 2.0
        )
        print("❌ Temperature validation failed")
    except ValidationError:
        test_count += 1
        print("✅ Invalid temperature correctly rejected")
    
    # Test negative page
    try:
        PaginationParams(page=0)  # Should be >= 1
        print("❌ Page number validation failed")
    except ValidationError:
        test_count += 1
        print("✅ Invalid page number correctly rejected")
    
    # Test enums
    assert SubscriptionTier.FREE == "free"
    assert ModelName.GPT_4O_MINI == "gpt-4o-mini"
    test_count += 1
    print("✅ Enums working correctly")
    
    print(f"✅ Validation tests passed: {test_count}/4")

if __name__ == "__main__":
    test_validation() 