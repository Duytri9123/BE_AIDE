"""
WebSearch Service - Hệ thống tìm kiếm trực tuyến và AI Search Grounding.
Được thiết kế dựa trên kiến trúc 9router (open-sse/handlers/search):
- Antigravity Grounding qua `v1internal:generateContent` kèm tool `googleSearch`
- Google Gemini Grounding qua `generativelanguage.googleapis.com` kèm tool `google_search`
- OpenAI Web Search qua tool `web_search`
- Hỗ trợ các API tìm kiếm chuyên dụng (Tavily, Serper, Brave Search)
- Chuẩn hóa đầu ra thống nhất (Unified Search Result Shape)
"""

import time
import uuid
import re
import logging
from typing import Optional, Dict, Any, List
import httpx

from app.core.config import settings
from app.services.cache_service import cache_service
from app.services.ai.vision_analyzer import normalize_antigravity_model

logger = logging.getLogger(__name__)

ANTIGRAVITY_IDE_USER_AGENT = "antigravity/ide/2.11.0 darwin/arm64"
SEARCH_TIMEOUT = 25.0


class WebSearchService:
    """Service tìm kiếm và grounding thông tin từ web cho AI."""

    @staticmethod
    def _sanitize_query(query: str) -> str:
        """Làm sạch câu lệnh tìm kiếm, loại bỏ control characters."""
        if not query:
            return ""
        # Loại bỏ control characters
        clean = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", query)
        return clean.strip()

    @staticmethod
    def _expand_segment(text: str, segment: Dict[str, Any], before: int = 150, after: int = 250) -> str:
        """Mở rộng đoạn text trích dẫn về các câu xung quanh trong câu trả lời (giống expandSegment của 9router)."""
        start_idx = segment.get("startIndex")
        end_idx = segment.get("endIndex")
        if not text or not isinstance(start_idx, int) or not isinstance(end_idx, int):
            return ""
        start = max(0, start_idx - before)
        end = min(len(text), end_idx + after)
        snippet = text[start:end].strip()
        if start > 0:
            snippet = f"...{re.sub(r'^\S+', '', snippet)}"
        if end < len(text):
            snippet = f"{re.sub(r'\S+$', '', snippet)}..."
        return snippet.strip()

    @staticmethod
    async def search(
        query: str,
        provider: str,
        api_key: str,
        model: Optional[str] = None,
        max_results: int = 5,
        project_id: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Thực hiện tìm kiếm trực tuyến thông qua provider được chọn.
        Trả về kết quả chuẩn hóa dạng:
        {
            "success": bool,
            "provider": str,
            "query": str,
            "answer": str,
            "results": [
                {
                    "title": str,
                    "url": str,
                    "snippet": str,
                    "position": int,
                    "content": Optional[str]
                }
            ],
            "latency_ms": int,
            "error": Optional[str]
        }
        """
        clean_query = WebSearchService._sanitize_query(query)
        if not clean_query:
            return {
                "success": False,
                "provider": provider,
                "query": query,
                "answer": "",
                "results": [],
                "latency_ms": 0,
                "error": "Câu truy vấn tìm kiếm trống"
            }

        prov = (provider or "").lower().strip()
        cache_key = f"web_search:{prov}:{clean_query[:100]}:{max_results}"

        # Kiểm tra cache
        try:
            cached = await cache_service.get(cache_key)
            if cached and isinstance(cached, dict):
                return cached
        except Exception:
            pass

        start_time = time.time()
        try:
            if prov == "antigravity":
                result = await WebSearchService._search_antigravity(
                    clean_query, api_key, model=model, max_results=max_results, project_id=project_id
                )
            elif prov in ("google", "gemini"):
                result = await WebSearchService._search_google_gemini(
                    clean_query, api_key, model=model, max_results=max_results
                )
            elif prov in ("tavily",):
                result = await WebSearchService._search_tavily(
                    clean_query, api_key, max_results=max_results
                )
            elif prov in ("serper",):
                result = await WebSearchService._search_serper(
                    clean_query, api_key, max_results=max_results
                )
            elif prov in ("brave", "brave-search"):
                result = await WebSearchService._search_brave(
                    clean_query, api_key, max_results=max_results
                )
            elif prov in ("openai", "codex"):
                result = await WebSearchService._search_openai(
                    clean_query, api_key, model=model, base_url=base_url
                )
            else:
                # Mặc định thử qua Google Gemini hoặc báo lỗi
                result = await WebSearchService._search_google_gemini(
                    clean_query, api_key, model=model, max_results=max_results
                )

            elapsed_ms = int((time.time() - start_time) * 1000)
            result["latency_ms"] = elapsed_ms

            # Cache kết quả trong 1 ngày nếu thành công
            if result.get("success"):
                try:
                    await cache_service.set(cache_key, result, expire=86400)
                except Exception:
                    pass

            return result

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[WebSearchService] Search error ({prov}): {str(e)}", exc_info=True)
            return {
                "success": False,
                "provider": prov,
                "query": clean_query,
                "answer": "",
                "results": [],
                "latency_ms": elapsed_ms,
                "error": str(e)
            }

    @staticmethod
    async def _search_antigravity(
        query: str,
        token: str,
        model: Optional[str] = None,
        max_results: int = 5,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Tìm kiếm có grounding qua Google Antigravity.
        Endpoint: daily-cloudcode-pa.googleapis.com/v1internal:generateContent
        Tool: googleSearch
        """
        clean_token = token.strip()
        auth_header = clean_token if clean_token.lower().startswith("bearer ") else f"Bearer {clean_token}"
        target_model = normalize_antigravity_model(model or "ag/gemini-2.5-flash")
        pid = project_id or "cloudaicompanion-project"

        url = "https://daily-cloudcode-pa.googleapis.com/v1internal:generateContent"
        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json",
            "User-Agent": ANTIGRAVITY_IDE_USER_AGENT,
            "x-request-source": "local",
        }

        payload = {
            "project": pid,
            "model": target_model,
            "userAgent": "antigravity",
            "requestType": "search",
            "requestId": f"agent/{uuid.uuid4()}/{int(time.time() * 1000)}/{uuid.uuid4()}/1",
            "request": {
                "sessionId": f"-{int(time.time() * 1000)}",
                "contents": [{
                    "role": "user",
                    "parts": [{"text": query}]
                }],
                "tools": [{"googleSearch": {}}],
                "generationConfig": {
                    "temperature": 1.0,
                    "maxOutputTokens": 4096
                }
            }
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(SEARCH_TIMEOUT, connect=5.0)) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 401:
                raise Exception("Antigravity OAuth Bearer token không hợp lệ hoặc đã hết hạn.")
            elif resp.status_code == 429:
                raise Exception("Antigravity API bị giới hạn tần suất request (429).")
            resp.raise_for_status()

            data = resp.json()
            resp_obj = data.get("response", data)
            candidates = resp_obj.get("candidates", [])
            if not candidates:
                return {
                    "success": True,
                    "provider": "antigravity",
                    "query": query,
                    "answer": "",
                    "results": []
                }

            candidate = candidates[0]
            parts = candidate.get("content", {}).get("parts", [])
            answer_text = "".join(p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p).strip()

            # Parse grounding metadata
            grounding = candidate.get("groundingMetadata", {})
            chunks = grounding.get("groundingChunks", [])
            supports = grounding.get("groundingSupports", [])

            sources_map: Dict[str, Dict[str, Any]] = {}
            indexed_sources: List[Optional[Dict[str, Any]]] = []

            for ch in chunks:
                web = ch.get("web")
                if not web:
                    indexed_sources.append(None)
                    continue
                url_str = web.get("uri") or web.get("url") or ""
                if not url_str:
                    indexed_sources.append(None)
                    continue
                if url_str not in sources_map:
                    sources_map[url_str] = {
                        "title": web.get("title") or url_str,
                        "url": url_str,
                        "snippets": set(),
                        "contexts": set()
                    }
                indexed_sources.append(sources_map[url_str])

            for s in supports:
                segment = s.get("segment", {})
                grounded_text = segment.get("text", "")
                expanded_text = WebSearchService._expand_segment(answer_text, segment) or grounded_text
                chunk_indices = s.get("groundingChunkIndices", [])
                for idx in chunk_indices:
                    if isinstance(idx, int) and 0 <= idx < len(indexed_sources):
                        src = indexed_sources[idx]
                        if src:
                            if grounded_text:
                                src["snippets"].add(grounded_text)
                            if expanded_text:
                                src["contexts"].add(expanded_text)

            results: List[Dict[str, Any]] = []
            pos = 1
            for url_str, item in sources_map.items():
                snippets = " | ".join(item["snippets"]) if item["snippets"] else item["title"]
                context_str = "\n\n".join(item["contexts"]) if item["contexts"] else snippets
                results.append({
                    "position": pos,
                    "title": item["title"],
                    "url": url_str,
                    "snippet": snippets,
                    "content": context_str
                })
                pos += 1
                if pos > max_results:
                    break

            return {
                "success": True,
                "provider": "antigravity",
                "query": query,
                "answer": answer_text,
                "results": results
            }

    @staticmethod
    async def _search_google_gemini(
        query: str,
        api_key: str,
        model: Optional[str] = None,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Tìm kiếm có Google Search Grounding qua Gemini API Key chuẩn.
        Endpoint: generativelanguage.googleapis.com/v1beta/models/...
        Tool: google_search
        """
        clean_key = api_key.strip()
        target_model = (model or "gemini-2.5-flash").strip()
        if target_model.startswith("ag/"):
            target_model = target_model[3:]
        target_model = re.sub(r"-(tiered\(.*?\)|high|medium|low)", "", target_model)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={clean_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": query}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 4096
            }
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(SEARCH_TIMEOUT, connect=5.0)) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 401:
                raise Exception("Google API Key không hợp lệ.")
            elif resp.status_code == 429:
                raise Exception("Vượt quá giới hạn hạn ngạch Google Gemini API (429).")
            resp.raise_for_status()

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return {
                    "success": True,
                    "provider": "google",
                    "query": query,
                    "answer": "",
                    "results": []
                }

            candidate = candidates[0]
            parts = candidate.get("content", {}).get("parts", [])
            answer_text = "".join(p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p).strip()

            grounding = candidate.get("groundingMetadata", {})
            chunks = grounding.get("groundingChunks", [])
            results: List[Dict[str, Any]] = []

            for i, ch in enumerate(chunks[:max_results]):
                web = ch.get("web", {})
                url_str = web.get("uri") or web.get("url") or ""
                if url_str:
                    results.append({
                        "position": i + 1,
                        "title": web.get("title") or url_str,
                        "url": url_str,
                        "snippet": web.get("title") or "",
                        "content": None
                    })

            return {
                "success": True,
                "provider": "google",
                "query": query,
                "answer": answer_text,
                "results": results
            }

    @staticmethod
    async def _search_openai(
        query: str,
        api_key: str,
        model: Optional[str] = None,
        base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Gọi OpenAI với tool web_search để lấy câu trả lời và trích dẫn."""
        target_model = model or "gpt-4o"
        target_base = (base_url or "https://api.openai.com/v1").rstrip("/")
        url = f"{target_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": target_model,
            "messages": [{"role": "user", "content": query}],
            "tools": [{"type": "web_search"}]
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(SEARCH_TIMEOUT, connect=5.0)) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

            choice = data.get("choices", [{}])[0]
            msg = choice.get("message", {})
            content = msg.get("content") or ""

            # Extract url citations from annotations if present
            annotations = msg.get("annotations", [])
            results: List[Dict[str, Any]] = []
            for i, a in enumerate(annotations):
                c = a.get("url_citation") or a
                if c.get("url"):
                    results.append({
                        "position": i + 1,
                        "title": c.get("title") or c.get("url"),
                        "url": c.get("url"),
                        "snippet": c.get("title") or "",
                        "content": None
                    })

            return {
                "success": True,
                "provider": "openai",
                "query": query,
                "answer": content,
                "results": results
            }

    @staticmethod
    async def _search_tavily(query: str, api_key: str, max_results: int = 5) -> Dict[str, Any]:
        """Tìm kiếm chuyên dụng qua Tavily API."""
        url = "https://api.tavily.com/search"
        headers = {"Content-Type": "application/json"}
        payload = {
            "api_key": api_key.strip(),
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
            "include_answer": True
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(SEARCH_TIMEOUT, connect=5.0)) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

            answer = data.get("answer") or ""
            raw_results = data.get("results", [])
            results: List[Dict[str, Any]] = []
            for i, r in enumerate(raw_results[:max_results]):
                results.append({
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", ""),
                    "content": r.get("raw_content")
                })

            return {
                "success": True,
                "provider": "tavily",
                "query": query,
                "answer": answer,
                "results": results
            }

    @staticmethod
    async def _search_serper(query: str, api_key: str, max_results: int = 5) -> Dict[str, Any]:
        """Tìm kiếm Google Search qua Serper API."""
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": api_key.strip(),
            "Content-Type": "application/json"
        }
        payload = {"q": query, "num": max_results}

        async with httpx.AsyncClient(timeout=httpx.Timeout(SEARCH_TIMEOUT, connect=5.0)) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

            answer = data.get("answerBox", {}).get("answer") or data.get("answerBox", {}).get("snippet") or ""
            organic = data.get("organic", [])
            results: List[Dict[str, Any]] = []
            for i, r in enumerate(organic[:max_results]):
                results.append({
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "snippet": r.get("snippet", ""),
                    "content": None
                })

            return {
                "success": True,
                "provider": "serper",
                "query": query,
                "answer": answer,
                "results": results
            }

    @staticmethod
    async def _search_brave(query: str, api_key: str, max_results: int = 5) -> Dict[str, Any]:
        """Tìm kiếm qua Brave Search API."""
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "X-Subscription-Token": api_key.strip(),
            "Accept": "application/json"
        }
        params = {"q": query, "count": max_results}

        async with httpx.AsyncClient(timeout=httpx.Timeout(SEARCH_TIMEOUT, connect=5.0)) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

            web_results = data.get("web", {}).get("results", [])
            results: List[Dict[str, Any]] = []
            for i, r in enumerate(web_results[:max_results]):
                results.append({
                    "position": i + 1,
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("description", ""),
                    "content": None
                })

            return {
                "success": True,
                "provider": "brave",
                "query": query,
                "answer": "",
                "results": results
            }
