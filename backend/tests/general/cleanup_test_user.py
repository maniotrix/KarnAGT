#!/usr/bin/env python3
"""
Clean up test user from database
"""

import asyncio
import sys

# Add backend to path
sys.path.append('.')

from app.core.database import AsyncSessionLocal
from app.models.database.user import User
from app.models.database.user_memory import UserMemory
from app.models.database.memory_preference import MemoryPreference
from sqlalchemy import delete

async def cleanup_test_user():
    """Clean up test user and related data"""
    
    async with AsyncSessionLocal() as db:
        # Find test user
        from sqlalchemy import select
        result = await db.execute(
            select(User).where(User.email == "bucket_test@example.com")
        )
        test_user = result.scalar_one_or_none()
        
        if test_user:
            user_id = test_user.id
            print(f"Found test user with ID: {user_id}")
            
            # Delete related data
            await db.execute(delete(UserMemory).where(UserMemory.user_id == user_id))
            await db.execute(delete(MemoryPreference).where(MemoryPreference.user_id == user_id))
            await db.execute(delete(User).where(User.id == user_id))
            
            await db.commit()
            print("✅ Test user and related data cleaned up successfully")
        else:
            print("ℹ️  No test user found to clean up")

if __name__ == "__main__":
    asyncio.run(cleanup_test_user()) 