import asyncio
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import ScrollRequest, Filter, FieldCondition, MatchValue

async def test_status_filtering():
    client = AsyncQdrantClient(url='http://localhost:6333')
    
    try:
        collection_name = 'conversation_81ded89a-f54f-4ec5-8652-706b7b01ea64_486d2ec5'
        
        print(f"Testing status filtering in collection: {collection_name}")
        print("-" * 60)
        
        # Query for active documents
        active_filter = Filter(
            must=[
                FieldCondition(
                    key="status",
                    match=MatchValue(value="active")
                )
            ]
        )
        
        result_active = await client.scroll(
            collection_name=collection_name,
            limit=10,
            with_payload=True,
            scroll_filter=active_filter
        )
        
        print(f"🟢 ACTIVE documents found: {len(result_active[0])}")
        for i, point in enumerate(result_active[0]):
            if point.payload:
                print(f"  {i+1}. doc_id: {point.payload.get('doc_id', 'N/A')}")
                print(f"     file_name: {point.payload.get('file_name', 'N/A')}")
                print(f"     status: {point.payload.get('status', 'N/A')}")
        
        print()
        
        # Query for inactive documents
        inactive_filter = Filter(
            must=[
                FieldCondition(
                    key="status",
                    match=MatchValue(value="inactive")
                )
            ]
        )
        
        result_inactive = await client.scroll(
            collection_name=collection_name,
            limit=10,
            with_payload=True,
            scroll_filter=inactive_filter
        )
        
        print(f"🔴 INACTIVE documents found: {len(result_inactive[0])}")
        for i, point in enumerate(result_inactive[0]):
            if point.payload:
                print(f"  {i+1}. doc_id: {point.payload.get('doc_id', 'N/A')}")
                print(f"     file_name: {point.payload.get('file_name', 'N/A')}")
                print(f"     status: {point.payload.get('status', 'N/A')}")
                print(f"     deactivated_at: {point.payload.get('deactivated_at', 'N/A')}")
        
        print()
        
        # Query for all documents
        result_all = await client.scroll(
            collection_name=collection_name,
            limit=10,
            with_payload=True
        )
        
        print(f"📊 TOTAL documents found: {len(result_all[0])}")
        
        # Count by status
        status_counts = {}
        for point in result_all[0]:
            if point.payload:
                status = point.payload.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"Status breakdown: {status_counts}")
        
        # Test specific document IDs from the logs
        test_doc_ids = [
            'a0f7786a-d2d4-4688-b261-e7ff62325905',
            '566cc837-5196-4d5e-b2e1-06c5504510e9', 
            '6a3df3df-187b-4e7b-b2ba-da2b9ad8d61c'
        ]
        
        print(f"\n🔍 Testing specific document IDs from logs:")
        for doc_id in test_doc_ids:
            doc_filter = Filter(
                must=[
                    FieldCondition(
                        key="doc_id",
                        match=MatchValue(value=doc_id)
                    )
                ]
            )
            
            result = await client.scroll(
                collection_name=collection_name,
                limit=5,
                with_payload=True,
                scroll_filter=doc_filter
            )
            
            if result[0]:
                point = result[0][0]
                if point.payload:
                    print(f"  doc_id: {doc_id}")
                    print(f"  status: {point.payload.get('status', 'N/A')}")
                    print(f"  file_name: {point.payload.get('file_name', 'N/A')}")
                    print(f"  deactivated_at: {point.payload.get('deactivated_at', 'N/A')}")
                    print()
        
    except Exception as e:
        print(f'Error: {e}')

asyncio.run(test_status_filtering()) 