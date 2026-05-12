import asyncio
import os
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.storage import StorageContext
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters, FilterOperator
from llama_index.embeddings.openai import OpenAIEmbedding
from qdrant_client import QdrantClient, AsyncQdrantClient
from llama_index.core import QueryBundle

# Setup OpenAI API key
load_dotenv()

# Setup LlamaIndex settings
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-large")

collection_name = 'conversation_81ded89a-f54f-4ec5-8652-706b7b01ea64_486d2ec5'

async def step1_direct_qdrant_check():
    """Step 1: Direct Qdrant verification"""
    print("🔍 Step 1: Direct Qdrant verification")
    aclient = AsyncQdrantClient(url='http://localhost:6333')
    result = await aclient.scroll(
        collection_name=collection_name,
        limit=3,
        with_payload=True
    )
    
    print(f"Raw Qdrant data (first 3 points):")
    for i, point in enumerate(result[0]):
        if point.payload:
            print(f"  Point {i+1}:")
            print(f"    ID: {point.id}")
            print(f"    status in Qdrant: {point.payload.get('status', 'MISSING')}")
            print(f"    doc_id in Qdrant: {point.payload.get('doc_id', 'MISSING')}")
            print(f"    file_name in Qdrant: {point.payload.get('file_name', 'MISSING')}")
            
            # DEBUG: Check the _node_content field
            node_content = point.payload.get('_node_content', 'MISSING')
            if node_content != 'MISSING':
                print(f"    _node_content preview: {node_content[:200]}...")
                
                # Parse the node content to see the original metadata
                import json
                try:
                    node_data = json.loads(node_content)
                    node_metadata = node_data.get('metadata', {})
                    print(f"    Original node metadata status: {node_metadata.get('status', 'MISSING')}")
                except:
                    print(f"    Could not parse _node_content")
            else:
                print(f"    _node_content: MISSING")
    print()
    
    await aclient.close()

async def step2_raw_llamaindex_retrieval():
    """Step 2: Raw LlamaIndex retrieval (no filters)"""
    print("🔍 Step 2: Raw LlamaIndex retrieval (no filters or processors)")
    
    # Create fresh clients and storage context for this step
    client = QdrantClient(url='http://localhost:6333')
    aclient = AsyncQdrantClient(url='http://localhost:6333')
    
    vector_store = QdrantVectorStore(
        client=client,
        aclient=aclient,
        collection_name=collection_name,
        enable_hybrid=False
    )
    
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex(nodes=[], storage_context=storage_context)
    
    # Create retriever directly
    retriever = index.as_retriever(similarity_top_k=3)
    
    query_bundle = QueryBundle("passenger name")
    nodes = await retriever.aretrieve(query_bundle)
    
    print(f"Raw retrieval results: {len(nodes)} nodes")
    for i, node in enumerate(nodes):
        print(f"  Node {i+1}:")
        print(f"    status in LlamaIndex: {node.metadata.get('status', 'MISSING')}")
        print(f"    doc_id in LlamaIndex: {node.metadata.get('doc_id', 'MISSING')}")
        print(f"    file_name in LlamaIndex: {node.metadata.get('file_name', 'MISSING')}")
        print(f"    All metadata keys: {list(node.metadata.keys())}")
    print()
    
    await aclient.close()
    return nodes

async def step3_active_filter_test():
    """Step 3: Test with status='active' filter"""
    print("🔍 Step 3: Test with status='active' filter")
    
    # Create fresh clients and storage context for this step
    client = QdrantClient(url='http://localhost:6333')
    aclient = AsyncQdrantClient(url='http://localhost:6333')
    
    vector_store = QdrantVectorStore(
        client=client,
        aclient=aclient,
        collection_name=collection_name,
        enable_hybrid=False
    )
    
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex(nodes=[], storage_context=storage_context)
    
    active_filter = MetadataFilters(
        filters=[
            MetadataFilter(
                key="status",
                operator=FilterOperator.EQ,
                value="active"
            )
        ]
    )
    
    active_retriever = index.as_retriever(
        similarity_top_k=3,
        filters=active_filter
    )
    
    query_bundle = QueryBundle("passenger name")
    active_nodes = await active_retriever.aretrieve(query_bundle)
    
    print(f"Active filter results: {len(active_nodes)} nodes")
    for i, node in enumerate(active_nodes):
        print(f"  Node {i+1}:")
        print(f"    status: {node.metadata.get('status', 'MISSING')}")
        print(f"    doc_id: {node.metadata.get('doc_id', 'MISSING')}")
    print()
    
    await aclient.close()
    return active_nodes

async def step4_inactive_filter_test():
    """Step 4: Test with status='inactive' filter"""
    print("🔍 Step 4: Test with status='inactive' filter")
    
    # Create fresh clients and storage context for this step
    client = QdrantClient(url='http://localhost:6333')
    aclient = AsyncQdrantClient(url='http://localhost:6333')
    
    vector_store = QdrantVectorStore(
        client=client,
        aclient=aclient,
        collection_name=collection_name,
        enable_hybrid=False
    )
    
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex(nodes=[], storage_context=storage_context)
    
    inactive_filter = MetadataFilters(
        filters=[
            MetadataFilter(
                key="status",
                operator=FilterOperator.EQ,
                value="inactive"
            )
        ]
    )
    
    inactive_retriever = index.as_retriever(
        similarity_top_k=3,
        filters=inactive_filter
    )
    
    query_bundle = QueryBundle("passenger name")
    inactive_nodes = await inactive_retriever.aretrieve(query_bundle)
    
    print(f"Inactive filter results: {len(inactive_nodes)} nodes")
    for i, node in enumerate(inactive_nodes):
        print(f"  Node {i+1}:")
        print(f"    status: {node.metadata.get('status', 'MISSING')}")
        print(f"    doc_id: {node.metadata.get('doc_id', 'MISSING')}")
    print()
    
    await aclient.close()
    return inactive_nodes

async def step5_analysis(nodes, active_nodes, inactive_nodes):
    """Step 5: Analysis of results"""
    print("🔍 Step 5: Analysis")
    print(f"Qdrant direct query: All points have status='inactive'")
    print(f"LlamaIndex no filter: {len(nodes)} nodes")
    print(f"LlamaIndex active filter: {len(active_nodes)} nodes")
    print(f"LlamaIndex inactive filter: {len(inactive_nodes)} nodes")
    
    if len(nodes) > 0 and len(active_nodes) == 0 and len(inactive_nodes) > 0:
        print("✅ MetadataFilters are working correctly!")
    else:
        print("❌ MetadataFilters may not be working correctly!")
        
    # Check metadata consistency
    if len(nodes) > 0:
        first_node_status = nodes[0].metadata.get('status', 'MISSING')
        print(f"Metadata status in LlamaIndex nodes: {first_node_status}")
        
        if first_node_status != 'inactive':
            print(f"⚠️  Metadata inconsistency detected!")
            print(f"   Qdrant has 'inactive', LlamaIndex shows '{first_node_status}'")

async def test_pure_metadata_filtering():
    """Test pure LlamaIndex MetadataFilters without any custom codebase logic."""
    
    try:
        print(f"Testing PURE LlamaIndex MetadataFilters with collection: {collection_name}")
        print("=" * 70)
        
        # Run each step in isolation
        await step1_direct_qdrant_check()
        
        nodes = await step2_raw_llamaindex_retrieval()
        
        active_nodes = await step3_active_filter_test()
        
        inactive_nodes = await step4_inactive_filter_test()
        
        await step5_analysis(nodes, active_nodes, inactive_nodes)
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

asyncio.run(test_pure_metadata_filtering())