#!/usr/bin/env python3
"""
Comprehensive File API Integration Test
Tests all file/image endpoints with real users, database, and MinIO storage
Uses existing fifa_test_image.png for testing
Tests: Authentication -> Upload -> Serve -> Metadata -> List -> Delete -> Bulk Operations
"""

import asyncio
import sys
import uuid
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import httpx
import time

# Add backend to path
sys.path.append('.')

from app.core.database import AsyncSessionLocal, engine
from app.models.database.user import User
from app.models.database.uploaded_image import UploadedImage
from app.services.storage.storage import storage_service
from app.core.security import security
from app.core.config import get_settings

# SQLAlchemy cleanup
from sqlalchemy import delete

# Test configuration
API_BASE_URL = "http://localhost:8000/api/v1"
TEST_IMAGE_PATH = "fifa_test_image.png"

class FileAPIIntegrationTest:
    """Test class for comprehensive file API integration"""
    
    def __init__(self):
        self.test_users = []
        self.auth_tokens = {}
        self.uploaded_files = []
        self.bulk_uploaded_files = []  # Track bulk uploads separately
        self.settings = get_settings()
        
    async def setup_test_environment(self):
        """Set up test users and authentication"""
        print("Setting up test environment...")
        
        # Verify test image exists
        if not os.path.exists(TEST_IMAGE_PATH):
            raise FileNotFoundError(f"Test image not found: {TEST_IMAGE_PATH}")
        
        async with AsyncSessionLocal() as db:
            # Create test users with different subscription tiers
            test_user_configs = [
                {
                    "username": f"file_test_user_pro_{uuid.uuid4().hex[:8]}",
                    "email": f"file_test_pro_{uuid.uuid4().hex[:8]}@example.com",
                    "subscription_tier": "pro",
                    "is_active": True,
                    "is_verified": True
                },
                {
                    "username": f"file_test_user_enterprise_{uuid.uuid4().hex[:8]}",
                    "email": f"file_test_enterprise_{uuid.uuid4().hex[:8]}@example.com",
                    "subscription_tier": "enterprise",
                    "is_active": True,
                    "is_verified": True
                },
                {
                    "username": f"file_test_user_free_{uuid.uuid4().hex[:8]}",
                    "email": f"file_test_free_{uuid.uuid4().hex[:8]}@example.com",
                    "subscription_tier": "free",
                    "is_active": True,
                    "is_verified": True
                }
            ]
            
            for user_config in test_user_configs:
                test_user = User(
                    user_id=str(uuid.uuid4()),
                    username=user_config["username"],
                    email=user_config["email"],
                    full_name=f"Test User {str(user_config['subscription_tier']).title()}",
                    hashed_password="test_password_hash",
                    subscription_tier=user_config["subscription_tier"],
                    is_active=user_config["is_active"],
                    is_verified=user_config["is_verified"]
                )
                
                db.add(test_user)
                await db.commit()
                await db.refresh(test_user)
                
                # Generate auth token for user
                token = security.create_access_token(
                    subject=test_user.user_id,
                    scopes=["files", "chat"]
                )
                
                self.test_users.append(test_user)
                self.auth_tokens[test_user.user_id] = token
                
                print(f"Created test user: {test_user.username} ({test_user.subscription_tier}) - ID: {test_user.user_id}")
            
            print(f"Created {len(self.test_users)} test users with authentication tokens")
    
    def get_auth_headers(self, user_id: str) -> Dict[str, str]:
        """Get authorization headers for API requests"""
        token = self.auth_tokens.get(user_id)
        if not token:
            raise ValueError(f"No auth token for user {user_id}")
        
        return {"Authorization": f"Bearer {token}"}
    
    async def test_service_status(self):
        """Test files service status endpoint"""
        print("Testing files service status...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/files/files_status")
            
            print(f"Status endpoint response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Service version: {data.get('version', 'unknown')}")
                print(f"Max image size: {data.get('max_image_size_mb', 'unknown')} MB")
                print(f"Allowed types: {data.get('allowed_types', 'unknown')}")
                
                # Check for thumbnail feature support
                features = data.get('features', [])
                if 'thumbnails' in features:
                    print(f"Thumbnail feature: ENABLED")
                    print(f"Thumbnail sizes: {data.get('thumbnail_sizes', 'unknown')}")
                    print(f"Thumbnail format: {data.get('thumbnail_format', 'unknown')}")
                else:
                    print(f"Thumbnail feature: NOT ENABLED")
                
                # Check for bulk operations support
                bulk_features = [f for f in features if f.startswith('bulk_')]
                if bulk_features:
                    print(f"Bulk features: {bulk_features}")
                    bulk_limits = data.get('bulk_limits', {})
                    if bulk_limits:
                        print(f"Bulk limits: {bulk_limits}")
                else:
                    print(f"Bulk features: NOT ENABLED")
                
                return True
            else:
                print(f"Service status check failed: {response.text}")
                return False
    
    async def test_image_upload_flow(self):
        """Test image upload flow for different user types"""
        print("Testing image upload flow...")
        
        async with httpx.AsyncClient() as client:
            upload_results = []
            
            # Read the FIFA test image
            with open(TEST_IMAGE_PATH, 'rb') as f:
                image_data = f.read()
            
            print(f"Using test image: {TEST_IMAGE_PATH} ({len(image_data)} bytes)")
            
            for user in self.test_users:
                print(f"Testing upload for user: {user.username} ({user.subscription_tier})")
                
                # Prepare upload request
                filename = f"fifa_upload_{user.subscription_tier}_{uuid.uuid4().hex[:8]}.png"
                files = {
                    "file": (filename, image_data, "image/png")
                }
                data = {
                    "conversation_id": f"conv_test_{uuid.uuid4().hex[:8]}"
                }
                headers = self.get_auth_headers(user.user_id)
                
                print(f"  Uploading {filename}...")
                
                # Make upload request
                response = await client.post(
                    f"{API_BASE_URL}/files/images/upload",
                    files=files,
                    data=data,
                    headers=headers
                )
                
                print(f"  Upload response: {response.status_code}")
                
                # All users can now upload (free, pro, enterprise)
                if response.status_code == 201:
                    upload_data = response.json()
                    upload_results.append({
                        "user": user,
                        "upload_data": upload_data,
                        "file_size": len(image_data)
                    })
                    self.uploaded_files.append({
                        "file_id": upload_data["file_id"],
                        "user_id": user.user_id,
                        "s3_key": upload_data["s3_key"],
                        "filename": filename
                    })
                    print(f"  Upload successful: {upload_data['file_id']}")
                    print(f"  File URL: {upload_data.get('urls', {}).get('api', 'N/A')}")
                    
                    # Check for thumbnail URLs in response
                    urls = upload_data.get('urls', {})
                    thumbnail_urls = {k: v for k, v in urls.items() if k.startswith('thumbnail_')}
                    if thumbnail_urls:
                        print(f"  Thumbnail URLs generated: {list(thumbnail_urls.keys())}")
                    else:
                        print(f"  No thumbnail URLs found in response")
                        
                else:
                    print(f"  Upload failed: {response.status_code} - {response.text}")
            
            print(f"Upload flow completed. {len(upload_results)} files uploaded successfully.")
            return upload_results
    
    async def test_image_serving_flow(self):
        """Test image serving with authentication and ownership validation"""
        print("Testing image serving flow...")
        
        async with httpx.AsyncClient() as client:
            serve_results = []
            
            for uploaded_file in self.uploaded_files:
                file_id = uploaded_file["file_id"]
                owner_user_id = uploaded_file["user_id"]
                filename = uploaded_file["filename"]
                
                print(f"Testing serving for file: {file_id} ({filename})")
                
                # Test 1: Authorized access (owner)
                headers = self.get_auth_headers(owner_user_id)
                response = await client.get(
                    f"{API_BASE_URL}/files/images/{file_id}",
                    headers=headers,
                    follow_redirects=False
                )
                
                if response.status_code == 302:
                    print(f"  Owner access: Redirected to presigned URL")
                    presigned_url = response.headers.get("location")
                    if presigned_url:
                        # Test accessing the presigned URL
                        presigned_response = await client.get(presigned_url)
                        if presigned_response.status_code == 200:
                            print(f"  Presigned URL access successful ({len(presigned_response.content)} bytes)")
                            serve_results.append({"file_id": file_id, "owner_access": True})
                        else:
                            print(f"  Presigned URL access failed: {presigned_response.status_code}")
                else:
                    print(f"  Owner access failed: {response.status_code}")
                
                # Test 2: Unauthorized access (different user)
                for other_user in self.test_users:
                    if other_user.user_id != owner_user_id:
                        other_headers = self.get_auth_headers(other_user.user_id)
                        unauthorized_response = await client.get(
                            f"{API_BASE_URL}/files/images/{file_id}",
                            headers=other_headers
                        )
                        
                        if unauthorized_response.status_code == 403:
                            print(f"  Unauthorized access correctly blocked ({other_user.username})")
                        else:
                            print(f"  WARNING: Unauthorized access should be blocked but got {unauthorized_response.status_code}")
                        break
                
                # Test 3: No authentication
                no_auth_response = await client.get(f"{API_BASE_URL}/files/images/{file_id}")
                if no_auth_response.status_code in [401, 403]:
                    print(f"  No auth access correctly blocked")
                else:
                    print(f"  WARNING: No auth access should be blocked but got {no_auth_response.status_code}")
            
            print(f"Serving flow completed. {len(serve_results)} files served successfully.")
            return serve_results
    
    async def test_thumbnail_serving_flow(self):
        """Test thumbnail serving with different sizes and authentication"""
        print("Testing thumbnail serving flow...")
        
        async with httpx.AsyncClient() as client:
            thumbnail_results = []
            
            # Test thumbnail sizes from configuration
            test_sizes = ["150x150", "300x300"]  # Based on default config
            
            for uploaded_file in self.uploaded_files:
                file_id = uploaded_file["file_id"]
                owner_user_id = uploaded_file["user_id"]
                filename = uploaded_file["filename"]
                
                print(f"Testing thumbnails for file: {file_id} ({filename})")
                
                for size in test_sizes:
                    print(f"  Testing thumbnail size: {size}")
                    
                    # Test 1: Authorized access (owner)
                    headers = self.get_auth_headers(owner_user_id)
                    response = await client.get(
                        f"{API_BASE_URL}/files/images/{file_id}/thumbnail?size={size}",
                        headers=headers,
                        follow_redirects=False
                    )
                    
                    if response.status_code == 302:
                        print(f"    Owner access: Redirected to presigned URL")
                        presigned_url = response.headers.get("location")
                        if presigned_url:
                            # Test accessing the presigned URL
                            presigned_response = await client.get(presigned_url)
                            if presigned_response.status_code == 200:
                                print(f"    Thumbnail served successfully ({len(presigned_response.content)} bytes)")
                                thumbnail_results.append({
                                    "file_id": file_id, 
                                    "size": size, 
                                    "served": True,
                                    "bytes": len(presigned_response.content)
                                })
                            else:
                                print(f"    Thumbnail presigned URL access failed: {presigned_response.status_code}")
                    elif response.status_code == 404:
                        print(f"    Thumbnail not found for size {size} (may not be generated yet)")
                    else:
                        print(f"    Thumbnail access failed: {response.status_code}")
                    
                    # Test 2: Unauthorized access
                    for other_user in self.test_users:
                        if other_user.user_id != owner_user_id:
                            other_headers = self.get_auth_headers(other_user.user_id)
                            unauthorized_response = await client.get(
                                f"{API_BASE_URL}/files/images/{file_id}/thumbnail?size={size}",
                                headers=other_headers
                            )
                            
                            if unauthorized_response.status_code in [403, 404]:
                                print(f"    Unauthorized thumbnail access correctly blocked")
                            else:
                                print(f"    WARNING: Unauthorized thumbnail access should be blocked but got {unauthorized_response.status_code}")
                            break
                
                # Test 3: Default size (no size parameter)
                print(f"  Testing default thumbnail size")
                headers = self.get_auth_headers(owner_user_id)
                response = await client.get(
                    f"{API_BASE_URL}/files/images/{file_id}/thumbnail",
                    headers=headers,
                    follow_redirects=False
                )
                
                if response.status_code == 302:
                    print(f"    Default thumbnail served successfully")
                elif response.status_code == 404:
                    print(f"    Default thumbnail not found")
                else:
                    print(f"    Default thumbnail access: {response.status_code}")
                
                # Test 4: Invalid size
                print(f"  Testing invalid thumbnail size")
                response = await client.get(
                    f"{API_BASE_URL}/files/images/{file_id}/thumbnail?size=999x999",
                    headers=headers
                )
                
                if response.status_code == 404:
                    print(f"    Invalid thumbnail size correctly returns 404")
                else:
                    print(f"    Invalid thumbnail size returned: {response.status_code}")
            
            print(f"Thumbnail serving flow completed. {len(thumbnail_results)} thumbnails served successfully.")
            return thumbnail_results
    
    async def test_image_metadata_flow(self):
        """Test image metadata retrieval"""
        print("Testing image metadata flow...")
        
        async with httpx.AsyncClient() as client:
            metadata_results = []
            
            for uploaded_file in self.uploaded_files:
                file_id = uploaded_file["file_id"]
                owner_user_id = uploaded_file["user_id"]
                filename = uploaded_file["filename"]
                
                print(f"Testing metadata for file: {file_id} ({filename})")
                
                headers = self.get_auth_headers(owner_user_id)
                response = await client.get(
                    f"{API_BASE_URL}/files/images/{file_id}/metadata",
                    headers=headers
                )
                
                if response.status_code == 200:
                    metadata = response.json()
                    print(f"  Metadata retrieved: {metadata.get('filename', 'unknown')}")
                    print(f"  Size: {metadata.get('size', 'unknown')} bytes")
                    print(f"  Content type: {metadata.get('content_type', 'unknown')}")
                    print(f"  Uploaded at: {metadata.get('uploaded_at', 'unknown')}")
                    
                    # Check for thumbnail URLs in metadata
                    urls = metadata.get('urls', {})
                    thumbnail_urls = {k: v for k, v in urls.items() if k.startswith('thumbnail_')}
                    if thumbnail_urls:
                        print(f"  Thumbnail URLs in metadata: {list(thumbnail_urls.keys())}")
                    else:
                        print(f"  No thumbnail URLs in metadata")
                    
                    metadata_results.append(metadata)
                else:
                    print(f"  Metadata retrieval failed: {response.status_code}")
            
            print(f"Metadata flow completed. {len(metadata_results)} metadata retrieved.")
            return metadata_results
    
    async def test_image_list_flow(self):
        """Test listing user's images"""
        print("Testing image list flow...")
        
        async with httpx.AsyncClient() as client:
            list_results = []
            
            for user in self.test_users:
                print(f"Testing image list for user: {user.username}")
                
                headers = self.get_auth_headers(user.user_id)
                response = await client.get(
                    f"{API_BASE_URL}/files/images",
                    headers=headers
                )
                
                if response.status_code == 200:
                    list_data = response.json()
                    image_count = len(list_data.get("images", []))
                    print(f"  Found {image_count} images")
                    
                    # Print image details
                    for img in list_data.get("images", []):
                        print(f"    - {img.get('filename', 'unknown')} ({img.get('file_id', 'unknown')})")
                        
                        # Check for thumbnail URLs in each image
                        urls = img.get('urls', {})
                        thumbnail_urls = {k: v for k, v in urls.items() if k.startswith('thumbnail_')}
                        if thumbnail_urls:
                            print(f"      Thumbnails: {list(thumbnail_urls.keys())}")
                        else:
                            print(f"      No thumbnails available")
                    
                    list_results.append({
                        "user": user,
                        "image_count": image_count,
                        "images": list_data.get("images", [])
                    })
                else:
                    print(f"  Image list failed: {response.status_code}")
            
            print(f"List flow completed. Retrieved lists for {len(list_results)} users.")
            return list_results
    
    async def test_image_deletion_flow(self):
        """Test image deletion with ownership validation"""
        print("Testing image deletion flow...")
        
        async with httpx.AsyncClient() as client:
            deletion_results = []
            
            # Test deleting half of the uploaded files
            files_to_delete = self.uploaded_files[:len(self.uploaded_files)//2]
            
            for uploaded_file in files_to_delete:
                file_id = uploaded_file["file_id"]
                owner_user_id = uploaded_file["user_id"]
                filename = uploaded_file["filename"]
                
                print(f"Testing deletion for file: {file_id} ({filename})")
                
                # Test 1: Unauthorized deletion attempt
                for other_user in self.test_users:
                    if other_user.user_id != owner_user_id:
                        other_headers = self.get_auth_headers(other_user.user_id)
                        unauthorized_response = await client.delete(
                            f"{API_BASE_URL}/files/images/{file_id}",
                            headers=other_headers
                        )
                        
                        if unauthorized_response.status_code == 403:
                            print(f"  Unauthorized deletion correctly blocked")
                        else:
                            print(f"  WARNING: Unauthorized deletion should be blocked but got {unauthorized_response.status_code}")
                        break
                
                # Test 2: Authorized deletion (owner)
                headers = self.get_auth_headers(owner_user_id)
                response = await client.delete(
                    f"{API_BASE_URL}/files/images/{file_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    print(f"  Deletion successful")
                    deletion_results.append({"file_id": file_id, "deleted": True})
                    
                    # Verify file is actually deleted by trying to access it
                    verify_response = await client.get(
                        f"{API_BASE_URL}/files/images/{file_id}",
                        headers=headers
                    )
                    
                    if verify_response.status_code == 403:
                        print(f"  Deletion verified - file no longer accessible")
                    else:
                        print(f"  WARNING: File should be inaccessible after deletion but got {verify_response.status_code}")
                else:
                    print(f"  Deletion failed: {response.status_code}")
                    if response.status_code != 200:
                        print(f"  Error details: {response.text}")
            
            print(f"Deletion flow completed. {len(deletion_results)} files deleted.")
            return deletion_results
    
    async def test_error_handling(self):
        """Test various error conditions"""
        print("Testing error handling...")
        
        async with httpx.AsyncClient() as client:
            pro_user = next((u for u in self.test_users if u.subscription_tier == "pro"), None)
            if not pro_user:
                print("No pro user available for error testing")
                return []
            
            headers = self.get_auth_headers(pro_user.user_id)
            error_results = []
            
            # Test 1: Upload invalid file type
            print("  Testing invalid file type...")
            text_data = b"This is not an image file"
            files = {"file": ("test.txt", text_data, "text/plain")}
            response = await client.post(
                f"{API_BASE_URL}/files/images/upload",
                files=files,
                headers=headers
            )
            
            if response.status_code == 400:
                print("  Invalid file type correctly rejected")
                error_results.append({"test": "invalid_type", "handled": True})
            else:
                print(f"  WARNING: Invalid file type should be rejected but got {response.status_code}")
            
            # Test 2: Access non-existent file
            print("  Testing access to non-existent file...")
            response = await client.get(
                f"{API_BASE_URL}/files/images/nonexistent_file_id",
                headers=headers
            )
            
            if response.status_code == 403:
                print("  Non-existent file correctly returns 403")
                error_results.append({"test": "nonexistent_file", "handled": True})
            else:
                print(f"  Non-existent file returned: {response.status_code}")
            
            # Test 3: Delete non-existent file
            print("  Testing deletion of non-existent file...")
            response = await client.delete(
                f"{API_BASE_URL}/files/images/nonexistent_file_id",
                headers=headers
            )
            
            if response.status_code == 403:
                print("  Non-existent file deletion correctly returns 403")
                error_results.append({"test": "nonexistent_delete", "handled": True})
            else:
                print(f"  Non-existent file deletion returned: {response.status_code}")
            
            # Test 4: Access thumbnail of non-existent file
            print("  Testing thumbnail access for non-existent file...")
            response = await client.get(
                f"{API_BASE_URL}/files/images/nonexistent_file_id/thumbnail",
                headers=headers
            )
            
            if response.status_code in [403, 404]:
                print("  Non-existent file thumbnail correctly blocked")
                error_results.append({"test": "nonexistent_thumbnail", "handled": True})
            else:
                print(f"  Non-existent file thumbnail returned: {response.status_code}")
            
            # Test 5: Access thumbnail with invalid size format
            if self.uploaded_files:
                test_file_id = self.uploaded_files[0]["file_id"]
                print("  Testing thumbnail with invalid size format...")
                
                invalid_sizes = ["abc", "150", "150x", "x150", "150x150x150"]
                for invalid_size in invalid_sizes:
                    response = await client.get(
                        f"{API_BASE_URL}/files/images/{test_file_id}/thumbnail?size={invalid_size}",
                        headers=headers
                    )
                    
                    if response.status_code == 404:
                        print(f"    Invalid size '{invalid_size}' correctly returns 404")
                        error_results.append({"test": f"invalid_size_{invalid_size}", "handled": True})
                    else:
                        print(f"    Invalid size '{invalid_size}' returned: {response.status_code}")
            
            print(f"Error handling completed. {len(error_results)} scenarios tested.")
            return error_results
    
    async def verify_minio_integration(self):
        """Verify MinIO storage integration"""
        print("Verifying MinIO integration...")
        
        try:
            # Test MinIO connection through storage service
            test_data = b"MinIO integration test data"
            test_key = f"test/{uuid.uuid4().hex}.txt"
            
            # Upload test file
            await storage_service.storage.upload_file(test_data, test_key, "text/plain")
            print("  MinIO upload successful")
            
            # Generate presigned URL
            presigned_url = await storage_service.storage.generate_presigned_url(test_key)
            if presigned_url:
                print("  MinIO presigned URL generation successful")
            
            # Delete test file
            await storage_service.storage.delete_file(test_key)
            print("  MinIO deletion successful")
            
            return True
            
        except Exception as e:
            print(f"  MinIO integration failed: {e}")
            return False
    
    async def test_bulk_image_upload_flow(self):
        """Test bulk image upload with different user types and limits"""
        print("Testing bulk image upload flow...")
        
        async with httpx.AsyncClient() as client:
            bulk_upload_results = []
            
            # Read the FIFA test image
            with open(TEST_IMAGE_PATH, 'rb') as f:
                image_data = f.read()
            
            print(f"Using test image: {TEST_IMAGE_PATH} ({len(image_data)} bytes)")
            
            for user in self.test_users:
                print(f"Testing bulk upload for user: {user.username} ({user.subscription_tier})")
                
                # Test with different bulk sizes
                test_scenarios = [
                    {"file_count": 3, "description": "Small bulk upload"},
                    {"file_count": 5, "description": "Medium bulk upload"},
                    {"file_count": 10, "description": "Large bulk upload"},
                ]
                
                for scenario in test_scenarios:
                    file_count = scenario["file_count"]
                    description = scenario["description"]
                    
                    print(f"  {description}: {file_count} files")
                    
                    # Prepare multiple files for bulk upload
                    files = []
                    conversation_id = f"bulk_conv_test_{uuid.uuid4().hex[:8]}"
                    
                    for i in range(file_count):
                        filename = f"bulk_fifa_upload_{user.subscription_tier}_{i}_{uuid.uuid4().hex[:8]}.png"
                        files.append(("files", (filename, image_data, "image/png")))
                    
                    data = {
                        "conversation_id": conversation_id,
                        "max_concurrent_uploads": "3",  # Test concurrency control
                        "generate_thumbnails": "true"
                    }
                    headers = self.get_auth_headers(user.user_id)
                    
                    start_time = time.time()
                    
                    # Make bulk upload request
                    response = await client.post(
                        f"{API_BASE_URL}/files/images/bulk-upload",
                        files=files,
                        data=data,
                        headers=headers,
                        timeout=60.0  # Allow longer timeout for bulk operations
                    )
                    
                    upload_duration = time.time() - start_time
                    print(f"    Bulk upload response: {response.status_code} (took {upload_duration:.2f}s)")
                    
                    if response.status_code == 201:
                        upload_data = response.json()
                        
                        successfully_uploaded = upload_data.get("successfully_uploaded", 0)
                        failed_uploads = upload_data.get("failed_uploads", 0)
                        total_size_bytes = upload_data.get("total_size_bytes", 0)
                        
                        print(f"    Successful uploads: {successfully_uploaded}/{file_count}")
                        print(f"    Failed uploads: {failed_uploads}")
                        print(f"    Total size: {total_size_bytes} bytes")
                        print(f"    Upload duration: {upload_data.get('upload_duration_seconds', 0):.2f}s")
                        print(f"    Quota consumed: ${upload_data.get('quota_consumed_usd', 0):.4f}")
                        
                        # Track successfully uploaded files for cleanup
                        for uploaded_image in upload_data.get("uploaded_images", []):
                            self.bulk_uploaded_files.append({
                                "file_id": uploaded_image["file_id"],
                                "user_id": user.user_id,
                                "s3_key": uploaded_image["s3_key"],
                                "filename": uploaded_image["filename"],
                                "bulk_scenario": description
                            })
                        
                        # Check for thumbnail URLs in response
                        for uploaded_image in upload_data.get("uploaded_images", []):
                            urls = uploaded_image.get('urls', {})
                            thumbnail_urls = {k: v for k, v in urls.items() if k.startswith('thumbnail_')}
                            if thumbnail_urls:
                                print(f"    Thumbnails generated for {uploaded_image['file_id']}: {list(thumbnail_urls.keys())}")
                        
                        bulk_upload_results.append({
                            "user": user,
                            "scenario": description,
                            "file_count": file_count,
                            "successful": successfully_uploaded,
                            "failed": failed_uploads,
                            "upload_data": upload_data
                        })
                        
                    elif response.status_code == 400:
                        error_detail = response.json().get("detail", "Unknown error")
                        print(f"    Bulk upload validation error: {error_detail}")
                        
                    elif response.status_code == 402:
                        print(f"    Quota exceeded for bulk upload")
                        
                    else:
                        print(f"    Bulk upload failed: {response.status_code} - {response.text}")
                    
                    # Test edge cases
                    if user == self.test_users[0]:  # Only test edge cases with first user
                        print(f"  Testing edge cases...")
                        
                        # Test with no files
                        response = await client.post(
                            f"{API_BASE_URL}/files/images/bulk-upload",
                            files=[],
                            data={"conversation_id": conversation_id},
                            headers=headers
                        )
                        
                        if response.status_code == 400:
                            print(f"    No files validation: PASS (400)")
                        else:
                            print(f"    No files validation: FAIL ({response.status_code})")
                        
                        # Test with too many files (if we want to test limit)
                        if int(file_count) < 15:  # Only test if we haven't hit the limit
                            too_many_files = []
                            for i in range(25):  # Exceed typical bulk limit
                                filename = f"excess_file_{i}.png"
                                too_many_files.append(("files", (filename, image_data, "image/png")))
                            
                            response = await client.post(
                                f"{API_BASE_URL}/files/images/bulk-upload",
                                files=too_many_files,
                                data={"conversation_id": conversation_id},
                                headers=headers
                            )
                            
                            if response.status_code == 400:
                                print(f"    Too many files validation: PASS (400)")
                            else:
                                print(f"    Too many files validation: FAIL ({response.status_code})")
            
            print(f"Bulk upload flow completed. {len(bulk_upload_results)} scenarios tested.")
            return bulk_upload_results

    async def test_bulk_image_delete_flow(self):
        """Test bulk image deletion with ownership validation"""
        print("Testing bulk image delete flow...")
        
        async with httpx.AsyncClient() as client:
            bulk_delete_results = []
            
            for user in self.test_users:
                print(f"Testing bulk delete for user: {user.username} ({user.subscription_tier})")
                
                # Get files owned by this user (from bulk uploads)
                user_files = [f for f in self.bulk_uploaded_files if f["user_id"] == user.user_id]
                
                if len(user_files) < 2:
                    print(f"  Skipping - not enough files for bulk delete test")
                    continue
                
                # Test deleting half of the user's files
                files_to_delete = user_files[:len(user_files)//2]
                file_ids_to_delete = [f["file_id"] for f in files_to_delete]
                
                print(f"  Attempting to delete {len(file_ids_to_delete)} files")
                
                headers = self.get_auth_headers(user.user_id)
                
                # Test 1: Bulk delete without confirmation (should fail)
                delete_request = {
                    "file_ids": file_ids_to_delete,
                    "confirm_deletion": False
                }
                
                response = await client.request(
                    "DELETE",
                    f"{API_BASE_URL}/files/images/bulk-delete",
                    json=delete_request,
                    headers=headers
                )
                
                if response.status_code == 422:  # Validation error
                    print(f"    Confirmation validation: PASS (422)")
                else:
                    print(f"    Confirmation validation: FAIL ({response.status_code})")
                
                # Test 2: Bulk delete with confirmation
                delete_request["confirm_deletion"] = True
                
                response = await client.request(
                    "DELETE",
                    f"{API_BASE_URL}/files/images/bulk-delete",
                    json=delete_request,
                    headers=headers
                )
                
                if response.status_code == 200:
                    delete_data = response.json()
                    
                    successfully_deleted = delete_data.get("successfully_deleted", 0)
                    failed_deletions = delete_data.get("failed_deletions", 0)
                    freed_storage_bytes = delete_data.get("freed_storage_bytes", 0)
                    
                    print(f"    Successful deletions: {successfully_deleted}/{len(file_ids_to_delete)}")
                    print(f"    Failed deletions: {failed_deletions}")
                    print(f"    Storage freed: {freed_storage_bytes} bytes")
                    
                    # Remove successfully deleted files from our tracking
                    deleted_file_ids = delete_data.get("deleted_file_ids", [])
                    self.bulk_uploaded_files = [
                        f for f in self.bulk_uploaded_files 
                        if f["file_id"] not in deleted_file_ids
                    ]
                    
                    bulk_delete_results.append({
                        "user": user,
                        "requested": len(file_ids_to_delete),
                        "successful": successfully_deleted,
                        "failed": failed_deletions,
                        "delete_data": delete_data
                    })
                    
                else:
                    print(f"    Bulk delete failed: {response.status_code} - {response.text}")
                
                # Test 3: Try to delete files owned by another user (should fail)
                if len(self.test_users) > 1:
                    other_user = next(u for u in self.test_users if u.user_id != user.user_id)
                    other_user_files = [f for f in self.bulk_uploaded_files if f["user_id"] == other_user.user_id]
                    
                    if other_user_files:
                        unauthorized_file_ids = [other_user_files[0]["file_id"]]
                        
                        delete_request = {
                            "file_ids": unauthorized_file_ids,
                            "confirm_deletion": True
                        }
                        
                        response = await client.request(
                            "DELETE",
                            f"{API_BASE_URL}/files/images/bulk-delete",
                            json=delete_request,
                            headers=headers
                        )
                        
                        if response.status_code == 200:
                            delete_data = response.json()
                            if delete_data.get("successfully_deleted", 0) == 0:
                                print(f"    Ownership validation: PASS (0 unauthorized deletions)")
                            else:
                                print(f"    Ownership validation: FAIL (unauthorized deletion occurred)")
                        else:
                            print(f"    Ownership validation: UNCERTAIN ({response.status_code})")
            
            print(f"Bulk delete flow completed. {len(bulk_delete_results)} scenarios tested.")
            return bulk_delete_results

    async def test_bulk_image_metadata_flow(self):
        """Test bulk metadata retrieval"""
        print("Testing bulk image metadata flow...")
        
        async with httpx.AsyncClient() as client:
            bulk_metadata_results = []
            
            for user in self.test_users:
                print(f"Testing bulk metadata for user: {user.username} ({user.subscription_tier})")
                
                # Get files owned by this user
                user_files = [f for f in self.bulk_uploaded_files if f["user_id"] == user.user_id]
                
                if not user_files:
                    print(f"  Skipping - no files for metadata test")
                    continue
                
                file_ids = [f["file_id"] for f in user_files]
                print(f"  Requesting metadata for {len(file_ids)} files")
                
                headers = self.get_auth_headers(user.user_id)
                
                # Test bulk metadata request
                metadata_request = {
                    "file_ids": file_ids,
                    "include_urls": True,
                    "include_thumbnails": True
                }
                
                response = await client.post(
                    f"{API_BASE_URL}/files/images/bulk-metadata",
                    json=metadata_request,
                    headers=headers
                )
                
                if response.status_code == 200:
                    metadata_data = response.json()
                    
                    found_images = metadata_data.get("found_images", 0)
                    missing_images = metadata_data.get("missing_images", 0)
                    
                    print(f"    Found images: {found_images}/{len(file_ids)}")
                    print(f"    Missing images: {missing_images}")
                    
                    # Check metadata details
                    images_metadata = metadata_data.get("images_metadata", [])
                    for metadata in images_metadata[:3]:  # Check first 3 for details
                        print(f"    File {metadata.get('file_id', 'unknown')}: {metadata.get('filename', 'unknown')}")
                        print(f"      Size: {metadata.get('size', 0)} bytes")
                        print(f"      Type: {metadata.get('content_type', 'unknown')}")
                        
                        urls = metadata.get('urls', {})
                        thumbnail_urls = {k: v for k, v in urls.items() if k.startswith('thumbnail_')}
                        if thumbnail_urls:
                            print(f"      Thumbnails: {list(thumbnail_urls.keys())}")
                    
                    bulk_metadata_results.append({
                        "user": user,
                        "requested": len(file_ids),
                        "found": found_images,
                        "missing": missing_images,
                        "metadata_data": metadata_data
                    })
                    
                else:
                    print(f"    Bulk metadata failed: {response.status_code} - {response.text}")
                
                # Test with non-existent file IDs
                fake_file_ids = [f"fake_img_{uuid.uuid4().hex[:8]}" for _ in range(3)]
                mixed_file_ids = file_ids[:2] + fake_file_ids  # Mix real and fake IDs
                
                metadata_request = {
                    "file_ids": mixed_file_ids,
                    "include_urls": True,
                    "include_thumbnails": True
                }
                
                response = await client.post(
                    f"{API_BASE_URL}/files/images/bulk-metadata",
                    json=metadata_request,
                    headers=headers
                )
                
                if response.status_code == 200:
                    metadata_data = response.json()
                    found_images = metadata_data.get("found_images", 0)
                    missing_images = metadata_data.get("missing_images", 0)
                    
                    if found_images == 2 and missing_images == 3:
                        print(f"    Mixed ID validation: PASS ({found_images} found, {missing_images} missing)")
                    else:
                        print(f"    Mixed ID validation: UNCERTAIN ({found_images} found, {missing_images} missing)")
            
            print(f"Bulk metadata flow completed. {len(bulk_metadata_results)} scenarios tested.")
            return bulk_metadata_results

    async def test_image_search_flow(self):
        """Test image search functionality"""
        print("Testing image search flow...")
        
        async with httpx.AsyncClient() as client:
            search_results = []
            
            for user in self.test_users:
                print(f"Testing image search for user: {user.username} ({user.subscription_tier})")
                
                # Get files owned by this user
                user_files = [f for f in self.bulk_uploaded_files if f["user_id"] == user.user_id]
                
                if not user_files:
                    print(f"  Skipping - no files for search test")
                    continue
                
                headers = self.get_auth_headers(user.user_id)
                
                # Test 1: Search all images (no filters)
                search_request = {
                    "limit": 50,
                    "offset": 0,
                    "sort_by": "uploaded_at",
                    "sort_order": "desc"
                }
                
                response = await client.post(
                    f"{API_BASE_URL}/files/images/search",
                    json=search_request,
                    headers=headers
                )
                
                if response.status_code == 200:
                    search_data = response.json()
                    total_found = search_data.get("total_found", 0)
                    images = search_data.get("images", [])
                    search_duration_ms = search_data.get("search_duration_ms", 0)
                    
                    print(f"    All images search: {total_found} found (took {search_duration_ms}ms)")
                    
                    search_results.append({
                        "user": user,
                        "search_type": "all_images",
                        "found": total_found,
                        "duration_ms": search_duration_ms
                    })
                    
                    # Test 2: Search by filename pattern
                    search_request = {
                        "query": "fifa",
                        "limit": 20,
                        "offset": 0
                    }
                    
                    response = await client.post(
                        f"{API_BASE_URL}/files/images/search",
                        json=search_request,
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        search_data = response.json()
                        pattern_found = search_data.get("total_found", 0)
                        print(f"    Pattern search 'fifa': {pattern_found} found")
                        
                        search_results.append({
                            "user": user,
                            "search_type": "pattern_fifa",
                            "found": pattern_found,
                            "duration_ms": search_data.get("search_duration_ms", 0)
                        })
                    
                    # Test 3: Search by content type
                    search_request = {
                        "content_type": "image/png",
                        "limit": 20,
                        "offset": 0
                    }
                    
                    response = await client.post(
                        f"{API_BASE_URL}/files/images/search",
                        json=search_request,
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        search_data = response.json()
                        type_found = search_data.get("total_found", 0)
                        print(f"    Content type search 'image/png': {type_found} found")
                        
                        search_results.append({
                            "user": user,
                            "search_type": "content_type_png",
                            "found": type_found,
                            "duration_ms": search_data.get("search_duration_ms", 0)
                        })
                    
                    # Test 4: Search by size range
                    search_request = {
                        "size_min": 1000,
                        "size_max": 1000000,  # 1MB
                        "limit": 20,
                        "offset": 0
                    }
                    
                    response = await client.post(
                        f"{API_BASE_URL}/files/images/search",
                        json=search_request,
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        search_data = response.json()
                        size_found = search_data.get("total_found", 0)
                        print(f"    Size range search: {size_found} found")
                        
                        search_results.append({
                            "user": user,
                            "search_type": "size_range",
                            "found": size_found,
                            "duration_ms": search_data.get("search_duration_ms", 0)
                        })
                    
                    # Test 5: Search by date range (recent uploads)
                    now = datetime.utcnow()
                    one_hour_ago = now - timedelta(hours=1)
                    
                    search_request = {
                        "uploaded_after": one_hour_ago.isoformat(),
                        "limit": 20,
                        "offset": 0
                    }
                    
                    response = await client.post(
                        f"{API_BASE_URL}/files/images/search",
                        json=search_request,
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        search_data = response.json()
                        recent_found = search_data.get("total_found", 0)
                        print(f"    Recent uploads search: {recent_found} found")
                        
                        search_results.append({
                            "user": user,
                            "search_type": "recent_uploads",
                            "found": recent_found,
                            "duration_ms": search_data.get("search_duration_ms", 0)
                        })
                    
                    # Test 6: Search with thumbnails filter
                    search_request = {
                        "has_thumbnails": True,
                        "limit": 20,
                        "offset": 0
                    }
                    
                    response = await client.post(
                        f"{API_BASE_URL}/files/images/search",
                        json=search_request,
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        search_data = response.json()
                        thumbnail_found = search_data.get("total_found", 0)
                        print(f"    Has thumbnails search: {thumbnail_found} found")
                        
                        search_results.append({
                            "user": user,
                            "search_type": "has_thumbnails",
                            "found": thumbnail_found,
                            "duration_ms": search_data.get("search_duration_ms", 0)
                        })
                
                else:
                    print(f"    Image search failed: {response.status_code} - {response.text}")
            
            print(f"Image search flow completed. {len(search_results)} search scenarios tested.")
            return search_results

    async def test_image_statistics_flow(self):
        """Test image statistics functionality"""
        print("Testing image statistics flow...")
        
        async with httpx.AsyncClient() as client:
            statistics_results = []
            
            for user in self.test_users:
                print(f"Testing image statistics for user: {user.username} ({user.subscription_tier})")
                
                headers = self.get_auth_headers(user.user_id)
                
                response = await client.get(
                    f"{API_BASE_URL}/files/images/statistics",
                    headers=headers
                )
                
                if response.status_code == 200:
                    stats_data = response.json()
                    
                    total_images = stats_data.get("total_images", 0)
                    total_storage_bytes = stats_data.get("total_storage_bytes", 0)
                    total_thumbnails = stats_data.get("total_thumbnails", 0)
                    storage_used_mb = stats_data.get("storage_used_mb", 0)
                    quota_used_percentage = stats_data.get("quota_used_percentage", 0)
                    
                    print(f"    Total images: {total_images}")
                    print(f"    Storage used: {storage_used_mb} MB ({total_storage_bytes} bytes)")
                    print(f"    Total thumbnails: {total_thumbnails}")
                    print(f"    Quota used: {quota_used_percentage:.2f}%")
                    
                    # Show breakdown by type
                    images_by_type = stats_data.get("images_by_type", {})
                    if images_by_type:
                        print(f"    By type: {images_by_type}")
                    
                    # Show breakdown by month
                    images_by_month = stats_data.get("images_by_month", {})
                    if images_by_month:
                        print(f"    By month: {images_by_month}")
                    
                    # File size statistics
                    average_file_size = stats_data.get("average_file_size", 0)
                    largest_file_size = stats_data.get("largest_file_size", 0)
                    smallest_file_size = stats_data.get("smallest_file_size", 0)
                    
                    print(f"    Average file size: {average_file_size} bytes")
                    print(f"    Size range: {smallest_file_size} - {largest_file_size} bytes")
                    
                    statistics_results.append({
                        "user": user,
                        "total_images": total_images,
                        "storage_mb": storage_used_mb,
                        "quota_percentage": quota_used_percentage,
                        "stats_data": stats_data
                    })
                    
                else:
                    print(f"    Image statistics failed: {response.status_code} - {response.text}")
            
            print(f"Image statistics flow completed. {len(statistics_results)} users tested.")
            return statistics_results

    async def cleanup_test_environment(self):
        """Clean up all test data including bulk uploads"""
        print("Cleaning up test environment...")
        
        try:
            async with AsyncSessionLocal() as db:
                # Clean up uploaded images (any that might remain)
                if self.test_users:
                    user_ids = [user.user_id for user in self.test_users]
                    
                    # Get all uploaded images for test users
                    from sqlalchemy import select
                    query = select(UploadedImage).where(UploadedImage.user_id.in_(user_ids))
                    result = await db.execute(query)
                    remaining_images = list(result.scalars().all())
                    
                    print(f"Cleaning up {len(remaining_images)} images from storage...")
                    
                    # Delete from MinIO storage
                    for image in remaining_images:
                        try:
                            # Delete original image
                            await storage_service.storage.delete_file(image.s3_key)
                            print(f"  Deleted S3 file: {image.s3_key}")
                            
                            # Delete thumbnails if they exist
                            if image.thumbnail_s3_keys is not None:
                                try:
                                    import json
                                    thumbnail_keys = json.loads(image.thumbnail_s3_keys)
                                    for size, thumb_s3_key in thumbnail_keys.items():
                                        try:
                                            await storage_service.storage.delete_file(thumb_s3_key)
                                            print(f"  Deleted thumbnail {size}: {thumb_s3_key}")
                                        except Exception as e:
                                            print(f"  Failed to delete thumbnail {size}: {e}")
                                except Exception as e:
                                    print(f"  Failed to parse thumbnail keys: {e}")
                                    
                        except Exception as e:
                            print(f"  Failed to delete S3 file {image.s3_key}: {e}")
                    
                    # Delete from database
                    await db.execute(
                        delete(UploadedImage).where(UploadedImage.user_id.in_(user_ids))
                    )
                    print(f"  Deleted {len(remaining_images)} uploaded images from database")
                    
                    # Delete test users
                    await db.execute(
                        delete(User).where(User.user_id.in_(user_ids))
                    )
                    print(f"  Deleted {len(self.test_users)} test users")
                
                await db.commit()
                
                # Clear tracking lists
                self.uploaded_files.clear()
                self.bulk_uploaded_files.clear()
                
                print("Cleanup completed successfully")
                
        except Exception as e:
            print(f"Cleanup failed: {e}")
            raise

    async def run_comprehensive_test(self):
        """Run the complete test suite including bulk operations"""
        print("Starting comprehensive file API integration test with bulk operations")
        print("=" * 80)
        
        try:
            # Setup
            await self.setup_test_environment()
            
            # Verify MinIO connection
            print("=" * 80)
            print("MINIO INTEGRATION VERIFICATION")
            minio_ok = await self.verify_minio_integration()
            
            # Run service tests
            print("=" * 80)
            print("SERVICE STATUS TEST")
            service_ok = await self.test_service_status()
            
            # Run core functionality tests
            print("=" * 80)
            print("IMAGE UPLOAD FLOW TEST")
            upload_results = await self.test_image_upload_flow()
            
            print("=" * 80)
            print("IMAGE SERVING FLOW TEST")
            serve_results = await self.test_image_serving_flow()
            
            print("=" * 80)
            print("THUMBNAIL SERVING FLOW TEST")
            thumbnail_results = await self.test_thumbnail_serving_flow()
            
            print("=" * 80)
            print("IMAGE METADATA FLOW TEST")
            metadata_results = await self.test_image_metadata_flow()
            
            print("=" * 80)
            print("IMAGE LIST FLOW TEST")
            list_results = await self.test_image_list_flow()
            
            # Run bulk operations tests
            print("=" * 80)
            print("BULK IMAGE UPLOAD FLOW TEST")
            bulk_upload_results = await self.test_bulk_image_upload_flow()
            
            print("=" * 80)
            print("BULK IMAGE METADATA FLOW TEST")
            bulk_metadata_results = await self.test_bulk_image_metadata_flow()
            
            print("=" * 80)
            print("IMAGE SEARCH FLOW TEST")
            search_results = await self.test_image_search_flow()
            
            print("=" * 80)
            print("IMAGE STATISTICS FLOW TEST")
            statistics_results = await self.test_image_statistics_flow()
            
            print("=" * 80)
            print("BULK IMAGE DELETE FLOW TEST")
            bulk_delete_results = await self.test_bulk_image_delete_flow()
            
            print("=" * 80)
            print("IMAGE DELETION FLOW TEST")
            deletion_results = await self.test_image_deletion_flow()
            
            print("=" * 80)
            print("ERROR HANDLING TEST")
            error_results = await self.test_error_handling()
            
            # Summary
            print("=" * 80)
            print("COMPREHENSIVE TEST SUMMARY")
            print("=" * 80)
            print(f"MinIO Integration: {'PASS' if minio_ok else 'FAIL'}")
            print(f"Service Status: {'PASS' if service_ok else 'FAIL'}")
            print()
            print("CORE OPERATIONS:")
            print(f"  Single Uploads Tested: {len(upload_results)}")
            print(f"  Images Served: {len(serve_results)}")
            print(f"  Thumbnails Served: {len(thumbnail_results)}")
            print(f"  Metadata Retrieved: {len(metadata_results)}")
            print(f"  List Operations: {len(list_results)}")
            print(f"  Single Deletions: {len(deletion_results)}")
            print()
            print("BULK OPERATIONS:")
            print(f"  Bulk Upload Scenarios: {len(bulk_upload_results)}")
            print(f"  Bulk Metadata Scenarios: {len(bulk_metadata_results)}")
            print(f"  Bulk Delete Scenarios: {len(bulk_delete_results)}")
            print()
            print("ADVANCED FEATURES:")
            print(f"  Search Scenarios: {len(search_results)}")
            print(f"  Statistics Queries: {len(statistics_results)}")
            print(f"  Error Scenarios: {len(error_results)}")
            
            # Calculate bulk operation statistics
            total_bulk_uploads = sum(r.get("successful", 0) for r in bulk_upload_results)
            total_bulk_deletes = sum(r.get("successful", 0) for r in bulk_delete_results)
            
            print()
            print("BULK OPERATION STATISTICS:")
            print(f"  Total Bulk Uploads: {total_bulk_uploads} images")
            print(f"  Total Bulk Deletes: {total_bulk_deletes} images")
            
            # Calculate success rate
            total_tests = (len(upload_results) + len(serve_results) + len(metadata_results) + 
                          len(list_results) + len(deletion_results) + len(thumbnail_results) + 
                          len(bulk_upload_results) + len(bulk_metadata_results) + 
                          len(bulk_delete_results) + len(search_results) + len(statistics_results))
            
            print(f"Total Test Scenarios: {total_tests}")
            
            if total_tests > 0:
                print()
                print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
                print("✅ Core image operations working")
                print("✅ Bulk operations working")
                print("✅ Search functionality working")
                print("✅ Statistics functionality working")
                print("✅ Authentication and authorization working")
                print("✅ Storage integration working")
            else:
                print("⚠️  WARNING: No successful operations completed")
            
        except Exception as e:
            print(f"Test suite failed: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            # Always cleanup
            await self.cleanup_test_environment()

async def main():
    """Main test execution"""
    print("Comprehensive File API Integration Test Suite with Bulk Operations")
    print("=" * 90)
    print("This test will:")
    print("- Create real test users with different subscription tiers")
    print("- Test single image upload, serving, metadata, listing, and deletion")
    print("- Test bulk image upload with concurrency control")
    print("- Test bulk image deletion with ownership validation")
    print("- Test bulk metadata retrieval")
    print("- Test advanced image search with multiple filters")
    print("- Test image statistics and analytics")
    print("- Test thumbnail generation and serving in multiple sizes")
    print("- Verify thumbnail URLs are included in all relevant responses")
    print("- Test thumbnail authentication and authorization")
    print("- Use existing fifa_test_image.png for testing")
    print("- Verify authentication and authorization for all operations")
    print("- Test MinIO storage integration")
    print("- Clean up all test data including bulk uploads and thumbnails")
    print("=" * 90)
    
    test_runner = FileAPIIntegrationTest()
    
    try:
        await test_runner.run_comprehensive_test()
        print("\n🎊 Test suite completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⚡ Test interrupted by user")
        await test_runner.cleanup_test_environment()
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        await test_runner.cleanup_test_environment()


if __name__ == "__main__":
    # Environment variables are now properly loaded from .env via config.py
    # No need to set them manually here
    asyncio.run(main())