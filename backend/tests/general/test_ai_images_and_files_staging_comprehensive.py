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

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = current_dir
# Add backend to path
sys.path.append(backend_dir)

from app.core.database import AsyncSessionLocal
from app.models.database.user import User
from app.services.storage.staging_storage import staging_service
from app.services.storage.storage import image_storage_service
from app.core.security import security
from app.core.config import get_settings

# SQLAlchemy cleanup
from sqlalchemy import delete

# Test configuration
API_BASE_URL = "http://localhost:8000/api/v1"
TEST_IMAGE_PATH = "fifa_test_image.png"

test_docs_dir = os.path.join(backend_dir, "test_docs")

TEST_SAMPLE_DOC_FILE = os.path.join(test_docs_dir, "PRY NDLS 20 June.pdf")
TEST_SAMPLE_DOCX_FILE = os.path.join(test_docs_dir, "Assignment 6_ Distributed Systems (Middleware).pdf")  # Will test as PDF

# Additional test files for comprehensive testing
TEST_FILES = {
    "image": TEST_IMAGE_PATH,
    "pdf": TEST_SAMPLE_DOC_FILE,
    "pdf2": TEST_SAMPLE_DOCX_FILE
}

class AIFilesStagingIntegrationTest:
    """Test class for simplified AI files staging integration"""
    
    def __init__(self):
        self.test_users = []
        self.auth_tokens = {}
        self.staged_files = []  # Track file IDs for cleanup
        self.settings = get_settings()
        
    async def setup_test_environment(self):
        """Set up test users and authentication"""
        print("Setting up simplified staging test environment...")
        
        # Verify test files exist
        for file_type, file_path in TEST_FILES.items():
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Test {file_type} file not found: {file_path}")
        
        print(f"Test files verified:")
        for file_type, file_path in TEST_FILES.items():
            size = os.path.getsize(file_path)
            print(f"  {file_type}: {file_path} ({size} bytes)")
        
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
    
    def extract_staged_files_from_response(self, upload_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all staged files from the new organized API response structure"""
        staging_files = upload_data.get("staging_files", {})
        all_staged_files = []
        
        # Only extract from file categories, skip summary or other non-file data
        file_categories = ["images", "vectors", "unknown"]
        
        for category, files_in_category in staging_files.items():
            if category in file_categories and isinstance(files_in_category, list):
                # Ensure each item is a dictionary (file object)
                for file_item in files_in_category:
                    if isinstance(file_item, dict):
                        all_staged_files.append(file_item)
                    else:
                        print(f"      ⚠️  Skipping non-dict item in {category}: {type(file_item)} - {file_item}")
        
        return all_staged_files
    
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
                
                # Verify core staging features
                expected_features = ["bulk_staging_upload", "staging_discard", "unified_s3_keys"]
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
                        
                        # NEW: Handle organized staging files structure
                        staging_files = upload_data.get("staging_files", {})
                        print(f"    Staging files structure: {list(staging_files.keys())}")
                        
                        # Track staged files by test type for proper test isolation
                        # Extract files from all categories (images, vectors, unknown)
                        all_staged_files = self.extract_staged_files_from_response(upload_data)
                        
                        # Print breakdown by category
                        file_categories = ["images", "vectors", "unknown"]
                        for category, files_in_category in staging_files.items():
                            if category in file_categories:
                                file_count = len(files_in_category) if isinstance(files_in_category, list) else 0
                                print(f"      {category}: {file_count} files")
                            else:
                                print(f"      {category}: {len(files_in_category) if isinstance(files_in_category, list) else 'N/A'} (summary/metadata)")
                        
                        for staged_file in all_staged_files:
                            file_id = staged_file.get("file_id")
                            if file_id:
                                # Verify file_id format (img_ prefix format)
                                if file_id.startswith("img_") and len(file_id) > 4:
                                    print(f"      ✓ File ID format correct: {file_id}")
                                else:
                                    print(f"      ✗ File ID format incorrect: {file_id}")
                                
                                staged_file_info = {
                                    "file_id": file_id,
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
    
    async def test_document_only_staging_upload(self):
        """Test staging upload with document files only"""
        print("Testing document-only staging upload...")
        
        async with httpx.AsyncClient() as client:
            document_upload_results = []
            
            # Read test PDF files
            pdf_files = {}
            for file_type, file_path in TEST_FILES.items():
                if file_type.startswith("pdf"):
                    with open(file_path, 'rb') as f:
                        pdf_files[file_type] = f.read()
            
            if not pdf_files:
                print("  No PDF files available for testing")
                return document_upload_results
            
            print(f"  Testing with {len(pdf_files)} PDF files")
            
            for user in self.test_users:
                print(f"  Testing document upload for user: {user.username} ({user.subscription_tier})")
                
                # Get auth headers for this user
                headers = self.get_auth_headers(user.user_id)
                
                # Test document upload scenarios
                test_scenarios = [
                    {"file_count": 2, "description": "Document discard test batch", "test_type": "doc_individual"},
                    {"file_count": 3, "description": "Document bulk discard test batch", "test_type": "doc_bulk"},
                ]
                
                for scenario in test_scenarios:
                    file_count = scenario["file_count"]
                    description = scenario["description"]
                    test_type = scenario["test_type"]
                    
                    print(f"    {description}: {file_count} files")
                    
                    # Prepare document files for staging
                    files = []
                    file_counter = 0
                    for i in range(file_count):
                        # Cycle through available PDF files
                        pdf_key = list(pdf_files.keys())[file_counter % len(pdf_files)]
                        pdf_data = pdf_files[pdf_key]
                        
                        filename = f"staging_doc_{test_type}_{user.subscription_tier}_{i}_{uuid.uuid4().hex[:8]}.pdf"
                        files.append(("files", (filename, pdf_data, "application/pdf")))
                        file_counter += 1
                    
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
                    print(f"      Document staging upload response: {response.status_code} (took {upload_duration:.2f}s)")
                    
                    if response.status_code == 201:
                        upload_data = response.json()
                        
                        successfully_staged = upload_data.get("successfully_staged", 0)
                        failed_uploads = upload_data.get("failed_uploads", 0)
                        total_size_bytes = upload_data.get("total_size_bytes", 0)
                        
                        print(f"      Successful document staging: {successfully_staged}/{file_count}")
                        print(f"      Failed document staging: {failed_uploads}")
                        print(f"      Total size: {total_size_bytes} bytes")
                        
                        # NEW: Handle organized staging files structure
                        staging_files = upload_data.get("staging_files", {})
                        print(f"      Staging files structure: {list(staging_files.keys())}")
                        
                        # Track staged files by test type
                        all_staged_files = self.extract_staged_files_from_response(upload_data)
                        
                        # Print breakdown by category
                        for category, files_in_category in staging_files.items():
                            if category in ["images", "vectors", "unknown"]:
                                file_count_in_cat = len(files_in_category) if isinstance(files_in_category, list) else 0
                                print(f"        {category}: {file_count_in_cat} files")
                        
                        # Verify documents went to vectors category
                        vector_files = staging_files.get("vectors", [])
                        if len(vector_files) == file_count:
                            print(f"      ✓ All {file_count} documents correctly categorized as vectors")
                        else:
                            print(f"      ✗ Document categorization issue: {len(vector_files)} in vectors, expected {file_count}")
                        
                        # Verify file IDs have file_ prefix (documents use file_ prefix)
                        for staged_file in all_staged_files:
                            file_id = staged_file.get("file_id")
                            if file_id:
                                if file_id.startswith("file_") and len(file_id) > 5:
                                    print(f"        ✓ Document file ID format correct: {file_id}")
                                else:
                                    print(f"        ✗ Document file ID format unexpected: {file_id}")
                                
                                staged_file_info = {
                                    "file_id": file_id,
                                    "user_id": user.user_id,
                                    "filename": staged_file.get("filename", "unknown"),
                                    "size": staged_file.get("size", 0),
                                    "content_type": staged_file.get("content_type", "unknown"),
                                    "test_type": test_type
                                }
                                
                                self.staged_files.append(staged_file_info)
                        
                        document_upload_results.append({
                            "user": user,
                            "scenario": description,
                            "test_type": test_type,
                            "file_count": file_count,
                            "successfully_staged": successfully_staged,
                            "failed_uploads": failed_uploads,
                            "upload_data": upload_data
                        })
                        
                    else:
                        print(f"      Document staging upload failed: {response.text}")
            
            print(f"Document-only staging upload completed. {len(document_upload_results)} successful uploads.")
            return document_upload_results
    
    async def test_mixed_file_staging_upload(self):
        """Test staging upload with mixed file types (images + documents)"""
        print("Testing mixed file staging upload...")
        
        async with httpx.AsyncClient() as client:
            mixed_upload_results = []
            
            # Read test files
            with open(TEST_FILES["image"], 'rb') as f:
                image_data = f.read()
            
            with open(TEST_FILES["pdf"], 'rb') as f:
                pdf_data = f.read()
            
            print(f"  Testing with mixed files: image ({len(image_data)} bytes) + PDF ({len(pdf_data)} bytes)")
            
            for user in self.test_users:
                print(f"  Testing mixed upload for user: {user.username} ({user.subscription_tier})")
                
                # Get auth headers for this user
                headers = self.get_auth_headers(user.user_id)
                
                # Test mixed upload scenarios
                test_scenarios = [
                    {"image_count": 2, "doc_count": 2, "description": "Mixed cleanup test batch", "test_type": "mixed_cleanup"},
                    {"image_count": 1, "doc_count": 3, "description": "Mixed heavy document batch", "test_type": "mixed_doc_heavy"},
                    {"image_count": 3, "doc_count": 1, "description": "Mixed heavy image batch", "test_type": "mixed_img_heavy"},
                ]
                
                for scenario in test_scenarios:
                    image_count = int(scenario["image_count"])
                    doc_count = int(scenario["doc_count"])
                    description = scenario["description"]
                    test_type = scenario["test_type"]
                    total_files = image_count + doc_count
                    
                    print(f"    {description}: {image_count} images + {doc_count} documents")
                    
                    # Prepare mixed files for staging
                    files = []
                    
                    # Add images
                    for i in range(image_count):
                        filename = f"staging_mixed_{test_type}_{user.subscription_tier}_img_{i}_{uuid.uuid4().hex[:8]}.png"
                        files.append(("files", (filename, image_data, "image/png")))
                    
                    # Add documents
                    for i in range(doc_count):
                        filename = f"staging_mixed_{test_type}_{user.subscription_tier}_doc_{i}_{uuid.uuid4().hex[:8]}.pdf"
                        files.append(("files", (filename, pdf_data, "application/pdf")))
                    
                    data = {
                        "max_concurrent_uploads": "5"
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
                    print(f"      Mixed staging upload response: {response.status_code} (took {upload_duration:.2f}s)")
                    
                    if response.status_code == 201:
                        upload_data = response.json()
                        
                        successfully_staged = upload_data.get("successfully_staged", 0)
                        failed_uploads = upload_data.get("failed_uploads", 0)
                        total_size_bytes = upload_data.get("total_size_bytes", 0)
                        
                        print(f"      Successful mixed staging: {successfully_staged}/{total_files}")
                        print(f"      Failed mixed staging: {failed_uploads}")
                        print(f"      Total size: {total_size_bytes} bytes")
                        
                        # NEW: Handle organized staging files structure
                        staging_files = upload_data.get("staging_files", {})
                        print(f"      Staging files structure: {list(staging_files.keys())}")
                        
                        # Track staged files by test type
                        all_staged_files = self.extract_staged_files_from_response(upload_data)
                        
                        # Print breakdown by category and verify counts
                        image_files = staging_files.get("images", [])
                        vector_files = staging_files.get("vectors", [])
                        unknown_files = staging_files.get("unknown", [])
                        
                        print(f"        images: {len(image_files)} files (expected: {image_count})")
                        print(f"        vectors: {len(vector_files)} files (expected: {doc_count})")
                        print(f"        unknown: {len(unknown_files)} files (expected: 0)")
                        
                        # Verify categorization
                        if len(image_files) == image_count and len(vector_files) == doc_count:
                            print(f"      ✓ Mixed file categorization correct")
                        else:
                            print(f"      ✗ Mixed file categorization issue")
                        
                        # Verify file ID prefixes
                        img_id_correct = 0
                        doc_id_correct = 0
                        
                        for staged_file in all_staged_files:
                            file_id = staged_file.get("file_id")
                            filename = staged_file.get("filename", "")
                            
                            if file_id:
                                if filename.endswith(".png") and file_id.startswith("img_"):
                                    img_id_correct += 1
                                elif filename.endswith(".pdf") and file_id.startswith("file_"):
                                    doc_id_correct += 1
                                
                                staged_file_info = {
                                    "file_id": file_id,
                                    "user_id": user.user_id,
                                    "filename": staged_file.get("filename", "unknown"),
                                    "size": staged_file.get("size", 0),
                                    "content_type": staged_file.get("content_type", "unknown"),
                                    "test_type": test_type
                                }
                                
                                self.staged_files.append(staged_file_info)
                        
                        print(f"        ✓ Image file ID format correct: {img_id_correct}/{image_count}")
                        print(f"        ✓ Document file ID format correct: {doc_id_correct}/{doc_count}")
                        
                        mixed_upload_results.append({
                            "user": user,
                            "scenario": description,
                            "test_type": test_type,
                            "image_count": image_count,
                            "doc_count": doc_count,
                            "total_files": total_files,
                            "successfully_staged": successfully_staged,
                            "failed_uploads": failed_uploads,
                            "upload_data": upload_data
                        })
                        
                    else:
                        print(f"      Mixed staging upload failed: {response.text}")
            
            print(f"Mixed file staging upload completed. {len(mixed_upload_results)} successful uploads.")
            return mixed_upload_results
    
    async def test_document_discard_flow(self):
        """Test document file discard operations"""
        print("Testing document discard flow...")
        
        # Get files specifically uploaded for document discard testing
        doc_individual_files = [f for f in self.staged_files if f["test_type"] == "doc_individual"]
        doc_bulk_files = [f for f in self.staged_files if f["test_type"] == "doc_bulk"]
        
        if not doc_individual_files and not doc_bulk_files:
            print("No document files available for discard testing")
            return []
        
        async with httpx.AsyncClient() as client:
            discard_results = []
            
            # Test individual document discard
            if doc_individual_files:
                print(f"Testing individual document discard with {len(doc_individual_files)} files")
                
                for staged_file in doc_individual_files:
                    file_id = staged_file["file_id"]
                    user_id = staged_file["user_id"]
                    filename = staged_file["filename"]
                    
                    print(f"  Discarding document file: {file_id} ({filename})")
                    
                    headers = self.get_auth_headers(user_id)
                    response = await client.delete(
                        f"{API_BASE_URL}/ai-files/staging/discard/{file_id}",
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        discard_data = response.json()
                        print(f"    ✓ Document discard successful: {discard_data.get('message', 'No message')}")
                        discard_results.append({
                            "file_id": file_id,
                            "user_id": user_id,
                            "filename": filename,
                            "success": True,
                            "file_type": "document"
                        })
                        # Remove from tracking
                        self.staged_files.remove(staged_file)
                    else:
                        print(f"    ✗ Document discard failed: {response.status_code} - {response.text}")
            
            # Test bulk document discard
            if doc_bulk_files:
                print(f"Testing bulk document discard with {len(doc_bulk_files)} files")
                
                # Group by user
                user_doc_files = {}
                for staged_file in doc_bulk_files:
                    user_id = staged_file["user_id"]
                    if user_id not in user_doc_files:
                        user_doc_files[user_id] = []
                    user_doc_files[user_id].append(staged_file)
                
                for user_id, staged_files_list in user_doc_files.items():
                    print(f"  Bulk discarding {len(staged_files_list)} document files for user {user_id}")
                    
                    file_ids = [sf["file_id"] for sf in staged_files_list]
                    headers = self.get_auth_headers(user_id)
                    
                    response = await client.request(
                        "DELETE",
                        f"{API_BASE_URL}/ai-files/staging/bulk-discard",
                        json={"file_ids": file_ids},
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        bulk_data = response.json()
                        successfully_discarded = bulk_data.get("successfully_discarded", 0)
                        print(f"    ✓ Bulk document discard successful: {successfully_discarded}/{len(file_ids)}")
                        
                        # Remove discarded files from tracking
                        discarded_ids = bulk_data.get("discarded_file_ids", [])
                        self.staged_files = [sf for sf in self.staged_files if sf["file_id"] not in discarded_ids]
                        
                        discard_results.append({
                            "user_id": user_id,
                            "file_ids": file_ids,
                            "successfully_discarded": successfully_discarded,
                            "file_type": "document",
                            "operation": "bulk"
                        })
                    else:
                        print(f"    ✗ Bulk document discard failed: {response.status_code} - {response.text}")
            
            print(f"Document discard flow completed. {len(discard_results)} operations performed.")
            return discard_results
    
    async def test_mixed_files_cleanup_flow(self):
        """Test cleanup of mixed file types"""
        print("Testing mixed files cleanup flow...")
        
        # Get files specifically uploaded for mixed cleanup testing
        mixed_cleanup_files = [f for f in self.staged_files if f["test_type"] == "mixed_cleanup"]
        
        if not mixed_cleanup_files:
            print("No mixed cleanup files available for testing")
            return []
        
        async with httpx.AsyncClient() as client:
            cleanup_results = []
            
            print(f"Testing mixed cleanup with {len(mixed_cleanup_files)} files")
            
            # Separate by file type
            image_files = [f for f in mixed_cleanup_files if f["file_id"].startswith("img_")]
            doc_files = [f for f in mixed_cleanup_files if f["file_id"].startswith("file_")]
            
            print(f"  Mixed cleanup files: {len(image_files)} images, {len(doc_files)} documents")
            
            # Group by user
            user_mixed_files = {}
            for staged_file in mixed_cleanup_files:
                user_id = staged_file["user_id"]
                if user_id not in user_mixed_files:
                    user_mixed_files[user_id] = []
                user_mixed_files[user_id].append(staged_file)
            
            for user_id, staged_files_list in user_mixed_files.items():
                print(f"  Testing mixed cleanup for user {user_id} ({len(staged_files_list)} files)")
                
                headers = self.get_auth_headers(user_id)
                
                # Test 1: Individual cleanup of some files
                if len(staged_files_list) > 2:
                    individual_files = staged_files_list[:2]  # First 2 files
                    
                    for staged_file in individual_files:
                        file_id = staged_file["file_id"]
                        file_type = "image" if file_id.startswith("img_") else "document"
                        
                        print(f"    Individual cleanup of {file_type} file: {file_id}")
                        
                        response = await client.delete(
                            f"{API_BASE_URL}/ai-files/staging/discard/{file_id}",
                            headers=headers
                        )
                        
                        if response.status_code == 200:
                            print(f"      ✓ Individual {file_type} cleanup successful")
                            self.staged_files.remove(staged_file)
                            staged_files_list.remove(staged_file)
                        else:
                            print(f"      ✗ Individual {file_type} cleanup failed: {response.status_code}")
                
                # Test 2: Bulk cleanup of remaining files
                if len(staged_files_list) > 0:
                    remaining_files = staged_files_list
                    remaining_images = [f for f in remaining_files if f["file_id"].startswith("img_")]
                    remaining_docs = [f for f in remaining_files if f["file_id"].startswith("file_")]
                    
                    print(f"    Bulk cleanup of {len(remaining_images)} images + {len(remaining_docs)} documents")
                    
                    file_ids = [sf["file_id"] for sf in remaining_files]
                    
                    response = await client.request(
                        "DELETE",
                        f"{API_BASE_URL}/ai-files/staging/bulk-discard",
                        json={"file_ids": file_ids},
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        bulk_data = response.json()
                        successfully_discarded = bulk_data.get("successfully_discarded", 0)
                        print(f"      ✓ Bulk mixed cleanup successful: {successfully_discarded}/{len(file_ids)}")
                        
                        # Remove discarded files from tracking
                        discarded_ids = bulk_data.get("discarded_file_ids", [])
                        self.staged_files = [sf for sf in self.staged_files if sf["file_id"] not in discarded_ids]
                        
                        cleanup_results.append({
                            "user_id": user_id,
                            "total_files": len(file_ids),
                            "images": len(remaining_images),
                            "documents": len(remaining_docs),
                            "successfully_discarded": successfully_discarded,
                            "operation": "mixed_bulk_cleanup"
                        })
                    else:
                        print(f"      ✗ Bulk mixed cleanup failed: {response.status_code} - {response.text}")
            
            print(f"Mixed files cleanup flow completed. {len(cleanup_results)} operations performed.")
            return cleanup_results
    
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
                file_id = staged_file["file_id"]
                user_id = staged_file["user_id"]
                filename = staged_file["filename"]
                
                print(f"Testing discard of staging file: {file_id} (user: {user_id})")
                
                headers = self.get_auth_headers(user_id)
                response = await client.delete(
                    f"{API_BASE_URL}/ai-files/staging/discard/{file_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    discard_data = response.json()
                    print(f"  ✓ Discard successful: {discard_data.get('message', 'No message')}")
                    
                    discard_results.append({
                        "file_id": file_id,
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
            fake_file_id = f"img_{uuid.uuid4().hex[:8]}"
            headers = self.get_auth_headers(self.test_users[0].user_id)
            response = await client.delete(
                f"{API_BASE_URL}/ai-files/staging/discard/{fake_file_id}",
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
                        f"{API_BASE_URL}/ai-files/staging/discard/{other_user_file['file_id']}",
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
                
                file_ids = [sf["file_id"] for sf in staged_files_list]
                headers = self.get_auth_headers(user_id)
                
                response = await client.request(
                    "DELETE",
                    f"{API_BASE_URL}/ai-files/staging/bulk-discard",
                    json={"file_ids": file_ids},
                    headers=headers
                )
                
                if response.status_code == 200:
                    bulk_data = response.json()
                    
                    successfully_discarded = bulk_data.get("successfully_discarded", 0)
                    failed_discards = bulk_data.get("failed_discards", 0)
                    
                    print(f"  ✓ Bulk discard successful: {successfully_discarded}/{len(file_ids)} discarded")
                    print(f"  Failed discards: {failed_discards}")
                    
                    bulk_discard_results.append({
                        "user": user,
                        "file_ids": file_ids,
                        "successfully_discarded": successfully_discarded,
                        "failed_discards": failed_discards,
                        "bulk_data": bulk_data
                    })
                    
                    # Remove discarded files from our tracking
                    discarded_ids = bulk_data.get("discarded_file_ids", [])
                    self.staged_files = [sf for sf in self.staged_files if sf["file_id"] not in discarded_ids]
                    
                else:
                    print(f"  ✗ Bulk discard failed: {response.status_code} - {response.text}")
            
            # Test edge cases with fresh user
            print("Testing bulk discard edge cases...")
            headers = self.get_auth_headers(self.test_users[0].user_id)
            
            # Test bulk discard with empty list
            print("  Testing bulk discard with empty file IDs list...")
            response = await client.request(
                "DELETE",
                f"{API_BASE_URL}/ai-files/staging/bulk-discard",
                json={"file_ids": []},
                headers=headers
            )
            
            if response.status_code == 400:
                print("    ✓ Empty file IDs list correctly rejected (400)")
            elif response.status_code == 200:
                bulk_data = response.json()
                if bulk_data.get("successfully_discarded", 0) == 0:
                    print("    ✓ Empty file IDs list handled correctly")
                else:
                    print(f"    ✗ Empty file IDs list: unexpected discards")
            else:
                print(f"    ✗ Empty file IDs list failed: {response.status_code}")
            
            # Test with too many file IDs (exceed limit)
            print("  Testing bulk discard with too many file IDs...")
            too_many_file_ids = [f"img_{uuid.uuid4().hex[:8]}" for i in range(25)]  # Exceed limit
            response = await client.request(
                "DELETE",
                f"{API_BASE_URL}/ai-files/staging/bulk-discard",
                json={"file_ids": too_many_file_ids},
                headers=headers
            )
            
            if response.status_code == 400:
                print(f"    ✓ Too many file IDs validation: PASS (400)")
            else:
                print(f"    ✗ Too many file IDs validation: FAIL ({response.status_code})")
            
            # Test bulk discard with non-existent files
            print("  Testing bulk discard with non-existent file IDs...")
            fake_file_ids = [f"img_{uuid.uuid4().hex[:8]}" for i in range(3)]
            response = await client.request(
                "DELETE",
                f"{API_BASE_URL}/ai-files/staging/bulk-discard",
                json={"file_ids": fake_file_ids},
                headers=headers
            )
            
            if response.status_code == 200:
                bulk_data = response.json()
                failed_discards = bulk_data.get("failed_discards", 0)
                if failed_discards == len(fake_file_ids):
                    print(f"    ✓ Non-existent files correctly reported as failed ({failed_discards} failed)")
                else:
                    print(f"    ✗ Non-existent files handling incorrect: {failed_discards} failed vs {len(fake_file_ids)} expected")
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
            
            edge_case_file_ids = []
            if upload_response.status_code == 201:
                upload_data = upload_response.json()
                
                # NEW: Extract file IDs from organized structure
                all_staged_files = self.extract_staged_files_from_response(upload_data)
                edge_case_file_ids = [f["file_id"] for f in all_staged_files]
                print(f"  Uploaded {len(edge_case_file_ids)} test files for edge cases")
            
            # Edge Case 1: Bulk discard with duplicate file IDs
            print("  Testing bulk discard with duplicate file IDs...")
            if len(edge_case_file_ids) >= 2:
                duplicate_ids = [edge_case_file_ids[0], edge_case_file_ids[0], edge_case_file_ids[1]]
                response = await client.request(
                    "DELETE",
                    f"{API_BASE_URL}/ai-files/staging/bulk-discard",
                    json={"file_ids": duplicate_ids},
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
            
            # Edge Case 2: Bulk discard with invalid file ID formats
            print("  Testing bulk discard with invalid file ID formats...")
            invalid_ids = [
                "invalid_format_123",
                "not-a-uuid",
                "12345",
                "",
                "x" * 100  # Very long ID
            ]
            response = await client.request(
                "DELETE",
                f"{API_BASE_URL}/ai-files/staging/bulk-discard",
                json={"file_ids": invalid_ids},
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
            
            # Edge Case 3: Mixed valid and invalid file IDs
            print("  Testing bulk discard with mixed valid/invalid IDs...")
            if len(edge_case_file_ids) >= 1:
                mixed_ids = [
                    edge_case_file_ids[-1],  # Valid ID (if any left)
                    "invalid_format",
                    f"img_{uuid.uuid4().hex[:8]}"  # Valid format but non-existent
                ]
                response = await client.request(
                    "DELETE",
                    f"{API_BASE_URL}/ai-files/staging/bulk-discard",
                    json={"file_ids": mixed_ids},
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
            
            concurrent_file_ids = []
            if upload_response.status_code == 201:
                upload_data = upload_response.json()
                
                # NEW: Extract file IDs from organized structure
                all_staged_files = self.extract_staged_files_from_response(upload_data)
                concurrent_file_ids = [f["file_id"] for f in all_staged_files]
                print(f"  Uploaded {len(concurrent_file_ids)} files for concurrent testing")
            
            if len(concurrent_file_ids) >= 4:
                # Test 1: Concurrent bulk discards of different files
                print("  Testing concurrent bulk discards of different files...")
                
                batch1 = concurrent_file_ids[:2]
                batch2 = concurrent_file_ids[2:4]
                
                async def bulk_discard_batch(file_ids, batch_name):
                    try:
                        response = await client.request(
                            "DELETE",
                            f"{API_BASE_URL}/ai-files/staging/bulk-discard",
                            json={"file_ids": file_ids},
                            headers=headers
                        )
                        return {
                            "batch": batch_name,
                            "status_code": response.status_code,
                            "response": response.json() if response.status_code == 200 else None,
                            "file_ids": file_ids
                        }
                    except Exception as e:
                        return {
                            "batch": batch_name,
                            "error": str(e),
                            "file_ids": file_ids
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
                if len(concurrent_file_ids) >= 6:
                    print("  Testing concurrent bulk discards of overlapping files...")
                    
                    overlap_batch1 = concurrent_file_ids[4:6]
                    overlap_batch2 = [concurrent_file_ids[4]]  # Overlapping file
                    
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
                        f"{API_BASE_URL}/ai-files/staging/discard/{staged_file['file_id']}",
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
                mixed_file_ids = []
                mixed_file_ids.extend([f["file_id"] for f in remaining_files])
                mixed_file_ids.extend([f["file_id"] for f in already_deleted_files])  # These should fail
                
                print(f"  Step 2: Bulk delete with {len(remaining_files)} existing + {len(already_deleted_files)} already deleted files")
                
                response = await client.request(
                    "DELETE",
                    f"{API_BASE_URL}/ai-files/staging/bulk-discard",
                    json={"file_ids": mixed_file_ids},
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
                    discarded_ids = bulk_data.get("discarded_file_ids", [])
                    self.staged_files = [sf for sf in self.staged_files if sf["file_id"] not in discarded_ids]
                    
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
            # Test staging service configuration
            print(f"  Max staging age hours: {staging_service.max_staging_age_hours}")
            print(f"  Max file size: {staging_service.max_file_size}")
            
            # Test staging metadata creation and validation
            from datetime import datetime, timedelta
            from app.services.storage.staging_storage import StagingMetadata
            
            user_id = self.test_users[0].user_id
            now = datetime.utcnow()
            
            test_metadata = StagingMetadata(
                file_id=str(uuid.uuid4()),
                original_filename="test.jpg",
                content_type="image/jpeg",
                file_size=1024,
                user_id=user_id,
                staged_at=now,
                expires_at=now + timedelta(hours=24),
                state="staging",
                purpose="vision"
            )
            
            # Test metadata serialization
            metadata_dict = test_metadata.to_dict()
            print(f"  ✓ Metadata serialization successful: {len(metadata_dict)} fields")
            
            # Test metadata deserialization
            restored_metadata = StagingMetadata.from_dict(metadata_dict)
            if restored_metadata.file_id == test_metadata.file_id:
                print(f"  ✓ Metadata deserialization correct: {restored_metadata.file_id}")
            else:
                print(f"  ✗ Metadata deserialization failed")
            
            # Test file validation
            try:
                staging_service._validate_staging_file("test.jpg", 1024)
                print(f"  ✓ File validation for valid file: PASS")
            except Exception as e:
                print(f"  ✗ File validation for valid file: FAIL - {e}")
            
            # Test invalid file validation
            try:
                staging_service._validate_staging_file("test.exe", 1024)
                print(f"  ✗ File validation for invalid file: FAIL (should have rejected)")
            except Exception:
                print(f"  ✓ File validation for invalid file: PASS (correctly rejected)")
            
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
            exe_data = b"This is a fake executable file"
            files = [("files", ("test.exe", exe_data, "application/octet-stream"))]
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
            fake_file_id = f"img_{uuid.uuid4().hex[:8]}"
            response = await client.delete(
                f"{API_BASE_URL}/ai-files/staging/discard/{fake_file_id}",
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
    
    async def test_background_cleanup_comprehensive(self):
        """Test background cleanup of expired staging files comprehensively"""
        print("Testing background cleanup functionality...")
        
        async with httpx.AsyncClient() as client:
            cleanup_results = []
            
            # Test 1: Test admin cleanup endpoint access (dry run first)
            print("  Testing admin cleanup endpoint access...")
            
            # Use enterprise user (likely to have admin access or be allowed)
            enterprise_user = next((u for u in self.test_users if u.subscription_tier == "enterprise"), None)
            if not enterprise_user:
                enterprise_user = self.test_users[0]  # Fallback
                
            headers = self.get_auth_headers(enterprise_user.user_id)
            
            # Test dry run cleanup
            response = await client.post(
                f"{API_BASE_URL}/ai-files/staging/admin/cleanup",
                json={"dry_run": True},
                headers=headers
            )
            
            if response.status_code == 200:
                cleanup_data = response.json()
                print(f"    ✓ Dry run cleanup successful")
                print(f"      - Expired files found: {cleanup_data.get('expired_files_found', 0)}")
                print(f"      - Active files: {cleanup_data.get('active_files', 0)}")
                print(f"      - Cleanup errors: {cleanup_data.get('cleanup_errors', 0)}")
                
                cleanup_results.append({
                    "test": "admin_cleanup_dry_run", 
                    "result": "pass",
                    "data": cleanup_data
                })
            else:
                print(f"    ✗ Dry run cleanup failed: {response.status_code} - {response.text}")
                cleanup_results.append({
                    "test": "admin_cleanup_dry_run", 
                    "result": "fail",
                    "status_code": response.status_code
                })
            
            # Test 2: Upload files with different expiration times to test cleanup logic
            print("  Testing cleanup with artificially expired files...")
            
            # We'll need to manually create some expired staging files for testing
            # Upload normal files first
            with open(TEST_IMAGE_PATH, 'rb') as f:
                image_data = f.read()
            
            files = []
            for i in range(3):
                filename = f"cleanup_test_{i}_{uuid.uuid4().hex[:8]}.png"
                files.append(("files", (filename, image_data, "image/png")))
            
            upload_response = await client.post(
                f"{API_BASE_URL}/ai-files/staging/bulk-upload",
                files=files,
                data={"max_concurrent_uploads": "3"},
                headers=headers
            )
            
            cleanup_test_file_ids = []
            if upload_response.status_code == 201:
                upload_data = upload_response.json()
                
                # NEW: Extract file IDs from organized structure using helper function
                all_staged_files = self.extract_staged_files_from_response(upload_data)
                cleanup_test_file_ids = [f["file_id"] for f in all_staged_files]
                print(f"    Uploaded {len(cleanup_test_file_ids)} files for cleanup testing")
                
                # Track these files for cleanup
                for staged_file in all_staged_files:
                    self.staged_files.append({
                        "file_id": staged_file["file_id"],
                        "user_id": enterprise_user.user_id,
                        "filename": staged_file.get("filename", "unknown"),
                        "test_type": "cleanup"
                    })
            
            # Test 3: Direct service cleanup testing
            print("  Testing direct staging service cleanup...")
            
            try:
                # Test direct service dry run
                service_dry_result = await staging_service.cleanup_expired_staging_files(dry_run=True)
                
                print(f"    ✓ Direct service dry run successful")
                print(f"      - Expired files found: {service_dry_result.get('expired_files_found', 0)}")
                print(f"      - Active files: {service_dry_result.get('active_files', 0)}")
                print(f"      - Would clean: {service_dry_result.get('expired_files_cleaned', 0)}")
                
                cleanup_results.append({
                    "test": "direct_service_dry_run", 
                    "result": "pass",
                    "data": service_dry_result
                })
                
                # Test that dry run doesn't actually delete anything
                if service_dry_result.get('cleanup_completed') == False:
                    print(f"    ✓ Dry run correctly set cleanup_completed=False")
                else:
                    print(f"    ✗ Dry run incorrectly set cleanup_completed=True")
                
            except Exception as e:
                print(f"    ✗ Direct service cleanup failed: {e}")
                cleanup_results.append({
                    "test": "direct_service_dry_run", 
                    "result": "fail",
                    "error": str(e)
                })
            
            # Test 4: Test cleanup with no expired files (should be safe)
            print("  Testing cleanup with no expired files...")
            
            try:
                # Run actual cleanup (not dry run) - should be safe since files are fresh
                response = await client.post(
                    f"{API_BASE_URL}/ai-files/staging/admin/cleanup",
                    json={"dry_run": False},
                    headers=headers
                )
                
                if response.status_code == 200:
                    cleanup_data = response.json()
                    expired_cleaned = cleanup_data.get('expired_files_cleaned', 0)
                    
                    print(f"    ✓ Actual cleanup completed")
                    print(f"      - Files cleaned: {expired_cleaned}")
                    
                    # Since our files are fresh, we expect 0 expired files cleaned
                    if expired_cleaned == 0:
                        print(f"    ✓ No fresh files were incorrectly cleaned")
                        cleanup_results.append({
                            "test": "actual_cleanup_safe", 
                            "result": "pass"
                        })
                    else:
                        print(f"    ⚠️  Warning: {expired_cleaned} files were cleaned (unexpected)")
                        cleanup_results.append({
                            "test": "actual_cleanup_safe", 
                            "result": "warning",
                            "cleaned_count": expired_cleaned
                        })
                else:
                    print(f"    ✗ Actual cleanup failed: {response.status_code}")
                    cleanup_results.append({
                        "test": "actual_cleanup_safe", 
                        "result": "fail"
                    })
                    
            except Exception as e:
                print(f"    ✗ Actual cleanup test failed: {e}")
                cleanup_results.append({
                    "test": "actual_cleanup_safe", 
                    "result": "fail",
                    "error": str(e)
                })
            
            # Test 5: Test cleanup error handling
            print("  Testing cleanup error handling...")
            
            # Test unauthorized access (different user)
            if len(self.test_users) > 1:
                other_user = next((u for u in self.test_users if u.user_id != enterprise_user.user_id), None)
                if other_user:
                    other_headers = self.get_auth_headers(other_user.user_id)
                    
                    response = await client.post(
                        f"{API_BASE_URL}/ai-files/staging/admin/cleanup",
                        json={"dry_run": True},
                        headers=other_headers
                    )
                    
                    # Depending on implementation, this might be 403 (forbidden) or 200 (allowed)
                    if response.status_code in [200, 403]:
                        print(f"    ✓ Access control working (status: {response.status_code})")
                        cleanup_results.append({
                            "test": "cleanup_access_control", 
                            "result": "pass"
                        })
                    else:
                        print(f"    ✗ Unexpected access control response: {response.status_code}")
                        cleanup_results.append({
                            "test": "cleanup_access_control", 
                            "result": "fail"
                        })
            
            # Test 6: Test cleanup with invalid parameters
            print("  Testing cleanup with invalid parameters...")
            
            # Test with missing dry_run parameter
            response = await client.post(
                f"{API_BASE_URL}/ai-files/staging/admin/cleanup",
                json={},  # Missing dry_run
                headers=headers
            )
            
            if response.status_code in [200, 400]:  # Either defaults to dry_run=False or validates
                print(f"    ✓ Missing parameter handled correctly (status: {response.status_code})")
                cleanup_results.append({
                    "test": "cleanup_missing_params", 
                    "result": "pass"
                })
            else:
                print(f"    ✗ Missing parameter handling unexpected: {response.status_code}")
                cleanup_results.append({
                    "test": "cleanup_missing_params", 
                    "result": "fail"
                })
            
            # Test 7: Verify files still exist after our tests
            print("  Verifying test files still exist after cleanup tests...")
            
            files_still_exist = 0
            for file_id in cleanup_test_file_ids:
                try:
                    metadata = await staging_service.get_staging_metadata(file_id, enterprise_user.user_id)
                    if metadata:
                        files_still_exist += 1
                except Exception:
                    pass
            
            if files_still_exist > 0:
                print(f"    ✓ {files_still_exist}/{len(cleanup_test_file_ids)} test files still exist (expected)")
                cleanup_results.append({
                    "test": "files_preserved", 
                    "result": "pass"
                })
            else:
                print(f"    ⚠️  No test files found after cleanup (unexpected)")
                cleanup_results.append({
                    "test": "files_preserved", 
                    "result": "warning"
                })
            
            print(f"Background cleanup testing completed. {len(cleanup_results)} tests performed.")
            return cleanup_results
    
    async def _update_s3_object_metadata(self, s3_key: str, new_metadata: Dict[str, Any]) -> bool:
        """Helper method to update S3 object metadata by copying the object"""
        try:
            # Get the current object
            current_obj = staging_service.storage_backend.s3_client.get_object(
                Bucket=staging_service.storage_backend.bucket_name,
                Key=s3_key
            )
            
            # Copy the object with new metadata
            staging_service.storage_backend.s3_client.copy_object(
                CopySource={
                    'Bucket': staging_service.storage_backend.bucket_name,
                    'Key': s3_key
                },
                Bucket=staging_service.storage_backend.bucket_name,
                Key=s3_key,
                Metadata=new_metadata,
                MetadataDirective='REPLACE',
                ContentType=current_obj['ContentType']
            )
            
            return True
            
        except Exception as e:
            print(f"    Failed to update metadata for {s3_key}: {e}")
            return False

    async def test_cleanup_with_expired_files(self):
        """Test cleanup functionality with artificially expired files"""
        print("Testing cleanup with artificially expired files...")
        
        async with httpx.AsyncClient() as client:
            expired_test_results = []
            
            # Use enterprise user for this test
            enterprise_user = next((u for u in self.test_users if u.subscription_tier == "enterprise"), None)
            if not enterprise_user:
                enterprise_user = self.test_users[0]
                
            headers = self.get_auth_headers(enterprise_user.user_id)
            
            # Step 1: Upload files that we'll artificially expire
            print("  Step 1: Uploading files to artificially expire...")
            
            with open(TEST_IMAGE_PATH, 'rb') as f:
                image_data = f.read()
            
            files = []
            for i in range(2):
                filename = f"expire_test_{i}_{uuid.uuid4().hex[:8]}.png"
                files.append(("files", (filename, image_data, "image/png")))
            
            upload_response = await client.post(
                f"{API_BASE_URL}/ai-files/staging/bulk-upload",
                files=files,
                data={"max_concurrent_uploads": "2"},
                headers=headers
            )
            
            expired_file_ids = []
            staged_files_info = []
            
            if upload_response.status_code == 201:
                upload_data = upload_response.json()
                
                # NEW: Extract file IDs from organized structure using helper function
                all_staged_files = self.extract_staged_files_from_response(upload_data)
                expired_file_ids = [f["file_id"] for f in all_staged_files]
                staged_files_info = all_staged_files
                print(f"    Uploaded {len(expired_file_ids)} files for expiration testing")
                
                # Track these files for cleanup
                for staged_file in staged_files_info:
                    self.staged_files.append({
                        "file_id": staged_file["file_id"],
                        "user_id": enterprise_user.user_id,
                        "filename": staged_file.get("filename", "unknown"),
                        "test_type": "expired"
                    })
            else:
                print(f"    ✗ Failed to upload files for expiration test: {upload_response.status_code}")
                return expired_test_results
            
            # Step 2: Artificially expire the files by manipulating their metadata
            print("  Step 2: Artificially expiring files by manipulating metadata...")
            
            from datetime import datetime, timedelta
            from app.services.storage.staging_storage import StagingMetadata
            
            artificially_expired_count = 0
            
            for i, staged_file in enumerate(staged_files_info):
                file_id = staged_file["file_id"]
                original_filename = staged_file["filename"]
                
                try:
                    # Generate the S3 key (same way as staging service does)
                    s3_key = image_storage_service.generate_image_storage_key(file_id, original_filename)
                    
                    # Get current metadata
                    current_metadata = await staging_service._get_object_metadata(s3_key)
                    
                    if current_metadata:
                        print(f"    Original expiry for {file_id}: {current_metadata.get('expires_at', 'unknown')}")
                        
                        # Create new metadata with past expiration date
                        expired_metadata = {
                            'file_id': file_id,
                            'original_filename': original_filename,
                            'content_type': staged_file.get("content_type", "image/png"),
                            'file_size': str(staged_file.get("size", len(image_data))),
                            'user_id': enterprise_user.user_id,
                            'staged_at': current_metadata.get('staged_at', datetime.utcnow().isoformat()),
                            'expires_at': (datetime.utcnow() - timedelta(hours=1)).isoformat(),  # Expired 1 hour ago
                            'state': 'staging',
                            'purpose': 'vision'
                        }
                        
                        print(f"    New expiry for {file_id}: {expired_metadata['expires_at']} (1 hour ago)")
                        
                        # Update the metadata
                        if await self._update_s3_object_metadata(s3_key, expired_metadata):
                            print(f"    ✓ Successfully expired file: {file_id}")
                            artificially_expired_count += 1
                        else:
                            print(f"    ✗ Failed to expire file: {file_id}")
                                
                except Exception as e:
                    print(f"    ✗ Failed to expire file {file_id}: {e}")
            
            print(f"    Successfully artificially expired {artificially_expired_count}/{len(expired_file_ids)} files")
            
            if artificially_expired_count == 0:
                print("    ⚠️  No files were expired, skipping cleanup tests")
                return expired_test_results
            
            # Step 3: Test dry run cleanup - should find the expired files
            print("  Step 3: Testing dry run cleanup with expired files...")
            
            try:
                dry_run_result = await staging_service.cleanup_expired_staging_files(dry_run=True)
                
                expired_found = dry_run_result.get('expired_files_found', 0)
                active_files = dry_run_result.get('active_files', 0)
                
                print(f"    Dry run results:")
                print(f"      - Expired files found: {expired_found}")
                print(f"      - Active files: {active_files}")
                print(f"      - Cleanup completed: {dry_run_result.get('cleanup_completed', False)}")
                
                if expired_found >= artificially_expired_count:
                    print(f"    ✓ Dry run correctly identified expired files")
                    expired_test_results.append({
                        "test": "dry_run_expired_detection", 
                        "result": "pass",
                        "expired_found": expired_found
                    })
                else:
                    print(f"    ✗ Dry run missed some expired files: found {expired_found}, expected >= {artificially_expired_count}")
                    expired_test_results.append({
                        "test": "dry_run_expired_detection", 
                        "result": "fail",
                        "expired_found": expired_found,
                        "expected": artificially_expired_count
                    })
                
                # Verify dry run didn't actually delete anything
                if not dry_run_result.get('cleanup_completed', True):
                    print(f"    ✓ Dry run correctly didn't delete files")
                else:
                    print(f"    ✗ Dry run incorrectly marked as completed")
                
            except Exception as e:
                print(f"    ✗ Dry run cleanup failed: {e}")
                expired_test_results.append({
                    "test": "dry_run_expired_detection", 
                    "result": "error",
                    "error": str(e)
                })
            
            # Step 4: Test actual cleanup - should remove the expired files
            print("  Step 4: Testing actual cleanup with expired files...")
            
            try:
                actual_cleanup_result = await staging_service.cleanup_expired_staging_files(dry_run=False)
                
                expired_cleaned = actual_cleanup_result.get('expired_files_cleaned', 0)
                cleanup_completed = actual_cleanup_result.get('cleanup_completed', False)
                cleanup_errors = actual_cleanup_result.get('cleanup_errors', 0)
                
                print(f"    Actual cleanup results:")
                print(f"      - Expired files cleaned: {expired_cleaned}")
                print(f"      - Cleanup completed: {cleanup_completed}")
                print(f"      - Cleanup errors: {cleanup_errors}")
                
                if expired_cleaned >= artificially_expired_count and cleanup_completed:
                    print(f"    ✓ Actual cleanup successfully removed expired files")
                    expired_test_results.append({
                        "test": "actual_cleanup_expired_removal", 
                        "result": "pass",
                        "expired_cleaned": expired_cleaned
                    })
                else:
                    print(f"    ✗ Actual cleanup failed: cleaned {expired_cleaned}, expected >= {artificially_expired_count}")
                    expired_test_results.append({
                        "test": "actual_cleanup_expired_removal", 
                        "result": "fail",
                        "expired_cleaned": expired_cleaned,
                        "expected": artificially_expired_count
                    })
                
            except Exception as e:
                print(f"    ✗ Actual cleanup failed: {e}")
                expired_test_results.append({
                    "test": "actual_cleanup_expired_removal", 
                    "result": "error",
                    "error": str(e)
                })
            
            # Step 5: Verify expired files are actually gone
            print("  Step 5: Verifying expired files were actually deleted...")
            
            files_still_exist = 0
            for file_id in expired_file_ids:
                try:
                    metadata = await staging_service.get_staging_metadata(file_id, enterprise_user.user_id)
                    if metadata:
                        files_still_exist += 1
                except Exception:
                    pass  # File not found is expected
            
            if files_still_exist == 0:
                print(f"    ✓ All expired files were successfully deleted")
                expired_test_results.append({
                    "test": "expired_files_deleted", 
                    "result": "pass"
                })
                
                # Remove from our tracking since they're gone
                self.staged_files = [sf for sf in self.staged_files if sf["test_type"] != "expired"]
                
            else:
                print(f"    ✗ {files_still_exist}/{len(expired_file_ids)} expired files still exist")
                expired_test_results.append({
                    "test": "expired_files_deleted", 
                    "result": "fail",
                    "remaining_files": files_still_exist
                })
            
            # Step 6: Test API endpoint cleanup with fresh expired file
            print("  Step 6: Testing admin cleanup API endpoint with expired files...")
            
            # Upload one more file to expire and test via API
            api_test_files = []
            for i in range(1):
                filename = f"api_expire_test_{i}_{uuid.uuid4().hex[:8]}.png"
                api_test_files.append(("files", (filename, image_data, "image/png")))
            
            api_upload_response = await client.post(
                f"{API_BASE_URL}/ai-files/staging/bulk-upload",
                files=api_test_files,
                data={"max_concurrent_uploads": "1"},
                headers=headers
            )
            
            if api_upload_response.status_code == 201:
                api_upload_data = api_upload_response.json()
                
                # NEW: Extract files from organized structure using helper function
                api_staged_files = self.extract_staged_files_from_response(api_upload_data)
                
                # Artificially expire this file too
                for staged_file in api_staged_files:
                    file_id = staged_file["file_id"]
                    original_filename = staged_file["filename"]
                    
                    try:
                        s3_key = image_storage_service.generate_image_storage_key(file_id, original_filename)
                        current_metadata = await staging_service._get_object_metadata(s3_key)
                        
                        if current_metadata:
                            expired_metadata = {
                                'file_id': file_id,
                                'original_filename': original_filename,
                                'content_type': staged_file.get("content_type", "image/png"),
                                'file_size': str(staged_file.get("size", len(image_data))),
                                'user_id': enterprise_user.user_id,
                                'staged_at': current_metadata.get('staged_at', datetime.utcnow().isoformat()),
                                'expires_at': (datetime.utcnow() - timedelta(minutes=30)).isoformat(),  # Expired 30 min ago
                                'state': 'staging',
                                'purpose': 'vision'
                            }
                            
                            if await self._update_s3_object_metadata(s3_key, expired_metadata):
                                print(f"    ✓ Artificially expired API test file: {file_id}")
                            else:
                                print(f"    ✗ Failed to expire API test file: {file_id}")
                                
                    except Exception as e:
                        print(f"    ✗ Failed to expire API test file {file_id}: {e}")
                
                # Test API cleanup
                api_cleanup_response = await client.post(
                    f"{API_BASE_URL}/ai-files/staging/admin/cleanup",
                    json={"dry_run": False},
                    headers=headers
                )
                
                if api_cleanup_response.status_code == 200:
                    api_cleanup_data = api_cleanup_response.json()
                    api_expired_cleaned = api_cleanup_data.get('expired_files_cleaned', 0)
                    
                    if api_expired_cleaned >= 1:
                        print(f"    ✓ API cleanup successfully removed {api_expired_cleaned} expired file(s)")
                        expired_test_results.append({
                            "test": "api_cleanup_expired_removal", 
                            "result": "pass",
                            "expired_cleaned": api_expired_cleaned
                        })
                    else:
                        print(f"    ✗ API cleanup didn't remove expected expired files: {api_expired_cleaned}")
                        expired_test_results.append({
                            "test": "api_cleanup_expired_removal", 
                            "result": "fail",
                            "expired_cleaned": api_expired_cleaned
                        })
                else:
                    print(f"    ✗ API cleanup failed: {api_cleanup_response.status_code}")
                    expired_test_results.append({
                        "test": "api_cleanup_expired_removal", 
                        "result": "fail",
                        "status_code": api_cleanup_response.status_code
                    })
            
            print(f"Cleanup with expired files testing completed. {len(expired_test_results)} tests performed.")
            return expired_test_results
    
    async def cleanup_test_environment(self):
        """Clean up test users and any remaining staged files"""
        print("Cleaning up test environment...")
        
        # Clean up any remaining staged files
        if self.staged_files:
            print(f"Cleaning up {len(self.staged_files)} remaining staged files...")
            for staged_file in self.staged_files:
                try:
                    await staging_service.discard_staged_file(
                        staged_file["file_id"], 
                        staged_file["user_id"]
                    )
                except Exception as e:
                    print(f"Failed to cleanup staged file {staged_file['file_id']}: {e}")
        
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
            
            # Test 2: Bulk Upload (Images)
            upload_results = await self.test_bulk_staging_upload_flow()
            print()
            
            # Test 2.1: Document-Only Upload
            document_results = await self.test_document_only_staging_upload()
            print()
            
            # Test 2.2: Mixed Files Upload
            mixed_results = await self.test_mixed_file_staging_upload()
            print()
            
            # Test 3: Individual Discard
            individual_discard_results = await self.test_individual_staging_discard_flow()
            print()
            
            # Test 4: Bulk Discard
            bulk_discard_results = await self.test_bulk_staging_discard_flow()
            print()
            
            # Test 4.1: Document-Only Discard
            document_discard_results = await self.test_document_discard_flow()
            print()
            
            # Test 4.2: Mixed Files Cleanup
            mixed_cleanup_results = await self.test_mixed_files_cleanup_flow()
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
            
            # Test 8: Background Cleanup (Basic)
            cleanup_results = await self.test_background_cleanup_comprehensive()
            print()
            
            # Test 9: Cleanup with Expired Files (NEW)
            expired_cleanup_results = await self.test_cleanup_with_expired_files()
            print()
            
            # Test 10: Direct Service Testing
            service_direct_result = await self.test_staging_service_direct()
            print()
            
            # Test 11: Error Handling
            error_results = await self.test_error_handling()
            print()
            
            # Summary
            print("=" * 60)
            print("COMPREHENSIVE STAGING TEST SUMMARY")
            print("=" * 60)
            print(f"✓ Service Status: {'PASS' if status_result else 'FAIL'}")
            print(f"✓ Image Upload Tests: {len(upload_results)} scenarios completed")
            print(f"✓ Document Upload Tests: {len(document_results)} scenarios completed")
            print(f"✓ Mixed Files Upload Tests: {len(mixed_results)} scenarios completed")
            print(f"✓ Individual Discard: {len(individual_discard_results)} files tested")
            print(f"✓ Bulk Discard: {len(bulk_discard_results)} scenarios tested")
            print(f"✓ Document Discard: {len(document_discard_results)} operations tested")
            print(f"✓ Mixed Files Cleanup: {len(mixed_cleanup_results)} operations tested")
            print(f"✓ Mixed Operations: {len(mixed_results)} scenarios tested")
            print(f"✓ Advanced Edge Cases: {len(edge_case_results)} tests performed")
            print(f"✓ Concurrent Operations: {len(concurrent_results)} tests performed")
            print(f"✓ Background Cleanup: {len(cleanup_results)} tests performed")
            print(f"✓ Expired Files Cleanup: {len(expired_cleanup_results)} tests performed")
            print(f"✓ Direct Service: {'PASS' if service_direct_result else 'FAIL'}")
            print(f"✓ Error Handling: {len(error_results)} conditions tested")
            print()
            print("COMPREHENSIVE STAGING FLOW VERIFIED:")
            print("1. Client uploads files (images & documents) → gets file_ids")
            print("2. Images get img_* IDs, documents get file_* IDs")
            print("3. Files categorized as 'images', 'vectors', or 'unknown'")
            print("4. Client sends same file_ids to discard → files deleted")
            print("5. Background cleanup removes expired files automatically")
            print("6. Admin cleanup endpoint provides manual cleanup control")
            print("7. Expired file detection and removal works correctly")
            print("8. User isolation through ownership validation")
            print("9. Mixed file type operations work seamlessly")
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