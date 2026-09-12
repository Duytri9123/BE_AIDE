import asyncio
from sqlalchemy import select
from app.db.session import async_engine, AsyncSessionLocal
from app.models.ai_provider import AiProvider
from app.models.ai_provider_model import AiProviderModel
from app.models.ai_connection import AiConnection

# Icon đường dẫn phục vụ từ /admin/static/providers/
DEFAULT_PROVIDERS = [
    {
        "id": "antigravity",
        "name": "Antigravity",
        "slug": "antigravity",
        "api_type": "antigravity_engine",
        "base_url": "https://api.antigravity.google.com/v1",
        "description": "Antigravity AI Engine (Google DeepMind Architecture)",
        "icon": "/admin/static/providers/antigravity.png",
        "is_active": True,
        "sort_order": 0,
        "models": [
            {"model_key": "ag/gemini-3.8-flash-high", "label": "Gemini 3.8 Flash High (Mới nhất, Deep Reasoning, Khuyên dùng)", "sort_order": 0},
            {"model_key": "ag/gemini-3.8-flash-medium", "label": "Gemini 3.8 Flash Medium (Standard)", "sort_order": 1},
            {"model_key": "ag/gemini-3.8-flash-low", "label": "Gemini 3.8 Flash Low (Quick)", "sort_order": 2},
            {"model_key": "ag/gemini-3.7-flash-high", "label": "Gemini 3.7 Flash High (Khuyên dùng)", "sort_order": 3},
            {"model_key": "ag/gemini-3.7-flash-medium", "label": "Gemini 3.7 Flash Medium (Standard)", "sort_order": 4},
            {"model_key": "ag/gemini-3.7-flash-low", "label": "Gemini 3.7 Flash Low (Quick)", "sort_order": 5},
            {"model_key": "ag/gemini-3.6-flash-high", "label": "Gemini 3.6 Flash High", "sort_order": 6},
            {"model_key": "ag/gemini-3.6-flash-medium", "label": "Gemini 3.6 Flash Medium", "sort_order": 7},
            {"model_key": "ag/gemini-3.5-flash", "label": "Gemini 3.5 Flash", "sort_order": 8},
            {"model_key": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6 (Độ chính xác cao)", "sort_order": 9},
            {"model_key": "gpt-oss-120b-medium", "label": "GPT-OSS 120B Medium", "sort_order": 10},
            {"model_key": "gemini-2.5-flash", "label": "Gemini 2.5 Flash", "sort_order": 11},
            {"model_key": "gemini-2.5-pro", "label": "Gemini 2.5 Pro", "sort_order": 12},
        ]
    },
    {
        "id": "codex",
        "name": "Codex / OpenAI API",
        "slug": "codex",
        "api_type": "openai_compatible",
        "base_url": "https://api.openai.com/v1",
        "description": "Kết nối trực tiếp OpenAI API bằng Project API Key",
        "icon": "/admin/static/providers/codex.png",
        "is_active": True,
        "sort_order": 1,
        "models": [
            {"model_key": "gpt-6-astra", "label": "GPT-6 Astra", "sort_order": 1},
            {"model_key": "gpt-5.6-sol", "label": "GPT-5.6 Sol", "sort_order": 2},
            {"model_key": "gpt-5.6-terra", "label": "GPT-5.6 Terra", "sort_order": 3},
            {"model_key": "gpt-5.6-luna", "label": "GPT-5.6 Luna", "sort_order": 4},
            {"model_key": "gpt-5.5", "label": "GPT-5.5", "sort_order": 5},
        ]
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "slug": "openai",
        "api_type": "openai_compatible",
        "base_url": "https://api.openai.com/v1",
        "description": "Các model OpenAI dùng trong Codex — hỗ trợ suy luận, lập trình, hình ảnh và tài liệu kỹ thuật",
        "icon": "/admin/static/providers/openai.png",
        "is_active": True,
        "sort_order": 2,
        "models": [
            {"model_key": "gpt-6-astra", "label": "GPT-6 Astra", "sort_order": 1},
            {"model_key": "gpt-5.6-sol", "label": "GPT-5.6 Sol", "sort_order": 2},
            {"model_key": "gpt-5.6-terra", "label": "GPT-5.6 Terra", "sort_order": 3},
            {"model_key": "gpt-5.6-luna", "label": "GPT-5.6 Luna", "sort_order": 4},
            {"model_key": "gpt-5.5", "label": "GPT-5.5", "sort_order": 5},
        ]
    },
    {
        "id": "anthropic",
        "name": "Anthropic Claude",
        "slug": "anthropic",
        "api_type": "anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "description": "Claude 3.5 Sonnet & Haiku — Đọc hiểu sơ đồ phức tạp và tài liệu kỹ thuật dài",
        "icon": "/admin/static/providers/anthropic.png",
        "is_active": True,
        "sort_order": 3,
        "models": [
            {"model_key": "claude-3-5-sonnet-20241022", "label": "Claude 3.5 Sonnet (Độ chính xác cao nhất)", "sort_order": 1},
            {"model_key": "claude-3-5-haiku-20241022", "label": "Claude 3.5 Haiku", "sort_order": 2},
            {"model_key": "claude-3-opus-20240229", "label": "Claude 3 Opus", "sort_order": 3},
        ]
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "slug": "deepseek",
        "api_type": "openai_compatible",
        "base_url": "https://api.deepseek.com/v1",
        "description": "DeepSeek-V3 & DeepSeek-R1 (Suy luận chuyên sâu, giá rẻ)",
        "icon": "/admin/static/providers/deepseek.png",
        "is_active": True,
        "sort_order": 4,
        "models": [
            {"model_key": "deepseek-chat", "label": "DeepSeek-V3 (Chat & Trích xuất nhanh)", "sort_order": 1},
            {"model_key": "deepseek-reasoner", "label": "DeepSeek-R1 (Suy luận logic & toán học)", "sort_order": 2},
        ]
    },
    {
        "id": "google",
        "name": "Google Gemini",
        "slug": "google",
        "api_type": "google_gemini",
        "base_url": "https://generativelanguage.googleapis.com",
        "description": "Google Gemini Developer API (Sử dụng API Key AIza...)",
        "icon": "/admin/static/providers/google.png",
        "is_active": True,
        "sort_order": 0,
        "models": [
            {"model_key": "gemini-2.5-flash", "label": "Gemini 2.5 Flash (Khuyên dùng)", "sort_order": 1},
            {"model_key": "gemini-2.5-pro", "label": "Gemini 2.5 Pro (Suy luận sâu)", "sort_order": 2},
            {"model_key": "gemini-2.0-flash", "label": "Gemini 2.0 Flash (Tốc độ cao)", "sort_order": 3},
        ]
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "slug": "openrouter",
        "api_type": "openai_compatible",
        "base_url": "https://openrouter.ai/api/v1",
        "description": "Cổng kết nối đa mô hình: Gemini, Claude, GPT, Llama, Qwen",
        "icon": "/admin/static/providers/openrouter.png",
        "is_active": True,
        "sort_order": 5,
        "models": [
            {"model_key": "google/gemini-2.0-flash-001", "label": "Gemini 2.0 Flash (qua OpenRouter)", "sort_order": 1},
            {"model_key": "anthropic/claude-3.5-sonnet", "label": "Claude 3.5 Sonnet (qua OpenRouter)", "sort_order": 2},
            {"model_key": "openai/gpt-4o", "label": "GPT-4o (qua OpenRouter)", "sort_order": 3},
            {"model_key": "deepseek/deepseek-chat", "label": "DeepSeek-V3 (qua OpenRouter)", "sort_order": 4},
        ]
    },
    {
        "id": "groq",
        "name": "Groq",
        "slug": "groq",
        "api_type": "openai_compatible",
        "base_url": "https://api.groq.com/openai/v1",
        "description": "Groq LPU — Tốc độ suy luận cực nhanh, phù hợp phân tích realtime",
        "icon": "/admin/static/providers/groq.png",
        "is_active": True,
        "sort_order": 6,
        "models": [
            {"model_key": "llama-3.3-70b-versatile", "label": "Llama 3.3 70B (Groq)", "sort_order": 1},
            {"model_key": "llama-3.1-8b-instant", "label": "Llama 3.1 8B Instant (Groq)", "sort_order": 2},
            {"model_key": "mixtral-8x7b-32768", "label": "Mixtral 8x7B (Groq)", "sort_order": 3},
        ]
    },
    {
        "id": "mistral",
        "name": "Mistral AI",
        "slug": "mistral",
        "api_type": "openai_compatible",
        "base_url": "https://api.mistral.ai/v1",
        "description": "Mistral Large / Small — Hiệu quả chi phí tốt, hỗ trợ tiếng Pháp và tiếng Anh",
        "icon": "/admin/static/providers/mistral.png",
        "is_active": True,
        "sort_order": 7,
        "models": [
            {"model_key": "mistral-large-latest", "label": "Mistral Large Latest", "sort_order": 1},
            {"model_key": "mistral-small-latest", "label": "Mistral Small Latest", "sort_order": 2},
            {"model_key": "codestral-latest", "label": "Codestral (Code)", "sort_order": 3},
        ]
    },
    {
        "id": "ollama",
        "name": "Ollama",
        "slug": "ollama",
        "api_type": "openai_compatible",
        "base_url": "http://localhost:11434/v1",
        "description": "Chạy mô hình AI cục bộ (offline) — Không tốn token, bảo mật tuyệt đối",
        "icon": "/admin/static/providers/ollama.png",
        "is_active": True,
        "sort_order": 8,
        "models": [
            {"model_key": "llama3.1:8b", "label": "Llama 3.1 8B (Local)", "sort_order": 1},
            {"model_key": "qwen2.5:7b", "label": "Qwen 2.5 7B (Local)", "sort_order": 2},
            {"model_key": "mistral:7b", "label": "Mistral 7B (Local)", "sort_order": 3},
        ]
    },
    {
        "id": "xai",
        "name": "xAI",
        "slug": "xai",
        "api_type": "openai_compatible",
        "base_url": "https://api.x.ai/v1",
        "description": "Grok 2 / Grok Vision — Mô hình đa phương thức mạnh mẽ từ xAI (Elon Musk)",
        "icon": "/admin/static/providers/xai.png",
        "is_active": True,
        "sort_order": 9,
        "models": [
            {"model_key": "grok-2-vision-1212", "label": "Grok 2 Vision (Multi-modal)", "sort_order": 1},
            {"model_key": "grok-2-1212", "label": "Grok 2 (Text)", "sort_order": 2},
        ]
    },
]

async def update_provider_icons():
    async with AsyncSessionLocal() as session:
        for provider_data in DEFAULT_PROVIDERS:
            # Không thay đổi DEFAULT_PROVIDERS tại chỗ để hàm có thể chạy lặp lại
            # an toàn trong cùng một process.
            p_data = {k: v for k, v in provider_data.items() if k != "models"}
            models_data = provider_data.get("models", [])
            
            # Check if provider exists
            res = await session.execute(select(AiProvider).where(AiProvider.id == p_data["id"]))
            provider = res.scalar_one_or_none()
            
            if not provider:
                provider = AiProvider(**p_data)
                session.add(provider)
                await session.flush()
                print(f"[NEW] Provider: {provider.name}")
            else:
                # Update icon and description
                provider.icon = p_data["icon"]
                provider.description = p_data.get("description", provider.description)
                print(f"[UPDATE] Provider: {provider.name} -> icon set")

            # Thêm model mới và đồng bộ lại nhãn/thứ tự cho model đã tồn tại.
            for m in models_data:
                res_m = await session.execute(
                    select(AiProviderModel).where(
                        AiProviderModel.provider_id == provider.id,
                        AiProviderModel.model_key == m["model_key"]
                    )
                )
                model_obj = res_m.scalar_one_or_none()
                if not model_obj:
                    model_obj = AiProviderModel(provider_id=provider.id, **m)
                    session.add(model_obj)
                    print(f"  [NEW] Model: {m['model_key']}")
                else:
                    model_obj.label = m["label"]
                    model_obj.sort_order = m["sort_order"]
                    model_obj.is_active = True

        await session.commit()
        print("\nDone! All providers & icons updated in DB.")

if __name__ == "__main__":
    asyncio.run(update_provider_icons())
