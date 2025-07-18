import asyncio
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import ScrollRequest, Filter, FieldCondition, MatchValue

async def test_all_document_statuses():
    """Test all document statuses in Qdrant to find mixed status issues."""
    
    client = AsyncQdrantClient(url='http://localhost:6333')
    
    try:
        collection_name = 'conversation_81ded89a-f54f-4ec5-8652-706b7b01ea64_486d2ec5'
        
        print(f"Testing ALL document statuses in collection: {collection_name}")
        print("=" * 70)
        
        # Get ALL documents with pagination
        all_points = []
        next_page_offset = None
        
        while True:
            result = await client.scroll(
                collection_name=collection_name,
                limit=100,
                offset=next_page_offset,
                with_payload=True
            )
            
            points, next_page_offset = result
            all_points.extend(points)
            
            if next_page_offset is None:
                break
        
        print(f"📊 Total documents found: {len(all_points)}")
        print()
        
        # Analyze status distribution
        status_counts = {}
        status_by_doc_id = {}
        
        for point in all_points:
            if point.payload:
                status = point.payload.get('status', 'unknown')
                doc_id = point.payload.get('doc_id', 'unknown')
                file_name = point.payload.get('file_name', 'unknown')
                
                # Count by status
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Track by doc_id
                if doc_id not in status_by_doc_id:
                    status_by_doc_id[doc_id] = {
                        'file_name': file_name,
                        'statuses': [],
                        'chunks': []
                    }
                
                status_by_doc_id[doc_id]['statuses'].append(status)
                status_by_doc_id[doc_id]['chunks'].append({
                    'id': point.id,
                    'status': status,
                    'deactivated_at': point.payload.get('deactivated_at', 'N/A')
                })
        
        print("📊 Status Distribution:")
        for status, count in status_counts.items():
            print(f"  {status}: {count} chunks")
        
        print()
        print("📊 Document Analysis:")
        
        for doc_id, info in status_by_doc_id.items():
            unique_statuses = list(set(info['statuses']))
            print(f"  Doc ID: {doc_id}")
            print(f"  File: {info['file_name']}")
            print(f"  Unique statuses: {unique_statuses}")
            print(f"  Total chunks: {len(info['chunks'])}")
            
            # Check for mixed statuses
            if len(unique_statuses) > 1:
                print(f"  ⚠️  MIXED STATUS DETECTED!")
                for chunk in info['chunks']:
                    print(f"    Chunk {chunk['id']}: {chunk['status']} (deactivated: {chunk['deactivated_at']})")
            
            print()
        
        # Check specific document IDs from the logs
        test_doc_ids = [
            'a0f7786a-d2d4-4688-b261-e7ff62325905',
            '566cc837-5196-4d5e-b2e1-06c5504510e9', 
            '6a3df3df-187b-4e7b-b2ba-da2b9ad8d61c'
        ]
        
        print("🔍 Checking specific document IDs from logs:")
        for doc_id in test_doc_ids:
            if doc_id in status_by_doc_id:
                info = status_by_doc_id[doc_id]
                print(f"  {doc_id}: {info['file_name']} - {len(info['chunks'])} chunks")
                unique_statuses = list(set(info['statuses']))
                print(f"    Statuses: {unique_statuses}")
                
                # Show first few chunks
                for i, chunk in enumerate(info['chunks'][:3]):
                    print(f"    Chunk {i+1}: {chunk['status']} (deactivated: {chunk['deactivated_at']})")
                if len(info['chunks']) > 3:
                    print(f"    ... and {len(info['chunks']) - 3} more chunks")
                print()
            else:
                print(f"  {doc_id}: NOT FOUND")
        
        # Test query with similarity to understand what LlamaIndex is getting
        print("🔍 Testing direct Qdrant query with similarity search:")
        
        # This simulates what LlamaIndex might be doing
        from qdrant_client.models import VectorParams, Distance
        
        # Create a dummy vector (we can't actually run similarity search without embeddings)
        # But we can check what the first few results would be
        
        dummy_result = await client.scroll(
            collection_name=collection_name,
            limit=5,
            with_payload=True
        )
        
        print("First 5 documents (simulating similarity search):")
        for i, point in enumerate(dummy_result[0]):
            if point.payload:
                print(f"  {i+1}. ID: {point.id}")
                print(f"     doc_id: {point.payload.get('doc_id', 'N/A')}")
                print(f"     status: {point.payload.get('status', 'N/A')}")
                print(f"     file_name: {point.payload.get('file_name', 'N/A')}")
                print(f"     deactivated_at: {point.payload.get('deactivated_at', 'N/A')}")
                print()
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

asyncio.run(test_all_document_statuses()) 