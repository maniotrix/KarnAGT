#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CodeSandbox Server Runner

Runs both Jupyter Server and FastAPI application.
"""

import os
import sys
import asyncio
import subprocess
import time
from pathlib import Path
import uvicorn
import httpx

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded from .env file")
except ImportError:
    print("⚠️  python-dotenv not available, using system environment variables only")

# Add the project root directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir
sys.path.insert(0, project_root)

from app.utils.logger import get_logger
from app.core.config import get_settings

# Get logger and settings
logger = get_logger("server_runner")
settings = get_settings()


class ServiceManager:
    """Manages Jupyter and FastAPI services"""
    
    def __init__(self):
        self.jupyter_process = None
        self.fastapi_task = None
        
    async def start_jupyter_server(self):
        """Start Jupyter Server"""
        logger.info(f"🔧 Starting Jupyter Server on {settings.jupyter_host}:{settings.jupyter_port}")
        
        # Jupyter server command
        cmd = [
            "jupyter", "server",
            f"--ip={settings.jupyter_host}",
            f"--port={settings.jupyter_port}",
            f"--allow-origin={settings.cors_origins}",
            "--no-browser",
            f"--ServerApp.token={settings.jupyter_token}",
            f"--ServerApp.password={settings.jupyter_password}",
            "--ServerApp.allow_remote_access=True"
        ]
        
        # Start Jupyter server process
        self.jupyter_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for Jupyter to be ready
        await self._wait_for_jupyter()
        logger.info("✅ Jupyter Server is ready")
        
    async def _wait_for_jupyter(self, timeout=30):
        """Wait for Jupyter Server to be ready"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{settings.jupyter_url}/api/status",
                        timeout=5.0
                    )
                    if response.status_code == 200:
                        return
            except Exception:
                pass
            
            await asyncio.sleep(1)
        
        raise RuntimeError("Jupyter Server failed to start within timeout")
    
    async def start_fastapi_server(self):
        """Start FastAPI application"""
        logger.info(f"🚀 Starting FastAPI server on {settings.host}:{settings.port}")
        
        # FastAPI server configuration
        config = uvicorn.Config(
            "app.main:app",
            host=settings.host,
            port=settings.port,
            log_level="info",
            access_log=True,
            workers=1,  # Single worker for development
            loop="asyncio"
        )
        
        # Create and start server
        server = uvicorn.Server(config)
        await server.serve()
    
    async def start_services(self):
        """Start both services"""
        try:
            # Start Jupyter Server first
            await self.start_jupyter_server()
            
            # Start FastAPI server
            await self.start_fastapi_server()
            
        except KeyboardInterrupt:
            logger.info("🛑 Received shutdown signal")
            await self.cleanup()
        except Exception as e:
            logger.error(f"❌ Error starting services: {e}")
            await self.cleanup()
            raise
    
    async def cleanup(self):
        """Cleanup services"""
        logger.info("🧹 Cleaning up services...")
        
        # Terminate Jupyter process
        if self.jupyter_process:
            self.jupyter_process.terminate()
            try:
                self.jupyter_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.jupyter_process.kill()
            logger.info("✅ Jupyter Server stopped")
        
        logger.info("✅ Cleanup complete")


def print_startup_info():
    """Print startup information"""
    print("=" * 60)
    print(f"🏗️  {settings.app_name} v{settings.app_version}")
    print("=" * 60)
    print(f"📊 Environment: {settings.environment}")
    print(f"🔧 Jupyter Server: {settings.jupyter_url}")
    print(f"🚀 FastAPI Server: http://{settings.host}:{settings.port}")
    print(f"📚 API Docs: http://{settings.host}:{settings.port}/docs")
    print(f"🔍 Health Check: http://{settings.host}:{settings.port}/api/v1/health")
    print("=" * 60)
    print("🎯 Simple API Usage:")
    print(f"   POST http://{settings.host}:{settings.port}/api/v1/workspace/create")
    print(f"   POST http://{settings.host}:{settings.port}/api/v1/workspace/{{id}}/upload")
    print(f"   POST http://{settings.host}:{settings.port}/api/v1/workspace/{{id}}/execute")
    print(f"   GET  http://{settings.host}:{settings.port}/api/v1/workspace/{{id}}/files")
    print("=" * 60)
    print("Press Ctrl+C to stop\n")


async def main():
    """Main function"""
    print_startup_info()
    
    try:
        service_manager = ServiceManager()
        await service_manager.start_services()
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    # Run the async main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 