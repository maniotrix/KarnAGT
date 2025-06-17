"""
Test script for Image Upload API
Tests the Phase 1 implementation of image upload functionality
"""
import requests
import os
import json
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
TEST_IMAGE_PATH = "fifa_test_image.png"  # Use existing test image

def test_auth_and_get_token():
    """Get authentication token for testing"""
    # For testing, we'll need to either:
    # 1. Use an existing user token
    # 2. Create a test user and login
    # For now, let's check the files endpoint without auth
    print("🔍 Testing files service status...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/files/files_status")
        print(f"✅ Files service status: {response.status_code}")
        print(f"📄 Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error testing files service: {e}")
        return False

def test_image_upload_without_auth():
    """Test image upload endpoint (should fail without auth)"""
    print("\n🔍 Testing image upload without authentication...")
    
    if not os.path.exists(TEST_IMAGE_PATH):
        print(f"❌ Test image not found: {TEST_IMAGE_PATH}")
        return False
    
    try:
        with open(TEST_IMAGE_PATH, 'rb') as f:
            files = {'file': (TEST_IMAGE_PATH, f, 'image/png')}
            response = requests.post(
                f"{API_BASE_URL}/files/images/upload",
                files=files
            )
        
        print(f"📤 Upload response status: {response.status_code}")
        print(f"📄 Response: {response.text}")
        
        # Should fail with 401 or 403 (authentication required)
        if response.status_code in [401, 403]:
            print("✅ Correctly requires authentication")
            return True
        else:
            print("⚠️  Expected authentication error, got different response")
            return False
            
    except Exception as e:
        print(f"❌ Error testing image upload: {e}")
        return False

def test_api_structure():
    """Test API endpoint structure"""
    print("\n🔍 Testing API endpoint structure...")
    
    endpoints_to_test = [
        "/files/files_status",
        "/files/images/upload",
        "/files/images/test123",
        "/files/images/test123/metadata",
        "/files/images"
    ]
    
    results = {}
    for endpoint in endpoints_to_test:
        try:
            response = requests.get(f"{API_BASE_URL}{endpoint}")
            results[endpoint] = {
                "status": response.status_code,
                "accessible": response.status_code != 404
            }
            print(f"📡 {endpoint}: {response.status_code}")
        except Exception as e:
            results[endpoint] = {"status": "error", "error": str(e)}
            print(f"❌ {endpoint}: {e}")
    
    return results

def main():
    """Run all tests"""
    print("🚀 Starting Image Upload API Tests")
    print("=" * 50)
    
    # Test 1: Basic service status
    service_ok = test_auth_and_get_token()
    
    # Test 2: API structure
    api_structure = test_api_structure()
    
    # Test 3: Upload without auth (should fail correctly)
    auth_test = test_image_upload_without_auth()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"✅ Files service accessible: {service_ok}")
    print(f"✅ Authentication properly enforced: {auth_test}")
    print(f"📡 API endpoints structure: {len([k for k, v in api_structure.items() if v.get('accessible', False)])} accessible")
    
    print("\n🎯 NEXT STEPS:")
    print("1. Start the backend server: python start_dev.py")
    print("2. Create a test user or get authentication token")
    print("3. Test authenticated image upload")
    print("4. Verify MinIO storage integration")

if __name__ == "__main__":
    main() 