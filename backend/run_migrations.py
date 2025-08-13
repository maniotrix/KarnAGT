#!/usr/bin/env python3
"""
Database Migration Runner
Handles Alembic migrations safely before container startup
"""
import os
import sys
import subprocess
from pathlib import Path

# Add app to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Load environment variables
try:
    from dotenv import load_dotenv
    env_file = current_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ Loaded environment from: {env_file}")
        # Set encoding defaults
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        os.environ.setdefault("PYTHONLEGACYWINDOWSIOENCODING", "utf-8")
        os.environ.setdefault("PYTHONUTF8", "1")
        print(f"✅ Encoding defaults set")
    else:
        print(f"⚠️ No .env file found at: {env_file}")
        raise RuntimeError("No .env file found")
except ImportError:
    print("⚠️ python-dotenv not installed, using system environment")
    raise

def check_database_connection():
    """Check if database is accessible"""
    try:
        from app.core.config import settings
        import asyncpg
        import asyncio
        
        async def test_connection():
            # Extract connection details from DATABASE_URL
            database_url = settings.DATABASE_URL
            conn = await asyncpg.connect(database_url)
            await conn.close()
            return True
        
        asyncio.run(test_connection())
        return True
        
    except ImportError:
        print("⚠️ asyncpg not available, skipping database connection test")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def run_migrations():
    """Run Alembic migrations with direct streaming"""
    try:
        print("🔄 Running database migrations...")
        print("=" * 50)
        
        # Change to backend directory for alembic
        os.chdir(current_dir)
        
        # Run alembic upgrade head - streams directly to terminal
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            text=True,
            check=True
            # No capture_output - streams everything directly!
        )
        
        print("=" * 50)
        print("✅ Migrations completed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed with exit code: {e.returncode}")
        return False
    except FileNotFoundError:
        print("❌ Alembic not found. Install with: pip install alembic")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during migration: {e}")
        return False

def main():
    """Main migration function"""
    print("🗄️ Database Migration Runner")
    print("=" * 40)
    
    # Check database connection
    print("🔍 Checking database connection...")
    if not check_database_connection():
        print("❌ Cannot connect to database. Make sure database containers are running.")
        sys.exit(1)
    
    print("✅ Database connection successful")
    print("")
    
    # Run migrations
    success = run_migrations()
    
    if success:
        print("")
        print("🎉 Migration process completed successfully!")
        print("You can now start the application containers.")
    else:
        print("")
        print("❌ Migration process failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
