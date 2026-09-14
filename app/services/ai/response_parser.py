import json
import re
import logging
from dataclasses import dataclass
from typing import Optional, Any, List, Dict

from app.core.config import settings
from app.core.exceptions import ResponseParsingError

logger = logging.getLogger(__name__)

def _safe_float(val, default: Optional[float] = None) -> Optional[float]:
    if val is None or val == "":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def _safe_int(val, default: Optional[int] = None) -> Optional[int]:
    if val is None or val == "":
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

@dataclass
class ExtractedDevice:
    category: str
    name: str
    spec: str
    in_a: Optional[float]
    icu_ka: Optional[float]
    poles: Optional[int]
    quantity: int
    brand: str
    part_number: str
    confidence: float
    section: Optional[str] = None
    notes: Optional[str] = None
    is_block: bool = False  # Đánh dấu nếu là block/module
    block_parent: Optional[str] = None  # Tên block cha (nếu device thuộc block)
    panel_code: Optional[str] = None
    panel_name: Optional[str] = None
    location: Optional[str] = None
    box_2d: Optional[list] = None
    evidence_image: Optional[str] = None
    suggested_brands: Optional[list] = None
    tag: Optional[str] = None
    mounting: Optional[str] = None
    electrical_function: Optional[str] = None
    upstream_device: Optional[str] = None
    downstream_device: Optional[str] = None
    connected_load: Optional[str] = None
    accompanying_accessories: Optional[list] = None
    compatible_proposal: Optional[dict] = None
class ResponseParserService:
    @staticmethod
    def extract_completeness_warnings(ai_response: str) -> List[str]:
        """Return AI-reported devices/clusters needing user review."""
        warnings: List[str] = []
        for block in ResponseParserService.extract_json_blocks(ai_response):
            if not isinstance(block, dict):
                continue
            review = block.get("completeness_review")
            if not isinstance(review, dict):
                continue
            for key, label in (("missing_devices", "Thiết bị có thể bị sót"), ("unanalysed_clusters", "Cụm chưa phân tích")):
                values = review.get(key)
                if isinstance(values, list):
                    warnings.extend(f"{label}: {str(value)}" for value in values if str(value).strip())
        return warnings

    @staticmethod
    def parse_device_list(ai_response: str) -> list[ExtractedDevice]:
        """Parse text AI output thành danh sách thiết bị."""
        if not ai_response or not ai_response.strip():
            logger.warning("AI response is empty")
            return []
        
        json_blocks = ResponseParserService.extract_json_blocks(ai_response)
        
        if not json_blocks:
            logger.warning("No JSON blocks found in AI response")
            logger.warning(f"AI response preview: {ai_response[:500]}")
            return []
        
        devices = []
        for block_idx, block in enumerate(json_blocks):
            items_to_process = []
            top_panel_code = None
            top_panel_name = None
            top_location = None
            if isinstance(block, list):
                items_to_process = block
            elif isinstance(block, dict):
                top_panel_code = str(block.get("panel_code") or "").strip() or None
                top_panel_name = str(block.get("panel_name") or "").strip() or None
                top_location = str(block.get("location") or "").strip() or None
                if "panels" in block and isinstance(block["panels"], list):
                    for panel_item in block["panels"]:
                        if not isinstance(panel_item, dict):
                            continue
                        p_code = str(panel_item.get("panel_code") or "").strip() or top_panel_code
                        p_name = str(panel_item.get("panel_name") or "").strip() or top_panel_name
                        p_loc = str(panel_item.get("location") or "").strip() or top_location
                        for d_item in (panel_item.get("devices") or panel_item.get("items") or []):
                            if isinstance(d_item, dict):
                                d_item_copy = dict(d_item)
                                if not d_item_copy.get("panel_code"):
                                    d_item_copy["panel_code"] = p_code
                                if not d_item_copy.get("panel_name"):
                                    d_item_copy["panel_name"] = p_name
                                if not d_item_copy.get("location"):
                                    d_item_copy["location"] = p_loc
                                items_to_process.append(d_item_copy)
                elif "devices" in block and isinstance(block["devices"], list):
                    items_to_process = block["devices"]
                elif "items" in block and isinstance(block["items"], list):
                    items_to_process = block["items"]

            # Auto-split any mistakenly merged Fuse & Pilot Light items
            expanded_items = []
            for item in items_to_process:
                if not isinstance(item, dict):
                    continue
                name_lower = str(item.get("name") or "").lower()
                cat_lower = str(item.get("category") or "").lower()
                tag_lower = str(item.get("tag") or "").lower()
                is_merged = (
                    ("cầu chì" in name_lower or "fuse" in name_lower or cat_lower == "fuse" or "fu" in tag_lower)
                    and ("đèn" in name_lower or "báo pha" in name_lower or "pilot" in name_lower or "light" in name_lower or cat_lower == "light" or "hl" in tag_lower)
                )
                if is_merged:
                    fuse_item = dict(item)
                    fuse_item["category"] = "FUSE"
                    fuse_item["tag"] = item.get("tag") if (item.get("tag") and "fu" in str(item.get("tag")).lower()) else "FU1"
                    fuse_item["name"] = "Cầu chì bảo vệ tín hiệu (1x6A)"
                    fuse_item["spec"] = item.get("spec") or "1x6A"
                    fuse_item["quantity"] = 1
                    fuse_item["section"] = item.get("section") or "Đo lường & Giám sát"
                    fuse_item["electrical_function"] = "MEASUREMENT"
                    fuse_item["notes"] = "Bảo vệ mạch tín hiệu đèn báo pha đầu vào tủ điện."

                    light_item = dict(item)
                    light_item["category"] = "LIGHT"
                    light_item["tag"] = "HL1"
                    light_item["name"] = "Đèn báo pha R"
                    light_item["spec"] = "Đèn báo pha 220V"
                    light_item["quantity"] = 1
                    light_item["section"] = item.get("section") or "Đo lường & Giám sát"
                    light_item["electrical_function"] = "MEASUREMENT"
                    light_item["notes"] = "Đèn báo có điện nguồn cấp pha R đầu vào tủ điện."

                    orig_box = item.get("box_2d")
                    if isinstance(orig_box, list) and len(orig_box) == 4:
                        ymin, xmin, ymax, xmax = orig_box
                        # Trên sơ đồ SLD, Cầu chì luôn nằm phía trên, Đèn báo pha nằm phía dưới theo phương đứng
                        mid_y = (ymin + ymax) // 2
                        fuse_item["box_2d"] = [ymin, xmin, max(ymin + 1, mid_y), xmax]
                        light_item["box_2d"] = [mid_y, xmin, ymax, xmax]

                    expanded_items.append(fuse_item)
                    expanded_items.append(light_item)
                else:
                    expanded_items.append(item)
            items_to_process = expanded_items

            for item_idx, item in enumerate(items_to_process):
                try:
                    is_block = str(item.get("category", "")).upper() == "BLOCK"
                    notes_text = str(item.get("notes") or "")
                    block_parent = None
                    if "thuộc block" in notes_text.lower() or "trong block" in notes_text.lower():
                        match = re.search(r'[Bb]lock\s+([^\s,\.]+)', notes_text)
                        if match:
                            block_parent = match.group(1)
                    
                    dev_panel_code = str(item.get("panel_code") or "").strip() or top_panel_code
                    dev_panel_name = str(item.get("panel_name") or "").strip() or top_panel_name
                    dev_location = str(item.get("location") or "").strip() or top_location

                    device = ExtractedDevice(
                        category=str(item.get("category") or "Thiết bị"),
                        name=str(item.get("name") or "Thiết bị"),
                        spec=str(item.get("spec") or ""),
                        in_a=_safe_float(item.get("in_a")),
                        icu_ka=_safe_float(item.get("icu_ka")),
                        poles=_safe_int(item.get("poles")),
                        quantity=_safe_int(item.get("quantity"), 1) or 1,
                        brand=str(item.get("brand") or ""),
                        part_number=str(item.get("part_number") or ""),
                        confidence=_safe_float(item.get("confidence"), settings.DEFAULT_CONFIDENCE) or settings.DEFAULT_CONFIDENCE,
                        section=str(item.get("section") or "").strip() or None,
                        notes=notes_text.strip() or None,
                        is_block=is_block,
                        block_parent=block_parent,
                        panel_code=dev_panel_code,
                        panel_name=dev_panel_name,
                        location=dev_location,
                        box_2d=item.get("box_2d") if isinstance(item.get("box_2d"), list) else None,
                        evidence_image=item.get("evidence_image"),
                        suggested_brands=item.get("suggested_brands") if isinstance(item.get("suggested_brands"), list) else None,
                        tag=str(item.get("tag") or "").strip() or None,
                        mounting=str(item.get("mounting") or "").strip() or None,
                        electrical_function=str(item.get("electrical_function") or "").strip() or None,
                        upstream_device=str(item.get("upstream_device") or "").strip() or None,
                        downstream_device=str(item.get("downstream_device") or "").strip() or None,
                        connected_load=str(item.get("connected_load") or "").strip() or None,
                        accompanying_accessories=item.get("accompanying_accessories") if isinstance(item.get("accompanying_accessories"), list) else None,
                        compatible_proposal=item.get("compatible_proposal") if isinstance(item.get("compatible_proposal"), dict) else None
                    )
                    devices.append(device)
                except Exception as e:
                    logger.warning(
                        f"Failed to parse device at block {block_idx}, item {item_idx}: {str(e)}",
                        extra={"item": item, "error": str(e)}
                    )
                    continue
        
        logger.info(f"Parsed {len(devices)} devices from AI response")
        return devices

    @staticmethod
    def extract_thinking(response: str) -> tuple[str, str]:
        """Tách riêng thẻ <thinking> và nội dung chính."""
        match = re.search(r'<thinking>(.*?)</thinking>', response, re.DOTALL)
        if match:
            thinking = match.group(1).strip()
            content = response.replace(match.group(0), "").strip()
            return thinking, content
        return "", response

    @staticmethod
    def extract_table_data(response: str) -> list[dict]:
        """Parse markdown tables."""
        # Giả lập parse table đơn giản
        return []

    @staticmethod
    def _clean_and_parse_json_str(raw_str: str) -> Optional[Any]:
        """Cố gắng parse một chuỗi JSON bằng nhiều cấp độ sửa lỗi tự động."""
        if not raw_str or not raw_str.strip():
            return None
            
        cleaned = raw_str.strip()
        
        # 1. Thử parse trực tiếp với strict=False
        try:
            return json.loads(cleaned, strict=False)
        except Exception:
            pass

        # 2. Sửa trailing commas: {"a": 1,} -> {"a": 1} hoặc [1, 2,] -> [1, 2]
        try:
            fixed = re.sub(r',\s*([}\]])', r'\1', cleaned)
            return json.loads(fixed, strict=False)
        except Exception:
            pass

        # 3. Thay thế Python booleans/None: True -> true, False -> false, None -> null
        try:
            fixed = re.sub(r'\bTrue\b', 'true', cleaned)
            fixed = re.sub(r'\bFalse\b', 'false', fixed)
            fixed = re.sub(r'\bNone\b', 'null', fixed)
            fixed = re.sub(r',\s*([}\]])', r'\1', fixed)
            return json.loads(fixed, strict=False)
        except Exception:
            pass

        # 4. Xử lý chuỗi bị cắt cụt (truncated JSON do giới hạn max tokens)
        try:
            # Tìm ngược từ cuối chuỗi về các dấu đóng ngoặc '}' hoặc ']' gần nhất
            for i in range(len(cleaned) - 1, -1, -1):
                ch = cleaned[i]
                if ch in ('}', ']'):
                    sub = cleaned[:i + 1]
                    stack = []
                    in_str = False
                    escape = False
                    for c in sub:
                        if escape:
                            escape = False
                            continue
                        if c == '\\':
                            escape = True
                            continue
                        if c == '"':
                            in_str = not in_str
                            continue
                        if not in_str:
                            if c in ('{', '['):
                                stack.append(c)
                            elif c == '}' and stack and stack[-1] == '{':
                                stack.pop()
                            elif c == ']' and stack and stack[-1] == '[':
                                stack.pop()

                    if not in_str and stack:
                        tail = ""
                        for opener in reversed(stack):
                            if opener == '{':
                                tail += '}'
                            elif opener == '[':
                                tail += ']'
                        candidate = sub + tail
                        candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
                        try:
                            res = json.loads(candidate, strict=False)
                            return res
                        except Exception:
                            pass
        except Exception:
            pass

        # 5. Dự phòng đơn giản cho chuỗi cắt cụt không chứa '}' hoặc ']'
        try:
            open_braces = cleaned.count('{') - cleaned.count('}')
            open_brackets = cleaned.count('[') - cleaned.count(']')
            if open_braces > 0 or open_brackets > 0:
                truncated_fixed = cleaned
                if truncated_fixed.count('"') % 2 != 0:
                    truncated_fixed += '"'
                truncated_fixed = re.sub(r',\s*$', '', truncated_fixed)
                truncated_fixed += (']' * max(0, open_brackets)) + ('}' * max(0, open_braces))
                truncated_fixed = re.sub(r',\s*([}\]])', r'\1', truncated_fixed)
                return json.loads(truncated_fixed, strict=False)
        except Exception:
            pass

        return None

    @staticmethod
    def extract_json_blocks(response: str) -> list[Any]:
        """
        Tìm và parse các khối JSON từ response của AI.
        Hỗ trợ:
        - Markdown code blocks: ```json ... ```, ```JSON ... ```, ``` ... ```
        - Markdown blocks chưa đóng ngoặc (do bị truncated)
        - Raw JSON text: {...} hoặc [...] không có markdown code blocks
        - AI model kèm thinking/reasoning tags: <think>...</think>, <thought>...</thought>
        - AI model kèm văn bản dẫn nhập / kết luận trước hoặc sau JSON
        """
        if not response or not isinstance(response, str) or not response.strip():
            return []

        # 1. Bóc tách và loại bỏ thẻ thinking/reasoning nếu có
        cleaned_response = re.sub(
            r'<(?:thinking|thought|think)>[\s\S]*?</(?:thinking|thought|think)>',
            '',
            response,
            flags=re.IGNORECASE
        ).strip()
        if not cleaned_response:
            cleaned_response = response.strip()

        blocks: list[Any] = []

        # Chiến lược 1: Tìm markdown code fences (```json, ```JSON, ```, etc.)
        fence_matches = list(re.finditer(r'```(?:json|JSON)?\s*([\s\S]*?)(?:```|$)', cleaned_response))
        for m in fence_matches:
            content = m.group(1).strip()
            if content and (content.startswith('{') or content.startswith('[')):
                parsed = ResponseParserService._clean_and_parse_json_str(content)
                if parsed is not None:
                    blocks.append(parsed)

        if blocks:
            return blocks

        # Chiến lược 2: Quét ngoặc cân bằng (bracket balancing) tìm outermost JSON Object {...} hoặc Array [...]
        for open_ch, close_ch in [('{', '}'), ('[', ']')]:
            start_idx = cleaned_response.find(open_ch)
            while start_idx != -1:
                depth = 0
                in_str = False
                escape = False
                end_idx = -1
                for i in range(start_idx, len(cleaned_response)):
                    ch = cleaned_response[i]
                    if escape:
                        escape = False
                        continue
                    if ch == '\\':
                        escape = True
                        continue
                    if ch == '"':
                        in_str = not in_str
                        continue
                    if not in_str:
                        if ch == open_ch:
                            depth += 1
                        elif ch == close_ch:
                            depth -= 1
                            if depth == 0:
                                end_idx = i
                                break

                if end_idx != -1:
                    candidate = cleaned_response[start_idx:end_idx + 1]
                    parsed = ResponseParserService._clean_and_parse_json_str(candidate)
                    if parsed is not None:
                        blocks.append(parsed)
                    start_idx = cleaned_response.find(open_ch, end_idx + 1)
                else:
                    candidate = cleaned_response[start_idx:]
                    parsed = ResponseParserService._clean_and_parse_json_str(candidate)
                    if parsed is not None:
                        blocks.append(parsed)
                    break

            if blocks:
                return blocks

        # Chiến lược 3: Fallback Regex greedy từ ký tự mở đầu tiên tới ký tự đóng cuối cùng
        match_obj = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', cleaned_response)
        if match_obj:
            candidate = match_obj.group(1)
            parsed = ResponseParserService._clean_and_parse_json_str(candidate)
            if parsed is not None:
                blocks.append(parsed)
                return blocks

        if not blocks:
            logger.warning("No valid JSON blocks found in response")
            preview = cleaned_response[:500].replace('\n', ' ')
            logger.warning(f"AI raw response snippet ({len(cleaned_response)} chars): {preview}")

        return blocks

    @staticmethod
    def extract_panels_metadata(ai_response: str) -> list[dict]:
        """Trích xuất danh sách các tủ (panel_code, panel_name, dimension, location) từ response."""
        json_blocks = ResponseParserService.extract_json_blocks(ai_response)
        panels = []
        seen_codes = set()
        for block in json_blocks:
            if isinstance(block, dict):
                if "panels" in block and isinstance(block["panels"], list):
                    for p in block["panels"]:
                        if not isinstance(p, dict):
                            continue
                        p_code = str(p.get("panel_code") or "").strip()
                        if p_code and p_code not in seen_codes:
                            seen_codes.add(p_code)
                            dim_val = str(p.get("dimension") or p.get("enclosure_dimensions") or "").strip()
                            panels.append({
                                "panel_code": p_code,
                                "panel_name": str(p.get("panel_name") or "").strip(),
                                "dimension": dim_val,
                                "enclosure_dimensions": dim_val,
                                "location": str(p.get("location") or "").strip(),
                            })
                elif block.get("panel_code"):
                    p_code = str(block.get("panel_code")).strip()
                    if p_code and p_code not in seen_codes:
                        seen_codes.add(p_code)
                        dim_val = str(block.get("dimension") or block.get("enclosure_dimensions") or "").strip()
                        panels.append({
                            "panel_code": p_code,
                            "panel_name": str(block.get("panel_name") or "").strip(),
                            "dimension": dim_val,
                            "enclosure_dimensions": dim_val,
                            "location": str(block.get("location") or "").strip(),
                        })
        return panels

    @staticmethod
    def extract_layout_intent(ai_response: str) -> Optional[dict]:
        """Trích xuất ý định bố trí không gian (cable_entry, incomer_position, busbar_arrangement, circuit_groups)."""
        json_blocks = ResponseParserService.extract_json_blocks(ai_response)
        for block in json_blocks:
            if isinstance(block, dict):
                if isinstance(block.get("layout_intent"), dict):
                    return block["layout_intent"]
                if "panels" in block and isinstance(block["panels"], list):
                    for p in block["panels"]:
                        if isinstance(p, dict) and isinstance(p.get("layout_intent"), dict):
                            return p["layout_intent"]
        return None

    @staticmethod
    def extract_technical_proposals(ai_response: str) -> list[dict]:
        """Trích xuất danh sách đề xuất kỹ thuật tương thích do AI phân tích từ bản vẽ."""
        json_blocks = ResponseParserService.extract_json_blocks(ai_response)
        proposals = []
        seen = set()
        for block in json_blocks:
            if not isinstance(block, dict):
                continue
            # 1. Top level proposals
            top_props = block.get("technical_proposals") or block.get("compatible_proposals") or []
            if isinstance(top_props, list):
                for tp in top_props:
                    if isinstance(tp, dict):
                        orig_d = tp.get("original_device") or tp.get("name") or ""
                        prop_d = tp.get("proposed_device") or tp.get("suggested_device") or ""
                        key = f"{orig_d}_{prop_d}"
                        if (orig_d or prop_d) and key not in seen:
                            seen.add(key)
                            proposals.append({
                                "original_device": orig_d,
                                "original_spec": tp.get("original_spec") or tp.get("spec") or "",
                                "ai_analysis": tp.get("ai_analysis") or tp.get("reason") or "",
                                "proposed_device": prop_d,
                                "proposed_spec": tp.get("proposed_spec") or "",
                                "suggested_brand": tp.get("suggested_brand") or tp.get("brand") or "",
                                "technical_reason": tp.get("technical_reason") or "Bảo toàn 100% sơ đồ nguyên lý"
                            })
            # 2. Panel level proposals
            if isinstance(block.get("panels"), list):
                for p in block["panels"]:
                    if not isinstance(p, dict):
                        continue
                    p_props = p.get("technical_proposals") or p.get("compatible_proposals") or []
                    if isinstance(p_props, list):
                        for tp in p_props:
                            if isinstance(tp, dict):
                                orig_d = tp.get("original_device") or tp.get("name") or ""
                                prop_d = tp.get("proposed_device") or tp.get("suggested_device") or ""
                                key = f"{orig_d}_{prop_d}"
                                if (orig_d or prop_d) and key not in seen:
                                    seen.add(key)
                                    proposals.append({
                                        "original_device": orig_d,
                                        "original_spec": tp.get("original_spec") or tp.get("spec") or "",
                                        "ai_analysis": tp.get("ai_analysis") or tp.get("reason") or "",
                                        "proposed_device": prop_d,
                                        "proposed_spec": tp.get("proposed_spec") or "",
                                        "suggested_brand": tp.get("suggested_brand") or tp.get("brand") or "",
                                        "technical_reason": tp.get("technical_reason") or "Bảo toàn 100% sơ đồ nguyên lý"
                                    })
                    # Device level proposals
                    for d in (p.get("devices") or p.get("items") or []):
                        if isinstance(d, dict) and isinstance(d.get("compatible_proposal"), dict):
                            cp = d["compatible_proposal"]
                            orig_d = cp.get("original_device") or d.get("name") or ""
                            prop_d = cp.get("proposed_device") or cp.get("suggested_name") or ""
                            key = f"{orig_d}_{prop_d}"
                            if (orig_d or prop_d) and key not in seen:
                                seen.add(key)
                                proposals.append({
                                    "original_device": orig_d,
                                    "original_spec": cp.get("original_spec") or d.get("spec") or "",
                                    "ai_analysis": cp.get("ai_analysis") or "",
                                    "proposed_device": prop_d,
                                    "proposed_spec": cp.get("proposed_spec") or "",
                                    "suggested_brand": cp.get("suggested_brand") or d.get("brand") or "",
                                    "technical_reason": cp.get("technical_reason") or "Bảo toàn 100% sơ đồ nguyên lý"
                                })
        return proposals
