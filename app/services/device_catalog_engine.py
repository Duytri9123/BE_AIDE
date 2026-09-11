"""
Device Catalog Engine (In-Memory JSON AI Matcher)
Provides sub-millisecond device lookup, parametric search, and fuzzy AI matching
for CAD takeoff, BOM generation, and Busbar calculation.
"""
import json
import os
import re
import unicodedata
from typing import Dict, List, Optional, Any, Tuple

def strip_accents(s: str) -> str:
    if not s:
        return ""
    s = str(s).replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

ACCESSORY_SYNONYMS = {
    "LIGHT": ["pilot_lamp", "pilot", "den", "lamp", "indicator", "light"],
    "PILOT": ["pilot_lamp", "pilot", "den", "lamp", "indicator"],
    "BUTTON": ["push_button", "estop", "nut nhan", "button"],
    "SWITCH": ["selector_switch", "chuyen mach", "switch"],
    "METER": ["meter", "dong ho", "mfm", "volt", "ampe", "multimeter"],
    "TERMINAL": ["domino", "cau dau", "terminal", "tb1"],
    "DOMINO": ["domino", "cau dau", "terminal", "tb1"],
    "RELAY": ["relay", "ro le", "intermediate"],
    "TIMER": ["timer", "hen gio", "on_delay", "thoi gian"],
    "CT": ["ct", "bien dong", "toroidal"],
    "FUSE": ["fuse", "cau chi"],
    "DUCT": ["duct", "mang cap", "mang"],
    "DIN_RAIL": ["din_rail", "thanh ray", "din 35"],
    "BUSBAR": ["busbar", "thanh cai", "thanh dong"],
    "SPD": ["spd", "chong set", "surge", "chong set lan truyen"],
}

BRAND_SYNONYMS = {
    "ls": "ls_standard",
    "ls standard": "ls_standard",
    "ls kinh te": "ls_standard",
    "ls premium": "ls_premium",
    "ls cao cap": "ls_premium",
    "schneider": "schneider",
    "schneider electric": "schneider",
    "sne": "schneider",
    "se": "schneider",
    "chint": "chint",
    "chint electric": "chint",
    "abb": "abb",
    "mitsubishi": "mitsubishi",
    "mitsu": "mitsubishi",
    "emic": "emic",
    "samwha": "samwha",
    "samhwa": "samwha",
    "shilin": "shihlin",
    "shihlin": "shihlin",
    "shihlin electric": "shihlin",
    "siemens": "siemens",
    "fuji": "fuji",
    "terasaki": "terasaki",
    "hyundai": "hyundai",
    "panasonic": "panasonic",
    "cnc": "cnc"
}

TYPE_SYNONYMS = {
    "aptomat": "MCB",
    "mcb": "MCB",
    "attomat": "MCB",
    "cb": "MCB",
    "khoi": "MCCB",
    "mccb": "MCCB",
    "elcb": "ELCB",
    "rcbo": "RCBO",
    "rccb": "RCCB",
    "chong giat": "RCCB",
    "chong ro": "RCCB",
    "afdd": "AFDD",
    "contactor": "Contactor",
    "khoi dong tu": "Contactor",
    "acb": "ACB",
    "may cat": "ACB",
    "may cat khong khi": "ACB",
    "cong to": "Meter",
    "meter": "Meter",
    "dong ho": "Meter",
    "tu bu": "Capacitor",
    "capacitor": "Capacitor"
}

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
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            catalog_path = os.path.join(base_dir, "data", "catalog_data.json")

        self.catalog_path = catalog_path
        self.items: List[Dict[str, Any]] = []
        self.sku_index: Dict[str, Dict[str, Any]] = {}
        self.brand_index: Dict[str, List[Dict[str, Any]]] = {}
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
            raw_items = json.load(f)

        self.items = [_normalize_device_item(it) for it in raw_items]
        self.sku_index.clear()
        self.brand_index.clear()
        self.type_index.clear()

        for item in self.items:
            sku = (item.get("ma") or "").strip()
            if sku:
                # Key by exact lower-case and compact alphanumeric
                self.sku_index[sku.lower()] = item
                compact_sku = re.sub(r'[^a-z0-9]', '', sku.lower())
                self.sku_index[compact_sku] = item

            brand = (item.get("brand") or "").lower()
            if brand not in self.brand_index:
                self.brand_index[brand] = []
            self.brand_index[brand].append(item)

            dev_type = (item.get("t") or "MCB").upper()
            if dev_type not in self.type_index:
                self.type_index[dev_type] = []
            self.type_index[dev_type].append(item)

        # Nạp danh mục phụ kiện cơ điện (catalog_accessories.json: Busbars, DIN Rails, Strut, Ducts, Door accessories)
        acc_path = os.path.join(os.path.dirname(self.catalog_path), "catalog_accessories.json")
        self.accessories = {}
        if os.path.exists(acc_path):
            try:
                with open(acc_path, "r", encoding="utf-8") as f_acc:
                    self.accessories = json.load(f_acc)
            except Exception as e:
                print(f"[WARN] Failed to load catalog_accessories.json: {e}")

        print(f"[DeviceCatalogEngine] Loaded and indexed {len(self.items)} devices across {len(self.brand_index)} brands and {len(self.accessories)} accessory groups in RAM.")

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

        # Nhóm cần tra cứu: nếu chỉ định đúng nhóm (door_accessories, accessories, busbar, din_rail, cable_duct) thì chỉ tìm trong nhóm đó
        target_groups = []
        if cat_lower in self.accessories:
            target_groups.append(self.accessories[cat_lower])
        else:
            for g_v in self.accessories.values():
                if isinstance(g_v, dict) and "items" in g_v:
                    target_groups.append(g_v)

        if not kw_lower and target_groups:
            first_g = target_groups[0]
            if isinstance(first_g, dict) and first_g.get("items"):
                return first_g["items"][0]

        # Xây dựng danh sách cụm từ tìm kiếm
        search_terms = []
        if kw_lower:
            search_terms.append(kw_lower)
        if cat_lower and cat_lower not in self.accessories:
            search_terms.append(cat_lower)

        # Mở rộng từ đồng nghĩa
        for syn_k, syn_list in ACCESSORY_SYNONYMS.items():
            k_upper = syn_k.upper()
            is_cat_match = (cat_lower not in self.accessories) and (k_upper in cat_lower.upper())
            if (kw_lower and k_upper in kw_lower.upper()) or is_cat_match:
                for syn in syn_list:
                    if syn not in search_terms:
                        search_terms.append(syn)

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
            return best_item

        return None

    def get_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """Exact SKU lookup (sub-millisecond O(1))."""
        if not sku:
            return None
        sku_clean = sku.strip().lower()
        if sku_clean in self.sku_index:
            return self.sku_index[sku_clean]
        
        compact = re.sub(r'[^a-z0-9]', '', sku_clean)
        return self.sku_index.get(compact)

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
        """Filter devices by parametric specifications."""
        brand_key = BRAND_SYNONYMS.get(brand.lower(), brand.lower()) if brand else None
        
        # Start with brand or type subset if available for faster filtering
        if brand_key and brand_key in self.brand_index:
            pool = self.brand_index[brand_key]
        elif device_type and device_type.upper() in self.type_index:
            pool = self.type_index[device_type.upper()]
        else:
            pool = self.items

        results = []
        for item in pool:
            if brand_key:
                item_brand = (item.get("brand") or "").lower()
                if item_brand != brand_key and item.get("brand_display", "").lower() != brand_key:
                    continue

            if device_type:
                # Synonym values are intentionally display-cased (for example
                # "Meter" and "Contactor"), while catalog types are compared
                # in uppercase. Normalize both sides so these device families
                # can actually be matched during takeoff.
                target_type = str(TYPE_SYNONYMS.get(device_type.lower(), device_type)).upper()
                item_type = (item.get("t") or "").upper()
                if item_type != target_type:
                    continue

            if poles is not None:
                item_poles = item.get("p")
                if item_poles is not None and item_poles != poles:
                    continue

            if in_current is not None:
                item_in = item.get("in")
                if item_in is not None and float(item_in) != float(in_current):
                    continue

            if kva is not None:
                item_kva = item.get("kva")
                if item_kva is not None and float(item_kva) != float(kva):
                    continue

            if min_icu is not None:
                item_icu = item.get("icu")
                if item_icu is None or float(item_icu) < float(min_icu):
                    continue

            if max_icu is not None:
                item_icu = item.get("icu")
                if item_icu is not None and float(item_icu) > float(max_icu):
                    continue

            if series:
                item_series = (item.get("series") or "").lower()
                if series.lower() not in item_series:
                    continue

            results.append(item)
            if len(results) >= limit:
                break

        return results

    def match_from_text(self, text: str) -> List[Tuple[Dict[str, Any], float]]:
        """
        Smart AI Text Parser & Matcher.
        Accepts any noisy string from CAD text/single line diagram and matches optimal device models.
        Returns list of (DeviceItem, confidence_score [0.0 - 1.0]).
        """
        if not text or not text.strip():
            return []

        text_clean = text.strip()
        
        # 1. Direct SKU exact check
        exact_item = self.get_by_sku(text_clean)
        if exact_item:
            return [(exact_item, 1.0)]

        # 2. Extract parameters using Regex
        text_lower = text_clean.lower()

        # Detect Brand
        detected_brand = None
        for syn, canonical in BRAND_SYNONYMS.items():
            if syn in text_lower:
                detected_brand = canonical
                break

        # Detect Type
        detected_type = None
        for syn, canonical in TYPE_SYNONYMS.items():
            if re.search(r'\b' + re.escape(syn) + r'\b', text_lower):
                detected_type = canonical
                break

        # Detect Poles (e.g. 1P, 2P, 3P, 4P, 1P+N, 3P+N, 3P4W, 1 pha, 3 pha)
        detected_poles = None
        p_match = re.search(r'\b([1-4])\s*p\b', text_lower)
        if p_match:
            detected_poles = int(p_match.group(1))
        elif "1 pha" in text_lower or "1pha" in text_lower:
            detected_poles = 1
        elif "3 pha" in text_lower or "3pha" in text_lower:
            detected_poles = 3

        # Detect Current In (e.g. 6A, 10A, 16A, 100A, 1600A, In=100A, In100)
        detected_in = None
        in_match = re.search(r'\b(?:in\s*[=:]?\s*)?(\d+(?:\.\d+)?)\s*a\b', text_lower)
        if in_match:
            try:
                detected_in = float(in_match.group(1))
            except ValueError:
                pass
        
        # Detect Capacity kVA / kVAr for Capacitors (e.g. 25kvar, 25kva, 25k)
        detected_kva = None
        kva_match = re.search(r'\b(\d+(?:\.\d+)?)\s*(?:kvar|kva|k)\b', text_lower)
        if kva_match and not in_match:
            try:
                detected_kva = float(kva_match.group(1))
            except ValueError:
                pass

        # Detect Breaking capacity Icu (e.g. 6kA, 10kA, 36kA, 50kA, 65kA, Icu=36kA)
        detected_icu = None
        icu_match = re.search(r'\b(?:icu\s*[=:]?\s*)?(\d+(?:\.\d+)?)\s*ka\b', text_lower)
        if icu_match:
            try:
                detected_icu = float(icu_match.group(1))
            except ValueError:
                pass

        # Detect Series hints
        detected_series = None
        series_candidates = ["la63n", "la63h", "la125h", "abn", "abs", "easy9", "ik60n", "ic60n", "c120", "gopact", "nxb", "nxm", "sj200", "s200", "fa1", "fa2", "fa4", "dsp", "bh-d6", "bh-d10", "bhw-t10", "nf32", "nf63", "nf125", "nf250", "cv-140", "dle"]
        for s in series_candidates:
            if s in text_lower:
                detected_series = s
                break

        # Filter candidate pool
        candidates = self.filter_devices(
            brand=detected_brand,
            device_type=detected_type,
            poles=detected_poles,
            in_current=detected_in,
            min_icu=detected_icu,
            kva=detected_kva,
            series=detected_series,
            limit=50
        )

        if not candidates:
            # Fallback broader search
            candidates = self.filter_devices(
                brand=detected_brand,
                poles=detected_poles,
                in_current=detected_in,
                limit=30
            )

        # Score candidates
        scored: List[Tuple[Dict[str, Any], float]] = []
        for it in candidates:
            score = 0.5
            if detected_brand and (it.get("brand") == detected_brand or it.get("brand_display", "").lower() == detected_brand):
                score += 0.2
            if detected_type and it.get("t", "").upper() == detected_type:
                score += 0.15
            if detected_poles and it.get("p") == detected_poles:
                score += 0.1
            if detected_in and it.get("in") == detected_in:
                score += 0.15
            if detected_kva and it.get("kva") == detected_kva:
                score += 0.15
            if detected_icu and it.get("icu") == detected_icu:
                score += 0.1
            if detected_series and detected_series in (it.get("series") or "").lower():
                score += 0.1
            
            # Check SKU / Name token overlap
            sku_tokens = set(it.get("ma", "").lower().split())
            text_tokens = set(text_lower.split())
            overlap = len(sku_tokens & text_tokens)
            if overlap:
                score += min(0.2, overlap * 0.08)

            final_score = min(0.99, score)
            scored.append((it, round(final_score, 2)))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:5]

    def get_ai_function_tool_schema(self) -> Dict[str, Any]:
        """Returns standard Function Tool schema for LLMs (OpenAI, Gemini, Claude)."""
        return {
            "name": "lookup_device_catalog",
            "description": "Tra cứu thông số kỹ thuật, kích thước lắp đặt, bước cực Pitch, vị trí lỗ bắt thanh cái Busbar và đơn giá thiết bị điện từ catalog 1.498 model (LS, Schneider, Chint, ABB, Mitsubishi, EMIC, Samwha).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Chuỗi văn bản hoặc mã ký hiệu thiết bị cần tra cứu (ví dụ: 'LA63N 1P 16A', 'MCCB 3P 100A 36kA Mitsubishi', 'Tụ bù 25kvar Samwha')"
                    },
                    "brand": {
                        "type": "string",
                        "enum": ["ls_standard", "ls_premium", "schneider", "chint", "abb", "mitsubishi", "emic", "samwha"],
                        "description": "Thương hiệu thiết bị (tùy chọn)"
                    },
                    "device_type": {
                        "type": "string",
                        "enum": ["MCB", "MCCB", "ELCB", "RCBO", "RCCB", "AFDD", "Contactor", "ACB", "Meter", "Capacitor"],
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
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Tra cứu thông tin thiết bị, mã SKU và đơn giá thực tế từ Catalog 40.000+ sản phẩm.
        Trả về dict: {sku, name, brand, unit_price, dimensions, parameters, catalog_matched: bool}
        """
        cat_upper = (category or "").upper()
        
        # 1. Exact SKU lookup if part_number provided
        if part_number:
            exact = self.get_by_sku(part_number)
            if exact:
                return {
                    "sku": exact.get("ma") or part_number,
                    "name": exact.get("n") or name or f"{category} {part_number}",
                    "brand": exact.get("brand_display") or exact.get("brand") or brand or "LS",
                    "unit_price": int(exact.get("g") or 0),
                    "dimensions": exact.get("dimensions", {}),
                    "parameters": exact.get("parameters", {}),
                    "catalog_matched": True
                }

        # 2. Parametric lookup
        brand_target = BRAND_SYNONYMS.get(brand.lower(), brand.lower()) if brand else None
        matches = self.filter_devices(
            brand=brand_target,
            device_type=category,
            poles=poles,
            in_current=in_a,
            limit=5
        )
        if matches:
            best = matches[0]
            price = int(best.get("g") or 0)
            return {
                "sku": best.get("ma") or "",
                "name": best.get("n") or name or "",
                "brand": best.get("brand_display") or best.get("brand") or "",
                "unit_price": price,
                "dimensions": best.get("dimensions", {}),
                "parameters": best.get("parameters", {}),
                "catalog_matched": True
            }

        # 3. Fuzzy text matching
        search_query = f"{category} {poles or ''}P {in_a or ''}A {part_number or ''} {name or ''}".strip()
        fuzzy = self.match_from_text(search_query)
        if fuzzy:
            best, score = fuzzy[0]
            if score >= 0.6:
                price = int(best.get("g") or 0)
                return {
                    "sku": best.get("ma") or part_number or "",
                    "name": best.get("n") or name or "",
                    "brand": brand or "",
                    "unit_price": price,
                    "dimensions": best.get("dimensions", {}),
                    "parameters": best.get("parameters", {}),
                    "catalog_matched": True
                }

        # No synthetic SKU, brand, or market price: an unmatched item must be
        # surfaced for catalog maintenance and user confirmation.
        return {
            "sku": "",
            "name": name or "",
            "brand": brand or "",
            "unit_price": 0,
            "dimensions": {},
            "parameters": {},
            "catalog_matched": False
        }

# Global singleton instance
catalog_engine = DeviceCatalogEngine()
