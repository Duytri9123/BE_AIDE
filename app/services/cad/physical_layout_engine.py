"""
Physical Layout Engine - Hệ Thống Bố Trí Vật Lý Tủ Điện Chuẩn Công Nghiệp
Phân tích quan hệ 6 tầng:
Electrical Schematic -> Circuit -> Device -> Load -> Physical Component -> Physical Location

Tuân thủ 8 bước kỹ thuật:
1. Trích xuất toàn diện thiết bị (kèm Tag, Upstream, Downstream, Connected Load, Rating)
2. Phân loại thiết bị theo vị trí lắp đặt (Mounting Classification: 7 loại)
3. Xác định vị trí vật lý theo nguyên tắc công thái học & kỹ thuật điện
4. Bố trí theo cấu trúc chuẩn: INCOMING -> MAIN PROTECTION -> MAIN BUSBAR -> OUTGOING -> CONTROL -> TERMINAL
5. Sinh mô hình dữ liệu Physical Layout Model 3D/2D (Tag, Type, Mounting, X, Y, Z, W, H, D)
6. Kiểm tra xung đột hình học (Collision, Overlap, Clearance, Door Clearance -> LAYOUT_CONFLICT)
7. Chế độ PANEL_LAYOUT_ONLY (Cabinet, Plate, Components, Busbar, Rails, Ducts, Terminals, Dimensions, Tags - Không vẽ dây)
8. Traceability 2 chiều (CAD Component -> Tag -> Circuit -> Load -> SKU -> BOM STT)
"""
import re
import math
from typing import List, Dict, Any, Optional, Tuple
from app.core.config import settings
from app.core.constants import (
    BUSBAR_REQUIRED_MIN_CURRENT_A,
    FLOOR_STANDING_HEIGHT_THRESHOLD_MM,
)


class MountingType:
    DOOR_MOUNTED = "DOOR_MOUNTED"
    INNER_COVER_MOUNTED = "INNER_COVER_MOUNTED"
    MOUNTING_PLATE_MOUNTED = "MOUNTING_PLATE_MOUNTED"
    DIN_RAIL_MOUNTED = "DIN_RAIL_MOUNTED"
    BUSBAR_MOUNTED = "BUSBAR_MOUNTED"
    CABINET_MOUNTED = "CABINET_MOUNTED"
    NOT_PHYSICALLY_MOUNTED = "NOT_PHYSICALLY_MOUNTED"


class ElectricalFunction:
    INCOMING = "INCOMING"
    MAIN_PROTECTION = "MAIN_PROTECTION"
    MAIN_BUSBAR = "MAIN_BUSBAR"
    OUTGOING_PROTECTION = "OUTGOING_PROTECTION"
    CONTROL_AUXILIARY = "CONTROL_AUXILIARY"
    TERMINAL_CONNECTION = "TERMINAL_CONNECTION"
    MEASUREMENT = "MEASUREMENT"
    EARTHING = "EARTHING"


class PhysicalLayoutEngine:
    """
    Engine tính toán và kiểm tra bố trí vật lý 3 chiều (Spatial Layout Engine) cho tủ bảng điện.
    """

    @staticmethod
    def classify_mounting(device: Dict[str, Any]) -> str:
        """
        BƯỚC 2 — PHÂN LOẠI THIẾT BỊ THEO VỊ TRÍ LẮP ĐẶT (7 nhóm chuẩn kỹ thuật)
        """
        cat = str(device.get("category") or "").upper()
        name = str(device.get("name") or "").upper()
        in_a = float(device.get("in_a") or 0)
        section = str(device.get("section") or "").upper()

        # 1. DOOR_MOUNTED: Thiết bị gắn trên cánh tủ ngoài
        if any(k in cat for k in ["METER", "LIGHT", "PILOT", "HMI", "BUTTON", "SWITCH"]) or \
           any(k in name for k in ["ĐỒNG HỒ", "ĐÈN BÁO", "CHUYỂN MẠCH", "NÚT NHẤN", "VOLT", "AMPE", "MFM", "KHOA"]):
            # Ngoại trừ biến dòng CT (CT xỏ lỗ gắn trên busbar hoặc thanh cáp)
            if "CT" not in cat and "BIẾN DÒNG" not in name:
                return MountingType.DOOR_MOUNTED

        # 2. BUSBAR_MOUNTED: Gắn trên hệ thanh cái đồng
        if any(k in cat for k in ["BUSBAR", "CT"]) or any(k in name for k in ["THANH CÁI", "BIẾN DÒNG", "ĐỒNG THANH"]):
            return MountingType.BUSBAR_MOUNTED

        # 3. CABINET_MOUNTED: Cố định vào kết cấu khung vỏ tủ
        if any(k in cat for k in ["DUCT", "FAN", "LOUVER", "PLINTH", "ENCLOSURE"]) or \
           any(k in name for k in ["MÁNG CÁP", "QUẠT HÚT", "CHỚP THOÁNG", "CHÂN ĐẾ", "VỎ TỦ"]):
            return MountingType.CABINET_MOUNTED

        # 4. MOUNTING_PLATE_MOUNTED: Gắn trực tiếp lên tấm panel lưng (Mounting plate)
        # Các thiết bị lớn, tải trọng nặng: ACB, MCCB lớn (>= 160A), biến tần VFD, khởi động mềm, biến áp
        if "ACB" in cat or (cat == "MCCB" and in_a >= 160) or \
           any(k in cat for k in ["VFD", "SOFT_STARTER", "TRANSFORMER", "INVERTER"]) or \
           any(k in name for k in ["BIẾN TẦN", "KHỞI ĐỘNG MỀM", "BIẾN ÁP"]):
            return MountingType.MOUNTING_PLATE_MOUNTED

        # 5. DIN_RAIL_MOUNTED: Gắn trên ray nhôm DIN 35mm (IEC 60715)
        # MCB, RCBO, MCCB nhỏ (<160A có đế ray hoặc plate), contactor, relay, timer, fuse tép, domino terminal
        if any(k in cat for k in ["MCB", "RCBO", "RCCB", "FUSE", "CONTACTOR", "TIMER", "RELAY", "TERMINAL", "POWER_SUPPLY"]) or \
           any(k in name for k in ["APTOMAT NHÁNH", "CẦU CHÌ", "KHỞI ĐỘNG TỪ", "RƠ LE", "HẸN GIỜ", "CẦU ĐẤU", "DOMINO", "BỘ NGUỒN"]):
            return MountingType.DIN_RAIL_MOUNTED

        # Mặc định với MCCB công suất nhỏ: gắn trên ray hoặc plate
        if cat == "MCCB":
            return MountingType.MOUNTING_PLATE_MOUNTED if in_a >= 100 else MountingType.DIN_RAIL_MOUNTED

        # 6. NOT_PHYSICALLY_MOUNTED: Các đối tượng thuộc sơ đồ logic
        if any(k in name for k in ["TBA", "NGUỒN NGOÀI", "LƯỚI ĐIỆN", "TẢI NGOÀI", "ĐỘNG CƠ NGOÀI"]):
            return MountingType.NOT_PHYSICALLY_MOUNTED

        return MountingType.MOUNTING_PLATE_MOUNTED

    @staticmethod
    def extract_or_assign_tag(device: Dict[str, Any], index: int, role: str) -> str:
        """
        BƯỚC 1 & 8 — TRÍCH XUẤT HOẶC KHỞI TẠO TAG ĐỊNH DANH DUY NHẤT THEO TIÊU CHUẨN IEC 81346
        Ví dụ: QF1, QF2, KM1, KT1, PI1, PA1, PV1, HL1, FU1, TB1, PE
        """
        raw_name = str(device.get("name") or "").strip()
        raw_notes = str(device.get("notes") or "").strip()
        cat = str(device.get("category") or "").upper()
        existing_tag = str(device.get("tag") or "").strip()

        if existing_tag:
            return existing_tag.upper()

        combined = f"{raw_name} {raw_notes}".upper()

        # Tìm kiếm các mẫu tag phổ biến trên bản vẽ kỹ thuật (ví dụ: QF1, 1M, M1, MCCB-01, CB-1, KM1, KT1...)
        m_tag = re.search(r'\b(QF\d+|KM\d+|KT\d+|HL\d+|PA\d+|PV\d+|PI\d+|FU\d+|TB\d+|MCB\d+|MCCB\d+|M\d+|\d+M)\b', combined)
        if m_tag:
            return m_tag.group(1)

        # Nếu không có tag sẵn trên bản vẽ, sinh tag kỹ thuật chuẩn IEC
        if role == ElectricalFunction.INCOMING or "INCOMER" in combined or "TỔNG" in combined:
            return "QF1"
        elif "ACB" in cat or "MCCB" in cat or "MCB" in cat or "RCBO" in cat:
            return f"QF{index + 1}"
        elif "CONTACTOR" in cat or "KHỞI ĐỘNG TỪ" in combined:
            return f"KM{index + 1}"
        elif "TIMER" in cat or "HẸN GIỜ" in combined:
            return f"KT{index + 1}"
        elif "RELAY" in cat or "RƠ LE" in combined:
            return f"KA{index + 1}"
        elif "FUSE" in cat or "CẦU CHÌ" in combined:
            return f"FU{index + 1}"
        elif "CT" in cat or "BIẾN DÒNG" in combined:
            return f"TA{index + 1}"
        elif "LIGHT" in cat or "ĐÈN" in combined:
            return f"HL{index + 1}"
        elif "VOLT" in combined or "VÔN" in combined:
            return "PV1"
        elif "AMPE" in combined:
            return "PA1"
        elif "METER" in cat or "MFM" in combined or "ĐỒNG HỒ" in combined:
            return "PI1"
        elif "TERMINAL" in cat or "DOMINO" in combined:
            return "TB1"
        elif "PE" in combined or "TIẾP ĐỊA" in combined:
            return "PE"
        elif "N" in combined or "TRUNG TÍNH" in combined:
            return "N"

        return f"D{index + 1}"

    @staticmethod
    def get_component_dimensions(device: Dict[str, Any]) -> Tuple[float, float, float]:
        """
        Lấy kích thước vật lý thực tế (Width x Height x Depth mm) trực tiếp từ Catalog thiết bị của hệ thống:
        - catalog_data.json (1.498 model thiết bị đóng cắt của các hãng LS, Schneider, Mitsubishi, ABB, Chint...)
        - catalog_accessories.json (Busbar, DIN rail, Máng cáp, Phụ kiện cánh tủ, Đồng hồ, Đèn báo...)
        Không tự tính kích thước hardcode để đảm bảo vị trí và kích thước trên bản vẽ chuẩn xác theo từng hãng.
        """
        # 1. Kiểm tra nếu device đã có sẵn dimensions hợp lệ từ kết quả tra cứu trước
        if isinstance(device.get("dimensions"), dict):
            dims = device["dimensions"]
            w = float(dims.get("w") or dims.get("w_mm") or 0)
            h = float(dims.get("h") or dims.get("h_mm") or 0)
            d = float(dims.get("d") or dims.get("d_mm") or 0)
            if w > 0 and h > 0:
                return (w, h, d if d > 0 else 60.0)

        cat = str(device.get("category") or "").upper()
        name = str(device.get("name") or "")
        poles = int(device.get("poles") or (1 if "MCB" in cat and "3P" not in name.upper() else 3))
        in_a = float(device.get("in_a") or 0)
        min_icu = float(device.get("icu_ka") or device.get("icu") or 0)
        brand = str(device.get("brand") or "").strip()
        part_number = str(device.get("part_number") or device.get("sku") or "").strip()

        # 2. Kích thước trực tiếp từ bản vẽ hoặc thông số thiết bị do người dùng/sơ đồ chỉ định
        dw = float(device.get("w") or device.get("width") or 0)
        dh = float(device.get("h") or device.get("height") or 0)
        dd = float(device.get("d") or device.get("depth") or 0)
        if dw > 0 and dh > 0:
            return (dw, dh, dd if dd > 0 else 50.0)

        # 3. Phân loại tra cứu: Thiết bị đóng cắt chính (Breakers) vs Phụ kiện / Cánh tủ (Accessories)
        try:
            from app.services.device_catalog_engine import catalog_engine

            breaker_types = ["ACB", "MCCB", "MCB", "RCBO", "RCCB", "ELCB", "CONTACTOR", "ATS", "MTS", "SPD"]
            is_breaker = any(b in cat for b in breaker_types)

            # 3.1 Tra cứu thiết bị đóng cắt chính từ catalog_data.json
            if is_breaker:
                cat_info = catalog_engine.lookup_device_info(
                    category=cat,
                    in_a=in_a if in_a > 0 else None,
                    poles=poles,
                    brand=brand if brand else None,
                    part_number=part_number if part_number else None,
                    name=name,
                    min_icu=min_icu if min_icu > 0 else None,
                )
                if cat_info and isinstance(cat_info.get("dimensions"), dict):
                    c_dims = cat_info["dimensions"]
                    cw = float(c_dims.get("w") or 0)
                    ch = float(c_dims.get("h") or 0)
                    cd = float(c_dims.get("d") or 0)
                    if cw > 0 and ch > 0:
                        device["dimensions"] = c_dims
                        if not device.get("part_number") and cat_info.get("sku") and cat_info.get("rating_compatible", True):
                            device["part_number"] = cat_info["sku"]
                        elif cat_info.get("dimension_proxy") and cat_info.get("sku"):
                            device["dimension_proxy_sku"] = cat_info["sku"]
                        if not device.get("brand") and cat_info.get("brand"):
                            device["brand"] = cat_info["brand"]
                        if cat_info.get("compatibility_warning"):
                            device["catalog_compatibility_warning"] = cat_info["compatibility_warning"]
                            device["catalog_rating_compatible"] = False
                        else:
                            device["catalog_rating_compatible"] = True
                        return (cw, ch, cd if cd > 0 else 60.0)

            # 3.2 Tra cứu phụ kiện cơ điện & mặt cánh từ catalog_accessories.json
            item_id = str(device.get("id") or device.get("catalog_id") or "").lower()
            if item_id:
                acc_it = catalog_engine.get_accessory(item_id)
                if acc_it:
                    aw = float(acc_it.get("w_mm") or acc_it.get("cut_w_mm") or acc_it.get("outer_dia_mm") or (acc_it.get("cut_dia_mm", 0) + 7) or 0)
                    ah = float(acc_it.get("h_mm") or acc_it.get("cut_h_mm") or acc_it.get("outer_dia_mm") or (acc_it.get("cut_dia_mm", 0) + 7) or 0)
                    ad = float(acc_it.get("d_mm") or 50.0)
                    if aw > 0 and ah > 0:
                        return (aw, ah, ad)

            # Xác định nhóm phụ kiện ưu tiên theo Category hoặc Tên
            category_group_map = {
                "METER": "door_accessories",
                "LIGHT": "door_accessories",
                "PILOT": "door_accessories",
                "PILOT_LIGHT": "door_accessories",
                "BUTTON": "door_accessories",
                "PUSH_BUTTON": "door_accessories",
                "SWITCH": "door_accessories",
                "SELECTOR_SWITCH": "door_accessories",
                "FAN": "door_accessories",
                "LOCK": "door_accessories",
                "TERMINAL": "accessories",
                "DOMINO": "accessories",
                "RELAY": "accessories",
                "TIMER": "accessories",
                "CT": "accessories",
                "FUSE": "accessories",
                "BUSBAR": "busbar",
                "EARTH_BAR": "busbar",
                "DIN_RAIL": "din_rail",
                "DUCT": "cable_duct",
                "CABLE_DUCT": "cable_duct",
                "SPD": "accessories",
            }
            preferred_group = None
            for cat_k, grp_v in category_group_map.items():
                if cat_k in cat or cat_k in name.upper():
                    preferred_group = grp_v
                    break

            search_groups = [preferred_group] if preferred_group else []
            for g in ["accessories", "door_accessories", "busbar", "din_rail", "cable_duct"]:
                if g not in search_groups:
                    search_groups.append(g)

            acc_kw = name or cat
            for group_name in search_groups:
                acc_it = catalog_engine.lookup_accessory(group_name, acc_kw)
                if acc_it:
                    aw = float(acc_it.get("w_mm") or acc_it.get("cut_w_mm") or acc_it.get("outer_dia_mm") or (acc_it.get("cut_dia_mm", 0) + 7) or 0)
                    ah = float(acc_it.get("h_mm") or acc_it.get("cut_h_mm") or acc_it.get("outer_dia_mm") or (acc_it.get("cut_dia_mm", 0) + 7) or 0)
                    ad = float(acc_it.get("d_mm") or 50.0)
                    if aw > 0 and ah > 0:
                        return (aw, ah, ad)

            # 3.3 Dự phòng nếu không thuộc nhóm breaker nhưng vẫn có trong catalog chính
            if not is_breaker:
                cat_info = catalog_engine.lookup_device_info(
                    category=cat,
                    in_a=in_a if in_a > 0 else None,
                    poles=poles,
                    brand=brand if brand else None,
                    part_number=part_number if part_number else None,
                    name=name,
                    min_icu=min_icu if min_icu > 0 else None,
                )
                if cat_info and isinstance(cat_info.get("dimensions"), dict):
                    c_dims = cat_info["dimensions"]
                    cw = float(c_dims.get("w") or 0)
                    ch = float(c_dims.get("h") or 0)
                    cd = float(c_dims.get("d") or 0)
                    if cw > 0 and ch > 0:
                        device["dimensions"] = c_dims
                        return (cw, ch, cd if cd > 0 else 60.0)
        except Exception:
            pass

        # 4. Mặc định cho thiết bị custom chưa xác định được trong catalog (tránh crash layout)
        return (60.0, 80.0, 60.0)

    @staticmethod
    def generate_busbar_svg(width: float, height: float, phase: str, label: str = "") -> str:
        """Sinh mã SVG vector thanh cái đồng nguyên chất chuẩn màu pha IEC & bước lỗ bu-lông."""
        color_map = {
            "R": "#e53935", "L1": "#e53935",
            "S": "#f9a825", "L2": "#f9a825",
            "T": "#1565c0", "L3": "#1565c0",
            "N": "#212121", "PE": "#2e7d32"
        }
        bar_col = color_map.get(phase.upper(), "#d97706")
        num_holes = max(2, int(width / 70.0))
        hole_pitch = width / (num_holes + 1)
        holes_svg = "".join([
            f'<circle cx="{hole_pitch * (i + 1):.1f}" cy="{height / 2:.1f}" r="3.2" fill="#0f172a" stroke="#ffffff" stroke-width="0.8"/>'
            f'<line x1="{hole_pitch * (i + 1) - 3.5:.1f}" y1="{height / 2:.1f}" x2="{hole_pitch * (i + 1) + 3.5:.1f}" y2="{height / 2:.1f}" stroke="#ffffff" stroke-width="0.5"/>'
            f'<line x1="{hole_pitch * (i + 1):.1f}" y1="{height / 2 - 3.5:.1f}" x2="{hole_pitch * (i + 1):.1f}" y2="{height / 2 + 3.5:.1f}" stroke="#ffffff" stroke-width="0.5"/>'
            for i in range(num_holes)
        ])
        text_disp = label or f"BUSBAR {phase}"
        return (
            f'<svg viewBox="0 0 {width:.1f} {height:.1f}" width="{width:.1f}" height="{height:.1f}" xmlns="http://www.w3.org/2000/svg">'
            f'<rect x="0" y="0" width="{width:.1f}" height="{height:.1f}" rx="2" fill="{bar_col}" stroke="#0f172a" stroke-width="1.2"/>'
            f'{holes_svg}'
            f'<text x="14" y="{height / 2 + 3.5:.1f}" fill="#ffffff" font-size="8.5" font-family="sans-serif" font-weight="bold">{text_disp}</text>'
            f'</svg>'
        )

    @staticmethod
    def generate_din_rail_svg(width: float, height: float = 35.0) -> str:
        """Sinh mã SVG vector thanh ray nhôm xẻ rãnh mạ kẽm DIN TH35 (IEC 60715)."""
        num_slots = max(3, int(width / 25.0))
        slot_w = 12.0
        slot_h = 5.0
        slots_svg = "".join([
            f'<rect x="{15.0 + i * 25.0:.1f}" y="{(height - slot_h) / 2:.1f}" width="{slot_w}" height="{slot_h}" rx="2.5" fill="#334155" stroke="#94a3b8" stroke-width="0.5"/>'
            for i in range(num_slots) if 15.0 + i * 25.0 + slot_w < width - 10
        ])
        return (
            f'<svg viewBox="0 0 {width:.1f} {height:.1f}" width="{width:.1f}" height="{height:.1f}" xmlns="http://www.w3.org/2000/svg">'
            f'<rect x="0" y="0" width="{width:.1f}" height="{height:.1f}" fill="#cbd5e1" stroke="#64748b" stroke-width="1.2"/>'
            f'<rect x="0" y="4" width="{width:.1f}" height="{height - 8:.1f}" fill="#e2e8f0" stroke="#94a3b8" stroke-width="0.8"/>'
            f'{slots_svg}'
            f'<text x="{width / 2:.1f}" y="{height / 2 + 3:.1f}" fill="#64748b" font-size="8" font-family="sans-serif" font-weight="bold" text-anchor="middle">DIN 35 (IEC 60715)</text>'
            f'</svg>'
        )

    @staticmethod
    def generate_cable_duct_svg(width: float, height: float, is_vertical: bool = True) -> str:
        """Sinh mã SVG vector máng cáp nhựa xẻ rãnh thoát dây (Slotted PVC Cable Duct)."""
        if is_vertical:
            num_fingers = max(2, int(height / 16.0))
            slots_svg = "".join([
                f'<line x1="2" y1="{8 + i * 16:.1f}" x2="{width - 2:.1f}" y2="{8 + i * 16:.1f}" stroke="#475569" stroke-width="2"/>'
                for i in range(num_fingers) if 8 + i * 16 < height - 8
            ])
        else:
            num_fingers = max(2, int(width / 16.0))
            slots_svg = "".join([
                f'<line x1="{8 + i * 16:.1f}" y1="2" x2="{8 + i * 16:.1f}" y2="{height - 2:.1f}" stroke="#475569" stroke-width="2"/>'
                for i in range(num_fingers) if 8 + i * 16 < width - 8
            ])
        return (
            f'<svg viewBox="0 0 {width:.1f} {height:.1f}" width="{width:.1f}" height="{height:.1f}" xmlns="http://www.w3.org/2000/svg">'
            f'<rect x="0" y="0" width="{width:.1f}" height="{height:.1f}" rx="2" fill="#94a3b8" stroke="#475569" stroke-width="1.2"/>'
            f'{slots_svg}'
            f'<rect x="4" y="4" width="{max(2.0, width - 8):.1f}" height="{max(2.0, height - 8):.1f}" fill="#cbd5e1" stroke="#64748b" stroke-width="0.8" opacity="0.85"/>'
            f'</svg>'
        )

    @staticmethod
    def generate_breaker_svg(
        cat: str,
        width: float,
        height: float,
        tag: str,
        in_a: float,
        poles: int = 3,
        brand: str = "VN",
        sku: str = ""
    ) -> str:
        """Sinh mã SVG vector thiết bị đóng cắt công nghiệp chân thực (ACB/MCCB/MCB/Contactor)."""
        cat_u = cat.upper()
        brand_u = brand.upper()
        if "SCHNEIDER" in brand_u:
            body_col = "#1e293b"
            accent_col = "#009639"
        elif "MITSUBISHI" in brand_u:
            body_col = "#0f172a"
            accent_col = "#e60012"
        elif "ABB" in brand_u:
            body_col = "#1e293b"
            accent_col = "#ff000f"
        elif "LS" in brand_u:
            body_col = "#1e293b"
            accent_col = "#004b97"
        else:
            body_col = "#1e293b"
            accent_col = "#3b82f6"

        pole_w = width / max(1, poles)
        term_h = min(12.0, height * 0.12)
        terminals_svg = "".join([
            f'<rect x="{i * pole_w + 3:.1f}" y="2" width="{max(2.0, pole_w - 6):.1f}" height="{term_h:.1f}" rx="1.5" fill="#d97706" stroke="#92400e" stroke-width="0.8"/>'
            f'<rect x="{i * pole_w + 3:.1f}" y="{height - term_h - 2:.1f}" width="{max(2.0, pole_w - 6):.1f}" height="{term_h:.1f}" rx="1.5" fill="#d97706" stroke="#92400e" stroke-width="0.8"/>'
            for i in range(poles)
        ])

        handle_w = min(width * 0.45, 32.0)
        handle_h = min(height * 0.28, 28.0)
        handle_x = (width - handle_w) / 2.0
        handle_y = (height - handle_h) / 2.0

        return (
            f'<svg viewBox="0 0 {width:.1f} {height:.1f}" width="{width:.1f}" height="{height:.1f}" xmlns="http://www.w3.org/2000/svg">'
            f'<rect x="0" y="0" width="{width:.1f}" height="{height:.1f}" rx="3" fill="{body_col}" stroke="#0f172a" stroke-width="1.5"/>'
            f'{terminals_svg}'
            f'<rect x="3" y="{term_h + 3:.1f}" width="{max(4.0, width - 6):.1f}" height="{max(4.0, height - 2 * term_h - 6):.1f}" rx="2" fill="#334155" stroke="{accent_col}" stroke-width="1"/>'
            f'<rect x="{handle_x:.1f}" y="{handle_y:.1f}" width="{handle_w:.1f}" height="{handle_h:.1f}" rx="2" fill="#0f172a" stroke="#cbd5e1" stroke-width="1"/>'
            f'<rect x="{handle_x + 3:.1f}" y="{handle_y + 2:.1f}" width="{max(2.0, handle_w - 6):.1f}" height="{handle_h / 2:.1f}" rx="1" fill="#dc2626"/>'
            f'<text x="{width / 2:.1f}" y="{term_h + 14:.1f}" fill="#38bdf8" font-size="8" font-family="sans-serif" font-weight="bold" text-anchor="middle">[{tag}]</text>'
            f'<text x="{width / 2:.1f}" y="{height - term_h - 6:.1f}" fill="#f8fafc" font-size="7" font-family="sans-serif" font-weight="bold" text-anchor="middle">{cat_u} {int(in_a)}A</text>'
            f'</svg>'
        )

    @staticmethod
    def generate_door_accessory_svg(
        acc_type: str,
        width: float,
        height: float,
        tag: str = "",
        label: str = "",
        color: str = "#e53935"
    ) -> str:
        """Sinh mã SVG vector phụ kiện mặt cánh tủ (Đồng hồ LCD MFM, Đèn báo pha, Khóa tay gạt)."""
        center_x = width / 2.0
        center_y = height / 2.0

        if acc_type == "pilot_lamp":
            r_outer = min(center_x, center_y) * 0.95
            r_lens = r_outer * 0.72
            return (
                f'<svg viewBox="0 0 {width:.1f} {height:.1f}" width="{width:.1f}" height="{height:.1f}" xmlns="http://www.w3.org/2000/svg">'
                f'<circle cx="{center_x:.1f}" cy="{center_y:.1f}" r="{r_outer:.1f}" fill="#334155" stroke="#64748b" stroke-width="2"/>'
                f'<circle cx="{center_x:.1f}" cy="{center_y:.1f}" r="{r_outer * 0.88:.1f}" fill="#0f172a"/>'
                f'<circle cx="{center_x:.1f}" cy="{center_y:.1f}" r="{r_lens:.1f}" fill="{color}"/>'
                f'<circle cx="{center_x - r_lens * 0.3:.1f}" cy="{center_y - r_lens * 0.3:.1f}" r="{r_lens * 0.28:.1f}" fill="#ffffff" opacity="0.4"/>'
                f'<text x="{center_x:.1f}" y="{center_y + 3.5:.1f}" fill="#ffffff" font-size="8.5" font-family="sans-serif" font-weight="bold" text-anchor="middle">220V</text>'
                f'</svg>'
            )

        if acc_type == "digital_meter":
            return (
                f'<svg viewBox="0 0 {width:.1f} {height:.1f}" width="{width:.1f}" height="{height:.1f}" xmlns="http://www.w3.org/2000/svg">'
                f'<rect x="2" y="2" width="{width - 4:.1f}" height="{height - 4:.1f}" rx="4" fill="#1e293b" stroke="#0f172a" stroke-width="2.5"/>'
                f'<rect x="8" y="8" width="{width - 16:.1f}" height="{height * 0.52:.1f}" rx="2" fill="#022c22" stroke="#059669" stroke-width="1"/>'
                f'<text x="14" y="22" fill="#34d399" font-size="8" font-family="monospace" font-weight="bold">U: 380.5 V</text>'
                f'<text x="14" y="34" fill="#34d399" font-size="8" font-family="monospace" font-weight="bold">I: 245.2 A</text>'
                f'<text x="14" y="46" fill="#34d399" font-size="8" font-family="monospace" font-weight="bold">P: 158.4 kW</text>'
                f'<circle cx="{width * 0.3:.1f}" cy="{height * 0.8:.1f}" r="4" fill="#475569" stroke="#94a3b8"/>'
                f'<circle cx="{width * 0.5:.1f}" cy="{height * 0.8:.1f}" r="4" fill="#475569" stroke="#94a3b8"/>'
                f'<circle cx="{width * 0.7:.1f}" cy="{height * 0.8:.1f}" r="4" fill="#475569" stroke="#94a3b8"/>'
                f'<text x="{width / 2:.1f}" y="{height - 5:.1f}" fill="#94a3b8" font-size="7" font-family="sans-serif" text-anchor="middle">MFM 96x96</text>'
                f'</svg>'
            )

        return (
            f'<svg viewBox="0 0 {width:.1f} {height:.1f}" width="{width:.1f}" height="{height:.1f}" xmlns="http://www.w3.org/2000/svg">'
            f'<rect x="2" y="2" width="{width - 4:.1f}" height="{height - 4:.1f}" rx="3" fill="#334155" stroke="#cbd5e1" stroke-width="1.5"/>'
            f'<text x="{center_x:.1f}" y="{center_y + 3:.1f}" fill="#ffffff" font-size="8" font-family="sans-serif" font-weight="bold" text-anchor="middle">{label or tag}</text>'
            f'</svg>'
        )

    @staticmethod
    def render_full_view_svg(
        view_type: str,
        enclosure: Dict[str, float],
        components: List[Dict[str, Any]],
        mounting_plate: Optional[Dict[str, float]] = None
    ) -> str:
        """
        Sinh bản vẽ SVG toàn cảnh hoàn chỉnh theo chuẩn công nghiệp cho:
        - 'internal_ga': Tấm gá plate, busbars, máng cáp, ray DIN, thiết bị đóng cắt, domino, PE.
        - 'inner_cover': Tấm che Form 2B, khe khoét cần gạt, khóa góc 1/4 vòng.
        - 'front_door': Mặt cánh ngoài, đèn báo pha, đồng hồ LCD, cảnh báo điện giật, khóa xoay.
        """
        W = float(enclosure.get("W", 800.0))
        H = float(enclosure.get("H", 1200.0))
        plinth = float(enclosure.get("plinth", 100.0 if H >= 1200 else 0.0))
        total_h = H + plinth

        elements: List[str] = []

        if view_type == "internal_ga":
            # 1. Khung tủ ngoài & Chân đế
            elements.append(f'<rect x="0" y="0" width="{W}" height="{total_h}" fill="#1e293b" stroke="#475569" stroke-width="2"/>')
            if plinth > 0:
                elements.append(f'<rect x="0" y="0" width="{W}" height="{plinth}" fill="#0f172a" stroke="#334155" stroke-width="1.5"/>')
                elements.append(f'<text x="{W / 2}" y="{plinth / 2 + 4}" fill="#64748b" font-size="11" font-family="sans-serif" font-weight="bold" text-anchor="middle">CHÂN ĐẾ {int(plinth)}mm</text>')

            # 2. Tấm gá Panel Lưng (Mounting Plate)
            if mounting_plate:
                px = mounting_plate["x"]
                py = total_h - (mounting_plate["y"] + mounting_plate["height"])
                pw = mounting_plate["width"]
                ph = mounting_plate["height"]
                elements.append(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="3" fill="#e2e8f0" stroke="#94a3b8" stroke-width="1.5"/>')
                for hx, hy in [(px + 12, py + 12), (px + pw - 12, py + 12), (px + 12, py + ph - 12), (px + pw - 12, py + ph - 12)]:
                    elements.append(f'<circle cx="{hx}" cy="{hy}" r="5" fill="#334155" stroke="#ffffff" stroke-width="1"/>')

            # 3. Lắp ghép từng Component Block vào tọa độ SVG
            for c in components:
                if c.get("mounting") == MountingType.DOOR_MOUNTED:
                    continue
                cx = float(c.get("x", 0))
                cy_eng = float(c.get("y", 0))
                cw = float(c.get("width", 60))
                ch = float(c.get("height", 80))
                cy = total_h - (cy_eng + ch)
                svg_block = c.get("svg_content", "")
                if svg_block:
                    elements.append(f'<g transform="translate({cx:.1f}, {cy:.1f})">{svg_block}</g>')
                else:
                    elements.append(f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cw:.1f}" height="{ch:.1f}" fill="#475569" stroke="#94a3b8" stroke-width="1"/>')

        elif view_type == "front_door":
            elements.append(f'<rect x="0" y="0" width="{W}" height="{total_h}" fill="#f1f5f9" stroke="#334155" stroke-width="3"/>')
            if plinth > 0:
                elements.append(f'<rect x="0" y="0" width="{W}" height="{plinth}" fill="#0f172a" stroke="#334155" stroke-width="1.5"/>')
                elements.append(f'<text x="{W / 2}" y="{plinth / 2 + 4}" fill="#64748b" font-size="11" font-family="sans-serif" font-weight="bold" text-anchor="middle">CHÂN ĐẾ {int(plinth)}mm</text>')

            elements.append(f'<rect x="15" y="{plinth + 15}" width="{W - 30}" height="{H - 30}" rx="4" fill="#e2e8f0" stroke="#64748b" stroke-width="2"/>')

            warn_w = 120.0
            warn_h = 75.0
            warn_x = (W - warn_w) / 2.0
            warn_y = plinth + H * 0.55
            elements.append(f'<rect x="{warn_x}" y="{warn_y}" width="{warn_w}" height="{warn_h}" rx="3" fill="#fef08a" stroke="#ca8a04" stroke-width="1.5"/>')
            elements.append(f'<text x="{W / 2}" y="{warn_y + 24}" fill="#b91c1c" font-size="11" font-family="sans-serif" font-weight="bold" text-anchor="middle">NGUY HIỂM</text>')
            elements.append(f'<text x="{W / 2}" y="{warn_y + 44}" fill="#1e293b" font-size="9.5" font-family="sans-serif" font-weight="bold" text-anchor="middle">CÓ ĐIỆN 380V</text>')
            elements.append(f'<text x="{W / 2}" y="{warn_y + 62}" fill="#475569" font-size="7" font-family="sans-serif" text-anchor="middle">KHÔNG PHẬN SỰ MIỄN VÀO</text>')

            lock_x = W - 45.0
            lock_y = plinth + H * 0.45
            elements.append(f'<rect x="{lock_x}" y="{lock_y}" width="20" height="70" rx="3" fill="#475569" stroke="#0f172a" stroke-width="1.5"/>')
            elements.append(f'<circle cx="{lock_x + 10}" cy="{lock_y + 20}" r="4" fill="#cbd5e1"/>')

            for c in components:
                if c.get("mounting") != MountingType.DOOR_MOUNTED:
                    continue
                cx = float(c.get("x", 0))
                cy_eng = float(c.get("y", 0))
                cw = float(c.get("width", 30))
                ch = float(c.get("height", 30))
                cy = total_h - (cy_eng + ch)
                svg_block = c.get("svg_content", "")
                if svg_block:
                    elements.append(f'<g transform="translate({cx:.1f}, {cy:.1f})">{svg_block}</g>')

        elif view_type == "inner_cover":
            elements.append(f'<rect x="0" y="0" width="{W}" height="{total_h}" fill="#0f172a" stroke="#334155" stroke-width="2"/>')
            cov_margin = 25.0
            cx1 = cov_margin
            cy1 = plinth + cov_margin
            cw = W - 2 * cov_margin
            ch = H - 2 * cov_margin
            elements.append(f'<rect x="{cx1}" y="{cy1}" width="{cw}" height="{ch}" rx="3" fill="#334155" stroke="#94a3b8" stroke-width="2"/>')
            for kx, ky in [(cx1 + 18, cy1 + 18), (cx1 + cw - 18, cy1 + 18), (cx1 + 18, cy1 + ch - 18), (cx1 + cw - 18, cy1 + ch - 18)]:
                elements.append(f'<circle cx="{kx}" cy="{ky}" r="6" fill="#94a3b8" stroke="#ffffff" stroke-width="0.8"/>')
                elements.append(f'<line x1="{kx - 4}" y1="{ky}" x2="{kx + 4}" y2="{ky}" stroke="#1e293b" stroke-width="1.2"/>')

            for c in components:
                if c.get("function") in [ElectricalFunction.MAIN_PROTECTION, ElectricalFunction.OUTGOING_PROTECTION]:
                    kx = float(c.get("x", 0)) - 5.0
                    ky_eng = float(c.get("y", 0)) - 5.0
                    kw = float(c.get("width", 60)) + 10.0
                    kh = float(c.get("height", 80)) + 10.0
                    ky = total_h - (ky_eng + kh)
                    elements.append(f'<rect x="{kx:.1f}" y="{ky:.1f}" width="{kw:.1f}" height="{kh:.1f}" rx="2" fill="#0f172a" stroke="#cbd5e1" stroke-dasharray="3,2" stroke-width="1"/>')
                    elements.append(f'<text x="{kx + kw / 2:.1f}" y="{ky - 4:.1f}" fill="#38bdf8" font-size="8" font-family="sans-serif" text-anchor="middle">[{c.get("tag")}]</text>')

        body_svg = "\n".join(elements)
        return (
            f'<svg viewBox="0 0 {W:.1f} {total_h:.1f}" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">\n'
            f'{body_svg}\n'
            f'</svg>'
        )

    @staticmethod
    def compute_physical_layout_model(
        devices: List[Dict[str, Any]],
        enclosure_spec: Optional[Dict[str, Any]] = None,
        mode: str = "PANEL_LAYOUT_ONLY",
        layout_intent: Optional[Dict[str, Any]] = None,
        cabinet_w: Optional[float] = None,
        cabinet_h: Optional[float] = None,
        cabinet_d: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        BƯỚC 4 & 5 — TẠO TOÀN BỘ DỮ LIỆU PHYSICAL LAYOUT MODEL 3D/2D
        Lắp ghép Catalog SVG Blocks thông minh dựa trên AI Spatial Layout Intent:
        - cable_entry: 'TOP' (cáp vào nóc) / 'BOTTOM' (cáp vào đáy)
        - incomer_position: 'TOP_LEFT', 'TOP_CENTER', 'BOTTOM_LEFT'
        - busbar_arrangement: 'TOP_HORIZONTAL', 'BOTTOM_HORIZONTAL', 'NONE'
        - circuit_groups: Phân cụm xuất tuyến theo chức năng kỹ thuật trên sơ đồ
        - door_accessories: Danh mục phụ kiện cánh tủ
        """
        if enclosure_spec is None:
            enclosure_spec = {}
        H = float(cabinet_h or enclosure_spec.get("height") or enclosure_spec.get("H") or 1200.0)
        W = float(cabinet_w or enclosure_spec.get("width") or enclosure_spec.get("W") or 800.0)
        D = float(cabinet_d or enclosure_spec.get("depth") or enclosure_spec.get("D") or 400.0)
        plinth_h = float(enclosure_spec.get("plinth_height") or (settings.ENCLOSURE_DEFAULT_PLINTH_HEIGHT if H >= FLOOR_STANDING_HEIGHT_THRESHOLD_MM else 0.0))

        # Phân tích ý định bố trí từ AI (hoặc tự suy luận từ thiết bị)
        intent = layout_intent or {}
        cable_entry = str(intent.get("cable_entry") or "TOP").upper()
        busbar_opt = str(intent.get("busbar_arrangement") or "AUTO").upper()

        # Kích thước tấm gá panel lưng (Mounting Plate)
        margin = 35.0
        plate_w = W - 2 * margin
        plate_h = H - 2 * margin
        plate_x = margin
        plate_y = plinth_h + margin
        plate_z = 40.0

        duct_w = 40.0  # Máng cáp sườn chuẩn 40x60mm
        work_x1 = plate_x + duct_w + 14.0
        work_x2 = plate_x + plate_w - duct_w - 14.0
        usable_w = max(200.0, work_x2 - work_x1)

        components: List[Dict[str, Any]] = []
        traceability_matrix: List[Dict[str, Any]] = []

        # 1. Tìm Incomer (Thiết bị đầu vào)
        protection = [d for d in devices if str(d.get("category", "")).upper() in ["ACB", "MCCB", "MCB", "RCBO", "RCCB", "ELCB"]]
        explicit = [d for d in protection if str(d.get("section", "")).upper() in ["ĐẦU VÀO", "DAU VAO", "INCOMER", "NGUỒN CẤP", "NGUON CAP"] or any(k in str(d.get("name", "")).upper() for k in ("INCOMER", "TỔNG", "TONG"))]
        incomer_dev = max(explicit or protection or devices, key=lambda d: float(d.get("in_a") or 0)) if devices else None

        inc_a = float(incomer_dev.get("in_a") or 63.0) if incomer_dev else 63.0
        is_3phase = bool(incomer_dev and int(incomer_dev.get("poles") or 3) >= 3)
        need_busbar = (busbar_opt != "NONE") and (inc_a >= BUSBAR_REQUIRED_MIN_CURRENT_A)

        # Phân chia Zone theo hướng cáp vào/ra (Cable Entry: TOP vs BOTTOM)
        top_margin = 25.0
        if cable_entry == "BOTTOM":
            # Cáp vào từ đáy tủ: Terminal Block & Incomer ưu tiên ở nửa dưới
            pe_bar_y = plate_y + 15.0
            pe_bar_h = 15.0
            tb_y = pe_bar_y + pe_bar_h + 15.0
            tb_h = 45.0
            inc_w, inc_h, inc_d = PhysicalLayoutEngine.get_component_dimensions(incomer_dev) if incomer_dev else (80, 130, 75)
            inc_zone_h = max(150.0, inc_h + 30.0)
            inc_y = tb_y + tb_h + 20.0
            zone_branches_bottom = inc_y + inc_zone_h + 15.0
            zone_branches_top = plate_y + plate_h - top_margin - 10.0
            busbar_y = zone_branches_top + 10.0 if need_busbar else 0.0
        else:
            # Cáp vào từ nóc tủ (Chuẩn phổ biến nhất công nghiệp): Busbar nóc -> Incomer -> Nhánh -> Domino đáy
            if need_busbar:
                busbar_h = 120.0
                busbar_y = plate_y + plate_h - top_margin - busbar_h
                zone_inc_top = busbar_y - duct_w - 15.0
            else:
                busbar_h = 0.0
                busbar_y = 0.0
                zone_inc_top = plate_y + plate_h - top_margin

            inc_w, inc_h, inc_d = PhysicalLayoutEngine.get_component_dimensions(incomer_dev) if incomer_dev else (80, 130, 75)
            inc_zone_h = max(150.0, inc_h + 30.0)
            inc_y = zone_inc_top - inc_zone_h + 15.0

            pe_bar_y = plate_y + 15.0
            pe_bar_h = 15.0
            tb_y = pe_bar_y + pe_bar_h + 18.0
            tb_h = 45.0
            bottom_duct_y = tb_y + tb_h + 12.0
            zone_branches_bottom = bottom_duct_y + duct_w + 10.0
            zone_branches_top = inc_y - duct_w - 18.0

        avail_branch_h = max(100.0, zone_branches_top - zone_branches_bottom)

        # -------------------------------------------------------------
        # KHỞI TẠO CÁC COMPONENT CỐ ĐỊNH KẾT CẤU (CABINET & BUSBAR)
        # -------------------------------------------------------------
        duct_svg_v = PhysicalLayoutEngine.generate_cable_duct_svg(width=duct_w, height=plate_h - 10, is_vertical=True)

        components.append({
            "tag": "DUCT_L",
            "type": "CABLE_DUCT",
            "mounting": MountingType.CABINET_MOUNTED,
            "function": ElectricalFunction.CONTROL_AUXILIARY,
            "x": plate_x + 4,
            "y": plate_y + 5,
            "z": plate_z,
            "width": duct_w,
            "height": plate_h - 10,
            "depth": 60.0,
            "orientation": 0,
            "catalog_id": "duct_40x60",
            "svg_symbol": "duct_40x60",
            "svg_content": duct_svg_v,
            "dimensions": {"w": duct_w, "h": plate_h - 10, "d": 60.0}
        })
        components.append({
            "tag": "DUCT_R",
            "type": "CABLE_DUCT",
            "mounting": MountingType.CABINET_MOUNTED,
            "function": ElectricalFunction.CONTROL_AUXILIARY,
            "x": plate_x + plate_w - duct_w - 4,
            "y": plate_y + 5,
            "z": plate_z,
            "width": duct_w,
            "height": plate_h - 10,
            "depth": 60.0,
            "orientation": 0,
            "catalog_id": "duct_40x60",
            "svg_symbol": "duct_40x60",
            "svg_content": duct_svg_v,
            "dimensions": {"w": duct_w, "h": plate_h - 10, "d": 60.0}
        })

        # Thanh đồng tiếp địa an toàn PE ở đáy
        pe_svg = PhysicalLayoutEngine.generate_busbar_svg(width=usable_w, height=pe_bar_h, phase="PE", label="PE (EARTH)")
        components.append({
            "tag": "PE",
            "type": "EARTH_BAR",
            "mounting": MountingType.BUSBAR_MOUNTED,
            "function": ElectricalFunction.EARTHING,
            "x": work_x1,
            "y": pe_bar_y,
            "z": plate_z + 10,
            "width": usable_w,
            "height": pe_bar_h,
            "depth": 10.0,
            "orientation": 0,
            "circuit": "He thong tiep dia an toan",
            "connected_load": "Vo tu & Thiet bi",
            "sku": f"Cu {int(inc_a / 4)}mm2 PE",
            "catalog_id": "bb_20x2_0_PE",
            "svg_symbol": "bb_20x2_0_PE",
            "svg_content": pe_svg,
            "dimensions": {"w": usable_w, "h": pe_bar_h, "d": 10.0},
            "bom_stt": 3
        })

        # Giàn thanh cái đồng chính R-S-T-N (Main Busbars)
        if need_busbar:
            for b_idx, phase_name in enumerate(["R", "S", "T", "N"]):
                b_y = busbar_y + 90.0 - b_idx * 26.0
                b_svg = PhysicalLayoutEngine.generate_busbar_svg(width=usable_w + 20, height=12.0, phase=phase_name, label=f"PHA {phase_name}")
                components.append({
                    "tag": f"BUSBAR_{phase_name}",
                    "type": "BUSBAR",
                    "mounting": MountingType.BUSBAR_MOUNTED,
                    "function": ElectricalFunction.MAIN_BUSBAR,
                    "x": work_x1 - 10,
                    "y": b_y,
                    "z": plate_z + 30,
                    "width": usable_w + 20,
                    "height": 12.0,
                    "depth": 6.0,
                    "orientation": 0,
                    "circuit": f"Pha {phase_name}",
                    "connected_load": "Toan bo cac nhanh",
                    "upstream_device": "QF1" if inc_a < 1000 else "TBA",
                    "sku": f"Cu {int(inc_a / 2)}mm2 (Dong do 99.9%)",
                    "catalog_id": f"bb_30x4_0_{phase_name}",
                    "svg_symbol": f"bb_30x4_0_{phase_name}",
                    "svg_content": b_svg,
                    "dimensions": {"w": usable_w + 20, "h": 12.0, "d": 6.0},
                    "bom_stt": 3
                })

        # -------------------------------------------------------------
        # BỐ TRÍ ZONE 2: INCOMER (MAIN PROTECTION)
        # -------------------------------------------------------------
        bom_counter = 1
        if incomer_dev:
            inc_tag = PhysicalLayoutEngine.extract_or_assign_tag(incomer_dev, 0, ElectricalFunction.INCOMING)
            incomer_dev["tag"] = inc_tag
            inc_comp_x = work_x1 + 10.0
            inc_comp_y = inc_y + (inc_zone_h - inc_h) / 2.0
            inc_mounting = PhysicalLayoutEngine.classify_mounting(incomer_dev)
            inc_brand = incomer_dev.get("brand") or "VN"
            inc_cat = incomer_dev.get("category", "MCCB").upper()

            inc_svg = PhysicalLayoutEngine.generate_breaker_svg(
                cat=inc_cat,
                width=inc_w,
                height=inc_h,
                tag=inc_tag,
                in_a=inc_a,
                poles=int(incomer_dev.get("poles") or 3),
                brand=inc_brand,
                sku=incomer_dev.get("part_number") or ""
            )

            components.append({
                "tag": inc_tag,
                "type": inc_cat,
                "mounting": inc_mounting,
                "function": ElectricalFunction.MAIN_PROTECTION,
                "x": inc_comp_x,
                "y": inc_comp_y,
                "z": plate_z + 15,
                "width": inc_w,
                "height": inc_h,
                "depth": inc_d,
                "orientation": 0,
                "circuit": "Nguon cap tong (Incomer TBA)",
                "connected_load": "Thanh cai chinh & he thong",
                "upstream_device": "TBA",
                "downstream_device": "MAIN_BUSBAR",
                "sku": incomer_dev.get("part_number") or f"{inc_cat}-{int(inc_a)}A",
                "brand": inc_brand,
                "catalog_id": incomer_dev.get("part_number") or f"{inc_cat.lower()}_{int(inc_a)}a",
                "svg_symbol": f"device_{str(inc_brand).lower()}_{inc_cat.lower()}",
                "svg_content": inc_svg,
                "dimensions": {"w": inc_w, "h": inc_h, "d": inc_d},
                "bom_stt": bom_counter
            })
            traceability_matrix.append({
                "tag": inc_tag,
                "equipment": f"{inc_cat} {incomer_dev.get('poles', 3)}P {int(inc_a)}A",
                "circuit": "Lộ tổng cấp nguồn TBA",
                "schematic_ref": "Incomer 3P",
                "load": "Toàn bộ phụ tải tủ điện",
                "sku": incomer_dev.get("part_number") or f"{inc_cat}-{int(inc_a)}A",
                "brand": inc_brand,
                "bom_stt": bom_counter
            })
            bom_counter += 1

        # -------------------------------------------------------------
        # BỐ TRÍ ZONE 2 (TIẾP): THIẾT BỊ ĐIỀU KHIỂN & PHỤ TRỢ (Contactor, Timer, Relay)
        # -------------------------------------------------------------
        ctrl_devs = [
            d for d in devices
            if any(k in str(d.get("category", "")).upper() or k in str(d.get("name", "")).upper() for k in ["CONTACTOR", "TIMER", "RELAY", "FUSE"])
            and d != incomer_dev
        ]
        curr_ctrl_x = work_x1 + inc_w + 25.0
        unplaced_controls = []
        for c_idx, cd in enumerate(ctrl_devs):
            cw, ch, cd_depth = PhysicalLayoutEngine.get_component_dimensions(cd)
            if curr_ctrl_x + cw > work_x2:
                unplaced_controls.extend(ctrl_devs[c_idx:])
                break
            c_tag = PhysicalLayoutEngine.extract_or_assign_tag(cd, c_idx, ElectricalFunction.CONTROL_AUXILIARY)
            cd["tag"] = c_tag
            c_y = inc_y + (inc_zone_h - ch) / 2.0
            c_cat = cd.get("category", "CONTROL").upper()
            c_brand = cd.get("brand") or "VN"

            c_svg = PhysicalLayoutEngine.generate_breaker_svg(
                cat=c_cat,
                width=cw,
                height=ch,
                tag=c_tag,
                in_a=float(cd.get("in_a") or 25),
                poles=int(cd.get("poles") or 3),
                brand=c_brand,
                sku=cd.get("part_number") or ""
            )

            components.append({
                "tag": c_tag,
                "type": c_cat,
                "mounting": MountingType.DIN_RAIL_MOUNTED,
                "function": ElectricalFunction.CONTROL_AUXILIARY,
                "x": curr_ctrl_x,
                "y": c_y,
                "z": plate_z + 15,
                "width": cw,
                "height": ch,
                "depth": cd_depth,
                "orientation": 0,
                "circuit": "Mach dieu khien tu dong",
                "connected_load": cd.get("name", "Dieu khien"),
                "upstream_device": inc_tag if incomer_dev else "QF1",
                "sku": cd.get("part_number") or cd.get("name"),
                "brand": c_brand,
                "catalog_id": cd.get("part_number") or f"{c_cat.lower()}_{c_tag.lower()}",
                "svg_symbol": f"device_{str(c_brand).lower()}_{c_cat.lower()}",
                "svg_content": c_svg,
                "dimensions": {"w": cw, "h": ch, "d": cd_depth},
                "bom_stt": bom_counter
            })
            traceability_matrix.append({
                "tag": c_tag,
                "equipment": cd.get("name"),
                "circuit": "Mạch điều khiển & liên động",
                "schematic_ref": cd.get("name"),
                "load": cd.get("notes") or "Điều khiển",
                "sku": cd.get("part_number") or cd.get("name"),
                "brand": c_brand,
                "bom_stt": bom_counter
            })
            bom_counter += 1
            curr_ctrl_x += cw + 12.0

        # -------------------------------------------------------------
        # BỐ TRÍ ZONE 3: CÁC LỘ NHÁNH PHÂN PHỐI (OUTGOING PROTECTION)
        # -------------------------------------------------------------
        branch_devs = [
            d for d in devices
            if d != incomer_dev and d not in ctrl_devs and
            PhysicalLayoutEngine.classify_mounting(d) in [MountingType.DIN_RAIL_MOUNTED, MountingType.MOUNTING_PLATE_MOUNTED]
        ]

        # Phân loại nhóm thiết bị nhánh: MCCB khối lớn vs MCB/RCBO module ray DIN
        mccb_devs = [
            d for d in branch_devs
            if str(d.get("category", "")).upper() in ["MCCB", "ACB", "ELCB"] or float(d.get("in_a") or 0) >= 100.0
        ]
        mcb_devs = [d for d in branch_devs if d not in mccb_devs]

        # Xếp các thiết bị theo hàng ngang (Row Bin Packing)
        rows: List[Dict[str, Any]] = []

        def pack_devices_into_rows(dev_list: List[Dict[str, Any]], row_type: str):
            if not dev_list:
                return
            curr_row_devs = []
            curr_w = 0.0
            for d in dev_list:
                dw, dh, dd = PhysicalLayoutEngine.get_component_dimensions(d)
                needed_w = dw + (15.0 if curr_row_devs else 0.0)
                if curr_w + needed_w > usable_w and curr_row_devs:
                    max_h = max(PhysicalLayoutEngine.get_component_dimensions(x)[1] for x in curr_row_devs)
                    rows.append({"type": row_type, "devices": curr_row_devs, "max_h": max_h})
                    curr_row_devs = [d]
                    curr_w = dw
                else:
                    curr_row_devs.append(d)
                    curr_w += needed_w
            if curr_row_devs:
                max_h = max(PhysicalLayoutEngine.get_component_dimensions(x)[1] for x in curr_row_devs)
                rows.append({"type": row_type, "devices": curr_row_devs, "max_h": max_h})

        pack_devices_into_rows(mccb_devs, "MCCB_ROW")
        pack_devices_into_rows(mcb_devs, "DIN_RAIL_ROW")

        # Tính toán phân bố cao độ Y an toàn, tuyệt đối không va chạm
        total_row_h = sum(r['max_h'] for r in rows)
        n_rows = len(rows)
        free_h = avail_branch_h - total_row_h
        row_gap = max(20.0, min(55.0, free_h / (n_rows + 1) if n_rows > 0 else 30.0))

        din_svg = PhysicalLayoutEngine.generate_din_rail_svg(width=usable_w, height=15.0)

        curr_top_y = zone_branches_top - row_gap
        for t_idx, r_data in enumerate(rows):
            r_h = r_data['max_h']
            tier_center_y = curr_top_y - r_h / 2.0
            r_type = r_data['type']

            components.append({
                "tag": f"DIN_RAIL_{t_idx + 1}",
                "type": "DIN_RAIL",
                "mounting": MountingType.CABINET_MOUNTED,
                "function": ElectricalFunction.CONTROL_AUXILIARY,
                "x": work_x1,
                "y": tier_center_y - 7.5,
                "z": plate_z,
                "width": usable_w,
                "height": 15.0,
                "depth": 7.5,
                "orientation": 0,
                "catalog_id": "din_35_400",
                "svg_symbol": "din_35_400",
                "svg_content": din_svg,
                "dimensions": {"w": usable_w, "h": 35.0, "d": 7.5}
            })

            curr_rx = work_x1 + 15.0
            for b_idx, bd in enumerate(r_data['devices']):
                bw, bh, bd_depth = PhysicalLayoutEngine.get_component_dimensions(bd)
                b_tag = PhysicalLayoutEngine.extract_or_assign_tag(bd, b_idx, ElectricalFunction.OUTGOING_PROTECTION)
                bd["tag"] = b_tag
                b_y = tier_center_y - bh / 2.0
                b_cat = bd.get("category", "MCB").upper()
                b_brand = bd.get("brand") or "VN"

                b_svg = PhysicalLayoutEngine.generate_breaker_svg(
                    cat=b_cat,
                    width=bw,
                    height=bh,
                    tag=b_tag,
                    in_a=float(bd.get("in_a") or 16),
                    poles=int(bd.get("poles") or 1),
                    brand=b_brand,
                    sku=bd.get("part_number") or ""
                )

                components.append({
                    "tag": b_tag,
                    "type": b_cat,
                    "mounting": MountingType.DIN_RAIL_MOUNTED if r_type == "DIN_RAIL_ROW" else MountingType.MOUNTING_PLATE_MOUNTED,
                    "function": ElectricalFunction.OUTGOING_PROTECTION,
                    "x": curr_rx,
                    "y": b_y,
                    "z": plate_z + 15,
                    "width": bw,
                    "height": bh,
                    "depth": bd_depth,
                    "orientation": 0,
                    "circuit": f"Lo nhanh {b_tag}",
                    "connected_load": bd.get("notes") or bd.get("name") or "Tai tieu thu",
                    "upstream_device": "MAIN_BUSBAR" if need_busbar else (incomer_dev.get("tag") if incomer_dev else "QF1"),
                    "downstream_device": f"TERMINAL_{b_tag}",
                    "sku": bd.get("part_number") or f"{b_cat}-{bd.get('spec')}",
                    "brand": b_brand,
                    "catalog_id": bd.get("part_number") or f"{b_cat.lower()}_{b_tag.lower()}",
                    "svg_symbol": f"device_{str(b_brand).lower()}_{b_cat.lower()}",
                    "svg_content": b_svg,
                    "dimensions": {"w": bw, "h": bh, "d": bd_depth},
                    "bom_stt": bom_counter
                })
                traceability_matrix.append({
                    "tag": b_tag,
                    "equipment": f"{b_cat} {bd.get('spec')}",
                    "circuit": f"Xuất tuyến lộ nhánh {b_tag}",
                    "schematic_ref": bd.get("name") or b_tag,
                    "load": bd.get("notes") or "Phụ tải tiêu thụ",
                    "sku": bd.get("part_number") or f"{b_cat}-{bd.get('spec')}",
                    "brand": b_brand,
                    "bom_stt": bom_counter
                })
                bom_counter += 1
                curr_rx += bw + 15.0

            curr_top_y = tier_center_y - r_h / 2.0 - row_gap

        # -------------------------------------------------------------
        # BỐ TRÍ ZONE 4: HÀNG CẦU ĐẤU RA TẢI (TERMINAL BLOCK TB1)
        # -------------------------------------------------------------
        tb_w = usable_w * 0.85
        tb_svg = (
            f'<svg viewBox="0 0 {tb_w:.1f} {tb_h:.1f}" width="{tb_w:.1f}" height="{tb_h:.1f}" xmlns="http://www.w3.org/2000/svg">'
            f'<rect x="0" y="0" width="{tb_w:.1f}" height="{tb_h:.1f}" rx="2" fill="#475569" stroke="#334155" stroke-width="1.2"/>'
            f'<line x1="0" y1="{tb_h / 2:.1f}" x2="{tb_w:.1f}" y2="{tb_h / 2:.1f}" stroke="#94a3b8" stroke-dasharray="4,2"/>'
            f'<text x="{tb_w / 2:.1f}" y="{tb_h / 2 + 4:.1f}" fill="#f8fafc" font-size="8.5" font-family="sans-serif" font-weight="bold" text-anchor="middle">DOMINO TB1 (CẦU ĐẤU RA TẢI)</text>'
            f'</svg>'
        )
        components.append({
            "tag": "TB1",
            "type": "TERMINAL_BLOCK",
            "mounting": MountingType.DIN_RAIL_MOUNTED,
            "function": ElectricalFunction.TERMINAL_CONNECTION,
            "x": work_x1,
            "y": tb_y,
            "z": plate_z + 10,
            "width": tb_w,
            "height": tb_h,
            "depth": 40.0,
            "orientation": 0,
            "circuit": "Hang kep domino dau noi cap dong luc",
            "connected_load": "Cap ha the ra phu tai cong trinh",
            "upstream_device": "Cac nhanh xuat tuyen",
            "sku": "DOMINO-DINRAIL-35MM",
            "catalog_id": "domino_din_35",
            "svg_symbol": "domino_din_35",
            "svg_content": tb_svg,
            "dimensions": {"w": tb_w, "h": tb_h, "d": 40.0},
            "bom_stt": bom_counter
        })

        # -------------------------------------------------------------
        # BỐ TRÍ THIẾT BỊ TRÊN CÁNH CỬA (DOOR_MOUNTED)
        # -------------------------------------------------------------
        door_devs = [
            d for d in devices if PhysicalLayoutEngine.classify_mounting(d) == MountingType.DOOR_MOUNTED
        ]
        door_y_start = plinth_h + H - 110.0
        curr_door_y = door_y_start

        # Đèn báo pha R-S-T
        pilot_lights = [d for d in door_devs if "LIGHT" in str(d.get("category", "")).upper() or "ĐÈN" in str(d.get("name", "")).upper()]
        if pilot_lights or need_busbar:
            light_colors = {"PHA_R": "#e53935", "PHA_S": "#f9a825", "PHA_T": "#1565c0"}
            for l_i, col_name in enumerate(["PHA_R", "PHA_S", "PHA_T"]):
                l_x = (W / 2) - 60.0 + l_i * 60.0
                p_svg = PhysicalLayoutEngine.generate_door_accessory_svg(
                    acc_type="pilot_lamp",
                    width=30.0,
                    height=30.0,
                    tag=f"HL_{col_name}",
                    label=col_name,
                    color=light_colors.get(col_name, "#e53935")
                )
                components.append({
                    "tag": f"HL_{col_name}",
                    "type": "PILOT_LIGHT",
                    "mounting": MountingType.DOOR_MOUNTED,
                    "function": ElectricalFunction.MEASUREMENT,
                    "x": l_x,
                    "y": curr_door_y,
                    "z": D,
                    "width": 30.0,
                    "height": 30.0,
                    "depth": 50.0,
                    "orientation": 0,
                    "circuit": f"Giam sat dien ap {col_name}",
                    "connected_load": "Den bao pha LED 220VAC",
                    "upstream_device": incomer_dev.get("tag") if incomer_dev else "QF1",
                    "sku": "LIGHT-LED-220VAC",
                    "brand": "VN",
                    "catalog_id": f"door_pilot_{col_name.lower()}",
                    "svg_symbol": f"door_pilot_{col_name.lower()}",
                    "svg_content": p_svg,
                    "dimensions": {"w": 30.0, "h": 30.0, "d": 50.0},
                    "bom_stt": bom_counter
                })
            curr_door_y -= 75.0

        # Đồng hồ đo đa năng / Vôn / Ampe
        meters = [d for d in door_devs if d not in pilot_lights]
        for m_i, md in enumerate(meters):
            mw, mh, md_depth = PhysicalLayoutEngine.get_component_dimensions(md)
            m_tag = PhysicalLayoutEngine.extract_or_assign_tag(md, m_i, ElectricalFunction.MEASUREMENT)
            md["tag"] = m_tag
            m_svg = PhysicalLayoutEngine.generate_door_accessory_svg(
                acc_type="digital_meter",
                width=mw,
                height=mh,
                tag=m_tag,
                label=md.get("name") or "MFM"
            )
            components.append({
                "tag": m_tag,
                "type": md.get("category", "METER").upper(),
                "mounting": MountingType.DOOR_MOUNTED,
                "function": ElectricalFunction.MEASUREMENT,
                "x": (W - mw) / 2.0,
                "y": curr_door_y - mh,
                "z": D,
                "width": mw,
                "height": mh,
                "depth": md_depth,
                "orientation": 0,
                "circuit": "Do luong dien nang",
                "connected_load": md.get("name"),
                "upstream_device": incomer_dev.get("tag") if incomer_dev else "QF1",
                "sku": md.get("part_number") or md.get("name"),
                "brand": md.get("brand") or "VN",
                "catalog_id": "door_meter_multi",
                "svg_symbol": "door_meter_multi",
                "svg_content": m_svg,
                "dimensions": {"w": mw, "h": mh, "d": md_depth},
                "bom_stt": bom_counter
            })
            curr_door_y -= mh + 35.0

        # Rút ngắn thanh cái theo đúng phạm vi các điểm đấu nối thay vì luôn chạy
        # hết bề rộng tấm gá. Chừa 35 mm mỗi đầu để thao tác đầu cốt/sứ đỡ.
        # Cách này làm bố trí thay đổi theo từng BOM và giảm lượng đồng dư.
        copper_optimization = {
            "applied": False,
            "full_width_mm": round(usable_w + 20.0, 1),
            "optimized_width_mm": 0.0,
            "saving_mm_per_bar": 0.0,
            "bar_count": 0,
        }
        main_bars = [c for c in components if c.get("type") == "BUSBAR"]
        connection_devices = [
            c for c in components
            if c.get("function") in (
                ElectricalFunction.MAIN_PROTECTION,
                ElectricalFunction.OUTGOING_PROTECTION,
            )
        ]
        if main_bars and connection_devices:
            centers = [float(c["x"]) + float(c["width"]) / 2.0 for c in connection_devices]
            bar_x1 = max(work_x1 - 10.0, min(centers) - 35.0)
            bar_x2 = min(work_x2 + 10.0, max(centers) + 35.0)
            min_support_span = min(usable_w + 20.0, 180.0)
            if bar_x2 - bar_x1 < min_support_span:
                mid_x = (bar_x1 + bar_x2) / 2.0
                bar_x1 = max(work_x1 - 10.0, mid_x - min_support_span / 2.0)
                bar_x2 = min(work_x2 + 10.0, bar_x1 + min_support_span)
                bar_x1 = bar_x2 - min_support_span

            optimized_w = max(0.0, bar_x2 - bar_x1)
            for bar in main_bars:
                bar["x"] = bar_x1
                bar["width"] = optimized_w
                bar["dimensions"]["w"] = optimized_w
                phase = str(bar.get("tag", "BUSBAR")).replace("BUSBAR_", "")
                bar["svg_content"] = PhysicalLayoutEngine.generate_busbar_svg(
                    width=optimized_w, height=float(bar["height"]), phase=phase, label=f"PHA {phase}"
                )

            full_w = usable_w + 20.0
            copper_optimization = {
                "applied": optimized_w < full_w - 0.5,
                "full_width_mm": round(full_w, 1),
                "optimized_width_mm": round(optimized_w, 1),
                "saving_mm_per_bar": round(max(0.0, full_w - optimized_w), 1),
                "bar_count": len(main_bars),
            }

        # -------------------------------------------------------------
        # BƯỚC 6 — KIỂM TRA XUNG ĐỘT HÌNH HỌC (CONFLICT VALIDATION)
        # -------------------------------------------------------------
        conflict_res = PhysicalLayoutEngine.validate_geometric_conflicts(
            components=components,
            enclosure_dims={"H": H, "W": W, "D": D}
        )
        if unplaced_controls:
            conflict_res.setdefault("conflicts", []).append({
                "type": "PLACEMENT_INCOMPLETE",
                "detail": f"{len(unplaced_controls)} thiết bị điều khiển không đủ chỗ trong vùng lắp đặt; cần tăng kích thước tủ hoặc bố trí lại.",
            })
            conflict_res["has_conflict"] = True
            conflict_res["status"] = "LAYOUT_CONFLICT"

        # -------------------------------------------------------------
        # SINH TOÀN BỘ 3 HÌNH CHIẾU SVG VECTOR CHUẨN CÔNG NGHIỆP
        # -------------------------------------------------------------
        mounting_plate_spec = {"x": plate_x, "y": plate_y, "width": plate_w, "height": plate_h, "z": plate_z}
        enclosure_spec_dict = {"H": H, "W": W, "D": D, "plinth": plinth_h}

        svg_views = {
            "internal_ga_svg": PhysicalLayoutEngine.render_full_view_svg(
                view_type="internal_ga",
                enclosure=enclosure_spec_dict,
                components=components,
                mounting_plate=mounting_plate_spec
            ),
            "front_door_svg": PhysicalLayoutEngine.render_full_view_svg(
                view_type="front_door",
                enclosure=enclosure_spec_dict,
                components=components,
                mounting_plate=mounting_plate_spec
            ),
            "inner_cover_svg": PhysicalLayoutEngine.render_full_view_svg(
                view_type="inner_cover",
                enclosure=enclosure_spec_dict,
                components=components,
                mounting_plate=mounting_plate_spec
            )
        }

        return {
            "mode": mode,
            "layout_intent": {
                "cable_entry": cable_entry,
                "busbar_arrangement": "TOP_HORIZONTAL" if need_busbar and cable_entry == "TOP" else ("BOTTOM_HORIZONTAL" if need_busbar else "NONE"),
                "incomer_position": "TOP_LEFT" if cable_entry == "TOP" else "BOTTOM_LEFT",
            },
            "enclosure": enclosure_spec_dict,
            "mounting_plate": mounting_plate_spec,
            "components": components,
            "conflict_check": conflict_res,
            "traceability_matrix": traceability_matrix,
            "total_components": len(components),
            "copper_optimization": copper_optimization,
            "svg_views": svg_views
        }

    @staticmethod
    def validate_geometric_conflicts(
        components: Optional[List[Dict[str, Any]]] = None,
        enclosure_dims: Optional[Dict[str, float]] = None,
        physical_layout: Optional[Dict[str, Any]] = None,
        cabinet_w: Optional[float] = None,
        cabinet_h: Optional[float] = None,
        cabinet_d: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        BƯỚC 6 — XUNG ĐỘT HÌNH HỌC (Geometric Conflict & Clearance Validation)
        Kiểm tra:
        - Component collision / overlap
        - Clearance cách điện và máng đi dây
        - Door clearance (chiều sâu thiết bị cửa vs plate)
        - Cabinet depth limits
        """
        if components is None:
            if physical_layout and isinstance(physical_layout, dict):
                components = physical_layout.get("components", [])
            else:
                components = []

        if enclosure_dims is None:
            enclosure_dims = {}

        conflicts = []
        H = float(cabinet_h or enclosure_dims.get("H") or enclosure_dims.get("height") or 1200.0)
        W = float(cabinet_w or enclosure_dims.get("W") or enclosure_dims.get("width") or 800.0)
        D = float(cabinet_d or enclosure_dims.get("D") or enclosure_dims.get("depth") or 400.0)

        # 1. Kiểm tra va chạm chiều sâu (Cabinet Depth vs Component Depth + Door Clearance)
        plate_z = 40.0
        for comp in components:
            tag = comp.get("tag", "")
            comp_d = comp.get("depth", 50.0)
            mounting = comp.get("mounting")

            if mounting in [MountingType.MOUNTING_PLATE_MOUNTED, MountingType.DIN_RAIL_MOUNTED]:
                total_depth_needed = plate_z + comp_d + 30.0  # Dự phòng 30mm tới mặt cover
                if total_depth_needed > D:
                    conflicts.append({
                        "type": "DEPTH_EXCEEDED",
                        "tag": tag,
                        "detail": f"Thiết bị {tag} có chiều sâu {comp_d}mm cần khoang sâu {total_depth_needed}mm vượt quá chiều sâu tủ D={D}mm."
                    })

            if mounting == MountingType.DOOR_MOUNTED:
                # Thiết bị gắn cửa nhô vào trong lòng tủ
                door_intrusion = comp_d
                # Kiểm tra khoảng hở an toàn với tấm cover/thiết bị bên trong (khoảng hở tối thiểu 40mm)
                if door_intrusion > (D - 120.0):
                    conflicts.append({
                        "type": "DOOR_CLEARANCE_CONFLICT",
                        "tag": tag,
                        "detail": f"Thiết bị cánh tủ {tag} nhô sâu {door_intrusion}mm có nguy cơ va chạm với khung panel che mặt (Cover)."
                    })

        # 2. Kiểm tra chồng lấn 2D (AABB Collision) giữa các thiết bị trên cùng mặt phẳng plate
        plate_comps = [
            c for c in components
            if c.get("mounting") in [MountingType.MOUNTING_PLATE_MOUNTED, MountingType.DIN_RAIL_MOUNTED] and "DUCT" not in c.get("tag", "")
        ]

        for i in range(len(plate_comps)):
            c1 = plate_comps[i]
            x1, y1, w1, h1 = c1["x"], c1["y"], c1["width"], c1["height"]
            for j in range(i + 1, len(plate_comps)):
                c2 = plate_comps[j]
                x2, y2, w2, h2 = c2["x"], c2["y"], c2["width"], c2["height"]

                # Kiểm tra giao nhau 2D AABB có xét khoảng hở tối thiểu (Margin 5mm)
                overlap_x = not (x1 + w1 + 5.0 <= x2 or x2 + w2 + 5.0 <= x1)
                overlap_y = not (y1 + h1 + 5.0 <= y2 or y2 + h2 + 5.0 <= y1)

                if overlap_x and overlap_y:
                    conflicts.append({
                        "type": "COMPONENT_OVERLAP",
                        "tag1": c1.get("tag"),
                        "tag2": c2.get("tag"),
                        "detail": f"Xung đột va chạm không gian giữa {c1.get('tag')} và {c2.get('tag')} trên tấm gá thiết bị."
                    })

        has_conflict = len(conflicts) > 0
        return {
            "status": "LAYOUT_CONFLICT" if has_conflict else "OK",
            "has_conflict": has_conflict,
            "conflicts": conflicts
        }
