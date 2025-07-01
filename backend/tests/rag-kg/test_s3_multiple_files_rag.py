import os
from dotenv import load_dotenv
import uuid
from datetime import datetime
import asyncio
from typing import List, Dict, Any

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))

import sys
sys.path.append(backend_dir)

from app.services.knowledge.rag_service import RAGService, QueryWithResult
from app.services.knowledge.config import RAGConfig, QdrantConfig
from app.services.storage.storage import S3StorageBackend, get_content_type, generate_file_id, generate_storage_key
from app.utils.profiler_util import PerformanceMonitor

load_dotenv()

def print_performance_summary(perf_monitor: PerformanceMonitor, query_times: List[float]) -> None:
    """Print comprehensive performance summary like test_rag_service.py."""
    print(f"\n🎉 S3 RAG test completed!")
    
    print(f"\n📊 PERFORMANCE SUMMARY:")
    print(f"=" * 60)
    summary = perf_monitor.get_summary()
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

async def test_s3_multiple_files_rag():
    """Main test function for multiple S3 files RAG using existing codebase components."""
    
    print("🚀 Starting S3 Multiple Files RAG Test")
    print("=" * 60)
    
    # Use existing PerformanceMonitor from profiler_util.py
    perf_monitor = PerformanceMonitor()
    perf_monitor.print_system_info()
    
    # Initialize configurations using existing classes
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
    rag_config = RAGConfig(
        s3_bucket_name="test-rag-bucket",
        exclude_patterns=excluded_patterns if len(excluded_patterns) > 0 else None,
    )
    
    qdrant_config = QdrantConfig(
        url="http://localhost:6333",
        collection_name=f"test_multifile_{uuid.uuid4().hex[:8]}"
    )
    
    print(f"📋 Configuration:")
    print(f"   S3 Bucket: {rag_config.s3_bucket_name}")
    print(f"   Qdrant Collection: {qdrant_config.collection_name}")
    print(f"   Chunk Size: {rag_config.chunk_size}")
    print(f"   Top K: {rag_config.similarity_top_k}")
    print()
    
    # Initialize RAG service - use existing service
    rag_service = RAGService(rag_config)
    uploaded_s3_keys = []
    
    try:
        # Phase 1: Upload ALL files to S3
        perf_monitor.start_timing("S3 Upload")
        
        uploaded_s3_keys = await upload_all_test_files_to_s3(rag_config)
        upload_duration = perf_monitor.end_timing("S3 Upload")
        
        if not uploaded_s3_keys:
            print("❌ No files uploaded. Exiting test.")
            return
        
        # Phase 2: Get index from S3 using existing RAG service method
        perf_monitor.start_timing("Document Indexing/Loading")
        
        print("🔧 Setting up vector store and creating index from S3...")
        index = await rag_service.get_query_index_from_s3(
            rag_config.s3_bucket_name, 
            uploaded_s3_keys, 
            qdrant_config,
            add_s3_metadata=False
        )
        print(f"✅ Created index from S3 documents")
        
        index_duration = perf_monitor.end_timing("Document Indexing/Loading")
        
        # Phase 3: Run queries one by one (same as test_rag_service.py)
        perf_monitor.start_timing("Query Processing")
        
        # Use exact same queries as test_rag_llamaindex_with_vectordb.py for consistency
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
        
        # Run queries one by one like test_rag_service.py
        print(f"🔍 Running {len(queries)} test queries one by one...")
        query_times = []
        
        for i, query in enumerate(queries, 1):
            import time as time_module
            # Time individual query
            query_start = time_module.time()
            
            query_results: List[QueryWithResult] = await rag_service.get_query_results_from_index(index, [query])
            
            query_end = time_module.time()
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
        
        query_duration = perf_monitor.end_timing("Query Processing")
        
        # Print performance summary using the same format as test_rag_service.py
        print_performance_summary(perf_monitor, query_times)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        print(f"Error traceback:\n{traceback.format_exc()}")
        
    finally:
        # Always cleanup resources using existing cleanup functions
        print("\n🧹 Starting cleanup...")
        perf_monitor.start_timing("Cleanup")
        
        await cleanup_s3_files(uploaded_s3_keys, rag_config.s3_bucket_name)
        await cleanup_qdrant_collection(qdrant_config)
        
        perf_monitor.end_timing("Cleanup")
        print("✅ All cleanup completed")

def test_s3_files_availability():
    """Test that test_docs directory exists and has files."""
    print("🔍 Checking test_docs directory availability...")
    
    test_docs_dir = os.path.join(backend_dir, "test_docs")
    
    if not os.path.exists(test_docs_dir):
        print(f"❌ test_docs directory not found: {test_docs_dir}")
        return False
        
    # Get all files from test_docs directory
    all_files = []
    for filename in os.listdir(test_docs_dir):
        file_path = os.path.join(test_docs_dir, filename)
        if os.path.isfile(file_path):
            size_mb = os.path.getsize(file_path) / 1024 / 1024
            all_files.append((filename, size_mb))
            print(f"   ✅ {filename} ({size_mb:.2f} MB)")
    
    print(f"\n📊 File Availability Summary:")
    print(f"   📁 Directory: {test_docs_dir}")
    print(f"   📄 Total Files: {len(all_files)}")
    
    if len(all_files) == 0:
        print("❌ No files found in test_docs directory")
        return False
    
    return True

if __name__ == "__main__":
    async def run_all_tests():
        print("🚀 Running S3 Multiple Files RAG Tests")
        print("=" * 60)
        
        # Test 1: Check file availability
        if not test_s3_files_availability():
            print("❌ No test files available. Exiting.")
            return
        
        print("\n" + "=" * 60)
        
        # Test 2: Main RAG test using existing codebase components
        await test_s3_multiple_files_rag()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
    
    asyncio.run(run_all_tests()) 