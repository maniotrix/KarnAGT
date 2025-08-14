#!/usr/bin/env python3
"""
Setup Script for Stream Cancellation Tests

This script ensures all dependencies are installed and the environment is ready for testing.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Command: {cmd}")
        print(f"   Error: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is adequate"""
    print("🐍 Checking Python version...")
    
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} is too old. Need Python 3.8+")
        return False


def install_dependencies():
    """Install required dependencies"""
    dependencies = [
        "aiohttp",
        "uvicorn[standard]",
        "fastapi",
        "pydantic",
        "sqlalchemy",
        "asyncpg",  # For PostgreSQL async support
    ]
    
    print("📦 Installing dependencies...")
    
    for dep in dependencies:
        cmd = f"{sys.executable} -m pip install {dep}"
        if not run_command(cmd, f"Installing {dep}"):
            return False
    
    return True


def check_backend_structure():
    """Check if backend structure is in place"""
    print("📁 Checking backend structure...")
    
    required_files = [
        "app/main.py",
        "app/api/v1/endpoints/chat.py",
        "app/services/chat/streaming_service.py",
        "app/integrations/openai/streaming_handler.py",
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing required files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False
    else:
        print("✅ Backend structure looks good")
        return True


def create_test_config():
    """Create test configuration if needed"""
    print("⚙️  Setting up test configuration...")
    
    # Create a simple test config
    test_config = """# Test Configuration
# Add any test-specific environment variables here

# Backend URL
TEST_BACKEND_URL=http://localhost:8000

# Test settings
TEST_TIMEOUT=30
TEST_MAX_EVENTS=10
"""
    
    config_path = Path("test_config.env")
    if not config_path.exists():
        with open(config_path, "w") as f:
            f.write(test_config)
        print("✅ Created test configuration file")
    else:
        print("✅ Test configuration already exists")
    
    return True


def verify_test_files():
    """Verify test files are present"""
    print("🧪 Checking test files...")
    
    test_files = [
        "test_stream_cancellation.py",
        "test_client_disconnection.py",
        "run_stream_tests.py",
    ]
    
    missing_files = []
    for file_path in test_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing test files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False
    else:
        print("✅ All test files present")
        return True


def main():
    """Main setup function"""
    print("🎯 Stream Cancellation Test Setup")
    print("=" * 50)
    
    # Change to backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    print(f"📂 Working directory: {backend_dir.absolute()}")
    
    setup_steps = [
        ("Python Version Check", check_python_version),
        ("Backend Structure Check", check_backend_structure),
        ("Test Files Check", verify_test_files),
        ("Dependencies Installation", install_dependencies),
        ("Test Configuration", create_test_config),
    ]
    
    failed_steps = []
    
    for step_name, step_function in setup_steps:
        print(f"\n🔄 {step_name}")
        print("-" * 30)
        
        if not step_function():
            failed_steps.append(step_name)
            print(f"❌ {step_name} failed")
        else:
            print(f"✅ {step_name} completed")
    
    print("\n" + "=" * 50)
    
    if failed_steps:
        print("❌ Setup completed with errors:")
        for step in failed_steps:
            print(f"   - {step}")
        print("\n💡 Fix the errors above before running tests")
        return False
    else:
        print("🎉 Setup completed successfully!")
        print("\n🚀 Ready to run tests:")
        print("   python run_stream_tests.py")
        print("\n📖 Or run individual tests:")
        print("   python test_stream_cancellation.py")
        print("   python test_client_disconnection.py")
        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 