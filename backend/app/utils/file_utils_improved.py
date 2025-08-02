#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File Utilities

Utility functions for file operations with proper error handling,
security validation, and best practices.
"""

import os
from pathlib import Path
from typing import Optional, Tuple
from app.logging.logger import get_logger

logger = get_logger(__name__)

# Constants
DEFAULT_MAX_FILE_SIZE_MB = 100
MAX_FILENAME_LENGTH = 255
BYTES_PER_MB = 1024 * 1024


class FileUtilsError(Exception):
    """Base exception for file utils errors"""
    pass


class FileNotFoundError(FileUtilsError):
    """Exception raised when file is not found"""
    pass


class FileTooLargeError(FileUtilsError):
    """Exception raised when file exceeds size limit"""
    pass


class InvalidPathError(FileUtilsError):
    """Exception raised for invalid or unsafe file paths"""
    pass


def _validate_file_path(source: str) -> Path:
    """
    Validate and normalize file path for security
    
    Args:
        source: File path to validate
        
    Returns:
        Validated Path object
        
    Raises:
        InvalidPathError: If path is invalid or unsafe
    """
    if not source or not source.strip():
        raise InvalidPathError("File path cannot be empty")
    
    try:
        path = Path(source).resolve()  # Resolve to absolute path
        
        # Security: Prevent directory traversal attacks
        # This is a basic check - you might want more sophisticated validation
        if ".." in str(path):
            raise InvalidPathError(f"Path contains directory traversal: {source}")
        
        # Check if path is too long (filesystem limit)
        if len(str(path)) > 4096:  # Common filesystem limit
            raise InvalidPathError(f"Path too long: {len(str(path))} characters")
            
        return path
        
    except (OSError, ValueError) as e:
        raise InvalidPathError(f"Invalid file path '{source}': {e}")


def _validate_filename(filename: str) -> str:
    """
    Validate filename for security and compatibility
    
    Args:
        filename: Filename to validate
        
    Returns:
        Validated filename
        
    Raises:
        InvalidPathError: If filename is invalid
    """
    if not filename or not filename.strip():
        raise InvalidPathError("Filename cannot be empty")
    
    # Remove any path separators for security
    clean_filename = os.path.basename(filename)
    
    if len(clean_filename) > MAX_FILENAME_LENGTH:
        raise InvalidPathError(f"Filename too long: {len(clean_filename)} > {MAX_FILENAME_LENGTH}")
    
    # Check for hidden files (security consideration)
    if clean_filename.startswith('.'):
        raise InvalidPathError("Hidden files not allowed for security reasons")
    
    # Check for invalid characters (basic check)
    invalid_chars = '<>:"|?*'
    if any(char in clean_filename for char in invalid_chars):
        raise InvalidPathError(f"Filename contains invalid characters: {clean_filename}")
    
    return clean_filename


def get_file_content_sync(
    source: str, 
    max_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB, 
    filename: Optional[str] = None
) -> Tuple[bytes, str]:
    """
    Get the content of a local file synchronously with proper validation
    
    Args:
        source: Local file path
        max_size_mb: Maximum file size in MB (default: 100MB)
        filename: Optional filename override
        
    Returns:
        Tuple of (file_content_bytes, final_filename)
        
    Raises:
        FileNotFoundError: If file doesn't exist
        FileTooLargeError: If file exceeds size limit
        InvalidPathError: If path or filename is invalid
        FileUtilsError: For other file operation errors
        
    Examples:
        >>> content, name = get_file_content_sync("/path/to/file.txt")
        >>> content, name = get_file_content_sync("/path/to/file.txt", max_size_mb=50)
        >>> content, name = get_file_content_sync("/path/to/file.txt", filename="custom.txt")
    """
    logger.debug(f"Reading local file: {source}")
    
    try:
        # Validate and normalize path
        path = _validate_file_path(source)
        
        # Check if file exists
        if not path.exists():
            raise FileNotFoundError(f"Local file not found: {source}")
        
        if not path.is_file():
            raise InvalidPathError(f"Path is not a file: {source}")
        
        # Check file size before reading
        file_size = path.stat().st_size
        max_size_bytes = max_size_mb * BYTES_PER_MB
        
        if file_size > max_size_bytes:
            raise FileTooLargeError(
                f"File too large: {file_size:,} bytes "
                f"(max: {max_size_bytes:,} bytes / {max_size_mb}MB)"
            )
        
        # Determine final filename
        if filename:
            final_filename = _validate_filename(filename)
        else:
            final_filename = _validate_filename(path.name)
        
        # Read file content
        # Using Path.read_bytes() is fine here - it handles the file context automatically
        logger.info(f"Reading file: {path} ({file_size:,} bytes)")
        content = path.read_bytes()
        
        # Verify content was read correctly
        if len(content) != file_size:
            raise FileUtilsError(
                f"File size mismatch: expected {file_size} bytes, read {len(content)} bytes"
            )
        
        logger.info(f"Successfully read file: {final_filename} ({len(content):,} bytes)")
        return content, final_filename
        
    except (FileNotFoundError, FileTooLargeError, InvalidPathError):
        # Re-raise our custom exceptions as-is
        raise
        
    except PermissionError as e:
        logger.error(f"Permission denied reading file {source}: {e}")
        raise FileUtilsError(f"Permission denied: {source}")
        
    except OSError as e:
        logger.error(f"OS error reading file {source}: {e}")
        raise FileUtilsError(f"Failed to read file {source}: {e}")
        
    except Exception as e:
        logger.error(f"Unexpected error reading file {source}: {e}")
        raise FileUtilsError(f"Unexpected error reading file {source}: {e}")


async def get_file_content(
    source: str, 
    max_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB, 
    filename: Optional[str] = None
) -> Tuple[bytes, str]:
    """
    Get the content of a local file asynchronously
    
    This is a wrapper around the synchronous version for async compatibility.
    For truly async file I/O, consider using aiofiles library.
    
    Args:
        source: Local file path
        max_size_mb: Maximum file size in MB (default: 100MB)  
        filename: Optional filename override
        
    Returns:
        Tuple of (file_content_bytes, final_filename)
        
    Raises:
        FileNotFoundError: If file doesn't exist
        FileTooLargeError: If file exceeds size limit
        InvalidPathError: If path or filename is invalid
        FileUtilsError: For other file operation errors
    """
    # For local file operations, we can use the sync version
    # In the future, you might want to use aiofiles for truly async I/O:
    # async with aiofiles.open(path, 'rb') as f:
    #     content = await f.read()
    
    return get_file_content_sync(source, max_size_mb, filename)


def get_file_info(source: str) -> dict:
    """
    Get information about a file without reading its content
    
    Args:
        source: Local file path
        
    Returns:
        Dictionary with file information
        
    Raises:
        FileNotFoundError: If file doesn't exist
        InvalidPathError: If path is invalid
    """
    try:
        path = _validate_file_path(source)
        
        if not path.exists():
            raise FileNotFoundError(f"Local file not found: {source}")
        
        if not path.is_file():
            raise InvalidPathError(f"Path is not a file: {source}")
        
        stat = path.stat()
        
        return {
            'path': str(path),
            'name': path.name,
            'size': stat.st_size,
            'size_mb': stat.st_size / BYTES_PER_MB,
            'modified': stat.st_mtime,
            'created': stat.st_ctime,
            'is_file': path.is_file(),
            'is_dir': path.is_dir(),
            'suffix': path.suffix,
            'stem': path.stem
        }
        
    except (FileNotFoundError, InvalidPathError):
        raise
    except Exception as e:
        logger.error(f"Error getting file info for {source}: {e}")
        raise FileUtilsError(f"Failed to get file info: {e}")


# Utility constants for external use
__all__ = [
    'get_file_content',
    'get_file_content_sync', 
    'get_file_info',
    'FileUtilsError',
    'FileNotFoundError',
    'FileTooLargeError',
    'InvalidPathError',
    'DEFAULT_MAX_FILE_SIZE_MB',
    'MAX_FILENAME_LENGTH'
]