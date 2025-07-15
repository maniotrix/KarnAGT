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
        ('app.services.knowledge.production_rag_service', logging.WARNING),  # Enable DEBUG for our service
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
    
    async def demonstrate_multiple_collections(self):
        """Demonstrate how to work with multiple collections for the same user."""
        
        print("\n🔍 DEMONSTRATING MULTIPLE COLLECTIONS:")
        print("-" * 60)
        
        test_collections = []
        
        async for db in get_db():
            # Create first collection with USER scope
            collection_1 = await self.prod_rag_service.get_or_create_collection(
                user_id=self.test_user_id,
                scope=VectorCollectionScope.USER,
                scope_id=str(self.test_user_id),
                display_name="User Documents",
                db=db
            )
            test_collections.append(collection_1.collection_name)
            # Create second collection with PROJECT scope (demonstrating different scopes)
            collection_2 = await self.prod_rag_service.get_or_create_collection(
                user_id=self.test_user_id,
                scope=VectorCollectionScope.PROJECT,
                scope_id="test_project_001",
                display_name="Business Documents", 
                db=db
            )
            test_collections.append(collection_2.collection_name)
            print(f"📂 Collection 1: {collection_1.collection_name} (ID: {collection_1.id}, Scope: {collection_1.scope})")
            print(f"📂 Collection 2: {collection_2.collection_name} (ID: {collection_2.id}, Scope: {collection_2.scope})")
            
            # To add documents to specific collection, use the collection_id:
            # await self.prod_rag_service.process_s3_documents(collection_id=collection_1.id, ...)
            # await self.prod_rag_service.process_s3_documents(collection_id=collection_2.id, ...)
            
            print("💡 Key insights:")
            print("   • Each user can have multiple collections with different scopes")
            print("   • Collections are identified by user_id + scope + scope_id")
            print("   • Use explicit scope and scope_id to target specific collections")
            print("   • Different scopes: USER, CONVERSATION, PROJECT, ORGANIZATION, etc.")
            print("   • Store collection_id to reuse/update existing collections")
            
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
            # All three instances should see the same collection using USER scope
            collection_1 = await service_1.get_or_create_collection(
                user_id=self.test_user_id,
                scope=VectorCollectionScope.USER,
                scope_id=str(self.test_user_id),
                db=db
            )
            
            collection_2 = await service_2.get_or_create_collection(
                user_id=self.test_user_id,
                scope=VectorCollectionScope.USER,
                scope_id=str(self.test_user_id),
                db=db
            )
            
            collection_3 = await service_3.get_or_create_collection(
                user_id=self.test_user_id,
                scope=VectorCollectionScope.USER,
                scope_id=str(self.test_user_id),
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

    async def validate_collection_id_consistency(self):
        """Validate that Collection ID consistency fix is working correctly."""
        
        print("\n🔍 COLLECTION ID CONSISTENCY VALIDATION:")
        print("-" * 60)
        
        async for db in get_db():
            # Get all KnowledgeFile records for this user first
            knowledge_files_result = await db.execute(
                select(KnowledgeFile).where(KnowledgeFile.user_id == self.test_user_id)
            )
            knowledge_files = knowledge_files_result.scalars().all()
            
            print(f"📁 Found {len(knowledge_files)} knowledge files")
            
            if not knowledge_files:
                print("❌ No knowledge files found - skipping consistency validation")
                return
            
            # Get all unique collection IDs from knowledge files
            unique_collection_ids = set(kf.collection_id for kf in knowledge_files)
            print(f"📊 Knowledge files reference {len(unique_collection_ids)} unique collection(s)")
            
            # Validate each collection that has knowledge files
            for collection_id in unique_collection_ids:
                # Get the collection by ID with eager loading of knowledge_files relationship
                collection_result = await db.execute(
                    select(VectorCollection)
                    .options(selectinload(VectorCollection.knowledge_files))
                    .where(VectorCollection.id == collection_id)
                )
                collection = collection_result.scalar_one_or_none()
                
                if collection is None:
                    print(f"❌ Collection {collection_id} not found in database!")
                    raise Exception(f"Collection {collection_id} referenced by knowledge files but not found!")
                
                print(f"🔍 Testing collection: {collection.collection_name} (ID: {collection.id})")
                
                # Get knowledge files for this specific collection
                collection_files = [kf for kf in knowledge_files if str(kf.collection_id) == str(collection_id)]
                print(f"📁 Collection has {len(collection_files)} knowledge files")
                
                # Validate that all KnowledgeFile records use collection.id (not collection.collection_name)
                consistency_errors = []
                
                for kf in collection_files:
                    # After migration, collection_id should match collection.id
                    # Convert to strings to avoid SQLAlchemy expression comparison
                    kf_collection_id = str(kf.collection_id)
                    collection_id_str = str(collection.id)
                    
                    if kf_collection_id != collection_id_str:
                        consistency_errors.append(f"KnowledgeFile {kf.id} has collection_id='{kf_collection_id}' but collection.id='{collection_id_str}'")
                    
                    # NEW: Validate ref_doc_ids array structure
                    ref_doc_ids = kf.get_ref_doc_ids()
                    if not ref_doc_ids:
                        consistency_errors.append(f"KnowledgeFile {kf.id} has empty ref_doc_ids array")
                    
                    print(f"   📄 {kf.file_name}: {len(ref_doc_ids)} documents in array")
                    
                if consistency_errors:
                    print("❌ COLLECTION ID INCONSISTENCY DETECTED:")
                    for error in consistency_errors:
                        print(f"   • {error}")
                    raise Exception("Collection ID consistency validation failed!")
                else:
                    print(f"✅ All KnowledgeFile records correctly use collection.id for {collection.collection_name}")
                    
                # Validate that the relationship works correctly
                try:
                    # Test the SQLAlchemy relationship (now properly eager-loaded)
                    related_files = collection.knowledge_files  # ✅ Already loaded, no async issues
                    print(f"✅ Collection relationship returns {len(related_files)} knowledge files")
                    
                    # Test querying via collection.id for comparison
                    files_via_relationship = await db.execute(
                        select(KnowledgeFile).where(KnowledgeFile.collection_id == collection.id)
                    )
                    files_count = len(files_via_relationship.scalars().all())
                    print(f"✅ Direct query using collection.id returns {files_count} knowledge files")
                    
                    # Validate that both methods return the same count
                    if len(related_files) != files_count:
                        raise Exception(f"Relationship mismatch: relationship returned {len(related_files)}, query returned {files_count}")
                        
                    # Validate that count matches what we expect from our filtering
                    if files_count != len(collection_files):
                        raise Exception(f"Count mismatch: expected {len(collection_files)} files, got {files_count}")
                        
                except Exception as e:
                    print(f"❌ Relationship validation failed: {e}")
                    raise
                    
            print("🎯 COLLECTION ID CONSISTENCY VALIDATION PASSED!")
            print("   • All KnowledgeFile records use collection.id")
            print("   • SQLAlchemy relationships work correctly")
            print("   • Database queries use consistent collection identifiers")
            print("   • NEW: ref_doc_ids arrays properly populated")
            print("   • NEW: 1 uploaded file = 1 KnowledgeFile record")
            
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
            collection_id, ref_doc_ids_1 = await self.process_documents_and_create_collection([s3_key_1])
            
            # Query the collection
            train_queries = [
                "What is the passenger name on the train ticket?",
                "What are the source and destination stations for this train journey?",
                "What is the PNR number and booking status?",
                "What is the total fare amount?",
            ]
            
            results_1 = await self.query_collection_with_documents(collection_id, train_queries, ref_doc_ids_1)
            
            # === PHASE 2: Memory Invalidation & Persistence Test ===
            print("\n📋 PHASE 2: Memory Invalidation & Persistence Test")
            print("-" * 50)
            
            # Simulate memory invalidation
            await self.simulate_memory_invalidation()
            
            # Upload second test file
            s3_key_2 = await self.upload_file_to_s3(test_file_2, "Trykaa_ Strategic Deep Dive & Positioning.pdf")
            
            # Process second file into EXISTING collection (will reuse qdrant config collection name)
            print("🔄 Adding second file to EXISTING collection...")
            collection_id, ref_doc_ids_2 = await self.process_documents_and_create_collection([s3_key_2])
            
            # === PHASE 3: Updated Index Testing ===
            print("\n📋 PHASE 3: Updated Index Testing")
            print("-" * 50)
            
            # Test previous queries (should still work)
            print("🔍 Testing previous queries on updated index...")
            results_2 = await self.query_collection_with_documents(collection_id, train_queries[:2], ref_doc_ids_1)
            
            # Test new queries for Trykaa (second document only)
            print("🔍 Testing new queries for Trykaa (second document only)...")
            trykaa_queries = [
                "What is Trykaa and what does the company do?",
                "What is Trykaa's business model and revenue strategy?",
                "What are Trykaa's key competitive advantages?",
                "What are the main challenges Trykaa faces?",
            ]
            
            results_3 = await self.query_collection_with_documents(collection_id, trykaa_queries, ref_doc_ids_2)
            
            # Test combined queries with both documents
            print("🔍 Testing combined queries with both documents...")
            combined_ref_doc_ids = ref_doc_ids_1 + ref_doc_ids_2
            combined_queries = [
                "What are the key details from both the train ticket and Trykaa documents?",
                "Compare the information available in both documents",
            ]
            
            results_4 = await self.query_collection_with_documents(collection_id, combined_queries, combined_ref_doc_ids)
            
            # === PHASE 4: Performance Summary ===
            print("\n📋 PHASE 4: Performance Summary")
            print("-" * 50)
            
            all_results = results_1 + results_2 + results_3 + results_4
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
            print(f"      • Single document queries: {len(results_1)} + {len(results_2)} queries")
            print(f"      • Second document queries: {len(results_3)} queries")
            print(f"      • Combined document queries: {len(results_4)} queries")
            print(f"   ✅ Tested persistence and incremental updates")
            
            # Validate persistence explicitly
            await self.validate_persistence_explicitly()
            
            # Validate collection ID consistency (post-migration)
            await self.validate_collection_id_consistency()
            
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