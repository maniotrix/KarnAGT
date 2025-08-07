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
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONLEGACYWINDOWSIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")

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
        # Enable reload in development
        reload_enabled = os.environ.get("ENVIRONMENT") == "development"
        # Limit reload to application code only to avoid walking large directories and high cpu and memory usage
        reload_dirs = [str(Path(__file__).parent / "app")] if reload_enabled else None
        reload_excludes = ["venv/*", "*.pyc", "__pycache__/*", "workspaces/*", "logs/*", "test_*", "migrations/*"] if reload_enabled else None
        print(f"🔧 Environment: {os.environ.get('ENVIRONMENT')}")
        print(f"🔄 Auto-reload enabled: {reload_enabled}")

        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=reload_enabled,
            reload_dirs=reload_dirs,
            reload_excludes=reload_excludes,
            reload_delay=0.25,  # Prevent excessive restarts
            log_level="info"
        )
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Try installing dependencies: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1) 