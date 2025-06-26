from llama_index.core import VectorStoreIndex, Document, Settings, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.vector_stores import SimpleVectorStore
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
import os
import time
import psutil
import torch
from dotenv import load_dotenv

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


current_dir = os.path.dirname(os.path.abspath(__file__))

backend_dir = os.path.dirname(os.path.dirname(current_dir))
test_docs_dir = os.path.join(backend_dir, "test_docs")


# Configure LlamaIndex settings globally
Settings.llm = OpenAI(model="gpt-4o-mini-2024-07-18")
Settings.embed_model = OpenAIEmbedding()

# Load real documents from test_docs folder
perf_monitor.start_timing("Document Loading")
from llama_index.core import SimpleDirectoryReader

# Load documents from the test_docs folder
docs = SimpleDirectoryReader(test_docs_dir).load_data()
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

# Option 2: Qdrant In-Memory (DEFAULT - No external server needed!)
perf_monitor.start_timing("Vector Store Setup")
print("📝 Using Qdrant (in-memory mode)...")
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

# Create the index with your chosen vector store
perf_monitor.start_timing("Document Embedding & Indexing")
index = VectorStoreIndex.from_documents(
    documents=docs,
    storage_context=storage_context,
    transformations=[node_parser],
    show_progress=True
)
perf_monitor.end_timing("Document Embedding & Indexing")

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
    "Tell me about AI agents and their capabilities",
    "What are the key features of distributed systems?",
    "How do human cells compare to AI agents?"
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

print(f"\n⏱️  Detailed Timing Breakdown:")
operations = summary.get('operations', {})
total_time = summary.get('total_time', 0)
if isinstance(operations, dict) and isinstance(total_time, (int, float)):
    for operation, duration in operations.items():
        percentage = (duration / total_time) * 100 if total_time > 0 else 0
        print(f"   • {operation}: {duration:.3f}s ({percentage:.1f}%)")

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