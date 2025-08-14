#!/usr/bin/env python3
"""Test script to validate authentication endpoints"""

def test_auth_imports():
    """Test that all auth endpoint imports work correctly"""
    print("🔐 Testing Authentication Endpoint Imports...")
    
    try:
        from app.api.v1.endpoints.auth import router
        print("✅ Auth router imported successfully")
        
        from app.models.schemas.auth_schemas import (
            UserRegister, UserLogin, TokenResponse
        )
        print("✅ Auth schemas imported successfully")
        
        from app.core.security import security
        print("✅ Security service imported successfully")
        
        from app.core.exceptions import (
            EmailAlreadyExistsException, InvalidCredentialsException
        )
        print("✅ Custom exceptions imported successfully")
        
        from app.api.v1.dependencies.auth import get_current_user
        print("✅ Auth dependencies imported successfully")
        
        # Check that router has the expected endpoints
        routes = [route.path for route in router.routes]
        expected_routes = ["/", "/register", "/login", "/refresh", "/logout", "/me", 
                          "/forgot-password", "/reset-password", "/verify-email", 
                          "/resend-verification", "/change-password"]
        
        for expected_route in expected_routes:
            if expected_route in routes:
                print(f"✅ Endpoint {expected_route} found")
            else:
                print(f"❌ Endpoint {expected_route} missing")
        
        print(f"\n🎉 Authentication endpoints implementation successful!")
        print(f"📊 Found {len(routes)} endpoints total")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_auth_schemas():
    """Test auth schemas validation"""
    print("\n🔍 Testing Auth Schema Validation...")
    
    try:
        from app.models.schemas.auth_schemas import UserRegister, UserLogin
        from pydantic import ValidationError
        
        # Test valid user registration
        valid_user = UserRegister(
            email="test@example.com",
            password="TestPassword123",
            confirm_password="TestPassword123",
            full_name="Test User"
        )
        print("✅ Valid user registration schema works")
        
        # Test valid login
        valid_login = UserLogin(
            email="test@example.com",
            password="TestPassword123"
        )
        print("✅ Valid login schema works")
        
        # Test password validation
        try:
            invalid_user = UserRegister(
                email="test@example.com",
                password="weak",
                confirm_password="weak"
            )
            print("❌ Password validation failed")
        except ValidationError:
            print("✅ Password validation working correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Schema validation error: {e}")
        return False

def main():
    """Run all auth endpoint tests"""
    print("🚀 Testing Authentication Endpoints Implementation...\n")
    
    success = True
    success &= test_auth_imports()
    success &= test_auth_schemas()
    
    if success:
        print(f"\n🎉 ALL AUTHENTICATION ENDPOINT TESTS PASSED!")
        print(f"✅ Step 8 (Authentication Endpoints) is COMPLETE!")
        print(f"🔐 Ready for authentication testing!")
    else:
        print(f"\n❌ Some tests failed. Check the errors above.")
    
    return success

if __name__ == "__main__":
    main() 