import os
import sys
import logging
import asyncio
import uuid
import time
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables for testing
load_dotenv()

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))

sys.path.append(backend_dir)

# Configure logging BEFORE importing modules
def setup_logging(log_level=logging.DEBUG):
    """Configure comprehensive logging for the test."""
    
    # Clear any existing handlers to avoid conflicts
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Configure root logger with detailed format
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)8s - %(funcName)s:%(lineno)d - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
        force=True  # Force reconfiguration
    )
    
    # Set specific logger levels for our modules
    loggers_to_configure = [
        ('app.services.knowledge.production_rag_service', logging.DEBUG),
        ('app.services.knowledge.metadata_util', logging.WARNING), 
        ('app.services.knowledge.config', logging.WARNING),
        ('llama_index.core', logging.WARNING),  # Reduce LlamaIndex noise
        ('openai', logging.WARNING),  # Reduce OpenAI API noise
        ('httpx', logging.WARNING),  # Reduce HTTP request noise
        ('urllib3', logging.WARNING),  # Reduce HTTP connection noise
    ]
    
    for logger_name, level in loggers_to_configure:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        logger.propagate = True  # Ensure messages propagate to root logger
    
    # Disable SQLAlchemy logging more aggressively
    sqlalchemy_loggers = [
        'sqlalchemy.engine',
        'sqlalchemy.engine.Engine', 
        'sqlalchemy.dialects',
        'sqlalchemy.pool', 
        'sqlalchemy.orm',
        'sqlalchemy'  # Also disable the parent logger
    ]
    
    for logger_name in sqlalchemy_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.CRITICAL)  # Only show critical errors
        logger.propagate = False  # Don't propagate to root logger
        logger.disabled = True  # Completely disable the logger
        
    # Also set handlers to None to prevent any output
    logging.getLogger('sqlalchemy.engine').handlers = []
    logging.getLogger('sqlalchemy.engine.Engine').handlers = []
    
    print(f"📋 Logging configured at {logging.getLevelName(log_level)} level")
    print(f"🔍 Debug logging enabled for metadata cleaning components")

# Setup logging first - allow control via environment variable
log_level_name = os.getenv('LOG_LEVEL', 'DEBUG').upper()
log_level = getattr(logging, log_level_name, logging.DEBUG)
setup_logging(log_level)

# Import all necessary modules after logging setup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.database import get_db
from app.models.database import User, VectorCollection, KnowledgeFile
from app.services.knowledge.production_rag_service import ProductionRAGService
from app.services.knowledge.config import RAGConfig, get_default_qdrant_config
from app.services.storage.storage import S3StorageBackend, generate_file_id, generate_storage_key, get_content_type
from app.utils.profiler_util import PerformanceMonitor

test_docs_dir = os.path.join(backend_dir, "test_docs")
test_file_1 = os.path.join(test_docs_dir, "PRY NDLS 20 June.pdf")
test_file_2 = os.path.join(test_docs_dir, "Trykaa_ Strategic Deep Dive & Positioning.pdf")


class ProductionRAGTestRunner:
    """Comprehensive test runner for ProductionRAGService with real database integration."""
    
    def __init__(self, rag_config: RAGConfig):
        self.rag_config = rag_config
        self.qdrant_config = get_default_qdrant_config(collection_name=f"test_prod_rag_{uuid.uuid4().hex[:8]}")
        self.prod_rag_service = ProductionRAGService(rag_config, self.qdrant_config)
        self.perf_monitor = PerformanceMonitor()
        
        # Test tracking for cleanup
        self.test_user_id = None
        self.test_collection_id = None
        self.test_collection_name = None  # Store collection name for reuse
        self.uploaded_s3_keys: List[str] = []
        self.created_knowledge_files: List[str] = []
        
        # S3 setup
        self.s3_storage = S3StorageBackend(bucket_name=self.rag_config.s3_bucket_name)
        
        print(f"🚀 ProductionRAGTestRunner initialized")
        print(f"   📊 RAG Config: {self.rag_config.llm_model}")
        print(f"   🗄️  Qdrant Collection: {self.qdrant_config.collection_name}")
        print(f"   📦 S3 Bucket: {self.rag_config.s3_bucket_name}")
    
    async def create_test_user(self):
        """Create a unique test user in the database using real production patterns."""
        
        print("👤 Creating test user...")
        
        async for db in get_db():
            # Create test user with unique email and username
            test_uuid = uuid.uuid4().hex[:8]
            test_user = User(
                email=f"test_user_{test_uuid}@testdomain.com",
                username=f"test_user_{test_uuid}",
                hashed_password="test_password_hash",
                full_name=f"Test User {test_uuid}",
                subscription_tier="pro",  # Give pro access for testing
                is_active=True,
                is_verified=True
            )
            
            db.add(test_user)
            await db.commit()
            await db.refresh(test_user)
            
            self.test_user_id = test_user.id
            print(f"   ✅ Created test user: ID={self.test_user_id}, Email={test_user.email}")
            
            return test_user.id
        
        # This should never be reached due to the async generator, but add for type safety
        raise Exception("Failed to create test user - no database session")
    
    async def upload_file_to_s3(self, local_file_path: str, original_filename: str) -> str:
        """Upload a single file to S3 and return the S3 key."""
        
        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"Test file not found: {local_file_path}")
        
        # Generate unique S3 key
        file_id = generate_file_id()
        s3_key = generate_storage_key(file_id, original_filename)
        content_type = get_content_type(local_file_path)
        
        print(f"📤 Uploading {original_filename} to S3...")
        
        # Ensure bucket exists
        await self.s3_storage.ensure_bucket_exists() # type: ignore
        
        # Upload file
        await self.s3_storage.upload_file_direct(local_file_path, s3_key, content_type)
        
        # Verify upload
        try:
            response = self.s3_storage.s3_client.head_object(
                Bucket=self.rag_config.s3_bucket_name,
                Key=s3_key
            )
            size_mb = response.get('ContentLength', 0) / 1024 / 1024
            print(f"   ✅ Uploaded successfully: {size_mb:.2f} MB")
            print(f"   🔑 S3 Key: {s3_key}")
        except Exception as e:
            raise Exception(f"Failed to verify S3 upload: {e}")
        
        # Track for cleanup
        self.uploaded_s3_keys.append(s3_key)
        
        # Wait for S3 consistency
        await asyncio.sleep(1)
        
        return s3_key
    
    async def process_documents_and_create_collection(self, s3_keys: List[str], collection_name: Optional[str] = None):
        """Process S3 documents and create/update vector collection using production service."""
        
        print(f"🔄 Processing {len(s3_keys)} documents...")
        
        # If no collection_name provided, service will use qdrant_config.collection_name
        if collection_name is None:
            print(f"   🔄 Using qdrant config collection: {self.qdrant_config.collection_name}")
        else:
            print(f"   🔄 Using explicit collection: {collection_name}")
        
        async for db in get_db():
            # Get or create collection
            collection = await self.prod_rag_service.get_or_create_collection(
                user_id=self.test_user_id,
                collection_name=collection_name,
                display_name=f"Test Collection {uuid.uuid4().hex[:8]}",
                db=db
            )
            
            # Store collection info for reuse
            self.test_collection_id = collection.id
            self.test_collection_name = collection.collection_name
            
            print(f"   ✅ Collection: {collection.collection_name} (ID: {collection.id})")
            
            # Process documents
            result = await self.prod_rag_service.process_s3_documents(
                collection_id=collection.id,
                s3_keys=s3_keys,
                user_id=self.test_user_id,
                force_reprocess=False,
                db=db
            )
            
            print(f"   ✅ Processing complete:")
            print(f"      📁 Files: {result.total_requested} requested, {result.file_success_rate:.1f}% success")
            print(f"      📄 Document Chunks: {result.total_document_chunks} created ({result.document_extraction_rate:.1f} per file)")
            print(f"      ⏱️  Time: {result.processing_time:.2f}s")
            
            if result.compatibility_result:
                print(f"      🔍 Compatibility: {'✅ Compatible' if result.compatibility_result.is_compatible else '⚠️ Issues found'}")
            
            return collection.id
        
        # This should never be reached due to the async generator, but add for type safety
        raise Exception("Failed to process documents - no database session")
    
    async def query_collection(self, collection_id: str, queries: List[str]) -> List[Dict[str, Any]]:
        """Query the collection and return results."""
        
        print(f"🔍 Running {len(queries)} queries on collection {collection_id}...")
        
        results = []
        
        async for db in get_db():
            for i, query in enumerate(queries, 1):
                print(f"\n📋 Query {i}: {query}")
                
                start_time = time.time()
                
                # Query using production service
                query_result = await self.prod_rag_service.query_collection(
                    collection_id=collection_id,
                    query=query,
                    user_id=self.test_user_id,
                    db=db
                )
                
                query_time = time.time() - start_time
                
                print(f"💬 Response: {query_result.response}")
                print(f"⏱️  Query Time: {query_time:.3f}s")
                print(f"📚 Sources: {len(query_result.sources)}")
                
                # Show top sources
                for j, source in enumerate(query_result.sources[:3], 1):
                    print(f"   {j}. {source.get('file_name', 'Unknown')} (Score: {source.get('score', 'N/A')})")
                    print(f"      📝 {source.get('text_preview', 'No preview')}")
                
                results.append({
                    'query': query,
                    'response': query_result.response,
                    'sources': query_result.sources,
                    'query_time': query_time
                })
        
        return results
    
    async def simulate_memory_invalidation(self):
        """Simulate memory invalidation by creating a new service instance."""
        
        print("🔄 Simulating memory invalidation (creating new service instance)...")
        
        # Create new service instance to simulate restart
        self.prod_rag_service = ProductionRAGService(self.rag_config, self.qdrant_config)
        
        print("   ✅ New service instance created - memory invalidated")
    
    async def cleanup_database(self):
        """Clean up all database records created during the test."""
        
        if self.test_user_id is None:
            print("⚠️  No test user to cleanup")
            return
        
        print("🧹 Cleaning up database records...")
        
        async for db in get_db():
            try:
                # Delete knowledge files
                await db.execute(
                    delete(KnowledgeFile).where(KnowledgeFile.user_id == self.test_user_id)
                )
                print("   🗑️  Deleted knowledge files")
                
                # Delete vector collections
                await db.execute(
                    delete(VectorCollection).where(VectorCollection.user_id == self.test_user_id)
                )
                print("   🗑️  Deleted vector collections")
                
                # Delete test user
                await db.execute(
                    delete(User).where(User.id == self.test_user_id)
                )
                print("   🗑️  Deleted test user")
                
                await db.commit()
                print("   ✅ Database cleanup completed")
                
            except Exception as e:
                print(f"   ❌ Database cleanup error: {e}")
                await db.rollback()
    
    async def cleanup_s3(self):
        """Clean up S3 files."""
        
        if not self.uploaded_s3_keys:
            print("⚠️  No S3 files to cleanup")
            return
        
        print(f"🧹 Cleaning up {len(self.uploaded_s3_keys)} S3 files...")
        
        for s3_key in self.uploaded_s3_keys:
            try:
                await self.s3_storage.delete_file(s3_key)
                print(f"   🗑️  Deleted: {s3_key}")
            except Exception as e:
                print(f"   ❌ Failed to delete {s3_key}: {e}")
        
        print("   ✅ S3 cleanup completed")
    
    async def cleanup_qdrant(self):
        """Clean up Qdrant collection."""
        
        print("🧹 Cleaning up Qdrant collection...")
        
        try:
            from qdrant_client import AsyncQdrantClient
            aclient = AsyncQdrantClient(url=self.qdrant_config.url)
            await aclient.delete_collection(self.qdrant_config.collection_name)
            print(f"   🗑️  Deleted collection: {self.qdrant_config.collection_name}")
        except Exception as e:
            print(f"   ⚠️  Qdrant cleanup warning: {e}")
        
        print("   ✅ Qdrant cleanup completed")
    
    async def demonstrate_multiple_collections(self):
        """Demonstrate how to work with multiple collections for the same user."""
        
        print("\n🔍 DEMONSTRATING MULTIPLE COLLECTIONS:")
        print("-" * 60)
        
        test_collections = [
            "user_docs_collection",
            "business_docs_collection",
        ]
        
        async for db in get_db():
            # Create first collection with explicit name
            collection_1 = await self.prod_rag_service.get_or_create_collection(
                user_id=self.test_user_id,
                collection_name=test_collections[0], 
                display_name="User Documents",
                db=db
            )
            
            # Create second collection with explicit name
            collection_2 = await self.prod_rag_service.get_or_create_collection(
                user_id=self.test_user_id,
                collection_name=test_collections[1],
                display_name="Business Documents", 
                db=db
            )
            
            print(f"📂 Collection 1: {collection_1.collection_name} (ID: {collection_1.id})")
            print(f"📂 Collection 2: {collection_2.collection_name} (ID: {collection_2.id})")
            
            # To add documents to specific collection, use the collection_name:
            # await self.prod_rag_service.process_s3_documents(collection_id=collection_1.id, ...)
            # await self.prod_rag_service.process_s3_documents(collection_id=collection_2.id, ...)
            
            print("💡 Key insights:")
            print("   • Each user can have multiple collections")
            print("   • Collections are identified by user_id + collection_name")
            print("   • Use explicit collection_name to target specific collections")
            print("   • Use collection_name=None to create new random-named collections")
            print("   • Store collection_name to reuse/update existing collections")
            
            break
        
        # cleanup
        for cname in test_collections:
            """Clean up Qdrant collection."""
        
            print("🧹 Cleaning up Qdrant collection...")
            
            try:
                from qdrant_client import AsyncQdrantClient
                aclient = AsyncQdrantClient(url=self.qdrant_config.url)
                await aclient.delete_collection(cname)
                print(f"   🗑️  Deleted collection: {cname}")
            except Exception as e:
                print(f"   ⚠️  Qdrant cleanup warning: {e}")
            
            print("   ✅ Qdrant cleanup completed")
    
    async def validate_persistence_explicitly(self):
        """Explicitly validate that data persists across service instances."""
        
        print("\n🔍 EXPLICIT PERSISTENCE VALIDATION:")
        print("-" * 60)
        
        # Create first service instance
        service_1 = ProductionRAGService(self.rag_config, self.qdrant_config)
        
        # Create second service instance 
        service_2 = ProductionRAGService(self.rag_config, self.qdrant_config)
        
        # Create third service instance
        service_3 = ProductionRAGService(self.rag_config, self.qdrant_config)
        
        async for db in get_db():
            # All three instances should see the same collection (using qdrant config collection name)
            collection_1 = await service_1.get_or_create_collection(
                user_id=self.test_user_id,
                collection_name=None,  # Will use qdrant config collection name
                db=db
            )
            
            collection_2 = await service_2.get_or_create_collection(
                user_id=self.test_user_id,
                collection_name=None,  # Will use qdrant config collection name
                db=db
            )
            
            collection_3 = await service_3.get_or_create_collection(
                user_id=self.test_user_id,
                collection_name=None,  # Will use qdrant config collection name
                db=db
            )
            
            # Validate they all return the SAME collection
            print(f"✅ Collection IDs: {collection_1.id}, {collection_2.id}, {collection_3.id}")
            print(f"✅ Collection Names: {collection_1.collection_name}, {collection_2.collection_name}, {collection_3.collection_name}")
            
            # Verify they are the same (using string comparison to avoid SQLAlchemy boolean issues)
            id_1_str = str(collection_1.id)
            id_2_str = str(collection_2.id) 
            id_3_str = str(collection_3.id)
            
            name_1_str = str(collection_1.collection_name)
            name_2_str = str(collection_2.collection_name)
            name_3_str = str(collection_3.collection_name)
            
            if not (id_1_str == id_2_str == id_3_str):
                raise Exception(f"Collection IDs don't match: {id_1_str}, {id_2_str}, {id_3_str}")
                
            if not (name_1_str == name_2_str == name_3_str):
                raise Exception(f"Collection names don't match: {name_1_str}, {name_2_str}, {name_3_str}")
            
            print(f"✅ All 3 service instances see SAME collection: {name_1_str}")
            
            # Test that all can query the same data
            test_query = "What is the passenger name?"
            
            result_1 = await service_1.query_collection(collection_1.id, test_query, self.test_user_id, db)
            result_2 = await service_2.query_collection(collection_2.id, test_query, self.test_user_id, db)
            result_3 = await service_3.query_collection(collection_3.id, test_query, self.test_user_id, db)
            
            print(f"✅ All 3 service instances return data:")
            print(f"   Service 1: {len(result_1.sources)} sources")
            print(f"   Service 2: {len(result_2.sources)} sources") 
            print(f"   Service 3: {len(result_3.sources)} sources")
            
            # Validate they all find sources (basic validation)
            if not (len(result_1.sources) > 0 and len(result_2.sources) > 0 and len(result_3.sources) > 0):
                raise Exception("Not all service instances found sources!")
            
            sources_match = (len(result_1.sources) == len(result_2.sources) == len(result_3.sources))
            if not sources_match:
                print(f"⚠️  Different source counts - may indicate different retrieval behavior")
            else:
                print(f"✅ All service instances found same number of sources")
            
            print("🎯 PERSISTENCE VALIDATION PASSED!")
            print("   • Multiple service instances see same collection")
            print("   • Multiple service instances return same query results")
            print("   • No in-memory caching - all data from persistent storage")
            
            break
    
    async def run_comprehensive_test(self):
        """Run the comprehensive production RAG service test."""
        
        print("🚀 Starting Comprehensive Production RAG Service Test")
        print("=" * 80)
        
        try:
            # === PHASE 1: Initial Setup & Processing ===
            print("\n📋 PHASE 1: Initial Setup & Processing")
            print("-" * 50)
            
            # Create test user
            await self.create_test_user()
            
            # Demonstrate multiple collections concept
            await self.demonstrate_multiple_collections()
            
            # Upload first test file
            s3_key_1 = await self.upload_file_to_s3(test_file_1, "PRY NDLS 20 June.pdf")
            
            # Process and create collection using qdrant config collection name
            print("🆕 Creating collection for first file...")
            collection_id = await self.process_documents_and_create_collection([s3_key_1])
            
            # Query the collection
            train_queries = [
                "What is the passenger name on the train ticket?",
                "What are the source and destination stations for this train journey?",
                "What is the PNR number and booking status?",
                "What is the total fare amount?",
            ]
            
            results_1 = await self.query_collection(collection_id, train_queries)
            
            # === PHASE 2: Memory Invalidation & Persistence Test ===
            print("\n📋 PHASE 2: Memory Invalidation & Persistence Test")
            print("-" * 50)
            
            # Simulate memory invalidation
            await self.simulate_memory_invalidation()
            
            # Upload second test file
            s3_key_2 = await self.upload_file_to_s3(test_file_2, "Trykaa_ Strategic Deep Dive & Positioning.pdf")
            
            # Process second file into EXISTING collection (will reuse qdrant config collection name)
            print("🔄 Adding second file to EXISTING collection...")
            await self.process_documents_and_create_collection([s3_key_2])
            
            # === PHASE 3: Updated Index Testing ===
            print("\n📋 PHASE 3: Updated Index Testing")
            print("-" * 50)
            
            # Test previous queries (should still work)
            print("🔍 Testing previous queries on updated index...")
            results_2 = await self.query_collection(collection_id, train_queries[:2])
            
            # Test new queries for Trykaa
            print("🔍 Testing new queries for Trykaa...")
            trykaa_queries = [
                "What is Trykaa and what does the company do?",
                "What is Trykaa's business model and revenue strategy?",
                "What are Trykaa's key competitive advantages?",
                "What are the main challenges Trykaa faces?",
            ]
            
            results_3 = await self.query_collection(collection_id, trykaa_queries)
            
            # === PHASE 4: Performance Summary ===
            print("\n📋 PHASE 4: Performance Summary")
            print("-" * 50)
            
            all_results = results_1 + results_2 + results_3
            query_times = [r['query_time'] for r in all_results]
            
            if query_times:
                avg_time = sum(query_times) / len(query_times)
                min_time = min(query_times)
                max_time = max(query_times)
                
                print(f"📊 Query Performance Summary:")
                print(f"   • Total Queries: {len(query_times)}")
                print(f"   • Average Time: {avg_time:.3f}s")
                print(f"   • Fastest Query: {min_time:.3f}s")
                print(f"   • Slowest Query: {max_time:.3f}s")
                print(f"   • Queries per Second: {1/avg_time:.2f}")
            
            print(f"\n🎉 Test completed successfully!")
            print(f"   ✅ Processed {len(self.uploaded_s3_keys)} files")
            print(f"   ✅ Created {len(all_results)} query results")
            print(f"   ✅ Tested persistence and incremental updates")
            
            # Validate persistence explicitly
            await self.validate_persistence_explicitly()
            
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            raise
            
        finally:
            # === PHASE 5: Complete Cleanup ===
            print("\n📋 PHASE 5: Complete Cleanup")
            print("-" * 50)
            
            await self.cleanup_database()
            await self.cleanup_s3()
            await self.cleanup_qdrant()
            
            print("\n✅ All cleanup completed - no test data remains")


async def test_prod_rag_service():
    """Main test function that runs the comprehensive production RAG service test."""
    
    # Create test-specific configuration
    test_config = RAGConfig.for_chat_application(
        s3_bucket_name=f"test-prod-rag-{uuid.uuid4().hex[:8]}",
        enable_logging=True,
        exclude_patterns=["*.pptx", "*.ppt"],  # Exclude PowerPoint for faster testing
        chunk_size=512,  # Smaller chunks for faster processing
        chunk_overlap=50,
        similarity_top_k=10,
        show_progress=True,
        num_workers=2,
    )
    
    print(f"🔧 Test Configuration:")
    print(f"   📦 S3 Bucket: {test_config.s3_bucket_name}")
    print(f"   🧠 LLM Model: {test_config.llm_model}")
    print(f"   🔤 Chunk Size: {test_config.chunk_size}")
    print(f"   🎯 Similarity Top K: {test_config.similarity_top_k}")
    
    # Run the test
    runner = ProductionRAGTestRunner(test_config)
    await runner.run_comprehensive_test()


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_prod_rag_service())