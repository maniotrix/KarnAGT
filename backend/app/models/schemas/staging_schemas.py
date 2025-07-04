"""
Staging File Data Structures
Provides clean separation between image files (for OpenAI/LLM) and vector files (for RAG)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import mimetypes
from pathlib import Path


class FileType(Enum):
    """File type classification for processing"""
    IMAGE = "image"
    VECTOR = "vector"
    UNKNOWN = "unknown"


class FilePurpose(Enum):
    """Processing purpose for staged files"""
    VISION = "vision"  # For OpenAI vision API
    RAG = "rag"       # For RAG processing
    MIXED = "mixed"   # Contains both types


@dataclass
class StagingFileInfo:
    """Individual staging file information"""
    file_id: str
    s3_key: str
    filename: str
    content_type: str
    file_size: int
    file_type: FileType = FileType.UNKNOWN
    
    def __post_init__(self):
        """Auto-classify file type based on content type and extension"""
        if not self.file_type or self.file_type == FileType.UNKNOWN:
            self.file_type = self._classify_file_type()
    
    def _classify_file_type(self) -> FileType:
        """Classify file as image or vector document"""
        # Check by content type first
        if self.content_type.startswith('image/'):
            return FileType.IMAGE
        
        # Check by file extension for vector documents
        extension = Path(self.filename).suffix.lower()
        vector_extensions = {
            '.pdf', '.doc', '.docx', '.txt', '.md', '.rtf',
            '.ppt', '.pptx', '.xls', '.xlsx', '.csv',
            '.odt', '.ods', '.odp', '.epub'
        }
        
        if extension in vector_extensions:
            return FileType.VECTOR
        
        # Check content type for vector documents
        vector_content_types = {
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/plain',
            'text/markdown',
            'text/csv'
        }
        
        if self.content_type in vector_content_types:
            return FileType.VECTOR
        
        return FileType.UNKNOWN
    
    @property
    def is_image(self) -> bool:
        """Check if file is an image"""
        return self.file_type == FileType.IMAGE
    
    @property
    def is_vector_document(self) -> bool:
        """Check if file is a vector document"""
        return self.file_type == FileType.VECTOR
    
    @property
    def is_processable(self) -> bool:
        """Check if file can be processed by either image or vector pipeline"""
        return self.file_type in [FileType.IMAGE, FileType.VECTOR]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "file_id": self.file_id,
            "s3_key": self.s3_key,
            "filename": self.filename,
            "content_type": self.content_type,
            "file_size": self.file_size,
            "file_type": self.file_type.value,
            "is_image": self.is_image,
            "is_vector_document": self.is_vector_document
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StagingFileInfo':
        """Create from dictionary"""
        file_type = FileType.UNKNOWN
        if "file_type" in data:
            try:
                file_type = FileType(data["file_type"])
            except ValueError:
                file_type = FileType.UNKNOWN
        
        return cls(
            file_id=data["file_id"],
            s3_key=data["s3_key"],
            filename=data.get("filename", ""),
            content_type=data.get("content_type", "application/octet-stream"),
            file_size=data.get("file_size", 0),
            file_type=file_type
        )


@dataclass
class StagingFileCollection:
    """Collection of staging files organized by type"""
    images: List[StagingFileInfo] = field(default_factory=list)
    vectors: List[StagingFileInfo] = field(default_factory=list)
    unknown: List[StagingFileInfo] = field(default_factory=list)
    
    @property
    def total_count(self) -> int:
        """Total number of files"""
        return len(self.images) + len(self.vectors) + len(self.unknown)
    
    @property
    def image_count(self) -> int:
        """Number of image files"""
        return len(self.images)
    
    @property
    def vector_count(self) -> int:
        """Number of vector documents"""
        return len(self.vectors)
    
    @property
    def unknown_count(self) -> int:
        """Number of unknown/unprocessable files"""
        return len(self.unknown)
    
    @property
    def purpose(self) -> FilePurpose:
        """Determine overall purpose of the collection"""
        has_images = self.image_count > 0
        has_vectors = self.vector_count > 0
        
        if has_images and has_vectors:
            return FilePurpose.MIXED
        elif has_images:
            return FilePurpose.VISION
        elif has_vectors:
            return FilePurpose.RAG
        else:
            return FilePurpose.MIXED  # Default for empty or unknown files
    
    @property
    def is_empty(self) -> bool:
        """Check if collection is empty"""
        return self.total_count == 0
    
    @property
    def has_processable_files(self) -> bool:
        """Check if collection has any processable files"""
        return self.image_count > 0 or self.vector_count > 0
    
    @property
    def has_images(self) -> bool:
        """Check if collection has image files"""
        return self.image_count > 0
    
    @property
    def has_vectors(self) -> bool:
        """Check if collection has vector documents"""
        return self.vector_count > 0
    
    def add_file(self, file_info: StagingFileInfo) -> None:
        """Add file to appropriate list based on type"""
        if file_info.is_image:
            self.images.append(file_info)
        elif file_info.is_vector_document:
            self.vectors.append(file_info)
        else:
            self.unknown.append(file_info)
    
    def get_all_files(self) -> List[StagingFileInfo]:
        """Get all files as a single list"""
        return self.images + self.vectors + self.unknown
    
    def get_processable_files(self) -> List[StagingFileInfo]:
        """Get only processable files (images + vectors)"""
        return self.images + self.vectors
    
    def get_image_file_ids(self) -> List[str]:
        """Get file IDs for image files only"""
        return [img.file_id for img in self.images]
    
    def get_vector_s3_keys(self) -> List[str]:
        """Get S3 keys for vector documents only"""
        return [doc.s3_key for doc in self.vectors]
    
    def get_image_staging_data(self) -> List[Dict[str, str]]:
        """Get image files formatted for staging service"""
        return [
            {"file_id": img.file_id, "s3_key": img.s3_key}
            for img in self.images
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "images": [img.to_dict() for img in self.images],
            "vectors": [doc.to_dict() for doc in self.vectors],
            "unknown": [file.to_dict() for file in self.unknown],
            "summary": {
                "total_count": self.total_count,
                "image_count": self.image_count,
                "vector_count": self.vector_count,
                "unknown_count": self.unknown_count,
                "purpose": self.purpose.value,
                "has_processable_files": self.has_processable_files,
                "has_images": self.has_images,
                "has_vectors": self.has_vectors
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StagingFileCollection':
        """Create from dictionary"""
        collection = cls()
        
        # Add images
        for img_data in data.get("images", []):
            img_info = StagingFileInfo.from_dict(img_data)
            collection.images.append(img_info)
        
        # Add vectors
        for doc_data in data.get("vectors", []):
            doc_info = StagingFileInfo.from_dict(doc_data)
            collection.vectors.append(doc_info)
        
        # Add unknown
        for file_data in data.get("unknown", []):
            file_info = StagingFileInfo.from_dict(file_data)
            collection.unknown.append(file_info)
        
        return collection


def validate_staging_files_structure(staging_files: Dict[str, List[Dict[str, str]]]) -> tuple[bool, List[str]]:
    """Validate staging files structure and return errors"""
    errors = []
    
    if not staging_files:
        return True, []
    
    if not isinstance(staging_files, dict):
        errors.append("staging_files must be a dictionary")
        return False, errors
    
    valid_keys = {"images", "vectors", "unknown"}
    
    for key in staging_files.keys():
        if key not in valid_keys:
            errors.append(f"Invalid key '{key}'. Must be one of: {valid_keys}")
    
    for file_type, file_list in staging_files.items():
        if not isinstance(file_list, list):
            errors.append(f"{file_type}: Must be a list")
            continue
        
        for i, file_data in enumerate(file_list):
            if not isinstance(file_data, dict):
                errors.append(f"{file_type}[{i}]: Must be a dictionary")
                continue
            
            if "file_id" not in file_data:
                errors.append(f"{file_type}[{i}]: Missing file_id")
            
            if "s3_key" not in file_data:
                errors.append(f"{file_type}[{i}]: Missing s3_key")
    
    return len(errors) == 0, errors 