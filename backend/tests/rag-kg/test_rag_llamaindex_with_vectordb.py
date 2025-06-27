from llama_index.core import VectorStoreIndex, Document, Settings, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.vector_stores import SimpleVectorStore
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.core.readers.base import BaseReader
from typing import Optional
import os
import time
import psutil
import torch
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))

backend_dir = os.path.dirname(os.path.dirname(current_dir))

import sys
sys.path.append(backend_dir)

from app.utils.CustomPptxReader import OpenAIPptxReader

# Uncomment the vector store you want to use:

# Option 1: Qdrant (in-memory mode)
from qdrant_client import QdrantClient

# Option 2: Chroma (in-memory)
# import chromadb

# Option 3: Chroma (persistent)
# import chromadb

load_dotenv()

# Performance monitoring setup
def get_device_info():
    """Get CPU and GPU information"""
    cpu_count = psutil.cpu_count()
    cpu_freq = psutil.cpu_freq()
    memory = psutil.virtual_memory()
    
    gpu_info = "No GPU detected"
    if torch.cuda.is_available():
        gpu_info = f"GPU: {torch.cuda.get_device_name(0)} (CUDA Available)"
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        gpu_info = "GPU: Apple Metal Performance Shaders (MPS)"
    
    return {
        "cpu_count": cpu_count,
        "cpu_freq": f"{cpu_freq.current:.2f} MHz" if cpu_freq else "Unknown",
        "memory_total": f"{memory.total / (1024**3):.2f} GB",
        "gpu_info": gpu_info
    }

class PerformanceMonitor:
    def __init__(self):
        self.timings = {}
        
    def start_timing(self, operation):
        """Start timing an operation"""
        print(f"⏱️  Starting {operation}...")
        self.timings[operation] = {
            'start_time': time.time(),
            'cpu_before': psutil.cpu_percent(interval=0.1),
            'memory_before': psutil.virtual_memory().percent
        }
        
    def end_timing(self, operation):
        """End timing an operation"""
        if operation not in self.timings:
            return
            
        timing = self.timings[operation]
        end_time = time.time()
        cpu_after = psutil.cpu_percent(interval=0.1)
        memory_after = psutil.virtual_memory().percent
        
        duration = end_time - timing['start_time']
        timing['duration'] = duration
        timing['cpu_after'] = cpu_after
        timing['memory_after'] = memory_after
        
        print(f"✅ {operation} completed in {duration:.3f}s")
        print(f"   📊 CPU: {timing['cpu_before']:.1f}% → {cpu_after:.1f}%")
        print(f"   💾 Memory: {timing['memory_before']:.1f}% → {memory_after:.1f}%")
        
        return duration
        
    def get_summary(self):
        """Get performance summary"""
        total_time = sum(t.get('duration', 0) for t in self.timings.values())
        return {
            'total_time': total_time,
            'operations': {k: v.get('duration', 0) for k, v in self.timings.items()}
        }

# Initialize performance monitor
perf_monitor = PerformanceMonitor()

print("🧪 Testing LlamaIndex RAG with different vector databases...")
print("🖥️  System Information:")
device_info = get_device_info()
for key, value in device_info.items():
    print(f"   {key}: {value}")
print()


test_docs_dir = os.path.join(backend_dir, "test_docs")


# Configure LlamaIndex settings globally
Settings.llm = OpenAI(model="gpt-4o-mini-2024-07-18")
Settings.embed_model = OpenAIEmbedding()

# Load real documents from test_docs folder
perf_monitor.start_timing("Document Loading")
from llama_index.core import SimpleDirectoryReader

print("📄 Creating new document reader...")
pptx_reader = OpenAIPptxReader(enable_logging=True)
file_extractor: Optional[dict[str, BaseReader]] = {
    ".pptx": pptx_reader,
    ".ppt": pptx_reader
    }
exclude = ["*.pdf"]
docs = SimpleDirectoryReader(test_docs_dir, file_extractor=file_extractor, exclude=exclude).load_data()

perf_monitor.end_timing("Document Loading")
print(f"✅ Loaded {len(docs)} documents from test_docs folder")

# Print document info
for i, doc in enumerate(docs[:3]):  # Show first 3 documents
    print(f"   📄 Document {i+1}: {doc.metadata.get('file_name', 'Unknown')} ({len(doc.text)} chars)")
if len(docs) > 3:
    print(f"   📄 ... and {len(docs) - 3} more documents")

# Create node parser
node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)

# ==========================================
# CHOOSE YOUR VECTOR DATABASE:
# ==========================================

# Option 1: In-Memory (SimpleVectorStore) - DEFAULT
# print("📝 Using SimpleVectorStore (in-memory)...")
# vector_store = SimpleVectorStore()
# storage_context = StorageContext.from_defaults(vector_store=vector_store)

# Option 2: Qdrant In-Memory with Persistence (OPTIMIZED)
perf_monitor.start_timing("Vector Store Setup")
print("📝 Using Qdrant (in-memory mode with caching)...")

# Create cache directory
cache_dir = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(cache_dir, exist_ok=True)

client = QdrantClient(":memory:")  # In-memory mode - no server needed!
vector_store = QdrantVectorStore(client=client, collection_name="test_collection")
storage_context = StorageContext.from_defaults(vector_store=vector_store)
perf_monitor.end_timing("Vector Store Setup")

# Option 3: Chroma In-Memory (Uncomment to use)
# print("📝 Using ChromaVectorStore (in-memory)...")
# chroma_client = chromadb.EphemeralClient()
# chroma_collection = chroma_client.create_collection("llamaindex_test")
# vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
# storage_context = StorageContext.from_defaults(vector_store=vector_store)

# Option 4: Chroma Persistent (Uncomment to use)
# print("📝 Using ChromaVectorStore (persistent)...")
# chroma_client = chromadb.PersistentClient(path="./chroma_db")
# chroma_collection = chroma_client.get_or_create_collection("llamaindex_test")
# vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
# storage_context = StorageContext.from_defaults(vector_store=vector_store)

# Check if cached index exists and is valid
cache_file = os.path.join(cache_dir, "index_cache.json")
embeddings_cache = os.path.join(cache_dir, "embeddings_cache.pkl")
cache_metadata = os.path.join(cache_dir, "cache_metadata.json")

def is_cache_valid(enable_cache: bool = False):
    if not enable_cache:
        return False
    
    """Check if cache is still valid based on document modification times"""
    if not all(os.path.exists(f) for f in [cache_file, embeddings_cache, cache_metadata]):
        return False
    
    try:
        import json
        with open(cache_metadata, 'r') as f:
            metadata = json.load(f)
        
        cached_doc_count = metadata.get('doc_count', 0)
        cached_timestamp = metadata.get('timestamp', 0)
        
        # Check if document count changed
        if len(docs) != cached_doc_count:
            print(f"📄 Document count changed: {cached_doc_count} → {len(docs)}")
            return False
        
        # Check if any documents were modified since cache creation
        latest_doc_time = 0
        for doc in docs:
            file_path = doc.metadata.get('file_path', '')
            if file_path and os.path.exists(file_path):
                doc_time = os.path.getmtime(file_path)
                latest_doc_time = max(latest_doc_time, doc_time)
        
        if latest_doc_time > cached_timestamp:
            print(f"📄 Documents modified since cache creation")
            return False
        
        return True
    except Exception as e:
        print(f"⚠️  Cache validation failed: {e}")
        return False

if is_cache_valid():
    print("🚀 Loading cached index and embeddings...")
    perf_monitor.start_timing("Loading Cached Index")
    try:
        # Load from cache
        from llama_index.core import load_index_from_storage
        storage_context = StorageContext.from_defaults(persist_dir=cache_dir)
        index = load_index_from_storage(storage_context)
        perf_monitor.end_timing("Loading Cached Index")
        print("✅ Cached index loaded successfully!")
    except Exception as e:
        print(f"⚠️  Cache loading failed: {e}")
        print("🔄 Creating fresh index...")
        # Create fresh index if cache fails
        perf_monitor.start_timing("Document Embedding & Indexing")
        index = VectorStoreIndex.from_documents(
            documents=docs,
            storage_context=storage_context,
            transformations=[node_parser],
            show_progress=True
        )
        perf_monitor.end_timing("Document Embedding & Indexing")
        
        # Save to cache
        print("💾 Saving index to cache...")
        index.storage_context.persist(persist_dir=cache_dir)
        
        # Save cache metadata
        import json
        cache_metadata_data = {
            'doc_count': len(docs),
            'timestamp': time.time(),
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'model_config': {
                'llm': getattr(Settings.llm, 'model', 'Unknown'),
                'embedding': type(Settings.embed_model).__name__,
                'chunk_size': node_parser.chunk_size,
                'chunk_overlap': node_parser.chunk_overlap
            }
        }
        
        with open(cache_metadata, 'w') as f:
            json.dump(cache_metadata_data, f, indent=2)
        
        print("✅ Index cached for future use!")
else:
    # Create the index with your chosen vector store (first time)
    print("🆕 Creating fresh index (first time)...")
    perf_monitor.start_timing("Document Embedding & Indexing")
    index = VectorStoreIndex.from_documents(
        documents=docs,
        storage_context=storage_context,
        transformations=[node_parser],
        show_progress=True
    )
    perf_monitor.end_timing("Document Embedding & Indexing")
    
    # Save to cache for future runs
    print("💾 Saving index to cache...")
    index.storage_context.persist(persist_dir=cache_dir)
    
    # Save cache metadata
    import json
    cache_metadata_data = {
        'doc_count': len(docs),
        'timestamp': time.time(),
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'model_config': {
            'llm': getattr(Settings.llm, 'model', 'Unknown'),
            'embedding': type(Settings.embed_model).__name__,
            'chunk_size': node_parser.chunk_size,
            'chunk_overlap': node_parser.chunk_overlap
        }
    }
    
    with open(cache_metadata, 'w') as f:
        json.dump(cache_metadata_data, f, indent=2)
    
    print("✅ Index cached for future use!")

print("✅ Vector store created and documents indexed!")
print("🔍 Creating RAG query engine...")

# Create query engine
query_engine = index.as_query_engine(
    similarity_top_k=3,
    response_mode="tree_summarize",
    verbose=True
)

print("✅ RAG query engine created!")

# Try multiple queries relevant to your documents
queries = [
    "What is Trykaa and what does the company do?",
    "What do customer reviews say about Trykaa? What are the ratings and feedback?",
]

print(f"\n🔍 Testing {len(queries)} queries on your real documents...")

for i, query in enumerate(queries, 1):
    print(f"\n❓ Query {i}: '{query}'")
    
    # Time each query individually
    query_name = f"Query {i} (RAG Inference)"
    perf_monitor.start_timing(query_name)
    response = query_engine.query(query)
    query_time = perf_monitor.end_timing(query_name)
    
    print(f"🤖 Answer: {response}")
    print(f"⚡ Query processed in {query_time:.3f}s")
    
    # Show sources for ALL queries
    if hasattr(response, 'source_nodes') and response.source_nodes:
        print(f"📚 Sources ({len(response.source_nodes)} found):")
        for j, node in enumerate(response.source_nodes[:3], 1):  # Show top 3 sources
            source_file = node.metadata.get('file_name', 'Unknown')
            source_text = node.text[:100].replace('\n', ' ') + '...'
            print(f"   {j}. {source_file}: {source_text}")
    else:
        print("📚 No sources found")
    
    print("-" * 80)

print(f"\n🎉 LlamaIndex RAG test completed!")

# Performance Summary
print(f"\n📊 PERFORMANCE SUMMARY:")
print(f"=" * 60)
summary = perf_monitor.get_summary()
print(f"⏱️  Total Execution Time: {summary['total_time']:.3f}s")
print(f"💾 Vector Store Used: {type(vector_store).__name__}")
print(f"📄 Documents Processed: {len(docs)}")

# Check if cache was used
operations_dict = summary.get('operations', {})
cache_used = False
if isinstance(operations_dict, dict):
    cache_used = any("Loading Cached Index" in op for op in operations_dict.keys())
if cache_used:
    print(f"🚀 Cache Status: USED (Significant speedup!)")
    print(f"📁 Cache Location: {os.path.relpath(cache_dir)}")
else:
    print(f"💾 Cache Status: CREATED (Next run will be faster!)")
    print(f"📁 Cache Location: {os.path.relpath(cache_dir)}")

print(f"\n⏱️  Detailed Timing Breakdown:")
operations = summary.get('operations', {})
total_time = summary.get('total_time', 0)
if isinstance(operations, dict) and isinstance(total_time, (int, float)):
    for operation, duration in operations.items():
        percentage = (duration / total_time) * 100 if total_time > 0 else 0
        cache_indicator = ""
        if "Loading Cached Index" in operation:
            cache_indicator = " 🚀 (CACHED!)"
        elif "Document Embedding & Indexing" in operation:
            cache_indicator = " 💾 (will be cached)"
        elif "Model Warmup" in operation:
            cache_indicator = " 🔥 (optimization)"
        print(f"   • {operation}: {duration:.3f}s ({percentage:.1f}%){cache_indicator}")

# Calculate average query time
query_times = []
if isinstance(operations, dict):
    query_times = [duration for op, duration in operations.items() if 'Query' in op and 'RAG Inference' in op]
if query_times:
    avg_query_time = sum(query_times) / len(query_times)
    print(f"\n⚡ Average Query Time: {avg_query_time:.3f}s")
    print(f"🔥 Queries per Second: {1/avg_query_time:.2f}")

# Hardware utilization summary
print(f"\n🖥️  Hardware Information:")
print(f"   • CPU Cores: {device_info['cpu_count']}")
print(f"   • CPU Frequency: {device_info['cpu_freq']}")
print(f"   • Total Memory: {device_info['memory_total']}")
print(f"   • GPU Status: {device_info['gpu_info']}")

# Embedding model info
print(f"\n🧠 Model Configuration:")
llm_model = getattr(Settings.llm, 'model', 'Unknown')
print(f"   • LLM: {llm_model}")
print(f"   • Embedding Model: {type(Settings.embed_model).__name__}")
print(f"   • Chunk Size: {node_parser.chunk_size}")
print(f"   • Chunk Overlap: {node_parser.chunk_overlap}")

print(f"\n🔧 To use different vector stores, uncomment the relevant section above")

# Additional vector databases LlamaIndex supports:
print(f"\n📋 LlamaIndex supports these vector databases:")
print(f"   - Qdrant (production-ready)")
print(f"   - Chroma (good for prototyping)")
print(f"   - Pinecone (cloud-based)")
print(f"   - Weaviate (semantic search)")
print(f"   - Milvus (scalable)")
print(f"   - Faiss (Facebook AI)")
print(f"   - SimpleVectorStore (in-memory)")
print(f"   - And 20+ more!") 