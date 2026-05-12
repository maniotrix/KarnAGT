"""
Isolated Qdrant Test with Proper Vector Configuration

This test fixes the "vector name error: text-dense" issue by:
- Properly configuring vector dimensions and names
- Explicitly creating collections with correct schema
- Using consistent vector naming between LlamaIndex and Qdrant
"""

import asyncio
import os
from typing import List, Tuple
from dotenv import load_dotenv

from llama_index.core import VectorStoreIndex, Document, Settings, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.qdrant import QdrantVectorStore

# Qdrant server setup: import BOTH sync and async clients
from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Load environment
load_dotenv()

class QdrantIsolatedTest:
    def __init__(self):
        # Configure LlamaIndex settings
        Settings.llm = OpenAI(model="gpt-3.5-turbo", temperature=0.1)
        Settings.embed_model = OpenAIEmbedding(model="text-embedding-ada-002")
        
        # Test documents
        self.test_docs = [
            Document(text="This is a test document about artificial intelligence."),
            Document(text="Machine learning is a subset of AI that focuses on algorithms."),
            Document(text="Vector databases store high-dimensional data efficiently."),
        ]
        
        # Qdrant server configuration
        self.host = "localhost"
        self.port = 6333
        self.collection_name = "test_collection"
        
    async def test_qdrant_server_connection(self) -> Tuple[QdrantClient, AsyncQdrantClient]:
        """Test Qdrant server connection."""
        try:
            print("\n🔧 Testing Qdrant server connection...")
            
            # Create both sync and async clients for server
            sync_client = QdrantClient(host=self.host, port=self.port)
            async_client = AsyncQdrantClient(host=self.host, port=self.port)
            
            print("✅ Both clients created successfully")
            
            # Test server connectivity
            collections = await async_client.get_collections()
            print(f"✅ Server connected, collections: {len(collections.collections)}")
            
            return sync_client, async_client
            
        except Exception as e:
            print(f"❌ Server connection failed: {e}")
            print("💡 Make sure Qdrant server is running: docker run -p 6333:6333 qdrant/qdrant")
            raise

    async def create_collection_with_proper_schema(self, sync_client: QdrantClient, async_client: AsyncQdrantClient):
        """Create collection with proper vector schema to avoid 'text-dense' error."""
        try:
            print(f"\n🔧 Creating collection '{self.collection_name}' with proper schema...")
            
            # Delete collection if it exists (for clean test)
            try:
                await async_client.delete_collection(self.collection_name)
                print("🗑️ Deleted existing collection")
            except:
                pass  # Collection doesn't exist, that's fine
            
            # Get embedding dimension from OpenAI (text-embedding-ada-002 = 1536 dimensions)
            embedding_dim = 1536
            
            # Create collection with explicit vector configuration
            # This fixes the "vector name error: text-dense" issue
            await async_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=embedding_dim,
                    distance=Distance.COSINE
                )
            )
            
            print(f"✅ Collection created with {embedding_dim} dimensions")
            
            # Verify collection exists
            collection_info = await async_client.get_collection(self.collection_name)
            print(f"✅ Collection verified: {collection_info.config.params.vectors}")
            
        except Exception as e:
            print(f"❌ Collection creation failed: {e}")
            raise

    async def test_vector_store_creation(self, sync_client: QdrantClient, async_client: AsyncQdrantClient) -> StorageContext:
        """Test QdrantVectorStore creation with proper configuration."""
        try:
            print("\n🔧 Testing QdrantVectorStore creation...")
            
            # Create vector store with both clients (LlamaIndex requirement)
            # The collection already exists with proper schema
            vector_store = QdrantVectorStore(
                client=sync_client,           # Sync client for LlamaIndex compatibility
                aclient=async_client,         # Async client for async operations
                collection_name=self.collection_name,
                enable_hybrid=False           # Disable hybrid search for simplicity
            )
            
            print("✅ QdrantVectorStore created successfully")
            
            # Create storage context
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            print("✅ StorageContext created successfully")
            
            return storage_context
            
        except Exception as e:
            print(f"❌ Vector store creation failed: {e}")
            raise

    async def test_index_creation(self, storage_context: StorageContext) -> VectorStoreIndex:
        """Test VectorStoreIndex creation."""
        try:
            print("\n🔧 Testing VectorStoreIndex creation...")
            
            # Create node parser
            node_parser = SentenceSplitter(
                chunk_size=512,
                chunk_overlap=50
            )
            
            print("📝 Creating index from documents...")
            
            # Create index - this should now work without vector name errors
            index = VectorStoreIndex.from_documents(
                documents=self.test_docs,
                storage_context=storage_context,
                transformations=[node_parser],
                show_progress=True
            )
            
            print("✅ VectorStoreIndex created successfully")
            return index
            
        except Exception as e:
            print(f"❌ Index creation failed: {e}")
            raise

    async def test_query_engine(self, index: VectorStoreIndex):
        """Test async query engine."""
        try:
            print("\n🔧 Testing async query engine...")
            
            # Create query engine
            query_engine = index.as_query_engine(
                similarity_top_k=2,
                response_mode="tree_summarize"
            )
            
            # Test query
            test_query = "What is artificial intelligence?"
            print(f"❓ Testing query: '{test_query}'")
            
            response = await query_engine.aquery(test_query)
            print(f"🤖 Response: {response}")
            
            print("✅ Query engine working successfully")
            
        except Exception as e:
            print(f"❌ Query engine failed: {e}")
            raise

    async def run_full_test(self):
        """Run the complete test with proper Qdrant server setup."""
        sync_client = None
        async_client = None
        
        try:
            print("🚀 Starting Qdrant server test with proper vector configuration...\n")
            
            # Step 1: Test server connection
            sync_client, async_client = await self.test_qdrant_server_connection()
            
            # Step 2: Create collection with proper schema
            await self.create_collection_with_proper_schema(sync_client, async_client)
            
            # Step 3: Test vector store creation
            storage_context = await self.test_vector_store_creation(sync_client, async_client)
            
            # Step 4: Test index creation
            index = await self.test_index_creation(storage_context)
            
            # Step 5: Test query engine
            await self.test_query_engine(index)
            
            print("\n🎉 All tests passed! Qdrant server setup is working correctly!")
            print("💡 Key fixes applied:")
            print("   - Used Qdrant server instead of memory mode")
            print("   - Pre-created collection with proper vector schema")
            print("   - Configured correct embedding dimensions (1536)")
            print("   - Used both sync and async clients as required by LlamaIndex")
            
        except Exception as e:
            print(f"\n💥 Test failed: {e}")
            print("🔍 Check Qdrant server status and configuration")
        finally:
            # Cleanup: close clients
            try:
                if async_client is not None:
                    await async_client.close()
                if sync_client is not None:
                    sync_client.close()
                print("🧹 Clients closed successfully")
            except:
                pass

# Run the test
if __name__ == "__main__":
    test = QdrantIsolatedTest()
    asyncio.run(test.run_full_test()) 