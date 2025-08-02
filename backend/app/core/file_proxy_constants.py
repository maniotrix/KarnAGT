"""
File Proxy Constants
Centralized constants for file proxy endpoints and URL generation
"""

import os
from enum import Enum
from typing import Dict, Any
from app.core.config import settings

# =============================================================================
# FILE PROXY ENDPOINT CONSTANTS
# =============================================================================

class FileProxyType(str, Enum):
    """File types supported by proxy system"""
    IMAGE = "image"
    KNOWLEDGE = "knowledge"
    CODE_GENERATED = "code_generated"

class FileProxyEndpoints:
    """File proxy endpoint path constants"""
    
    # Base proxy path for URL generation (full API path)
    BASE_PATH = "/api/v1/proxy"
    
    # Specific endpoint patterns for URL generation
    IMAGE_PROXY = f"{BASE_PATH}/images/{{file_id}}"
    KNOWLEDGE_PROXY = f"{BASE_PATH}/files/{{knowledge_file_id}}"
    CODE_GENERATED_PROXY = f"{BASE_PATH}/code-files/{{file_id}}"
    
    # Router patterns (simple paths for FastAPI route decoration)
    IMAGE_PROXY_ROUTE = "/images/{file_id}"
    KNOWLEDGE_PROXY_ROUTE = "/files/{knowledge_file_id}"
    CODE_GENERATED_PROXY_ROUTE = "/code-files/{file_id}"

class FileProxyParams:
    """Parameter names used in file proxy endpoints"""
    
    FILE_ID = "file_id"
    KNOWLEDGE_FILE_ID = "knowledge_file_id"
    
    # Query parameters
    DOWNLOAD = "download"  # Force download vs inline
    FILENAME = "filename"  # Override filename
    CACHE_DURATION = "cache"  # Cache duration in seconds

class FileProxyHeaders:
    """Headers used in file proxy responses"""
    
    CONTENT_TYPE = "Content-Type"
    CONTENT_DISPOSITION = "Content-Disposition"
    CONTENT_LENGTH = "Content-Length"
    CACHE_CONTROL = "Cache-Control"
    X_FILE_ID = "X-File-ID"
    X_FILE_TYPE = "X-File-Type"
    X_USER_ID = "X-User-ID"

# =============================================================================
# URL GENERATION HELPERS
# =============================================================================
    
BASE_URL = settings.server_base_url

def build_image_proxy_url(file_id: str, **query_params) -> str:
    """
    Build image proxy URL with optional query parameters
    
    Args:
        base_url: API base URL (e.g., "https://api.yourapp.com")
        file_id: Image file ID
        **query_params: Optional query parameters
        
    Returns:
        Complete proxy URL
    """
    if not file_id:
        raise ValueError("File ID is required")
    
    url = f"{BASE_URL.rstrip('/')}{FileProxyEndpoints.IMAGE_PROXY.format(file_id=file_id)}"
    
    if query_params:
        query_string = "&".join([f"{k}={v}" for k, v in query_params.items() if v is not None])
        if query_string:
            url = f"{url}?{query_string}"
    
    return url

def build_knowledge_proxy_url(knowledge_file_id: str, **query_params) -> str:
    """
    Build knowledge file proxy URL with optional query parameters
    
    Args:
        base_url: API base URL (e.g., "https://api.yourapp.com")  
        knowledge_file_id: Knowledge file ID
        **query_params: Optional query parameters
        
    Returns:
        Complete proxy URL
    """
    if not knowledge_file_id:
        raise ValueError("Knowledge file ID is required")
    
    url = f"{BASE_URL.rstrip('/')}{FileProxyEndpoints.KNOWLEDGE_PROXY.format(knowledge_file_id=knowledge_file_id)}"
    
    if query_params:
        query_string = "&".join([f"{k}={v}" for k, v in query_params.items() if v is not None])
        if query_string:
            url = f"{url}?{query_string}"
    
    return url

def build_code_generated_proxy_url(file_id: str) -> str:
    """
    Build code-generated file proxy URL
    
    Args:
        file_id: Code-generated file ID with CODE_GENERATED_FILE_PREFIX (e.g., "code_generated_2024_01_15_abc12345_myfile.png")
        
    Returns:
        Complete proxy URL
    """
    if not file_id:
        raise ValueError("File ID is required")
    
    url = f"{BASE_URL.rstrip('/')}{FileProxyEndpoints.CODE_GENERATED_PROXY.format(file_id=file_id)}"
    return url

# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

class FileProxyConfig:
    """Configuration constants for file proxy system"""
    
    # Security
    DEFAULT_PRESIGNED_EXPIRY = 300  # 5 minutes for proxy operations
    MAX_PRESIGNED_EXPIRY = 3600     # 1 hour maximum expiry
    
    # Performance
    DEFAULT_CACHE_DURATION = 3600   # 1 hour default cache
    MAX_CACHE_DURATION = 86400      # 24 hours maximum cache
    
    # File handling
    MAX_FILE_SIZE_MB = 100          # Maximum file size for proxy
    CHUNK_SIZE = 8192               # Streaming chunk size
    
    # Storage paths
    CODE_SANDBOX_GENERATED_PREFIX = "code_sandbox_generated"
    CODE_GENERATED_FILE_PREFIX = "code_generated"
    
    # Rate limiting (requests per minute per user)
    RATE_LIMIT_PER_USER = 100
    
    # Allowed query parameters
    ALLOWED_QUERY_PARAMS = {
        FileProxyParams.DOWNLOAD,
        FileProxyParams.FILENAME,
        FileProxyParams.CACHE_DURATION
    }

# =============================================================================
# RESPONSE CONSTANTS
# =============================================================================

class FileProxyErrors:
    """Error message constants for file proxy"""
    
    FILE_NOT_FOUND = "File not found or access denied"
    INVALID_FILE_ID = "Invalid file ID format"
    INVALID_KNOWLEDGE_FILE_ID = "Invalid knowledge file ID"
    UNAUTHORIZED_ACCESS = "Unauthorized file access"
    FILE_TOO_LARGE = "File too large for proxy access"
    PROCESSING_ERROR = "Error processing file request"
    INVALID_PARAMETERS = "Invalid request parameters"

class FileProxyStatus:
    """Status constants for file proxy operations"""
    
    SUCCESS = "success"
    ERROR = "error"
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"
    INVALID_REQUEST = "invalid_request"

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_file_proxy_metadata(file_type: FileProxyType, file_id: str, **extra_data) -> Dict[str, Any]:
    """
    Generate standardized metadata for file proxy operations
    
    Args:
        file_type: Type of file (image/knowledge)
        file_id: File identifier
        **extra_data: Additional metadata
        
    Returns:
        Standardized metadata dictionary
    """
    return {
        "file_type": file_type.value,
        "file_id": file_id,
        "proxy_version": "1.0",
        "timestamp": None,  # Will be set by endpoint
        **extra_data
    }

def validate_file_proxy_params(file_type: FileProxyType, **params) -> Dict[str, Any]:
    """
    Validate file proxy parameters
    
    Args:
        file_type: Type of file being proxied
        **params: Parameters to validate
        
    Returns:
        Validated parameters dictionary
        
    Raises:
        ValueError: If parameters are invalid
    """
    validated = {}
    
    if file_type == FileProxyType.IMAGE:
        file_id = params.get(FileProxyParams.FILE_ID)
        if not file_id or not isinstance(file_id, str):
            raise ValueError(FileProxyErrors.INVALID_FILE_ID)
        if not file_id.startswith(("img_", "file_")):
            raise ValueError(FileProxyErrors.INVALID_FILE_ID)
        validated[FileProxyParams.FILE_ID] = file_id
        
    elif file_type == FileProxyType.KNOWLEDGE:
        knowledge_file_id = params.get(FileProxyParams.KNOWLEDGE_FILE_ID)
        if not isinstance(knowledge_file_id, str) or not knowledge_file_id.strip():
            raise ValueError(FileProxyErrors.INVALID_KNOWLEDGE_FILE_ID)
        validated[FileProxyParams.KNOWLEDGE_FILE_ID] = knowledge_file_id
    
    # Validate optional parameters
    for param_name, param_value in params.items():
        if param_name in FileProxyConfig.ALLOWED_QUERY_PARAMS and param_value is not None:
            validated[param_name] = param_value
    
    return validated

# =============================================================================
# CONTEXT INTEGRATION CONSTANTS
# =============================================================================

class ContextFileKeys:
    """Keys used when adding file URLs to context"""
    
    # Image context keys
    IMAGE_FILE_ID = "file_id"
    IMAGE_OPENAI_FILE_ID = "openai_file_id"
    IMAGE_FILENAME = "filename"
    IMAGE_DOWNLOAD_URL = "image_file_url"
    IMAGE_CONTENT_TYPE = "content_type"
    
    # Knowledge file context keys
    KNOWLEDGE_FILE_ID = "knowledge_file_id"
    KNOWLEDGE_REF_DOC_IDS = "ref_doc_ids"
    KNOWLEDGE_FILENAME = "filename" 
    KNOWLEDGE_DOWNLOAD_URL = "knowledge_file_url"
    KNOWLEDGE_CONTENT_TYPE = "content_type"
    KNOWLEDGE_NODE_COUNT = "node_count"
    
    # Common context keys
    FILE_SIZE = "file_size"
    PROCESSING_STATUS = "processing_status"