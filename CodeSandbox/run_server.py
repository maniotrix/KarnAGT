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

# Initialize logging first
from app.core.logging_config import setup_logging
setup_logging()

from app.core.config import get_settings
from app.utils.logger import AppLogger

# Get settings
settings = get_settings()
logger = AppLogger("RUN_SERVER")


class ServiceManager:
    """Manages Jupyter and FastAPI services"""
    
    def __init__(self):
        self.jupyter_process = None
        self.fastapi_task = None
        
    async def start_jupyter_server(self):
        """Start Jupyter Server"""
        logger.info("Starting Jupyter Server",
                   host=settings.jupyter_host,
                   port=settings.jupyter_port,
                   token_set=bool(settings.jupyter_token))
        
        # Get Jupyter server command from settings
        cmd = settings.get_jupyter_command_args()
        
        # Start Jupyter server process
        try:
            logger.info(f"🔧 Executing command: {' '.join(cmd)}")
            
            self.jupyter_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give the process a moment to start
            await asyncio.sleep(2)
            
            # Check if process is still running
            if self.jupyter_process.poll() is None:
                logger.info(f"✅ Jupyter Server process started (PID: {self.jupyter_process.pid})")
                logger.info(f"Stdout: {self.jupyter_process.stdout}")
                logger.info(f"Stderr: {self.jupyter_process.stderr}")
            else:
                # Process terminated, get the output
                stdout, stderr = self.jupyter_process.communicate()
                logger.error(f"❌ Jupyter Server process terminated unexpectedly!")
                logger.error(f"📝 Exit code: {self.jupyter_process.returncode}")
                logger.error(f"📝 Stdout: {stdout}")
                logger.error(f"📝 Stderr: {stderr}")
                raise RuntimeError(f"Jupyter Server process terminated with exit code {self.jupyter_process.returncode}: {stderr}")
        except Exception as e:
            logger.error(f"❌ Error starting Jupyter Server: {e}")
            raise
        
        # Wait for Jupyter to be ready
        await self._wait_for_jupyter()
        logger.info("✅ Jupyter Server is ready")
        
    async def _wait_for_jupyter(self, timeout=30):
        """Wait for Jupyter Server to be ready"""
        logger.info(f"⏳ Waiting for Jupyter Server at {settings.jupyter_url}/api/status...")
        start_time = time.time()
        
        # Get authentication headers for Jupyter API
        headers = settings.get_jupyter_headers()
        
        while time.time() - start_time < timeout:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{settings.jupyter_url}/api/status",
                        headers=headers,
                        timeout=5.0
                    )
                    if response.status_code == 200:
                        return
                    else:
                        logger.debug(f"🔄 Jupyter not ready yet: {response}")
            except Exception as e:
                logger.debug(f"🔄 Jupyter not ready yet: {e}")
            
            await asyncio.sleep(1)
        
        raise RuntimeError(f"Jupyter Server failed to start within timeout: {timeout}s")
    
    async def start_fastapi_server(self):
        """Start FastAPI application using simple uvicorn.run approach"""
        logger.info(f"🚀 Starting FastAPI server on {settings.host}:{settings.port}")
        
        # Enable reload in development
        reload_enabled = settings.environment == "development"
        logger.info(f"🔧 Environment: {settings.environment}")
        logger.info(f"🔄 Auto-reload enabled: {reload_enabled}")
        
        # Use the simple uvicorn.run approach (like your working start_dev.py)
        try:
            import uvicorn
            uvicorn.run(
                "app.main:app",
                host=settings.host,
                port=settings.port,
                reload=reload_enabled,  # Simple reload flag
                log_level="info",
                access_log=True
            )
        except KeyboardInterrupt:
            logger.info("🛑 FastAPI server stopped by user")
        except Exception as e:
            logger.error(f"❌ FastAPI server error: {e}")
            raise
    
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
    if settings.environment == "development":
        print("🔄 Auto-reload: ENABLED")
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
    if settings.environment == "development":
        print("💡 Development Tips:")
        print("   • Code changes will trigger automatic server restart")
        print("   • Jupyter server runs independently and won't restart")
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