#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cleanup Generated Files Script

Simple script to delete all generated files from S3/MinIO storage.
Run this after tests to clean up any persisted files.

Usage:
    python scripts/cleanup_generated_files.py
    python scripts/cleanup_generated_files.py --dry-run
    python scripts/cleanup_generated_files.py --prefix generated/2025/01/08
"""

import sys
import os
import asyncio
import argparse
from datetime import datetime

# Add backend to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)


from app.services.storage.storage import S3StorageBackend
from app.core.config import settings


async def cleanup_generated_files(prefix: str = "generated/", dry_run: bool = False):
    """
    Delete all generated files from S3/MinIO storage.
    
    Args:
        prefix: S3 prefix to delete (default: "generated/" for all generated files)
        dry_run: If True, only list files that would be deleted without actually deleting
    """
    print(f"🧹 Generated Files Cleanup Script")
    print(f"Bucket: {settings.S3_BUCKET_NAME}")
    print(f"Endpoint: {settings.S3_ENDPOINT_URL}")
    print(f"Prefix: {prefix}")
    print(f"Mode: {'DRY RUN' if dry_run else 'DELETE'}")
    print("-" * 50)
    
    # Initialize S3 storage backend
    try:
        storage_backend = S3StorageBackend()
        print("✅ Connected to S3 storage backend")
    except Exception as e:
        print(f"❌ Failed to connect to S3: {e}")
        return
    
    try:
        # List all objects with the specified prefix
        print(f"📋 Listing objects with prefix '{prefix}'...")
        
        objects_to_delete = []
        total_size = 0
        
        # Use boto3 client directly to list objects
        paginator = storage_backend.s3_client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(
            Bucket=settings.S3_BUCKET_NAME,
            Prefix=prefix
        )
        
        for page in page_iterator:
            if 'Contents' not in page:
                continue
                
            for obj in page['Contents']:
                key = obj['Key']
                size = obj['Size']
                modified = obj['LastModified']
                
                objects_to_delete.append({
                    'Key': key,
                    'Size': size,
                    'LastModified': modified
                })
                total_size += size
                
                print(f"  📄 {key} ({size:,} bytes, modified: {modified})")
        
        if not objects_to_delete:
            print(f"✅ No files found with prefix '{prefix}'")
            return
        
        print("-" * 50)
        print(f"📊 Summary:")
        print(f"   Files found: {len(objects_to_delete):,}")
        print(f"   Total size: {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)")
        
        if dry_run:
            print("🔍 DRY RUN: No files were deleted")
            return
        
        # Confirm deletion
        print(f"\n⚠️  WARNING: This will permanently delete {len(objects_to_delete)} files!")
        response = input("Are you sure you want to continue? (yes/N): ").strip().lower()
        
        if response != 'yes':
            print("❌ Cancelled by user")
            return
        
        # Delete files in batches (S3 allows max 1000 objects per delete request)
        print(f"🗑️  Deleting files...")
        deleted_count = 0
        batch_size = 1000
        
        for i in range(0, len(objects_to_delete), batch_size):
            batch = objects_to_delete[i:i + batch_size]
            
            # Prepare delete request
            delete_objects = [{'Key': obj['Key']} for obj in batch]
            
            try:
                response = storage_backend.s3_client.delete_objects(
                    Bucket=settings.S3_BUCKET_NAME,
                    Delete={'Objects': delete_objects}
                )
                
                # Count successfully deleted objects
                deleted_batch = len(response.get('Deleted', []))
                deleted_count += deleted_batch
                
                print(f"   ✅ Deleted batch {i//batch_size + 1}: {deleted_batch} files")
                
                # Report any errors
                if 'Errors' in response and response['Errors']:
                    for error in response['Errors']:
                        print(f"   ❌ Error deleting {error['Key']}: {error['Message']}")
                        
            except Exception as e:
                print(f"   ❌ Error deleting batch {i//batch_size + 1}: {e}")
                continue
        
        print("-" * 50)
        print(f"✅ Cleanup completed!")
        print(f"   Files deleted: {deleted_count:,} / {len(objects_to_delete):,}")
        print(f"   Storage freed: ~{total_size / 1024 / 1024:.2f} MB")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        raise


def main():
    """Main entry point for the cleanup script"""
    parser = argparse.ArgumentParser(
        description="Delete generated files from S3/MinIO storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Delete all generated files
  python scripts/cleanup_generated_files.py

  # Dry run to see what would be deleted
  python scripts/cleanup_generated_files.py --dry-run

  # Delete files from specific date
  python scripts/cleanup_generated_files.py --prefix generated/2025/01/08

  # Delete test files only
  python scripts/cleanup_generated_files.py --prefix test-generated/
        """
    )
    
    parser.add_argument(
        '--prefix',
        default='generated/',
        help='S3 prefix to delete (default: generated/)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='List files that would be deleted without actually deleting them'
    )
    
    args = parser.parse_args()
    
    # Run the async cleanup function
    try:
        asyncio.run(cleanup_generated_files(
            prefix=args.prefix,
            dry_run=args.dry_run
        ))
    except KeyboardInterrupt:
        print("\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()