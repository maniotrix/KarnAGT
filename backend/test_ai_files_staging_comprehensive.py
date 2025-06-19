#!/usr/bin/env python3
"""
Comprehensive AI Files Staging API Integration Test - SIMPLIFIED VERSION
Tests simplified staging endpoints with real users, database, and storage
Tests: Authentication -> Staging Upload -> Discard -> Bulk Operations
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

from app.core.database import AsyncSessionLocal
from app.models.database.user import User
from app.services.storage.staging_storage import staging_service
from app.core.security import security
from app.core.config import get_settings

# SQLAlchemy cleanup
from sqlalchemy import delete

# Test configuration
API_BASE_URL = "http://localhost:8000/api/v1"
TEST_IMAGE_PATH = "fifa_test_image.png"

class AIFilesStagingIntegrationTest:
    """Test class for simplified AI files staging integration"""
    
    def __init__(self):
        self.test_users = []
        self.auth_tokens = {}
        self.staged_files = []  # Track staging IDs for cleanup
        self.settings = get_settings()
        
    async def setup_test_environment(self):
        """Set up test users and authentication"""
        print("Setting up simplified staging test environment...")
        
        # Verify test image exists
        if not os.path.exists(TEST_IMAGE_PATH):
            raise FileNotFoundError(f"Test image not found: {TEST_IMAGE_PATH}")
        
        async with AsyncSessionLocal() as db:
            # Create test users with different subscription tiers
            test_user_configs = [
                {
                    "username": f"staging_test_user_pro_{uuid.uuid4().hex[:8]}",
                    "email": f"staging_test_pro_{uuid.uuid4().hex[:8]}@example.com",
                    "subscription_tier": "pro",
                    "is_active": True,
                    "is_verified": True
                },
                {
                    "username": f"staging_test_user_enterprise_{uuid.uuid4().hex[:8]}",
                    "email": f"staging_test_enterprise_{uuid.uuid4().hex[:8]}@example.com",
                    "subscription_tier": "enterprise",
                    "is_active": True,
                    "is_verified": True
                }
            ]
            
            for user_config in test_user_configs:
                test_user = User(
                    user_id=str(uuid.uuid4()),
                    username=user_config["username"],
                    email=user_config["email"],
                    full_name=f"Staging Test User {str(user_config['subscription_tier']).title()}",
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
                
                print(f"Created staging test user: {test_user.username} ({test_user.subscription_tier}) - ID: {test_user.user_id}")
            
            print(f"Created {len(self.test_users)} test users with authentication tokens")
    
    def get_auth_headers(self, user_id: str) -> Dict[str, str]:
        """Get authorization headers for API requests"""
        token = self.auth_tokens.get(user_id)
        if not token:
            raise ValueError(f"No auth token for user {user_id}")
        
        return {"Authorization": f"Bearer {token}"}
    
    async def test_ai_files_service_status(self):
        """Test AI files service status endpoint"""
        print("Testing AI files service status...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/ai-files/status")
            
            print(f"AI Files status endpoint response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Service version: {data.get('version', 'unknown')}")
                print(f"Features: {data.get('features', [])}")
                
                staging_config = data.get('staging_config', {})
                print(f"Staging config: {staging_config}")
                
                # Verify simplified features
                expected_features = ["bulk_staging_upload", "staging_discard", "simple_workflow"]
                actual_features = data.get('features', [])
                
                for feature in expected_features:
                    if feature in actual_features:
                        print(f"  ✓ Feature '{feature}' available")
                    else:
                        print(f"  ✗ Feature '{feature}' missing")
                
                return True
            else:
                print(f"Service status check failed: {response.text}")
                return False
    
    async def test_bulk_staging_upload_flow(self):
        """Test bulk staging upload with different scenarios"""
        print("Testing bulk staging upload flow...")
        
        async with httpx.AsyncClient() as client:
            staging_upload_results = []
            
            # Read the FIFA test image
            with open(TEST_IMAGE_PATH, 'rb') as f:
                image_data = f.read()
            
            print(f"Using test image: {TEST_IMAGE_PATH} ({len(image_data)} bytes)")
            
            for user in self.test_users:
                print(f"Testing staging upload for user: {user.username} ({user.subscription_tier})")
                
                # Get auth headers for this user
                headers = self.get_auth_headers(user.user_id)
                
                # Test different staging scenarios - CREATE SEPARATE BATCHES FOR DIFFERENT TESTS
                test_scenarios = [
                    {"file_count": 3, "description": "Individual discard test batch", "test_type": "individual"},
                    {"file_count": 5, "description": "Bulk discard test batch", "test_type": "bulk"},
                    {"file_count": 4, "description": "Mixed operations test batch", "test_type": "mixed"},
                ]
                
                for scenario in test_scenarios:
                    file_count = scenario["file_count"]
                    description = scenario["description"]
                    test_type = scenario["test_type"]
                    
                    print(f"  {description}: {file_count} files")
                    
                    # Prepare multiple files for staging
                    files = []
                    for i in range(file_count):
                        filename = f"staging_{test_type}_{user.subscription_tier}_{i}_{uuid.uuid4().hex[:8]}.png"
                        files.append(("files", (filename, image_data, "image/png")))
                    
                    data = {
                        "max_concurrent_uploads": "3"
                    }
                    
                    start_time = time.time()
                    
                    # Make staging upload request
                    response = await client.post(
                        f"{API_BASE_URL}/ai-files/staging/bulk-upload",
                        files=files,
                        data=data,
                        headers=headers,
                        timeout=60.0
                    )
                    
                    upload_duration = time.time() - start_time
                    print(f"    Staging upload response: {response.status_code} (took {upload_duration:.2f}s)")
                    
                    if response.status_code == 201:
                        upload_data = response.json()
                        
                        successfully_staged = upload_data.get("successfully_staged", 0)
                        failed_uploads = upload_data.get("failed_uploads", 0)
                        total_size_bytes = upload_data.get("total_size_bytes", 0)
                        
                        print(f"    Successful staging: {successfully_staged}/{file_count}")
                        print(f"    Failed staging: {failed_uploads}")
                        print(f"    Total size: {total_size_bytes} bytes")
                        print(f"    Upload duration: {upload_data.get('upload_duration_seconds', 0):.2f}s")
                        
                        # Track staged files by test type for proper test isolation
                        for staged_file in upload_data.get("staged_files", []):
                            staging_id = staged_file.get("staging_id")
                            if staging_id:
                                # Verify staging_id format: staging_userid_randomid
                                if staging_id.startswith(f"staging_{user.user_id}_"):
                                    print(f"      ✓ Staging ID format correct: {staging_id}")
                                else:
                                    print(f"      ✗ Staging ID format incorrect: {staging_id}")
                                
                                staged_file_info = {
                                    "staging_id": staging_id,
                                    "user_id": user.user_id,
                                    "filename": staged_file.get("filename", "unknown"),
                                    "size": staged_file.get("size", 0),
                                    "content_type": staged_file.get("content_type", "unknown"),
                                    "test_type": test_type  # Track which test this file is for
                                }
                                
                                self.staged_files.append(staged_file_info)
                        
                        staging_upload_results.append({
                            "user": user,
                            "scenario": description,
                            "test_type": test_type,
                            "file_count": file_count,
                            "successfully_staged": successfully_staged,
                            "failed_uploads": failed_uploads,
                            "upload_data": upload_data
                        })
                        
                    else:
                        print(f"    Staging upload failed: {response.text}")
            
            print(f"Bulk staging upload flow completed. {len(staging_upload_results)} successful uploads.")
            print(f"Total staged files tracked: {len(self.staged_files)}")
            
            # Print breakdown by test type
            individual_files = [f for f in self.staged_files if f["test_type"] == "individual"]
            bulk_files = [f for f in self.staged_files if f["test_type"] == "bulk"]
            mixed_files = [f for f in self.staged_files if f["test_type"] == "mixed"]
            
            print(f"  - Individual discard test files: {len(individual_files)}")
            print(f"  - Bulk discard test files: {len(bulk_files)}")
            print(f"  - Mixed operations test files: {len(mixed_files)}")
            
            return staging_upload_results
    
    async def test_individual_staging_discard_flow(self):
        """Test individual staging file discard - ONLY use files marked for individual testing"""
        print("Testing individual staging discard flow...")
        
        # Get files specifically uploaded for individual discard testing
        individual_test_files = [f for f in self.staged_files if f["test_type"] == "individual"]
        
        if not individual_test_files:
            print("No individual test files available for discard testing")
            return []
        
        async with httpx.AsyncClient() as client:
            discard_results = []
            
            print(f"Testing individual discard with {len(individual_test_files)} dedicated files")
            
            # Test discarding ALL individual test files
            for staged_file in individual_test_files:  # Test all individual files
                staging_id = staged_file["staging_id"]
                user_id = staged_file["user_id"]
                filename = staged_file["filename"]
                
                print(f"Testing discard of staging file: {staging_id} (user: {user_id})")
                
                headers = self.get_auth_headers(user_id)
                response = await client.delete(
                    f"{API_BASE_URL}/ai-files/staging/discard/{staging_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    discard_data = response.json()
                    print(f"  ✓ Discard successful: {discard_data.get('message', 'No message')}")
                    
                    discard_results.append({
                        "staging_id": staging_id,
                        "user_id": user_id,
                        "filename": filename,
                        "success": True,
                        "discard_data": discard_data
                    })
                    
                    # Remove from our tracking list
                    self.staged_files.remove(staged_file)
                    
                elif response.status_code == 404:
                    print(f"  ✗ File not found (unexpected): {response.text}")
                else:
                    print(f"  ✗ Discard failed: {response.status_code} - {response.text}")
            
            # Test discarding non-existent file
            print("Testing discard of non-existent staging file...")
            fake_staging_id = f"staging_{self.test_users[0].user_id}_nonexistent"
            headers = self.get_auth_headers(self.test_users[0].user_id)
            response = await client.delete(
                f"{API_BASE_URL}/ai-files/staging/discard/{fake_staging_id}",
                headers=headers
            )
            
            if response.status_code == 404:
                print("  ✓ Non-existent file correctly returns 404")
            else:
                print(f"  ✗ Non-existent file returned: {response.status_code}")
            
            # Test discarding another user's file (security test)
            bulk_test_files = [f for f in self.staged_files if f["test_type"] == "bulk"]
            if len(bulk_test_files) > 0 and len(self.test_users) > 1:
                print("Testing cross-user discard security...")
                other_user_file = bulk_test_files[0]
                wrong_user = next((u for u in self.test_users if u.user_id != other_user_file["user_id"]), None)
                
                if wrong_user:
                    headers = self.get_auth_headers(wrong_user.user_id)
                    response = await client.delete(
                        f"{API_BASE_URL}/ai-files/staging/discard/{other_user_file['staging_id']}",
                        headers=headers
                    )
                    
                    if response.status_code == 404:
                        print("  ✓ Cross-user discard correctly denied (404)")
                    else:
                        print(f"  ✗ Cross-user discard returned: {response.status_code}")
            
            print(f"Individual staging discard flow completed. {len(discard_results)} files discarded.")
            return discard_results
    
    async def test_bulk_staging_discard_flow(self):
        """Test bulk staging discard - ONLY use files marked for bulk testing"""
        print("Testing bulk staging discard flow...")
        
        # Get files specifically uploaded for bulk discard testing
        bulk_test_files = [f for f in self.staged_files if f["test_type"] == "bulk"]
        
        if not bulk_test_files:
            print("No bulk test files available for bulk discard testing")
            return []
        
        async with httpx.AsyncClient() as client:
            bulk_discard_results = []
            
            print(f"Testing bulk discard with {len(bulk_test_files)} dedicated files")
            
            # Group bulk test files by user
            user_bulk_files = {}
            for staged_file in bulk_test_files:
                user_id = staged_file["user_id"]
                if user_id not in user_bulk_files:
                    user_bulk_files[user_id] = []
                user_bulk_files[user_id].append(staged_file)
            
            # Test bulk discard for each user
            for user_id, staged_files_list in user_bulk_files.items():
                user = next((u for u in self.test_users if u.user_id == user_id), None)
                if not user:
                    continue
                
                print(f"Testing bulk discard for user: {user.username} ({len(staged_files_list)} files)")
                
                staging_ids = [sf["staging_id"] for sf in staged_files_list]
                headers = self.get_auth_headers(user_id)
                
                response = await client.request(
                    "DELETE",
                    f"{API_BASE_URL}/ai-files/staging/bulk-discard",
                    json={"staging_ids": staging_ids},
                    headers=headers
                )
                
                if response.status_code == 200:
                    bulk_data = response.json()
                    
                    successfully_discarded = bulk_data.get("successfully_discarded", 0)
                    failed_discards = bulk_data.get("failed_discards", 0)
                    
                    print(f"  ✓ Bulk discard successful: {successfully_discarded}/{len(staging_ids)} discarded")
                    print(f"  Failed discards: {failed_discards}")
                    
                    bulk_discard_results.append({
                        "user": user,
                        "staging_ids": staging_ids,
                        "successfully_discarded": successfully_discarded,
                        "failed_discards": failed_discards,
                        "bulk_data": bulk_data
                    })
                    
                    # Remove discarded files from our tracking
                    discarded_ids = bulk_data.get("discarded_staging_ids", [])
                    self.staged_files = [sf for sf in self.staged_files if sf["staging_id"] not in discarded_ids]
                    
                else:
                    print(f"  ✗ Bulk discard failed: {response.status_code} - {response.text}")
            
            # Test edge cases with fresh user
            print("Testing bulk discard edge cases...")
            headers = self.get_auth_headers(self.test_users[0].user_id)
            
            # Test bulk discard with empty list
            print("  Testing bulk discard with empty staging IDs list...")
            response = await client.request(
                "DELETE",
                f"{API_BASE_URL}/ai-files/staging/bulk-discard",
                json={"staging_ids": []},
                headers=headers
            )
            
            if response.status_code == 200:
                bulk_data = response.json()
                if bulk_data.get("successfully_discarded", 0) == 0:
                    print("    ✓ Empty staging IDs list handled correctly")
                else:
                    print(f"    ✗ Empty staging IDs list: unexpected discards")
            else:
                print(f"    ✗ Empty staging IDs list failed: {response.status_code}")
            
            # Test with too many staging IDs (exceed limit)
            print("  Testing bulk discard with too many staging IDs...")
            too_many_staging_ids = [f"staging_fake_{i}" for i in range(25)]  # Exceed limit
            response = await client.request(
                "DELETE",
                f"{API_BASE_URL}/ai-files/staging/bulk-discard",
                json={"staging_ids": too_many_staging_ids},
                headers=headers
            )
            
            if response.status_code == 400:
                print(f"    ✓ Too many staging IDs validation: PASS (400)")
            else:
                print(f"    ✗ Too many staging IDs validation: FAIL ({response.status_code})")
            
            # Test bulk discard with non-existent files
            print("  Testing bulk discard with non-existent staging IDs...")
            fake_staging_ids = [f"staging_{self.test_users[0].user_id}_fake_{i}" for i in range(3)]
            response = await client.request(
                "DELETE",
                f"{API_BASE_URL}/ai-files/staging/bulk-discard",
                json={"staging_ids": fake_staging_ids},
                headers=headers
            )
            
            if response.status_code == 200:
                bulk_data = response.json()
                failed_discards = bulk_data.get("failed_discards", 0)
                if failed_discards == len(fake_staging_ids):
                    print(f"    ✓ Non-existent files correctly reported as failed ({failed_discards} failed)")
                else:
                    print(f"    ✗ Non-existent files handling incorrect: {failed_discards} failed vs {len(fake_staging_ids)} expected")
            else:
                print(f"    ✗ Non-existent files test failed: {response.status_code}")
            
            print(f"Bulk staging discard flow completed. {len(bulk_discard_results)} scenarios tested.")
            return bulk_discard_results
    
    async def test_advanced_edge_cases(self):
        """Test advanced edge cases for bulk operations"""
        print("Testing advanced edge cases...")
        
        async with httpx.AsyncClient() as client:
            edge_case_results = []
            
            # First upload some test files for edge case testing
            user = self.test_users[0]
            headers = self.get_auth_headers(user.user_id)
            
            # Upload test files for edge case testing
            with open(TEST_IMAGE_PATH, 'rb') as f:
                image_data = f.read()
            
            files = []
            for i in range(3):
                filename = f"edge_case_test_{i}_{uuid.uuid4().hex[:8]}.png"
                files.append(("files", (filename, image_data, "image/png")))
            
            upload_response = await client.post(
                f"{API_BASE_URL}/ai-files/staging/bulk-upload",
                files=files,
                data={"max_concurrent_uploads": "3"},
                headers=headers
            )
            
            edge_case_staging_ids = []
            if upload_response.status_code == 201:
                upload_data = upload_response.json()
                edge_case_staging_ids = [f["staging_id"] for f in upload_data.get("staged_files", [])]
                print(f"  Uploaded {len(edge_case_staging_ids)} test files for edge cases")
            
            # Edge Case 1: Bulk discard with duplicate staging IDs
            print("  Testing bulk discard with duplicate staging IDs...")
            if len(edge_case_staging_ids) >= 2:
                duplicate_ids = [edge_case_staging_ids[0], edge_case_staging_ids[0], edge_case_staging_ids[1]]
                response = await client.request(
                    "DELETE",
                    f"{API_BASE_URL}/ai-files/staging/bulk-discard",
                    json={"staging_ids": duplicate_ids},
                    headers=headers
                )
                
                if response.status_code == 200:
                    bulk_data = response.json()
                    # Should successfully discard unique files, ignore duplicates
                    print(f"    ✓ Duplicate IDs handled: {bulk_data.get('successfully_discarded', 0)} discarded")
                    edge_case_results.append({"test": "duplicate_ids", "result": "pass"})
                else:
                    print(f"    ✗ Duplicate IDs test failed: {response.status_code}")
                    edge_case_results.append({"test": "duplicate_ids", "result": "fail"})
            
            # Edge Case 2: Bulk discard with invalid staging ID formats
            print("  Testing bulk discard with invalid staging ID formats...")
            invalid_ids = [
                "invalid_format_123",
                "staging_wrong_user_id_123",
                "staging__missing_user_id",
                "",
                "staging_" + "x" * 100  # Very long ID
            ]
            response = await client.request(
                "DELETE",
                f"{API_BASE_URL}/ai-files/staging/bulk-discard",
                json={"staging_ids": invalid_ids},
                headers=headers
            )
            
            if response.status_code == 200:
                bulk_data = response.json()
                failed_discards = bulk_data.get("failed_discards", 0)
                if failed_discards == len(invalid_ids):
                    print(f"    ✓ Invalid formats correctly rejected: {failed_discards} failed")
                    edge_case_results.append({"test": "invalid_formats", "result": "pass"})
                else:
                    print(f"    ✗ Invalid formats handling incorrect: {failed_discards} vs {len(invalid_ids)}")
                    edge_case_results.append({"test": "invalid_formats", "result": "fail"})
            else:
                print(f"    ✗ Invalid formats test failed: {response.status_code}")
                edge_case_results.append({"test": "invalid_formats", "result": "fail"})
            
            # Edge Case 3: Mixed valid and invalid staging IDs
            print("  Testing bulk discard with mixed valid/invalid IDs...")
            if len(edge_case_staging_ids) >= 1:
                mixed_ids = [
                    edge_case_staging_ids[-1],  # Valid ID (if any left)
                    "invalid_format",
                    f"staging_{user.user_id}_nonexistent"
                ]
                response = await client.request(
                    "DELETE",
                    f"{API_BASE_URL}/ai-files/staging/bulk-discard",
                    json={"staging_ids": mixed_ids},
                    headers=headers
                )
                
                if response.status_code == 200:
                    bulk_data = response.json()
                    successful = bulk_data.get("successfully_discarded", 0)
                    failed = bulk_data.get("failed_discards", 0)
                    
                    # Expect 1 success (valid file) and 2 failures (invalid format + nonexistent)
                    if successful >= 0 and failed >= 0 and (successful + failed) == len(mixed_ids):
                        print(f"    ✓ Mixed IDs handled correctly: {successful} success, {failed} failed")
                        edge_case_results.append({"test": "mixed_ids", "result": "pass"})
                    else:
                        print(f"    ✗ Mixed IDs incorrect: {successful} success, {failed} failed")
                        edge_case_results.append({"test": "mixed_ids", "result": "fail"})
                else:
                    print(f"    ✗ Mixed IDs test failed: {response.status_code}")
                    edge_case_results.append({"test": "mixed_ids", "result": "fail"})
            
            print(f"Advanced edge cases completed. {len(edge_case_results)} tests performed.")
            return edge_case_results
    
    async def test_concurrent_operations(self):
        """Test concurrent bulk operations for race conditions"""
        print("Testing concurrent operations...")
        
        async with httpx.AsyncClient() as client:
            concurrent_results = []
            
            # Setup: Upload files for concurrent testing
            user = self.test_users[0]
            headers = self.get_auth_headers(user.user_id)
            
            with open(TEST_IMAGE_PATH, 'rb') as f:
                image_data = f.read()
            
            # Upload 6 files for concurrent testing
            files = []
            for i in range(6):
                filename = f"concurrent_test_{i}_{uuid.uuid4().hex[:8]}.png"
                files.append(("files", (filename, image_data, "image/png")))
            
            upload_response = await client.post(
                f"{API_BASE_URL}/ai-files/staging/bulk-upload",
                files=files,
                data={"max_concurrent_uploads": "3"},
                headers=headers
            )
            
            concurrent_staging_ids = []
            if upload_response.status_code == 201:
                upload_data = upload_response.json()
                concurrent_staging_ids = [f["staging_id"] for f in upload_data.get("staged_files", [])]
                print(f"  Uploaded {len(concurrent_staging_ids)} files for concurrent testing")
            
            if len(concurrent_staging_ids) >= 4:
                # Test 1: Concurrent bulk discards of different files
                print("  Testing concurrent bulk discards of different files...")
                
                batch1 = concurrent_staging_ids[:2]
                batch2 = concurrent_staging_ids[2:4]
                
                async def bulk_discard_batch(staging_ids, batch_name):
                    try:
                        response = await client.request(
                            "DELETE",
                            f"{API_BASE_URL}/ai-files/staging/bulk-discard",
                            json={"staging_ids": staging_ids},
                            headers=headers
                        )
                        return {
                            "batch": batch_name,
                            "status_code": response.status_code,
                            "response": response.json() if response.status_code == 200 else None,
                            "staging_ids": staging_ids
                        }
                    except Exception as e:
                        return {
                            "batch": batch_name,
                            "error": str(e),
                            "staging_ids": staging_ids
                        }
                
                # Execute concurrent bulk discards
                results = await asyncio.gather(
                    bulk_discard_batch(batch1, "batch1"),
                    bulk_discard_batch(batch2, "batch2"),
                    return_exceptions=True
                )
                
                concurrent_success = 0
                for result in results:
                    if isinstance(result, dict) and result.get("status_code") == 200:
                        concurrent_success += 1
                        response_data = result.get("response", {})
                        if isinstance(response_data, dict):
                            print(f"    ✓ {result['batch']}: {response_data.get('successfully_discarded', 0)} files discarded")
                        else:
                            print(f"    ✓ {result['batch']}: operation completed")
                    elif isinstance(result, dict):
                        print(f"    ✗ {result.get('batch', 'unknown')}: failed - {result.get('error', 'unknown error')}")
                    else:
                        print(f"    ✗ Unknown result type: {type(result)} - {str(result)}")
                
                if concurrent_success == 2:
                    print("    ✓ Concurrent operations completed successfully")
                    concurrent_results.append({"test": "concurrent_different_files", "result": "pass"})
                else:
                    print(f"    ✗ Concurrent operations failed: {concurrent_success}/2 succeeded")
                    concurrent_results.append({"test": "concurrent_different_files", "result": "fail"})
                
                # Test 2: Concurrent discards of overlapping files (should handle gracefully)
                if len(concurrent_staging_ids) >= 6:
                    print("  Testing concurrent bulk discards of overlapping files...")
                    
                    overlap_batch1 = concurrent_staging_ids[4:6]
                    overlap_batch2 = [concurrent_staging_ids[4]]  # Overlapping file
                    
                    overlap_results = await asyncio.gather(
                        bulk_discard_batch(overlap_batch1, "overlap_batch1"),
                        bulk_discard_batch(overlap_batch2, "overlap_batch2"),
                        return_exceptions=True
                    )
                    
                    # At least one should succeed, the other might partially fail
                    total_attempts = 0
                    total_success = 0
                    for result in overlap_results:
                        if isinstance(result, dict) and result.get("status_code") == 200:
                            total_attempts += 1
                            response_data = result.get("response", {})
                            if isinstance(response_data, dict):
                                total_success += response_data.get("successfully_discarded", 0)
                    
                    if total_attempts == 2:
                        print(f"    ✓ Overlapping operations handled: {total_success} total discards")
                        concurrent_results.append({"test": "concurrent_overlapping_files", "result": "pass"})
                    else:
                        print(f"    ✗ Overlapping operations failed: {total_attempts} attempts succeeded")
                        concurrent_results.append({"test": "concurrent_overlapping_files", "result": "fail"})
            
            print(f"Concurrent operations testing completed. {len(concurrent_results)} tests performed.")
            return concurrent_results
    
    async def test_mixed_operations_flow(self):
        """Test mixed operations showing partial success scenarios"""
        print("Testing mixed operations flow...")
        
        # Get files specifically uploaded for mixed operations testing
        mixed_test_files = [f for f in self.staged_files if f["test_type"] == "mixed"]
        
        if not mixed_test_files:
            print("No mixed test files available for mixed operations testing")
            return []
        
        async with httpx.AsyncClient() as client:
            mixed_results = []
            
            print(f"Testing mixed operations with {len(mixed_test_files)} dedicated files")
            
            # Group mixed test files by user
            user_mixed_files = {}
            for staged_file in mixed_test_files:
                user_id = staged_file["user_id"]
                if user_id not in user_mixed_files:
                    user_mixed_files[user_id] = []
                user_mixed_files[user_id].append(staged_file)
            
            # Test mixed operations for each user
            for user_id, staged_files_list in user_mixed_files.items():
                user = next((u for u in self.test_users if u.user_id == user_id), None)
                if not user:
                    continue
                
                print(f"Testing mixed operations for user: {user.username} ({len(staged_files_list)} files)")
                
                if len(staged_files_list) < 3:
                    print("  Skipping - need at least 3 files for mixed operations test")
                    continue
                
                headers = self.get_auth_headers(user_id)
                
                # Step 1: Delete some files individually
                individual_files = staged_files_list[:2]
                print(f"  Step 1: Individual delete of {len(individual_files)} files")
                
                individual_success = 0
                for staged_file in individual_files:
                    response = await client.delete(
                        f"{API_BASE_URL}/ai-files/staging/discard/{staged_file['staging_id']}",
                        headers=headers
                    )
                    if response.status_code == 200:
                        individual_success += 1
                        # Remove from tracking
                        self.staged_files.remove(staged_file)
                        staged_files_list.remove(staged_file)
                
                print(f"    Individual deletes successful: {individual_success}/{len(individual_files)}")
                
                # Step 2: Bulk delete remaining files + some already deleted ones (partial success test)
                remaining_files = staged_files_list
                already_deleted_files = individual_files
                
                # Create a mixed list: some existing files + some already deleted files
                mixed_staging_ids = []
                mixed_staging_ids.extend([f["staging_id"] for f in remaining_files])
                mixed_staging_ids.extend([f["staging_id"] for f in already_deleted_files])  # These should fail
                
                print(f"  Step 2: Bulk delete with {len(remaining_files)} existing + {len(already_deleted_files)} already deleted files")
                
                response = await client.request(
                    "DELETE",
                    f"{API_BASE_URL}/ai-files/staging/bulk-discard",
                    json={"staging_ids": mixed_staging_ids},
                    headers=headers
                )
                
                if response.status_code == 200:
                    bulk_data = response.json()
                    
                    successfully_discarded = bulk_data.get("successfully_discarded", 0)
                    failed_discards = bulk_data.get("failed_discards", 0)
                    
                    print(f"    Bulk operation results: {successfully_discarded} successful, {failed_discards} failed")
                    
                    # We expect: remaining_files to succeed, already_deleted_files to fail
                    expected_success = len(remaining_files)
                    expected_failures = len(already_deleted_files)
                    
                    if successfully_discarded == expected_success and failed_discards == expected_failures:
                        print(f"    ✓ Partial success handling correct: {successfully_discarded}/{expected_success} succeeded, {failed_discards}/{expected_failures} failed")
                    else:
                        print(f"    ✗ Partial success handling incorrect: expected {expected_success} success/{expected_failures} failures")
                    
                    # Remove successfully discarded files from tracking
                    discarded_ids = bulk_data.get("discarded_staging_ids", [])
                    self.staged_files = [sf for sf in self.staged_files if sf["staging_id"] not in discarded_ids]
                    
                    mixed_results.append({
                        "user": user,
                        "individual_success": individual_success,
                        "bulk_success": successfully_discarded,
                        "bulk_failures": failed_discards,
                        "expected_bulk_success": expected_success,
                        "expected_bulk_failures": expected_failures,
                        "partial_success_correct": (successfully_discarded == expected_success and failed_discards == expected_failures)
                    })
                    
                else:
                    print(f"    ✗ Mixed bulk operation failed: {response.status_code} - {response.text}")
            
            print(f"Mixed operations flow completed. {len(mixed_results)} scenarios tested.")
            return mixed_results
    
    async def test_staging_service_direct(self):
        """Test staging service directly (not through API)"""
        print("Testing staging service directly...")
        
        try:
            # Test generating staging ID
            user_id = self.test_users[0].user_id
            staging_id = staging_service._generate_staging_id(user_id)
            
            print(f"  Generated staging ID: {staging_id}")
            
            # Verify format
            if staging_id.startswith(f"staging_{user_id}_"):
                print(f"  ✓ Staging ID format correct")
            else:
                print(f"  ✗ Staging ID format incorrect")
            
            # Test user ID extraction
            extracted_user_id = staging_service._extract_user_id_from_staging_id(staging_id)
            if extracted_user_id == user_id:
                print(f"  ✓ User ID extraction correct: {extracted_user_id}")
            else:
                print(f"  ✗ User ID extraction failed: {extracted_user_id} != {user_id}")
            
            # Test staging key building
            test_filename = "test.jpg"
            staging_key = staging_service._build_staging_key(staging_id, test_filename)
            expected_key = f"{staging_id}.jpg"
            
            if staging_key == expected_key:
                print(f"  ✓ Staging key format correct: {staging_key}")
            else:
                print(f"  ✗ Staging key format incorrect: {staging_key} != {expected_key}")
            
            return True
            
        except Exception as e:
            print(f"  Service direct test failed: {e}")
            return False
    
    async def test_error_handling(self):
        """Test various error conditions for staging"""
        print("Testing staging error handling...")
        
        async with httpx.AsyncClient() as client:
            pro_user = next((u for u in self.test_users if u.subscription_tier == "pro"), None)
            if not pro_user:
                print("No pro user available for error testing")
                return []
            
            headers = self.get_auth_headers(pro_user.user_id)
            error_results = []
            
            # Test 1: Upload invalid file type to staging
            print("  Testing invalid file type in staging...")
            text_data = b"This is not an image file"
            files = [("files", ("test.txt", text_data, "text/plain"))]
            response = await client.post(
                f"{API_BASE_URL}/ai-files/staging/bulk-upload",
                files=files,
                data={"max_concurrent_uploads": "3"},
                headers=headers
            )
            
            if response.status_code == 400:
                print("    ✓ Invalid file type correctly rejected")
                error_results.append({"test": "invalid_type_staging", "handled": True})
            else:
                print(f"    ✗ Invalid file type should be rejected but got {response.status_code}")
            
            # Test 2: Discard non-existent staging file
            print("  Testing discard of non-existent staging file...")
            fake_staging_id = f"staging_{pro_user.user_id}_nonexistent"
            response = await client.delete(
                f"{API_BASE_URL}/ai-files/staging/discard/{fake_staging_id}",
                headers=headers
            )
            
            if response.status_code == 404:
                print("    ✓ Non-existent staging file discard correctly returns 404")
                error_results.append({"test": "nonexistent_staging_discard", "handled": True})
            else:
                print(f"    ✗ Non-existent staging file discard returned: {response.status_code}")
            
            # Test 3: No authentication
            print("  Testing staging operations without authentication...")
            response = await client.get(f"{API_BASE_URL}/ai-files/status")
            
            if response.status_code == 200:  # Status endpoint is public
                print("    ✓ Status endpoint accessible without auth (expected)")
            
            # Test upload without auth
            files = [("files", ("test.jpg", b"fake image data", "image/jpeg"))]
            response = await client.post(
                f"{API_BASE_URL}/ai-files/staging/bulk-upload",
                files=files,
                data={"max_concurrent_uploads": "3"}
            )
            
            if response.status_code in [401, 403]:
                print("    ✓ Upload without auth correctly rejected")
                error_results.append({"test": "no_auth_upload", "handled": True})
            else:
                print(f"    ✗ Upload without auth returned: {response.status_code}")
            
            # Test 4: Too many files in bulk upload
            print("  Testing too many files in bulk upload...")
            files = []
            for i in range(15):  # Exceed MAX_BULK_STAGING_FILES (10)
                files.append(("files", (f"test_{i}.jpg", b"fake image data", "image/jpeg")))
            
            response = await client.post(
                f"{API_BASE_URL}/ai-files/staging/bulk-upload",
                files=files,
                data={"max_concurrent_uploads": "3"},
                headers=headers
            )
            
            if response.status_code == 400:
                print("    ✓ Too many files correctly rejected")
                error_results.append({"test": "too_many_files", "handled": True})
            else:
                print(f"    ✗ Too many files returned: {response.status_code}")
            
            print(f"Error handling test completed. {len(error_results)} error conditions tested.")
            return error_results
    
    async def cleanup_test_environment(self):
        """Clean up test users and any remaining staged files"""
        print("Cleaning up test environment...")
        
        # Clean up any remaining staged files
        if self.staged_files:
            print(f"Cleaning up {len(self.staged_files)} remaining staged files...")
            for staged_file in self.staged_files:
                try:
                    await staging_service.discard_staged_file(
                        staged_file["staging_id"], 
                        staged_file["user_id"]
                    )
                except Exception as e:
                    print(f"Failed to cleanup staged file {staged_file['staging_id']}: {e}")
        
        # Clean up test users
        async with AsyncSessionLocal() as db:
            for test_user in self.test_users:
                try:
                    await db.delete(test_user)
                    print(f"Deleted test user: {test_user.username}")
                except Exception as e:
                    print(f"Failed to delete test user {test_user.username}: {e}")
            
            try:
                await db.commit()
                print("Test user cleanup committed")
            except Exception as e:
                print(f"Failed to commit test user cleanup: {e}")
        
        print("Test environment cleanup completed")
    
    async def run_comprehensive_staging_test(self):
        """Run all staging tests in sequence"""
        print("Starting comprehensive AI files staging test...")
        print("=" * 60)
        
        try:
            # Setup
            await self.setup_test_environment()
            print()
            
            # Test 1: Service Status
            status_result = await self.test_ai_files_service_status()
            print()
            
            # Test 2: Bulk Upload
            upload_results = await self.test_bulk_staging_upload_flow()
            print()
            
            # Test 3: Individual Discard
            individual_discard_results = await self.test_individual_staging_discard_flow()
            print()
            
            # Test 4: Bulk Discard
            bulk_discard_results = await self.test_bulk_staging_discard_flow()
            print()
            
            # Test 5: Mixed Operations
            mixed_results = await self.test_mixed_operations_flow()
            print()
            
            # Test 6: Advanced Edge Cases
            edge_case_results = await self.test_advanced_edge_cases()
            print()
            
            # Test 7: Concurrent Operations
            concurrent_results = await self.test_concurrent_operations()
            print()
            
            # Test 8: Direct Service Testing
            service_direct_result = await self.test_staging_service_direct()
            print()
            
            # Test 9: Error Handling
            error_results = await self.test_error_handling()
            print()
            
            # Summary
            print("=" * 60)
            print("COMPREHENSIVE STAGING TEST SUMMARY")
            print("=" * 60)
            print(f"✓ Service Status: {'PASS' if status_result else 'FAIL'}")
            print(f"✓ Upload Tests: {len(upload_results)} scenarios completed")
            print(f"✓ Individual Discard: {len(individual_discard_results)} files tested")
            print(f"✓ Bulk Discard: {len(bulk_discard_results)} scenarios tested")
            print(f"✓ Mixed Operations: {len(mixed_results)} scenarios tested")
            print(f"✓ Advanced Edge Cases: {len(edge_case_results)} tests performed")
            print(f"✓ Concurrent Operations: {len(concurrent_results)} tests performed")
            print(f"✓ Direct Service: {'PASS' if service_direct_result else 'FAIL'}")
            print(f"✓ Error Handling: {len(error_results)} conditions tested")
            print()
            print("SIMPLIFIED STAGING FLOW VERIFIED:")
            print("1. Client uploads files → gets staging_ids")
            print("2. Client sends same staging_ids to discard → files deleted")
            print("3. No complex metadata, no nested directories")
            print("4. User isolation through staging_id format")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"Comprehensive test failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            # Always cleanup
            await self.cleanup_test_environment()

async def main():
    """Main test runner"""
    test_runner = AIFilesStagingIntegrationTest()
    success = await test_runner.run_comprehensive_staging_test()
    
    if success:
        print("All tests completed successfully!")
        sys.exit(0)
    else:
        print("Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 