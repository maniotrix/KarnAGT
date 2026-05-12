import asyncio
import os
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.storage import StorageContext
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters, FilterOperator
from llama_index.embeddings.openai import OpenAIEmbedding
from qdrant_client import QdrantClient, AsyncQdrantClient

async def test_llamaindex_filtering():
    """Test if LlamaIndex MetadataFilters work correctly with Qdrant."""
    
    try:
        # Setup OpenAI API key
        from dotenv import load_dotenv
        load_dotenv()
        
        # Setup LlamaIndex settings with correct embedding model (3072 dimensions)
        Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-large")
        
        collection_name = 'conversation_81ded89a-f54f-4ec5-8652-706b7b01ea64_486d2ec5'
        
        print(f"Testing LlamaIndex MetadataFilters with collection: {collection_name}")
        print("-" * 60)
        
        # Create Qdrant clients
        client = QdrantClient(url='http://localhost:6333')
        aclient = AsyncQdrantClient(url='http://localhost:6333')
        
        # Create vector store
        vector_store = QdrantVectorStore(
            client=client,
            aclient=aclient,
            collection_name=collection_name,
            enable_hybrid=False
        )
        
        # Create storage context
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # Create index
        index = VectorStoreIndex(
            nodes=[],  # Empty - connecting to existing
            storage_context=storage_context
        )
        
        # Test 1: Query without filters (should return results)
        print("🔍 Test 1: Query without filters")
        query_engine_no_filter = index.as_query_engine(
            similarity_top_k=3,
            response_mode="compact"
        )
        
        response_no_filter = await query_engine_no_filter.aquery("passenger name")
        print(f"Results without filter: {len(response_no_filter.source_nodes) if response_no_filter.source_nodes else 0} nodes")
        
        if response_no_filter.source_nodes:
            for i, node in enumerate(response_no_filter.source_nodes):
                print(f"  Node {i+1}:")
                print(f"    doc_id: {node.metadata.get('doc_id', 'N/A')}")
                print(f"    status: {node.metadata.get('status', 'N/A')}")
                print(f"    file_name: {node.metadata.get('file_name', 'N/A')}")
        
        print()
        
        # Test 2: Query with active filter (should return 0 results)
        print("🔍 Test 2: Query with status='active' filter")
        active_filter = MetadataFilters(
            filters=[
                MetadataFilter(
                    key="status",
                    operator=FilterOperator.EQ,
                    value="active"
                )
            ]
        )
        
        query_engine_active = index.as_query_engine(
            similarity_top_k=3,
            response_mode="compact",
            filters=active_filter
        )
        
        response_active = await query_engine_active.aquery("passenger name")
        print(f"Results with active filter: {len(response_active.source_nodes) if response_active.source_nodes else 0} nodes")
        
        if response_active.source_nodes:
            for i, node in enumerate(response_active.source_nodes):
                print(f"  Node {i+1}:")
                print(f"    doc_id: {node.metadata.get('doc_id', 'N/A')}")
                print(f"    status: {node.metadata.get('status', 'N/A')}")
                print(f"    file_name: {node.metadata.get('file_name', 'N/A')}")
        
        print()
        
        # Test 3: Query with inactive filter (should return results)
        print("🔍 Test 3: Query with status='inactive' filter")
        inactive_filter = MetadataFilters(
            filters=[
                MetadataFilter(
                    key="status",
                    operator=FilterOperator.EQ,
                    value="inactive"
                )
            ]
        )
        
        query_engine_inactive = index.as_query_engine(
            similarity_top_k=3,
            response_mode="compact",
            filters=inactive_filter
        )
        
        response_inactive = await query_engine_inactive.aquery("passenger name")
        print(f"Results with inactive filter: {len(response_inactive.source_nodes) if response_inactive.source_nodes else 0} nodes")
        
        if response_inactive.source_nodes:
            for i, node in enumerate(response_inactive.source_nodes):
                print(f"  Node {i+1}:")
                print(f"    doc_id: {node.metadata.get('doc_id', 'N/A')}")
                print(f"    status: {node.metadata.get('status', 'N/A')}")
                print(f"    file_name: {node.metadata.get('file_name', 'N/A')}")
        
        print()
        
        # Test 4: Direct response comparison
        print("🔍 Test 4: Response comparison")
        print(f"No filter response: {str(response_no_filter) if response_no_filter else 'N/A'}")
        print(f"Active filter response: {str(response_active) if response_active else 'N/A'}")
        print(f"Inactive filter response: {str(response_inactive) if response_inactive else 'N/A'}")
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

asyncio.run(test_llamaindex_filtering()) 