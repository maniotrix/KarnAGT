#!/usr/bin/env python3
"""
Script to check and clean up Qdrant collections created during testing.
"""

import os
import sys
import asyncio
import logging
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(backend_dir)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from qdrant_client import AsyncQdrantClient
from app.services.knowledge.config import get_default_qdrant_config


class QdrantCollectionChecker:
    """Utility to check and clean up Qdrant collections."""
    
    def __init__(self, qdrant_url: Optional[str] = None):
        self.qdrant_config = get_default_qdrant_config()
        self.qdrant_url = qdrant_url or self.qdrant_config.url
        print(f"🔍 Connecting to Qdrant at: {self.qdrant_url}")
    
    async def list_all_collections(self) -> List[str]:
        """List all collections in Qdrant."""
        
        print("📋 Listing all collections in Qdrant...")
        
        try:
            aclient = AsyncQdrantClient(url=self.qdrant_url)
            collections = await aclient.get_collections()
            
            collection_names = [col.name for col in collections.collections]
            
            print(f"📊 Found {len(collection_names)} collections:")
            if collection_names:
                for i, name in enumerate(collection_names, 1):
                    print(f"   {i}. {name}")
            else:
                print("   (No collections found)")
            
            return collection_names
            
        except Exception as e:
            print(f"❌ Error listing collections: {e}")
            return []
    
    async def find_test_collections(self) -> List[str]:
        """Find collections that look like test collections."""
        
        all_collections = await self.list_all_collections()
        
        test_patterns = [
            "test_prod_rag_",
            "user_docs_collection", 
            "business_docs_collection",
            "test_rag_service_",
            "test_collection",
            "user_",  # Generic user pattern
        ]
        
        test_collections = []
        
        for collection in all_collections:
            for pattern in test_patterns:
                if pattern in collection:
                    test_collections.append(collection)
                    break
        
        print(f"\n🔍 Found {len(test_collections)} test collections:")
        if test_collections:
            for i, name in enumerate(test_collections, 1):
                print(f"   {i}. {name}")
        else:
            print("   (No test collections found)")
        
        return test_collections
    
    async def get_collection_info(self, collection_name: str) -> dict:
        """Get detailed information about a collection."""
        
        try:
            aclient = AsyncQdrantClient(url=self.qdrant_url)
            info = await aclient.get_collection(collection_name)
            
            # Extract vector config safely
            vector_config = {"vector_size": "unknown", "distance": "unknown"}
            try:
                # Try to extract vector config with proper error handling
                vectors = getattr(info.config.params, 'vectors', None)
                if vectors:
                    vector_config["vector_size"] = getattr(vectors, 'size', 'unknown')
                    distance = getattr(vectors, 'distance', None)
                    if distance:
                        vector_config["distance"] = str(distance)
            except Exception:
                # Use default values if extraction fails
                pass
            
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "status": info.status,
                "config": vector_config
            }
            
        except Exception as e:
            return {
                "name": collection_name,
                "error": str(e)
            }
    
    async def show_collection_details(self, collection_names: List[str]):
        """Show detailed information about collections."""
        
        print(f"\n📊 Collection Details:")
        print("-" * 80)
        
        for collection_name in collection_names:
            info = await self.get_collection_info(collection_name)
            
            print(f"\n📁 {collection_name}:")
            
            if "error" in info:
                print(f"   ❌ Error: {info['error']}")
            else:
                print(f"   📊 Points: {info['points_count']}")
                print(f"   🔢 Vectors: {info['vectors_count']}")
                print(f"   🏷️  Status: {info['status']}")
                print(f"   📐 Vector Size: {info['config']['vector_size']}")
                print(f"   📏 Distance: {info['config']['distance']}")
    
    async def delete_collection(self, collection_name: str, force: bool = False) -> bool:
        """Delete a specific collection."""
        
        if not force:
            response = input(f"🗑️  Delete collection '{collection_name}'? (y/N): ")
            if response.lower() != 'y':
                print("   ⏭️  Skipped")
                return False
        
        try:
            aclient = AsyncQdrantClient(url=self.qdrant_url)
            await aclient.delete_collection(collection_name)
            print(f"   ✅ Deleted: {collection_name}")
            return True
            
        except Exception as e:
            print(f"   ❌ Error deleting {collection_name}: {e}")
            return False
    
    async def cleanup_test_collections(self, force: bool = False):
        """Clean up all test collections."""
        
        test_collections = await self.find_test_collections()
        
        if not test_collections:
            print("✅ No test collections found to clean up")
            return
        
        print(f"\n🧹 Cleaning up {len(test_collections)} test collections...")
        
        if not force:
            response = input(f"🚨 Delete ALL {len(test_collections)} test collections? (y/N): ")
            if response.lower() != 'y':
                print("⏭️  Cleanup cancelled")
                return
        
        deleted_count = 0
        
        for collection_name in test_collections:
            success = await self.delete_collection(collection_name, force=True)
            if success:
                deleted_count += 1
        
        print(f"\n✅ Cleanup complete: {deleted_count}/{len(test_collections)} collections deleted")
    
    async def run_interactive_cleanup(self):
        """Run interactive cleanup process."""
        
        print("🔍 Qdrant Collection Cleanup Tool")
        print("=" * 50)
        
        while True:
            print("\n📋 Options:")
            print("1. List all collections")
            print("2. Find test collections")
            print("3. Show collection details")
            print("4. Delete specific collection")
            print("5. Cleanup all test collections")
            print("0. Exit")
            
            choice = input("\n🎯 Select option: ").strip()
            
            if choice == "1":
                await self.list_all_collections()
                
            elif choice == "2":
                await self.find_test_collections()
                
            elif choice == "3":
                collections = await self.find_test_collections()
                if collections:
                    await self.show_collection_details(collections)
                
            elif choice == "4":
                collection_name = input("Collection name to delete: ").strip()
                if collection_name:
                    await self.delete_collection(collection_name)
                
            elif choice == "5":
                await self.cleanup_test_collections()
                
            elif choice == "0":
                print("👋 Goodbye!")
                break
                
            else:
                print("❌ Invalid option")


async def main():
    """Main function."""
    
    checker = QdrantCollectionChecker()
    
    # Check if we have command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--cleanup":
            await checker.cleanup_test_collections(force=False)
        elif sys.argv[1] == "--force-cleanup":
            await checker.cleanup_test_collections(force=True)
        elif sys.argv[1] == "--list":
            await checker.list_all_collections()
        elif sys.argv[1] == "--test":
            await checker.find_test_collections()
        else:
            print("Usage:")
            print("  python check_qdrant_collections.py              # Interactive mode")
            print("  python check_qdrant_collections.py --list       # List all collections")
            print("  python check_qdrant_collections.py --test       # Find test collections")
            print("  python check_qdrant_collections.py --cleanup    # Clean up test collections")
            print("  python check_qdrant_collections.py --force-cleanup  # Force cleanup without prompts")
    else:
        # Interactive mode
        await checker.run_interactive_cleanup()


if __name__ == "__main__":
    asyncio.run(main()) 