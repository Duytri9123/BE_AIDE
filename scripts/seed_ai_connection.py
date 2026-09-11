import asyncio
import uuid
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.ai_connection import AiConnection

async def seed_ai():
    # Let's check if there is an existing key or we can set it
    async with AsyncSessionLocal() as session:
        stmt = select(AiConnection)
        conns = (await session.execute(stmt)).scalars().all()
        if not conns:
            # Create a default Antigravity / Gemini connection
            # If the user is on the admin page, they will also save their key
            print("AiConnection table is empty. Admin can save connection in UI or seed here.")
        else:
            for c in conns:
                c.is_active = True
                print(f"Connection ID {c.id}: Provider={c.provider}, Model={c.selected_model}, Active={c.is_active}")
            await session.commit()

if __name__ == "__main__":
    asyncio.run(seed_ai())
