#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Run the FastAPI server
"""

import os
import sys
import uvicorn

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from aicore.code_executor.logger import get_logger

# Configure logger
logger = get_logger()

# Server configuration
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8080

def start_server():
    """Start the FastAPI server directly."""
    try:
        # Import here to avoid circular imports
        from fastapi_server import app
        
        logger.info(f"Starting server on {SERVER_HOST}:{SERVER_PORT}")
        
        # Run server directly - no threads needed!
        uvicorn.run(
            app,
            host=SERVER_HOST,
            port=SERVER_PORT,
            log_level="info",
            access_log=True
        )
        
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        raise


def main():
    """Main function to run the server."""
    print("FastAPI Code Executor Service")
    print("=" * 50)
    print(f"🚀 Starting server on {SERVER_HOST}:{SERVER_PORT}")
    print(f"📡 API Docs: http://{SERVER_HOST}:{SERVER_PORT}/docs")
    print(f"🔍 Health: http://{SERVER_HOST}:{SERVER_PORT}/health")
    print("=" * 50)
    print("Press Ctrl+C to stop\n")
    
    try:
        start_server()
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 