"""
Device Catalog Engine (In-Memory JSON AI Matcher)
Provides sub-millisecond device lookup, parametric search, and fuzzy AI matching
for CAD takeoff, BOM generation, and Busbar calculation.
"""
import json
import os
import re
import unicodedata
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from app.services.cache_service import cache_service

def strip_accents(s: str) -> str:
    if not s:
        return ""
    s = str(s).replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def _normalize_device_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures consistent dictionary structure for AI and CAD consumers."""
    normalized = dict(item)
    
    # Ensure dimensions dictionary
    if not isinstance(normalized.get("dimensions"), dict):
        normalized["dimensions"] = {
            "w": normalized.get("w"),
            "h": normalized.get("h"),
            "d": normalized.get("d"),
            "pitch": normalized.get("pitch"),
            "pole_w": normalized.get("pole_w"),
            "busbar_level": normalized.get("busbar_level")
        }

    # Ensure parameters dictionary
    if not isinstance(normalized.get("parameters"), dict):
        normalized["parameters"] = {
            "p": normalized.get("p"),
            "in": normalized.get("in"),
            "icu": normalized.get("icu"),
            "idelta": normalized.get("idelta"),
            "kva": normalized.get("kva"),
            "meterKind": normalized.get("meterKind"),
            "busbar_holes": normalized.get("busbar_holes"),
            "mount_holes": normalized.get("mount_holes")
        }

    # Ensure key aliases
    if "sku" not in normalized and "ma" in normalized:
        normalized["sku"] = normalized["ma"]
    if "ma" not in normalized and "sku" in normalized:
        normalized["ma"] = normalized["sku"]

    if "name" not in normalized and "n" in normalized:
        normalized["name"] = normalized["n"]
    if "n" not in normalized and "name" in normalized:
        normalized["n"] = normalized["name"]

    if "price" not in normalized and "g" in normalized:
        normalized["price"] = normalized["g"]
    if "g" not in normalized and "price" in normalized:
        normalized["g"] = normalized["price"]

    if "category" not in normalized and "t" in normalized:
        normalized["category"] = normalized["t"]
    if "t" not in normalized and "category" in normalized:
        normalized["t"] = normalized["category"]

    if "poles" not in normalized and "p" in normalized:
        normalized["poles"] = normalized["p"]
    if "p" not in normalized and "poles" in normalized:
        normalized["p"] = normalized["poles"]

    if "in_a" not in normalized and "in" in normalized:
        normalized["in_a"] = normalized["in"]

    return normalized

class DeviceCatalogEngine:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls, catalog_path: Optional[str] = None):
        return cls(catalog_path)

    def __init__(self, catalog_path: Optional[str] = None):
        if self._initialized:
            return
        
        if not catalog_path:
            from app.services.equipment_library import CATALOG_DIR
            catalog_path = str(CATALOG_DIR / "equipment_catalog.jsonl")
        elif not catalog_path.endswith("equipment_catalog.jsonl"):
            raise ValueError("Legacy catalog input is disabled; use equipment_catalog.jsonl")

        self.catalog_path = catalog_path
        self.items: List[Dict[str, Any]] = []
        self.sku_index: Dict[str, Dict[str, Any]] = {}
        self.brand_index: Dict[str, List[Dict[str, Any]]] = {}
        self.brand_alias_index: Dict[str, str] = {}
        self.type_index: Dict[str, List[Dict[str, Any]]] = {}
        self.accessories: Dict[str, Any] = {}
        
        self.load_catalog()
        self._initialized = True

    def load_catalog(self):
        """Load and index all devices into RAM for instant O(1) lookup."""
        if not os.path.exists(self.catalog_path):
            print(f"[WARN] Catalog JSON not found at: {self.catalog_path}")
            return

        with open(self.catalog_path, "r", encoding="utf-8") as f:
            source_rows = [json.loads(line) for line in f]

        self.items = []
        code_counts = {}
        for rec in source_rows:
            if rec.get('record_type') != 'priced_variant' or not rec.get('price'):
                continue
            spec = rec['specifications']
            dims = spec.get('dimensions_mm') or {}
            front = dims.get('visible_front') or []
            model = str(rec.get('model') or '').strip()
            material = str(rec.get('material_code') or '').strip()
            category = str(rec.get('category') or '').upper()
            type_match = re.search(r'\b(MCCB|MCB|ACB|RCBO|RCCB|ELCB|CONTACTOR|ATS|SPD)\b', category)
            dev_type = type_match.group(1) if type_match else category
            icu_raw = str(spec.get('breaking_capacity_ka') or '')
            icu_match = re.search(r'\d+(?:[.,]\d+)?', icu_raw)
            icu = float(icu_match.group().replace(',', '.')) if icu_match else None
            item = _normalize_device_item({
                'catalog_id': rec['catalog_id'], 'ma': material or model,
                'n': rec['display_name'], 'brand': rec['brand'].lower(),
                'brand_display': rec['brand'], 'series': model,
                't': dev_type,
                'p': spec.get('poles'), 'in': spec.get('current_a'),
                'icu': icu,
                'g': rec['price']['amount_vnd'],
                'dimensions': {'w': front[0] if len(front) >= 2 else None,
                               'h': front[1] if len(front) >= 2 else None,
                               'd': None},
                'source': rec['source_record'], 'cad': rec['cad'],
                'catalog_status': rec['cad']['status'],
            })
            self.items.append(item)
            for code in {model.casefold(), material.casefold()} - {''}:
                code_counts[code] = code_counts.get(code, 0) + 1
        self.sku_index.clear()
        self.brand_index.clear()
        self.brand_alias_index.clear()
        self.type_index.clear()

        for item in self.items:
            for sku in {str(item.get('ma') or '').casefold(), str(item.get('series') or '').casefold()} - {''}:
                if code_counts.get(sku) == 1:
                    self.sku_index[sku] = item

            brand = (item.get("brand") or "").lower()
            if brand not in self.brand_index:
                self.brand_index[brand] = []
            self.brand_index[brand].append(item)
            # Catalog data is authoritative for manufacturer aliases. This lets
            # newly imported vendors work without changing Python constants.
            for alias in (brand, item.get("brand_display"), item.get("manufacturer")):
                alias_key = strip_accents(str(alias or "")).lower().strip()
                if alias_key:
                    self.brand_alias_index.setdefault(alias_key, brand)

            dev_type = (item.get("t") or "MCB").upper()
            if dev_type not in self.type_index:
                self.type_index[dev_type] = []
            self.type_index[dev_type].append(item)

        # The historical accessory catalog is not an authorized fallback.
        self.accessories = {}

        # Xóa cache catalog cũ nếu nạp lại catalog mới
        try:
            cache_service.clear_prefix_sync("catalog:")
        except Exception:
            pass

        print(
            f"[DeviceCatalogEngine] Loaded {len(self.items)} catalog items "
            f"({len(self.brand_index)} brands, {len(self.type_index)} types). "
            f"Source-backed 2026 records only; unresolved variants stay unpriced."
        )

    def resolve_brand(self, brand: Optional[str]) -> Optional[str]:
        if not brand:
            return None
        raw = strip_accents(brand).lower().strip()
        # Prefer a real key/display name present in the current catalog. Legacy
        # aliases are only a fallback for older requests.
        return self.brand_alias_index.get(raw, raw)

    def get_accessory(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Tra cứu phụ kiện (Busbar, DIN rail, Máng cáp, Đèn báo, Đồng hồ, Khóa...) theo ID từ catalog_accessories.json."""
        if not item_id or not self.accessories:
            return None
        target = item_id.lower().strip()
        for group in self.accessories.values():
            if isinstance(group, dict) and "items" in group:
                for it in group["items"]:
                    if it.get("id", "").lower() == target:
                        return it
        return None

    def lookup_accessory(self, category: str, keyword: str = "") -> Optional[Dict[str, Any]]:
        """Tìm phụ kiện phù hợp nhất từ catalog_accessories.json theo chủng loại hoặc từ khóa (hỗ trợ tiếng Việt không dấu, cụm từ và từ đồng nghĩa)."""
        if not self.accessories:
            return None
        cat_lower = (category or "").lower().strip()
        kw_lower = (keyword or "").lower().strip()

        cache_key = f"catalog:acc:{cat_lower}:{kw_lower}"
        cached = cache_service.get_json_sync(cache_key)
        if cached is not None:
            return cached if cached != "__NONE__" else None

        # Nhóm cần tra cứu: nếu chỉ định đúng nhóm (door_accessories, accessories, busbar, din_rail, cable_duct) thì chỉ tìm trong nhóm đó
        target_groups = []
        if cat_lower in self.accessories:
            target_groups.append(self.accessories[cat_lower])
        else:
            for g_v in self.accessories.values():
                if isinstance(g_v, dict) and "items" in g_v:
                    target_groups.append(g_v)

        # Xây dựng danh sách cụm từ tìm kiếm
        search_terms = []
        if kw_lower:
            search_terms.append(kw_lower)
        if cat_lower and cat_lower not in self.accessories:
            search_terms.append(cat_lower)

        best_item = None
        best_score = 0

        for g in target_groups:
            if not (isinstance(g, dict) and "items" in g):
                continue
            for it in g["items"]:
                s_raw = f"{it.get('id', '')} {it.get('name', '')} {it.get('type', '')} {it.get('category', '')} {it.get('note', '')}"
                s_norm = strip_accents(s_raw).lower()

                item_score = 0
                for term in search_terms:
                    term_norm = strip_accents(term).lower().strip()
                    if not term_norm:
                        continue
                    # 1. Khớp chính xác ID hoặc type
                    if term_norm == str(it.get("id", "")).lower() or term_norm == str(it.get("type", "")).lower():
                        item_score = max(item_score, 500)
                    # 2. Khớp trọn vẹn cụm từ
                    elif term_norm in s_norm:
                        item_score = max(item_score, 200 + len(term_norm))
                    else:
                        # 3. Khớp các từ đơn (tokens)
                        tokens = [t for t in term_norm.split() if len(t) > 1]
                        matched_tokens = sum(1 for t in tokens if t in s_norm)
                        if matched_tokens >= 2:
                            item_score = max(item_score, matched_tokens * 20)
                        elif matched_tokens == 1 and len(tokens) == 1:
                            item_score = max(item_score, 15)

                if item_score > best_score:
                    best_score = item_score
                    best_item = it

        if best_score > 0 and best_item:
            cache_service.set_json_sync(cache_key, best_item, expire=86400)
            return best_item

        cache_service.set_json_sync(cache_key, "__NONE__", expire=86400)
        return None

    def get_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """Exact unique source-code lookup without historical cache entries."""
        if not sku:
            return None
        return self.sku_index.get(sku.strip().casefold())

    def filter_devices(
        self,
        brand: Optional[str] = None,
        device_type: Optional[str] = None,
        poles: Optional[int] = None,
        in_current: Optional[float] = None,
        min_icu: Optional[float] = None,
        max_icu: Optional[float] = None,
        kva: Optional[float] = None,
        series: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Return a candidate only when an explicit code resolves uniquely."""
        if not series:
            return []
        from app.services.equipment_library import resolve_price_variant
        row = resolve_price_variant(series, brand, poles, in_current, min_icu)
        if not row:
            return []
        item = next((candidate for candidate in self.items
                     if candidate['catalog_id'] == row['catalog_id']), None)
        return [item] if item and (not device_type or item['t'] == device_type.upper()) else []

    def search_candidates(
        self, *, brand: str, device_type: str,
        poles: Optional[int] = None, in_current: Optional[float] = None,
        min_icu: Optional[float] = None, limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Read matching priced variants without claiming an exact SKU selection."""
        brand_key = self.resolve_brand(brand)
        kind = str(device_type or "").strip().upper()
        if not brand_key or not kind:
            return []
        rows = []
        for item in self.brand_index.get(brand_key, []):
            if str(item.get("t") or "").upper() != kind:
                continue
            if poles is not None and item.get("p") != poles:
                continue
            # Family catalog rows sometimes omit the exact ampere variant;
            # expose them for reading, but never promote them to an exact SKU.
            if in_current is not None and item.get("in") is not None and item.get("in") != in_current:
                continue
            if min_icu is not None and (item.get("icu") is None or float(item["icu"]) < min_icu):
                continue
            rows.append(item)
        rows.sort(key=lambda item: (item.get("in") != in_current if in_current is not None else False,
                                    str(item.get("series") or ""), str(item.get("ma") or "")))
        return rows[:max(1, min(int(limit), 50))]

    def match_from_text(self, text: str) -> List[Tuple[Dict[str, Any], float]]:
        """
        Smart AI Text Parser & Matcher.
        Accepts any noisy string from CAD text/single line diagram and matches optimal device models.
        Returns list of (DeviceItem, confidence_score [0.0 - 1.0]).
        """
        if not text or not text.strip():
            return []

        # Text resemblance is not an order code. Only a unique source code can
        # be auto-matched; broader search remains available in the new API.
        exact = self.get_by_sku(text.strip())
        return [(exact, 1.0)] if exact else []

    def get_ai_function_tool_schema(self) -> Dict[str, Any]:
        """Returns standard Function Tool schema for LLMs (OpenAI, Gemini, Claude)."""
        return {
            "name": "lookup_device_catalog",
            "description": "Tra cứu thông số kỹ thuật, kích thước lắp đặt và đơn giá từ catalog thiết bị hiện có.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Chuỗi văn bản hoặc mã ký hiệu thiết bị cần tra cứu từ bản vẽ hoặc yêu cầu người dùng"
                    },
                    "brand": {
                        "type": "string",
                        "description": "Thương hiệu thiết bị (tùy chọn)"
                    },
                    "device_type": {
                        "type": "string",
                        "description": "Chủng loại thiết bị (tùy chọn)"
                    },
                    "poles": {
                        "type": "integer",
                        "enum": [1, 2, 3, 4],
                        "description": "Số cực (tùy chọn)"
                    },
                    "in_current": {
                        "type": "number",
                        "description": "Dòng định mức In (A) (tùy chọn)"
                    }
                },
                "required": ["query"]
            }
        }

    def lookup_device_info(
        self,
        category: str,
        in_a: Optional[float] = None,
        poles: Optional[int] = None,
        brand: Optional[str] = None,
        part_number: Optional[str] = None,
        name: Optional[str] = None,
        min_icu: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Tra cứu thông tin thiết bị, mã SKU và đơn giá thực tế từ Catalog 40.000+ sản phẩm.
        Trả về dict: {sku, name, brand, unit_price, dimensions, parameters, catalog_matched: bool}
        """
        from app.services.equipment_library import resolve_price_variant
        source_row = resolve_price_variant(part_number or '', brand, poles, in_a, min_icu)
        if source_row:
            front = ((source_row['specifications'].get('dimensions_mm') or {}).get('visible_front') or [])
            return {
                'sku': source_row['material_code'] or source_row['model'],
                'name': source_row['display_name'], 'brand': source_row['brand'],
                'unit_price': int(source_row['price']['amount_vnd']),
                'dimensions': {'w': front[0] if len(front) >= 2 else None,
                               'h': front[1] if len(front) >= 2 else None, 'd': None},
                'parameters': source_row['specifications'], 'cad': source_row['cad'],
                'source': source_row['source_record'], 'catalog_id': source_row['catalog_id'],
                'catalog_matched': True, 'rating_compatible': True,
            }
        return {
            'sku': part_number or '', 'name': name or '', 'brand': brand or '',
            'unit_price': 0, 'dimensions': {}, 'parameters': {},
            'catalog_matched': False, 'rating_compatible': False,
            'price_source': 'not_found',
            'price_note': 'Không tìm được biến thể duy nhất trong catalog 2026.',
        }

    async def resolve_price_smart(
        self,
        *,
        name: str,
        category: str,
        brand: str = "",
        spec: str = "",
        part_number: str = "",
        in_a: Optional[float] = None,
        poles: Optional[int] = None,
        min_icu: Optional[float] = None,
        ai_connections: Optional[List] = None,
        db: Optional[Any] = None,
        enable_web_search: bool = True,
    ) -> Dict[str, Any]:
        """
        Tra giá thống minh theo 4 cấp ưu tiên:
        P1: Custom (Admin nhập tay) → P2: Catalog → P3: CAD Library → P4: Web Search
        Wrapper gọi DevicePriceResolver.resolve().
        """
        from app.services.ai.device_price_resolver import DevicePriceResolver
        return await DevicePriceResolver.resolve(
            name=name,
            category=category,
            brand=brand,
            spec=spec,
            part_number=part_number,
            in_a=in_a,
            poles=poles,
            min_icu=min_icu,
            catalog_engine=self,
            ai_connections=ai_connections,
            db=db,
            enable_web_search=enable_web_search,
        )

# Global singleton instance
catalog_engine = DeviceCatalogEngine()
