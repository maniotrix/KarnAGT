from llama_index.core import VectorStoreIndex, Document, Settings, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.vector_stores import SimpleVectorStore
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.core.readers.base import BaseReader
from typing import Optional, List, Dict, Any
import os
import time
import psutil
import torch
import asyncio
import json
from dotenv import load_dotenv
from dataclasses import dataclass
from pathlib import Path

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))

import sys
sys.path.append(backend_dir)

from app.utils.CustomPptxReader import OpenAIPptxReader

# Uncomment the vector store you want to use:
from qdrant_client import QdrantClient, AsyncQdrantClient

# Option 2: Chroma (in-memory)
# import chromadb

# Option 3: Chroma (persistent)
# import chromadb

load_dotenv()

@dataclass
class DeviceInfo:
    """System device information."""
    cpu_count: int
    cpu_freq: str
    memory_total: str
    gpu_info: str

@dataclass
class TestConfig:
    """Configuration for RAG test."""
    model: str = "gpt-4o-mini-2024-07-18"
    chunk_size: int = 512
    chunk_overlap: int = 50
    similarity_top_k: int = 3
    num_workers: int = 2
    enable_logging: bool = True
    exclude_patterns: List[str] = None
    enable_cache: bool = False
    enable_delay: bool = True
    delay_seconds: int = 1

class PerformanceMonitor:
    """Monitor and track performance metrics."""
    
    def __init__(self):
        self.timings: Dict[str, Dict[str, Any]] = {}
        
    def start_timing(self, operation: str) -> None:
        """Start timing an operation."""
        print(f"⏱️  Starting {operation}...")
        self.timings[operation] = {
            'start_time': time.time(),
            'cpu_before': psutil.cpu_percent(interval=0.1),
            'memory_before': psutil.virtual_memory().percent
        }
        
    def end_timing(self, operation: str) -> float:
        """End timing an operation and return duration."""
        if operation not in self.timings:
            return 0.0
            
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
        
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        total_time = sum(t.get('duration', 0) for t in self.timings.values())
        return {
            'total_time': total_time,
            'operations': {k: v.get('duration', 0) for k, v in self.timings.items()}
        }

class RAGTestRunner:
    """Main class for running RAG performance tests."""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.perf_monitor = PerformanceMonitor()
        self.device_info = self._get_device_info()
        self.test_docs_dir = os.path.join(backend_dir, "test_docs")
        self.cache_dir = os.path.join(os.path.dirname(__file__), "cache")
        
        # Initialize components
        self.docs: List[Document] = []
        self.index: Optional[VectorStoreIndex] = None
        self.query_engine = None
        
        # Setup LlamaIndex settings
        Settings.llm = OpenAI(model=self.config.model)
        Settings.embed_model = OpenAIEmbedding()
        
    def _get_device_info(self) -> DeviceInfo:
        """Get CPU and GPU information."""
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        memory = psutil.virtual_memory()
        
        gpu_info = "No GPU detected"
        if torch.cuda.is_available():
            gpu_info = f"GPU: {torch.cuda.get_device_name(0)} (CUDA Available)"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            gpu_info = "GPU: Apple Metal Performance Shaders (MPS)"
        
        return DeviceInfo(
            cpu_count=cpu_count,
            cpu_freq=f"{cpu_freq.current:.2f} MHz" if cpu_freq else "Unknown",
            memory_total=f"{memory.total / (1024**3):.2f} GB",
            gpu_info=gpu_info
        )
    
    def print_system_info(self) -> None:
        """Print system information."""
        print("🧪 Testing LlamaIndex RAG with different vector databases...")
        print("🖥️  System Information:")
        print(f"   cpu_count: {self.device_info.cpu_count}")
        print(f"   cpu_freq: {self.device_info.cpu_freq}")
        print(f"   memory_total: {self.device_info.memory_total}")
        print(f"   gpu_info: {self.device_info.gpu_info}")
        print()
    
    async def load_documents_async(self) -> List[Document]:
        """Load documents asynchronously."""
        from llama_index.core import SimpleDirectoryReader
        
        print("📄 Creating new document reader...")
        pptx_reader = OpenAIPptxReader(enable_logging=self.config.enable_logging, 
                                        model_name=self.config.model, 
                                        enable_delay=self.config.enable_delay, 
                                        delay_seconds=self.config.delay_seconds)
        file_extractor: Dict[str, BaseReader] = {
            ".pptx": pptx_reader,
            ".ppt": pptx_reader
        }
        
        reader = SimpleDirectoryReader(
            self.test_docs_dir, 
            file_extractor=file_extractor, 
            exclude=self.config.exclude_patterns
        )
        return await reader.aload_data(show_progress=True, num_workers=self.config.num_workers)
    
    async def setup_vector_store(self) -> StorageContext:
        """Setup vector store with Qdrant server (production setup)."""
        print("📝 Using Qdrant server (production-ready setup)...")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Use Qdrant server for production-ready setup (fixes "text-dense" error)
        from qdrant_client.models import Distance, VectorParams
        
        # Create both sync and async clients for LlamaIndex compatibility
        client = QdrantClient(host="localhost", port=6333)
        aclient = AsyncQdrantClient(host="localhost", port=6333)
        
        collection_name = "rag_collection"
        
        # Create collection with proper schema to avoid "text-dense" error
        try:
            await aclient.delete_collection(collection_name)
            print("🗑️ Cleaned existing collection")
        except:
            pass  # Collection doesn't exist
        
        # Create collection with proper vector configuration
        await aclient.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=1536,  # OpenAI text-embedding-ada-002 dimensions
                distance=Distance.COSINE
            )
        )
        print("✅ Collection created with proper vector schema")
        
        vector_store = QdrantVectorStore(
            client=client, 
            aclient=aclient, 
            collection_name=collection_name,
            enable_hybrid=False  # Disable for better performance
        )
        return StorageContext.from_defaults(vector_store=vector_store)
    
    def is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self.config.enable_cache:
            return False
        
        cache_file = os.path.join(self.cache_dir, "index_cache.json")
        embeddings_cache = os.path.join(self.cache_dir, "embeddings_cache.pkl")
        cache_metadata = os.path.join(self.cache_dir, "cache_metadata.json")
        
        if not all(os.path.exists(f) for f in [cache_file, embeddings_cache, cache_metadata]):
            return False
        
        try:
            with open(cache_metadata, 'r') as f:
                metadata = json.load(f)
            
            cached_doc_count = metadata.get('doc_count', 0)
            cached_timestamp = metadata.get('timestamp', 0)
            
            if len(self.docs) != cached_doc_count:
                print(f"📄 Document count changed: {cached_doc_count} → {len(self.docs)}")
                return False
            
            # Check if any documents were modified since cache creation
            latest_doc_time = 0
            for doc in self.docs:
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
    
    def create_index(self, storage_context: StorageContext) -> VectorStoreIndex:
        """Create or load vector index."""
        node_parser = SentenceSplitter(
            chunk_size=self.config.chunk_size, 
            chunk_overlap=self.config.chunk_overlap
        )
        
        if self.is_cache_valid():
            print("🚀 Loading cached index and embeddings...")
            self.perf_monitor.start_timing("Loading Cached Index")
            try:
                from llama_index.core import load_index_from_storage
                storage_context = StorageContext.from_defaults(persist_dir=self.cache_dir)
                index = load_index_from_storage(storage_context)
                self.perf_monitor.end_timing("Loading Cached Index")
                print("✅ Cached index loaded successfully!")
                # Ensure we return the correct type
                if not isinstance(index, VectorStoreIndex):
                    raise TypeError(f"Expected VectorStoreIndex, got {type(index)}")
                return index
            except Exception as e:
                print(f"⚠️  Cache loading failed: {e}")
                print("🔄 Creating fresh index...")
        
        # Create fresh index
        print("🆕 Creating fresh index (first time)...")
        self.perf_monitor.start_timing("Document Embedding & Indexing")
        index = VectorStoreIndex.from_documents(
            documents=self.docs,
            storage_context=storage_context,
            transformations=[node_parser],
            show_progress=True
        )
        self.perf_monitor.end_timing("Document Embedding & Indexing")
        
        # Save to cache
        if self.config.enable_cache:
            print("💾 Saving index to cache...")
            index.storage_context.persist(persist_dir=self.cache_dir)
            
            cache_metadata_data = {
                'doc_count': len(self.docs),
                'timestamp': time.time(),
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'model_config': {
                    'llm': getattr(Settings.llm, 'model', 'Unknown'),
                    'embedding': type(Settings.embed_model).__name__,
                    'chunk_size': self.config.chunk_size,
                    'chunk_overlap': self.config.chunk_overlap
                }
            }
            
            cache_metadata_file = os.path.join(self.cache_dir, "cache_metadata.json")
            with open(cache_metadata_file, 'w') as f:
                json.dump(cache_metadata_data, f, indent=2)
            
            print("✅ Index cached for future use!")
        
        return index
    
    async def run_queries_async(self, queries: List[str]) -> List[float]:
        """Run queries asynchronously but sequentially for clean output."""
        print(f"\n🔍 Testing {len(queries)} queries asynchronously (sequential for clean output)...")
        query_times = []
        
        for i, query in enumerate(queries, 1):
            print(f"\n❓ Query {i}: '{query}'")
            
            query_name = f"Query {i} (RAG Inference)"
            self.perf_monitor.start_timing(query_name)
            response = await self.query_engine.aquery(query)
            query_time = self.perf_monitor.end_timing(query_name)
            query_times.append(query_time)
            
            print(f"🤖 Answer: {response}")
            print(f"⚡ Query processed in {query_time:.3f}s")
            
            if hasattr(response, 'source_nodes') and response.source_nodes:
                print(f"📚 Sources ({len(response.source_nodes)} found):")
                for j, node in enumerate(response.source_nodes[:3], 1):
                    source_file = node.metadata.get('file_name', 'Unknown')
                    source_text = node.text[:100].replace('\n', ' ') + '...'
                    print(f"   {j}. {source_file}: {source_text}")
            else:
                print("📚 No sources found")
            
            print("-" * 80)
        
        return query_times
    
    def print_performance_summary(self, query_times: List[float]) -> None:
        """Print comprehensive performance summary."""
        print(f"\n🎉 LlamaIndex RAG test completed!")
        
        print(f"\n📊 PERFORMANCE SUMMARY:")
        print(f"=" * 60)
        summary = self.perf_monitor.get_summary()
        print(f"⏱️  Total Execution Time: {summary['total_time']:.3f}s")
        print(f"💾 Vector Store Used: QdrantVectorStore")
        print(f"📄 Documents Processed: {len(self.docs)}")
        
        # Cache status
        operations_dict = summary.get('operations', {})
        cache_used = any("Loading Cached Index" in op for op in operations_dict.keys()) if isinstance(operations_dict, dict) else False
        if cache_used:
            print(f"🚀 Cache Status: USED (Significant speedup!)")
        else:
            print(f"💾 Cache Status: CREATED (Next run will be faster!)")
        print(f"📁 Cache Location: {os.path.relpath(self.cache_dir)}")
        
        # Timing breakdown
        print(f"\n⏱️  Detailed Timing Breakdown:")
        if isinstance(operations_dict, dict) and isinstance(summary.get('total_time'), (int, float)):
            total_time = summary['total_time']
            for operation, duration in operations_dict.items():
                percentage = (duration / total_time) * 100 if total_time > 0 else 0
                cache_indicator = ""
                if "Loading Cached Index" in operation:
                    cache_indicator = " 🚀 (CACHED!)"
                elif "Document Embedding & Indexing" in operation:
                    cache_indicator = " 💾 (will be cached)"
                print(f"   • {operation}: {duration:.3f}s ({percentage:.1f}%){cache_indicator}")
        
        # Query performance
        if query_times:
            avg_query_time = sum(query_times) / len(query_times)
            print(f"\n⚡ Average Query Time: {avg_query_time:.3f}s")
            print(f"🔥 Queries per Second: {1/avg_query_time:.2f}")
        
        # Hardware info
        print(f"\n🖥️  Hardware Information:")
        print(f"   • CPU Cores: {self.device_info.cpu_count}")
        print(f"   • CPU Frequency: {self.device_info.cpu_freq}")
        print(f"   • Total Memory: {self.device_info.memory_total}")
        print(f"   • GPU Status: {self.device_info.gpu_info}")
        
        # Model config
        print(f"\n🧠 Model Configuration:")
        print(f"   • LLM: {self.config.model}")
        print(f"   • Embedding Model: {type(Settings.embed_model).__name__}")
        print(f"   • Chunk Size: {self.config.chunk_size}")
        print(f"   • Chunk Overlap: {self.config.chunk_overlap}")
    
    async def run_test_async(self) -> None:
        """Run the complete test asynchronously."""
        self.print_system_info()
        
        # Load documents
        self.perf_monitor.start_timing("Document Loading")
        self.docs = await self.load_documents_async()
        self.perf_monitor.end_timing("Document Loading")
        
        print(f"✅ Loaded {len(self.docs)} documents from test_docs folder")
        for i, doc in enumerate(self.docs[:3]):
            print(f"   📄 Document {i+1}: {doc.metadata.get('file_name', 'Unknown')} ({len(doc.text)} chars)")
        if len(self.docs) > 3:
            print(f"   📄 ... and {len(self.docs) - 3} more documents")
        
        # Setup vector store
        self.perf_monitor.start_timing("Vector Store Setup")
        storage_context = await self.setup_vector_store()
        self.perf_monitor.end_timing("Vector Store Setup")
        
        # Create index
        self.index = self.create_index(storage_context)
        
        # Create query engine
        print("🔍 Creating RAG query engine...")
        self.query_engine = self.index.as_query_engine(
            similarity_top_k=self.config.similarity_top_k,
            response_mode="tree_summarize",
            verbose=True
        )
        print("✅ RAG query engine created!")
        
        # Run queries - organized by document for easy commenting
        queries = []
        
        # === TRYKAA QUERIES ===
        # Queries for Trykaa business documents (Strategic Deep Dive, Pitch Deck, Transforming Future)
        trykaa_queries = [
            "What is Trykaa and what does the company do?",
            "What do customer reviews say about Trykaa? What are the ratings and feedback?",
            "What is Trykaa's business model and revenue strategy?",
            "What are Trykaa's key competitive advantages in the fashion retail space?",
            "What are the main challenges Trykaa faces in the online fashion market?",
            "What is Trykaa's target market and customer demographics?",
            "What technology solutions does Trykaa use for their platform?",
            "What are Trykaa's future growth plans and expansion strategies?",
            "What is Trykaa's market positioning compared to competitors?",
            "What are the key metrics and KPIs mentioned for Trykaa's performance?",
        ]
        queries.extend(trykaa_queries)
        
        # === AI AGENTS QUERIES ===
        # Queries for "Comparing a Human Cell to AI Agents" and "Practical Guide to Building Agents"
        ai_agents_queries = [
            "What are the key similarities between human cells and AI agents?",
            "What are the projected differences between AI agents in 2025 vs 2035?",
            "What are the main components of an AI agent architecture?",
            "What are the best practices for building AI agents?",
            "What are the different types of AI agents mentioned in the documents?",
            "What are the key challenges in building effective AI agents?",
            "How do AI agents handle decision-making processes?",
            "What are the ethical considerations for AI agent development?",
            "What tools and frameworks are recommended for building AI agents?",
            "What are the performance metrics for evaluating AI agents?",
        ]
        queries.extend(ai_agents_queries)
        
        # === DISTRIBUTED SYSTEMS QUERIES ===
        # Queries for "Assignment 6: Distributed Systems (Middleware)"
        distributed_systems_queries = [
            "What are the key concepts of distributed systems middleware?",
            "What are the main types of middleware discussed in the assignment?",
            "What are the advantages and disadvantages of different middleware approaches?",
            "What are the common patterns in distributed systems architecture?",
            "What are the key challenges in implementing distributed systems?",
            "What are the performance considerations for distributed systems middleware?",
            "What are the security aspects of distributed systems mentioned?",
            "What are the fault tolerance mechanisms in distributed systems?",
            "What are the scalability strategies for distributed systems?",
            "What are the communication protocols used in distributed systems?",
        ]
        queries.extend(distributed_systems_queries)
        
        # === IRCTC TRAIN TICKET QUERIES ===
        # Queries for "abhilasha_6_april_ticket.pdf" - IRCTC generated train ticket
        train_ticket_queries = [
            "What is the passenger name on the train ticket?",
            "What are the source and destination stations for this train journey?",
            "What is the train number and train name mentioned in the ticket?",
            "What is the travel date and departure time for this journey?",
            "What is the class of travel and seat/berth details?",
            "What is the PNR number and booking status?",
            "What is the total fare amount and payment details?",
            "What are the coach and seat/berth numbers assigned?",
            "What is the booking date and time for this ticket?",
            "What are the passenger age and gender details mentioned?",
        ]
        queries.extend(train_ticket_queries)
        
        # === SAMPLE QUERY SUBSETS (Comment/Uncomment as needed) ===
        
        # Quick test queries (uncomment for fast testing)
        # quick_test_queries = [
        #     "What is Trykaa?",
        #     "What are AI agents?",
        #     "What is middleware in distributed systems?",
        # ]
        # queries = quick_test_queries  # Replace all queries with quick test
        
        # Business-focused queries only (uncomment to focus on business documents)
        # business_queries = trykaa_queries
        # queries = business_queries
        
        # Technical queries only (uncomment to focus on technical documents)
        # technical_queries = ai_agents_queries + distributed_systems_queries
        # queries = technical_queries
        
        # Single document testing (uncomment and modify as needed)
        # queries = trykaa_queries[:3]  # Test only first 3 Trykaa queries
        # queries = ai_agents_queries[:3]  # Test only first 3 AI agent queries
        
        query_times = await self.run_queries_async(queries)
        self.print_performance_summary(query_times)
        
def main():
    """Main function - runs async test when executed directly."""
    excluded_patterns = [
        # "*.pdf",
        # "*.docx",
        # "*.doc",
        # "*.txt",
        # "*.csv",
        # "*.xls",
        # "*.xlsx",
        # "*.pptx",
        # "*.ppt",
        # "*.jpg",
        # "*.jpeg",
        # "*.png",
        # "*.gif"
        ]
    config = TestConfig(
        model="gpt-4o-mini-2024-07-18",
        chunk_size=512,
        chunk_overlap=50,
        similarity_top_k=3,
        num_workers=2,
        enable_logging=True,
        exclude_patterns=excluded_patterns if len(excluded_patterns) > 0 else None,
        enable_cache=False,
        enable_delay=True,
        delay_seconds=2
    )
    
    print(f"Using Config options: {config}")
    
    runner = RAGTestRunner(config)
    
    # Run async test for better performance
    asyncio.run(runner.run_test_async())

if __name__ == "__main__":
    main()

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