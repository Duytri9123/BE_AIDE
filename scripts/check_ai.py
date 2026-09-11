import asyncio
import os
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.ai_connection import AiConnection

async def main():
    async with AsyncSessionLocal() as session:
        stmt = select(AiConnection)
        result = await session.execute(stmt)
        connections = result.scalars().all()
        print("AI Connections in DB:")
        for c in connections:
            print(f"ID: {c.id}, Provider: {c.provider}, Model: {c.selected_model}, Active: {c.is_active}, Key: {c.api_key[:10] if c.api_key else 'None'}")
        
    print("\nEnvironment AI Keys:")
    for k in ["OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY"]:
        val = os.environ.get(k)
        print(f"{k}: {'Exists (' + val[:8] + '...)' if val else 'Not Set'}")

if __name__ == "__main__":
    asyncio.run(main())
