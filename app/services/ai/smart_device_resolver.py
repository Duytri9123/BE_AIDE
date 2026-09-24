"""
SmartDeviceResolver - Suy luận loại thiết bị điện từ ngữ cảnh mạch nguyên lý.

Các trường hợp phức tạp cần suy luận:
- "Đồng hồ" → Ampe kế / Vôn kế / MFM / Công tơ điện
- "Khởi động từ" → Đơn / Sao-tam giác / Đảo chiều
- "Relay" → Relay trung gian / Relay bảo vệ / Relay dòng chạm đất
- "Công tắc" → Selector switch / Chuyển mạch A-O-M
- Thiết bị lắp đặt (tiếp địa, ray DIN) → Đề xuất, không vào BOM
"""
from __future__ import annotations

import re
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Quy tắc suy luận từ ngữ cảnh mạch
# ─────────────────────────────────────────────────────────────

# Đồng hồ: từ khóa → loại cụ thể
METER_INFERENCE_RULES: List[Tuple[List[str], str, str]] = [
    # (trigger_keywords, resolved_name, resolved_category)
    (["ampe", "ampe kế", "ammeter", "ampere", "đo dòng", "bien dong", "ct", "ia", "ib", "ic"], "Ampe kế", "AmpereMeter"),
    (["vôn", "von ke", "voltmeter", "đo áp", "volt", "voltage", "ua", "ub", "uc", "uab"], "Vôn kế", "VoltMeter"),
    (["mfm", "đa năng", "multi", "power meter", "multimeter", "đo công suất", "kwh", "kw", "kvar"], "Đồng hồ đa năng MFM", "MFM"),
    (["công tơ", "cong to", "energy", "kwh meter", "kWh", "điện năng", "đo năng lượng"], "Công tơ điện", "EnergyMeter"),
    (["tần số", "tan so", "hz", "frequency"], "Đồng hồ tần số", "FrequencyMeter"),
    (["hệ số công suất", "he so cong suat", "cos phi", "cosφ", "power factor"], "Đồng hồ hệ số công suất", "PowerFactorMeter"),
]

# Khởi động từ / Contactor: từ ngữ cảnh → loại starter
STARTER_INFERENCE_RULES: List[Tuple[List[str], str, str, int]] = [
    # (trigger_keywords, resolved_name, config_type, contactor_count)
    (["sao tam giac", "sao-tam giác", "y/d", "y-d", "star delta", "star/delta", "sao/tam giác"], "Khởi động từ sao-tam giác", "star_delta", 3),
    (["dao chieu", "đảo chiều", "reverse", "forward reverse", "f/r", "chạy thuận nghịch", "thuận nghịch"], "Khởi động từ đảo chiều", "reversing", 2),
    (["doi noi", "đổi nối", "pole change", "2 tốc độ", "2 speed", "hai toc do"], "Khởi động từ đổi nối", "pole_change", 2),
    (["mềm", "soft starter", "khởi động mềm"], "Bộ khởi động mềm", "soft_starter", 0),
    (["bien tan", "biến tần", "vfd", "inverter", "drive"], "Biến tần", "vfd", 0),
]

# Relay: từ ngữ cảnh → loại relay
RELAY_INFERENCE_RULES: List[Tuple[List[str], str, str]] = [
    (["trung gian", "intermediate", "auxiliary", "phụ trợ", "14 chân", "11 chân"], "Relay trung gian", "IntermediateRelay"),
    (["bảo vệ dòng", "overcurrent", "51", "quá dòng"], "Relay bảo vệ quá dòng", "OvercurrentRelay"),
    (["chạm đất", "cham dat", "ground fault", "earth fault", "51g", "64"], "Relay bảo vệ chạm đất", "EarthFaultRelay"),
    (["điện áp thấp", "undervoltage", "27", "áp thấp"], "Relay bảo vệ điện áp thấp", "UndervoltageRelay"),
    (["nhiệt độ", "nhiet do", "temperature", "thermal", "relay nhiệt"], "Relay nhiệt", "ThermalRelay"),
    (["hẹn giờ", "hen gio", "timer", "thời gian", "delay", "on delay", "off delay"], "Timer relay", "TimerRelay"),
]

# Biến dòng CT
CT_INFERENCE_RULES: List[Tuple[List[str], str]] = [
    (["toroidal", "vòng", "vong", "lỗ xuyên"], "Biến dòng toroidal CT"),
    (["kẹp", "kep", "split core", "cắt đôi"], "Biến dòng kẹp CT"),
    (["bar type", "thanh cái", "busbar"], "Biến dòng thanh cái CT"),
]

# Từ khóa lắp đặt (không vào BOM, chỉ đề xuất)
INSTALLATION_ONLY_KEYWORDS = {
    "tiếp địa", "tiep dia", "grounding", "earthing", "pe conductor",
    "thanh nối đất", "ground bar", "earth bar",
    "ray din", "din rail", "thanh ray", "omega rail",
    "máng cáp", "mang cap", "cable duct", "cable tray", "wireway",
    "vít", "vis", "screw", "ốc", "bu lông", "bolt",
    "gioăng", "gasket", "seal",
}


class SmartDeviceResolver:
    """
    Suy luận loại thiết bị điện cụ thể từ tên chung và ngữ cảnh mạch điện.
    Được gọi TRƯỚC khi tra catalog để có tên chính xác hơn.
    """

    @staticmethod
    def _normalize(text: str) -> str:
        """Chuẩn hóa text: lowercase, bỏ dấu đơn giản."""
        if not text:
            return ""
        # Giữ dấu tiếng Việt nhưng lowercase
        return text.lower().strip()

    @staticmethod
    def is_installation_only(name: str, category: str = "", notes: str = "") -> bool:
        """
        Xác định thiết bị chỉ là phụ kiện lắp đặt (tiếp địa, ray DIN...)
        → Không đưa vào BOM, chỉ đề xuất trong installation_considerations.
        """
        combined = SmartDeviceResolver._normalize(f"{name} {category} {notes}")
        return any(kw in combined for kw in INSTALLATION_ONLY_KEYWORDS)

    @staticmethod
    def resolve_meter_type(
        name: str, notes: str = "", circuit_context: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Suy luận loại đồng hồ đo từ tên và ngữ cảnh mạch.
        Returns: {resolved_name, resolved_category, confidence, reasoning}
        """
        combined = SmartDeviceResolver._normalize(f"{name} {notes} {circuit_context}")

        # Kiểm tra xem có phải tên chung chung không
        generic_meter_triggers = ["đồng hồ", "dong ho", "meter", "đo lường", "đo"]
        is_generic = any(t in combined for t in generic_meter_triggers)
        if not is_generic:
            return None

        # Áp dụng quy tắc suy luận
        for keywords, resolved_name, resolved_category in METER_INFERENCE_RULES:
            if any(kw in combined for kw in keywords):
                return {
                    "resolved_name": resolved_name,
                    "resolved_category": resolved_category,
                    "confidence": 0.85,
                    "reasoning": f"Suy luận từ ngữ cảnh: tìm thấy '{next(kw for kw in keywords if kw in combined)}'",
                    "needs_web_search": True,  # Loại này thường cần web search giá
                }

        # Không đủ ngữ cảnh - đề xuất các khả năng
        return {
            "resolved_name": "Đồng hồ (cần xác định loại)",
            "resolved_category": "Meter",
            "confidence": 0.3,
            "reasoning": "Chưa đủ thông tin xác định loại đồng hồ. Cần kiểm tra đường dây đo lường.",
            "alternatives": ["Ampe kế", "Vôn kế", "Đồng hồ đa năng MFM", "Công tơ điện"],
            "needs_web_search": False,
        }

    @staticmethod
    def resolve_starter_type(
        name: str, notes: str = "", circuit_context: str = "",
        contactor_count_in_vicinity: int = 1,
    ) -> Optional[Dict[str, Any]]:
        """
        Suy luận cấu hình khởi động từ.
        Returns: {config_type, contactor_count, resolved_name, confidence, reasoning}
        """
        combined = SmartDeviceResolver._normalize(f"{name} {notes} {circuit_context}")

        # Chỉ xử lý nếu là khởi động từ / contactor
        starter_triggers = ["khởi động từ", "khoi dong tu", "contactor", "kdt"]
        is_starter = any(t in combined for t in starter_triggers)
        if not is_starter:
            return None

        for keywords, resolved_name, config_type, cnt in STARTER_INFERENCE_RULES:
            if any(kw in combined for kw in keywords):
                return {
                    "resolved_name": resolved_name,
                    "config_type": config_type,
                    "contactor_count": cnt if cnt > 0 else contactor_count_in_vicinity,
                    "confidence": 0.88,
                    "reasoning": f"Phát hiện cấu hình: '{next(kw for kw in keywords if kw in combined)}'",
                    "note": f"Cần {cnt} contactor cho cấu hình {config_type}" if cnt > 1 else "",
                }

        # Kiểm tra bằng số lượng contactor trong vùng lân cận
        if contactor_count_in_vicinity == 3:
            return {
                "resolved_name": "Khởi động từ sao-tam giác (suy luận từ số lượng)",
                "config_type": "star_delta",
                "contactor_count": 3,
                "confidence": 0.65,
                "reasoning": "Suy luận: phát hiện 3 contactor trong vùng lân cận → nhiều khả năng là sao-tam giác",
                "note": "Cần xác nhận sơ đồ điều khiển",
            }
        elif contactor_count_in_vicinity == 2:
            return {
                "resolved_name": "Khởi động từ đảo chiều (suy luận từ số lượng)",
                "config_type": "reversing",
                "contactor_count": 2,
                "confidence": 0.60,
                "reasoning": "Suy luận: phát hiện 2 contactor trong vùng lân cận → có thể là đảo chiều",
                "note": "Cần xác nhận có liên động cơ học/điện không",
            }

        # Contactor đơn thông thường
        return {
            "resolved_name": "Khởi động từ (đơn)",
            "config_type": "single",
            "contactor_count": 1,
            "confidence": 0.75,
            "reasoning": "Không phát hiện dấu hiệu cấu hình phức tạp → khởi động từ đơn",
        }

    @staticmethod
    def resolve_relay_type(
        name: str, notes: str = "", circuit_context: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Suy luận loại relay từ ngữ cảnh."""
        combined = SmartDeviceResolver._normalize(f"{name} {notes} {circuit_context}")
        relay_triggers = ["relay", "rơ le", "ro le", "rl"]
        is_relay = any(t in combined for t in relay_triggers)
        if not is_relay:
            return None

        for keywords, resolved_name, resolved_category in RELAY_INFERENCE_RULES:
            if any(kw in combined for kw in keywords):
                return {
                    "resolved_name": resolved_name,
                    "resolved_category": resolved_category,
                    "confidence": 0.82,
                    "reasoning": f"Suy luận từ: '{next(kw for kw in keywords if kw in combined)}'",
                    "needs_web_search": True,
                }

        return {
            "resolved_name": "Relay trung gian",
            "resolved_category": "IntermediateRelay",
            "confidence": 0.5,
            "reasoning": "Mặc định relay trung gian khi không đủ ngữ cảnh",
            "needs_web_search": True,
        }

    @staticmethod
    def resolve_device(
        name: str,
        category: str = "",
        notes: str = "",
        circuit_context: str = "",
        contactor_count_in_vicinity: int = 1,
    ) -> Dict[str, Any]:
        """
        Entry point chính. Suy luận loại thiết bị từ tên và ngữ cảnh.

        Returns dict:
          - is_installation_only (bool): chỉ là phụ kiện lắp đặt, không vào BOM
          - resolved_name (str): tên chính xác sau suy luận
          - resolved_category (str): danh mục chính xác
          - confidence (float): 0..1
          - reasoning (str): lý do suy luận
          - needs_web_search (bool): cần web search giá
          - alternatives (List[str]): các khả năng khác (nếu không chắc)
          - config_type (str): cho starter (single/star_delta/reversing...)
          - contactor_count (int): số contactor cần cho starter
        """
        # Kiểm tra phụ kiện lắp đặt
        if SmartDeviceResolver.is_installation_only(name, category, notes):
            return {
                "is_installation_only": True,
                "resolved_name": name,
                "resolved_category": "Installation",
                "confidence": 0.9,
                "reasoning": "Phụ kiện lắp đặt - đề xuất kỹ thuật, không đưa vào BOM tự động",
                "needs_web_search": False,
            }

        name_lower = SmartDeviceResolver._normalize(name)
        cat_lower = SmartDeviceResolver._normalize(category)

        # Suy luận theo loại
        result = None

        # 1. Đồng hồ
        if any(t in name_lower or t in cat_lower for t in ["đồng hồ", "dong ho", "meter", "đo"]):
            result = SmartDeviceResolver.resolve_meter_type(name, notes, circuit_context)

        # 2. Khởi động từ / Contactor
        elif any(t in name_lower or t in cat_lower for t in ["khởi động từ", "khoi dong tu", "contactor", "kdt"]):
            result = SmartDeviceResolver.resolve_starter_type(
                name, notes, circuit_context, contactor_count_in_vicinity
            )

        # 3. Relay
        elif any(t in name_lower or t in cat_lower for t in ["relay", "rơ le", "ro le"]):
            result = SmartDeviceResolver.resolve_relay_type(name, notes, circuit_context)

        if result:
            result.setdefault("is_installation_only", False)
            result.setdefault("original_name", name)
            result.setdefault("original_category", category)
            return result

        # Không cần suy luận thêm
        return {
            "is_installation_only": False,
            "resolved_name": name,
            "resolved_category": category,
            "confidence": 1.0,
            "reasoning": "Loại thiết bị đã rõ ràng, không cần suy luận thêm",
            "needs_web_search": False,
        }

    @staticmethod
    def enrich_circuit_assessment(
        circuit_assessment: Dict[str, Any],
        extracted_devices: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Sau khi có circuit_assessment (preflight), suy luận lại loại thiết bị
        cho các thiết bị có tên chung chung trong extracted_devices.

        Trả về danh sách thiết bị đã được bổ sung thông tin suy luận.
        """
        if not circuit_assessment or not extracted_devices:
            return extracted_devices

        # Lấy circuit context từ assessment
        circuit_summary = circuit_assessment.get("circuit_summary") or ""
        functional_groups = circuit_assessment.get("functional_groups") or []
        ambiguous_symbols = circuit_assessment.get("ambiguous_symbols") or []

        # Build context string cho từng thiết bị
        fg_text = " ".join(
            str(fg.get("description") or "")
            for fg in functional_groups
            if isinstance(fg, dict)
        )
        amb_text = " ".join(
            str(sym.get("possible_types") or sym.get("description") or "")
            for sym in ambiguous_symbols
            if isinstance(sym, dict)
        )
        full_context = f"{circuit_summary} {fg_text} {amb_text}"

        # Đếm số contactor theo từng khu vực
        contactor_counts: Dict[str, int] = {}
        for dev in extracted_devices:
            name = (dev.get("name") or "").lower()
            section = dev.get("section") or "default"
            if any(t in name for t in ["contactor", "khởi động từ", "kdt"]):
                contactor_counts[section] = contactor_counts.get(section, 0) + 1

        enriched = []
        for dev in extracted_devices:
            dev_copy = dict(dev)
            name = dev_copy.get("name") or ""
            category = dev_copy.get("category") or ""
            notes = dev_copy.get("notes") or ""
            section = dev_copy.get("section") or "default"

            # Lấy ngữ cảnh bổ sung từ ambiguous_symbols nếu có
            device_specific_context = next(
                (
                    str(sym.get("description") or "") + " " + str(sym.get("possible_types") or "")
                    for sym in ambiguous_symbols
                    if isinstance(sym, dict) and (
                        name.lower() in str(sym.get("tag") or "").lower()
                        or name.lower() in str(sym.get("description") or "").lower()
                    )
                ),
                "",
            )
            combined_context = f"{full_context} {device_specific_context} {notes}"

            cnt_in_section = contactor_counts.get(section, 1)
            resolution = SmartDeviceResolver.resolve_device(
                name=name,
                category=category,
                notes=notes,
                circuit_context=combined_context,
                contactor_count_in_vicinity=cnt_in_section,
            )

            # Gắn kết quả suy luận
            dev_copy["smart_resolved"] = resolution
            dev_copy["is_installation_only"] = resolution.get("is_installation_only", False)

            # Cập nhật tên/category nếu confidence đủ cao
            if (
                resolution.get("confidence", 0) >= 0.75
                and not resolution.get("is_installation_only")
                and resolution.get("resolved_name") != name
            ):
                dev_copy["original_name"] = name
                dev_copy["name"] = resolution["resolved_name"]
                dev_copy["category"] = resolution.get("resolved_category") or category
                dev_copy["smart_resolution_note"] = resolution.get("reasoning") or ""

            enriched.append(dev_copy)

        return enriched
