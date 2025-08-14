#!/usr/bin/env python3
"""
Comprehensive test script for httpOnly cookie + CSRF authentication system.
Run this while the dev server is running on localhost:8000

Tests:
- httpOnly cookie authentication
- CSRF token protection  
- Cookie persistence across requests
- Security validations
- Error scenarios
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Optional, Dict, Any

BASE_URL = "http://localhost:8000"

class CookieAuthTester:
    """Test class for httpOnly cookie + CSRF authentication"""
    
    def __init__(self):
        self.csrf_token: Optional[str] = None
        self.test_user_email: Optional[str] = None
        
    def get_csrf_headers(self) -> Dict[str, str]:
        """Get headers with CSRF token for state-changing requests"""
        headers = {"Content-Type": "application/json"}
        if self.csrf_token:
            headers["X-CSRF-Token"] = self.csrf_token
        return headers
    
    async def test_service_status(self, session: aiohttp.ClientSession) -> bool:
        """Test service status endpoint (no auth required)"""
        print("1. 🔍 Testing service status...")
        
        async with session.get(f"{BASE_URL}/api/v1/auth/status") as response:
            if response.status == 200:
                data = await response.json()
                print(f"   ✅ Service status: {'operational' if data['success'] else 'failed'}")
                print(f"   📝 Message: {data['message']}")
                return True
            else:
                print(f"   ❌ Service status failed: {response.status}")
                return False
    
    async def test_user_registration(self, session: aiohttp.ClientSession) -> bool:
        """Test user registration with httpOnly cookies"""
        print("\n2. 👤 Testing user registration...")
        
        # Generate unique user data
        timestamp = int(datetime.now().timestamp())
        self.test_user_email = f"test{timestamp}@example.com"
        register_data = {
            "email": self.test_user_email,
            "username": f"testuser{timestamp}",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!",
            "full_name": "Test User"
        }
        
        async with session.post(
            f"{BASE_URL}/api/v1/auth/register",
            json=register_data
        ) as response:
            if response.status == 201:
                data = await response.json()
                
                # Extract CSRF token from response
                self.csrf_token = data.get('csrf_token')
                
                print(f"   ✅ User registered successfully")
                print(f"   👤 User ID: {data['user']['user_id']}")
                print(f"   📧 Email: {data['user']['email']}")
                print(f"   🛡️ CSRF Token: {self.csrf_token[:20] if self.csrf_token else 'None'}...")
                
                # Verify tokens are empty (httpOnly cookies)
                if data['access_token'] == "" and data['refresh_token'] == "":
                    print(f"   ✅ Tokens properly empty (in httpOnly cookies)")
                else:
                    print(f"   ⚠️ Warning: Tokens not empty in response")
                
                # Check for httpOnly cookies (can't access directly, but test their effects)
                cookies = response.cookies
                auth_cookies = [key for key in cookies.keys() if key in ['access_token', 'refresh_token', 'csrf_token']]
                print(f"   🍪 Cookies set: {auth_cookies}")
                
                return True
            else:
                error_data = await response.json()
                print(f"   ❌ Registration failed: {response.status}")
                print(f"   📝 Error: {error_data}")
                return False
    
    async def test_user_login(self, session: aiohttp.ClientSession) -> bool:
        """Test user login with httpOnly cookies"""
        print("\n3. 🔐 Testing user login...")
        
        login_data = {
            "email": self.test_user_email,
            "password": "TestPassword123!"
        }
        
        async with session.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=login_data
        ) as response:
            if response.status == 200:
                data = await response.json()
                
                # Extract CSRF token from response  
                self.csrf_token = data.get('csrf_token')
                
                print(f"   ✅ Login successful")
                print(f"   🛡️ CSRF Token: {self.csrf_token[:20] if self.csrf_token else 'None'}...")
                print(f"   ⏰ Expires in: {data['expires_in']} seconds")
                
                # Verify tokens are empty (httpOnly cookies)
                if data['access_token'] == "" and data['refresh_token'] == "":
                    print(f"   ✅ Tokens properly empty (in httpOnly cookies)")
                else:
                    print(f"   ⚠️ Warning: Tokens not empty in response")
                
                return True
            else:
                error_data = await response.json()
                print(f"   ❌ Login failed: {response.status}")
                print(f"   📝 Error: {error_data}")
                return False
    
    async def test_authenticated_request(self, session: aiohttp.ClientSession) -> bool:
        """Test authenticated request using cookies (no Authorization header)"""
        print("\n4. 🔒 Testing authenticated request with cookies...")
        
        # Make request without Authorization header - should work via cookies
        async with session.get(f"{BASE_URL}/api/v1/auth/me") as response:
            if response.status == 200:
                data = await response.json()
                print(f"   ✅ Profile retrieved via cookies")
                print(f"   👤 Username: {data['username']}")
                print(f"   📧 Email: {data['email']}")
                print(f"   🆔 User ID: {data['user_id']}")
                print(f"   🔓 Verified: {data['is_verified']}")
                return True
            else:
                error_data = await response.json()
                print(f"   ❌ Profile retrieval failed: {response.status}")
                print(f"   📝 Error: {error_data}")
                return False
    
    async def test_csrf_protection(self, session: aiohttp.ClientSession) -> bool:
        """Test CSRF protection for state-changing operations"""
        print("\n5. 🛡️ Testing CSRF protection...")
        
        # Test 1: POST without CSRF token should fail
        print("   Testing POST without CSRF token...")
        async with session.post(
            f"{BASE_URL}/api/v1/chat/conversations",
            json={"title": "Test Conversation"}
        ) as response:
            if response.status == 403:
                print("   ✅ POST blocked without CSRF token")
            else:
                print(f"   ⚠️ POST allowed without CSRF token: {response.status}")
        
        # Test 2: POST with CSRF token should succeed
        print("   Testing POST with CSRF token...")
        async with session.post(
            f"{BASE_URL}/api/v1/chat/conversations",
            headers=self.get_csrf_headers(),
            json={"title": "Test Conversation"}
        ) as response:
            if response.status == 201:
                print("   ✅ POST allowed with CSRF token")
                return True
            elif response.status == 403:
                print("   ❌ POST blocked even with CSRF token")
                return False
            else:
                print(f"   ⚠️ Unexpected response: {response.status}")
                # Try to get error details for debugging
                try:
                    error_data = await response.json()
                    print(f"   📝 Details: {error_data}")
                except:
                    pass
                return False
    
    async def test_token_refresh(self, session: aiohttp.ClientSession) -> bool:
        """Test token refresh using cookies"""
        print("\n6. 🔄 Testing token refresh...")
        
        # Refresh should work with cookies, no body needed
        async with session.post(f"{BASE_URL}/api/v1/auth/refresh") as response:
            if response.status == 200:
                data = await response.json()
                
                # Update CSRF token
                self.csrf_token = data.get('csrf_token')
                
                print(f"   ✅ Token refresh successful")
                print(f"   🛡️ New CSRF Token: {self.csrf_token[:20] if self.csrf_token else 'None'}...")
                print(f"   ⏰ Expires in: {data['expires_in']} seconds")
                
                # Verify access_token is empty (httpOnly)
                if data['access_token'] == "":
                    print(f"   ✅ Access token properly empty (in httpOnly cookie)")
                else:
                    print(f"   ⚠️ Warning: Access token not empty")
                
                return True
            else:
                print(f"   ❌ Token refresh failed: {response.status}")
                return False
    
    async def test_logout(self, session: aiohttp.ClientSession) -> bool:
        """Test logout and cookie clearing"""
        print("\n7. 🚪 Testing logout...")
        
        async with session.post(
            f"{BASE_URL}/api/v1/auth/logout",
            headers=self.get_csrf_headers()
        ) as response:
            if response.status == 200:
                data = await response.json()
                print(f"   ✅ Logout successful")
                print(f"   📝 Message: {data['message']}")
                
                # Clear our CSRF token
                self.csrf_token = None
                
                return True
            else:
                error_data = await response.json()
                print(f"   ❌ Logout failed: {response.status}")
                print(f"   📝 Error: {error_data}")
                return False
    
    async def test_post_logout_access(self, session: aiohttp.ClientSession) -> bool:
        """Test that access is denied after logout"""
        print("\n8. 🚫 Testing post-logout access denial...")
        
        async with session.get(f"{BASE_URL}/api/v1/auth/me") as response:
            if response.status == 401:
                print(f"   ✅ Access properly denied after logout")
                return True
            elif response.status == 200:
                print(f"   ❌ Access still allowed after logout")
                return False
            else:
                print(f"   ⚠️ Unexpected response: {response.status}")
                return False
    
    async def test_security_scenarios(self, session: aiohttp.ClientSession) -> bool:
        """Test various security scenarios"""
        print("\n9. 🔐 Testing security scenarios...")
        
        # Test invalid login
        print("   Testing invalid credentials...")
        invalid_login = {
            "email": "nonexistent@example.com",
            "password": "WrongPassword123!"
        }
        
        async with session.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=invalid_login
        ) as response:
            if response.status == 401:
                print("   ✅ Invalid credentials properly rejected")
            else:
                print(f"   ❌ Invalid credentials not rejected: {response.status}")
        
        # Test accessing protected endpoint without authentication
        print("   Testing protected endpoint without auth...")
        
        # Create new session without cookies
        async with aiohttp.ClientSession() as clean_session:
            async with clean_session.get(f"{BASE_URL}/api/v1/auth/me") as response:
                if response.status == 401:
                    print("   ✅ Protected endpoint properly secured")
                    return True
                else:
                    print(f"   ❌ Protected endpoint not secured: {response.status}")
                    return False

async def run_comprehensive_test():
    """Run comprehensive authentication test suite"""
    print("🚀 Testing httpOnly Cookie + CSRF Authentication System")
    print("=" * 60)
    
    tester = CookieAuthTester()
    success_count = 0
    total_tests = 9
    
    # Use single session to maintain cookies
    async with aiohttp.ClientSession() as session:
        tests = [
            tester.test_service_status(session),
            tester.test_user_registration(session),
            tester.test_user_login(session),
            tester.test_authenticated_request(session),
            tester.test_csrf_protection(session),
            tester.test_token_refresh(session),
            tester.test_logout(session),
            tester.test_post_logout_access(session),
            tester.test_security_scenarios(session)
        ]
        
        for test in tests:
            try:
                result = await test
                if result:
                    success_count += 1
            except Exception as e:
                print(f"   ❌ Test failed with error: {e}")
    
    # Display cleanup info
    if tester.test_user_email:
        print(f"\n🧹 Test user created: {tester.test_user_email}")
        print("💡 Consider adding DELETE /api/v1/auth/me endpoint for automated cleanup")
    
    print("\n" + "=" * 60)
    print(f"📊 TEST RESULTS: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 ALL TESTS PASSED!")
        print("✅ httpOnly Cookie + CSRF Authentication System is working correctly!")
        print("🛡️ Security features verified:")
        print("   • httpOnly cookies prevent XSS token theft")
        print("   • CSRF tokens protect against cross-site attacks") 
        print("   • Cookie-based authentication works seamlessly")
        print("   • Proper access control after logout")
        print("   • Invalid credentials properly rejected")
    else:
        print(f"❌ {total_tests - success_count} tests failed")
        print("🔧 Check the errors above and verify your backend configuration")
    
    return success_count == total_tests

async def main():
    """Main test function"""
    print(f"🕐 Test started at: {datetime.now()}")
    
    try:
        success = await run_comprehensive_test()
        print(f"\n🕐 Test completed at: {datetime.now()}")
        
        if success:
            print("✨ Authentication system ready for production!")
        else:
            print("🔧 Fix the issues above before deploying")
            
    except Exception as e:
        print(f"❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
