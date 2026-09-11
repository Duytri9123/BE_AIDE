"""
Admin helper API routes - Test AI connections & Models.
Provides live testing of API Keys and Model outputs with latency measurement.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from typing import Optional, List
import httpx
import time
import json
import os
import uuid

from app.db.session import get_db
from app.models.ai_connection import AiConnection
from app.models.ai_provider import AiProvider
from app.models.ai_provider_model import AiProviderModel
from app.core.config import settings
from app.services.ai.vision_analyzer import normalize_antigravity_model

router = APIRouter(prefix="/admin-api", tags=["Admin Helpers"])


class TestConnectionRequest(BaseModel):
    connection_id: Optional[str] = None
    provider_id: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    prompt: Optional[str] = None


class TestConnectionResponse(BaseModel):
    success: bool
    message: str
    provider: Optional[str] = None
    model_used: Optional[str] = None
    response_text: Optional[str] = None
    latency_ms: Optional[int] = None


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


async def _call_antigravity(api_key: str, model: str, prompt: str) -> dict:
    start = time.time()
    clean_key = api_key.strip()
    auth_header = clean_key if clean_key.lower().startswith("bearer ") else f"Bearer {clean_key}"
    target_model = normalize_antigravity_model(model)

    url = "https://daily-cloudcode-pa.googleapis.com/v1internal:generateContent"
    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json",
        "User-Agent": "antigravity/ide/2.1.1 darwin/arm64",
        "x-request-source": "local",
    }
    payload = {
        "project": "cloudaicompanion-project",
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
            }
        }
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
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
            text = "".join(p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p)
        else:
            text = str(data)
        return {"text": text, "latency_ms": elapsed}


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
        raise HTTPException(
            status_code=400,
            detail="Chưa chọn model trong cấu hình BE. Hãy chọn model cụ thể trước khi kiểm tra kết nối.",
        )

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
    base_url = (provider.base_url if provider and provider.base_url else settings.AI_COMPATIBLE_DEFAULT_BASE_URL)

    prompt = req.prompt or settings.AI_CONNECTION_TEST_PROMPT

    try:
        if api_type == "antigravity_engine" or provider_id == "antigravity":
            result_data = await _call_antigravity(api_key, model, prompt)
        elif api_type == "google_gemini" or provider_id == "google":
            result_data = await _call_google_gemini(api_key, model, prompt)
        elif api_type == "anthropic" or provider_id == "anthropic":
            result_data = await _call_anthropic(api_key, model, prompt)
        else:
            # openai_compatible (OpenAI, DeepSeek, OpenRouter, Groq, Mistral, Ollama, xAI, etc.)
            result_data = await _call_openai_compatible(base_url, api_key, model, prompt)

        return TestConnectionResponse(
            success=True,
            message=f"Kết nối thành công với {provider_name}!",
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
