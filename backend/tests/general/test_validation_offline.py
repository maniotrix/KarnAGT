#!/usr/bin/env python3
"""
Offline validation tests - test validation logic without running server
Tests the Pydantic schemas directly
"""

from pydantic import ValidationError
import sys
import os
from typing import Dict, Any, cast

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.models.schemas.auth_schemas import UserRegister, UserLogin
from app.utils.validation_utils import validate_email_security, sanitize_text_input, validate_username_security, validate_password_strength, SecurityValidationError

def test_user_register_validation():
    """Test UserRegister schema validation directly"""
    print("\n📝 Testing UserRegister Schema Validation...")
    
    try:
        from app.models.schemas.auth_schemas import UserRegister
    except ImportError as e:
        print(f"❌ Failed to import UserRegister schema: {e}")
        return False
    
    passed = 0
    failed = 0
    
    # Valid cases
    valid_cases = [
        {
            "data": {
                "email": "user@example.com",
                "password": "Password123",
                "confirm_password": "Password123",
                "full_name": "John Smith"
            },
            "description": "Valid complete registration"
        },
        {
            "data": {
                "email": "test@domain.co.uk", 
                "password": "SecurePass1",
                "confirm_password": "SecurePass1"
            },
            "description": "Valid minimal registration"
        }
    ]
    
    for case in valid_cases:
        try:
            data_dict = cast(Dict[str, Any], case["data"])
            user = UserRegister(**data_dict)
            print(f"✅ {case['description']}: PASSED")
            passed += 1
        except ValidationError as e:
            print(f"❌ {case['description']}: FAILED - {e}")
            failed += 1
    
    # Invalid cases that should fail
    invalid_cases = [
        {
            "data": {
                "email": "user@" + "a" * 300 + ".com",
                "password": "Password123",
                "confirm_password": "Password123"
            },
            "description": "Email too long",
            "expected_error": "Email too long"
        },
        {
            "data": {
                "email": "user..double@example.com",
                "password": "Password123", 
                "confirm_password": "Password123"
            },
            "description": "Email with consecutive dots",
            "expected_error": "consecutive dots"
        },
        {
            "data": {
                "email": "user@example.com",
                "password": "weak",
                "confirm_password": "weak"
            },
            "description": "Weak password",
            "expected_error": "at least 8 characters"
        },
        {
            "data": {
                "email": "user@example.com", 
                "password": "password123",
                "confirm_password": "password123"
            },
            "description": "Password missing uppercase",
            "expected_error": "uppercase letter"
        },
        {
            "data": {
                "email": "user@example.com",
                "password": "PASSWORD123", 
                "confirm_password": "PASSWORD123"
            },
            "description": "Password missing lowercase",
            "expected_error": "lowercase letter"
        },
        {
            "data": {
                "email": "user@example.com",
                "password": "Password",
                "confirm_password": "Password"
            },
            "description": "Password missing digit",
            "expected_error": "digit"
        },
        {
            "data": {
                "email": "user@example.com",
                "password": "Password123",
                "confirm_password": "DifferentPass123"
            },
            "description": "Password confirmation mismatch",
            "expected_error": "do not match"
        },
        {
            "data": {
                "email": "user@example.com",
                "password": "Password123",
                "confirm_password": "Password123",
                "full_name": "<script>alert('xss')</script>"
            },
            "description": "XSS in full name",
            "expected_error": "invalid characters"
        },
        {
            "data": {
                "email": "user@example.com",
                "password": "Password123", 
                "confirm_password": "Password123",
                "username": "admin"
            },
            "description": "Reserved username",
            "expected_error": "reserved"
        },
        {
            "data": {
                "email": "user@example.com",
                "password": "Password123",
                "confirm_password": "Password123", 
                "username": "12345"
            },
            "description": "All-numeric username",
            "expected_error": "all numbers"
        }
    ]
    
    for case in invalid_cases:
        try:
            data_dict = cast(Dict[str, Any], case["data"])
            user = UserRegister(**data_dict)
            print(f"❌ {case['description']}: FAILED - Should have been rejected")
            failed += 1
        except ValidationError as e:
            error_str = str(e).lower()
            expected_error = str(case["expected_error"])  # type: str
            expected_lower = expected_error.lower()
            if expected_lower in error_str:
                print(f"✅ {case['description']}: CORRECTLY REJECTED")
                passed += 1
            else:
                print(f"⚠️  {case['description']}: Rejected but wrong error - {e}")
                failed += 1
    
    print(f"\n📊 UserRegister Validation Results: {passed} passed, {failed} failed")
    return failed == 0


def test_user_login_validation():
    """Test UserLogin schema validation directly"""
    print("\n🚪 Testing UserLogin Schema Validation...")
    
    try:
        from app.models.schemas.auth_schemas import UserLogin
    except ImportError as e:
        print(f"❌ Failed to import UserLogin schema: {e}")
        return False
    
    passed = 0
    failed = 0
    
    # Valid cases
    valid_cases = [
        {
            "data": {"email": "user@example.com", "password": "anypassword"},
            "description": "Valid login"
        }
    ]
    
    for case in valid_cases:
        try:
            data_dict = cast(Dict[str, Any], case["data"])
            login = UserLogin(**data_dict)
            print(f"✅ {case['description']}: PASSED")
            passed += 1
        except ValidationError as e:
            print(f"❌ {case['description']}: FAILED - {e}")
            failed += 1
    
    # Invalid cases
    invalid_cases = [
        {
            "data": {"email": "invalid-email", "password": "password"},
            "description": "Invalid email format",
            "expected_error": "valid email"
        },
        {
            "data": {"email": "user@" + "a" * 500 + ".com", "password": "password"},
            "description": "Email too long",
            "expected_error": "too long"
        },
        {
            "data": {"email": "user..double@example.com", "password": "password"},
            "description": "Email with consecutive dots",
            "expected_error": "consecutive dots"
        }
    ]
    
    for case in invalid_cases:
        try:
            data_dict = cast(Dict[str, Any], case["data"])
            login = UserLogin(**data_dict)
            print(f"❌ {case['description']}: FAILED - Should have been rejected")
            failed += 1
        except ValidationError as e:
            error_str = str(e).lower()
            expected_error = str(case["expected_error"])  # type: str
            expected_lower = expected_error.lower()
            if expected_lower in error_str:
                print(f"✅ {case['description']}: CORRECTLY REJECTED")
                passed += 1
            else:
                print(f"⚠️  {case['description']}: Rejected but wrong error - {e}")
                failed += 1
    
    print(f"\n📊 UserLogin Validation Results: {passed} passed, {failed} failed")
    return failed == 0


def test_validation_utils():
    """Test the validation utility functions directly"""
    print("\n🛠️  Testing Validation Utility Functions...")
    
    try:
        from app.utils.validation_utils import (
            validate_email_security,
            sanitize_text_input,
            validate_username_security,
            validate_password_strength,
            SecurityValidationError
        )
    except ImportError as e:
        print(f"❌ Failed to import validation utils: {e}")
        return False
    
    passed = 0
    failed = 0
    
    # Test email validation
    email_tests = [
        ("user@example.com", True, "Valid email"),
        ("user..double@example.com", False, "Consecutive dots"),
        (".user@example.com", False, "Leading dot"),
        ("user@example.com.", False, "Trailing dot"),
        ("user@" + "a" * 300 + ".com", False, "Domain too long")
    ]
    
    for email, should_pass, desc in email_tests:
        try:
            result = validate_email_security(email)
            if should_pass:
                print(f"✅ Email - {desc}: PASSED")
                passed += 1
            else:
                print(f"❌ Email - {desc}: Should have failed")
                failed += 1
        except SecurityValidationError:
            if not should_pass:
                print(f"✅ Email - {desc}: CORRECTLY REJECTED")
                passed += 1
            else:
                print(f"❌ Email - {desc}: Should have passed")
                failed += 1
    
    # Test text sanitization
    text_tests = [
        ("Normal Name", True, "Valid name"),
        ("<script>alert('xss')</script>", False, "XSS attempt"),
        ("Name{injection}", False, "Injection brackets"),
        ("Name    WithSpaces", False, "Excessive whitespace")
    ]
    
    for text, should_pass, desc in text_tests:
        try:
            result = sanitize_text_input(text, "Name")
            if should_pass:
                print(f"✅ Text - {desc}: PASSED")  
                passed += 1
            else:
                print(f"❌ Text - {desc}: Should have failed")
                failed += 1
        except SecurityValidationError:
            if not should_pass:
                print(f"✅ Text - {desc}: CORRECTLY REJECTED")
                passed += 1
            else:
                print(f"❌ Text - {desc}: Should have passed")
                failed += 1
    
    # Test username validation
    username_tests = [
        ("validuser", True, "Valid username"),
        ("admin", False, "Reserved username"),
        ("12345", False, "All numbers"),
        ("user@domain", False, "Invalid characters")
    ]
    
    for username, should_pass, desc in username_tests:
        try:
            result = validate_username_security(username)
            if should_pass:
                print(f"✅ Username - {desc}: PASSED")
                passed += 1
            else:
                print(f"❌ Username - {desc}: Should have failed")
                failed += 1
        except SecurityValidationError:
            if not should_pass:
                print(f"✅ Username - {desc}: CORRECTLY REJECTED")
                passed += 1
            else:
                print(f"❌ Username - {desc}: Should have passed")
                failed += 1
    
    print(f"\n📊 Validation Utils Results: {passed} passed, {failed} failed")
    return failed == 0


def main():
    """Run all offline validation tests"""
    print("🧪 Running Offline Validation Tests...")
    print("=" * 60)
    
    all_passed = True
    
    all_passed &= test_user_register_validation()
    all_passed &= test_user_login_validation()
    all_passed &= test_validation_utils()
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("🎉 ALL OFFLINE VALIDATION TESTS PASSED!")
        print("✅ Your Pydantic schemas are working correctly")
        print("✅ Your validation utilities are secure")
        print("\n🚀 Ready to test with live server using test_auth_validation.py")
    else:
        print("❌ SOME TESTS FAILED!")
        print("🔧 Check your validation logic")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
