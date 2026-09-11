import asyncio
import sys
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.ai_provider import AiProvider
from app.models.ai_provider_model import AiProviderModel

sys.stdout.reconfigure(encoding='utf-8')

async def list_models():
    async with AsyncSessionLocal() as session:
        providers = (await session.execute(select(AiProvider))).scalars().all()
        print("AI Providers in DB:")
        for p in providers:
            print(f"- Provider: id='{p.id}', name='{p.name}', active={p.is_active}")
            models = (await session.execute(select(AiProviderModel).where(AiProviderModel.provider_id == p.id))).scalars().all()
            for m in models:
                print(f"    model_key='{m.model_key}', label='{m.label}'")

if __name__ == "__main__":
    asyncio.run(list_models())
