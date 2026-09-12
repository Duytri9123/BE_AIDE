import time
import uuid
import base64
import httpx
import logging
import asyncio
import re
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List

from app.core.config import settings
from app.services.cache_service import cache_service
from app.services.ai.token_refresh_service import TokenRefreshService
from app.core.exceptions import (
    AIVisionError,
    AITimeoutError,
    AIRateLimitError,
    AIAuthenticationError,
    ImageParsingError
)

logger = logging.getLogger(__name__)

ANTIGRAVITY_IDE_USER_AGENT = "antigravity/ide/2.11.0 darwin/arm64"
CODEX_CLI_USER_AGENT = "codex_cli_rs/0.154.0"

# Mặc định base URL cho các provider OpenAI-compatible
DEFAULT_PROVIDER_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "groq": "https://api.groq.com/openai/v1",
    "xai": "https://api.x.ai/v1",
    "mistral": "https://api.mistral.ai/v1",
    "ollama": "http://localhost:11434/v1",
    "deepseek": "https://api.deepseek.com/v1",
}


def normalize_antigravity_model(model: str) -> str:
    """Chuẩn hóa tên model cho Google Antigravity (daily-cloudcode-pa.googleapis.com).

    Endpoint Google Cloud Code v1internal chỉ chấp nhận chính xác các model sau:
    - 'gemini-2.5-flash' cho các model Gemini Flash (mọi biến thể 3.x/2.x flash, tiered)
    - 'gemini-2.5-pro' cho Gemini Pro
    - 'claude-sonnet-4-6' cho Claude Sonnet / Opus
    - 'gpt-oss-120b-medium' cho GPT-OSS
    Lưu ý: Google API sẽ trả về HTTP 404 nếu gắn hậu tố -tiered(...) hoặc -high/-medium/-low.
    """
    clean_model = (model or "").lower().strip()
    if clean_model.startswith("ag/"):
        clean_model = clean_model[3:]
    if clean_model.startswith("models/"):
        clean_model = clean_model[7:]

    # Loại bỏ các hậu tố tiered và priority
    clean_model = re.sub(r"-tiered\([a-z]+\)", "", clean_model)
    clean_model = re.sub(r"-(high|medium|low)$", "", clean_model)
    clean_model = clean_model.strip()

    if not clean_model:
        return "gemini-2.5-flash"

    # Claude models
    if any(k in clean_model for k in ("claude", "sonnet", "opus")):
        return "claude-sonnet-4-6"

    # GPT / OSS models
    if any(k in clean_model for k in ("gpt", "oss")):
        return "gpt-oss-120b-medium"

    # Gemini Pro
    if "pro" in clean_model:
        return "gemini-2.5-pro"

    # Tất cả các biến thể Gemini Flash (3.8, 3.7, 3.6, 3.5, 2.5, 2.0, 1.5, flash)
    if "flash" in clean_model or "gemini" in clean_model:
        return "gemini-2.5-flash"

    return clean_model


class VisionAnalyzerService:
    @staticmethod
    async def analyze_image(
        image_path: str,
        prompt: str,
        provider: str,
        api_key: str,
        model: str,
        base_url: Optional[str] = None,
        enable_web_search: bool = False,
        project_id: Optional[str] = None,
    ) -> str:
        """Gọi API AI Vision (Gemini/OpenAI/Claude/Antigravity/Codex/OpenRouter/Groq/etc.) để phân tích hình ảnh."""
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
            
            prov = (provider or "").lower().strip()
            img_hash = hashlib.sha256(img_bytes).hexdigest()
            prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
            cache_key = f"ai_vision:{img_hash}:{prov}:{model.lower()}:{prompt_hash}:{enable_web_search}"

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
            if prov == "antigravity":
                if api_key and api_key.strip().startswith("AIza"):
                    logger.info("[VisionAnalyzerService] Phát hiện API Key Google Studio (AIza) trong cấu hình Antigravity -> Tự động chuyển hướng sang Google Gemini API an toàn.")
                    cleaned_model = model.removeprefix("ag/") if model.startswith("ag/") else model
                    if not cleaned_model or "gemini" not in cleaned_model.lower():
                        cleaned_model = "gemini-2.5-flash"
                    result = await VisionAnalyzerService._call_google_genai(
                        img_b64, prompt, api_key, cleaned_model, provider_name="Google", enable_web_search=enable_web_search
                    )
                else:
                    result = await VisionAnalyzerService._call_antigravity(
                        img_b64, prompt, api_key, model, enable_web_search=enable_web_search, project_id=project_id
                    )
            elif prov == "codex":
                result = await VisionAnalyzerService._call_codex(
                    img_b64, prompt, api_key, model, base_url=base_url
                )
            elif prov in ("anthropic", "claude"):
                result = await VisionAnalyzerService._call_anthropic(
                    img_b64, prompt, api_key, model
                )
            elif prov in ("gemini", "google"):
                cleaned_model = model
                if cleaned_model.startswith("ag/"):
                    cleaned_model = cleaned_model[3:]
                result = await VisionAnalyzerService._call_google_genai(
                    img_b64, prompt, api_key, cleaned_model, provider_name="Google", enable_web_search=enable_web_search
                )
            elif prov == "openai":
                result = await VisionAnalyzerService._call_openai(
                    img_b64, prompt, api_key, model, base_url=base_url, provider_name="OpenAI"
                )
            elif prov in DEFAULT_PROVIDER_BASE_URLS or base_url:
                # OpenRouter, Groq, xAI, Mistral, Ollama, DeepSeek...
                result = await VisionAnalyzerService._call_openai_compatible(
                    img_b64, prompt, api_key, model, base_url=base_url, provider_name=provider
                )
            else:
                raise AIVisionError(
                    f"Provider không được hỗ trợ: {provider}",
                    {"provider": provider, "supported": ["antigravity", "codex", "openai", "anthropic", "gemini", "google", "openrouter", "groq", "xai", "mistral", "ollama"]}
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
    async def analyze_text(
        prompt: str,
        provider: str,
        api_key: str,
        model: str,
        base_url: Optional[str] = None,
        enable_web_search: bool = False,
        project_id: Optional[str] = None,
    ) -> str:
        """Gọi API AI LLM để phân tích dữ liệu văn bản/sơ đồ kỹ thuật."""
        prov = (provider or "").lower().strip()
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        cache_key = f"ai_text:{prov}:{model.lower()}:{prompt_hash}:{enable_web_search}"

        try:
            cached_res = await cache_service.get(cache_key)
            if cached_res:
                logger.info(f"[VisionAnalyzerService] Cache HIT cho text prompt ({provider}/{model}). Trả về ngay lập tức.")
                return cached_res
        except Exception:
            pass

        result = None
        if prov == "antigravity":
            if api_key and api_key.strip().startswith("AIza"):
                logger.info("[VisionAnalyzerService] Phát hiện API Key Google Studio (AIza) trong cấu hình Antigravity -> Tự động chuyển hướng sang Google Gemini API an toàn.")
                cleaned_model = model.removeprefix("ag/") if model.startswith("ag/") else model
                if not cleaned_model or "gemini" not in cleaned_model.lower():
                    cleaned_model = "gemini-2.5-flash"
                result = await VisionAnalyzerService._call_google_genai(
                    "", prompt, api_key, cleaned_model, provider_name="Google", enable_web_search=enable_web_search
                )
            else:
                result = await VisionAnalyzerService._call_antigravity(
                    "", prompt, api_key, model, enable_web_search=enable_web_search, project_id=project_id
                )
        elif prov == "codex":
            result = await VisionAnalyzerService._call_codex(
                "", prompt, api_key, model, base_url=base_url
            )
        elif prov in ("anthropic", "claude"):
            result = await VisionAnalyzerService._call_anthropic(
                "", prompt, api_key, model
            )
        elif prov in ("gemini", "google"):
            cleaned_model = model
            if cleaned_model.startswith("ag/"):
                cleaned_model = cleaned_model[3:]
            result = await VisionAnalyzerService._call_google_genai(
                "", prompt, api_key, cleaned_model, provider_name="Google", enable_web_search=enable_web_search
            )
        elif prov == "openai":
            result = await VisionAnalyzerService._call_openai(
                "", prompt, api_key, model, base_url=base_url, provider_name="OpenAI"
            )
        elif prov in DEFAULT_PROVIDER_BASE_URLS or base_url:
            # OpenRouter, Groq, xAI, Mistral, Ollama, DeepSeek...
            result = await VisionAnalyzerService._call_openai_compatible(
                "", prompt, api_key, model, base_url=base_url, provider_name=provider
            )
        else:
            raise AIVisionError(
                f"Provider không được hỗ trợ: {provider}",
                {"provider": provider, "supported": ["antigravity", "codex", "openai", "anthropic", "gemini", "google", "openrouter", "groq", "xai", "mistral", "ollama"]}
            )

        if result and len(result) > 20:
            try:
                await cache_service.set(cache_key, result, expire=604800)
            except Exception:
                pass

        return result

    @staticmethod
    async def analyze_document(
        file_paths: list[str],
        prompt: str,
        provider: str,
        api_key: str,
        model: str,
        base_url: Optional[str] = None,
        enable_web_search: bool = False
    ) -> str:
        """Phân tích nhiều file tài liệu/bản vẽ — gọi analyze_image cho từng file ảnh, tổng hợp kết quả."""
        if not file_paths:
            return "```json\n[]\n```"

        results = []
        image_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

        for fp in file_paths:
            try:
                suffix = Path(fp).suffix.lower()
                if suffix in image_exts:
                    res = await VisionAnalyzerService.analyze_image(
                        fp, prompt, provider, api_key, model, base_url=base_url, enable_web_search=enable_web_search
                    )
                else:
                    # Đọc nội dung text của file và phân tích bằng LLM
                    try:
                        with open(fp, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read(20000)
                        file_prompt = f"{prompt}\n\nNội dung file:\n{content}"
                    except Exception:
                        file_prompt = prompt
                    res = await VisionAnalyzerService.analyze_text(
                        file_prompt, provider, api_key, model, base_url=base_url, enable_web_search=enable_web_search
                    )
                results.append(res)
            except Exception as e:
                logger.warning(f"analyze_document error on {fp}: {e}")
                continue

        if len(results) == 1:
            return results[0]

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
        target_base = (base_url or settings.AI_COMPATIBLE_DEFAULT_BASE_URL).rstrip("/")
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json"
        }
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
                    f"{target_base}/chat/completions",
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
    async def _call_openai_compatible(
        img_b64: str,
        prompt: str,
        api_key: str,
        model: str,
        base_url: Optional[str] = None,
        provider_name: str = "OpenAI Compatible",
    ) -> str:
        """Call các nhà cung cấp chuẩn OpenAI-compatible (OpenRouter, Groq, xAI, Mistral, Ollama)."""
        prov_key = (provider_name or "").lower().strip()
        default_url = DEFAULT_PROVIDER_BASE_URLS.get(prov_key, settings.AI_COMPATIBLE_DEFAULT_BASE_URL)
        target_base = (base_url or default_url).rstrip("/")

        headers = {
            "Content-Type": "application/json"
        }
        if api_key and api_key.strip():
            headers["Authorization"] = f"Bearer {api_key.strip()}"

        content = [{"type": "text", "text": prompt}]
        if img_b64:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
            })

        payload: Dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0.1,
        }

        timeout = float(settings.AI_VISION_TIMEOUT)
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=5.0)) as client:
                resp = await client.post(
                    f"{target_base}/chat/completions",
                    json=payload,
                    headers=headers,
                )

                if resp.status_code == 401:
                    raise AIAuthenticationError(
                        f"Khóa API {provider_name} không hợp lệ hoặc đã hết hạn",
                        {"status_code": 401, "provider": provider_name}
                    )
                elif resp.status_code == 429:
                    raise AIRateLimitError(
                        f"Vượt quá giới hạn request {provider_name} (429)",
                        {"status_code": 429, "provider": provider_name}
                    )
                elif resp.status_code >= 500:
                    raise AIVisionError(
                        f"{provider_name} server error: {resp.status_code}",
                        {"status_code": resp.status_code, "response": resp.text[:300]}
                    )

                resp.raise_for_status()
                data = resp.json()
                choices = data.get("choices", [])
                if not choices:
                    raise AIVisionError(
                        f"{provider_name} không trả về choices",
                        {"response": data}
                    )
                return choices[0].get("message", {}).get("content", "")

        except httpx.TimeoutException as e:
            raise AITimeoutError(
                f"Hết thời gian chờ {int(timeout)}s khi gọi {provider_name}",
                {"timeout": timeout, "error": str(e)}
            )
        except (AIAuthenticationError, AIRateLimitError, AITimeoutError, AIVisionError):
            raise
        except Exception as e:
            logger.error(f"Unexpected {provider_name} error: {str(e)}", exc_info=True)
            raise AIVisionError(
                f"Lỗi khi gọi {provider_name}: {str(e)}",
                {"error": str(e)}
            )

    @staticmethod
    async def _call_codex(
        img_b64: str,
        prompt: str,
        api_key: str,
        model: str,
        base_url: Optional[str] = None
    ) -> str:
        """
        Call OpenAI Codex Engine:
        - Nếu API Key là OpenAI API key thông thường (sk-...) -> gọi qua OpenAI API standard.
        - Nếu là Codex OAuth Token hoặc kết nối ChatGPT Backend -> gọi qua Responses API
          https://chatgpt.com/backend-api/codex/responses với header codex_cli_rs/0.154.0.
        """
        clean_key = api_key.strip()
        is_standard_openai_key = clean_key.startswith("sk-") or (base_url and "api.openai.com" in base_url)

        if is_standard_openai_key and not (base_url and "backend-api/codex" in base_url):
            # Gọi qua OpenAI API tiêu chuẩn
            return await VisionAnalyzerService._call_openai(
                img_b64, prompt, clean_key, model, base_url=base_url, provider_name="Codex (OpenAI API)"
            )

        # Gọi qua OpenAI Codex Responses API (Chuẩn 9router)
        codex_url = (base_url or "https://chatgpt.com/backend-api/codex/responses").rstrip("/")
        if not codex_url.endswith("/responses"):
            codex_url = f"{codex_url}/responses"

        auth_header = clean_key if clean_key.lower().startswith("bearer ") else f"Bearer {clean_key}"
        session_id = f"sess-{uuid.uuid4().hex[:12]}"

        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json",
            "User-Agent": CODEX_CLI_USER_AGENT,
            "originator": "codex_cli_rs",
            "session_id": session_id,
        }

        content_parts: List[Dict[str, Any]] = [{"type": "input_text", "text": prompt}]
        if img_b64:
            content_parts.append({
                "type": "input_image",
                "image_url": f"data:image/jpeg;base64,{img_b64}"
            })

        payload = {
            "model": model,
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": content_parts
                }
            ],
            "store": False,
            "stream": False,
            "instructions": "You are an expert AI assistant specializing in CAD drawings, electrical single-line diagrams, and BOM extraction.",
            "reasoning": {
                "effort": "low",
                "summary": "auto"
            },
            "include": ["reasoning.encrypted_content"]
        }

        timeout = float(settings.AI_VISION_TIMEOUT)
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=5.0)) as client:
                resp = await client.post(codex_url, headers=headers, json=payload)
                resp_text = resp.text

                # Bắt lỗi capacity / overloaded ẩn
                lower_text = resp_text.lower()
                if "selected model is at capacity" in lower_text or "model_at_capacity" in lower_text:
                    raise AIRateLimitError(
                        f"Codex: Mô hình '{model}' hiện đang quá tải (at capacity). Vui lòng thử lại sau.",
                        {"model": model, "error": "model_at_capacity"}
                    )
                if "server_is_overloaded" in lower_text:
                    raise AIRateLimitError(
                        "Codex: Máy chủ quá tải (server_is_overloaded). Vui lòng thử lại sau.",
                        {"model": model, "error": "server_is_overloaded"}
                    )

                if resp.status_code == 401:
                    raise AIAuthenticationError(
                        "Codex access token không hợp lệ hoặc đã hết hạn",
                        {"status_code": 401}
                    )
                elif resp.status_code == 429:
                    raise AIRateLimitError(
                        "Vượt quá giới hạn sử dụng OpenAI Codex (429)",
                        {"status_code": 429}
                    )

                resp.raise_for_status()
                data = resp.json()

                # Responses API extraction
                if "output" in data and isinstance(data["output"], list):
                    for item in data["output"]:
                        if item.get("type") == "message":
                            parts = item.get("content", [])
                            text = "".join(p.get("text", "") for p in parts if p.get("type") in ("output_text", "text"))
                            if text:
                                return text

                # Fallback format: choices
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]

                raise AIVisionError(
                    "Codex response không có nội dung văn bản hợp lệ",
                    {"response": data}
                )

        except (AIAuthenticationError, AIRateLimitError, AITimeoutError, AIVisionError):
            raise
        except httpx.TimeoutException as e:
            raise AITimeoutError(
                f"Hết thời gian chờ {int(timeout)}s khi gọi Codex API",
                {"timeout": timeout, "error": str(e)}
            )
        except Exception as e:
            logger.error(f"Unexpected Codex error: {str(e)}", exc_info=True)
            raise AIVisionError(
                f"Lỗi khi gọi Codex: {str(e)}",
                {"error": str(e)}
            )

    @staticmethod
    async def _call_anthropic(
        img_b64: str,
        prompt: str,
        api_key: str,
        model: str
    ) -> str:
        """Call Anthropic Messages API (Claude 3.5 / Claude 3) với Vision & Text."""
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key.strip(),
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        content_parts: List[Dict[str, Any]] = []
        if img_b64:
            content_parts.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": img_b64
                }
            })
        content_parts.append({
            "type": "text",
            "text": prompt
        })

        payload = {
            "model": model,
            "max_tokens": settings.AI_MAX_OUTPUT_TOKENS,
            "messages": [{"role": "user", "content": content_parts}]
        }

        timeout = float(settings.AI_VISION_TIMEOUT)
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=5.0)) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 401:
                    raise AIAuthenticationError(
                        "Khóa API Anthropic không hợp lệ",
                        {"status_code": 401}
                    )
                elif resp.status_code == 429:
                    raise AIRateLimitError(
                        "Vượt quá giới hạn request Anthropic (429)",
                        {"status_code": 429}
                    )
                elif resp.status_code >= 500:
                    raise AIVisionError(
                        f"Anthropic server error: {resp.status_code}",
                        {"status_code": resp.status_code, "response": resp.text[:300]}
                    )

                resp.raise_for_status()
                data = resp.json()
                content = data.get("content", [])
                text_parts = [p.get("text", "") for p in content if p.get("type") == "text"]
                result = "".join(text_parts).strip()
                if result:
                    return result
                raise AIVisionError("Anthropic response không chứa text", {"response": data})

        except (AIAuthenticationError, AIRateLimitError, AITimeoutError, AIVisionError):
            raise
        except httpx.TimeoutException as e:
            raise AITimeoutError(
                f"Hết thời gian chờ {int(timeout)}s khi gọi Anthropic",
                {"timeout": timeout, "error": str(e)}
            )
        except Exception as e:
            logger.error(f"Unexpected Anthropic error: {str(e)}", exc_info=True)
            raise AIVisionError(f"Lỗi khi gọi Anthropic: {str(e)}", {"error": str(e)})

    @staticmethod
    async def _call_gemini(img_b64: str, prompt: str, api_key: str, model: str, provider_name: str = "Google") -> str:
        """Gọi Google Generative AI trực tiếp."""
        clean_key = api_key.strip()
        target_model = (model or "").strip()
        if target_model.startswith("ag/"):
            target_model = target_model[3:]
        return await VisionAnalyzerService._call_google_genai(img_b64, prompt, clean_key, target_model, provider_name=provider_name)
    
    @staticmethod
    async def _call_antigravity(
        img_b64: str,
        prompt: str,
        token: str,
        model: str,
        enable_web_search: bool = False,
        project_id: Optional[str] = None
    ) -> str:
        """Call Antigravity API với OAuth token (chuẩn 9router: User-Agent 2.11.0, requestId, anti-ban)."""
        clean_token = token.strip()
        # 1. Đổi refresh token 1//... sang access token ya29... nếu cần
        if clean_token.startswith("1//"):
            active_token = await TokenRefreshService.get_active_token(clean_token)
        else:
            active_token = clean_token
        auth_header = active_token if active_token.lower().startswith("bearer ") else f"Bearer {active_token}"
        mapped_model = normalize_antigravity_model(model)

        # 2. Lấy project ID thực tế hoặc dùng default 'aicode-consumers'
        pid = project_id
        if not pid or pid in ("cloudaicompanion-project", ""):
            try:
                real_pid = await TokenRefreshService.get_project_id(active_token)
                pid = real_pid or "aicode-consumers"
            except Exception:
                pid = "aicode-consumers"
        if not pid:
            pid = "aicode-consumers"

        url = "https://daily-cloudcode-pa.googleapis.com/v1internal:generateContent"
        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json",
            "User-Agent": ANTIGRAVITY_IDE_USER_AGENT,
            "x-request-source": "local",
        }
        req_parts = [{"text": prompt}]
        if img_b64:
            req_parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img_b64}})

        tools = []
        if enable_web_search:
            tools.append({"googleSearch": {}})

        payload: Dict[str, Any] = {
            "project": pid,
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
        if tools:
            payload["request"]["tools"] = tools
        
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
                        f"Vượt quá giới hạn request Antigravity cho model '{mapped_model}' (429)",
                        {"status_code": 429, "model": mapped_model}
                    )
                elif resp.status_code == 404:
                    raise AIVisionError(
                        f"Mô hình Antigravity '{mapped_model}' không tồn tại trên máy chủ Google (HTTP 404).",
                        {"status_code": 404, "model": mapped_model, "response": resp.text[:300]}
                    )
                elif resp.status_code >= 500:
                    raise AIVisionError(
                        f"Antigravity server error ({resp.status_code}): {resp.text[:300]}",
                        {"status_code": resp.status_code}
                    )
                
                resp.raise_for_status()
                data = resp.json()
                resp_obj = data.get("response", data)
                candidates = resp_obj.get("candidates", [])
                
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    text_parts = [p.get("text", "") for p in parts if isinstance(p, dict) and p.get("text") and not p.get("thought")]
                    if not text_parts:
                        text_parts = [p.get("text", "") for p in parts if isinstance(p, dict) and p.get("text")]
                    result = "".join(text_parts).strip()
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
        provider_name: str = "Google",
        enable_web_search: bool = False,
    ) -> str:
        """Call Google Generative AI API (Google API key) — chỉ dùng model được chỉ định, không tự ý fallback sang model khác."""
        clean_model_name = (
            target_model
            .replace("-tiered(high)", "")
            .replace("-tiered(medium)", "")
            .replace("-tiered(low)", "")
            .replace("-high", "")
            .replace("-medium", "")
            .replace("-low", "")
        )

        if not clean_model_name:
            raise AIVisionError(
                "Chưa chọn model cho kết nối AI trong BE.",
                {"hint": "missing_selected_model"},
            )

        if "claude" in clean_model_name.lower() or "gpt" in clean_model_name.lower():
            raise AIVisionError(
                f"Model '{clean_model_name}' không tương thích với Google API Key. "
                "Vui lòng kiểm tra lại cấu hình provider và model trong Admin → Kết nối AI. "
                "Chỉ sử dụng API Key này với các model Gemini (ví dụ: gemini-2.5-flash, gemini-2.5-pro).",
                {"model": clean_model_name, "provider": provider_name, "hint": "use_gemini_model"}
            )

        timeout = float(settings.AI_VISION_TIMEOUT)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model_name}:generateContent?key={api_key}"
        gen_parts = [{"text": prompt}]
        if img_b64:
            gen_parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img_b64}})

        generation_config = {
            "maxOutputTokens": settings.AI_MAX_OUTPUT_TOKENS,
            "temperature": 0.1,
        }

        payload: Dict[str, Any] = {
            "contents": [{
                "parts": gen_parts
            }],
            "generationConfig": generation_config
        }
        if enable_web_search:
            payload["tools"] = [{"google_search": {}}]

        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=5.0)) as client:
            try:
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
