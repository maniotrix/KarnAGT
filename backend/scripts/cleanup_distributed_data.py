#!/usr/bin/env python3
"""
Cleanup Distributed Data Script

This script manually deletes all worker, stream, and conversation lock data from Redis.
Useful for testing, debugging, and system maintenance.

Usage:
    python scripts/cleanup_distributed_data.py [--force] [--workers-only] [--streams-only] [--locks-only]

Options:
    --force         Skip confirmation prompts
    --workers-only  Delete only worker registry data
    --streams-only  Delete only stream data
    --locks-only    Delete only conversation lock data
    --dry-run       Show what would be deleted without actually deleting
"""

import os
import sys
import argparse
import asyncio
from typing import List, Set
from datetime import datetime

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import redis.asyncio as redis
from app.core.config import settings


class DistributedDataCleanup:
    """Cleanup utility for distributed streaming data"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.redis_client = None
        self.deleted_count = {
            'workers': 0,
            'streams': 0, 
            'user_streams': 0,
            'worker_metadata': 0,
            'conversation_locks': 0
        }
    
    async def connect_redis(self):
        """Connect to Redis"""
        try:
            redis_url = settings.REDIS_URL or "redis://localhost:6379"
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            
            # Test connection
            await self.redis_client.ping()
            print(f"✅ Connected to Redis: {redis_url}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to Redis: {e}")
            return False
    
    async def get_worker_keys(self) -> List[str]:
        """Get all worker-related keys"""
        keys = []
        
        # Get all worker metadata keys
        worker_keys = await self.redis_client.keys("worker:*")
        keys.extend(worker_keys)
        
        # Add worker registry key
        if await self.redis_client.exists("workers:active"):
            keys.append("workers:active")
        
        return keys
    
    async def get_stream_keys(self) -> List[str]:
        """Get all stream-related keys"""
        keys = []
        
        # Get all stream metadata keys
        stream_keys = await self.redis_client.keys("stream:*")
        keys.extend(stream_keys)
        
        # Get all user stream keys
        user_stream_keys = await self.redis_client.keys("user:*:streams")
        keys.extend(user_stream_keys)
        
        return keys
    
    async def get_conversation_lock_keys(self) -> List[str]:
        """Get all conversation lock keys"""
        keys = []
        
        # Get all conversation lock keys
        conv_lock_keys = await self.redis_client.keys("conv_lock:*")
        keys.extend(conv_lock_keys)
        
        return keys
    
    async def analyze_data(self) -> dict:
        """Analyze current distributed data"""
        analysis = {
            'active_workers': [],
            'worker_metadata_count': 0,
            'active_streams': [],
            'user_streams_count': 0,
            'conversation_locks': [],
            'total_keys': 0
        }
        
        try:
            # Get active workers
            active_workers = await self.redis_client.smembers("workers:active")
            analysis['active_workers'] = list(active_workers) if active_workers else []
            
            # Count worker metadata
            worker_keys = await self.redis_client.keys("worker:*")
            analysis['worker_metadata_count'] = len(worker_keys)
            
            # Get stream keys
            stream_keys = await self.redis_client.keys("stream:*")
            analysis['active_streams'] = [key.replace('stream:', '') for key in stream_keys]
            
            # Count user stream keys
            user_stream_keys = await self.redis_client.keys("user:*:streams")
            analysis['user_streams_count'] = len(user_stream_keys)
            
            # Get conversation locks
            conv_lock_keys = await self.redis_client.keys("conv_lock:*")
            analysis['conversation_locks'] = [key.replace('conv_lock:', '') for key in conv_lock_keys]
            
            # Total keys
            all_keys = await self.get_worker_keys() + await self.get_stream_keys() + await self.get_conversation_lock_keys()
            analysis['total_keys'] = len(set(all_keys))  # Remove duplicates
            
        except Exception as e:
            print(f"⚠️ Error analyzing data: {e}")
        
        return analysis
    
    async def cleanup_workers(self) -> bool:
        """Delete all worker data"""
        try:
            worker_keys = await self.get_worker_keys()
            
            if not worker_keys:
                print("🔍 No worker data found")
                return True
            
            print(f"🗑️ {'[DRY RUN] Would delete' if self.dry_run else 'Deleting'} {len(worker_keys)} worker keys...")
            
            for key in worker_keys:
                if not self.dry_run:
                    await self.redis_client.delete(key)
                print(f"  {'[DRY RUN] Would delete' if self.dry_run else 'Deleted'}: {key}")
                
                if key == "workers:active":
                    self.deleted_count['workers'] += 1
                else:
                    self.deleted_count['worker_metadata'] += 1
            
            return True
            
        except Exception as e:
            print(f"❌ Error cleaning worker data: {e}")
            return False
    
    async def cleanup_streams(self) -> bool:
        """Delete all stream data"""
        try:
            stream_keys = await self.get_stream_keys()
            
            if not stream_keys:
                print("🔍 No stream data found")
                return True
            
            print(f"🗑️ {'[DRY RUN] Would delete' if self.dry_run else 'Deleting'} {len(stream_keys)} stream keys...")
            
            for key in stream_keys:
                if not self.dry_run:
                    await self.redis_client.delete(key)
                print(f"  {'[DRY RUN] Would delete' if self.dry_run else 'Deleted'}: {key}")
                
                if key.startswith("stream:"):
                    self.deleted_count['streams'] += 1
                elif key.startswith("user:") and key.endswith(":streams"):
                    self.deleted_count['user_streams'] += 1
            
            return True
            
        except Exception as e:
            print(f"❌ Error cleaning stream data: {e}")
            return False
    
    async def cleanup_conversation_locks(self) -> bool:
        """Delete all conversation lock data"""
        try:
            conv_lock_keys = await self.get_conversation_lock_keys()
            
            if not conv_lock_keys:
                print("🔍 No conversation lock data found")
                return True
            
            print(f"🗑️ {'[DRY RUN] Would delete' if self.dry_run else 'Deleting'} {len(conv_lock_keys)} conversation lock keys...")
            
            for key in conv_lock_keys:
                if not self.dry_run:
                    await self.redis_client.delete(key)
                print(f"  {'[DRY RUN] Would delete' if self.dry_run else 'Deleted'}: {key}")
                self.deleted_count['conversation_locks'] += 1
            
            return True
            
        except Exception as e:
            print(f"❌ Error cleaning conversation lock data: {e}")
            return False
    
    async def cleanup_all(self) -> bool:
        """Delete all distributed data"""
        success = True
        success &= await self.cleanup_workers()
        success &= await self.cleanup_streams()
        success &= await self.cleanup_conversation_locks()
        return success
    
    def print_analysis(self, analysis: dict):
        """Print data analysis"""
        print("\n📊 DISTRIBUTED DATA ANALYSIS")
        print("=" * 50)
        print(f"🏭 Active Workers: {len(analysis['active_workers'])}")
        for worker in analysis['active_workers']:
            print(f"   • {worker}")
        
        print(f"📦 Worker Metadata Keys: {analysis['worker_metadata_count']}")
        print(f"🌊 Active Streams: {len(analysis['active_streams'])}")
        for stream_id in analysis['active_streams'][:5]:  # Show first 5
            print(f"   • {stream_id}")
        if len(analysis['active_streams']) > 5:
            print(f"   • ... and {len(analysis['active_streams']) - 5} more")
        
        print(f"👥 User Stream Keys: {analysis['user_streams_count']}")
        print(f"🔒 Active Conversation Locks: {len(analysis['conversation_locks'])}")
        for conv_id in analysis['conversation_locks'][:3]:  # Show first 3
            print(f"   • {conv_id}")
        if len(analysis['conversation_locks']) > 3:
            print(f"   • ... and {len(analysis['conversation_locks']) - 3} more")
        
        print(f"🔑 Total Keys to Delete: {analysis['total_keys']}")
        print()
    
    def print_summary(self):
        """Print cleanup summary"""
        print("\n📊 CLEANUP SUMMARY")
        print("=" * 30)
        print(f"🏭 Workers Registry: {self.deleted_count['workers']}")
        print(f"📦 Worker Metadata: {self.deleted_count['worker_metadata']}")
        print(f"🌊 Stream Data: {self.deleted_count['streams']}")
        print(f"👥 User Streams: {self.deleted_count['user_streams']}")
        print(f"🔒 Conversation Locks: {self.deleted_count['conversation_locks']}")
        
        total = sum(self.deleted_count.values())
        print(f"🎯 Total Deleted: {total} keys")
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            try:
                await self.redis_client.aclose()  # type: ignore
            except AttributeError:
                # Fallback for older redis versions
                await self.redis_client.close()  # type: ignore


async def main():
    parser = argparse.ArgumentParser(description="Cleanup distributed streaming data from Redis")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompts")
    parser.add_argument("--workers-only", action="store_true", help="Delete only worker data")
    parser.add_argument("--streams-only", action="store_true", help="Delete only stream data")
    parser.add_argument("--locks-only", action="store_true", help="Delete only conversation lock data")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without deleting")
    
    args = parser.parse_args()
    
    print("🚀 DISTRIBUTED DATA CLEANUP UTILITY")
    print("=" * 50)
    print(f"🕒 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No data will be deleted")
    
    cleanup = DistributedDataCleanup(dry_run=args.dry_run)
    
    try:
        # Connect to Redis
        if not await cleanup.connect_redis():
            return 1
        
        # Analyze current data
        analysis = await cleanup.analyze_data()
        cleanup.print_analysis(analysis)
        
        if analysis['total_keys'] == 0:
            print("✅ No distributed data found. Nothing to cleanup.")
            return 0
        
        # Confirmation prompt
        if not args.force and not args.dry_run:
            print("⚠️  This will permanently delete all distributed streaming data!")
            response = input("Are you sure you want to continue? (yes/no): ").strip().lower()
            if response != 'yes':
                print("❌ Operation cancelled.")
                return 1
        
        # Perform cleanup
        success = False
        
        if args.workers_only:
            print("\n🏭 Cleaning worker data only...")
            success = await cleanup.cleanup_workers()
        elif args.streams_only:
            print("\n🌊 Cleaning stream data only...")
            success = await cleanup.cleanup_streams()
        elif args.locks_only:
            print("\n🔒 Cleaning conversation locks only...")
            success = await cleanup.cleanup_conversation_locks()
        else:
            print("\n🗑️ Cleaning all distributed data...")
            success = await cleanup.cleanup_all()
        
        # Print summary
        cleanup.print_summary()
        
        if success:
            print(f"\n✅ Cleanup {'simulation' if args.dry_run else 'completed'} successfully!")
            return 0
        else:
            print(f"\n❌ Cleanup {'simulation' if args.dry_run else 'completed'} with errors!")
            return 1
        
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user.")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1
    finally:
        await cleanup.close()


if __name__ == "__main__":
    exit(asyncio.run(main()))
