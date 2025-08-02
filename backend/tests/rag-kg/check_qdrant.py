import asyncio
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import ScrollRequest

async def check_metadata():
    client = AsyncQdrantClient(url='http://localhost:6333')
    
    try:
        # Get the collection name (you may need to adjust this)
        collections = await client.get_collections()
        print('Available collections:')
        for collection in collections.collections:
            print(f'  - {collection.name}')
        
        # Check the specific collection used in the failing test
        target_collection = "conversation_81ded89a-f54f-4ec5-8652-706b7b01ea64_486d2ec5"
        
        print(f'\nChecking metadata structure in collection: {target_collection}')
        
        result = await client.scroll(
            collection_name=target_collection,
            limit=5,
            with_payload=True
        )
        
        for i, point in enumerate(result[0]):
            print(f'\nPoint {i+1}:')
            print(f'  ID: {point.id}')
            if point.payload:
                print(f'  Payload keys: {list(point.payload.keys())}')
                if 'doc_id' in point.payload:
                    print(f'  doc_id: {point.payload["doc_id"]}')
                if 'ref_doc_id' in point.payload:
                    print(f'  ref_doc_id: {point.payload["ref_doc_id"]}')
                if 'status' in point.payload:
                    print(f'  status: {point.payload["status"]}')
                else:
                    print('  status: NOT FOUND')
                if 'file_name' in point.payload:
                    print(f'  file_name: {point.payload["file_name"]}')
                if 'deactivated_at' in point.payload:
                    print(f'  deactivated_at: {point.payload["deactivated_at"]}')
            else:
                print('  No payload found')
    except Exception as e:
        print(f'Error: {e}')

asyncio.run(check_metadata())