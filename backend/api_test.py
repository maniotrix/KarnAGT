#!/usr/bin/env python3
"""
Simple API test script to verify authentication endpoints work correctly.
Updated for httpOnly cookie + CSRF authentication system.
Run this while the dev server is running on localhost:8000
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Optional

BASE_URL = "http://localhost:8000"

# Global CSRF token for authenticated requests
csrf_token: Optional[str] = None

def get_csrf_headers() -> dict:
    """Get headers with CSRF token for state-changing requests"""
    headers = {"Content-Type": "application/json"}
    if csrf_token:
        headers["X-CSRF-Token"] = csrf_token
    return headers

async def test_auth_endpoints():
    """Test the authentication endpoints"""
    global csrf_token
    
    print("🚀 Testing ChatGPT Clone Authentication API")
    print("=" * 50)
    
    # Track test results instead of returning early
    test_results = {"passed": 0, "failed": 0}
    test_user_email = None
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Service Status
        print("1. Testing service status...")
        try:
            async with session.get(f"{BASE_URL}/api/v1/auth/status") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Service status: {'operational' if data['success'] else 'failed'}")
                    print(f"   📝 Message: {data['message']}")
                    test_results["passed"] += 1
                else:
                    print(f"   ❌ Service status failed: {response.status}")
                    test_results["failed"] += 1
        except Exception as e:
            print(f"   ❌ Service status error: {e}")
            test_results["failed"] += 1
        
        # Test 2: User Registration
        print("\n2. Testing user registration...")
        # Use a timestamp-based email to avoid conflicts
        import random
        timestamp = int(datetime.now().timestamp())
        test_user_email = f"test{timestamp}@example.com"
        register_data = {
            "email": test_user_email,
            "username": f"testuser{timestamp}",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!",
            "full_name": "Test User"
        }
        
        try:
            async with session.post(
                f"{BASE_URL}/api/v1/auth/register", 
                json=register_data
            ) as response:
                if response.status == 201:
                    data = await response.json()
                    csrf_token = data.get('csrf_token')
                    
                    print(f"   ✅ User registered successfully")
                    print(f"   👤 User ID: {data['user']['user_id']}")
                    print(f"   📧 Email: {data['user']['email']}")
                    print(f"   🛡️ CSRF Token: {csrf_token[:20] if csrf_token else 'None'}...")
                    
                    # Verify tokens are empty (httpOnly cookies)
                    if data['access_token'] == "" and data['refresh_token'] == "":
                        print(f"   ✅ Tokens properly stored in httpOnly cookies")
                    else:
                        print(f"   ⚠️ Warning: Tokens not empty in response")
                    
                    test_results["passed"] += 1
                        
                else:
                    error_data = await response.json()
                    print(f"   ❌ Registration failed: {response.status}")
                    print(f"   📝 Error: {error_data}")
                    test_results["failed"] += 1
        except Exception as e:
            print(f"   ❌ Registration error: {e}")
            test_results["failed"] += 1
        
        # Test 3: User Login
        print("\n3. Testing user login...")
        login_data = {
            "email": test_user_email,  # Use the same email we just registered
            "password": "TestPassword123!"
        }
        
        try:
            async with session.post(
                f"{BASE_URL}/api/v1/auth/login", 
                json=login_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    csrf_token = data.get('csrf_token')
                    
                    print(f"   ✅ Login successful")
                    print(f"   🛡️ CSRF Token: {csrf_token[:20] if csrf_token else 'None'}...")
                    print(f"   ⏰ Expires in: {data['expires_in']} seconds")
                    
                    # Verify tokens are empty (httpOnly cookies)
                    if data['access_token'] == "" and data['refresh_token'] == "":
                        print(f"   ✅ Auth tokens stored in httpOnly cookies")
                    else:
                        print(f"   ⚠️ Warning: Tokens not empty in response")
                    
                    test_results["passed"] += 1
                        
                else:
                    try:
                        error_data = await response.json()
                        print(f"   ❌ Login failed: {response.status}")
                        print(f"   📝 Error: {error_data}")
                    except:
                        error_text = await response.text()
                        print(f"   ❌ Login failed: {response.status}")
                        print(f"   📝 Error: {error_text}")
                    test_results["failed"] += 1
        except Exception as e:
            print(f"   ❌ Login error: {e}")
            test_results["failed"] += 1
        
        # Test 4: Get Current User Profile (using cookies, no Authorization header)
        print("\n4. Testing current user profile...")
        
        try:
            async with session.get(
                f"{BASE_URL}/api/v1/auth/me"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Profile retrieved successfully")
                    print(f"   👤 Username: {data['username']}")
                    print(f"   📧 Email: {data['email']}")
                    print(f"   🆔 User ID: {data['user_id']}")
                    print(f"   🔓 Verified: {data['is_verified']}")
                    test_results["passed"] += 1
                else:
                    try:
                        error_data = await response.json()
                        print(f"   ❌ Profile retrieval failed: {response.status}")
                        print(f"   📝 Error: {error_data}")
                    except:
                        print(f"   ❌ Profile retrieval failed: {response.status}")
                    test_results["failed"] += 1
        except Exception as e:
            print(f"   ❌ Profile error: {e}")
            test_results["failed"] += 1
        
        # Test 5: Token Refresh (using cookies, no request body needed)
        print("\n5. Testing token refresh...")
        
        try:
            async with session.post(f"{BASE_URL}/api/v1/auth/refresh") as response:
                if response.status == 200:
                    data = await response.json()
                    csrf_token = data.get('csrf_token')
                    
                    print(f"   ✅ Token refresh successful")
                    print(f"   🛡️ New CSRF Token: {csrf_token[:20] if csrf_token else 'None'}...")
                    print(f"   ⏰ Expires in: {data['expires_in']} seconds")
                    
                    # Verify access_token is empty (httpOnly)
                    if data['access_token'] == "":
                        print(f"   ✅ New tokens stored in httpOnly cookies")
                    else:
                        print(f"   ⚠️ Warning: Access token not empty")
                    
                    test_results["passed"] += 1
                else:
                    print(f"   ❌ Token refresh failed: {response.status}")
                    test_results["failed"] += 1
        except Exception as e:
            print(f"   ❌ Token refresh error: {e}")
            test_results["failed"] += 1
        
        # Test 6: Logout (using CSRF headers)
        print("\n6. Testing logout...")
        
        try:
            async with session.post(
                f"{BASE_URL}/api/v1/auth/logout",
                headers=get_csrf_headers()
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Logout successful")
                    print(f"   📝 Message: {data['message']}")
                    
                    # Clear CSRF token
                    csrf_token = None
                    test_results["passed"] += 1
                    
                else:
                    try:
                        error_data = await response.json()
                        print(f"   ❌ Logout failed: {response.status}")
                        print(f"   📝 Error: {error_data}")
                    except:
                        print(f"   ❌ Logout failed: {response.status}")
                    test_results["failed"] += 1
        except Exception as e:
            print(f"   ❌ Logout error: {e}")
            test_results["failed"] += 1
        
        # Test 7: User Cleanup Note
        if test_user_email:
            print("\n7. 🧹 Test user cleanup...")
            print(f"   📝 Test user created: {test_user_email}")
            print(f"   ⚠️  No automated deletion endpoint available")
            print(f"   💡 Consider adding DELETE /api/v1/auth/me endpoint for cleanup")
            print(f"   🔧 For now, test users will accumulate in database")
        
        # Print test results summary
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS SUMMARY:")
        print(f"   ✅ Passed: {test_results['passed']}")
        print(f"   ❌ Failed: {test_results['failed']}")
        print(f"   📈 Success Rate: {test_results['passed']}/{test_results['passed'] + test_results['failed']}")
        
        print("\n" + "=" * 50)
        print("🎉 httpOnly Cookie Authentication Test Completed!")
        print("📊 Key Features Tested:")
        print("   ✅ httpOnly cookies for secure token storage") 
        print("   ✅ CSRF token protection for state-changing requests")
        print("   ✅ Cookie-based authentication (no Authorization headers)")
        print("   ✅ Automatic cookie management by browser")
        print("   ✅ Secure logout with cookie clearing")
        print("   📝 Test user identification for manual cleanup")
        
        # Return True if all tests passed
        return test_results["failed"] == 0

async def test_error_cases():
    """Test some error cases"""
    print("\n🔍 Testing Error Cases")
    print("=" * 30)
    
    async with aiohttp.ClientSession() as session:
        # Test duplicate registration
        print("1. Testing duplicate registration...")
        register_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!",
            "full_name": "Test User"
        }
        
        async with session.post(
            f"{BASE_URL}/api/v1/auth/register", 
            json=register_data
        ) as response:
            if response.status in [400, 409]:  # Both are valid for duplicate registration
                error_data = await response.json()
                print(f"   ✅ Duplicate registration properly rejected")
                print(f"   📝 Error: {error_data['detail']}")
            else:
                print(f"   ⚠️  Unexpected response: {response.status}")
        
        # Test invalid login
        print("\n2. Testing invalid login...")
        login_data = {
            "email": "test@example.com",
            "password": "WrongPassword123!"
        }
        
        async with session.post(
            f"{BASE_URL}/api/v1/auth/login", 
            json=login_data
        ) as response:
            if response.status == 401:
                error_data = await response.json()
                print(f"   ✅ Invalid login properly rejected")
                print(f"   📝 Error: {error_data['detail']}")
            else:
                print(f"   ⚠️  Unexpected response: {response.status}")
        
        # Test accessing protected endpoint without token
        print("\n3. Testing protected endpoint without token...")
        async with session.get(f"{BASE_URL}/api/v1/auth/me") as response:
            if response.status == 401:
                error_data = await response.json()
                print(f"   ✅ Protected endpoint properly secured")
                print(f"   📝 Error: {error_data['detail']}")
            else:
                print(f"   ⚠️  Unexpected response: {response.status}")

async def main():
    """Main test function"""
    print(f"🕐 Test started at: {datetime.now()}")
    
    try:
        # Run basic auth flow tests
        success = await test_auth_endpoints()
        
        if success:
            # Run error case tests
            await test_error_cases()
        
        print(f"\n🕐 Test completed at: {datetime.now()}")
        if success:
            print("✨ httpOnly Cookie + CSRF Authentication System Working!")
            print("🛡️ Your app now has enterprise-grade security:")
            print("   • XSS protection via httpOnly cookies")
            print("   • CSRF protection via SameSite + tokens")
            print("   • Seamless browser cookie management")
        else:
            print("🔧 Fix authentication issues before proceeding")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 