"""
DevicePriceResolver - Hệ thống tra giá thiết bị thông minh với 3 cấp fallback:
1. Catalog báo giá chính thức (catalog_data.json) - nhanh nhất, chính xác nhất
2. Thư viện CAD (cad_device_registry.json) - có block vẽ nhưng chưa có giá
3. Web Search tự động - tra giá tham khảo trên internet
Kèm theo: Hệ thống nhập giá thủ công (Admin Override) - lưu vào custom_prices.json
"""

from __future__ import annotations

import json
import os
import re
import time
import logging
import asyncio
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Đường dẫn file giá tùy chỉnh (admin nhập tay)
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
CUSTOM_PRICES_PATH = os.path.join(DATA_DIR, "custom_prices.json")
CAD_REGISTRY_PATH = os.path.join(DATA_DIR, "cad_device_registry.json")


# ─────────────────────────────────────────────
# Mapping loại thiết bị → query web search
# ─────────────────────────────────────────────
DEVICE_SEARCH_TEMPLATES: Dict[str, str] = {
    "ampe_ke":     "{name} ampe kế ampere meter giá bán site:dienhathe.vn OR site:thietbidien.net OR site:schneider-electric.com",
    "von_ke":      "{name} vôn kế voltage meter giá bán site:dienhathe.vn OR site:thietbidien.net",
    "mfm":         "{name} đồng hồ đa năng multi-function meter giá bán",
    "cong_to":     "{name} công tơ điện energy meter giá bán Vietnam",
    "relay":       "{name} rơ le trung gian intermediate relay giá bán site:dienhathe.vn OR site:ls-electric.com",
    "timer":       "{name} timer relay hẹn giờ giá bán Vietnam",
    "overload":    "{name} relay nhiệt overload relay giá bán",
    "contactor":   "{name} khởi động từ contactor giá bán site:dienhathe.vn",
    "ct":          "{name} biến dòng current transformer CT giá bán Vietnam",
    "bien_tan":    "{name} biến tần VFD inverter giá bán Vietnam",
    "spd":         "{name} chống sét lan truyền SPD surge protector giá bán",
    "cau_dau":     "{name} cầu đấu terminal block giá bán site:dienhathe.vn",
    "den_bao":     "{name} đèn báo pilot light indicator lamp giá bán",
    "nut_nhan":    "{name} nút nhấn push button giá bán",
    "default":     "{name} {category} thiết bị điện giá bán Vietnam VND",
}

# Nhóm CAD → danh mục chuẩn hóa
CAD_GROUP_TO_CATEGORY: Dict[str, str] = {
    "Đồng hồ và công tơ": "Meter",
    "Rơ le và timer":     "Relay",
    "Contactor":          "Contactor",
    "Thiết bị đóng cắt": "CB",
    "Biến dòng":          "CT",
    "Cầu đấu":            "Terminal",
    "Đèn báo":            "PilotLamp",
    "Nút nhấn và còi":    "PushButton",
    "Biến tần":           "VFD",
    "Chống sét":          "SPD",
    "Tụ bù và cuộn kháng": "Capacitor",
    "Bộ nguồn DC":        "DCPS",
    "Bộ điều khiển":      "Controller",
}

# Loại thiết bị cần tra web khi không có trong catalog
TYPES_NEEDING_WEB_SEARCH = {
    "meter", "relay", "timer", "ct", "biến dòng", "đồng hồ",
    "ampe kế", "vôn kế", "mfm", "cầu đấu", "terminal", "đèn báo",
    "nút nhấn", "push button", "pilot", "biến tần", "vfd", "spd",
    "chống sét", "contactor",
}


class CustomPriceStore:
    """Quản lý giá tùy chỉnh do Admin nhập tay, lưu vào custom_prices.json."""

    _cache: Optional[Dict[str, Any]] = None
    _loaded_at: float = 0.0
    CACHE_TTL = 60.0  # giây

    @classmethod
    def _load(cls) -> Dict[str, Any]:
        now = time.monotonic()
        if cls._cache is not None and (now - cls._loaded_at) < cls.CACHE_TTL:
            return cls._cache
        if not os.path.exists(CUSTOM_PRICES_PATH):
            cls._cache = {}
            cls._loaded_at = now
            return cls._cache
        try:
            with open(CUSTOM_PRICES_PATH, "r", encoding="utf-8") as f:
                cls._cache = json.load(f)
        except Exception:
            cls._cache = {}
        cls._loaded_at = now
        return cls._cache

    @classmethod
    def _save(cls, data: Dict[str, Any]) -> None:
        with open(CUSTOM_PRICES_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        cls._cache = data
        cls._loaded_at = time.monotonic()

    @classmethod
    def get(cls, key: str) -> Optional[Dict[str, Any]]:
        """Tra giá tùy chỉnh theo key (sku hoặc tên chuẩn hóa)."""
        store = cls._load()
        return store.get(key.lower().strip())

    @classmethod
    def set(
        cls,
        key: str,
        price: int,
        name: str = "",
        brand: str = "",
        category: str = "",
        source_note: str = "admin",
        admin_user: str = "",
    ) -> Dict[str, Any]:
        """Lưu giá tùy chỉnh mới."""
        store = cls._load()
        entry = {
            "key": key.lower().strip(),
            "price": int(price),
            "name": name,
            "brand": brand,
            "category": category,
            "source_note": source_note,
            "updated_by": admin_user,
            "updated_at": datetime.now().isoformat(),
        }
        store[key.lower().strip()] = entry
        cls._save(store)
        return entry

    @classmethod
    def delete(cls, key: str) -> bool:
        store = cls._load()
        norm = key.lower().strip()
        if norm in store:
            del store[norm]
            cls._save(store)
            return True
        return False

    @classmethod
    def list_all(cls) -> List[Dict[str, Any]]:
        store = cls._load()
        return list(store.values())

    @classmethod
    def search(cls, query: str) -> List[Dict[str, Any]]:
        q = query.lower().strip()
        return [v for v in cls._load().values() if q in v.get("name", "").lower() or q in v.get("key", "")]


class CadRegistryCache:
    """Lazy load + index thư viện CAD theo group và name."""

    _data: Optional[Dict[str, Any]] = None

    @classmethod
    def _load(cls) -> Dict[str, Any]:
        if cls._data is not None:
            return cls._data
        if not os.path.exists(CAD_REGISTRY_PATH):
            cls._data = {"devices": [], "by_name": {}, "by_group": {}}
            return cls._data
        try:
            with open(CAD_REGISTRY_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            cls._data = {"devices": [], "by_name": {}, "by_group": {}}
            return cls._data

        devices = raw.get("devices", []) if isinstance(raw, dict) else raw
        by_name: Dict[str, Dict] = {}
        by_group: Dict[str, List] = {}
        for d in devices:
            if not isinstance(d, dict):
                continue
            name_key = (d.get("name") or "").strip().lower()
            if name_key:
                by_name[name_key] = d
            group = d.get("group") or ""
            by_group.setdefault(group, []).append(d)

        cls._data = {"devices": devices, "by_name": by_name, "by_group": by_group}
        return cls._data

    @classmethod
    def find(cls, name: str) -> Optional[Dict[str, Any]]:
        store = cls._load()
        return store["by_name"].get(name.lower().strip())

    @classmethod
    def find_by_group(cls, group: str, limit: int = 5) -> List[Dict[str, Any]]:
        store = cls._load()
        return store["by_group"].get(group, [])[:limit]

    @classmethod
    def search(cls, query: str) -> Optional[Dict[str, Any]]:
        """Tìm block CAD phù hợp nhất với query (tên, loại, hãng)."""
        store = cls._load()
        q = query.lower().strip()
        best = None
        best_score = 0
        for d in store["devices"]:
            score = 0
            name = (d.get("name") or "").lower()
            group = (d.get("group") or "").lower()
            desc = (d.get("recognition", {}).get("description") or "").lower() if isinstance(d.get("recognition"), dict) else ""
            if q in name:
                score = 100 + len(q)
            elif q in desc:
                score = 60
            elif q in group:
                score = 40
            else:
                tokens = q.split()
                matched = sum(1 for t in tokens if t in name or t in desc)
                score = matched * 20
            if score > best_score:
                best_score = score
                best = d
        return best if best_score > 0 else None


class DevicePriceResolver:
    """
    Tra giá thiết bị theo 4 cấp ưu tiên:
      P1: Custom Price (Admin nhập tay)
      P2: Catalog báo giá chính thức (catalog_data.json)
      P3: CAD Registry (có block vẽ, không có giá)
      P4: Web Search tự động
    """

    @staticmethod
    def _normalize_key(name: str, brand: str = "", category: str = "") -> str:
        parts = [p.strip().lower() for p in [brand, category, name] if p.strip()]
        return ":".join(parts)

    @staticmethod
    def _build_search_query(name: str, category: str, brand: str = "", spec: str = "") -> str:
        cat_lower = (category or "").lower()
        template_key = next(
            (k for k in DEVICE_SEARCH_TEMPLATES if k in cat_lower), "default"
        )
        tmpl = DEVICE_SEARCH_TEMPLATES[template_key]
        label = f"{brand} {name} {spec}".strip() if brand else f"{name} {spec}".strip()
        return tmpl.format(name=label, category=category)

    @staticmethod
    def needs_web_search(category: str, has_catalog_price: bool) -> bool:
        """Xác định xem có cần web search không."""
        if has_catalog_price:
            return False
        cat = (category or "").lower()
        return any(t in cat for t in TYPES_NEEDING_WEB_SEARCH)

    @staticmethod
    def resolve_from_catalog(
        catalog_engine: Any,
        category: str,
        name: str = "",
        brand: str = "",
        part_number: str = "",
        in_a: Optional[float] = None,
        poles: Optional[int] = None,
        min_icu: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Tra catalog báo giá. Trả None nếu không có."""
        try:
            result = catalog_engine.lookup_device_info(
                category=category,
                in_a=in_a,
                poles=poles,
                brand=brand,
                part_number=part_number,
                name=name,
                min_icu=min_icu,
            )
            if result and (result.get("unit_price") or 0) > 0:
                result["price_source"] = "catalog"
                return result
        except Exception as e:
            logger.warning("Catalog lookup error for '%s': %s", name, e)
        return None

    @staticmethod
    def resolve_from_cad(name: str, category: str, brand: str = "") -> Optional[Dict[str, Any]]:
        """Tìm block CAD phù hợp. Không có giá nhưng có thông tin vẽ."""
        query = f"{brand} {name} {category}".strip()
        cad_block = CadRegistryCache.search(query)
        if not cad_block:
            return None
        group = cad_block.get("group") or ""
        mapped_category = CAD_GROUP_TO_CATEGORY.get(group, category)
        return {
            "sku": "",
            "name": cad_block.get("name") or name,
            "brand": brand or "Chưa xác định",
            "unit_price": 0,
            "price": 0,
            "dimensions": {},
            "parameters": {},
            "cad": {
                "asset_ids": cad_block.get("asset_ids", []),
                "thumbnail_id": cad_block.get("thumbnail_id"),
                "sources": cad_block.get("sources", []),
            },
            "catalog_matched": False,
            "price_source": "cad_library",
            "price_note": "Có block CAD, chưa có giá catalog – đang tra giá tham khảo",
            "category": mapped_category,
        }

    @staticmethod
    async def resolve_from_web(
        name: str,
        category: str,
        brand: str = "",
        spec: str = "",
        ai_connections: Optional[List[Any]] = None,
        db: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """Web search để tra giá tham khảo."""
        if not ai_connections:
            return None

        query = DevicePriceResolver._build_search_query(name, category, brand, spec)
        logger.info("[PriceResolver] Web search: %s", query[:120])

        # Tìm connection có hỗ trợ web search
        from app.services.ai.web_search_service import WebSearchService
        from app.services.ai.connection_pool import ConnectionPoolService

        for conn in ai_connections:
            provider = (getattr(conn, "provider", "") or "").lower()
            api_key = getattr(conn, "api_key", "") or ""
            if not api_key:
                continue
            try:
                result = await WebSearchService.search(
                    query=query,
                    provider=provider,
                    api_key=api_key,
                    max_results=5,
                )
                if not result.get("success"):
                    continue

                # Trích xuất giá từ kết quả
                price_vnd = DevicePriceResolver._extract_price_from_search(result)
                answer_text = result.get("answer") or ""
                snippets = " ".join(r.get("snippet", "") for r in result.get("results", [])[:3])

                return {
                    "sku": "",
                    "name": name,
                    "brand": brand,
                    "unit_price": price_vnd,
                    "price": price_vnd,
                    "dimensions": {},
                    "parameters": {},
                    "catalog_matched": False,
                    "price_source": "web_search",
                    "price_note": f"Giá tham khảo từ web (cần xác nhận): {answer_text[:200] or snippets[:200]}",
                    "web_search_query": query,
                    "web_search_answer": answer_text[:500],
                }
            except Exception as e:
                logger.warning("[PriceResolver] Web search failed (%s): %s", provider, e)
                continue
        return None

    @staticmethod
    def _extract_price_from_search(search_result: Dict[str, Any]) -> int:
        """Trích xuất giá VND từ kết quả web search."""
        text = (search_result.get("answer") or "") + " ".join(
            r.get("snippet", "") for r in search_result.get("results", [])[:5]
        )
        # Tìm giá dạng: 1.234.000đ / 1,234,000 VND / 1234000 vnđ
        patterns = [
            r"(\d{1,3}(?:[.,]\d{3})+)\s*(?:đồng|vnđ|vnd|₫|đ)",
            r"(\d{1,3}(?:[.,]\d{3})+)",
        ]
        candidates: List[int] = []
        for pat in patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                raw = m.group(1).replace(".", "").replace(",", "")
                try:
                    val = int(raw)
                    if 10_000 <= val <= 500_000_000:  # lọc giá hợp lý
                        candidates.append(val)
                except ValueError:
                    pass
            if candidates:
                break

        if not candidates:
            return 0
        # Lấy giá trung vị để tránh outlier
        candidates.sort()
        return candidates[len(candidates) // 2]

    @staticmethod
    async def resolve(
        *,
        name: str,
        category: str,
        brand: str = "",
        spec: str = "",
        part_number: str = "",
        in_a: Optional[float] = None,
        poles: Optional[int] = None,
        min_icu: Optional[float] = None,
        catalog_engine: Optional[Any] = None,
        ai_connections: Optional[List[Any]] = None,
        db: Optional[Any] = None,
        enable_web_search: bool = True,
    ) -> Dict[str, Any]:
        """
        Resolve giá thiết bị theo thứ tự ưu tiên:
        P1 Custom → P2 Catalog → P3 CAD → P4 Web Search

        Returns dict với các field:
          - unit_price (int VND)
          - price_source: "custom" | "catalog" | "cad_library" | "web_search" | "not_found"
          - price_note: ghi chú nguồn / cảnh báo
          - catalog_matched (bool)
        """
        # ── P1: Custom Price (Admin nhập tay) ──────────────────────────
        custom_key = DevicePriceResolver._normalize_key(name, brand, category)
        custom = CustomPriceStore.get(custom_key)
        if not custom and part_number:
            custom = CustomPriceStore.get(part_number.lower())
        if custom:
            return {
                "sku": part_number or "",
                "name": name,
                "brand": brand,
                "unit_price": custom["price"],
                "price": custom["price"],
                "dimensions": {},
                "parameters": {},
                "catalog_matched": True,
                "price_source": "custom",
                "price_note": f"Giá Admin nhập tay ({custom.get('source_note', '')}) - cập nhật {custom.get('updated_at', '')[:10]}",
            }

        # ── P2: Catalog báo giá chính thức ────────────────────────────
        if catalog_engine:
            catalog_result = DevicePriceResolver.resolve_from_catalog(
                catalog_engine,
                category=category,
                name=name,
                brand=brand,
                part_number=part_number,
                in_a=in_a,
                poles=poles,
                min_icu=min_icu,
            )
            if catalog_result:
                catalog_result["price_note"] = "Giá catalog chính thức"
                return catalog_result

        # ── P3: CAD Registry (có block vẽ, chưa có giá) ───────────────
        cad_result = DevicePriceResolver.resolve_from_cad(name, category, brand)

        # ── P4: Web Search (tự động tra giá tham khảo) ─────────────────
        if enable_web_search and DevicePriceResolver.needs_web_search(category, False):
            web_result = await DevicePriceResolver.resolve_from_web(
                name=name,
                category=category,
                brand=brand,
                spec=spec,
                ai_connections=ai_connections,
                db=db,
            )
            if web_result:
                # Gắn thêm CAD block nếu tìm được
                if cad_result:
                    web_result["cad"] = cad_result.get("cad")
                return web_result

        # ── P3 fallback: chỉ có CAD, không có giá ─────────────────────
        if cad_result:
            return cad_result

        # ── Không tìm được gì ──────────────────────────────────────────
        return {
            "sku": part_number or "",
            "name": name,
            "brand": brand,
            "unit_price": 0,
            "price": 0,
            "dimensions": {},
            "parameters": {},
            "catalog_matched": False,
            "price_source": "not_found",
            "price_note": "Chưa có trong catalog, CAD library và web search. Cần nhập giá thủ công.",
        }
