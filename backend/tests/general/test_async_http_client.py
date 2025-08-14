#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Demo/Test script for the new AsyncHTTPClient utility
Shows how to use the improved async HTTP client for file downloads
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from app.utils.async_http_client import AsyncHTTPClient, download_file, get_file_info, HTTPClientError
from app.logging.logger import get_logger

logger = get_logger(__name__)

async def demo_async_http_client():
    """Demonstrate the AsyncHTTPClient functionality"""
    
    print("🚀 AsyncHTTPClient Demo")
    print("=" * 50)
    
    max_size_mb = 5
    
    # Test URLs (these should be publicly accessible files)
    test_urls = [
        "https://microsoftedge.github.io/Demos/json-dummy-data/5MB.json",  # Small 5mb JSON file
        "https://github.com/orangetw/Tiny-URL-Fuzzer/blob/master/samples.txt",  # Small text file
    ]
    
    # Demo 1: Using context manager
    print("\n📦 Demo 1: Using AsyncHTTPClient with context manager")
    async with AsyncHTTPClient(timeout=30) as client:
        for url in test_urls:
            try:
                print(f"\n⬇️  Downloading: {url}")
                content, filename = await client.download_file(url, max_size_mb=max_size_mb)
                print(f"✅ Success: {filename} ({len(content)} bytes)")
                
                # Show first 100 chars of content
                content_preview = content.decode('utf-8', errors='ignore')[:100]
                print(f"📄 Preview: {content_preview}...")
                
            except Exception as e:
                print(f"❌ Failed: {e}")
    
    # Demo 2: Using convenience function
    print("\n📦 Demo 2: Using convenience download_file() function")
    try:
        url = test_urls[0]
        print(f"⬇️  Downloading: {url}")
        content, filename = await download_file(url, max_size_mb=max_size_mb)
        print(f"✅ Success: {filename} ({len(content)} bytes)")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Demo 3: Getting file info without downloading
    print("\n📦 Demo 3: Getting file info with HEAD request")
    try:
        url = test_urls[0]
        print(f"ℹ️  Getting info for: {url}")
        info = await get_file_info(url)
        print(f"✅ File info:")
        for key, value in info.items():
            print(f"   {key}: {value}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Demo 4: Error handling - file too large
    print("\n📦 Demo 4: Error handling - size limit")
    try:
        url = test_urls[0]
        print(f"⬇️  Downloading with tiny size limit: {url}")
        content, filename = await download_file(url, max_size_mb=1)  # Small limit for demo
        print(f"❌ Success, but should fail: {filename} ({len(content)} bytes)")
    except Exception as e:
        print(f"✅ Expected error: {e} - ❌")
    
    # Demo 5: Error handling - invalid URL
    print("\n📦 Demo 5: Error handling - invalid URL")
    try:
        url = "https://this-domain-does-not-exist-12345.com/file.txt"
        print(f"⬇️  Downloading from invalid URL: {url}")
        content, filename = await download_file(url, timeout=5)
        print(f"❌ Success, but should fail: {filename} ({len(content)} bytes)")
    except Exception as e:
        print(f"✅ Expected error: {e} - ❌")
    
    print("\n🎉 Demo completed!")

if __name__ == "__main__":
    try:
        # Run the demo
        asyncio.run(demo_async_http_client())
        
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n💥 Demo failed: {e}")
        logger.exception("Demo failed with exception")