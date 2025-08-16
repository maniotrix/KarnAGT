#!/usr/bin/env python3
"""
Universal Application Startup Script
Auto-detects environment and configures accordingly
"""
import os
import sys
from pathlib import Path
from typing import List, Tuple
import re

# Add app to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# === Load Environment Variables FIRST ===
try:
    # Load .env file from the same directory as this script
    env_file = current_dir / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv()
        print(f"✅ Loaded environment from: {env_file}")
        
        from app.utils import validate_api_keys
        validate_api_keys()
        print(f"✅ Validated API keys")
        # Set encoding defaults
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        os.environ.setdefault("PYTHONLEGACYWINDOWSIOENCODING", "utf-8")
        os.environ.setdefault("PYTHONUTF8", "1")
        print(f"✅ Encoding defaults set")
    else:
        print(f"⚠️ No .env file found at: {env_file}")
        raise RuntimeError("No .env file found")
except ImportError:
    print("⚠️ python-dotenv not installed, skipping .env file loading")
    raise

from app.core.config import settings

def validate_bucket_name(bucket_name: str) -> Tuple[bool, List[str]]:
    """
    Validate bucket name according to S3/MinIO naming conventions
    
    AWS S3 Bucket naming rules:
    - Must be between 3 and 63 characters long
    - Can contain only lowercase letters, numbers, and hyphens
    - Cannot contain uppercase characters or underscores
    - Cannot start or end with a hyphen
    - Cannot have consecutive hyphens
    - Must not be formatted as an IP address (e.g., 192.168.1.1)
    
    Args:
        bucket_name: The bucket name to validate
        
    Returns:
        Tuple of (is_valid: bool, errors: List[str])
        - is_valid: True if the bucket name is valid
        - errors: List of specific validation errors (empty if valid)
    """
    errors = []
    
    # Check if bucket_name is provided
    if not bucket_name:
        errors.append("Bucket name cannot be empty")
        return False, errors
    
    # Check length (3-63 characters)
    if len(bucket_name) < 3:
        errors.append("Bucket name must be at least 3 characters long")
    elif len(bucket_name) > 63:
        errors.append("Bucket name cannot exceed 63 characters")
    
    # Check for valid characters (lowercase letters, numbers, hyphens only)
    if not re.match(r'^[a-z0-9-]+$', bucket_name):
        invalid_chars = set(char for char in bucket_name if not re.match(r'[a-z0-9-]', char))
        if invalid_chars:
            errors.append(f"Bucket name contains invalid characters: {', '.join(sorted(invalid_chars))}. Only lowercase letters, numbers, and hyphens are allowed")
    
    # Check for uppercase letters specifically (common mistake)
    if any(char.isupper() for char in bucket_name):
        errors.append("Bucket name cannot contain uppercase letters")
    
    # Check for underscores specifically (common mistake)
    if '_' in bucket_name:
        errors.append("Bucket name cannot contain underscores. Use hyphens (-) instead")
    
    # Check start/end with hyphen
    if bucket_name.startswith('-'):
        errors.append("Bucket name cannot start with a hyphen")
    if bucket_name.endswith('-'):
        errors.append("Bucket name cannot end with a hyphen")
    
    # Check for consecutive hyphens
    if '--' in bucket_name:
        errors.append("Bucket name cannot contain consecutive hyphens")
    
    # Check if it looks like an IP address
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ip_pattern, bucket_name):
        errors.append("Bucket name cannot be formatted as an IP address")
    
    # Check for dots (not recommended for SSL/TLS)
    if '.' in bucket_name:
        errors.append("Bucket name should not contain dots (.) as they can cause SSL/TLS certificate issues")
    
    is_valid = len(errors) == 0
    return is_valid, errors

def check_postgresql_health():
    """Check PostgreSQL connection health using settings"""
    from urllib.parse import urlparse
    try:
        print(f"🔍 Checking PostgreSQL health...")
        import asyncpg
        import asyncio        
        # Parse DATABASE_URL to get host and port for display
        parsed = urlparse(settings.DATABASE_URL)
        host_port = f"{parsed.hostname}:{parsed.port}"
        
        async def test_postgres():
            conn = await asyncpg.connect(settings.DATABASE_URL)
            await conn.execute("SELECT 1")
            await conn.close()
            return True
        
        asyncio.run(test_postgres())
        print(f"✅ PostgreSQL ({host_port}) - Healthy")
        return True
        
    except ImportError:
        print("⚠️ asyncpg not available - PostgreSQL check skipped")
        return False
    except Exception as e:
        parsed = urlparse(settings.DATABASE_URL)
        host_port = f"{parsed.hostname}:{parsed.port}"
        print(f"⚠️ PostgreSQL ({host_port}) - Unhealthy: {e}")
        return False

def check_redis_health():
    """Check Redis connection health using settings"""
    from urllib.parse import urlparse
    try:
        print(f"🔍 Checking Redis health...")
        import redis
        
        # Parse REDIS_URL to get connection details
        parsed = urlparse(settings.REDIS_URL)
        host_port = f"{parsed.hostname}:{parsed.port}"
        
        # Create Redis connection from URL
        r = redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        r.ping()
        print(f"✅ Redis ({host_port}) - Healthy")
        return True
        
    except ImportError:
        print("⚠️ redis not available - Redis check skipped")
        return False
    except Exception as e:
        parsed = urlparse(settings.REDIS_URL)
        host_port = f"{parsed.hostname}:{parsed.port}"
        print(f"⚠️ Redis ({host_port}) - Unhealthy: {e}")
        return False

def check_neo4j_health():
    """Check Neo4j connection health using settings"""
    try:
        print(f"🔍 Checking Neo4j health...")
        from neo4j import GraphDatabase
        
        driver = GraphDatabase.driver(
            settings.NEO4J_URL,
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
            connection_timeout=5
        )
        
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            result.single()
        
        driver.close()
        print(f"✅ Neo4j ({settings.NEO4J_URL}) - Healthy")
        return True
        
    except ImportError:
        print("⚠️ neo4j not available - Neo4j check skipped")
        return False
    except Exception as e:
        print(f"⚠️ Neo4j ({settings.NEO4J_URL}) - Unhealthy: {e}")
        return False

def check_qdrant_health():
    """Check Qdrant connection health using settings"""
    try:
        print(f"🔍 Checking Qdrant health...")
        import requests
        
        # Qdrant health endpoint
        health_url = f"{settings.QDRANT_URL}/readyz"
        response = requests.get(health_url, timeout=5)
        response.raise_for_status()
        
        print(f"✅ Qdrant ({settings.QDRANT_URL}) - Healthy")
        return True
        
    except ImportError:
        print("⚠️ requests not available - Qdrant check skipped")
        return False
    except Exception as e:
        print(f"⚠️ Qdrant ({settings.QDRANT_URL}) - Unhealthy: {e}")
        return False

def check_minio_health():
    """Check MinIO connection health using settings"""
    try:
        print(f"🔍 Checking MinIO health...")
        import boto3
        from botocore.client import Config
        from botocore.exceptions import ClientError
        
        # Only check if MinIO is configured
        if settings.STORAGE_BACKEND.lower() != "minio":
            print("ℹ️ MinIO not configured as storage backend")
            return True
        
        client = boto3.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4', connect_timeout=5, read_timeout=5),
            region_name=settings.S3_REGION
        )
        
        # Test connection by listing buckets
        client.list_buckets()
        print(f"✅ MinIO ({settings.S3_ENDPOINT_URL}) - Healthy")
        return True
        
    except ImportError:
        print("⚠️ boto3 not available - MinIO check skipped")
        return False
    except Exception as e:
        print(f"⚠️ MinIO ({settings.S3_ENDPOINT_URL}) - Unhealthy: {e}")
        return False

def check_codesandbox_health():
    """Check CodeSandbox connection health using settings"""
    try:
        print(f"🔍 Checking CodeSandbox health...")
        import requests
        
        # Only check if CodeSandbox URL is configured
        if not settings.CODESANDBOX_URL or settings.CODESANDBOX_URL.strip() == "":
            print("ℹ️ CodeSandbox URL not configured - skipping check")
            return True
        
        # CodeSandbox health endpoint
        health_url = f"{settings.CODESANDBOX_URL}/health"
        response = requests.get(health_url, timeout=10)
        response.raise_for_status()
        
        # Try to parse response as JSON for more detailed info
        try:
            health_data = response.json()
            status = health_data.get('status', 'unknown')
            if status.lower() in ['healthy', 'ok', 'up']:
                print(f"✅ CodeSandbox ({settings.CODESANDBOX_URL}) - Healthy")
                return True
            else:
                print(f"⚠️ CodeSandbox ({settings.CODESANDBOX_URL}) - Status: {status}")
                return False
        except ValueError:
            # Response is not JSON, but HTTP 200 means healthy
            print(f"✅ CodeSandbox ({settings.CODESANDBOX_URL}) - Healthy")
            return True
        
    except ImportError:
        print("⚠️ requests not available - CodeSandbox check skipped")
        return False
    except Exception as e:
        print(f"⚠️ CodeSandbox ({settings.CODESANDBOX_URL}) - Unhealthy: {e}")
        return False

def check_all_database_services():
    """Check health of all configured database and external services"""
    print("🏥 Database & External Services Health Check")
    print("=" * 50)
    
    services = [
        ("PostgreSQL", check_postgresql_health),
        ("Redis", check_redis_health),
        ("Neo4j", check_neo4j_health),
        ("Qdrant", check_qdrant_health),
        ("MinIO", check_minio_health),
        ("CodeSandbox", check_codesandbox_health)
    ]
    
    results = {}
    for service_name, check_func in services:
        results[service_name] = check_func()
        print()  # Empty line between checks
    
    # Summary
    healthy = sum(1 for status in results.values() if status)
    total = len(results)
    
    print("📊 Health Check Summary:")
    for service_name, is_healthy in results.items():
        status = "✅ HEALTHY" if is_healthy else "❌ UNHEALTHY"
        print(f"   • {service_name}: {status}")
    
    print(f"📈 Overall: {healthy}/{total} services healthy")
    
    if healthy == total:
        print("🎉 All database services are healthy!")
    else:
        print("⚠️ Some services are unhealthy - check logs above")
        raise RuntimeError("Some services are unhealthy - check logs above")
    
    return results

def setup_minio_if_needed():
    """Gracefully set up MinIO buckets if possible"""
    try:
        print("🪣 Checking MinIO setup...")
        print(f"🔍 Debug - Bucket name: {settings.S3_BUCKET_NAME}")
        is_valid, errors = validate_bucket_name(settings.S3_BUCKET_NAME)
        if not is_valid:
            print(f"❌ Invalid bucket name: {errors}")
            raise RuntimeError(f"Invalid bucket name: {errors}")
        # Only try if storage backend is MinIO
        if settings.STORAGE_BACKEND.lower() == "minio":
            import boto3
            from botocore.client import Config
            from botocore.exceptions import ClientError
            
            # Quick connection test
            client = boto3.client(
                's3',
                endpoint_url=settings.S3_ENDPOINT_URL,
                aws_access_key_id=settings.S3_ACCESS_KEY_ID,
                aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
                config=Config(signature_version='s3v4', connect_timeout=5, read_timeout=5),
                region_name=settings.S3_REGION
            )
            
            # Try to create bucket if it doesn't exist
            bucket_name = settings.S3_BUCKET_NAME
            try:
                client.head_bucket(Bucket=bucket_name)
                print(f"✅ MinIO bucket '{bucket_name}' exists")
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    try:
                        client.create_bucket(Bucket=bucket_name)
                        print(f"✅ Created MinIO bucket '{bucket_name}'")
                    except ClientError:
                        print(f"⚠️ Could not create bucket '{bucket_name}' - will try at runtime")
                else:
                    print(f"⚠️ MinIO bucket check failed - will try at runtime")
        else:
            print("ℹ️ MinIO not configured as storage backend")
            
    except ImportError:
        print("⚠️ boto3 not available - MinIO setup skipped")
    except Exception:
        print("⚠️ MinIO setup failed - will try at runtime")



if __name__ == "__main__":
    try:
        import uvicorn
        from app.main import app
        from app.core.config import settings
        
        # Environment detection
        environment = settings.ENVIRONMENT.lower()
        is_development = environment in ["development", "dev", "local"]
        
        print(f"🐳 Starting Application Backend Container ({environment.title()})...")
        print(f"🔧 Environment: {settings.ENVIRONMENT}")
        print(f"🔄 Development mode: {is_development}")
        print(f"🐛 Debug enabled: {is_development}")
        print("")
        
        # Check database services health
        check_all_database_services()
        print("")
        
        # Setup MinIO buckets
        setup_minio_if_needed()
        print("")
        
        # Environment-specific configuration  
        print(f"🌐 Starting server on 0.0.0.0:8000")
        print("")
        
        # Start the application
        if is_development:
            print("🔧 Development configuration:")
            print(f"   • Hot reload: True")
            print(f"   • Workers: 1")
            print(f"   • Log level: debug")
            
            uvicorn.run(
                "app.main:app",
                host="0.0.0.0",
                port=8000,
                reload=True,
                reload_dirs=["./app"],
                reload_excludes=["__pycache__", "*.pyc", "logs", "uploads", "workspaces", "*.log"],
                reload_delay=0.25,
                log_level="debug",
                workers=1
            )
        else:
            print("🚀 Production configuration:")
            print(f"   • Hot reload: False")
            print(f"   • Workers: 4")
            print(f"   • Log level: info")
            
            uvicorn.run(
                "app.main:app",
                host="0.0.0.0",
                port=8000,
                reload=False,
                log_level="info",
                workers=4,
                access_log=True,
                use_colors=False
            )
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure all dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Container startup failed: {e}")
        sys.exit(1)
