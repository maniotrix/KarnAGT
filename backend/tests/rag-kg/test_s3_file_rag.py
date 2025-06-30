import os
from dotenv import load_dotenv
import uuid
from datetime import datetime
import asyncio


current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))

import sys
sys.path.append(backend_dir)

from app.services.knowledge.rag_service import RAGService
from app.services.knowledge.config import RAGConfig
from app.services.storage.storage import S3StorageBackend, get_content_type

load_dotenv()
TEMP_DIR = os.path.join(current_dir, "tmp")
os.makedirs(TEMP_DIR, exist_ok=True)

def generate_file_id() -> str:
    """Generate unique file ID"""
    return f"file_{uuid.uuid4().hex[:8]}"

def generate_storage_key( file_id: str, filename: str) -> str:
    """Generate S3 key for file storage"""
    date_prefix = datetime.now().strftime("%Y/%m/%d")
    file_extension = os.path.splitext(filename)[1].lower()
    return f"files/{date_prefix}/{file_id}{file_extension}"

def extract_directory_from_s3_key(s3_key: str) -> str:
    """Extract directory path from S3 key (everything except the filename)"""
    # s3_key = "files/2025/06/30/file_abc123.pdf" 
    # returns = "files/2025/06/30"
    path_parts = s3_key.split("/")
    return "/".join(path_parts[:-1])  # All parts except the last (filename)

async def download_file_from_s3(bucket_name: str, s3_key: str):
    """Download a file from S3 to a local temp path"""
    s3_storage_backend = S3StorageBackend(bucket_name=bucket_name)
    
    # Extract filename from S3 key
    filename = os.path.basename(s3_key)
    local_file_path = os.path.join(TEMP_DIR, filename)
    
    downloaded_file_path = await s3_storage_backend.download_file(s3_key, local_file_path)
    if downloaded_file_path is None:
        raise Exception(f"Failed to download file {s3_key} to {local_file_path}")
    return downloaded_file_path

async def clear_temp_dir():
    """Clear the temp directory"""
    import shutil
    shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR, exist_ok=True)

async def test_s3_file_doc_loading():
    await clear_temp_dir()
    """Test loading documents from S3."""
    rag_config = RAGConfig(s3_bucket_name="test-rag-bucket")
    # upload test files to s3
    test_docs_dir = os.path.join(backend_dir, "test_docs")
    test_docs_file_name = "PRY NDLS 20 June.pdf"
    test_docs_file = os.path.join(test_docs_dir, test_docs_file_name)
    
    print(f"Uploading file {test_docs_file} to S3...")
   # Generate file ID and storage key
    file_id = generate_file_id()
    s3_key = generate_storage_key(file_id, test_docs_file_name)
    s3_storage_backend = S3StorageBackend(bucket_name=rag_config.s3_bucket_name)
    
    # Clear bucket first (and ensure it exists)
    print("Clearing and ensuring bucket exists...")
    await s3_storage_backend.ensure_bucket_exists()
    s3_storage_backend.clear_bucket(rag_config.s3_bucket_name)
    
    content_type = get_content_type(test_docs_file)
    
    # upload file to s3
    print(f"Uploading file {test_docs_file} to S3 with key: {s3_key}...")
    await s3_storage_backend.upload_file_direct(test_docs_file, s3_key, content_type)
    
    # Verify file exists after upload
    try:
        response = s3_storage_backend.s3_client.head_object(
            Bucket=rag_config.s3_bucket_name, 
            Key=s3_key
        )
        print(f"✅ File verified in S3: {s3_key}, Size: {response.get('ContentLength', 'unknown')}")
    except Exception as e:
        print(f"❌ File NOT found in S3 after upload: {e}")
        return
    
    # Wait a moment for eventual consistency
    print("Waiting for file to be available...")
    await asyncio.sleep(2)
    
    # load documents from s3
    rag_service = RAGService(RAGConfig())
    
    print(f"Loading file from S3 with key: {s3_key}")
    s3_path = s3_storage_backend.get_s3_path(s3_key)
    print(f"Generated S3 path: {s3_path}")
    print(f"Bucket name being used: {rag_config.s3_bucket_name}")
    
    # Extract the directory path from the S3 key
    directory_path = extract_directory_from_s3_key(s3_key)
    print(f"Directory path: {directory_path}")
    
    # Create the input_dir for SimpleDirectoryReader (bucket + directory path)
    input_dir = f"{rag_config.s3_bucket_name}/{directory_path}"
    print(f"Input directory for SimpleDirectoryReader: {input_dir}")
    
    # try:
    #     # download the file from s3
    #     downloaded_file_path = await download_file_from_s3(rag_config.s3_bucket_name, s3_key)
    #     print(f"Downloaded file path: {downloaded_file_path}")
    # except Exception as e:
    #     print(f"Error downloading file from S3: {e}")
    
    
    
    documents = []
    try:
        documents = await rag_service.load_s3_files_async(rag_config.s3_bucket_name, [s3_key])
    except Exception as e:
        import traceback
        print(f"Error loading documents from S3: {e}")
        print(f"Error type: {type(e)}")
        print(f"Error traceback: {traceback.format_exc()}")
        
    print(f"Loaded {len(documents)} documents from S3")
    print(f"Document content: {documents}")
    
    # finally delete the file from s3
    await s3_storage_backend.delete_file(s3_key)
    print(f"Deleted file from S3 with key: {s3_key}")
    
    # # clear the temp directory
    # await clear_temp_dir()
    # print(f"Cleared temp directory: {TEMP_DIR}")
    
    
async def test_temp_directory_cleanup():
    """Test that temporary directories are properly cleaned up after document processing."""
    print("\n=== Testing Temp Directory Cleanup ===")
    
    rag_config = RAGConfig(s3_bucket_name="test-rag-bucket")
    
    # Upload test file to S3 (same as before)
    test_docs_dir = os.path.join(backend_dir, "test_docs")
    test_docs_file_name = "PRY NDLS 20 June.pdf"
    test_docs_file = os.path.join(test_docs_dir, test_docs_file_name)
    
    file_id = generate_file_id()
    s3_key = generate_storage_key(file_id, test_docs_file_name)
    s3_storage_backend = S3StorageBackend(bucket_name=rag_config.s3_bucket_name)
    
    # Clear bucket and upload file
    await s3_storage_backend.ensure_bucket_exists()
    s3_storage_backend.clear_bucket(rag_config.s3_bucket_name)
    content_type = get_content_type(test_docs_file)
    await s3_storage_backend.upload_file_direct(test_docs_file, s3_key, content_type)
    
    # Track temp directories before processing
    temp_dir_before = []
    try:
        import tempfile
        temp_root = tempfile.gettempdir()
        print(f"System temp directory: {temp_root}")
        
        # List any existing s3_docs directories before our test
        import glob
        existing_s3_dirs = glob.glob(os.path.join(temp_root, "s3_docs_*"))
        print(f"Existing S3 temp directories before test: {len(existing_s3_dirs)}")
        temp_dir_before = existing_s3_dirs.copy()
        
        # Load documents - this will create and cleanup temp directory
        rag_service = RAGService(RAGConfig())
        documents = await rag_service.load_s3_files_async(rag_config.s3_bucket_name, [s3_key])
        
        # Check if any new temp directories remain after processing
        existing_s3_dirs_after = glob.glob(os.path.join(temp_root, "s3_docs_*"))
        new_temp_dirs = [d for d in existing_s3_dirs_after if d not in temp_dir_before]
        
        print(f"✅ Documents loaded: {len(documents)}")
        print(f"✅ S3 temp directories before: {len(temp_dir_before)}")
        print(f"✅ S3 temp directories after: {len(existing_s3_dirs_after)}")
        print(f"✅ New temp directories remaining: {len(new_temp_dirs)}")
        
        if len(new_temp_dirs) == 0:
            print("🎉 SUCCESS: All temporary directories were properly cleaned up!")
        else:
            print(f"⚠️  WARNING: {len(new_temp_dirs)} temp directories remain: {new_temp_dirs}")
            
        # Verify document metadata shows original temp path
        if documents:
            first_doc = documents[0]
            if 'file_path' in first_doc.metadata:
                temp_path = first_doc.metadata['file_path']
                print(f"📁 Document was processed from: {temp_path}")
                print(f"📁 Temp directory existed during processing: {os.path.dirname(temp_path)}")
                
                # Check if that specific directory still exists
                temp_dir_used = os.path.dirname(temp_path)
                if os.path.exists(temp_dir_used):
                    print(f"❌ ERROR: Temp directory still exists: {temp_dir_used}")
                else:
                    print(f"✅ SUCCESS: Temp directory was cleaned up: {temp_dir_used}")
    
    finally:
        # Cleanup S3
        await s3_storage_backend.delete_file(s3_key)
        print(f"🧹 Cleaned up S3 file: {s3_key}")

if __name__ == "__main__":
    import asyncio
    
    async def run_all_tests():
        print("🚀 Running S3 Document Loading Tests")
        print("=" * 50)
        
        # Test 1: Original document loading test
        await test_s3_file_doc_loading()
        
        # Test 2: Temp directory cleanup verification
        await test_temp_directory_cleanup()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed!")
    
    asyncio.run(run_all_tests())
    