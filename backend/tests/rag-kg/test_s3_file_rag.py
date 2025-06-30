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

async def test_s3_file_doc_loading():
    """Test loading documents from S3."""
    rag_config = RAGConfig()
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
    
    documents = []
    try:
        documents = await rag_service.load_s3_file_async(s3_key)
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
    
    
if __name__ == "__main__":
    asyncio.run(test_s3_file_doc_loading())
    