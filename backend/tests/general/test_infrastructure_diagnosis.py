#!/usr/bin/env python3
"""
Infrastructure Diagnosis Test
Identifies real issues with database, MinIO, and API endpoints
"""

import asyncio
import sys
import os
import httpx
from pathlib import Path

# Add backend to path
sys.path.append('.')

from app.core.database import AsyncSessionLocal, engine
from app.core.config import get_settings
from app.models.database.user import User
from app.models.database.uploaded_image import UploadedImage
from app.services.storage.storage import ImageStorageService
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

class InfrastructureDiagnostic:
    """Comprehensive infrastructure testing"""
    
    def __init__(self):
        self.settings = get_settings()
        self.issues = []
        self.successes = []
    
    def log_issue(self, component: str, issue: str):
        """Log an infrastructure issue"""
        self.issues.append(f"❌ {component}: {issue}")
        print(f"❌ {component}: {issue}")
    
    def log_success(self, component: str, message: str):
        """Log a successful test"""
        self.successes.append(f"✅ {component}: {message}")
        print(f"✅ {component}: {message}")
    
    async def test_database_connectivity(self):
        """Test database connection and table existence"""
        print("\n🔍 Testing Database Connectivity...")
        
        try:
            # Test basic connection
            async with AsyncSessionLocal() as db:
                result = await db.execute(text("SELECT 1"))
                self.log_success("Database", "Connection successful")
                
                # Test if uploaded_images table exists
                try:
                    await db.execute(text("SELECT COUNT(*) FROM uploaded_images"))
                    self.log_success("Database", "uploaded_images table exists")
                except Exception as e:
                    self.log_issue("Database", f"uploaded_images table missing: {e}")
                
                # Test if users table exists and has data
                try:
                    result = await db.execute(text("SELECT COUNT(*) FROM users"))
                    count = result.scalar()
                    self.log_success("Database", f"users table exists with {count} records")
                except Exception as e:
                    self.log_issue("Database", f"users table issue: {e}")
                
        except OperationalError as e:
            self.log_issue("Database", f"Connection failed: {e}")
        except Exception as e:
            self.log_issue("Database", f"Unexpected error: {e}")
    
    async def test_minio_with_database(self):
        """Test MinIO integration with proper database session"""
        print("\n🔍 Testing MinIO with Database Integration...")
        
        try:
            # Create test user first
            async with AsyncSessionLocal() as db:
                # Check if test user exists, create if not
                test_user_email = "infra_test@example.com"
                query = select(User).where(User.email == test_user_email)
                result = await db.execute(query)
                test_user = result.scalar_one_or_none()
                
                if not test_user:
                    test_user = User(
                        email=test_user_email,
                        username="infra_test_user",
                        hashed_password="test_hash",
                        full_name="Infrastructure Test User",
                        is_active=True,
                        is_verified=True,
                        subscription_tier="free"
                    )
                    db.add(test_user)
                    await db.commit()
                    await db.refresh(test_user)
                    self.log_success("Database", "Test user created")
                else:
                    self.log_success("Database", "Test user found")
                
                # Now test MinIO upload with database
                storage = ImageStorageService()
                
                # Create simple test image data
                test_image_data = self.create_test_png()
                test_filename = "infra_test.png"
                content_type = "image/png"
                
                try:
                    upload_result = await storage.upload_image(
                        file_data=test_image_data,
                        filename=test_filename,
                        content_type=content_type,
                        user_id=test_user.user_id,
                        db=db
                    )
                    
                    self.log_success("MinIO+DB", f"Upload successful: {upload_result['file_id']}")
                    
                    # Test presigned URL generation
                    try:
                        presigned_url = await storage.get_presigned_url(upload_result['s3_key'])
                        self.log_success("MinIO", f"Presigned URL generated: {presigned_url[:50]}...")
                    except Exception as e:
                        self.log_issue("MinIO", f"Presigned URL failed: {e}")
                    
                    # Test file cleanup
                    try:
                        deleted = await storage.delete_image(upload_result['s3_key'])
                        if deleted:
                            self.log_success("MinIO", "File deletion successful")
                        else:
                            self.log_issue("MinIO", "File deletion failed")
                    except Exception as e:
                        self.log_issue("MinIO", f"Delete error: {e}")
                    
                except Exception as e:
                    self.log_issue("MinIO+DB", f"Upload failed: {e}")
                    import traceback
                    print(f"Full error: {traceback.format_exc()}")
                
                # Cleanup test user
                await db.delete(test_user)
                await db.commit()
                
        except Exception as e:
            self.log_issue("MinIO+DB", f"Test setup failed: {e}")
            import traceback
            print(f"Full error: {traceback.format_exc()}")
    
    async def test_api_endpoints(self):
        """Test actual API endpoints that were failing"""
        print("\n🔍 Testing API Endpoints...")
        
        api_base = "http://localhost:8000/api/v1"
        
        async with httpx.AsyncClient() as client:
            # Test files status endpoint
            try:
                response = await client.get(f"{api_base}/files/files_status")
                if response.status_code == 200:
                    data = response.json()
                    self.log_success("API", f"Status endpoint: {data.get('service', 'unknown')} v{data.get('version', 'unknown')}")
                else:
                    self.log_issue("API", f"Status endpoint failed: {response.status_code}")
            except Exception as e:
                self.log_issue("API", f"Status endpoint error: {e}")
            
            # Test auth endpoint
            try:
                response = await client.get(f"{api_base}/auth/status")
                if response.status_code == 200:
                    self.log_success("API", "Auth service reachable")
                else:
                    self.log_issue("API", f"Auth service failed: {response.status_code}")
            except Exception as e:
                self.log_issue("API", f"Auth service error: {e}")
    
    async def test_specific_upload_endpoint(self):
        """Test the specific upload endpoint that was failing with 500 errors"""
        print("\n🔍 Testing Upload Endpoint Specifically...")
        
        api_base = "http://localhost:8000/api/v1"
        
        # Create a real test user via API
        async with httpx.AsyncClient() as client:
            # Register test user
            register_data = {
                "email": "upload_test@example.com",
                "password": "TestPass123!",
                "confirm_password": "TestPass123!",
                "full_name": "Upload Test User"
            }
            
            try:
                response = await client.post(f"{api_base}/auth/register", json=register_data)
                if response.status_code == 201:
                    auth_data = response.json()
                    token = auth_data["access_token"]
                    self.log_success("API", "Test user registered successfully")
                    
                    # Test image upload
                    headers = {"Authorization": f"Bearer {token}"}
                    test_image = self.create_test_png()
                    
                    files = {
                        "file": ("test.png", test_image, "image/png")
                    }
                    
                    try:
                        response = await client.post(
                            f"{api_base}/files/images/upload",
                            headers=headers,
                            files=files
                        )
                        
                        if response.status_code == 201:
                            upload_data = response.json()
                            self.log_success("API", f"Upload successful: {upload_data.get('file_id', 'unknown')}")
                        else:
                            self.log_issue("API", f"Upload failed: {response.status_code} - {response.text}")
                            
                    except Exception as e:
                        self.log_issue("API", f"Upload request error: {e}")
                
                else:
                    self.log_issue("API", f"User registration failed: {response.status_code} - {response.text}")
                    
            except Exception as e:
                self.log_issue("API", f"Registration error: {e}")
    
    def create_test_png(self) -> bytes:
        """Create a minimal valid PNG for testing"""
        # Minimal 1x1 transparent PNG
        return bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 dimensions
            0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,  # bit depth, color type, etc.
            0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,  # IDAT chunk start
            0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,  # compressed data
            0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,  # IDAT data
            0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,  # IEND chunk
            0x42, 0x60, 0x82
        ])
    
    async def run_all_tests(self):
        """Run all infrastructure tests"""
        print("🚀 Infrastructure Diagnosis Starting...")
        print(f"📊 Database URL: {self.settings.DATABASE_URL.split('@')[1] if '@' in self.settings.DATABASE_URL else 'localhost'}")
        print(f"🗄️  Storage Backend: {self.settings.STORAGE_BACKEND}")
        print(f"📦 S3 Endpoint: {self.settings.S3_ENDPOINT_URL}")
        print(f"🪣 S3 Bucket: {self.settings.S3_BUCKET_NAME}")
        
        await self.test_database_connectivity()
        await self.test_minio_with_database()
        await self.test_api_endpoints()
        await self.test_specific_upload_endpoint()
        
        print("\n" + "="*60)
        print("📋 INFRASTRUCTURE DIAGNOSIS SUMMARY")
        print("="*60)
        
        print(f"\n✅ SUCCESSES ({len(self.successes)}):")
        for success in self.successes:
            print(f"  {success}")
        
        print(f"\n❌ ISSUES FOUND ({len(self.issues)}):")
        for issue in self.issues:
            print(f"  {issue}")
        
        if not self.issues:
            print("\n🎉 ALL INFRASTRUCTURE TESTS PASSED!")
            print("The system should be ready for file uploads.")
        else:
            print(f"\n⚠️  {len(self.issues)} ISSUES NEED ATTENTION")
            print("These must be resolved for proper file upload functionality.")
        
        return len(self.issues) == 0

async def main():
    """Main test function"""
    diagnostic = InfrastructureDiagnostic()
    success = await diagnostic.run_all_tests()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 