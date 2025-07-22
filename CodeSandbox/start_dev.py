#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Development Startup Script

Quick start script for local development.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Load environment variables from .env file first
try:
    from dotenv import load_dotenv
    # Load .env file if it exists
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ Loaded environment variables from {env_file}")
    else:
        print(f"⚠️  No .env file found at {env_file}")
        print("💡 Copy env.example to .env and customize as needed")
except ImportError:
    print("⚠️  python-dotenv not available, using system environment variables only")

# Add project to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def main():
    """Start development environment"""
    print("🚀 CodeSandbox Development Startup")
    print("=" * 50)
    
    # Check if Jupyter is available
    try:
        subprocess.run(["jupyter", "--version"], capture_output=True, check=True)
        print("✅ Jupyter Server available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Jupyter Server not found. Install with:")
        print("   pip install jupyter-server")
        return 1
    
    # Check if FastAPI dependencies are available
    try:
        import fastapi
        import uvicorn
        import httpx
        print("✅ FastAPI dependencies available")
    except ImportError:
        print("❌ FastAPI dependencies missing. Install with:")
        print("   pip install -r requirements.txt")
        return 1
    
    # Set development environment defaults (only if not already set)
    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("DEBUG", "true")
    os.environ.setdefault("LOG_LEVEL", "INFO")
    
    # Create workspace directory
    workspace_path = Path(os.getenv("WORKSPACE_BASE_PATH", "/tmp/workspaces"))
    workspace_path.mkdir(parents=True, exist_ok=True)
    print(f"✅ Workspace directory: {workspace_path}")
    
    # Start the server
    print("🚀 Starting CodeSandbox...")
    print("   - Jupyter Server: http://127.0.0.1:8888")
    print("   - FastAPI Server: http://127.0.0.1:8080")  
    print("   - API Docs: http://127.0.0.1:8080/docs")
    print("   - Health Check: http://127.0.0.1:8080/api/v1/health")
    print()
    print("Press Ctrl+C to stop")
    print("-" * 50)
    
    try:
        from run_server import main as run_main
        import asyncio
        return asyncio.run(run_main())
    except KeyboardInterrupt:
        print("\n👋 Development server stopped")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 