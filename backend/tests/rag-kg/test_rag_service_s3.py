from typing import List
import os
import time
import asyncio
from dotenv import load_dotenv
import uuid

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))

import sys
sys.path.append(backend_dir)

from app.services.knowledge.rag_service import RAGService, QueryWithResult
from app.services.knowledge.config import RAGConfig, get_default_qdrant_config, QdrantConfig
from app.utils.profiler_util import PerformanceMonitor
from app.services.storage.storage import S3StorageBackend, generate_file_id, generate_storage_key, get_content_type

load_dotenv()

async def upload_all_test_files_to_s3(rag_config: RAGConfig) -> List[str]:
    """Upload ALL files from test_docs directory to S3 and return their S3 keys."""
    
    test_docs_dir = os.path.join(backend_dir, "test_docs")
    s3_storage_backend = S3StorageBackend(bucket_name=rag_config.s3_bucket_name)
    
    # Get all files from test_docs directory
    all_files = []
    if os.path.exists(test_docs_dir):
        for filename in os.listdir(test_docs_dir):
            file_path = os.path.join(test_docs_dir, filename)
            if os.path.isfile(file_path):  # Only include files, not directories
                all_files.append(filename)
    
    print(f"📤 Uploading ALL {len(all_files)} test files from test_docs to S3...")
    
    # Clear bucket first and ensure it exists
    print("🧹 Clearing and ensuring bucket exists...")
    await s3_storage_backend.ensure_bucket_exists()
    s3_storage_backend.clear_bucket(rag_config.s3_bucket_name)
    
    uploaded_keys = []
    
    for filename in all_files:
        file_path = os.path.join(test_docs_dir, filename)
        
        # Use existing functions from storage.py
        file_id = generate_file_id()
        s3_key = generate_storage_key(file_id, filename)
        content_type = get_content_type(file_path)
        
        # Upload file to S3
        print(f"   📄 Uploading: {filename} -> {s3_key}")
        await s3_storage_backend.upload_file_direct(file_path, s3_key, content_type)
        uploaded_keys.append(s3_key)
        
        # Verify file exists
        try:
            response = s3_storage_backend.s3_client.head_object(
                Bucket=rag_config.s3_bucket_name, 
                Key=s3_key
            )
            size_mb = response.get('ContentLength', 0) / 1024 / 1024
            print(f"     ✅ Verified: {size_mb:.2f} MB")
        except Exception as e:
            print(f"     ❌ Verification failed: {e}")
            
    print(f"✅ Successfully uploaded {len(uploaded_keys)} files")
    
    # Wait for eventual consistency
    print("⏳ Waiting for S3 eventual consistency...")
    await asyncio.sleep(3)
    
    return uploaded_keys

async def cleanup_s3_files(s3_keys: List[str], bucket_name: str):
    """Clean up uploaded S3 files using existing storage backend."""
    if not s3_keys:
        return
        
    print(f"🧹 Cleaning up {len(s3_keys)} S3 files...")
    s3_storage_backend = S3StorageBackend(bucket_name=bucket_name)
    
    for s3_key in s3_keys:
        try:
            await s3_storage_backend.delete_file(s3_key)
            print(f"   🗑️  Deleted: {s3_key}")
        except Exception as e:
            print(f"   ❌ Failed to delete {s3_key}: {e}")
            
    print("✅ S3 cleanup completed")


async def cleanup_qdrant_collection(qdrant_config: QdrantConfig):
    """Clean up Qdrant collection using existing client."""
    print("🧹 Cleaning up Qdrant collection...")
    
    try:
        from qdrant_client import AsyncQdrantClient
        aclient = AsyncQdrantClient(url=qdrant_config.url)
        await aclient.delete_collection(qdrant_config.collection_name)
        print(f"   🗑️  Deleted collection: {qdrant_config.collection_name}")
    except Exception as e:
        print(f"   ⚠️  Collection cleanup warning: {e}")
    
    print("✅ Qdrant cleanup completed")

class RAGTestRunner:
    """Main class for running RAG performance tests."""
    
    def __init__(self, config: RAGConfig):
        self.rag_config = config
        self.rag_service = RAGService(config)
        self.perf_monitor = PerformanceMonitor()
        
        # clear s3 bucket
        s3_storage_backend = S3StorageBackend(bucket_name=self.rag_config.s3_bucket_name)
        s3_storage_backend.clear_bucket(self.rag_config.s3_bucket_name)
        
    
    def print_performance_summary(self, query_times: List[float]) -> None:
        """Print comprehensive performance summary."""
        print(f"\n🎉 LlamaIndex RAG test completed!")
        
        print(f"\n📊 PERFORMANCE SUMMARY:")
        print(f"=" * 60)
        summary = self.perf_monitor.get_summary()
        total_time = summary.get('total_time', 0)
        print(f"⏱️  Total Execution Time: {total_time:.3f}s")
        
        # Timing breakdown
        print(f"\n⏱️  Detailed Timing Breakdown:")
        operations_dict = summary.get('operations', {})
        
        if operations_dict and total_time > 0:
            for operation, duration in operations_dict.items():
                if isinstance(duration, (int, float)) and duration > 0:
                    percentage = (duration / total_time) * 100
                    print(f"   • {operation}: {duration:.3f}s ({percentage:.1f}%)")
        else:
            print("   • No detailed timing data available")
        
        # Query performance
        if query_times:
            total_query_time = sum(query_times)
            avg_query_time = total_query_time / len(query_times)
            min_query_time = min(query_times)
            max_query_time = max(query_times)
            
            print(f"\n⚡ Query Performance:")
            print(f"   • Total Queries: {len(query_times)}")
            print(f"   • Total Query Time: {total_query_time:.3f}s")
            print(f"   • Average Query Time: {avg_query_time:.3f}s")
            print(f"   • Fastest Query: {min_query_time:.3f}s")
            print(f"   • Slowest Query: {max_query_time:.3f}s")
            print(f"   • Queries per Second: {1/avg_query_time:.2f}")
        else:
            print(f"\n⚡ Query Performance: No queries executed")
        
        
        # Model config
        print(f"\n🧠 Model Configuration:")
        print(f"   • LLM: {self.rag_config.llm_model}")
        print(f"   • Embedding Model: {type(self.rag_config.embedding_model).__name__}")
        print(f"   • Chunk Size: {self.rag_config.chunk_size}")
        print(f"   • Chunk Overlap: {self.rag_config.chunk_overlap}")
        
        # Performance insights
        print(f"\n💡 Performance Insights:")
        if operations_dict:
            indexing_time = operations_dict.get("Document Indexing/Loading", 0)
            query_time = operations_dict.get("Query Processing", 0)
            
            if indexing_time > 0 and query_time > 0:
                ratio = indexing_time / query_time
                print(f"   • Index/Query time ratio: {ratio:.1f}:1")
                if ratio > 10:
                    print(f"   • 🔍 Index creation dominates - consider caching")
                elif ratio < 2:
                    print(f"   • ⚡ Well-balanced performance")
            
            if query_times and len(query_times) > 1:
                query_avg = sum(query_times) / len(query_times)
                variance = sum((t - query_avg)**2 for t in query_times) / len(query_times)
                std_dev = variance ** 0.5
                if std_dev / query_avg > 0.5:
                    print(f"   • ⚠️  High query time variability (std: {std_dev:.3f}s)")
                else:
                    print(f"   • ✅ Consistent query performance")
        else:
            print(f"   • No performance data available for analysis")
    
    async def run_test_async(self) -> None:
        """Run the complete test asynchronously."""
        self.perf_monitor.print_system_info()
        
        # Start timing for index creation/loading
        self.perf_monitor.start_timing("Document Indexing/Loading")
        
        # Run queries - organized by document for easy commenting
        queries = []
        
        # === TRYKAA QUERIES ===
        # Queries for Trykaa business documents (Strategic Deep Dive, Pitch Deck, Transforming Future)
        # trykaa_queries = [
        #     "What is Trykaa and what does the company do?",
        #     "What do customer reviews say about Trykaa? What are the ratings and feedback?",
        #     "What is Trykaa's business model and revenue strategy?",
        #     "What are Trykaa's key competitive advantages in the fashion retail space?",
        #     "What are the main challenges Trykaa faces in the online fashion market?",
        #     "What is Trykaa's target market and customer demographics?",
        #     "What technology solutions does Trykaa use for their platform?",
        #     "What are Trykaa's future growth plans and expansion strategies?",
        #     "What is Trykaa's market positioning compared to competitors?",
        #     "What are the key metrics and KPIs mentioned for Trykaa's performance?",
        # ]
        # queries.extend(trykaa_queries)
        
        # # === AI AGENTS QUERIES ===
        # # Queries for "Comparing a Human Cell to AI Agents" and "Practical Guide to Building Agents"
        # ai_agents_queries = [
        #     "What are the key similarities between human cells and AI agents?",
        #     "What are the projected differences between AI agents in 2025 vs 2035?",
        #     "What are the main components of an AI agent architecture?",
        #     "What are the best practices for building AI agents?",
        #     "What are the different types of AI agents mentioned in the documents?",
        #     "What are the key challenges in building effective AI agents?",
        #     "How do AI agents handle decision-making processes?",
        #     "What are the ethical considerations for AI agent development?",
        #     "What tools and frameworks are recommended for building AI agents?",
        #     "What are the performance metrics for evaluating AI agents?",
        # ]
        # queries.extend(ai_agents_queries)
        
        # # === DISTRIBUTED SYSTEMS QUERIES ===
        # # Queries for "Assignment 6: Distributed Systems (Middleware)"
        # distributed_systems_queries = [
        #     "What are the key concepts of distributed systems middleware?",
        #     "What are the main types of middleware discussed in the assignment?",
        #     "What are the advantages and disadvantages of different middleware approaches?",
        #     "What are the common patterns in distributed systems architecture?",
        #     "What are the key challenges in implementing distributed systems?",
        #     "What are the performance considerations for distributed systems middleware?",
        #     "What are the security aspects of distributed systems mentioned?",
        #     "What are the fault tolerance mechanisms in distributed systems?",
        #     "What are the scalability strategies for distributed systems?",
        #     "What are the communication protocols used in distributed systems?",
        # ]
        # queries.extend(distributed_systems_queries)
        
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
        
        # Get the index (this is where most of the time is spent on first run)
        qdrant_config = get_default_qdrant_config(collection_name=f"test_rag_service_{uuid.uuid4().hex[:8]}")
        uploaded_s3_keys = await upload_all_test_files_to_s3(self.rag_config)
        print(f"✅ Uploaded {len(uploaded_s3_keys)} files to S3")
        index = await self.rag_service.get_query_index_from_s3(self.rag_config.s3_bucket_name, 
                                                            uploaded_s3_keys, qdrant_config, 
                                                            add_s3_metadata=False)
        print(f"✅ Created index from S3 documents")
        
        # End timing for index creation/loading
        index_time = self.perf_monitor.end_timing("Document Indexing/Loading")
        
        # Start timing for query processing
        self.perf_monitor.start_timing("Query Processing")
        
        query_times = []
        for i, query in enumerate(queries, 1):
            # Time individual query
            query_start = time.time()
            
            query_results : List[QueryWithResult] = await self.rag_service.get_query_results_from_index(index, [query])
            
            query_end = time.time()
            individual_query_time = query_end - query_start
            query_times.append(individual_query_time)
            
            print(f"Query {i}: {query}")
            print(f"Query Result: {query_results[0].result}")
            print(f"⏱️  Query Time: {individual_query_time:.3f}s")
            
            if hasattr(query_results[0].result, 'source_nodes') and query_results[0].result.source_nodes:
                print(f"📚 Sources ({len(query_results[0].result.source_nodes)} found):")
                for j, node in enumerate(query_results[0].result.source_nodes[:3], 1):
                    source_file = node.metadata.get('file_name', 'Unknown')
                    source_text = node.text[:100].replace('\n', ' ') + '...'
                    print(f"   {j}. {source_file}: {source_text}")
            else:
                print("📚 No sources found")
            print("-" * 60)
            
        # End timing for query processing
        self.perf_monitor.end_timing("Query Processing")
        
        self.print_performance_summary(query_times)
        
        # Cleanup S3 files
        await cleanup_s3_files(uploaded_s3_keys, self.rag_config.s3_bucket_name)
        print("✅ S3 cleanup completed")
        
        # Cleanup Qdrant collection
        await cleanup_qdrant_collection(qdrant_config)
        print("✅ Qdrant cleanup completed")

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
        "*.pptx",
        "*.ppt",
        # "*.jpg",
        # "*.jpeg",
        # "*.png",
        # "*.gif"
        ]
    
    # Use robust configuration that handles metadata variations and ensures comprehensive retrieval
    config = RAGConfig.for_robust_retrieval(
        s3_bucket_name="test-rag-bucket",
        enable_logging=True,
        exclude_patterns=excluded_patterns if len(excluded_patterns) > 0 else None,
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