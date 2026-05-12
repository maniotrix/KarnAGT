#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
HTTP Client Utility

General-purpose async HTTP client using aiohttp for file downloads and other HTTP operations.
Provides consistent error handling, timeouts, and retry logic.
"""

import asyncio
import aiohttp
from typing import Optional, Dict, Any
from pathlib import Path
from urllib.parse import urlparse, unquote
from app.logging.logger import get_logger

logger = get_logger(__name__)

class HTTPClientError(Exception):
    """Base exception for HTTP client errors"""
    pass

class DownloadError(HTTPClientError):
    """Exception raised when file download fails"""
    pass

class FileTooLargeError(HTTPClientError):
    """Exception raised when file exceeds size limit"""
    pass

class AsyncHTTPClient:
    """
    General-purpose async HTTP client for file downloads and other HTTP operations.
    Follows patterns from SandboxClient for consistency.
    Supports retry logic, timeout handling, and size limits.
    """
    
    def __init__(self, timeout: int = 60, max_retries: int = 3):
        """
        Initialize HTTP client
        
        Args:
            timeout: Default timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure aiohttp session is created"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def close(self):
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    def _extract_filename_from_url(self, url: str, response: aiohttp.ClientResponse) -> str:
        """
        Extract filename from URL or response headers
        
        Args:
            url: The download URL
            response: HTTP response object
            
        Returns:
            Extracted filename or fallback name
        """
        # Try Content-Disposition header first
        content_disposition = response.headers.get('Content-Disposition', '')
        if 'filename=' in content_disposition:
            try:
                filename = content_disposition.split('filename=')[1].strip('"\'')
                if filename:
                    return filename
            except (IndexError, AttributeError):
                pass
        
        # Fall back to URL path
        parsed_url = urlparse(url)
        path = unquote(parsed_url.path)
        filename = Path(path).name
        
        # Remove query parameters
        if '?' in filename:
            filename = filename.split('?')[0]
            
        return filename or 'downloaded_file'
    
    async def download_file(
        self,
        url: str,
        max_size_mb: int = 100,
        filename: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> tuple[bytes, str]:
        """
        Download a file from URL
        
        Args:
            url: URL to download from
            max_size_mb: Maximum file size in MB
            filename: Optional filename override
            headers: Optional HTTP headers
            
        Returns:
            Tuple of (file_content_bytes, filename)
            
        Raises:
            DownloadError: If download fails
            FileTooLargeError: If file exceeds size limit
            HTTPClientError: For other HTTP errors
        """
        await self._ensure_session()
        assert self.session is not None  # Type checker hint
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Downloading file from {url} (attempt {attempt + 1})")
                
                async with self.session.get(url, headers=headers) as response:
                    # Check status
                    if response.status != 200:
                        raise DownloadError(f"HTTP {response.status}: {await response.text()}")
                    
                    # Check content length if available
                    content_length = response.headers.get('Content-Length')
                    if content_length:
                        size_bytes = int(content_length)
                        max_bytes = max_size_mb * 1024 * 1024
                        if size_bytes > max_bytes:
                            raise FileTooLargeError(
                                f"File too large: {size_bytes} bytes (max: {max_bytes} bytes)"
                            )
                    
                    # Get filename
                    if not filename:
                        filename = self._extract_filename_from_url(url, response)
                    
                    # Read content
                    content = await response.read()
                    
                    # Double-check actual size
                    actual_size = len(content)
                    max_bytes = max_size_mb * 1024 * 1024
                    if actual_size > max_bytes:
                        raise FileTooLargeError(
                            f"File too large: {actual_size} bytes (max: {max_bytes} bytes)"
                        )
                    
                    logger.info(f"Successfully downloaded {filename} ({actual_size} bytes)")
                    return content, filename
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(f"Download attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    raise DownloadError(f"Failed to download after {self.max_retries} attempts: {e}")
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
            
            except (FileTooLargeError, DownloadError):
                # Don't retry these errors
                raise
                
            except Exception as e:
                logger.error(f"Unexpected error during download: {e}")
                raise HTTPClientError(f"Unexpected download error: {e}")
        
        # This should never be reached due to the retry logic, but ensures all paths return
        raise DownloadError("Download failed: maximum retries exceeded")
    

    async def head_request(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make a HEAD request to get file info without downloading
        
        Args:
            url: URL to check
            headers: Optional HTTP headers
            
        Returns:
            Dictionary with content-length, content-type, filename, etc.
            
        Raises:
            HTTPClientError: If request fails
        """
        await self._ensure_session()
        assert self.session is not None  # Type checker hint
        
        try:
            async with self.session.head(url, headers=headers) as response:
                if response.status != 200:
                    raise HTTPClientError(f"HEAD request failed: HTTP {response.status}")
                
                # Convert content-length to int if present
                content_length_str = response.headers.get('Content-Length')
                content_length_value: Optional[int] = None
                if content_length_str:
                    try:
                        content_length_value = int(content_length_str)
                    except ValueError:
                        content_length_value = None
                
                result: Dict[str, Any] = {
                    'content_length': content_length_value,
                    'content_type': response.headers.get('Content-Type'),
                    'last_modified': response.headers.get('Last-Modified'),
                    'filename': self._extract_filename_from_url(url, response)
                }
                
                return result
                
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            raise HTTPClientError(f"HEAD request failed: {e}")
        except Exception as e:
            raise HTTPClientError(f"Unexpected error in HEAD request: {e}")


# Utility functions for one-off operations
async def download_file(
    url: str,
    max_size_mb: int = 100,
    filename: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 60
) -> tuple[bytes, str]:
    """
    Convenience function to download a file without managing client manually
    
    Args:
        url: URL to download from
        max_size_mb: Maximum file size in MB
        filename: Optional filename override
        headers: Optional HTTP headers
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (file_content_bytes, filename)
    """
    async with AsyncHTTPClient(timeout=timeout) as client:
        return await client.download_file(url, max_size_mb, filename, headers)


async def get_file_info(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Convenience function to get file info without downloading
    
    Args:
        url: URL to check
        headers: Optional HTTP headers
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary with file information
    """
    async with AsyncHTTPClient(timeout=timeout) as client:
        return await client.head_request(url, headers)