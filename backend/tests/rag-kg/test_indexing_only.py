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
        ('app.services.knowledge.production_rag_service', logging.DEBUG),  # Enable DEBUG for our service
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
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.database import User, VectorCollection, VectorCollectionScope, KnowledgeFile
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
            
            self.test_user_id = test_user.user_id  # Use UUID string instead of integer id
            print(f"   ✅ Created test user: ID={self.test_user_id}, Email={test_user.email}")
            
            return test_user.user_id  # Return UUID string instead of integer id
        
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
    
    async def process_documents_and_create_collection(self, s3_keys: List[str], scope: VectorCollectionScope = VectorCollectionScope.USER):
        """Process S3 documents and create/update vector collection using production service."""
        
        print(f"🔄 Processing {len(s3_keys)} documents...")
        print(f"   🔄 Using scope: {scope.value}")
        
        async for db in get_db():
            # Get or create collection using explicit scope
            collection = await self.prod_rag_service.get_or_create_collection(
                user_id=self.test_user_id,
                scope=scope,
                scope_id=str(self.test_user_id),  # Use user_id as scope_id for user collections
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
            
            # Get ref_doc_ids from KnowledgeFile records using new schema
            from sqlalchemy import select
            from app.models.database.knowledge_file import KnowledgeFile
            
            knowledge_files_result = await db.execute(
                select(KnowledgeFile).where(
                    KnowledgeFile.collection_id == collection.id,
                    KnowledgeFile.file_path.in_(s3_keys)
                )
            )
            knowledge_files = knowledge_files_result.scalars().all()
            
            # NEW: Extract all ref_doc_ids from all files (flattened list)
            ref_doc_ids = []
            for kf in knowledge_files:
                file_ref_doc_ids = kf.get_ref_doc_ids()
                ref_doc_ids.extend(file_ref_doc_ids)
                print(f"      📄 File {kf.file_name}: {len(file_ref_doc_ids)} documents")
            
            print(f"      🆔 Total ref_doc_ids: {len(ref_doc_ids)} - {ref_doc_ids}")
            print(f"      📁 Files processed: {len(knowledge_files)} (1 file = 1 record)")
            
            return collection.id, ref_doc_ids
        
        # This should never be reached due to the async generator, but add for type safety
        raise Exception("Failed to process documents - no database session")
    
    async def query_collection_with_documents(self, collection_id: str, queries: List[str], ref_doc_ids: List[str]) -> List[Dict[str, Any]]:
        """Query collection with document ID filtering."""
        
        print(f"🔍 Running {len(queries)} filtered queries with {len(ref_doc_ids)} documents...")
        print(f"🎯 Using ref_doc_ids: {ref_doc_ids}")
        
        results = []
        
        async for db in get_db():
            for i, query in enumerate(queries, 1):
                print(f"\n📋 Filtered Query {i}: {query}")
                
                start_time = time.time()
                
                # Use document-filtered query
                query_result = await self.prod_rag_service.query_collection_with_documents(
                    collection_id=collection_id,
                    query=query,
                    document_ids=ref_doc_ids,
                    user_id=self.test_user_id,
                    db=db
                )
                
                query_time = time.time() - start_time
                
                print(f"💬 Response: {query_result.response}")
                print(f"⏱️  Query Time: {query_time:.3f}s")
                print(f"📚 Sources: {len(query_result.sources)}")
                
                # Show top sources with document verification
                for j, source in enumerate(query_result.sources[:3], 1):
                    filtered_flag = "✅" if source.get('document_filtered', False) else "❌"
                    print(f"   {j}. {source.get('file_name', 'Unknown')} (Score: {source.get('score', 'N/A')}) {filtered_flag}")
                    print(f"      📝 {source.get('text_preview', 'No preview')}")
                    print(f"      🆔 ref_doc_id: {source.get('ref_doc_id', 'Unknown')}")
                
                results.append({
                    'query': query,
                    'response': query_result.response,
                    'sources': query_result.sources,
                    'query_time': query_time,
                    'filtered_docs': ref_doc_ids
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
                    delete(User).where(User.user_id == self.test_user_id)  # Use user_id field instead of id field
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
        
        if self.test_collection_name is None:
            print("⚠️  No collection name to cleanup")
            return
            
        print("🧹 Cleaning up Qdrant collection...")
        
        try:
            from qdrant_client import AsyncQdrantClient
            aclient = AsyncQdrantClient(url=self.qdrant_config.url)
            await aclient.delete_collection(self.test_collection_name)
            print(f"   🗑️  Deleted collection: {self.test_collection_name}")
        except Exception as e:
            print(f"   ⚠️  Qdrant cleanup warning: {e}")
        
        print("   ✅ Qdrant cleanup completed")
    
    async def compare_database_vs_qdrant(self, collection_id: str, expected_ref_doc_ids: List[str]):
        """Compare what's stored in database vs Qdrant vector store."""
        
        print("🔍 Comparing Database vs Qdrant Storage...")
        
        async for db in get_db():
            # Step 1: Get data from database
            print("\n📋 Step 1: Check Database Storage")
            
            kf_result = await db.execute(
                select(KnowledgeFile).where(KnowledgeFile.user_id == self.test_user_id)
            )
            knowledge_files = kf_result.scalars().all()
            
            print(f"Found {len(knowledge_files)} KnowledgeFile records:")
            all_db_ref_doc_ids = []
            
            for i, kf in enumerate(knowledge_files, 1):
                ref_doc_ids = kf.get_ref_doc_ids()
                all_db_ref_doc_ids.extend(ref_doc_ids)
                print(f"  {i}. File: {kf.file_name}")
                print(f"      S3 Key: {kf.file_path}")
                print(f"      Collection ID: {kf.collection_id}")
                print(f"      Node Count: {kf.node_count}")
                print(f"      ref_doc_ids: {ref_doc_ids}")
            
            print(f"Total ref_doc_ids in DB: {len(all_db_ref_doc_ids)} - {all_db_ref_doc_ids}")
            
            # Step 2: Get data from Qdrant
            print("\n📋 Step 2: Check Qdrant Storage")
            
            try:
                from qdrant_client import QdrantClient
                
                client = QdrantClient(url=self.qdrant_config.url)
                collection_info = client.get_collection(self.test_collection_name)
                print(f"Qdrant collection points: {collection_info.points_count}")
                
                # Get all points
                scroll_result = client.scroll(self.test_collection_name, limit=50)
                points = scroll_result[0]
                
                print(f"Found {len(points)} points in Qdrant:")
                qdrant_doc_ids = []
                
                for i, point in enumerate(points, 1):
                    payload = point.payload
                    doc_id = payload.get('doc_id')
                    ref_doc_id = payload.get('ref_doc_id')
                    
                    if doc_id and doc_id != 'None':
                        qdrant_doc_ids.append(doc_id)
                    
                    print(f"  {i}. Point ID: {point.id}")
                    print(f"      doc_id: {doc_id}")
                    print(f"      ref_doc_id: {ref_doc_id}")
                    print(f"      file_name: {payload.get('file_name', 'Missing')}")
                    print(f"      _node_type: {payload.get('_node_type', 'Missing')}")
                    print(f"      Has _node_content: {'_node_content' in payload if payload else False}")
                
                print(f"Unique doc_ids in Qdrant: {len(set(qdrant_doc_ids))} - {list(set(qdrant_doc_ids))}")
                
                # Step 3: Compare and analyze
                print("\n📋 Step 3: Comparison Analysis")
                
                db_ref_doc_ids_set = set(all_db_ref_doc_ids)
                qdrant_doc_ids_set = set(qdrant_doc_ids)
                expected_ref_doc_ids_set = set(expected_ref_doc_ids)
                
                print(f"Expected ref_doc_ids: {expected_ref_doc_ids_set}")
                print(f"DB ref_doc_ids: {db_ref_doc_ids_set}")
                print(f"Qdrant doc_ids: {qdrant_doc_ids_set}")
                
                # Check expected vs actual
                if expected_ref_doc_ids_set == db_ref_doc_ids_set:
                    print("✅ MATCH: Expected ref_doc_ids match Database ref_doc_ids")
                else:
                    print("❌ MISMATCH: Expected vs Database ref_doc_ids")
                    print(f"   Expected but not in DB: {expected_ref_doc_ids_set - db_ref_doc_ids_set}")
                    print(f"   In DB but not expected: {db_ref_doc_ids_set - expected_ref_doc_ids_set}")
                
                # Check database vs qdrant
                if db_ref_doc_ids_set == qdrant_doc_ids_set:
                    print("✅ MATCH: Database and Qdrant have consistent ref_doc_ids")
                else:
                    print("❌ MISMATCH: Database and Qdrant have different ref_doc_ids")
                    print(f"   In DB but not Qdrant: {db_ref_doc_ids_set - qdrant_doc_ids_set}")
                    print(f"   In Qdrant but not DB: {qdrant_doc_ids_set - db_ref_doc_ids_set}")
                
                # Step 4: Root cause analysis
                print("\n📋 Step 4: Root Cause Analysis")
                
                if db_ref_doc_ids_set == qdrant_doc_ids_set == expected_ref_doc_ids_set:
                    print("🎯 SUCCESS: All data is consistent across Expected -> DB -> Qdrant")
                    print("   ✅ Document processing is working correctly")
                    print("   ✅ Database storage is working correctly") 
                    print("   ✅ Qdrant storage is working correctly")
                    print("   ✅ ref_doc_id/doc_id mapping is consistent")
                else:
                    print("❌ INCONSISTENCY DETECTED:")
                    
                    if expected_ref_doc_ids_set != db_ref_doc_ids_set:
                        print("   🔴 Issue in document processing or database storage")
                        print("   → Check _update_database_state method")
                    
                    if db_ref_doc_ids_set != qdrant_doc_ids_set:
                        print("   🔴 Issue in vector store storage or metadata handling")
                        print("   → Check node_to_metadata_dict or IngestionPipeline")
                    
                    if expected_ref_doc_ids_set == qdrant_doc_ids_set != db_ref_doc_ids_set:
                        print("   🔴 Database storage issue (Qdrant is correct)")
                        
                    if expected_ref_doc_ids_set == db_ref_doc_ids_set != qdrant_doc_ids_set:
                        print("   🔴 Qdrant storage issue (Database is correct)")
                
            except Exception as e:
                print(f"Error checking Qdrant: {e}")
                import traceback
                traceback.print_exc()
            
            break  # Exit the async generator
    
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
            
            
            # Upload first test file
            s3_key_1 = await self.upload_file_to_s3(test_file_1, "PRY NDLS 20 June.pdf")
            
            # Process and create collection using qdrant config collection name
            print("🆕 Creating collection for first file...")
            collection_id, ref_doc_ids_1 = await self.process_documents_and_create_collection([s3_key_1])
            
            # === PHASE 2: Database vs Qdrant Comparison ===
            print("\n📋 PHASE 2: Database vs Qdrant Storage Comparison")
            print("-" * 50)
            
            await self.compare_database_vs_qdrant(collection_id, ref_doc_ids_1)
            
            # Query the collection
            train_queries = [
                "What is the passenger name on the train ticket?",
            ]
            
            results_1 = await self.query_collection_with_documents(collection_id, train_queries, ref_doc_ids_1)

            
            # === PHASE 4: Performance Summary ===
            print("\n📋 PHASE 4: Performance Summary")
            print("-" * 50)
            
            all_results = results_1
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
            print(f"   ✅ Tested document-specific filtering:")
            print(f"      • Single document queries: {len(all_results)} queries")
            
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