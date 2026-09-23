"""
Admin helper API routes - Test AI connections & Models.
Provides live testing of API Keys and Model outputs with latency measurement.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from typing import Optional, List
import httpx
import time
import json
import os
import uuid
import re

from app.db.session import get_db
from app.models.ai_connection import AiConnection
from app.models.ai_provider import AiProvider
from app.models.ai_provider_model import AiProviderModel
from app.core.config import settings
from app.services.ai.vision_analyzer import antigravity_thinking_config, normalize_antigravity_model
from app.services.ai.web_search_service import WebSearchService
from app.services.ai.token_refresh_service import TokenRefreshService

router = APIRouter(prefix="/admin-api", tags=["Admin Helpers"])


class TestConnectionRequest(BaseModel):
    connection_id: Optional[str] = None
    provider_id: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    prompt: Optional[str] = None
    base_url: Optional[str] = None
    auth_type: Optional[str] = None


class TestConnectionResponse(BaseModel):
    success: bool
    message: str
    provider: Optional[str] = None
    model_used: Optional[str] = None
    response_text: Optional[str] = None
    latency_ms: Optional[int] = None


class DetectKeyRequest(BaseModel):
    raw_key: Optional[str] = None
    key: Optional[str] = None

    def get_raw_key(self) -> str:
        return (self.raw_key or self.key or "").strip()


class DetectKeyResponse(BaseModel):
    detected: bool
    provider_id: Optional[str] = None
    provider: Optional[str] = None
    provider_name: Optional[str] = None
    auth_type: Optional[str] = None
    format_name: str
    suggested_model: Optional[str] = None
    base_url: Optional[str] = None
    note: Optional[str] = None

    def __init__(self, **data):
        if "provider_id" in data and "provider" not in data:
            data["provider"] = data["provider_id"]
        elif "provider" in data and "provider_id" not in data:
            data["provider_id"] = data["provider"]
        super().__init__(**data)


async def _refresh_google_oauth_token(refresh_token: str, client_id: str = None, client_secret: str = None) -> str:
    """Đổi Google OAuth Refresh Token (1//...) lấy Access Token (ya29...) mới nhất qua TokenRefreshService."""
    return await TokenRefreshService.get_active_token(refresh_token, client_id=client_id, client_secret=client_secret)


async def _call_openai_compatible(base_url: str, api_key: str, model: str, prompt: str) -> dict:
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    start = time.time()
    async with httpx.AsyncClient(timeout=25.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        elapsed = int((time.time() - start) * 1000)
        resp.raise_for_status()
        data = resp.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"text": text, "latency_ms": elapsed}


ANTIGRAVITY_IDE_USER_AGENT = "antigravity/ide/2.11.0 darwin/arm64"
CODEX_CLI_USER_AGENT = "codex_cli_rs/0.154.0"


async def _call_antigravity(api_key: str, model: str, prompt: str) -> dict:
    start = time.time()
    clean_key = api_key.strip()

    # 1. Đổi refresh token 1//... sang access token ya29... nếu cần
    if clean_key.startswith("1//"):
        active_token = await TokenRefreshService.get_active_token(clean_key)
    else:
        active_token = clean_key
    auth_header = active_token if active_token.lower().startswith("bearer ") else f"Bearer {active_token}"

    # 2. Xử lý model chuẩn cho Google Antigravity
    target_model = normalize_antigravity_model(model)
    target_model = re.sub(r"-tiered\([a-z]+\)", "", target_model)
    if not target_model or "3.6" in target_model or target_model.startswith("ag/"):
        target_model = "gemini-2.5-flash"

    url = "https://daily-cloudcode-pa.googleapis.com/v1internal:generateContent"
    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json",
        "User-Agent": ANTIGRAVITY_IDE_USER_AGENT,
        "x-request-source": "local",
    }
    # Lấy Google Cloud Project ID thực tế qua loadCodeAssist (chuẩn 9router)
    pid = "aicode-consumers"
    try:
        real_pid = await TokenRefreshService.get_project_id(clean_key)
        if real_pid:
            pid = real_pid
    except Exception:
        pass

    payload = {
        "project": pid,
        "model": target_model,
        "userAgent": "antigravity",
        "requestType": "agent",
        "requestId": f"agent/{uuid.uuid4()}/{int(time.time() * 1000)}/{uuid.uuid4()}/1",
        "request": {
            "sessionId": f"-{int(time.time() * 1000)}",
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": 150,
                "temperature": 0.2,
                "thinkingConfig": antigravity_thinking_config(model),
            }
        }
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=5.0)) as client:
        resp = await client.post(url, headers=headers, json=payload)
        elapsed = int((time.time() - start) * 1000)
        if resp.status_code == 401:
            raise Exception("HTTP 401: Antigravity OAuth Bearer token không hợp lệ hoặc đã hết hạn.")
        elif resp.status_code == 429:
            raise Exception(f"HTTP 429 (Antigravity): Vượt quá giới hạn request cho model '{target_model}'.")
        resp.raise_for_status()
        data = resp.json()
        resp_obj = data.get("response", data)
        candidates = resp_obj.get("candidates", [])
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            text = "".join(p.get("text", "") for p in parts if isinstance(p, dict) and p.get("text"))
        else:
            text = str(data)
        return {"text": text, "latency_ms": elapsed}


async def _call_codex(api_key: str, model: str, prompt: str, base_url: Optional[str] = None) -> dict:
    clean_key = api_key.strip()
    is_standard_openai_key = clean_key.startswith("sk-") or (base_url and "api.openai.com" in base_url)
    if is_standard_openai_key and not (base_url and "backend-api/codex" in base_url):
        return await _call_openai_compatible(base_url or "https://api.openai.com/v1", clean_key, model, prompt)

    start = time.time()
    codex_url = (base_url or "https://chatgpt.com/backend-api/codex/responses").rstrip("/")
    if not codex_url.endswith("/responses"):
        codex_url = f"{codex_url}/responses"

    auth_header = clean_key if clean_key.lower().startswith("bearer ") else f"Bearer {clean_key}"
    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json",
        "User-Agent": CODEX_CLI_USER_AGENT,
        "originator": "codex_cli_rs",
        "session_id": f"sess-{uuid.uuid4().hex[:12]}",
    }
    payload = {
        "model": model,
        "input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        "store": False,
        "stream": False,
        "instructions": "You are an expert AI assistant specializing in CAD drawings and BOM extraction.",
        "reasoning": {"effort": "low", "summary": "auto"},
        "include": ["reasoning.encrypted_content"]
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=5.0)) as client:
        resp = await client.post(codex_url, headers=headers, json=payload)
        elapsed = int((time.time() - start) * 1000)
        resp_text = resp.text
        if "selected model is at capacity" in resp_text.lower():
            raise Exception(f"HTTP 429 (Codex): Mô hình '{model}' hiện đang quá tải (at capacity).")
        if resp.status_code == 401:
            raise Exception("HTTP 401: Codex OAuth Token không hợp lệ hoặc đã hết hạn.")
        elif resp.status_code == 429:
            raise Exception("HTTP 429: Vượt quá giới hạn rate limit OpenAI Codex.")
        resp.raise_for_status()
        data = resp.json()
        if "output" in data and isinstance(data["output"], list):
            for item in data["output"]:
                if item.get("type") == "message":
                    parts = item.get("content", [])
                    text = "".join(p.get("text", "") for p in parts if p.get("type") in ("output_text", "text"))
                    if text:
                        return {"text": text, "latency_ms": elapsed}
        if "choices" in data and len(data["choices"]) > 0:
            text = data["choices"][0]["message"]["content"]
            return {"text": text, "latency_ms": elapsed}
        return {"text": str(data), "latency_ms": elapsed}


async def _call_google_gemini(api_key: str, model: str, prompt: str) -> dict:
    """Gọi Google Generative Language API với Google API Key (AIzaSy...)"""
    start = time.time()
    clean_key = api_key.strip()
    cleaned_model = model or ""
    if cleaned_model.startswith("ag/"):
        cleaned_model = cleaned_model[3:]
    if cleaned_model.startswith("models/"):
        cleaned_model = cleaned_model[7:]

    cleaned_model = (
        cleaned_model
        .replace("-tiered(high)", "")
        .replace("-tiered(medium)", "")
        .replace("-tiered(low)", "")
        .replace("-high", "")
        .replace("-medium", "")
        .replace("-low", "")
    )

    if "claude" in cleaned_model.lower() or "gpt" in cleaned_model.lower():
        raise Exception(
            f"Mô hình '{model}' là mô hình Antigravity ({model}). "
            "Để kết nối Antigravity mô hình Claude/GPT, cổng xác thực yêu cầu OAuth Bearer Token (chuỗi token ya29....), "
            "không thể gọi thông qua Google API Key thông thường (AIzaSy...). "
            "Vui lòng sử dụng Bearer Token hoặc chuyển Provider sang Anthropic."
        )

    if not cleaned_model:
        raise Exception("Vui lòng chọn model cần kiểm tra.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{cleaned_model}:generateContent?key={clean_key}"
    gen_config = {
        "maxOutputTokens": 150,
        "temperature": 0.2,
    }
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": gen_config
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
        resp = await client.post(url, json=payload)
        elapsed = int((time.time() - start) * 1000)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                text = parts[0].get("text", "") if parts else ""
            else:
                text = str(data)
            return {"text": text, "latency_ms": elapsed}
        elif resp.status_code == 429:
            retry_note = ""
            try:
                err_j = resp.json()
                msg = err_j.get("error", {}).get("message", "")
                for line in msg.split("\n"):
                    if "Please retry in" in line or "Quota exceeded" in line:
                        retry_note = f" ({line.strip()})"
                        break
            except Exception:
                pass
            raise Exception(f"HTTP 429 (Model '{model}'): Vượt quá giới hạn hạn ngạch Google API{retry_note}. Vui lòng thử lại sau.")
        elif resp.status_code == 404:
            raise Exception(f"HTTP 404 (Model '{model}'): Mô hình không tồn tại hoặc không được hỗ trợ trên Google API Key này.")
        elif resp.status_code == 401:
            raise Exception("HTTP 401: API Key không hợp lệ hoặc đã hết hạn.")
        elif resp.status_code == 503:
            raise Exception(f"HTTP 503 (Model '{model}'): Google Gemini API quá tải hoặc tạm thời không khả dụng (High Demand). Vui lòng thử lại sau.")
        else:
            resp.raise_for_status()


async def _call_anthropic(api_key: str, model: str, prompt: str) -> dict:
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 150,
        "messages": [{"role": "user", "content": prompt}]
    }
    start = time.time()
    async with httpx.AsyncClient(timeout=25.0) as client:
        resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
        elapsed = int((time.time() - start) * 1000)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("content", [])
        text = content[0].get("text", "") if content else ""
        return {"text": text, "latency_ms": elapsed}


@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_ai_connection(
    req: TestConnectionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Test một AI Connection hoặc Provider + API Key trực tiếp"""
    api_key = req.api_key
    provider_id = req.provider_id
    model = req.model

    # 1. Nếu truyền connection_id, lấy từ DB
    if req.connection_id:
        conn_id_val = req.connection_id
        if isinstance(conn_id_val, str):
            try:
                conn_id_val = uuid.UUID(conn_id_val)
            except Exception:
                pass
        result = await db.execute(
            select(AiConnection).where(AiConnection.id == conn_id_val)
        )
        conn = result.scalar_one_or_none()
        if not conn:
            raise HTTPException(status_code=404, detail="Không tìm thấy connection")
        if not api_key:
            api_key = conn.api_key
        if not provider_id:
            provider_id = conn.provider
        if not model:
            if conn.selected_model:
                model = conn.selected_model
            else:
                # Nếu connection chưa gán model riêng, lấy Model AI ưu tiên cao nhất (#1) từ bảng AiProviderModel
                m_res = await db.execute(
                    select(AiProviderModel)
                    .where(AiProviderModel.provider_id == conn.provider, AiProviderModel.is_active == True)
                    .order_by(AiProviderModel.sort_order.asc(), AiProviderModel.id.asc())
                )
                top_m = m_res.scalars().first()
                if top_m and top_m.model_key:
                    model = top_m.model_key

    # 2. Lấy thông tin Provider từ DB
    provider = None
    if provider_id:
        prov_result = await db.execute(
            select(AiProvider).where(AiProvider.id == provider_id)
        )
        provider = prov_result.scalar_one_or_none()

    if not provider and provider_id:
        # Fallback provider resolution
        provider_name = provider_id.title()
    else:
        provider_name = provider.name if provider else "AI Provider"

    # 3. Kiểm tra tính tương thích giữa Model và Provider
    # Tránh trường hợp model của provider cũ bị gửi nhầm (vd: gemini-2.5-flash khi chuyển sang Antigravity/OpenAI)
    if provider_id and model:
        m_match = await db.execute(
            select(AiProviderModel).where(
                AiProviderModel.provider_id == provider_id,
                AiProviderModel.model_key == model
            )
        )
        if not m_match.scalar_one_or_none():
            # Model không thuộc provider này. Kiểm tra xem nó có phải của provider khác không
            other_m = await db.execute(
                select(AiProviderModel).where(
                    AiProviderModel.provider_id != provider_id,
                    AiProviderModel.model_key == model
                )
            )
            is_other_prov_model = other_m.scalar_one_or_none() is not None
            is_format_mismatch = (provider_id == "antigravity" and not model.startswith("ag/")) or (provider_id == "openai" and "gemini" in model.lower()) or (provider_id == "google" and ("claude" in model.lower() or "gpt" in model.lower() or model.startswith("ag/")))

            if is_other_prov_model or is_format_mismatch:
                # Tự động thay bằng model ưu tiên cao nhất (#1) của provider hiện tại
                m_top = await db.execute(
                    select(AiProviderModel)
                    .where(AiProviderModel.provider_id == provider_id, AiProviderModel.is_active == True)
                    .order_by(AiProviderModel.sort_order.asc(), AiProviderModel.id.asc())
                )
                top_model_obj = m_top.scalars().first()
                if top_model_obj:
                    model = top_model_obj.model_key

    if not model:
        fallback_models = {
            "antigravity": "ag/gemini-3.8-flash-high",
            "google": "gemini-2.5-flash",
            "codex": "gpt-5.6-sol",
            "deepseek": "deepseek-chat",
            "openai": "gpt-4o",
            "anthropic": "claude-3-5-sonnet-20241022",
            "groq": "llama-3.3-70b-versatile",
            "openrouter": "google/gemini-2.5-flash",
            "ollama": "llama3.2",
            "mistral": "mistral-large-latest",
            "xai": "grok-2-latest",
        }
        if provider_id:
            m_res = await db.execute(
                select(AiProviderModel)
                .where(AiProviderModel.provider_id == provider_id, AiProviderModel.is_active == True)
                .order_by(AiProviderModel.sort_order.asc(), AiProviderModel.id.asc())
            )
            top_m = m_res.scalars().first()
            if top_m and top_m.model_key:
                model = top_m.model_key
            else:
                model = fallback_models.get(provider_id, "default")
        else:
            model = "default"

    # 4. Kiểm tra API Key (tự động lấy từ DB AiConnection nếu có, ưu tiên priority)
    if not api_key and provider_id:
        conn_res = await db.execute(
            select(AiConnection)
            .where(AiConnection.provider == provider_id, AiConnection.is_active == True)
            .order_by(AiConnection.priority.asc(), AiConnection.created_at.desc())
        )
        active_conn = conn_res.scalars().first()
        if not active_conn:
            conn_res = await db.execute(
                select(AiConnection)
                .where(AiConnection.provider == provider_id)
                .order_by(AiConnection.priority.asc(), AiConnection.created_at.desc())
            )
            active_conn = conn_res.scalars().first()
        if active_conn and active_conn.api_key:
            api_key = active_conn.api_key

    if not api_key:
        # Kiểm tra env key
        if provider_id in ("google", "antigravity") and os.getenv("GEMINI_API_KEY"):
            api_key = os.getenv("GEMINI_API_KEY")
        elif provider_id == "openai" and os.getenv("OPENAI_API_KEY"):
            api_key = os.getenv("OPENAI_API_KEY")
        elif provider_id == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
            api_key = os.getenv("ANTHROPIC_API_KEY")
        elif provider_id == "deepseek" and os.getenv("DEEPSEEK_API_KEY"):
            api_key = os.getenv("DEEPSEEK_API_KEY")
        elif provider_id == "openrouter" and os.getenv("OPENROUTER_API_KEY"):
            api_key = os.getenv("OPENROUTER_API_KEY")
        elif provider_id == "groq" and os.getenv("GROQ_API_KEY"):
            api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        return TestConnectionResponse(
            success=False,
            provider=provider_name,
            model_used=model,
            message="Chưa cấu hình API Key. Vui lòng thêm API Key cho nhà cung cấp này trước khi kiểm tra."
        )

    # 5. Xác định phương thức gọi dựa trên api_type hoặc provider
    api_type = provider.api_type if provider else ("google_gemini" if provider_id == "google" else "openai_compatible")
    base_url = (req.base_url.strip() if (req.base_url and req.base_url.strip()) else None) or (provider.base_url if provider and provider.base_url else settings.AI_COMPATIBLE_DEFAULT_BASE_URL)

    # Xử lý tự động làm mới nếu là Google OAuth Refresh Token (bắt đầu bằng 1//)
    was_refreshed = False
    if api_key and api_key.strip().startswith("1//"):
        try:
            active_token = await _refresh_google_oauth_token(api_key.strip())
            if active_token:
                api_key = active_token
                was_refreshed = True
        except Exception as ref_err:
            return TestConnectionResponse(
                success=False,
                provider=provider_name,
                model_used=model,
                message=f"Lỗi làm mới Google OAuth Refresh Token: {str(ref_err)}"
            )

    prompt = req.prompt or settings.AI_CONNECTION_TEST_PROMPT

    try:
        if api_type == "antigravity_engine" or provider_id == "antigravity":
            result_data = await _call_antigravity(api_key, model, prompt)
        elif provider_id == "codex":
            result_data = await _call_codex(api_key, model, prompt, base_url=base_url)
        elif api_type == "google_gemini" or provider_id == "google":
            result_data = await _call_google_gemini(api_key, model, prompt)
        elif api_type == "anthropic" or provider_id == "anthropic":
            result_data = await _call_anthropic(api_key, model, prompt)
        else:
            # openai_compatible (OpenAI, DeepSeek, OpenRouter, Groq, Mistral, Ollama, xAI, Custom, etc.)
            result_data = await _call_openai_compatible(base_url, api_key, model, prompt)

        success_msg = f"Đã làm mới OAuth Token và kết nối thành công với {provider_name}!" if was_refreshed else f"Kết nối thành công với {provider_name}!"
        return TestConnectionResponse(
            success=True,
            message=success_msg,
            provider=provider_name,
            model_used=model,
            response_text=result_data["text"].strip(),
            latency_ms=result_data["latency_ms"],
        )

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}"
        try:
            err_json = e.response.json()
            if "error" in err_json:
                err_detail = err_json["error"]
                if isinstance(err_detail, dict):
                    error_msg += f": {err_detail.get('message', str(err_detail))}"
                else:
                    error_msg += f": {err_detail}"
            elif "message" in err_json:
                error_msg += f": {err_json['message']}"
        except Exception:
            error_msg += f": {e.response.text[:200]}"

        return TestConnectionResponse(
            success=False,
            provider=provider_name,
            model_used=model,
            message=f"Lỗi phản hồi từ nhà cung cấp ({error_msg})",
        )
    except httpx.ConnectError:
        return TestConnectionResponse(
            success=False,
            provider=provider_name,
            model_used=model,
            message=f"Không thể kết nối tới máy chủ {base_url}. Vui lòng kiểm tra địa chỉ mạng hoặc endpoint.",
        )
    except httpx.TimeoutException:
        return TestConnectionResponse(
            success=False,
            provider=provider_name,
            model_used=model,
            message=f"Yêu cầu tới {provider_name} bị quá thời gian chờ (Timeout sau 25s).",
        )
    except Exception as e:
        return TestConnectionResponse(
            success=False,
            provider=provider_name,
            model_used=model,
            message=f"Lỗi kết nối: {str(e)[:300]}",
        )


@router.get("/connections-by-provider/{provider_id}")
async def get_connections_by_provider(provider_id: str, db: AsyncSession = Depends(get_db)):
    """Lấy danh sách connections của một provider cụ thể theo thứ tự ưu tiên"""
    result = await db.execute(
        select(AiConnection)
        .where(AiConnection.provider == provider_id)
        .order_by(AiConnection.priority.asc(), AiConnection.created_at.desc())
    )
    connections = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "provider": c.provider,
            "selected_model": c.selected_model,
            "priority": c.priority,
            "api_key_masked": (c.api_key[:8] + "..." + c.api_key[-4:]) if c.api_key and len(c.api_key) > 12 else (c.api_key or ""),
            "has_key": bool(c.api_key),
            "is_active": c.is_active,
            "status": c.status,
            "last_error_at": c.last_error_at.isoformat() if c.last_error_at else None,
            "last_error_message": c.last_error_message,
        }
        for c in connections
    ]


@router.get("/provider-models/{provider_id}")
async def get_provider_models_admin(provider_id: str, db: AsyncSession = Depends(get_db)):
    """Lấy models của một provider sắp theo thứ tự ưu tiên (sort_order)"""
    result = await db.execute(
        select(AiProviderModel)
        .where(AiProviderModel.provider_id == provider_id)
        .order_by(AiProviderModel.sort_order, AiProviderModel.id)
    )
    models = result.scalars().all()
    return [{"model_key": m.model_key, "label": m.label, "is_active": m.is_active, "sort_order": m.sort_order} for m in models]


class UpdateModelPriorityRequest(BaseModel):
    sort_order: int


@router.post("/provider-models/{model_id}/priority")
async def update_model_priority(
    model_id: int,
    req: UpdateModelPriorityRequest,
    db: AsyncSession = Depends(get_db)
):
    """Cập nhật thứ tự ưu tiên (sort_order) cho một Model AI"""
    result = await db.execute(
        select(AiProviderModel).where(AiProviderModel.id == model_id)
    )
    model_obj = result.scalar_one_or_none()
    if not model_obj:
        raise HTTPException(status_code=404, detail="Không tìm thấy model")

    model_obj.sort_order = req.sort_order
    await db.commit()
    return {"success": True, "id": model_id, "sort_order": req.sort_order}


class ReorderModelItem(BaseModel):
    id: int
    sort_order: int


class ReorderModelsRequest(BaseModel):
    items: List[ReorderModelItem]


@router.post("/provider-models/reorder")
async def reorder_provider_models(
    req: ReorderModelsRequest,
    db: AsyncSession = Depends(get_db)
):
    """Cập nhật thứ tự ưu tiên (sort_order) cho nhiều Model AI cùng lúc qua kéo thả"""
    for item in req.items:
        await db.execute(
            update(AiProviderModel)
            .where(AiProviderModel.id == item.id)
            .values(sort_order=item.sort_order)
        )
    await db.commit()
    return {"success": True, "updated_count": len(req.items)}


class ToggleConnectionActiveRequest(BaseModel):
    is_active: bool


@router.post("/connections/{connection_id}/toggle-active")
async def toggle_connection_active(
    connection_id: str,
    req: ToggleConnectionActiveRequest,
    db: AsyncSession = Depends(get_db)
):
    """Bật / Tắt một AiConnection trực tiếp từ danh sách card"""
    try:
        conn_uuid = uuid.UUID(connection_id) if isinstance(connection_id, str) else connection_id
    except Exception:
        raise HTTPException(status_code=400, detail="Mã kết nối không hợp lệ")

    result = await db.execute(select(AiConnection).where(AiConnection.id == conn_uuid))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Không tìm thấy kết nối")

    conn.is_active = req.is_active
    await db.commit()
    return {"success": True, "id": str(conn.id), "is_active": conn.is_active}


class TestWebSearchRequest(BaseModel):
    query: str
    provider_id: Optional[str] = "antigravity"
    connection_id: Optional[str] = None
    model: Optional[str] = None
    max_results: Optional[int] = 5


class TestWebSearchResponse(BaseModel):
    success: bool
    provider: str
    query: str
    answer: str
    results: List[dict]
    latency_ms: int
    error: Optional[str] = None


@router.post("/test-websearch", response_model=TestWebSearchResponse)
async def test_web_search(
    req: TestWebSearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """Kiểm tra tìm kiếm trực tuyến và AI Grounding qua WebSearchService (chuẩn 9router)."""
    provider_id = (req.provider_id or "antigravity").lower().strip()
    api_key = None
    model = req.model
    base_url = None

    # Lấy API Key từ connection nếu có connection_id
    if req.connection_id:
        conn_id_val = req.connection_id
        if isinstance(conn_id_val, str):
            try:
                conn_id_val = uuid.UUID(conn_id_val)
            except Exception:
                pass
        result = await db.execute(select(AiConnection).where(AiConnection.id == conn_id_val))
        conn = result.scalar_one_or_none()
        if conn:
            api_key = conn.api_key
            provider_id = conn.provider.lower()
            if not model and conn.selected_model:
                model = conn.selected_model

    # Nếu chưa có api_key, tìm connection active đầu tiên của provider này
    if not api_key:
        conn_res = await db.execute(
            select(AiConnection)
            .where(AiConnection.provider == provider_id, AiConnection.is_active == True)
            .order_by(AiConnection.priority.asc())
        )
        active_conn = conn_res.scalars().first()
        if active_conn and active_conn.api_key:
            api_key = active_conn.api_key
            if not model:
                model = active_conn.selected_model

    # Lấy base_url từ AiProvider nếu có
    prov_res = await db.execute(select(AiProvider).where(AiProvider.id == provider_id))
    prov_obj = prov_res.scalar_one_or_none()
    if prov_obj and prov_obj.base_url:
        base_url = prov_obj.base_url

    if not api_key:
        raise HTTPException(
            status_code=400,
            detail=f"Chưa có API Key hoặc OAuth token khả dụng cho provider '{provider_id}'."
        )

    res = await WebSearchService.search(
        query=req.query,
        provider=provider_id,
        api_key=api_key,
        model=model,
        max_results=req.max_results or 5,
        base_url=base_url
    )
    return TestWebSearchResponse(
        success=res.get("success", False),
        provider=res.get("provider", provider_id),
        query=res.get("query", req.query),
        answer=res.get("answer", ""),
        results=res.get("results", []),
        latency_ms=res.get("latency_ms", 0),
        error=res.get("error")
    )


@router.post("/detect-key", response_model=DetectKeyResponse)
async def detect_ai_key(req: DetectKeyRequest):
    """Tự động phát hiện loại API Key / OAuth Token (tương tự 9router) và đề xuất Provider, Model phù hợp."""
    raw = req.get_raw_key()
    if not raw:
        return DetectKeyResponse(
            detected=False,
            format_name="Chưa nhập key",
            note="Vui lòng dán chuỗi API Key hoặc Token cần kiểm tra."
        )

    # 1. Antigravity OAuth Access Token (bắt đầu bằng ya29.)
    if raw.startswith("ya29."):
        return DetectKeyResponse(
            detected=True,
            provider_id="antigravity",
            provider_name="Antigravity",
            auth_type="bearer_token",
            format_name="Google Cloud Code / Antigravity OAuth Bearer Token",
            suggested_model="ag/gemini-3.8-flash-high",
            base_url="https://daily-cloudcode-pa.googleapis.com",
            note="Token Bearer chuẩn Antigravity (hiệu lực ~1 giờ). Tự động gắn User-Agent 2.11.0."
        )

    # 2. Antigravity OAuth Refresh Token (bắt đầu bằng 1//)
    if raw.startswith("1//"):
        return DetectKeyResponse(
            detected=True,
            provider_id="antigravity",
            provider_name="Antigravity",
            auth_type="oauth2",
            format_name="Google OAuth 2.0 Refresh Token (Tự Động Gia Hạn Vĩnh Viễn)",
            suggested_model="ag/gemini-3.8-flash-high",
            base_url="https://daily-cloudcode-pa.googleapis.com",
            note="Refresh Token chuẩn! Hệ thống sẽ tự động đổi lấy Access Token mới mỗi khi hết hạn."
        )

    # 3. Google Gemini Developer API Key (AI Studio)
    if raw.startswith("AIza"):
        return DetectKeyResponse(
            detected=True,
            provider_id="google",
            provider_name="Google Gemini",
            auth_type="api_key",
            format_name="Google Gemini Developer API Key (Google AI Studio)",
            suggested_model="gemini-2.5-flash",
            base_url="https://generativelanguage.googleapis.com",
            note="Khóa API chính thức của Google AI Studio (hỗ trợ cả Gemini 2.5 Flash, 2.5 Pro)."
        )

    # 4. Anthropic Claude API Key
    if raw.startswith("sk-ant-"):
        return DetectKeyResponse(
            detected=True,
            provider_id="anthropic",
            provider_name="Anthropic Claude",
            auth_type="api_key",
            format_name="Anthropic Claude Secret API Key",
            suggested_model="claude-3-5-sonnet-20241022",
            base_url="https://api.anthropic.com/v1",
            note="Khóa Claude chính hãng từ Anthropic Console (hỗ trợ Vision và bóc tách tài liệu)."
        )

    # 5. Groq LPU API Key
    if raw.startswith("gsk_"):
        return DetectKeyResponse(
            detected=True,
            provider_id="groq",
            provider_name="Groq",
            auth_type="api_key",
            format_name="Groq LPU Inference API Key",
            suggested_model="llama-3.3-70b-versatile",
            base_url="https://api.groq.com/openai/v1",
            note="Tốc độ suy luận siêu tốc (LPU). Thích hợp bóc tách và phản hồi cực nhanh."
        )

    # 6. OpenRouter API Key
    if raw.startswith("sk-or-v1-") or raw.startswith("sk-or-"):
        return DetectKeyResponse(
            detected=True,
            provider_id="openrouter",
            provider_name="OpenRouter",
            auth_type="api_key",
            format_name="OpenRouter Unified API Key",
            suggested_model="google/gemini-2.0-flash-001",
            base_url="https://openrouter.ai/api/v1",
            note="Cổng kết nối đa mô hình OpenRouter (gọi Claude, GPT, DeepSeek, Llama... qua 1 key)."
        )

    # 7. xAI (Grok) API Key
    if raw.startswith("xai-"):
        return DetectKeyResponse(
            detected=True,
            provider_id="xai",
            provider_name="xAI (Grok)",
            auth_type="api_key",
            format_name="xAI Grok API Key",
            suggested_model="grok-2-vision-1212",
            base_url="https://api.x.ai/v1",
            note="Mô hình đa phương thức Grok từ xAI (Elon Musk)."
        )

    # 8. OpenAI Project / Standard Key
    if raw.startswith("sk-proj-"):
        return DetectKeyResponse(
            detected=True,
            provider_id="openai",
            provider_name="OpenAI",
            auth_type="api_key",
            format_name="OpenAI Project API Key",
            suggested_model="gpt-6-astra",
            base_url="https://api.openai.com/v1",
            note="Khóa Project chính thức từ OpenAI Platform."
        )

    # 9. Codex / ChatGPT Session Token
    if raw.startswith("sess-") or (len(raw) > 300 and "." in raw):
        return DetectKeyResponse(
            detected=True,
            provider_id="codex",
            provider_name="Codex / OpenAI API",
            auth_type="bearer_token",
            format_name="OpenAI / ChatGPT OAuth Bearer Token (Codex Responses API)",
            suggested_model="gpt-5.6-terra",
            base_url="https://chatgpt.com/backend-api/codex/responses",
            note="Token phiên ChatGPT tương tự cơ chế 9router."
        )

    # 10. DeepSeek hoặc OpenAI standard sk-...
    if raw.startswith("sk-"):
        return DetectKeyResponse(
            detected=True,
            provider_id="deepseek",
            provider_name="DeepSeek",
            auth_type="api_key",
            format_name="DeepSeek / OpenAI-Compatible API Key",
            suggested_model="deepseek-chat",
            base_url="https://api.deepseek.com/v1",
            note="Khóa chuẩn OpenAI format (mặc định định tuyến DeepSeek hoặc đổi sang OpenAI / Mistral)."
        )

    # 11. Local instance / Ollama
    if raw.lower() in ("ollama", "local", "none", "test") or "localhost" in raw or "127.0.0.1" in raw:
        return DetectKeyResponse(
            detected=True,
            provider_id="ollama",
            provider_name="Ollama (Local)",
            auth_type="api_key",
            format_name="Ollama Local Instance",
            suggested_model="llama3.1:8b",
            base_url="http://localhost:11434/v1",
            note="Mô hình chạy offline nội bộ trên máy cá nhân hoặc server riêng (không tốn token)."
        )

    return DetectKeyResponse(
        detected=False,
        format_name="Khóa tùy biến (Custom API Key)",
        note="Định dạng chưa nhận diện tự động. Vui lòng tự chọn Provider và kiểm tra kết nối."
    )


@router.get("/providers-summary")
async def get_providers_summary(db: AsyncSession = Depends(get_db)):
    """Lấy danh sách tóm tắt tất cả các provider đang có cùng endpoint mặc định và danh sách model."""
    stmt = select(AiProvider).where(AiProvider.is_active == True).order_by(AiProvider.sort_order.asc())
    res = await db.execute(stmt)
    providers = res.scalars().all()

    out = []
    for p in providers:
        m_stmt = select(AiProviderModel).where(
            AiProviderModel.provider_id == p.id,
            AiProviderModel.is_active == True
        ).order_by(AiProviderModel.sort_order.asc(), AiProviderModel.id.asc())
        m_res = await db.execute(m_stmt)
        models = m_res.scalars().all()

        out.append({
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "api_type": p.api_type,
            "base_url": p.base_url or "",
            "description": p.description or "",
            "models": [{"key": m.model_key, "label": m.label} for m in models]
        })
    return out


@router.get("/antigravity/auth-url")
async def get_antigravity_auth_url(request: Request):
    """Tạo URL đăng nhập Google OAuth 2.0 Antigravity trực tiếp tương tự 9router."""
    # Chuẩn Desktop OAuth Client ID yêu cầu redirect_uri là localhost
    redirect_uri = "http://localhost:8000/api/v1/admin-api/antigravity/callback"
    auth_url = TokenRefreshService.build_auth_url(redirect_uri=redirect_uri)
    return {"auth_url": auth_url, "redirect_uri": redirect_uri}


@router.get("/antigravity/check-status")
async def check_antigravity_status(
    since: Optional[float] = None,
    db: AsyncSession = Depends(get_db)
):
    """Kiểm tra xem tài khoản Google Antigravity vừa được kết nối thành công chưa (Hỗ trợ cross-origin & cross-network)."""
    from datetime import datetime, timezone, timedelta

    now_utc = datetime.now(timezone.utc)
    # Mặc định lấy trong vòng 5 phút qua
    threshold = now_utc - timedelta(minutes=5)
    if since and since > 0:
        try:
            since_dt = datetime.fromtimestamp(since / 1000.0, tz=timezone.utc)
            # Trừ 30s buffer để phòng ngừa lệch đồng hồ giữa máy client và máy server
            threshold = since_dt - timedelta(seconds=30)
        except Exception:
            pass

    stmt = select(AiConnection).where(
        AiConnection.provider == "antigravity",
        AiConnection.is_active == True,
        AiConnection.email.isnot(None),
        AiConnection.updated_at >= threshold
    ).order_by(AiConnection.updated_at.desc()).limit(1)

    res = await db.execute(stmt)
    conn = res.scalar_one_or_none()

    if conn and conn.email:
        project_id = conn.quotas.get("project_id") if isinstance(conn.quotas, dict) else "cloudaicompanion-project"
        return {
            "connected": True,
            "id": str(conn.id),
            "email": conn.email or "Google Antigravity User",
            "project_id": project_id,
            "token": conn.api_key
        }

    return {"connected": False}


class ExchangeAntigravityRequest(BaseModel):
    code: Optional[str] = None
    callback_url: Optional[str] = None
    redirect_uri: Optional[str] = None


@router.post("/antigravity/exchange")
async def exchange_antigravity_code(
    payload: ExchangeAntigravityRequest,
    db: AsyncSession = Depends(get_db)
):
    """Đổi mã ủy quyền hoặc URL chuyển hướng từ Google lấy Refresh Token và Project ID cá nhân."""
    from urllib.parse import urlparse, parse_qs

    code = (payload.code or "").strip()
    redirect_uri = payload.redirect_uri or "http://localhost:8000/api/v1/admin-api/antigravity/callback"

    if payload.callback_url:
        cb = payload.callback_url.strip()
        if "?" in cb:
            parsed = urlparse(cb)
            qs = parse_qs(parsed.query)
            if "code" in qs:
                code = qs["code"][0]
        elif not code and (cb.startswith("4/") or cb.startswith("1//") or cb.startswith("ya29.")):
            code = cb

    if not code:
        raise HTTPException(
            status_code=400,
            detail="Vui lòng cung cấp Authorization Code (4/...) hoặc toàn bộ Callback URL từ trình duyệt."
        )

    # Nếu dán trực tiếp Refresh Token (1//...) hoặc Access Token (ya29.)
    if code.startswith("1//") or code.startswith("ya29."):
        refresh_token = code
        try:
            active_token = await TokenRefreshService.get_active_token(refresh_token)
            project_id = await TokenRefreshService.get_project_id(active_token)
            email = "Google Antigravity User"
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    u_resp = await client.get(
                        "https://www.googleapis.com/oauth2/v1/userinfo",
                        headers={"Authorization": f"Bearer {active_token}"}
                    )
                    if u_resp.status_code == 200:
                        email = u_resp.json().get("email", email)
            except Exception:
                pass
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Token không hợp lệ: {str(e)}")
    else:
        try:
            token_data = await TokenRefreshService.exchange_code_for_tokens(code, redirect_uri)
            refresh_token = token_data.get("refresh_token") or token_data.get("access_token")
            email = token_data.get("email") or "Google Antigravity User"
            project_id = token_data.get("project_id") or "cloudaicompanion-project"
        except Exception as ex:
            raise HTTPException(status_code=400, detail=f"Lỗi xác thực với Google: {str(ex)}")

    stmt = select(AiConnection).where(AiConnection.provider == "antigravity", AiConnection.email == email)
    res = await db.execute(stmt)
    conn = res.scalar_one_or_none()

    from datetime import datetime, timezone
    if not conn:
        conn = AiConnection(
            provider="antigravity",
            auth_type="oauth2",
            name=f"Antigravity OAuth ({email})",
            email=email,
            api_key=refresh_token,
            selected_model="ag/gemini-3.8-flash-high",
            is_active=True,
            status="active",
            tag="Google OAuth Direct",
            priority=1,
            quotas={"project_id": project_id},
            updated_at=datetime.now(timezone.utc)
        )
        db.add(conn)
    else:
        conn.api_key = refresh_token
        conn.auth_type = "oauth2"
        conn.is_active = True
        conn.status = "active"
        conn.updated_at = datetime.now(timezone.utc)
        quotas = dict(conn.quotas) if isinstance(conn.quotas, dict) else {}
        quotas["project_id"] = project_id
        conn.quotas = quotas
        db.add(conn)

    await db.commit()

    return {
        "success": True,
        "email": email,
        "project_id": project_id,
        "token_preview": refresh_token[:15] + "...",
        "message": f"Liên kết thành công tài khoản Google: {email} (Project ID: {project_id})"
    }


@router.get("/antigravity/callback")
async def antigravity_oauth_callback(
    code: Optional[str] = None,
    error: Optional[str] = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """Nhận code từ Google, tự đổi lấy Refresh Token và lấy Project ID thực tế qua loadCodeAssist."""
    if error:
        return HTMLResponse(f"<h3>Đăng nhập Google thất bại: {error}</h3><p><button onclick='window.close()'>Đóng</button></p>")
    if not code:
        return HTMLResponse("<h3>Không nhận được mã ủy quyền từ Google.</h3><p><button onclick='window.close()'>Đóng</button></p>")

    redirect_uri = "http://localhost:8000/api/v1/admin-api/antigravity/callback"

    try:
        token_data = await TokenRefreshService.exchange_code_for_tokens(code, redirect_uri)
        refresh_token = token_data.get("refresh_token") or token_data.get("access_token")
        email = token_data.get("email") or "Google Antigravity User"
        project_id = token_data.get("project_id") or "cloudaicompanion-project"

        stmt = select(AiConnection).where(AiConnection.provider == "antigravity", AiConnection.email == email)
        res = await db.execute(stmt)
        conn = res.scalar_one_or_none()

        from datetime import datetime, timezone
        if not conn:
            conn = AiConnection(
                provider="antigravity",
                auth_type="oauth2",
                name=f"Antigravity OAuth ({email})",
                email=email,
                api_key=refresh_token,
                selected_model="ag/gemini-3.8-flash-high",
                is_active=True,
                status="active",
                tag="Google OAuth Direct",
                priority=1,
                quotas={"project_id": project_id},
                updated_at=datetime.now(timezone.utc)
            )
            db.add(conn)
        else:
            conn.api_key = refresh_token
            conn.auth_type = "oauth2"
            conn.is_active = True
            conn.status = "active"
            conn.updated_at = datetime.now(timezone.utc)
            quotas = dict(conn.quotas) if isinstance(conn.quotas, dict) else {}
            quotas["project_id"] = project_id
            conn.quotas = quotas
            db.add(conn)

        await db.commit()

        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html lang="vi">
        <head>
          <title>Đang hoàn tất đăng nhập...</title>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
              font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
              display: flex;
              align-items: center;
              justify-content: center;
              height: 100vh;
              background: #f8fafc;
              color: #1e293b;
              text-align: center;
              padding: 16px;
            }}
            .box {{
              padding: 28px 32px;
              background: #ffffff;
              border-radius: 16px;
              box-shadow: 0 4px 20px rgba(0,0,0,0.06);
              border: 1px solid #e2e8f0;
              max-width: 360px;
              width: 100%;
            }}
            .spinner {{
              width: 40px;
              height: 40px;
              border: 3.5px solid #e2e8f0;
              border-top-color: #16a34a;
              border-radius: 50%;
              animation: spin 0.7s linear infinite;
              margin: 0 auto 14px;
            }}
            @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
          </style>
        </head>
        <body>
          <div class="box">
            <div class="spinner"></div>
            <div style="font-weight: 700; font-size: 16px; color: #16a34a; margin-bottom: 6px;">
              Đăng nhập thành công!
            </div>
            <div style="font-size: 13px; color: #64748b; margin-bottom: 12px;">
              Tài khoản <strong>{email}</strong> đã kết nối thành công.
            </div>
            <button onclick="try{{window.close();}}catch(e){{}};window.location.href='/admin/ai-connection/list';" style="background:#16a34a;color:#fff;border:none;padding:8px 18px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;">
              Đóng cửa sổ
            </button>
          </div>
          <script>
            const payload = {{
              status: 'success',
              email: '{email}',
              project_id: '{project_id}',
              token: '{refresh_token}'
            }};

            // 1. Gửi qua BroadcastChannel cho tất cả tab cùng origin
            try {{
              const bc = new BroadcastChannel('antigravity_oauth');
              bc.postMessage(payload);
            }} catch(e) {{}}

            // 2. Gửi qua localStorage
            try {{
              localStorage.setItem('antigravity_oauth_success', JSON.stringify({{
                ...payload,
                time: Date.now()
              }}));
            }} catch(e) {{}}

            // 3. Thử gọi trực tiếp hàm xử lý của window.opener (bọc an toàn tránh lỗi COOP)
            try {{
              if (window.opener) {{
                try {{
                  if (typeof window.opener.onAntigravitySuccess === 'function') {{
                    window.opener.onAntigravitySuccess(payload);
                  }}
                  if (typeof window.opener.onAntigravitySuccessList === 'function') {{
                    window.opener.onAntigravitySuccessList(payload);
                  }}
                }} catch(openerFnErr) {{}}
                try {{
                  window.opener.postMessage(payload, '*');
                }} catch(openerMsgErr) {{}}
              }}
            }} catch(e) {{}}

            // 4. Đóng cửa sổ ngay lập tức
            function closeSelf() {{
              try {{
                window.close();
              }} catch(e) {{}}
            }}

            closeSelf();
            setTimeout(closeSelf, 100);
            setTimeout(closeSelf, 400);
            setTimeout(closeSelf, 1000);

            // 5. Fallback nếu trình duyệt chặn hoàn toàn window.close
            setTimeout(function() {{
              try {{
                window.close();
              }} catch(e) {{}}
              window.location.href = '/admin/ai-connection/list';
            }}, 1500);
          </script>
        </body>
        </html>
        """)

    except Exception as ex:
        return HTMLResponse(f"""
        <div style="font-family:sans-serif;padding:30px;text-align:center;">
          <h3 style="color:#ef4444;">Lỗi xác thực OAuth: {str(ex)}</h3>
          <p style="margin-top:15px;"><button onclick="window.close()" style="padding:8px 16px;cursor:pointer;">Đóng cửa sổ</button></p>
        </div>
        """)

