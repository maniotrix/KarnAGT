#!/usr/bin/env python3
"""
ChatGPT Clone Backend - Setup and Test Script

This script will:
1. Check if database migrations are needed
2. Run migrations if required
3. Run the integration test suite
4. Provide setup guidance
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description, check=True):
    """Run a command and print results"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=check, 
            capture_output=True, 
            text=True
        )
        
        if result.stdout:
            print(f"  ✅ {result.stdout.strip()}")
        
        return result.returncode == 0
        
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Error: {e}")
        if e.stdout:
            print(f"  Output: {e.stdout}")
        if e.stderr:
            print(f"  Error: {e.stderr}")
        return False


def check_environment():
    """Check if environment is properly set up"""
    print("🔍 Environment Check...")
    
    # Check .env file
    env_file = Path(".env")
    if not env_file.exists():
        print("  ⚠️  .env file not found")
        print("  💡 Copy env.example to .env and configure your settings:")
        print("     cp env.example .env")
        return False
    
    # Check if OPENAI_API_KEY is set
    try:
        from app.core.config import settings
        if not settings.OPENAI_API_KEY or "your-" in settings.OPENAI_API_KEY:
            print("  ❌ OPENAI_API_KEY not set in .env file")
            print("  💡 Add your OpenAI API key to .env file")
            return False
        print("  ✅ OPENAI_API_KEY is set")
    except Exception as e:
        print(f"  ❌ Error checking settings: {e}")
        return False
    
    return True


def check_database():
    """Check database connection and migrations"""
    print("\n🗄️  Database Check...")
    
    # Check if we can connect to database
    try:
        from app.core.config import settings
        print(f"  📍 Database URL: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'local'}")
    except Exception as e:
        print(f"  ❌ Error checking database config: {e}")
        return False
    
    # Check current migration status
    success = run_command(
        "alembic current",
        "Checking current migration status",
        check=False
    )
    
    if not success:
        print("  ⚠️  Migration status check failed - database may not be initialized")
        return False
    
    # Check if migrations are needed
    success = run_command(
        "alembic check",
        "Checking if migrations are needed",
        check=False
    )
    
    return True


def run_migrations():
    """Run database migrations"""
    print("\n🔄 Running Database Migrations...")
    
    # Run migrations
    success = run_command(
        "alembic upgrade head",
        "Running migrations to latest version"
    )
    
    if success:
        print("  ✅ Migrations completed successfully")
        return True
    else:
        print("  ❌ Migration failed")
        return False


def install_dependencies():
    """Install or update dependencies"""
    print("\n📦 Checking Dependencies...")
    
    # Check if requirements.txt exists
    if not Path("requirements.txt").exists():
        print("  ❌ requirements.txt not found")
        return False
    
    # Install/update dependencies
    success = run_command(
        f"{sys.executable} -m pip install -r requirements.txt",
        "Installing/updating dependencies"
    )
    
    return success


def run_integration_tests():
    """Run the integration test suite"""
    print("\n🧪 Running Integration Tests...")
    
    # Run the test script
    result = subprocess.run([sys.executable, "test_integration.py"], capture_output=False)
    return result.returncode == 0


def main():
    """Main setup and test function"""
    print("🚀 ChatGPT Clone Backend - Setup and Test")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path("app").exists():
        print("❌ Error: Please run this script from the backend directory")
        sys.exit(1)
    
    # Step 1: Environment check
    if not check_environment():
        print("\n❌ Environment setup incomplete")
        print("\n💡 Next steps:")
        print("1. Copy env.example to .env: cp env.example .env")
        print("2. Edit .env file and add your OpenAI API key")
        print("3. Configure database connection in .env")
        print("4. Run this script again")
        sys.exit(1)
    
    # Step 2: Install dependencies
    if not install_dependencies():
        print("\n❌ Dependency installation failed")
        sys.exit(1)
    
    # Step 3: Database setup
    if not check_database():
        print("\n🔧 Database needs setup...")
        if not run_migrations():
            print("\n❌ Database setup failed")
            print("\n💡 Troubleshooting:")
            print("1. Make sure PostgreSQL is running")
            print("2. Check DATABASE_URL in .env file")
            print("3. Ensure database exists and is accessible")
            sys.exit(1)
    
    # Step 4: Run integration tests
    print("\n🎯 Environment ready - running integration tests...")
    if run_integration_tests():
        print("\n🎉 Setup Complete!")
        print("✅ Your ChatGPT Clone backend is ready to use!")
        print("\n🚀 To start the server:")
        print("   python main.py")
        print("   # or")
        print("   uvicorn main:app --reload --host 0.0.0.0 --port 8000")
    else:
        print("\n❌ Integration tests failed")
        print("Check the output above for specific issues")
        sys.exit(1)


if __name__ == "__main__":
    main() 