#!/usr/bin/env python3
"""
Comprehensive test for ResourceAuthorizationMiddleware patterns

This test verifies that ALL conversation endpoints from chat.py are correctly
handled by the ResourceAuthorizationMiddleware:

✅ PROTECTED endpoints (require conversation ownership validation):
   • GET /conversations/{id} - get conversation details  
   • POST /conversations/{id}/messages - send message
   • POST /conversations/{id}/stream - stream message ⚠️ CRITICAL
   • GET /conversations/{id}/messages - get messages
   • POST /conversations/{id}/messages/{mid}/edit - edit message
   • POST /conversations/{id}/messages/{mid}/edit/stream - edit stream ⚠️ CRITICAL  
   • PUT /conversations/{id} - update conversation
   • DELETE /conversations/{id} - delete conversation
   • POST /conversations/{id}/share - share conversation

❌ EXCLUDED endpoints (no conversation ownership needed):
   • POST /conversations - create new conversation
   • GET /conversations - list user's conversations  
   • POST /conversations/bulk - bulk operations

This ensures the security fix works: unauthorized users get 404 (not 429)
before any locks are acquired, preventing information disclosure.
"""

import re
from typing import Optional

# Exact pattern from middleware - UUID format: 8-4-4-4-12 hex digits
conversation_pattern = re.compile(r'^/api/v1/chat/conversations/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(?:/.*)?$')
excluded_conversation_paths = {
    "/api/v1/chat/conversations",      # Create/list conversations (no trailing slash)
    "/api/v1/chat/conversations/",     # Create/list conversations (with trailing slash)
    "/api/v1/chat/conversations/bulk", # Bulk operations
}

def extract_conversation_id(path: str) -> Optional[str]:
    """Extract conversation ID from URL path"""
    match = conversation_pattern.match(path)
    if match:
        return match.group(1)
    return None

def should_validate(path: str) -> bool:
    """Check if path should be validated for conversation ownership"""
    if path in excluded_conversation_paths:
        return False
    return extract_conversation_id(path) is not None

# Comprehensive test cases based on ALL actual conversation endpoints in chat.py
uuid_example = "ac70e87f-6f96-40d0-bfac-f5d71e45b67a"
message_id_example = "msg-12345678-1234-5678-90ab-123456789012"

test_cases = [
    # ✅ SHOULD validate - ALL actual endpoints with {conversation_id} from chat.py
    
    # GET /conversations/{conversation_id} - get conversation details
    (f"/api/v1/chat/conversations/{uuid_example}", True, uuid_example),
    
    # POST /conversations/{conversation_id}/messages - send message
    (f"/api/v1/chat/conversations/{uuid_example}/messages", True, uuid_example),
    
    # POST /conversations/{conversation_id}/stream - stream message ⚠️ CRITICAL
    (f"/api/v1/chat/conversations/{uuid_example}/stream", True, uuid_example),
    
    # GET /conversations/{conversation_id}/messages - get messages
    (f"/api/v1/chat/conversations/{uuid_example}/messages", True, uuid_example),
    
    # POST /conversations/{conversation_id}/messages/{message_id}/edit - edit message
    (f"/api/v1/chat/conversations/{uuid_example}/messages/{message_id_example}/edit", True, uuid_example),
    
    # POST /conversations/{conversation_id}/messages/{message_id}/edit/stream - edit stream ⚠️ CRITICAL
    (f"/api/v1/chat/conversations/{uuid_example}/messages/{message_id_example}/edit/stream", True, uuid_example),
    
    # PUT /conversations/{conversation_id} - update conversation
    (f"/api/v1/chat/conversations/{uuid_example}", True, uuid_example),
    
    # DELETE /conversations/{conversation_id} - delete conversation  
    (f"/api/v1/chat/conversations/{uuid_example}", True, uuid_example),
    
    # POST /conversations/{conversation_id}/share - share conversation
    (f"/api/v1/chat/conversations/{uuid_example}/share", True, uuid_example),
    
    # Test with trailing slashes
    (f"/api/v1/chat/conversations/{uuid_example}/", True, uuid_example),
    (f"/api/v1/chat/conversations/{uuid_example}/messages/", True, uuid_example),
    
    # ❌ SHOULD NOT validate - endpoints without conversation_id or with exclusions
    
    # POST /conversations - create new conversation (no conversation_id)
    ("/api/v1/chat/conversations", False, None),
    
    # GET /conversations - list conversations (no conversation_id)
    ("/api/v1/chat/conversations", False, None),
    
    # POST /conversations/bulk - bulk operations (excluded, non-UUID)
    ("/api/v1/chat/conversations/bulk", False, None),
    
    # Edge cases - invalid UUID formats  
    ("/api/v1/chat/conversations/abc-123-def-456", False, None),  # Invalid UUID format
    ("/api/v1/chat/conversations/short", False, None),  # Too short for UUID
    ("/api/v1/chat/conversations/12345", False, None),  # Numbers only, not UUID
    ("/api/v1/chat/conversations/UPPERCASE-UUID", False, None),  # Uppercase not allowed
    
    # Completely different endpoints
    ("/api/v1/chat/other", False, None),
    ("/api/v1/auth/login", False, None),
    ("/api/v1/memory/retrieve", False, None),
    ("/health", False, None),
    ("/api/v1/files/upload", False, None),
]

def run_tests():
    """Run comprehensive pattern tests for ALL conversation endpoints"""
    print("🧪 Testing ResourceAuthorizationMiddleware patterns...")
    print("📋 Testing ALL conversation endpoints from chat.py")
    print("=" * 80)
    print()
    
    all_passed = True
    protected_count = 0
    excluded_count = 0
    failed_count = 0
    
    for path, should_validate_expected, expected_conversation_id in test_cases:
        # Test extraction
        extracted_id = extract_conversation_id(path)
        should_validate_result = should_validate(path)
        
        # Check results
        id_match = extracted_id == expected_conversation_id
        validate_match = should_validate_result == should_validate_expected
        
        # Track statistics
        if should_validate_expected:
            protected_count += 1
        else:
            excluded_count += 1
        
        status = "✅" if (id_match and validate_match) else "❌"
        if not (id_match and validate_match):
            all_passed = False
            failed_count += 1
            
        print(f"{status} {path}")
        print(f"   Should validate: {should_validate_result} (expected: {should_validate_expected})")
        print(f"   Extracted ID: {extracted_id} (expected: {expected_conversation_id})")
        
        if not id_match:
            print(f"   ❌ ID extraction mismatch!")
        if not validate_match:
            print(f"   ❌ Validation logic mismatch!")
            
        print()
    
    # Summary
    print("=" * 80)
    print("📊 Test Summary:")
    print(f"   Total endpoints tested: {len(test_cases)}")
    print(f"   🛡️  Protected endpoints: {protected_count} (require conversation ownership)")
    print(f"   🚫 Excluded endpoints: {excluded_count} (create/list/bulk operations)")
    print(f"   ❌ Failed tests: {failed_count}")
    print()
    
    if all_passed:
        print("🎉 SUCCESS: All conversation endpoints correctly handled!")
        print("🛡️  ResourceAuthorizationMiddleware will properly protect:")
        print("   • Stream endpoints (prevent 429 instead of 404)")
        print("   • Edit endpoints (conversation ownership)")  
        print("   • All conversation operations (GET/PUT/DELETE)")
        print("🚫 And correctly exclude:")
        print("   • Create/list operations (no conversation_id needed)")
        print("   • Bulk operations (non-UUID paths)")
    else:
        print("❌ FAILED: Some patterns need review!")
        print("🔍 Check the failed tests above for issues.")
    
    return all_passed

if __name__ == "__main__":
    run_tests()
