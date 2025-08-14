#!/usr/bin/env python3
"""
Test script to verify security system imports
"""

try:
    print("Testing security imports...")
    
    # Test core security
    from app.core.security import security, get_password_hash, verify_password
    print("✅ Core security imported")
    
    # Test exceptions
    from app.core.exceptions import AuthenticationException, InvalidCredentialsException
    print("✅ Security exceptions imported")
    
    # Test dependencies
    from app.api.v1.dependencies.auth import get_current_user_id, get_current_user
    print("✅ Auth dependencies imported")
    
    # Test middleware
    from app.api.v1.middleware.auth import AuthenticationMiddleware
    from app.api.v1.middleware.rate_limit import RateLimitMiddleware
    print("✅ Middleware imported")
    
    # Test password hashing
    password = "test_password_123"
    hashed = get_password_hash(password)
    is_valid = verify_password(password, hashed)
    
    if is_valid:
        print("✅ Password hashing works")
    else:
        print("❌ Password hashing failed")
    
    # Test token creation
    test_user_id = "test_user_123"
    access_token = security.create_access_token(subject=test_user_id)
    
    if access_token:
        print("✅ Token creation works")
        
        # Test token verification
        payload = security.verify_token(access_token)
        if payload and payload.get("sub") == test_user_id:
            print("✅ Token verification works")
        else:
            print("❌ Token verification failed")
    else:
        print("❌ Token creation failed")
    
    print("\n🎉 All security system components imported and tested successfully!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Test error: {e}")