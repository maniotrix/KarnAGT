from llama_index.core import SimpleDirectoryReader, Document
import tempfile
import os
import shutil
import logging
import uuid
import time
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List, AsyncGenerator
from app.services.storage.storage import S3StorageBackend
from llama_index.core.readers.base import BaseReader

logger = logging.getLogger(__name__)

class S3DirectoryReader:
    """Scalable S3 directory reader with streaming and proper resource management."""
    
    def __init__(self, storage_backend: S3StorageBackend, max_concurrent_downloads: int = 5):
        """Initialize S3DirectoryReader with connection pooling."""
        self.storage_backend = storage_backend
        self.max_concurrent_downloads = max_concurrent_downloads
    
    def _create_temp_directory(self) -> str:
        """Create a unique temporary directory for downloaded files."""
        # Create unique identifier with timestamp, process ID, and UUID
        timestamp = int(time.time())
        process_id = os.getpid()
        unique_id = uuid.uuid4().hex[:8]
        
        # Create unique prefix
        unique_prefix = f"s3_docs_{timestamp}_{process_id}_{unique_id}_"
        
        temp_dir = tempfile.mkdtemp(prefix=unique_prefix)
        logger.info(f"Created unique temporary directory: {temp_dir}")
        return temp_dir
    
    def cleanup_temp_directory(self, temp_dir: str):
        """Clean up the temporary directory and all its contents."""
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.error(f"Failed to cleanup temporary directory {temp_dir}: {e}")
    
    @asynccontextmanager
    async def temp_directory_context(self) -> AsyncGenerator[str, None]:
        """Async context manager for temporary directory with guaranteed cleanup."""
        temp_dir = self._create_temp_directory()
        try:
            yield temp_dir
        finally:
            self.cleanup_temp_directory(temp_dir)
    
    async def download_files_streaming(self, s3_keys: List[str], temp_dir: str) -> Dict[str, Any]:
        """Download files using the storage backend's concurrent download method."""
        logger.info(f"Downloading {len(s3_keys)} files using storage backend with {self.max_concurrent_downloads} max concurrent downloads")
        
        # Use the storage backend's improved download_multiple_files method
        result = await self.storage_backend.download_multiple_files(
            keys=s3_keys,
            local_dir=temp_dir,
            max_concurrent=self.max_concurrent_downloads
        )
        
        # Convert result format to match expected interface
        successful_downloads = []
        for file_path in result["files"]:
            # Find matching S3 key by filename
            filename = os.path.basename(file_path)
            base_filename = filename.split('_')[0] if '_' in filename else filename  # Handle duplicate suffixes
            matching_key = next((key for key in s3_keys if os.path.basename(key) == filename or os.path.basename(key) == base_filename), None)
            if matching_key:
                successful_downloads.append({"s3_key": matching_key, "local_path": file_path})
        
        failed_downloads = [{"s3_key": key, "error": "Download failed"} for key in result["failed_keys"]]
        
        return {
            "successful_downloads": successful_downloads,
            "failed_downloads": failed_downloads,
            "total_requested": result["total_requested"],
            "success_count": result["successful"],
            "failure_count": result["failed_count"]
        }
    
    async def download_directory_streaming(self, s3_directory_prefix: str, temp_dir: str) -> Dict[str, Any]:
        """Download directory with streaming approach."""
        return await self.storage_backend.download_directory(s3_directory_prefix, temp_dir)
    
    async def load_documents_from_s3_keys(
        self,
        s3_keys: List[str],
        file_extractor: Optional[Dict[str, BaseReader]] = None,
        exclude_patterns: Optional[List[str]] = None,
        num_workers: Optional[int] = None,
        show_progress: bool = False,
        add_s3_metadata: bool = True
    ) -> List[Document]:
        """
        Load documents from specific S3 keys with proper resource management.
        
        Args:
            s3_keys: List of S3 keys to download and process
            file_extractor: Custom file extractors for different file types
            exclude_patterns: Patterns to exclude from processing
            num_workers: Number of worker threads for document processing
            show_progress: Whether to show progress bars
            add_s3_metadata: Whether to add S3 metadata to documents
            
        Returns:
            List of processed documents
        """
        if not s3_keys:
            logger.warning("No S3 keys provided")
            return []
        
        logger.info(f"Starting document loading from {len(s3_keys)} S3 keys")
        
        # Create mapping of S3 keys to original filenames for metadata preservation  
        s3_key_to_original_filename = {}
        for s3_key in s3_keys:
            # Try to extract original filename from S3 metadata
            original_filename = await self._get_original_filename_from_s3_metadata(s3_key)
            if not original_filename:
                # Fallback: guess original filename from the provided s3_key
                original_filename = self._extract_original_filename_from_context(s3_key)
            
            s3_key_to_original_filename[s3_key] = original_filename
        
        async with self.temp_directory_context() as temp_dir:
            # Step 1: Download files with streaming
            download_result = await self.download_files_streaming(s3_keys, temp_dir)
            
            if download_result["success_count"] == 0:
                logger.error("No files downloaded successfully")
                return []
            
            # Create mapping of local filenames to S3 keys and original filenames
            local_to_s3_mapping = {}
            for download_info in download_result["successful_downloads"]:
                local_path = download_info["local_path"] 
                s3_key = download_info["s3_key"]
                local_filename = os.path.basename(local_path)
                original_filename = s3_key_to_original_filename.get(s3_key, local_filename)
                
                local_to_s3_mapping[local_filename] = {
                    "s3_key": s3_key,
                    "original_filename": original_filename
                }
            
            # Step 2: Process documents using SimpleDirectoryReader
            logger.info(f"Processing {download_result['success_count']} downloaded files")
            
            reader = SimpleDirectoryReader(
                input_dir=temp_dir,
                file_extractor=file_extractor,
                exclude=exclude_patterns,
                recursive=True
            )
            
            documents = await reader.aload_data(
                show_progress=show_progress,
                num_workers=num_workers
            )
            
            # Step 3: Fix metadata to preserve original filenames and add S3 metadata
            for doc in documents:
                if hasattr(doc, 'metadata') and doc.metadata:
                    current_file_path = doc.metadata.get('file_path', '')
                    current_filename = os.path.basename(current_file_path)
                    
                    # Look up original filename and S3 key
                    mapping_info = local_to_s3_mapping.get(current_filename)
                    if mapping_info:
                        # CRITICAL FIX: Restore original filename in metadata
                        doc.metadata['file_name'] = mapping_info["original_filename"]
                        
                        if add_s3_metadata:
                            doc.metadata['source_type'] = 's3'
                            doc.metadata['s3_bucket'] = self.storage_backend.bucket_name
                            doc.metadata['s3_key'] = mapping_info["s3_key"]
                            # Keep both for compatibility
                            doc.metadata['s3_original_filename'] = mapping_info["original_filename"]
                    
                    elif add_s3_metadata:
                        # Fallback if mapping not found
                        doc.metadata['source_type'] = 's3'
                        doc.metadata['s3_bucket'] = self.storage_backend.bucket_name
                    
                    # Add status metadata for document lifecycle management
                    doc.metadata['status'] = 'active'
                    doc.metadata['created_at'] = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"Successfully processed {len(documents)} documents from S3 with restored filenames")
            return documents
    
    async def _get_original_filename_from_s3_metadata(self, s3_key: str) -> Optional[str]:
        """Try to get original filename from S3 object metadata."""
        try:
            response = self.storage_backend.s3_client.head_object(
                Bucket=self.storage_backend.bucket_name,
                Key=s3_key
            )
            # Check if original filename is stored in S3 metadata
            # S3 metadata keys are case-insensitive and often lowercase
            metadata = response.get('Metadata', {})
            
            # Try different possible metadata key variations
            for key in ['original-filename', 'original_filename', 'originalfilename']:
                if key in metadata:
                    original_filename = metadata[key]
                    logger.debug(f"Found original filename in S3 metadata: {original_filename}")
                    return original_filename
            
            return None
        except Exception as e:
            logger.debug(f"Could not get S3 metadata for {s3_key}: {e}")
            return None
    
    def _extract_original_filename_from_context(self, s3_key: str) -> str:
        """
        Extract or guess original filename from S3 key or context.
        
        This is a fallback method when S3 metadata is not available.
        In a proper implementation, the original filename should be passed
        to this method or stored in S3 metadata during upload.
        """
        # For now, return the S3 key basename as fallback
        # In practice, this should be enhanced to receive original filenames
        # from the calling context (e.g., from upload records or metadata)
        return os.path.basename(s3_key)
    
    async def load_documents_from_s3_directory(
        self,
        s3_directory_prefix: str,
        file_extractor: Optional[Dict[str, BaseReader]] = None,
        exclude_patterns: Optional[List[str]] = None,
        num_workers: Optional[int] = None,
        show_progress: bool = False,
        add_s3_metadata: bool = True
    ) -> List[Document]:
        """
        Load documents from an S3 directory with proper resource management.
        
        Args:
            s3_directory_prefix: S3 directory prefix to download and process
            file_extractor: Custom file extractors for different file types
            exclude_patterns: Patterns to exclude from processing
            num_workers: Number of worker threads for document processing
            show_progress: Whether to show progress bars
            add_s3_metadata: Whether to add S3 metadata to documents
            
        Returns:
            List of processed documents
        """
        logger.info(f"Starting document loading from S3 directory: {s3_directory_prefix}")
        
        async with self.temp_directory_context() as temp_dir:
            # Step 1: Download directory
            download_result = await self.download_directory_streaming(s3_directory_prefix, temp_dir)
            
            if not download_result.get("files"):
                logger.warning(f"No files found in S3 directory: {s3_directory_prefix}")
                return []
            
            # Step 2: Process documents
            logger.info(f"Processing {len(download_result['files'])} downloaded files")
            
            reader = SimpleDirectoryReader(
                input_dir=temp_dir,
                file_extractor=file_extractor,
                exclude=exclude_patterns or [],
                recursive=True
            )
            
            documents = await reader.aload_data(
                show_progress=show_progress,
                num_workers=num_workers
            )
            
            # Step 3: Add S3 metadata if requested
            if add_s3_metadata:
                for doc in documents:
                    if hasattr(doc, 'metadata') and doc.metadata:
                        doc.metadata['source_type'] = 's3'
                        doc.metadata['s3_bucket'] = self.storage_backend.bucket_name
                        doc.metadata['s3_prefix'] = s3_directory_prefix
            
            logger.info(f"Successfully processed {len(documents)} documents from S3 directory")
            return documents


# Convenience function for backward compatibility
async def load_s3_documents_async(
    s3_bucket_name: str,
    s3_keys: List[str], 
    file_extractor: Dict[str, BaseReader], 
    num_workers: int,
    show_progress: bool,
    add_s3_metadata: bool = True,
    exclude_patterns: Optional[list] = None
) -> List[Document]:
    """Load documents asynchronously (backward compatibility function)."""
    storage_backend = S3StorageBackend(bucket_name=s3_bucket_name)
    reader = S3DirectoryReader(storage_backend)
    
    return await reader.load_documents_from_s3_keys(
        s3_keys=s3_keys,
        file_extractor=file_extractor,
        exclude_patterns=exclude_patterns,
        num_workers=num_workers,
        show_progress=show_progress
    )
    