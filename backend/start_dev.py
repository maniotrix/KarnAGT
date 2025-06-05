#!/usr/bin/env python3
"""
Development Server Startup Script
"""
import os
import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Set environment to development if not set
os.environ.setdefault("ENVIRONMENT", "development")

if __name__ == "__main__":
    try:
        import uvicorn
        from app.main import app
        
        print("🚀 Starting ChatGPT Clone Backend...")
        print("📝 Make sure you have:")
        print("   1. Created a .env file (copy from env.example)")
        print("   2. Added your OPENAI_API_KEY")
        print("   3. Set up databases (PostgreSQL, Redis, etc.)")
        print("")
        
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Try installing dependencies: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1) 