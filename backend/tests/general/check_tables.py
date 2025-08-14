#!/usr/bin/env python3
import asyncio
import sys
sys.path.append('.')

from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def check_tables():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        tables = [row[0] for row in result.fetchall()]
        print('Available tables:', tables)
        
        # Check for specific tables
        expected_tables = ['users', 'conversations', 'messages', 'uploaded_images', 'cost_tracking', 'memory_preferences', 'user_memories', 'knowledge_files']
        
        for table in expected_tables:
            if table in tables:
                print(f"✅ {table} table exists")
            else:
                print(f"❌ {table} table missing")

if __name__ == "__main__":
    asyncio.run(check_tables()) 