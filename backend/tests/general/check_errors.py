#!/usr/bin/env python3
"""
Comprehensive error checking script for the backend
"""
import sys
import traceback
from typing import List, Tuple

def test_section(name: str):
    """Print test section header"""
    print(f"\n{'='*60}")
    print(f"🔍 {name}")
    print('='*60)

def check_result(test_name: str, success: bool, error: str = None):
    """Print test result"""
    status = "✅" if success else "❌"
    print(f"{status} {test_name}")
    if error and not success:
        print(f"   Error: {error}")

def main():
    """Run all error checks"""
    errors = []
    
    test_section("1. CORE IMPORTS")
    
    # Test core FastAPI imports
    try:
        from fastapi import FastAPI
        check_result("FastAPI import", True)
    except Exception as e:
        check_result("FastAPI import", False, str(e))
        errors.append(("FastAPI import", str(e)))
    
    # Test pydantic imports
    try:
        from pydantic import BaseModel
        from pydantic_settings import BaseSettings
        check_result("Pydantic imports", True)
    except Exception as e:
        check_result("Pydantic imports", False, str(e))
        errors.append(("Pydantic imports", str(e)))
    
    # Test SQLAlchemy imports
    try:
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy import select
        check_result("SQLAlchemy imports", True)
    except Exception as e:
        check_result("SQLAlchemy imports", False, str(e))
        errors.append(("SQLAlchemy imports", str(e)))
    
    test_section("2. SECURITY SYSTEM")
    
    # Test security imports
    try:
        from app.core.security import security, get_password_hash, verify_password
        check_result("Security core imports", True)
    except Exception as e:
        check_result("Security core imports", False, str(e))
        errors.append(("Security core imports", str(e)))
    
    # Test authentication dependencies
    try:
        from passlib.context import CryptContext
        from jose import jwt
        check_result("Authentication libraries", True)
    except Exception as e:
        check_result("Authentication libraries", False, str(e))
        errors.append(("Authentication libraries", str(e)))
    
    # Test password hashing
    try:
        password = "test123"
        hashed = get_password_hash(password)
        is_valid = verify_password(password, hashed)
        if is_valid:
            check_result("Password hashing functionality", True)
        else:
            check_result("Password hashing functionality", False, "Password verification failed")
            errors.append(("Password hashing", "Verification failed"))
    except Exception as e:
        check_result("Password hashing functionality", False, str(e))
        errors.append(("Password hashing", str(e)))
    
    # Test JWT tokens
    try:
        token = security.create_access_token("test_user")
        payload = security.verify_token(token)
        if payload and payload.get("sub") == "test_user":
            check_result("JWT token functionality", True)
        else:
            check_result("JWT token functionality", False, "Token verification failed")
            errors.append(("JWT tokens", "Token verification failed"))
    except Exception as e:
        check_result("JWT token functionality", False, str(e))
        errors.append(("JWT tokens", str(e)))
    
    test_section("3. CONFIGURATION")
    
    # Test settings import
    try:
        from app.core.config import settings
        check_result("Settings import", True)
        
        # Test key settings
        if settings.SECRET_KEY:
            check_result("SECRET_KEY configured", True)
        else:
            check_result("SECRET_KEY configured", False, "SECRET_KEY is empty")
            errors.append(("Configuration", "SECRET_KEY is empty"))
            
        if settings.DATABASE_URL:
            check_result("DATABASE_URL configured", True)
        else:
            check_result("DATABASE_URL configured", False, "DATABASE_URL is empty")
            errors.append(("Configuration", "DATABASE_URL is empty"))
            
    except Exception as e:
        check_result("Settings import", False, str(e))
        errors.append(("Settings", str(e)))
    
    test_section("4. DATABASE MODELS")
    
    # Test database models
    try:
        from app.models.database import User, Conversation, Message
        check_result("Database models import", True)
    except Exception as e:
        check_result("Database models import", False, str(e))
        errors.append(("Database models", str(e)))
    
    # Test database connection setup
    try:
        from app.core.database import get_db, engine
        check_result("Database connection setup", True)
    except Exception as e:
        check_result("Database connection setup", False, str(e))
        errors.append(("Database connection", str(e)))
    
    test_section("5. API DEPENDENCIES")
    
    # Test auth dependencies
    try:
        from app.api.v1.dependencies.auth import get_current_user_id, get_current_user
        check_result("Auth dependencies import", True)
    except Exception as e:
        check_result("Auth dependencies import", False, str(e))
        errors.append(("Auth dependencies", str(e)))
    
    # Test exceptions
    try:
        from app.core.exceptions import AuthenticationException, InvalidCredentialsException
        check_result("Custom exceptions import", True)
    except Exception as e:
        check_result("Custom exceptions import", False, str(e))
        errors.append(("Custom exceptions", str(e)))
    
    test_section("6. MIDDLEWARE")
    
    # Test middleware imports
    try:
        from app.api.v1.middleware.auth import AuthenticationMiddleware
        from app.api.v1.middleware.rate_limit import RateLimitMiddleware
        check_result("Middleware imports", True)
    except Exception as e:
        check_result("Middleware imports", False, str(e))
        errors.append(("Middleware", str(e)))
    
    # Test Redis import for rate limiting
    try:
        import redis.asyncio as redis
        check_result("Redis import for rate limiting", True)
    except Exception as e:
        check_result("Redis import for rate limiting", False, str(e))
        errors.append(("Redis import", str(e)))
    
    test_section("7. MAIN APPLICATION")
    
    # Test main app import
    try:
        from app.main import app
        check_result("Main FastAPI app import", True)
    except Exception as e:
        check_result("Main FastAPI app import", False, str(e))
        errors.append(("Main app", str(e)))
    
    # Test API router
    try:
        from app.api.router import api_router
        check_result("API router import", True)
    except Exception as e:
        check_result("API router import", False, str(e))
        errors.append(("API router", str(e)))
    
    test_section("8. EXTERNAL LIBRARIES")
    
    # Test external dependencies
    external_deps = [
        ("OpenAI", "openai"),
        ("Qdrant", "qdrant_client"),
        ("Neo4j", "neo4j"),
        ("Celery", "celery"),
        ("Alembic", "alembic"),
        ("Asyncpg", "asyncpg"),
    ]
    
    for name, module in external_deps:
        try:
            __import__(module)
            check_result(f"{name} library", True)
        except Exception as e:
            check_result(f"{name} library", False, str(e))
            errors.append((f"{name} library", str(e)))
    
    # SUMMARY
    test_section("SUMMARY")
    
    if errors:
        print(f"❌ Found {len(errors)} error(s):")
        for i, (component, error) in enumerate(errors, 1):
            print(f"  {i}. {component}: {error}")
        return False
    else:
        print("🎉 No errors found! Backend is ready to run.")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)