import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User
from app.models.brand import Brand
from app.models.device_category import DeviceCategory
from app.models.ai_provider import AiProvider
from app.models.ai_provider_model import AiProviderModel
from app.models.system_setting import SystemSetting

async def seed_all():
    async with AsyncSessionLocal() as session:
        print("[INFO] Seeding database...")

        # 1. Admin User
        admin = await session.scalar(select(User).where(User.email == "admin@aide.com"))
        if not admin:
            admin = User(
                email="admin@aide.com",
                name="System Administrator",
                hashed_password=get_password_hash("admin123"),
                role="admin",
                status="active",
                tokens=1000000,
                is_active=True,
                is_superuser=True,
            )
            session.add(admin)
            print("  + Created admin user: admin@aide.com / admin123")
        else:
            print("  - Admin user already exists")

        # 2. Test User
        test_user = await session.scalar(select(User).where(User.email == "duytris2003@gmail.com"))
        if not test_user:
            test_user = User(
                email="duytris2003@gmail.com",
                name="Nguyen Duy Tri",
                hashed_password=get_password_hash("Ndt09012003@"),
                role="user",
                status="active",
                tokens=50000,
                is_active=True,
                is_superuser=False,
            )
            session.add(test_user)
            print("  + Created test user: duytris2003@gmail.com")
        else:
            print("  - Test user already exists")

        # 3. Default Brands
        brands_data = ["Schneider Electric", "ABB", "LS Electric", "Mitsubishi Electric", "Chint", "Hyundai"]
        for b_name in brands_data:
            existing = await session.scalar(select(Brand).where(Brand.name == b_name))
            if not existing:
                session.add(Brand(name=b_name))
                print(f"  + Created brand: {b_name}")

        # 4. Default Categories
        categories_data = ["MCCB", "MCB", "ACB", "Contactor", "RCBO", "RCCB", "SPD", "VCB", "Relay", "Thermal Relay"]
        for c_name in categories_data:
            existing = await session.scalar(select(DeviceCategory).where(DeviceCategory.name == c_name))
            if not existing:
                session.add(DeviceCategory(name=c_name))
                print(f"  + Created category: {c_name}")

        # 5. Default AI Providers & Models
        gemini_provider = await session.scalar(select(AiProvider).where(AiProvider.id == "gemini"))
        if not gemini_provider:
            gemini_provider = AiProvider(
                id="gemini",
                name="Google Gemini",
                slug="gemini",
                api_type="google_gemini",
                base_url="https://generativelanguage.googleapis.com",
                is_active=True,
                sort_order=1,
            )
            session.add(gemini_provider)
            await session.flush()
            session.add(AiProviderModel(provider_id="gemini", model_key="gemini-2.5-flash", label="Gemini 2.5 Flash", is_active=True, sort_order=1))
            session.add(AiProviderModel(provider_id="gemini", model_key="gemini-2.5-pro", label="Gemini 2.5 Pro", is_active=True, sort_order=2))
            print("  + Created AI Provider: Google Gemini")

        openai_provider = await session.scalar(select(AiProvider).where(AiProvider.id == "openai"))
        if not openai_provider:
            openai_provider = AiProvider(
                id="openai",
                name="OpenAI",
                slug="openai",
                api_type="openai_compatible",
                base_url="https://api.openai.com/v1",
                is_active=True,
                sort_order=2,
            )
            session.add(openai_provider)
            await session.flush()
            openai_models = [
                ("gpt-6-astra", "GPT-6 Astra"),
                ("gpt-5.6-sol", "GPT-5.6 Sol"),
                ("gpt-5.6-terra", "GPT-5.6 Terra"),
                ("gpt-5.6-luna", "GPT-5.6 Luna"),
                ("gpt-5.5", "GPT-5.5"),
            ]
            for sort_order, (model_key, label) in enumerate(openai_models, start=1):
                session.add(AiProviderModel(
                    provider_id="openai",
                    model_key=model_key,
                    label=label,
                    is_active=True,
                    sort_order=sort_order,
                ))
            print("  + Created AI Provider: OpenAI")

        # 6. Default System Settings
        settings_defaults = {
            "app_title": "He Thong Boc Tach Ban Ve & Lap Du Toan Tu Bang Dien",
            "enclosure_reserve_factor": "0.20",
            "enclosure_step_mm": "50",
            "busbar_material": "copper",
            "vat_rate": "0.10",
        }
        for key, val in settings_defaults.items():
            existing = await session.scalar(select(SystemSetting).where(SystemSetting.key == key))
            if not existing:
                session.add(SystemSetting(key=key, value=val))
                print(f"  + Created setting: {key}")

        await session.commit()
        print("[SUCCESS] Database seeding complete!")

if __name__ == "__main__":
    asyncio.run(seed_all())
