import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.database.message import Message
from sqlalchemy import select
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Use correct database credentials from docker-compose.yml
DATABASE_URL = "postgresql+asyncpg://app_local_user:app_local_password@localhost:5432/app_local_db"
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def check_tool_calls():
    async with async_session() as session:
        # Get the latest assistant message
        result = await session.execute(
            select(Message)
            .where(Message.role == 'assistant')
            .order_by(Message.created_at.desc())
            .limit(5)
        )
        messages = result.scalars().all()
        
        print(f'Found {len(messages)} recent assistant messages:')
        for i, msg in enumerate(messages):
            print(f'{i+1}. Message ID: {msg.message_id}')
            print(f'   Role: {msg.role}')
            print(f'   Content preview: {msg.content[:100]}...' if msg.content else 'No content')
            print(f'   Tool calls: {msg.tool_calls}')
            print(f'   Created: {msg.created_at}')
            print('---')

if __name__ == "__main__":
    asyncio.run(check_tool_calls())