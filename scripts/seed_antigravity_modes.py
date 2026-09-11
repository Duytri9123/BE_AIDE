import asyncio
import sys
from sqlalchemy import select, update
from app.db.session import AsyncSessionLocal
from app.models.ai_provider import AiProvider
from app.models.ai_provider_model import AiProviderModel

sys.stdout.reconfigure(encoding='utf-8')

async def seed_antigravity_modes():
    async with AsyncSessionLocal() as session:
        # Check antigravity provider
        prov = (await session.execute(select(AiProvider).where(AiProvider.id == "antigravity"))).scalar_one_or_none()
        if not prov:
            prov = AiProvider(
                id="antigravity",
                name="Antigravity",
                description="Google Antigravity Advanced Agentic AI with Multi-Tier Reasoning",
                is_active=True
            )
            session.add(prov)
            await session.flush()
            
        # Add or update models without deleting existing records. Existing API
        # connections keep their configured model key during this update.
        models_data = [
            # Gemini 3.8 Flash (3 modes)
            ("ag/gemini-3.8-flash-high", "Gemini 3.8 Flash High (Fast, Maximum Reasoning)", 0),
            ("ag/gemini-3.8-flash-medium", "Gemini 3.8 Flash Medium (Balanced Reasoning)", 1),
            ("ag/gemini-3.8-flash-low", "Gemini 3.8 Flash Low (Quick Extraction)", 2),

            # Gemini 3.7 Flash (3 modes)
            ("ag/gemini-3.7-flash-high", "Gemini 3.7 Flash High (Fast, Maximum Reasoning)", 3),
            ("ag/gemini-3.7-flash-medium", "Gemini 3.7 Flash Medium (Balanced Reasoning)", 4),
            ("ag/gemini-3.7-flash-low", "Gemini 3.7 Flash Low (Quick Extraction)", 5),
        ]
        
        for key, label, sort in models_data:
            model = (await session.execute(
                select(AiProviderModel).where(
                    AiProviderModel.provider_id == "antigravity",
                    AiProviderModel.model_key == key,
                )
            )).scalar_one_or_none()
            if model:
                model.label = label
                model.is_active = True
                model.sort_order = sort
            else:
                session.add(AiProviderModel(
                    provider_id="antigravity",
                    model_key=key,
                    label=label,
                    is_active=True,
                    sort_order=sort,
                ))

        # Replace the former single 3.8 entry with the explicit High/Medium/Low
        # modes above, matching the Gemini 3.7 configuration.
        legacy_38 = (await session.execute(
            select(AiProviderModel).where(
                AiProviderModel.provider_id == "antigravity",
                AiProviderModel.model_key == "ag/gemini-3.8-flash",
            )
        )).scalar_one_or_none()
        if legacy_38:
            legacy_38.is_active = False

        # Only current, verified Antigravity Gemini models stay eligible for
        # automatic fallback. Older catalogue entries remain in the database for
        # audit but cannot be selected by the execution pool.
        current_keys = [key for key, _, _ in models_data]
        await session.execute(
            update(AiProviderModel)
            .where(
                AiProviderModel.provider_id == "antigravity",
                AiProviderModel.model_key.not_in(current_keys),
            )
            .values(is_active=False)
        )
            
        await session.commit()
        print("Successfully synced Gemini 3.8/3.7 High, Medium, and Low modes for Antigravity!")

if __name__ == "__main__":
    asyncio.run(seed_antigravity_modes())
