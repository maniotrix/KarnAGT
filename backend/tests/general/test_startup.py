#!/usr/bin/env python3
"""
Test FastAPI application startup
"""

try:
    print("Testing FastAPI app startup...")
    
    from app.main import app
    print("✅ FastAPI app imported successfully")
    
    print(f"📊 App title: {app.title}")
    print(f"📊 App version: {app.version}")
    print(f"🛡️ Middleware count: {len(app.user_middleware)}")
    
    # List middleware
    print("\n🔧 Configured middleware:")
    for i, middleware in enumerate(app.user_middleware, 1):
        middleware_name = middleware.cls.__name__
        print(f"  {i}. {middleware_name}")
    
    # Check routes
    print(f"\n🛣️ Route count: {len(app.routes)}")
    
    print("\n🚀 FastAPI application is ready to start!")
    
except Exception as e:
    print(f"❌ Error during startup: {e}")
    import traceback
    traceback.print_exc()