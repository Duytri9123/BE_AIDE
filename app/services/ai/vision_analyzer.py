import time
import uuid
import base64
import httpx
import logging
import asyncio
import re
import hashlib
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.services.cache_service import cache_service
from app.core.exceptions import (
    AIVisionError,
    AITimeoutError,
    AIRateLimitError,
    AIAuthenticationError,
    ImageParsingError
)

logger = logging.getLogger(__name__)


def normalize_antigravity_model(model: str) -> str:
    """Translate a DB model key to Antigravity's tiered model identifier.

    Flash versions are handled by pattern, so adding a new Gemini version in the
    database does not require another hard-coded mapping table.
    """
    clean_model = (model or "").removeprefix("ag/")
    tiered = re.fullmatch(
        r"(gemini-[\d.]+-flash)(?:-(high|medium|low)|-tiered\((high|medium|low)\))?",
        clean_model,
    )
    if tiered:
        base, direct_tier, existing_tier = tiered.groups()
        return f"{base}-tiered({direct_tier or existing_tier or 'low'})"

    # These are provider-specific endpoint aliases, not fallback candidates.
    return {
        "claude-sonnet-4.6": "claude-sonnet-4-6",
        "claude-opus-4.6": "claude-opus-4-6",
        "claude-opus-4.6-thinking": "claude-opus-4-6",
        "gpt-oss-120b": "gpt-oss-120b-medium",
    }.get(clean_model, clean_model)


class VisionAnalyzerService:
    @staticmethod
    async def analyze_image(image_path: str, prompt: str, provider: str, api_key: str, model: str) -> str:
        """Gọi API AI Vision (Gemini/OpenAI/Claude/Antigravity) để phân tích hình ảnh."""
        try:
            # Validate file exists
            if not Path(image_path).exists():
                raise ImageParsingError(
                    f"File không tồn tại: {image_path}",
                    {"path": image_path}
                )
            
            # Read and encode image
            try:
                with open(image_path, "rb") as f:
                    img_bytes = f.read()
                    img_b64 = base64.b64encode(img_bytes).decode()
            except PermissionError:
                raise ImageParsingError(
                    f"Không có quyền đọc file: {image_path}",
                    {"path": image_path}
                )
            except Exception as e:
                raise ImageParsingError(
                    f"Lỗi đọc file hình ảnh: {str(e)}",
                    {"path": image_path, "error": str(e)}
                )
            
            prov = provider.lower()
            img_hash = hashlib.sha256(img_bytes).hexdigest()
            prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
            cache_key = f"ai_vision:{img_hash}:{prov}:{model.lower()}:{prompt_hash}"

            # Kiểm tra cache trước khi gọi API
            try:
                cached_res = await cache_service.get(cache_key)
                if cached_res:
                    logger.info(f"[VisionAnalyzerService] Cache HIT cho {image_path} ({provider}/{model}). Trả về ngay lập tức.")
                    return cached_res
            except Exception as ce:
                logger.warning(f"[VisionAnalyzerService] Lỗi đọc cache: {ce}")

            logger.info(f"Analyzing image with {provider} ({model})", extra={
                "provider": provider,
                "model": model,
                "image_path": image_path
            })
            
            result = None
            if prov in ["openai", "codex"]:
                result = await VisionAnalyzerService._call_openai(img_b64, prompt, api_key, model, provider_name=provider)
            elif prov == "antigravity":
                result = await VisionAnalyzerService._call_antigravity(img_b64, prompt, api_key, model)
            elif prov in ["gemini", "google"]:
                cleaned_model = model
                if cleaned_model.startswith("ag/"):
                    cleaned_model = cleaned_model[3:]
                result = await VisionAnalyzerService._call_google_genai(img_b64, prompt, api_key, cleaned_model, provider_name="Google")
            else:
                raise AIVisionError(
                    f"Provider không được hỗ trợ: {provider}",
                    {"provider": provider, "supported": ["openai", "codex", "gemini", "google", "antigravity"]}
                )

            # Lưu vào cache (TTL 7 ngày = 604800s)
            if result and len(result) > 20:
                try:
                    await cache_service.set(cache_key, result, expire=604800)
                except Exception as se:
                    logger.warning(f"[VisionAnalyzerService] Lỗi ghi cache: {se}")

            return result
        except (AIVisionError, ImageParsingError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in analyze_image: {str(e)}", exc_info=True)
            raise AIVisionError(
                f"Lỗi không xác định khi phân tích hình ảnh: {str(e)}",
                {"error": str(e), "provider": provider}
            )

    @staticmethod
    async def analyze_text(prompt: str, provider: str, api_key: str, model: str) -> str:
        """Gọi API AI LLM để phân tích dữ liệu văn bản/sơ đồ kỹ thuật."""
        prov = provider.lower()
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        cache_key = f"ai_text:{prov}:{model.lower()}:{prompt_hash}"

        try:
            cached_res = await cache_service.get(cache_key)
            if cached_res:
                logger.info(f"[VisionAnalyzerService] Cache HIT cho text prompt ({provider}/{model}). Trả về ngay lập tức.")
                return cached_res
        except Exception:
            pass

        result = None
        if prov in ["openai", "codex"]:
            result = await VisionAnalyzerService._call_openai("", prompt, api_key, model, provider_name=provider)
        elif prov == "antigravity":
            result = await VisionAnalyzerService._call_antigravity("", prompt, api_key, model)
        elif prov in ["gemini", "google"]:
            cleaned_model = model
            if cleaned_model.startswith("ag/"):
                cleaned_model = cleaned_model[3:]
            result = await VisionAnalyzerService._call_google_genai("", prompt, api_key, cleaned_model, provider_name="Google")
        else:
            raise AIVisionError(
                f"Provider không được hỗ trợ: {provider}",
                {"provider": provider, "supported": ["openai", "codex", "gemini", "google", "antigravity"]}
            )

        if result and len(result) > 20:
            try:
                await cache_service.set(cache_key, result, expire=604800)
            except Exception:
                pass

        return result

    @staticmethod
    async def analyze_document(file_paths: list[str], prompt: str, provider: str, api_key: str, model: str) -> str:
        """Phân tích nhiều file tài liệu/bản vẽ — gọi analyze_image cho từng file ảnh, tổng hợp kết quả."""
        if not file_paths:
            return "```json\n[]\n```"

        results = []
        image_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

        for fp in file_paths:
            try:
                suffix = Path(fp).suffix.lower()
                if suffix in image_exts:
                    res = await VisionAnalyzerService.analyze_image(fp, prompt, provider, api_key, model)
                else:
                    # Đọc nội dung text của file và phân tích bằng LLM
                    try:
                        with open(fp, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read(20000)
                        file_prompt = f"{prompt}\n\nNội dung file:\n{content}"
                    except Exception:
                        file_prompt = prompt
                    res = await VisionAnalyzerService.analyze_text(file_prompt, provider, api_key, model)
                results.append(res)
            except Exception as e:
                logger.warning(f"analyze_document error on {fp}: {e}")
                continue

        # Ghép nhiều kết quả thành 1 JSON array
        if len(results) == 1:
            return results[0]

        # Khi nhiều file: trả về kết quả của file đầu tiên hợp lệ có dữ liệu
        for r in results:
            if r and "[]" not in r:
                return r
        return results[0] if results else "```json\n[]\n```"

    @staticmethod
    async def _call_openai(
        img_b64: str,
        prompt: str,
        api_key: str,
        model: str,
        base_url: Optional[str] = None,
        provider_name: str = "OpenAI",
    ) -> str:
        """Call OpenAI Vision API với error handling chi tiết"""
        headers = {"Authorization": f"Bearer {api_key}"}
        content = [{"type": "text", "text": prompt}]
        if img_b64:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
            })
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
        }
        if any(r in (model or "").lower() for r in ["o1", "o3", "o4"]):
            payload["reasoning_effort"] = "low"
        
        timeout = float(settings.AI_VISION_TIMEOUT)
        
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=5.0)) as client:
                resp = await client.post(
                    f"{(base_url or settings.AI_COMPATIBLE_DEFAULT_BASE_URL).rstrip('/')}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                
                if resp.status_code == 401:
                    raise AIAuthenticationError(
                        f"Khóa gateway {provider_name} không hợp lệ hoặc đã hết hạn",
                        {"status_code": 401}
                    )
                elif resp.status_code == 429:
                    raise AIRateLimitError(
                        f"Vượt quá giới hạn sử dụng {provider_name}",
                        {"status_code": 429, "response": resp.text}
                    )
                elif resp.status_code >= 500:
                    raise AIVisionError(
                        f"{provider_name} server error: {resp.status_code}",
                        {"status_code": resp.status_code, "response": resp.text}
                    )
                
                resp.raise_for_status()
                data = resp.json()
                
                if "choices" not in data or len(data["choices"]) == 0:
                    raise AIVisionError(
                    f"{provider_name} response không có choices",
                        {"response": data}
                    )
                
                return data["choices"][0]["message"]["content"]
                
        except httpx.TimeoutException as e:
            logger.error(f"{provider_name} timeout after {timeout}s: {str(e)}")
            raise AITimeoutError(
                f"Hết thời gian chờ {int(timeout)}s khi gọi {provider_name}",
                {"timeout": timeout, "error": str(e)}
            )
        except httpx.NetworkError as e:
            logger.error(f"{provider_name} network error: {str(e)}")
            raise AIVisionError(
                f"Lỗi kết nối mạng với {provider_name}: {str(e)}",
                {"error": str(e)}
            )
        except (AIAuthenticationError, AIRateLimitError, AITimeoutError, AIVisionError):
            raise
        except Exception as e:
            logger.error(f"Unexpected {provider_name} error: {str(e)}", exc_info=True)
            raise AIVisionError(
                f"Lỗi không xác định khi gọi {provider_name}: {str(e)}",
                {"error": str(e)}
            )

    @staticmethod
    async def _call_gemini(img_b64: str, prompt: str, api_key: str, model: str, provider_name: str = "Google") -> str:
        """Gọi Google Generative AI trực tiếp."""
        clean_key = api_key.strip()
        target_model = (model or "").strip()
        if target_model.startswith("ag/"):
            target_model = target_model[3:]
        return await VisionAnalyzerService._call_google_genai(img_b64, prompt, clean_key, target_model, provider_name=provider_name)
    
    @staticmethod
    async def _call_antigravity(img_b64: str, prompt: str, token: str, model: str) -> str:
        """Call Antigravity API với OAuth token (xử lý độc lập)"""
        clean_token = token.strip()
        auth_header = clean_token if clean_token.lower().startswith("bearer ") else f"Bearer {clean_token}"
        mapped_model = normalize_antigravity_model(model)
        url = "https://daily-cloudcode-pa.googleapis.com/v1internal:generateContent"
        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json",
            "User-Agent": "antigravity/ide/2.1.1 darwin/arm64",
            "x-request-source": "local",
        }
        req_parts = [{"text": prompt}]
        if img_b64:
            req_parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img_b64}})

        payload = {
            "project": "cloudaicompanion-project",
            "model": mapped_model,
            "userAgent": "antigravity",
            "requestType": "agent",
            "requestId": f"agent/{uuid.uuid4()}/{int(time.time() * 1000)}/{uuid.uuid4()}/1",
            "request": {
                "sessionId": f"-{int(time.time() * 1000)}",
                "contents": [{
                    "role": "user",
                    "parts": req_parts
                }],
                "generationConfig": {
                    "maxOutputTokens": settings.AI_MAX_OUTPUT_TOKENS,
                    "temperature": 0.1,
                }
            }
        }
        
        timeout = float(settings.AI_VISION_TIMEOUT)
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=5.0)) as client:
                resp = await client.post(url, headers=headers, json=payload)
                
                if resp.status_code == 401:
                    raise AIAuthenticationError(
                        "Antigravity OAuth token không hợp lệ hoặc đã hết hạn",
                        {"status_code": 401}
                    )
                elif resp.status_code == 429:
                    raise AIRateLimitError(
                        "Vượt quá giới hạn request Antigravity",
                        {"status_code": 429}
                    )
                
                resp.raise_for_status()
                data = resp.json()
                resp_obj = data.get("response", data)
                candidates = resp_obj.get("candidates", [])
                
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    result = "".join(p.get("text", "") for p in parts if "text" in p)
                    if result:
                        return result
                
                logger.warning(f"Antigravity response không có text: {data}")
                raise AIVisionError(
                    "Antigravity response không chứa text",
                    {"response": data}
                )
                
        except httpx.TimeoutException as e:
            logger.error(f"Antigravity timeout sau {int(timeout)}s: {str(e)}")
            raise AITimeoutError(
                f"Hết thời gian chờ {int(timeout)}s khi gọi Antigravity API",
                {"timeout": timeout, "error": str(e)}
            )
        except (AIAuthenticationError, AIRateLimitError, AITimeoutError, AIVisionError):
            raise
        except Exception as e:
            logger.error(f"Unexpected Antigravity error: {str(e)}", exc_info=True)
            raise AIVisionError(
                f"Lỗi không xác định khi gọi Antigravity: {str(e)}",
                {"error": str(e)}
            )
    
    @staticmethod
    async def _call_google_genai(
        img_b64: str,
        prompt: str,
        api_key: str,
        target_model: str,
        provider_name: str = "Google"
    ) -> str:
        """Call Google Generative AI API (Google API key) — chỉ dùng model được chỉ định, không tự ý fallback sang model khác."""
        # Làm sạch suffix tiered/quality khỏi tên model
        clean_model_name = (
            target_model
            .replace("-tiered(high)", "")
            .replace("-tiered(medium)", "")
            .replace("-tiered(low)", "")
            .replace("-high", "")
            .replace("-medium", "")
            .replace("-low", "")
        )

        # A model must be selected in BE; never silently select a default.
        if not clean_model_name:
            raise AIVisionError(
                "Chưa chọn model cho kết nối AI trong BE.",
                {"hint": "missing_selected_model"},
            )

        # Nếu model không phải Gemini (ví dụ claude-*, gpt-*) → báo lỗi ngay, không chuyển ngầm
        if "claude" in clean_model_name.lower() or "gpt" in clean_model_name.lower():
            raise AIVisionError(
                f"Model '{clean_model_name}' không tương thích với Google API Key. "
                "Vui lòng kiểm tra lại cấu hình provider và model trong Admin → Kết nối AI. "
                "Chỉ sử dụng API Key này với các model Gemini (ví dụ: gemini-2.5-flash, gemini-2.5-pro).",
                {"model": clean_model_name, "provider": provider_name, "hint": "use_gemini_model"}
            )

        # Gọi DUY NHẤT model được chỉ định — tắt thinking/reasoning để tối ưu tốc độ
        timeout = float(settings.AI_VISION_TIMEOUT)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model_name}:generateContent?key={api_key}"
        gen_parts = [{"text": prompt}]
        if img_b64:
            gen_parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img_b64}})

        generation_config = {
            "maxOutputTokens": settings.AI_MAX_OUTPUT_TOKENS,
            "temperature": 0.1,
        }

        payload = {
            "contents": [{
                "parts": gen_parts
            }],
            "generationConfig": generation_config
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=5.0)) as client:
            try:
                logger.info(f"Calling exact model: {clean_model_name} via {provider_name} (thinking disabled, timeout={timeout}s)")
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    if "candidates" in data and len(data["candidates"]) > 0:
                        content = data["candidates"][0].get("content", {})
                        parts = content.get("parts", [])
                        text_parts = [p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p]
                        full_text = "".join(text_parts).strip()
                        if full_text:
                            return full_text
                    raise AIVisionError(
                        f"Model '{clean_model_name}' không trả về nội dung text hợp lệ",
                        {"response": data, "model": clean_model_name}
                    )

                if resp.status_code == 401:
                    raise AIAuthenticationError(
                        f"Khóa API {provider_name} không hợp lệ hoặc đã hết hạn",
                        {"status_code": 401}
                    )
                elif resp.status_code == 429:
                    retry_note = ""
                    try:
                        err_j = resp.json()
                        msg = err_j.get("error", {}).get("message", "")
                        for line in msg.split("\n"):
                            if "Please retry in" in line or "Quota exceeded" in line:
                                retry_note = f" [{line.strip()}]"
                                break
                    except Exception:
                        pass
                    raise AIRateLimitError(
                        f"{provider_name} API (model '{clean_model_name}') trả về HTTP 429: Vượt quá giới hạn hạn ngạch{retry_note}.",
                        {"status_code": 429, "model": clean_model_name, "detail": resp.text[:300]}
                    )
                elif resp.status_code == 404:
                    raise AIVisionError(
                        f"Model '{clean_model_name}' không tồn tại hoặc không được hỗ trợ trên cổng {provider_name}.",
                        {"status_code": 404, "model": clean_model_name}
                    )
                elif resp.status_code == 400:
                    raise AIVisionError(
                        f"Yêu cầu không hợp lệ khi gọi {provider_name} model '{clean_model_name}': {resp.text[:300]}",
                        {"status_code": 400, "model": clean_model_name}
                    )
                elif resp.status_code == 503:
                    raise AIVisionError(
                        f"{provider_name} service tạm thời không khả dụng (503) — model: {clean_model_name}.",
                        {"status_code": 503, "model": clean_model_name}
                    )
                else:
                    resp.raise_for_status()

            except httpx.TimeoutException as e:
                raise AITimeoutError(
                    f"Hết thời gian chờ {int(timeout)}s khi gọi {provider_name} model '{clean_model_name}'",
                    {"timeout": timeout, "model": clean_model_name, "error": str(e)}
                )
            except (AIAuthenticationError, AIRateLimitError, AITimeoutError, AIVisionError):
                raise
            except Exception as ex:
                raise AIVisionError(
                    f"Lỗi khi gọi {provider_name} model '{clean_model_name}': {str(ex)}",
                    {"model": clean_model_name, "error": str(ex)}
                )
