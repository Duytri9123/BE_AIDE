"""
Enclosure CAD Generator Service - Professional Industrial Electrical Drawing
Tạo bản vẽ AutoCAD DXF kỹ thuật công nghiệp đầy đủ 4 mặt chính:
1. MẶT CÁNH NGOÀI CỦA TỦ (FRONT ELEVATION / DOOR CLOSED)
2. MẶT CÁNH TRONG / TẤM CHE COVER (INNER COVER PLATE - FORM 2B)
3. MẶT BỐ TRÍ THIẾT BỊ TRONG TỦ (INTERNAL GA - MOUNTING PLATE)
4. MẶT CẮT HÔNG / MẶT BÊN TỦ (SIDE VIEW / SECTION A-A)
5. BẢNG THỐNG KÊ VẬT TƯ & THIẾT BỊ (BOM TABLE)
"""
import os
import re
import math
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import ezdxf
from ezdxf.enums import TextEntityAlignment
from app.core.config import settings
from app.core.constants import (
    BUSBAR_REQUIRED_MIN_CURRENT_A,
    FLOOR_STANDING_HEIGHT_THRESHOLD_MM,
    DEFAULT_PANEL_CODE,
)
from app.services.cad.physical_layout_engine import PhysicalLayoutEngine, MountingType, ElectricalFunction


def clean_cad_text(text: Any) -> str:
    """Loại bỏ ký tự đặc biệt gây lỗi font CAD, giữ nguyên chữ tiếng Việt không dấu chuẩn kỹ thuật."""
    if not text:
        return ""
    text_str = str(text)
    replacements = {
        'đ': 'd', 'Đ': 'D',
        'ø': 'phi ', 'Ø': 'PHI ',
        '²': '2', '³': '3'
    }
    for k, v in replacements.items():
        text_str = text_str.replace(k, v)
    nfkd = unicodedata.normalize('NFKD', text_str)
    no_accent = "".join([c for c in nfkd if not unicodedata.combining(c)])
    cleaned = re.sub(r'[^\w\s\-\.\,\:\;\(\)\/\+\#\%\&\*\[\]]', '', no_accent)
    return cleaned.strip().upper()


def add_box(msp, p1, p2, layer="0_DEVICES", color=None):
    x1, y1 = p1
    x2, y2 = p2
    attribs = {"layer": layer}
    if color is not None:
        attribs["color"] = color
    return msp.add_lwpolyline([(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)], close=True, dxfattribs=attribs)


def add_dim_h(msp, x1, x2, y, text=None, layer="0_DIM"):
    """Vẽ đường kích thước nằm ngang với mũi tên gạch chéo 45 độ."""
    if x1 > x2:
        x1, x2 = x2, x1
    dist = int(round(x2 - x1))
    t_str = text or f"{dist}"
    msp.add_line((x1, y), (x2, y), dxfattribs={"layer": layer, "color": 1})
    msp.add_line((x1, y - 10), (x1, y + 10), dxfattribs={"layer": layer, "color": 1})
    msp.add_line((x2, y - 10), (x2, y + 10), dxfattribs={"layer": layer, "color": 1})
    msp.add_line((x1 - 4, y - 4), (x1 + 4, y + 4), dxfattribs={"layer": layer, "color": 1})
    msp.add_line((x2 - 4, y - 4), (x2 + 4, y + 4), dxfattribs={"layer": layer, "color": 1})
    msp.add_text(t_str, dxfattribs={"layer": "0_TEXT", "height": 8.0, "color": 1}).set_placement(
        ((x1 + x2) / 2, y + 5), align=TextEntityAlignment.BOTTOM_CENTER
    )


def add_dim_v(msp, x, y1, y2, text=None, layer="0_DIM"):
    """Vẽ đường kích thước thẳng đứng với mũi tên gạch chéo 45 độ."""
    if y1 > y2:
        y1, y2 = y2, y1
    dist = int(round(y2 - y1))
    t_str = text or f"{dist}"
    msp.add_line((x, y1), (x, y2), dxfattribs={"layer": layer, "color": 1})
    msp.add_line((x - 10, y1), (x + 10, y1), dxfattribs={"layer": layer, "color": 1})
    msp.add_line((x - 10, y2), (x + 10, y2), dxfattribs={"layer": layer, "color": 1})
    msp.add_line((x - 4, y1 - 4), (x + 4, y1 + 4), dxfattribs={"layer": layer, "color": 1})
    msp.add_line((x - 4, y2 - 4), (x + 4, y2 + 4), dxfattribs={"layer": layer, "color": 1})
    txt = msp.add_text(t_str, dxfattribs={"layer": "0_TEXT", "height": 8.0, "color": 1, "rotation": 90})
    txt.set_placement((x - 6, (y1 + y2) / 2), align=TextEntityAlignment.BOTTOM_CENTER)


def setup_cad_layers(doc):
    """Thiết lập các Layer chuẩn kỹ thuật cho bản vẽ AutoCAD DXF."""
    layers_def = [
        ("0_FRAME", 6, 40),       # Magenta (6) - Khung vỏ tủ
        ("0_PLATE", 4, 25),       # Cyan (4) - Tấm gá panel, ray din & cover
        ("0_DUCTS", 8, 18),       # Xám (8) - Máng cáp đi dây
        ("0_DEVICES", 7, 30),     # Trắng (7) - Khối thiết bị
        ("0_COPPER", 3, 35),      # Xanh lá (3) - Thanh tiếp địa PE / Busbar
        ("0_DOOR_ITEMS", 1, 25),  # Đỏ (1) - Đèn báo, đồng hồ, phụ kiện cánh
        ("0_DIM", 1, 15),         # Đỏ (1) - Đường kích thước
        ("0_TEXT_TITLE", 3, 30),  # Xanh lá (3) - Tiêu đề bản vẽ
        ("0_TEXT", 7, 20),        # Trắng (7) - Ghi chú thiết bị
        ("0_TABLE", 4, 25),       # Cyan (4) - Khung bảng BOM
        ("0_TABLE_HDR", 2, 30),   # Vàng (2) - Header bảng BOM
    ]
    for name, col, lw in layers_def:
        if name not in doc.layers:
            doc.layers.new(name, dxfattribs={"color": col, "lineweight": lw})


class EnclosureCadGeneratorService:
    @staticmethod
    def _get_device_dimension(dev: Dict[str, Any]) -> Tuple[float, float, float]:
        """
        Tính kích thước thực tế (width_mm, height_mm, depth_mm) của thiết bị
        từ Catalog thực tế (1.498 model chuẩn hãng) qua PhysicalLayoutEngine.
        """
        from app.services.cad.physical_layout_engine import PhysicalLayoutEngine
        return PhysicalLayoutEngine.get_component_dimensions(dev)

    @staticmethod
    def _partition_branch_rows(
        branch_devices: List[Dict[str, Any]],
        usable_rail_width: float
    ) -> List[List[Dict[str, Any]]]:
        """
        Phân chia các thiết bị nhánh vào từng hàng thanh ray DIN dựa trên chiều rộng thực tế.
        Mỗi thiết bị có khe hở đệm cách điện ~12mm.
        """
        if not branch_devices:
            return [[]]

        rows: List[List[Dict[str, Any]]] = []
        current_row: List[Dict[str, Any]] = []
        current_width = 0.0

        for dev in branch_devices:
            w, _, _ = EnclosureCadGeneratorService._get_device_dimension(dev)
            needed_w = w + 12.0

            if current_row and (current_width + needed_w > usable_rail_width):
                rows.append(current_row)
                current_row = [dev]
                current_width = needed_w
            else:
                current_row.append(dev)
                current_width += needed_w

        if current_row:
            rows.append(current_row)

        return rows

    @staticmethod
    def calculate_enclosure_specs(
        devices: List[Dict[str, Any]],
        preferred_dimensions: Optional[Tuple[float, float, float]] = None
    ) -> Dict[str, Any]:
        """
        Tính toán kích thước vỏ tủ điện thực tế dựa trên bố trí (Layout-Driven Sizing).
        Ưu tiên kích thước ghi rõ trên bản vẽ (preferred_dimensions: H, W, D) nếu có.
        """
        has_preferred = preferred_dimensions is not None and len(preferred_dimensions) >= 3 and preferred_dimensions[0] > 0
        incomer_dev = next(
            (d for d in devices if str(d.get("category", "")).upper() in ["ACB", "MCCB"] or str(d.get("section", "")).upper() in ["ĐẦU VÀO", "INCOMER", "NGUỒN CẤP"]),
            None
        )
        if not incomer_dev and devices:
            incomer_dev = max(devices, key=lambda d: float(d.get("in_a") or 0))

        incomer_a = float(incomer_dev.get("in_a") or 40) if incomer_dev else 40.0
        incomer_poles = int(incomer_dev.get("poles") or (3 if incomer_a > 63 else 2)) if incomer_dev else 2
        is_3phase = incomer_poles >= 3

        ctrl_devs = [
            d for d in devices
            if any(k in str(d.get("category", "")).upper() or k in str(d.get("name", "")).upper() for k in ["CONTACTOR", "TIMER", "RELAY", "BMS"])
        ]

        branch_units = [
            d for d in devices
            if d != incomer_dev and d not in ctrl_devs and str(d.get("category", "")).upper() not in ["LIGHT", "METER"]
        ]

        if has_preferred:
            chosen_h = float(preferred_dimensions[0])
            chosen_w = float(preferred_dimensions[1])
            chosen_d = float(preferred_dimensions[2])
        else:
            # 1. Xác định chiều rộng tối ưu W
            min_w = 500
            if incomer_a >= 1000:
                min_w = 1000
            elif incomer_a >= 400:
                min_w = 800
            elif incomer_a >= 160:
                min_w = 600

            inc_dim = EnclosureCadGeneratorService._get_device_dimension(incomer_dev) if incomer_dev else (80, 120, 75)
            ctrl_total_w = sum(EnclosureCadGeneratorService._get_device_dimension(c)[0] + 14 for c in ctrl_devs)
            row1_needed_w = inc_dim[0] + ctrl_total_w + 140

            standard_widths = [400, 500, 600, 700, 800, 1000, 1200]
            chosen_w = min_w
            for sw in standard_widths:
                if sw >= min_w and sw >= row1_needed_w:
                    chosen_w = sw
                    break
            if chosen_w < min_w:
                chosen_w = min_w

        usable_rail_w = max(250.0, chosen_w - 150.0)

        # 2. Phân chia các lộ nhánh vào các hàng ray DIN
        branch_rows = EnclosureCadGeneratorService._partition_branch_rows(branch_units, usable_rail_w)
        num_branch_rows = len(branch_rows)

        need_busbar = incomer_a >= BUSBAR_REQUIRED_MIN_CURRENT_A

        if not has_preferred:
            # Nếu số hàng ray quá nhiều (> 4) và tủ có thể mở rộng W, mở rộng W để cân đối chiều cao H
            if num_branch_rows > 4 and chosen_w < 1000:
                standard_widths = [400, 500, 600, 700, 800, 1000, 1200]
                for ww in [w for w in standard_widths if w > chosen_w]:
                    test_usable = ww - 150.0
                    test_rows = EnclosureCadGeneratorService._partition_branch_rows(branch_units, test_usable)
                    if len(test_rows) < num_branch_rows:
                        chosen_w = ww
                        usable_rail_w = test_usable
                        branch_rows = test_rows
                        num_branch_rows = len(test_rows)
                        break

            # 3. Tính chiều cao cần thiết H
            inc_dim = EnclosureCadGeneratorService._get_device_dimension(incomer_dev) if incomer_dev else (80, 120, 75)
            h_top = 220.0 if need_busbar else 130.0
            h_row1 = max(140.0, inc_dim[1] + 25.0)
            h_duct = 35.0
            h_per_branch_row = 155.0
            h_branches = num_branch_rows * h_per_branch_row
            h_bottom = 150.0

            # Dự phòng không gian 20% theo chuẩn IEC 61439
            h_raw = (h_top + h_row1 + h_duct + h_branches + h_bottom) * 1.20

            standard_heights = [600, 700, 800, 1000, 1200, 1400, 1600, 1800, 2000, 2200]
            chosen_h = standard_heights[-1]
            for sh in standard_heights:
                if sh >= h_raw:
                    chosen_h = sh
                    break

            # 4. Chiều sâu D
            if incomer_a >= 1000:
                chosen_d = 600 if chosen_h < 1800 else 800
            elif incomer_a >= 400:
                chosen_d = 350
            elif incomer_a >= 160:
                chosen_d = 250
            else:
                chosen_d = 200

        # 5. Độ dày tôn (Tole thickness) và chân đế (Plinth)
        plinth_h = settings.ENCLOSURE_DEFAULT_PLINTH_HEIGHT if chosen_h >= FLOOR_STANDING_HEIGHT_THRESHOLD_MM else 0
        if chosen_h >= 1600:
            thickness = float(settings.ENCLOSURE_DEFAULT_THICKNESS)
        elif chosen_h >= 1000:
            thickness = 1.5
        else:
            thickness = 1.2

        if need_busbar:
            phase_cu_area = int(incomer_a / 2)
            busbar_spec = f"Cu {phase_cu_area}mm2 (Phase R-S-T), N=50%, E=25%"
        else:
            busbar_spec = "Din-rail & Day dong Cadivi 1P+N (E=25%)"

        # 6. Đánh giá bố trí kỹ thuật
        total_branch_width = sum(EnclosureCadGeneratorService._get_device_dimension(b)[0] for b in branch_units)
        total_available_rail_w = max(1.0, num_branch_rows * usable_rail_w)
        filling_ratio = min(1.0, total_branch_width / total_available_rail_w)

        layout_eval = {
            "incomer_rating": int(incomer_a),
            "total_devices": len(devices),
            "branch_rows_count": num_branch_rows,
            "branch_devices_count": len(branch_units),
            "control_devices_count": len(ctrl_devs),
            "filling_ratio": round(filling_ratio, 2),
            "is_floor_standing": chosen_h >= 1200,
            "reserve_space_pct": 20,
            "dimension_rationale": (
                f"Kích thước H{chosen_h}xW{chosen_w}xD{chosen_d}mm được tính toán tối ưu từ bố trí: "
                f"1 ngăn tổng Incomer ({int(incomer_a)}A), "
                f"{num_branch_rows} hàng ray nhánh ({len(branch_units)} thiết bị), "
                f"độ điền đầy ray {int(filling_ratio * 100)}%, dự phòng 20% theo chuẩn IEC 61439."
            )
        }

        return {
            "height": chosen_h,
            "width": chosen_w,
            "depth": chosen_d,
            "thickness": thickness,
            "plinth_height": plinth_h,
            "doors": 1 if chosen_w <= 800 else 2,
            "incomer_rating": int(incomer_a),
            "poles": incomer_poles,
            "is_3phase": is_3phase,
            "busbar_spec": busbar_spec,
            "feeder_count": len(branch_units),
            "enclosure_code": f"H{chosen_h}xW{chosen_w}xD{chosen_d}xT{thickness}mm",
            "branch_rows": branch_rows,
            "layout_evaluation": layout_eval
        }

    @staticmethod
    def _draw_single_panel(
        msp,
        devices: List[Dict[str, Any]],
        panel_code: str,
        panel_name: str,
        specs: Dict[str, Any],
        x_offset: float = 0.0,
        y_offset: float = 100.0,
        draw_busbar: bool = True
    ):
        """
        Vẽ trọn vẹn 4 HÌNH CHIẾU KỸ THUẬT CỦA TỦ ĐIỆN + 1 BẢNG BOM:
        - VIEW 1: MẶT CÁNH NGOÀI CỦA TỦ (FRONT ELEVATION / DOOR CLOSED)
        - VIEW 2: MẶT CÁNH TRONG / TẤM COVER CHE MẶT (INNER COVER PLATE - FORM 2B)
        - VIEW 3: MẶT BỐ TRÍ THIẾT BỊ TRONG TỦ (INTERNAL GA - MOUNTING PLATE)
        - VIEW 4: MẶT CẮT HÔNG / MẶT BÊN TỦ (SIDE VIEW / SECTION A-A)
        - VIEW 5: BẢNG THỐNG KÊ VẬT TƯ & THIẾT BỊ (BILL OF MATERIALS - BOM TABLE)
        """
        H = specs["height"]
        W = specs["width"]
        D = specs["depth"]
        plinth_h = specs.get("plinth_height", 0)
        incomer_a = specs.get("incomer_rating", 40)
        incomer_poles = specs.get("poles", 2)
        is_3phase = specs.get("is_3phase", False)

        clean_panel_title = clean_cad_text(panel_code or f"TU_DIEN_{incomer_a}A")

        # 1. Phân loại thiết bị thực tế & Xác định kích thước chuẩn
        incomer_dev = next(
            (d for d in devices if str(d.get("category", "")).upper() in ["ACB", "MCCB"] or str(d.get("section", "")).upper() in ["ĐẦU VÀO", "INCOMER", "NGUỒN CẤP"]),
            None
        )
        if not incomer_dev and devices:
            incomer_dev = max(devices, key=lambda d: float(d.get("in_a") or 0))

        incomer_brand = incomer_dev.get("brand") if incomer_dev and incomer_dev.get("brand") else ""
        incomer_sku = incomer_dev.get("part_number") if incomer_dev and incomer_dev.get("part_number") else f"{incomer_poles}P-{incomer_a}A"
        incomer_name = incomer_dev.get("name") if incomer_dev and incomer_dev.get("name") else f"MCCB {incomer_poles}P {incomer_a}A"
        incomer_icu = int(incomer_dev.get("icu_ka") or (10 if incomer_a <= 63 else 36)) if incomer_dev else 10

        inc_dim = EnclosureCadGeneratorService._get_device_dimension(incomer_dev) if incomer_dev else (80, 120, 75)
        inc_w_actual = inc_dim[0]
        inc_h_actual = inc_dim[1]

        ctrl_devs = [
            d for d in devices
            if any(k in str(d.get("category", "")).upper() or k in str(d.get("name", "")).upper() for k in ["CONTACTOR", "TIMER", "RELAY", "BMS"])
        ]

        has_meter_device = any("METER" in str(d.get("category", "")).upper() or "DONG HO" in str(d.get("name", "")).upper() for d in devices)
        has_pilot_lights = any("LIGHT" in str(d.get("category", "")).upper() or "DEN" in str(d.get("name", "")).upper() for d in devices) or (incomer_a >= 63 and is_3phase)

        branch_units = [
            d for d in devices
            if d != incomer_dev and d not in ctrl_devs and str(d.get("category", "")).upper() not in ["LIGHT", "METER"]
        ]

        # Trích xuất hoặc gán Tag chuẩn IEC cho toàn bộ thiết bị phục vụ Traceability 2 chiều
        incomer_tag = incomer_dev.get("tag") if incomer_dev and incomer_dev.get("tag") else (
            PhysicalLayoutEngine.extract_or_assign_tag(incomer_dev, 0, ElectricalFunction.INCOMING) if incomer_dev else "QF1"
        )
        if incomer_dev:
            incomer_dev["tag"] = incomer_tag

        for c_idx, cd in enumerate(ctrl_devs):
            if not cd.get("tag"):
                cd["tag"] = PhysicalLayoutEngine.extract_or_assign_tag(cd, c_idx, ElectricalFunction.CONTROL_AUXILIARY)

        for b_idx, bd in enumerate(branch_units):
            if not bd.get("tag"):
                bd["tag"] = PhysicalLayoutEngine.extract_or_assign_tag(bd, b_idx, ElectricalFunction.OUTGOING_PROTECTION)

        usable_rail_w = max(250.0, W - 150.0)
        branch_rows = specs.get("branch_rows")
        if not branch_rows:
            branch_rows = EnclosureCadGeneratorService._partition_branch_rows(branch_units, usable_rail_w)

        BASE_Y = y_offset
        GAP = 160.0
        body_y = BASE_Y + plinth_h
        body_top = body_y + H

        # Tọa độ tấm panel gá thiết bị View 3 (Mounting Plate) để làm chuẩn quy chiếu toàn bộ các View
        margin = 32
        py1 = body_y + margin
        py2 = body_top - margin
        duct_w = 30

        # Kiểm tra sự cần thiết của hệ thống Thanh Cái Đồng Chính (Main Busbar Chamber)
        need_busbar = draw_busbar and (incomer_a >= 160 or (is_3phase and incomer_a >= 100))

        # Phân chia các Zone dọc chuẩn kỹ thuật Form 2B trên Mounting Plate:
        # Zone 1: Nóc tủ & Giàn thanh cái đồng chính (hoặc máng cáp nóc)
        if need_busbar:
            busbar_zone_h = 130.0
            busbar_top_duct_y = py2 - 25
            busbar_center_y = busbar_top_duct_y - duct_w - 50
            busbar_div_duct_y = busbar_center_y - 45
            zone2_top = busbar_div_duct_y - duct_w
        else:
            busbar_zone_h = 0.0
            busbar_center_y = 0.0
            busbar_top_duct_y = py2 - 25
            busbar_div_duct_y = 0.0
            zone2_top = busbar_top_duct_y - duct_w

        # Zone 2: Ngăn Aptomat Tổng Incomer & Khối Điều Khiển
        inc_zone_h = max(140.0, inc_h_actual + 25.0)
        inc_top = zone2_top - 15
        inc_bottom = inc_top - inc_zone_h
        inc_center_y = (inc_top + inc_bottom) / 2.0
        inc_box_y = inc_center_y - inc_h_actual / 2.0
        mid_duct_y = inc_bottom - 5
        zone3_top = mid_duct_y - duct_w - 10

        # Zone 4: Đáy tủ - Cầu đấu Domino & Thanh đồng tiếp địa PE
        pe_y = py1 + 12
        pe_h = 16
        tb_y = py1 + 42
        tb_h = 26
        bottom_duct_y = tb_y + tb_h + 10
        zone3_bottom = bottom_duct_y + duct_w + 10

        # Zone 3: Vùng phân phối các hàng ray DIN các lộ nhánh (Branch Tiers)
        avail_branch_h = zone3_top - zone3_bottom
        ideal_tier_h = 160.0
        num_tiers = max(len(branch_rows), int(round(avail_branch_h / ideal_tier_h))) if avail_branch_h > 120 else 1
        num_tiers = max(1, min(6, num_tiers))
        tier_pitch = avail_branch_h / num_tiers
        tier_centers = [zone3_top - (k + 0.5) * tier_pitch for k in range(num_tiers)]

        # =========================================================================
        # VIEW 1: MẶT CÁNH NGOÀI CỦA TỦ (FRONT ELEVATION / DOOR CLOSED)
        # =========================================================================
        v1_x = x_offset + 100
        v1_y = BASE_Y
        v1_w = W
        v1_h = H + plinth_h

        # Chân đế tủ nếu có
        if plinth_h > 0:
            add_box(msp, (v1_x, v1_y), (v1_x + v1_w, v1_y + plinth_h), layer="0_FRAME")
            msp.add_circle((v1_x + 40, v1_y + plinth_h / 2), radius=8, dxfattribs={"layer": "0_FRAME"})
            msp.add_circle((v1_x + v1_w - 40, v1_y + plinth_h / 2), radius=8, dxfattribs={"layer": "0_FRAME"})
            msp.add_text("CHAN DE 100mm", dxfattribs={"layer": "0_TEXT", "height": 8.0}).set_placement(
                (v1_x + v1_w / 2, v1_y + plinth_h / 2), align=TextEntityAlignment.MIDDLE_CENTER
            )

        add_box(msp, (v1_x, body_y), (v1_x + v1_w, body_top), layer="0_FRAME")
        add_box(msp, (v1_x + 14, body_y + 14), (v1_x + v1_w - 14, body_top - 14), layer="0_FRAME")

        # Bản lề cánh tủ bên trái
        for h_pos in [body_y + 80, body_top - 80]:
            add_box(msp, (v1_x - 8, h_pos - 20), (v1_x + 3, h_pos + 20), layer="0_FRAME")

        # Khóa tay nắm xoay bật công nghiệp bên phải
        lock_x = v1_x + v1_w - 32
        lock_y = body_y + H / 2
        add_box(msp, (lock_x - 10, lock_y - 36), (lock_x + 10, lock_y + 36), layer="0_DEVICES")
        msp.add_circle((lock_x, lock_y), radius=6, dxfattribs={"layer": "0_DEVICES"})
        msp.add_line((lock_x, lock_y - 20), (lock_x, lock_y + 20), dxfattribs={"layer": "0_DEVICES"})

        # Biển tên tủ Mica (Nameplate)
        np_w = v1_w - 140
        np_h = 36
        np_x = v1_x + (v1_w - np_w) / 2
        np_y = body_top - 60
        add_box(msp, (np_x, np_y), (np_x + np_w, np_y + np_h), layer="0_PLATE", color=4)
        msp.add_text(f"TU DIEN {clean_panel_title[:24]}", dxfattribs={"layer": "0_TEXT_TITLE", "height": 10.5, "color": 3}).set_placement(
            (v1_x + v1_w / 2, np_y + np_h / 2), align=TextEntityAlignment.MIDDLE_CENTER
        )

        curr_door_y = np_y - 20

        # Cụm Đèn Báo Pha R - S - T (Chỉ vẽ khi có đèn báo hoặc tủ lớn 3 pha)
        if has_pilot_lights:
            lamp_y = curr_door_y - 30
            lamp_colors = [1, 2, 3] if is_3phase else [1]
            lamp_labels = ["[HL1] PHA R", "[HL2] PHA S", "[HL3] PHA T"] if is_3phase else ["[HL1] NGUON"]
            lamp_count = len(lamp_colors)
            lamp_spacing = 60.0
            start_lamp_x = (v1_x + v1_w / 2) - ((lamp_count - 1) * lamp_spacing) / 2

            for l_idx, (col, lbl) in enumerate(zip(lamp_colors, lamp_labels)):
                lx = start_lamp_x + l_idx * lamp_spacing
                msp.add_circle((lx, lamp_y), radius=13, dxfattribs={"layer": "0_DOOR_ITEMS", "color": col})
                msp.add_circle((lx, lamp_y), radius=8, dxfattribs={"layer": "0_DOOR_ITEMS", "color": col})
                msp.add_text(lbl, dxfattribs={"layer": "0_TEXT", "height": 6.5, "color": col}).set_placement(
                    (lx, lamp_y - 22), align=TextEntityAlignment.MIDDLE_CENTER
                )
            curr_door_y = lamp_y - 35

        # Đồng hồ đo đa năng MFM (LCD 96x96mm) (Chỉ vẽ khi có trong BOM hoặc tủ MSB lớn >=160A 3 pha)
        should_draw_meter = has_meter_device or (incomer_a >= 160 and is_3phase and H >= 1000)
        if should_draw_meter:
            meter_y = curr_door_y - 100
            meter_size = 90
            meter_x = v1_x + (v1_w - meter_size) / 2
            add_box(msp, (meter_x, meter_y), (meter_x + meter_size, meter_y + meter_size), layer="0_DOOR_ITEMS", color=7)
            add_box(msp, (meter_x + 10, meter_y + 25), (meter_x + meter_size - 10, meter_y + meter_size - 10), layer="0_DOOR_ITEMS", color=4)
            msp.add_text("[PI1] DONG HO DA NANG MFM", dxfattribs={"layer": "0_TEXT_TITLE", "height": 6.5, "color": 3}).set_placement(
                (v1_x + v1_w / 2, meter_y + meter_size - 22), align=TextEntityAlignment.MIDDLE_CENTER
            )
            msp.add_text("V, A, Hz, CosPhi, kWh", dxfattribs={"layer": "0_TEXT", "height": 6.0}).set_placement(
                (v1_x + v1_w / 2, meter_y + meter_size - 40), align=TextEntityAlignment.MIDDLE_CENTER
            )
            msp.add_text("CLASS 0.5 - IEC", dxfattribs={"layer": "0_TEXT", "height": 5.5}).set_placement(
                (v1_x + v1_w / 2, meter_y + 10), align=TextEntityAlignment.MIDDLE_CENTER
            )

        # Biển cảnh báo an toàn điện tam giác sấm sét
        warn_y = body_y + 140
        warn_w = 110
        warn_h = 75
        warn_x = v1_x + (v1_w - warn_w) / 2
        add_box(msp, (warn_x, warn_y), (warn_x + warn_w, warn_y + warn_h), layer="0_DOOR_ITEMS", color=2)
        msp.add_text("NGUY HIEM", dxfattribs={"layer": "0_TEXT_TITLE", "height": 8.0, "color": 1}).set_placement(
            (v1_x + v1_w / 2, warn_y + warn_h - 22), align=TextEntityAlignment.MIDDLE_CENTER
        )
        msp.add_text(f"CO DIEN {'380V' if is_3phase else '220V'}", dxfattribs={"layer": "0_TEXT_TITLE", "height": 7.5, "color": 1}).set_placement(
            (v1_x + v1_w / 2, warn_y + warn_h - 40), align=TextEntityAlignment.MIDDLE_CENTER
        )
        msp.add_text("KHONG PHAN SU MIEN VAO", dxfattribs={"layer": "0_TEXT", "height": 5.5, "color": 2}).set_placement(
            (v1_x + v1_w / 2, warn_y + 14), align=TextEntityAlignment.MIDDLE_CENTER
        )

        # Chớp thoáng khí Louver nóc & đáy có lưới chắn côn trùng
        for louver_y in [body_y + 35, body_top - 35]:
            lv_w = v1_w - 180
            lv_x = v1_x + 90
            add_box(msp, (lv_x, louver_y - 12), (lv_x + lv_w, louver_y + 12), layer="0_FRAME")
            for line_offset in [-6, 0, 6]:
                msp.add_line((lv_x + 8, louver_y + line_offset), (lv_x + lv_w - 8, louver_y + line_offset), dxfattribs={"layer": "0_FRAME"})

        # Đường kích thước W & H cho View 1
        add_dim_h(msp, v1_x, v1_x + v1_w, body_top + 30, text=f"W={W}")
        add_dim_v(msp, v1_x - 35, body_y, body_top, text=f"H={H}")

        # Tiêu đề View 1
        msp.add_text(f"MAT CANH NGOAI TU (FRONT ELEVATION) - {clean_panel_title}", dxfattribs={"layer": "0_TEXT_TITLE", "height": 13.0}).set_placement(
            (v1_x + v1_w / 2, v1_y - 28), align=TextEntityAlignment.MIDDLE_CENTER
        )
        msp.add_text("CANH DONG KIN - CAP BAO VE IP54 - TY LE 1:10", dxfattribs={"layer": "0_TEXT", "height": 9.0}).set_placement(
            (v1_x + v1_w / 2, v1_y - 48), align=TextEntityAlignment.MIDDLE_CENTER
        )

        # =========================================================================
        # VIEW 2: MẶT CÁNH TRONG / TẤM COVER BẢO VỆ CHỐNG CHẠM (INNER COVER - FORM 2B)
        # =========================================================================
        v2_x = v1_x + v1_w + GAP
        v2_y = BASE_Y
        v2_w = W
        v2_h = H + plinth_h

        if plinth_h > 0:
            add_box(msp, (v2_x, v2_y), (v2_x + v2_w, v2_y + plinth_h), layer="0_FRAME")
            msp.add_text("CHAN DE 100mm", dxfattribs={"layer": "0_TEXT", "height": 8.0}).set_placement(
                (v2_x + v2_w / 2, v2_y + plinth_h / 2), align=TextEntityAlignment.MIDDLE_CENTER
            )

        # Khung viền tủ và Tấm Cover Form 2b
        add_box(msp, (v2_x, body_y), (v2_x + v2_w, body_top), layer="0_FRAME")
        cov_margin = 25
        cx1 = v2_x + cov_margin
        cy1 = body_y + cov_margin
        cx2 = v2_x + v2_w - cov_margin
        cy2 = body_top - cov_margin
        add_box(msp, (cx1, cy1), (cx2, cy2), layer="0_PLATE", color=4)
        add_box(msp, (cx1 + 8, cy1 + 8), (cx2 - 8, cy2 - 8), layer="0_PLATE", color=4)

        # 4 Khóa góc vặn 1/4 vòng (Quarter-turn fasteners)
        for fx, fy in [(cx1 + 18, cy1 + 18), (cx2 - 18, cy1 + 18), (cx1 + 18, cy2 - 18), (cx2 - 18, cy2 - 18)]:
            msp.add_circle((fx, fy), radius=6, dxfattribs={"layer": "0_PLATE", "color": 4})
            msp.add_line((fx - 4, fy), (fx + 4, fy), dxfattribs={"layer": "0_PLATE", "color": 4})
            msp.add_line((fx, fy - 4), (fx, fy + 4), dxfattribs={"layer": "0_PLATE", "color": 4})

        # 2 Tay nắm nhấc tấm cover bên hông
        for hand_y in [(cy1 + cy2) / 2 - 60, (cy1 + cy2) / 2 + 60]:
            add_box(msp, (cx1 + 14, hand_y - 12), (cx1 + 24, hand_y + 12), layer="0_DEVICES")
            add_box(msp, (cx2 - 24, hand_y - 12), (cx2 - 14, hand_y + 12), layer="0_DEVICES")

        # Khe khoét cần gạt Aptomat Tổng Incomer (ĐỒNG BỘ 100% CAO ĐỘ VỚI VIEW 3)
        inc_slot_w = min(v2_w - 180, inc_w_actual + 30)
        inc_slot_h = min(110.0, max(70.0, inc_h_actual * 0.45 + 15))
        inc_slot_x = v2_x + (v2_w - inc_slot_w) / 2
        inc_slot_y = inc_center_y - inc_slot_h / 2

        add_box(msp, (inc_slot_x, inc_slot_y), (inc_slot_x + inc_slot_w, inc_slot_y + inc_slot_h), layer="0_DEVICES")
        # Tay gạt Aptomat Incomer
        msp.add_circle((inc_slot_x + inc_slot_w / 2, inc_center_y), radius=12, dxfattribs={"layer": "0_DEVICES"})
        msp.add_text(f"[{incomer_tag}] INCOMER {incomer_a}A", dxfattribs={"layer": "0_TEXT_TITLE", "height": 7.5, "color": 3}).set_placement(
            (inc_slot_x + inc_slot_w / 2, inc_slot_y + inc_slot_h + 10), align=TextEntityAlignment.MIDDLE_CENTER
        )
        msp.add_text(f"MCCB {incomer_poles}P - Icu {incomer_icu}kA", dxfattribs={"layer": "0_TEXT", "height": 6.5}).set_placement(
            (inc_slot_x + inc_slot_w / 2, inc_slot_y - 12), align=TextEntityAlignment.MIDDLE_CENTER
        )

        # Khe khoét các hàng ray DIN (ĐỒNG BỘ 100% CAO ĐỘ TIER_CENTERS VỚI VIEW 3)
        rail_slot_w = v2_w - 150
        rail_slot_h = 55.0
        rail_slot_x = v2_x + 75

        global_dev_counter = 1
        for k_idx, c_y in enumerate(tier_centers):
            r_slot_y = c_y - rail_slot_h / 2.0
            add_box(msp, (rail_slot_x, r_slot_y), (rail_slot_x + rail_slot_w, r_slot_y + rail_slot_h), layer="0_DEVICES")
            slot_title = f"KHE KHOET APTOMAT NHANH - HANG {k_idx + 1}" if num_tiers > 1 else "KHE KHOET CAN GAT APTOMAT NHANH"
            msp.add_text(slot_title, dxfattribs={"layer": "0_TEXT", "height": 6.0}).set_placement(
                (v2_x + v2_w / 2, r_slot_y + rail_slot_h + 8), align=TextEntityAlignment.MIDDLE_CENTER
            )

            r_devs = branch_rows[k_idx] if k_idx < len(branch_rows) else []
            if r_devs:
                slot_unit_w = (rail_slot_w - 20) / max(4, len(r_devs))
                for s_idx, s_dev in enumerate(r_devs):
                    s_x = rail_slot_x + 10 + s_idx * slot_unit_w
                    add_box(msp, (s_x + 2, r_slot_y + 12), (s_x + slot_unit_w - 4, r_slot_y + rail_slot_h - 12), layer="0_DEVICES")
                    s_tag = s_dev.get("tag") or f"L{global_dev_counter}"
                    global_dev_counter += 1
                    msp.add_text(f"[{s_tag}]", dxfattribs={"layer": "0_TEXT_TITLE", "height": 5.5, "color": 3}).set_placement(
                        (s_x + slot_unit_w / 2, r_slot_y - 10), align=TextEntityAlignment.MIDDLE_CENTER
                    )
            else:
                msp.add_line((rail_slot_x + 15, r_slot_y + rail_slot_h / 2), (rail_slot_x + rail_slot_w - 15, r_slot_y + rail_slot_h / 2), dxfattribs={"layer": "0_DEVICES", "color": 8})
                msp.add_text("[RAY DU PHONG - NAP CHE BLANKING PLATE]", dxfattribs={"layer": "0_TEXT", "height": 6.0, "color": 8}).set_placement(
                    (v2_x + v2_w / 2, r_slot_y + rail_slot_h / 2 + 5), align=TextEntityAlignment.MIDDLE_CENTER
                )

        # Tiêu đề Form 2b trên mặt cover
        msp.add_text("TAM COVER KIM LOAI CHE MAT APTOMAT (FORM 2B)", dxfattribs={"layer": "0_TEXT_TITLE", "height": 8.0, "color": 3}).set_placement(
            (v2_x + v2_w / 2, cy1 + 45), align=TextEntityAlignment.MIDDLE_CENTER
        )
        msp.add_text("CHONG CHAM DIEN TRUC TIEP KHI THAO TAC VAN HANH", dxfattribs={"layer": "0_TEXT", "height": 6.5}).set_placement(
            (v2_x + v2_w / 2, cy1 + 25), align=TextEntityAlignment.MIDDLE_CENTER
        )

        # Tiêu đề View 2
        msp.add_text(f"MAT TAM CHE COVER FORM 2B - {clean_panel_title}", dxfattribs={"layer": "0_TEXT_TITLE", "height": 13.0}).set_placement(
            (v2_x + v2_w / 2, v2_y - 28), align=TextEntityAlignment.MIDDLE_CENTER
        )
        msp.add_text("KHOI MAT APTOMAT - AN TOAN VAN HANH - TY LE 1:10", dxfattribs={"layer": "0_TEXT", "height": 9.0}).set_placement(
            (v2_x + v2_w / 2, v2_y - 48), align=TextEntityAlignment.MIDDLE_CENTER
        )

        # =========================================================================
        # VIEW 3: MẶT BỐ TRÍ THIẾT BỊ TRONG TỦ (INTERNAL GA - MOUNTING PLATE)
        # =========================================================================
        v3_x = v2_x + v2_w + GAP
        v3_y = BASE_Y
        v3_w = W
        v3_h = H + plinth_h

        if plinth_h > 0:
            add_box(msp, (v3_x, v3_y), (v3_x + v3_w, v3_y + plinth_h), layer="0_FRAME")
            msp.add_text("CHAN DE 100mm", dxfattribs={"layer": "0_TEXT", "height": 8.0}).set_placement(
                (v3_x + v3_w / 2, v3_y + plinth_h / 2), align=TextEntityAlignment.MIDDLE_CENTER
            )

        # Thân vỏ tủ chính (Outer Frame - Magenta)
        add_box(msp, (v3_x, body_y), (v3_x + v3_w, body_top), layer="0_FRAME")
        add_box(msp, (v3_x + 12, body_y + 12), (v3_x + v3_w - 12, body_top - 12), layer="0_FRAME")

        # Tấm panel gá thiết bị bên trong (Mounting Plate - Cyan)
        px1 = v3_x + margin
        px2 = v3_x + v3_w - margin
        add_box(msp, (px1, py1), (px2, py2), layer="0_PLATE")

        # Máng cáp nhựa xẻ rãnh 2 bên sườn (Vertical Cable Ducts 30mm)
        add_box(msp, (px1 + 4, py1 + 4), (px1 + 4 + duct_w, py2 - 4), layer="0_DUCTS")
        add_box(msp, (px2 - 4 - duct_w, py1 + 4), (px2 - 4, py2 - 4), layer="0_DUCTS")

        work_x1 = px1 + duct_w + 14
        work_x2 = px2 - duct_w - 14
        work_w = work_x2 - work_x1

        # Thanh cái chỉ phủ vùng có điểm đấu nối (incomer + hàng nhánh rộng
        # nhất), có dự phòng thao tác 35 mm. Không kéo hết tấm gá nếu không cần.
        connection_span = inc_w_actual
        for row in branch_rows:
            row_span = sum(EnclosureCadGeneratorService._get_device_dimension(d)[0] + 12.0 for d in row)
            connection_span = max(connection_span, row_span)
        optimized_bar_w = min(work_w + 12.0, max(180.0, connection_span + 70.0))
        optimized_bar_x1 = work_x1 - 6.0
        optimized_bar_x2 = optimized_bar_x1 + optimized_bar_w
        copper_saved_per_bar = max(0.0, (work_w + 12.0) - optimized_bar_w)

        # Máng cáp ngang nóc tủ (Top horizontal cable duct)
        add_box(msp, (px1 + 4, busbar_top_duct_y - duct_w), (px2 - 4, busbar_top_duct_y), layer="0_DUCTS")

        # ZONE 1: GIÀN THANH CÁI ĐỒNG CHÍNH R - S - T - N (MAIN BUSBAR CHAMBER)
        if need_busbar:
            # Vẽ 4 thanh cái đồng ngang: R (Đỏ), S (Vàng), T (Xanh dương), N (Xanh lơ)
            bars = [
                (busbar_center_y + 24, "R", 1),
                (busbar_center_y + 8,  "S", 2),
                (busbar_center_y - 8,  "T", 5),
                (busbar_center_y - 24, "N", 4),
            ]
            bar_h = 10.0
            for by, b_lbl, b_col in bars:
                add_box(msp, (optimized_bar_x1, by - bar_h / 2), (optimized_bar_x2, by + bar_h / 2), layer="0_COPPER", color=b_col)
                msp.add_text(f"[BUSBAR_{b_lbl}] THANH CAI PHA {b_lbl}", dxfattribs={"layer": "0_TEXT", "height": 5.5, "color": b_col}).set_placement(
                    (optimized_bar_x1 + 6, by), align=TextEntityAlignment.MIDDLE_LEFT
                )
            # Sứ đỡ quả bàng cách điện SM đỡ thanh cái (Insulators)
            support_count = 2 if optimized_bar_w < 350 else 3
            for s_idx in range(support_count):
                ins_x = optimized_bar_x1 + optimized_bar_w * (s_idx + 1) / (support_count + 1)
                add_box(msp, (ins_x - 8, busbar_center_y - 32), (ins_x + 8, busbar_center_y + 32), layer="0_PLATE", color=8)
                msp.add_text("SM", dxfattribs={"layer": "0_TEXT", "height": 4.5, "color": 8}).set_placement(
                    (ins_x, busbar_center_y), align=TextEntityAlignment.MIDDLE_CENTER
                )
            msp.add_text(
                f"TOI UU DONG: L={optimized_bar_w:.0f}mm | GIAM {copper_saved_per_bar:.0f}mm/THANH",
                dxfattribs={"layer": "0_COPPER", "height": 5.5, "color": 3},
            ).set_placement((optimized_bar_x1, busbar_center_y - 40), align=TextEntityAlignment.MIDDLE_LEFT)
            # Máng cáp ngang ngăn cách Busbar và Incomer
            add_box(msp, (px1 + 4, busbar_div_duct_y - duct_w), (px2 - 4, busbar_div_duct_y), layer="0_DUCTS")

        # ZONE 2: HÀNG THIẾT BỊ ĐÓNG CẮT TỔNG INCOMER & KHỐI ĐIỀU KHIỂN
        inc_x = work_x1 + 8
        add_box(msp, (inc_x, inc_box_y), (inc_x + inc_w_actual, inc_box_y + inc_h_actual), layer="0_DEVICES")

        # Thông tin Incomer kèm TAG chuẩn IEC
        msp.add_text(f"[{incomer_tag}]", dxfattribs={"layer": "0_TEXT_TITLE", "height": 8.5, "color": 3}).set_placement(
            (inc_x + inc_w_actual / 2, inc_box_y + inc_h_actual + 10), align=TextEntityAlignment.MIDDLE_CENTER
        )
        msp.add_text(f"MCCB {incomer_poles}P {incomer_a}A", dxfattribs={"layer": "0_TEXT", "height": 7.5}).set_placement(
            (inc_x + inc_w_actual / 2, inc_box_y + inc_h_actual - 20), align=TextEntityAlignment.MIDDLE_CENTER
        )
        msp.add_text(f"Icu = {incomer_icu}kA", dxfattribs={"layer": "0_TEXT", "height": 6.5}).set_placement(
            (inc_x + inc_w_actual / 2, inc_box_y + inc_h_actual - 36), align=TextEntityAlignment.MIDDLE_CENTER
        )
        # Cần gạt trung tâm Incomer
        msp.add_circle((inc_x + inc_w_actual / 2, inc_center_y), radius=14, dxfattribs={"layer": "0_DEVICES"})
        msp.add_text(f"{incomer_a}A", dxfattribs={"layer": "0_TEXT_TITLE", "height": 8.5}).set_placement(
            (inc_x + inc_w_actual / 2, inc_center_y), align=TextEntityAlignment.MIDDLE_CENTER
        )
        msp.add_text(clean_cad_text(incomer_brand)[:14], dxfattribs={"layer": "0_TEXT", "height": 6.0}).set_placement(
            (inc_x + inc_w_actual / 2, inc_box_y + 15), align=TextEntityAlignment.MIDDLE_CENTER
        )

        # Thanh đồng Dropper cấp nguồn từ Busbar xuống cọc trên Incomer (nếu có busbar)
        if need_busbar:
            term_spacing = inc_w_actual / max(3, incomer_poles + 1)
            for p_i in range(incomer_poles):
                tx = inc_x + (p_i + 1) * term_spacing
                top_term_y = inc_box_y + inc_h_actual
                drop_src_y = busbar_center_y + 24 - p_i * 16
                msp.add_line((tx, top_term_y), (tx, drop_src_y), dxfattribs={"layer": "0_COPPER", "color": p_i + 1})
                msp.add_circle((tx, top_term_y), radius=3, dxfattribs={"layer": "0_COPPER", "color": p_i + 1})

        # Các thiết bị điều khiển đi kèm đặt cùng hàng Zone 2
        curr_cx = inc_x + inc_w_actual + 18
        avail_ctrl_w = work_x2 - curr_cx - 8
        num_ctrl = min(3, len(ctrl_devs))
        ctrl_unit_w = min(68, max(50, (avail_ctrl_w - 20) / max(1, num_ctrl))) if num_ctrl > 0 else 60

        for c_idx, cd in enumerate(ctrl_devs[:3]):
            cd_tag = cd.get("tag") or f"KM{c_idx + 1}"
            cd_name = clean_cad_text(cd.get("name") or "DIEU KHIEN")
            cd_h = min(110.0, inc_h_actual)
            cd_y = inc_center_y - cd_h / 2.0
            add_box(msp, (curr_cx, cd_y), (curr_cx + ctrl_unit_w, cd_y + cd_h), layer="0_DEVICES")
            # Hiển thị TAG thiết bị điều khiển
            msp.add_text(f"[{cd_tag}]", dxfattribs={"layer": "0_TEXT_TITLE", "height": 7.0, "color": 3}).set_placement(
                (curr_cx + ctrl_unit_w / 2, cd_y + cd_h + 8), align=TextEntityAlignment.MIDDLE_CENTER
            )

            if "CONTACTOR" in cd_name or "KHOI DONG TU" in cd_name:
                msp.add_text("CONTACTOR", dxfattribs={"layer": "0_TEXT", "height": 6.5}).set_placement(
                    (curr_cx + ctrl_unit_w / 2, cd_y + cd_h - 20), align=TextEntityAlignment.MIDDLE_CENTER
                )
                msp.add_text("2P 40A [K]", dxfattribs={"layer": "0_TEXT_TITLE", "height": 7.0}).set_placement(
                    (curr_cx + ctrl_unit_w / 2, cd_y + cd_h / 2), align=TextEntityAlignment.MIDDLE_CENTER
                )
                msp.add_text("220VAC", dxfattribs={"layer": "0_TEXT", "height": 5.5}).set_placement(
                    (curr_cx + ctrl_unit_w / 2, cd_y + 16), align=TextEntityAlignment.MIDDLE_CENTER
                )
            elif "TIMER" in cd_name or "HEN GIO" in cd_name:
                msp.add_text("TIMER 24H", dxfattribs={"layer": "0_TEXT", "height": 6.5}).set_placement(
                    (curr_cx + ctrl_unit_w / 2, cd_y + cd_h - 20), align=TextEntityAlignment.MIDDLE_CENTER
                )
                msp.add_circle((curr_cx + ctrl_unit_w / 2, cd_y + cd_h / 2), radius=12, dxfattribs={"layer": "0_DEVICES"})
                msp.add_text("[T]", dxfattribs={"layer": "0_TEXT_TITLE", "height": 7.0}).set_placement(
                    (curr_cx + ctrl_unit_w / 2, cd_y + cd_h / 2), align=TextEntityAlignment.MIDDLE_CENTER
                )
                msp.add_text("AUTO/MAN", dxfattribs={"layer": "0_TEXT", "height": 5.5}).set_placement(
                    (curr_cx + ctrl_unit_w / 2, cd_y + 16), align=TextEntityAlignment.MIDDLE_CENTER
                )
            elif "BMS" in cd_name or "RELAY" in cd_name:
                msp.add_text("TIEP DIEM", dxfattribs={"layer": "0_TEXT", "height": 6.0}).set_placement(
                    (curr_cx + ctrl_unit_w / 2, cd_y + cd_h - 20), align=TextEntityAlignment.MIDDLE_CENTER
                )
                msp.add_text("BMS INTERFACE", dxfattribs={"layer": "0_TEXT_TITLE", "height": 6.5}).set_placement(
                    (curr_cx + ctrl_unit_w / 2, cd_y + cd_h / 2), align=TextEntityAlignment.MIDDLE_CENTER
                )
                msp.add_text("ON/OFF/TRIP", dxfattribs={"layer": "0_TEXT", "height": 5.5}).set_placement(
                    (curr_cx + ctrl_unit_w / 2, cd_y + 16), align=TextEntityAlignment.MIDDLE_CENTER
                )
            else:
                msp.add_text(cd_name[:10], dxfattribs={"layer": "0_TEXT", "height": 6.5}).set_placement(
                    (curr_cx + ctrl_unit_w / 2, cd_y + cd_h / 2), align=TextEntityAlignment.MIDDLE_CENTER
                )
            curr_cx += ctrl_unit_w + 14

        # Máng cáp ngang phân cách giữa Incomer và các hàng nhánh
        add_box(msp, (px1 + 4, mid_duct_y - duct_w), (px2 - 4, mid_duct_y), layer="0_DUCTS")

        # ZONE 3: CÁC HÀNG THANH RAY DIN-RAIL VÀ CÁC LỘ NHÁNH PHÂN PHỐI (TIER CENTERS CHUẨN)
        global_branch_idx = 1
        for k_idx, c_y in enumerate(tier_centers):
            # Máng cáp ngang phân cách giữa các hàng ray
            if k_idx > 0:
                duct_between_y = c_y + tier_pitch / 2.0
                add_box(msp, (px1 + 4, duct_between_y - duct_w / 2), (px2 - 4, duct_between_y + duct_w / 2), layer="0_DUCTS")

            # Thanh ray DIN tiêu chuẩn nhôm 35mm
            rail_h = 15.0
            add_box(msp, (work_x1, c_y - rail_h / 2), (work_x2, c_y + rail_h / 2), layer="0_PLATE")
            msp.add_line((work_x1, c_y), (work_x2, c_y), dxfattribs={"layer": "0_PLATE"})

            r_devs = branch_rows[k_idx] if k_idx < len(branch_rows) else []
            b_curr_x = work_x1 + 10
            mcb_h = 75.0
            mcb_y = c_y - mcb_h / 2.0

            if r_devs:
                for bd in r_devs:
                    b_cat = str(bd.get("category", "")).upper()
                    b_poles = int(bd.get("poles") or 1)
                    b_curr = int(bd.get("in_a") or 16)
                    b_name = clean_cad_text(bd.get("name") or "MCB")

                    if "FUSE" in b_cat or "CAU CHI" in b_name:
                        bw = 28.0
                        add_box(msp, (b_curr_x, mcb_y), (b_curr_x + bw, mcb_y + mcb_h), layer="0_DEVICES")
                        msp.add_line((b_curr_x + bw / 2, mcb_y + 10), (b_curr_x + bw / 2, mcb_y + mcb_h - 10), dxfattribs={"layer": "0_DEVICES"})
                        msp.add_text("FUSE", dxfattribs={"layer": "0_TEXT", "height": 5.5}).set_placement(
                            (b_curr_x + bw / 2, mcb_y + mcb_h - 16), align=TextEntityAlignment.MIDDLE_CENTER
                        )
                        msp.add_text(f"{b_curr}A", dxfattribs={"layer": "0_TEXT_TITLE", "height": 6.5}).set_placement(
                            (b_curr_x + bw / 2, mcb_y + 16), align=TextEntityAlignment.MIDDLE_CENTER
                        )
                    elif "MCCB" in b_cat:
                        bw = 75.0 if b_poles <= 3 else 100.0
                        add_box(msp, (b_curr_x, mcb_y - 15), (b_curr_x + bw, mcb_y + mcb_h + 15), layer="0_DEVICES")
                        msp.add_text(f"MCCB {b_poles}P", dxfattribs={"layer": "0_TEXT", "height": 5.5}).set_placement(
                            (b_curr_x + bw / 2, mcb_y + mcb_h), align=TextEntityAlignment.MIDDLE_CENTER
                        )
                        msp.add_text(f"{b_curr}A", dxfattribs={"layer": "0_TEXT_TITLE", "height": 7.0}).set_placement(
                            (b_curr_x + bw / 2, mcb_y + 20), align=TextEntityAlignment.MIDDLE_CENTER
                        )
                    else:
                        bw = 18.0 * max(1, b_poles) if b_poles > 2 else (36.0 if b_poles <= 1 else 54.0)
                        add_box(msp, (b_curr_x, mcb_y), (b_curr_x + bw, mcb_y + mcb_h), layer="0_DEVICES")
                        add_box(msp, (b_curr_x + 6, mcb_y + 25), (b_curr_x + bw - 6, mcb_y + 50), layer="0_DEVICES")
                        msp.add_text(f"{b_poles}P", dxfattribs={"layer": "0_TEXT", "height": 5.5}).set_placement(
                            (b_curr_x + bw / 2, mcb_y + mcb_h - 14), align=TextEntityAlignment.MIDDLE_CENTER
                        )
                        msp.add_text(f"{b_curr}A", dxfattribs={"layer": "0_TEXT_TITLE", "height": 7.0}).set_placement(
                            (b_curr_x + bw / 2, mcb_y + 14), align=TextEntityAlignment.MIDDLE_CENTER
                        )

                    b_tag = bd.get("tag") or f"QF{global_branch_idx}"
                    global_branch_idx += 1
                    msp.add_text(f"[{b_tag}]", dxfattribs={"layer": "0_TEXT_TITLE", "height": 6.5, "color": 3}).set_placement(
                        (b_curr_x + bw / 2, mcb_y - 12), align=TextEntityAlignment.MIDDLE_CENTER
                    )
                    b_curr_x += bw + 12.0

                # Phần dự phòng cuối hàng ray
                spare_w = 50.0
                if b_curr_x + spare_w <= work_x2 - 10:
                    add_box(msp, (b_curr_x, mcb_y), (b_curr_x + spare_w, mcb_y + mcb_h), layer="0_PLATE", color=8)
                    msp.add_text("DU PHONG", dxfattribs={"layer": "0_TEXT", "height": 5.0, "color": 8}).set_placement(
                        (b_curr_x + spare_w / 2, mcb_y + mcb_h / 2), align=TextEntityAlignment.MIDDLE_CENTER
                    )
            else:
                # Hàng ray DIN dự phòng lắp sẵn
                msp.add_text("[THANH RAY DIN DU PHONG - SPARE DIN-RAIL (CAP DU PHONG 20-30%)]", dxfattribs={"layer": "0_TEXT", "height": 6.5, "color": 8}).set_placement(
                    (work_x1 + work_w / 2, c_y), align=TextEntityAlignment.MIDDLE_CENTER
                )

        # Máng cáp ngang đáy tủ (Bottom horizontal duct)
        add_box(msp, (px1 + 4, bottom_duct_y - duct_w), (px2 - 4, bottom_duct_y), layer="0_DUCTS")

        # ZONE 4: CẦU ĐẤU DOMINO & THANH TIẾP ĐỊA ĐÁY TỦ
        add_box(msp, (work_x1, tb_y), (work_x2, tb_y + tb_h), layer="0_DEVICES")
        tb_step = 16
        for tx in range(int(work_x1) + tb_step, int(work_x2), tb_step):
            msp.add_line((tx, tb_y), (tx, tb_y + tb_h), dxfattribs={"layer": "0_DEVICES"})
        msp.add_text("[TB1] HANG CAU DAU DOMINO XUAT TUYEN (TERMINAL BLOCKS)", dxfattribs={"layer": "0_TEXT", "height": 7.5}).set_placement(
            (work_x1 + work_w / 2, tb_y + tb_h + 10), align=TextEntityAlignment.MIDDLE_CENTER
        )

        if draw_busbar:
            add_box(msp, (work_x1, pe_y), (work_x2, pe_y + pe_h), layer="0_COPPER", color=3)
            for pex in [work_x1 + 30, work_x1 + work_w / 2, work_x2 - 30]:
                msp.add_circle((pex, pe_y + pe_h / 2), radius=4, dxfattribs={"layer": "0_COPPER", "color": 3})
            msp.add_text("[PE] THANH DONG TIEP DIA COPPER PE (E = 25% IN)", dxfattribs={"layer": "0_COPPER", "height": 7.0, "color": 3}).set_placement(
                (work_x1 + 15, pe_y + pe_h / 2), align=TextEntityAlignment.MIDDLE_LEFT
            )
        else:
            add_box(msp, (work_x1, pe_y), (work_x2, pe_y + pe_h), layer="0_PLATE", color=8)
            msp.add_text("[CHE DO FIT-CHECK]: CHI GA THIET BI KIEM TRA DIEN TICH (KHONG VE DONG)", dxfattribs={"layer": "0_TEXT", "height": 6.5, "color": 1}).set_placement(
                (work_x1 + work_w / 2, pe_y + pe_h / 2), align=TextEntityAlignment.MIDDLE_CENTER
            )

        # Tiêu đề View 3
        msp.add_text(f"MAT BO TRI THIET BI TRONG TU (INTERNAL GA) - {clean_panel_title}", dxfattribs={"layer": "0_TEXT_TITLE", "height": 13.0}).set_placement(
            (v3_x + v3_w / 2, v3_y - 28), align=TextEntityAlignment.MIDDLE_CENTER
        )
        msp.add_text(f"KICH THUOC: H{H} x W{W} x D{D}mm (TY LE 1:10)", dxfattribs={"layer": "0_TEXT", "height": 9.0}).set_placement(
            (v3_x + v3_w / 2, v3_y - 48), align=TextEntityAlignment.MIDDLE_CENTER
        )

        # =========================================================================
        # VIEW 4: MẶT CẮT HÔNG / MẶT BÊN TỦ (SIDE VIEW / SECTION A-A)
        # =========================================================================
        v4_x = v3_x + v3_w + GAP
        v4_y = BASE_Y
        v4_w = D
        v4_h = H + plinth_h

        if plinth_h > 0:
            add_box(msp, (v4_x, v4_y), (v4_x + v4_w, v4_y + plinth_h), layer="0_FRAME")
            msp.add_text(f"DE {plinth_h}mm", dxfattribs={"layer": "0_TEXT", "height": 7.5}).set_placement(
                (v4_x + v4_w / 2, v4_y + plinth_h / 2), align=TextEntityAlignment.MIDDLE_CENTER
            )

        # Thân tủ nhìn nghiêng từ cạnh sườn (Chiều sâu D x Chiều cao H)
        add_box(msp, (v4_x, body_y), (v4_x + v4_w, body_top), layer="0_FRAME")
        add_box(msp, (v4_x + 8, body_y + 8), (v4_x + v4_w - 8, body_top - 8), layer="0_FRAME")

        # Cánh tủ trước (Front Door Thickness 20mm) bên trái
        door_thick = 20
        add_box(msp, (v4_x, body_y), (v4_x + door_thick, body_top), layer="0_FRAME")
        # Bản lề cánh tủ
        for h_y in [body_y + 80, body_top - 80]:
            add_box(msp, (v4_x - 6, h_y - 18), (v4_x + 2, h_y + 18), layer="0_FRAME")

        # Tấm panel gá thiết bị bên trong (Mounting plate nhìn nghiêng)
        # Đặt cách mặt sau khoảng 40mm
        plate_back_offset = 40
        plate_x = v4_x + v4_w - plate_back_offset
        msp.add_line((plate_x, body_y + 30), (plate_x, body_top - 30), dxfattribs={"layer": "0_PLATE", "color": 4})
        msp.add_line((plate_x - 3, body_y + 30), (plate_x - 3, body_top - 30), dxfattribs={"layer": "0_PLATE", "color": 4})

        # Bát gá chữ Z đỡ tấm panel
        for z_y in [body_y + 50, body_top - 50]:
            msp.add_line((plate_x, z_y), (v4_x + v4_w - 8, z_y), dxfattribs={"layer": "0_PLATE", "color": 4})

        # Móc cẩu nóc tủ (Lifting Eyebolt) cho tủ đứng lớn
        if H >= 1200:
            eye_cx = v4_x + v4_w / 2
            msp.add_circle((eye_cx, body_top + 16), radius=12, dxfattribs={"layer": "0_FRAME"})
            msp.add_circle((eye_cx, body_top + 16), radius=7, dxfattribs={"layer": "0_FRAME"})
            add_box(msp, (eye_cx - 8, body_top), (eye_cx + 8, body_top + 6), layer="0_FRAME")

        # Tấm luồn cáp đáy & nóc (Cable Gland Plate)
        for gland_y in [body_y + 8, body_top - 14]:
            add_box(msp, (v4_x + 25, gland_y), (v4_x + v4_w - 25, gland_y + 6), layer="0_FRAME")
            msp.add_text("GLAND PLATE", dxfattribs={"layer": "0_TEXT", "height": 5.0}).set_placement(
                (v4_x + v4_w / 2, gland_y + 3), align=TextEntityAlignment.MIDDLE_CENTER
            )

        # Chớp thoáng nhiệt Louver sườn tủ
        slv_y = body_y + H * 0.7
        slv_w = v4_w - 60
        add_box(msp, (v4_x + 30, slv_y - 25), (v4_x + 30 + slv_w, slv_y + 25), layer="0_FRAME")
        for sl_off in [-15, -5, 5, 15]:
            msp.add_line((v4_x + 35, slv_y + sl_off), (v4_x + 30 + slv_w - 5, slv_y + sl_off), dxfattribs={"layer": "0_FRAME"})
        msp.add_text("CHOP THOANG KHI", dxfattribs={"layer": "0_TEXT", "height": 5.5}).set_placement(
            (v4_x + v4_w / 2, slv_y - 35), align=TextEntityAlignment.MIDDLE_CENTER
        )

        # Thanh đồng tiếp địa PE nhìn nghiêng ở đáy tủ
        add_box(msp, (plate_x - 15, body_y + 15), (plate_x, body_y + 35), layer="0_COPPER", color=3)
        msp.add_text("PE", dxfattribs={"layer": "0_COPPER", "height": 6.5, "color": 3}).set_placement(
            (plate_x - 8, body_y + 25), align=TextEntityAlignment.MIDDLE_CENTER
        )

        # Đường kích thước D & H cho View 4
        add_dim_h(msp, v4_x, v4_x + v4_w, body_top + 30, text=f"D={D}")
        add_dim_v(msp, v4_x + v4_w + 35, body_y, body_top, text=f"H={H}")

        # Tiêu đề View 4
        msp.add_text(f"MAT CAT HONG / MAT BEN TU (SIDE VIEW / SECTION A-A)", dxfattribs={"layer": "0_TEXT_TITLE", "height": 13.0}).set_placement(
            (v4_x + v4_w / 2, v4_y - 28), align=TextEntityAlignment.MIDDLE_CENTER
        )
        msp.add_text(f"CHIEU SAU D = {D}mm - TY LE 1:10", dxfattribs={"layer": "0_TEXT", "height": 9.0}).set_placement(
            (v4_x + v4_w / 2, v4_y - 48), align=TextEntityAlignment.MIDDLE_CENTER
        )

        # =========================================================================
        # VIEW 5: MẶT HÔNG ĐỐI DIỆN (E-SIDE VIEW)
        # =========================================================================
        v5_x = v4_x + v4_w + GAP
        add_box(msp, (v5_x, body_y), (v5_x + D, body_top), layer="0_FRAME")
        add_box(msp, (v5_x + 8, body_y + 8), (v5_x + D - 8, body_top - 8), layer="0_FRAME")
        for vent_y in (body_y + H * 0.30, body_y + H * 0.70):
            for off in (-15, -5, 5, 15):
                msp.add_line((v5_x + 35, vent_y + off), (v5_x + D - 35, vent_y + off), dxfattribs={"layer": "0_FRAME"})
        add_dim_h(msp, v5_x, v5_x + D, body_top + 30, text=f"D={D}")
        add_dim_v(msp, v5_x + D + 35, body_y, body_top, text=f"H={H}")
        msp.add_text("MAT HONG DOI DIEN (E-SIDE VIEW)", dxfattribs={"layer": "0_TEXT_TITLE", "height": 13.0}).set_placement(
            (v5_x + D / 2, v4_y - 28), align=TextEntityAlignment.MIDDLE_CENTER
        )

        # =========================================================================
        # VIEW 6 & 7: MẶT NÓC VÀ MẶT ĐÁY (TOP / BOTTOM VIEW)
        # =========================================================================
        plan_y = BASE_Y - D - 150
        for plan_idx, (plan_title, cable_entry) in enumerate((("MAT NOC TU (TOP VIEW)", "CABLE ENTRY"), ("MAT DAY TU (BOTTOM VIEW)", "GLAND PLATE"))):
            plan_x = v2_x + plan_idx * (W + GAP)
            add_box(msp, (plan_x, plan_y), (plan_x + W, plan_y + D), layer="0_FRAME")
            add_box(msp, (plan_x + 12, plan_y + 12), (plan_x + W - 12, plan_y + D - 12), layer="0_FRAME")
            gp_w = max(100.0, W * 0.55)
            gp_x = plan_x + (W - gp_w) / 2.0
            add_box(msp, (gp_x, plan_y + D * 0.32), (gp_x + gp_w, plan_y + D * 0.68), layer="0_PLATE")
            msp.add_text(cable_entry, dxfattribs={"layer": "0_TEXT", "height": 7.0}).set_placement(
                (plan_x + W / 2, plan_y + D / 2), align=TextEntityAlignment.MIDDLE_CENTER
            )
            add_dim_h(msp, plan_x, plan_x + W, plan_y + D + 25, text=f"W={W}")
            add_dim_v(msp, plan_x - 30, plan_y, plan_y + D, text=f"D={D}")
            msp.add_text(plan_title, dxfattribs={"layer": "0_TEXT_TITLE", "height": 12.0}).set_placement(
                (plan_x + W / 2, plan_y - 25), align=TextEntityAlignment.MIDDLE_CENTER
            )

        # =========================================================================
        # VIEW 8: BẢNG THỐNG KÊ VẬT TƯ & THIẾT BỊ (BILL OF MATERIALS - BOM TABLE)
        # =========================================================================
        tbl_x = v5_x + D + GAP
        tbl_w = 1150
        tbl_top_y = BASE_Y + H + plinth_h

        hdr_h = 44
        hdr_y = tbl_top_y - hdr_h
        add_box(msp, (tbl_x, hdr_y), (tbl_x + tbl_w, tbl_top_y), layer="0_TABLE", color=4)
        msp.add_text("BANG THONG KE VAT TU & THIET BI TU DIEN (BILL OF MATERIALS)", dxfattribs={"layer": "0_TABLE_HDR", "height": 13.0, "color": 2}).set_placement(
            (tbl_x + tbl_w / 2, tbl_top_y - 18), align=TextEntityAlignment.MIDDLE_CENTER
        )
        msp.add_text(f"TU DIEN: {clean_panel_title} | DIEN AP: 220/380VAC | CONG SUAT IN = {incomer_a}A", dxfattribs={"layer": "0_TEXT", "height": 8.5}).set_placement(
            (tbl_x + tbl_w / 2, tbl_top_y - 34), align=TextEntityAlignment.MIDDLE_CENTER
        )

        subhdr_h = 30
        subhdr_y = hdr_y - subhdr_h
        add_box(msp, (tbl_x, subhdr_y), (tbl_x + tbl_w, hdr_y), layer="0_TABLE", color=4)

        col_widths = [45, 290, 210, 270, 55, 45, 235]
        col_headers = ["STT", "TEN THIET BI & MO TA", "MA HIEU (SKU)", "THONG SO KY THUAT", "DVT", "SL", "HANG SAN XUAT"]

        curr_x = tbl_x
        for c_idx, (cw, chdr) in enumerate(zip(col_widths, col_headers)):
            if c_idx > 0:
                msp.add_line((curr_x, subhdr_y), (curr_x, hdr_y), dxfattribs={"layer": "0_TABLE", "color": 4})
            msp.add_text(chdr, dxfattribs={"layer": "0_TABLE_HDR", "height": 8.5, "color": 2}).set_placement(
                (curr_x + cw / 2, subhdr_y + subhdr_h / 2), align=TextEntityAlignment.MIDDLE_CENTER
            )
            curr_x += cw

        # Keep the same hierarchy as the quotation: cabinet/mechanical items
        # first, then every main device immediately followed by its attached
        # accessories. This preserves the parent-child relation in the DXF BOM.
        bom_rows = [{
            "name": f"VO TU DIEN {clean_panel_title[:16]} (SON TINH DIEN)",
            "sku": specs.get("enclosure_code", f"H{H}xW{W}xD{D}"),
            "spec": f"H{H}xW{W}xD{D}mm, T={specs.get('thickness', 1.5)}mm, IP54",
            "unit": "BO",
            "qty": 1,
            "brand": "VN"
        }]
        if draw_busbar:
            bom_rows.append({
                "name": "[BUSBAR & PE] HE PHAN PHOI DONG & TIEP DIA",
                "sku": clean_cad_text(specs.get("busbar_spec", "Cu 99.9%")),
                "spec": f"Dong do 99.9% Cu (In = {incomer_a}A, E=25%)",
                "unit": "HE",
                "qty": 1,
                "brand": "CADIVI / VN"
            })
        else:
            bom_rows.append({
                "name": "[FIT-CHECK] HE PHAN PHOI NGUON",
                "sku": "DAY NOI HOAC LUOC DONG COMB BUSBAR",
                "spec": "Chua tinh toan dong (Kiem tra dien tich ga lap)",
                "unit": "TAM",
                "qty": 1,
                "brand": "VN"
            })

        bom_rows.append({
            "name": clean_cad_text(f"[{incomer_tag}] {incomer_name}"),
            "sku": clean_cad_text(incomer_sku),
            "spec": clean_cad_text(f"{incomer_poles}P - {incomer_a}A - Icu {incomer_icu}kA"),
            "unit": "BO",
            "qty": 1,
            "brand": clean_cad_text(incomer_brand)
        })

        def append_attached_accessories(parent_device):
            parent_tag = clean_cad_text(parent_device.get("tag") or parent_device.get("name") or "THIET BI")
            for accessory in parent_device.get("accompanying_accessories") or []:
                if not isinstance(accessory, dict):
                    continue
                bom_rows.append({
                    "name": clean_cad_text(f"-> [{parent_tag}] {accessory.get('name') or accessory.get('code') or 'PHU KIEN'}"),
                    "sku": clean_cad_text(accessory.get("sku") or accessory.get("code") or "---"),
                    "spec": clean_cad_text(accessory.get("spec") or "PHU KIEN DI KEM"),
                    "unit": clean_cad_text(accessory.get("unit") or "CAI"),
                    "qty": int(accessory.get("quantity") or 1),
                    "brand": clean_cad_text(accessory.get("origin") or accessory.get("brand") or "VN")
                })

        if incomer_dev:
            append_attached_accessories(incomer_dev)

        for dev in devices:
            if dev == incomer_dev:
                continue
            cat = str(dev.get("category") or "").upper()
            d_tag = dev.get("tag")
            raw_name = str(dev.get("name") or cat or "THIET BI")
            d_name = clean_cad_text(f"[{d_tag}] {raw_name}" if d_tag else raw_name)
            d_sku = clean_cad_text(dev.get("part_number") or dev.get("model") or "---")
            d_spec = clean_cad_text(dev.get("spec") or f"{dev.get('poles', 1)}P - {dev.get('in_a', '')}A")
            d_qty = int(dev.get("quantity") or 1)
            
            dev_raw_b = (dev.get("brand") or "").strip()
            if dev_raw_b and dev_raw_b.upper() not in ["---", "OEM", "KHÔNG", "CHƯA RÕ", "CHUA RO"]:
                d_brand = clean_cad_text(dev_raw_b)
            elif any(k in cat for k in ["METER", "LIGHT", "CT", "ACCESSORY", "PHU KIEN"]) or "ĐỒNG HỒ" in cat or "ĐÈN" in cat:
                d_brand = "VN"
            else:
                d_brand = clean_cad_text(incomer_brand or "VN")

            if "MCB" in cat or "RCBO" in cat:
                d_unit = "TEP"
            elif "CT" in cat:
                d_unit = "QUA"
            elif "RELAY" in cat or "METER" in cat or "LIGHT" in cat or "FUSE" in cat:
                d_unit = "CAI"
            else:
                d_unit = "BO"

            bom_rows.append({
                "name": d_name,
                "sku": d_sku,
                "spec": d_spec,
                "unit": d_unit,
                "qty": d_qty,
                "brand": d_brand
            })
            append_attached_accessories(dev)

        row_h = 28
        row_y = subhdr_y

        # Do not truncate at 16 lines. Truncation made the DXF BOM disagree with
        # the Excel quotation and silently removed later devices/accessories.
        for r_idx, row in enumerate(bom_rows):
            row_y -= row_h
            add_box(msp, (tbl_x, row_y), (tbl_x + tbl_w, row_y + row_h), layer="0_TABLE", color=4)
            col_x = tbl_x
            row_data = [
                str(r_idx + 1),
                row["name"][:38],
                row["sku"][:26],
                row["spec"][:36],
                row["unit"],
                str(row["qty"]),
                row["brand"][:24]
            ]
            for cw, val in zip(col_widths, row_data):
                msp.add_line((col_x, row_y), (col_x, row_y + row_h), dxfattribs={"layer": "0_TABLE", "color": 4})
                align = TextEntityAlignment.MIDDLE_CENTER if cw <= 60 else TextEntityAlignment.MIDDLE_LEFT
                tx = col_x + cw / 2 if cw <= 60 else col_x + 8
                txt_color = 3 if cw == col_widths[-1] else 7
                msp.add_text(val, dxfattribs={"layer": "0_TEXT", "height": 6.2, "color": txt_color}).set_placement(
                    (tx, row_y + row_h / 2), align=align
                )
                col_x += cw

        footer_y = row_y - 28
        add_box(msp, (tbl_x, footer_y), (tbl_x + tbl_w, row_y), layer="0_TABLE", color=4)
        msp.add_text(
            f"TONG CONG: {len(bom_rows)} HANG MUC THIET BI",
            dxfattribs={"layer": "0_TABLE_HDR", "height": 8.5, "color": 2}
        ).set_placement((tbl_x + tbl_w / 2, footer_y + 14), align=TextEntityAlignment.MIDDLE_CENTER)

    @staticmethod
    def generate_dxf(
        project_id: int,
        project_name: str,
        devices: List[Dict[str, Any]],
        output_dir: Optional[str] = None,
        panel_code: Optional[str] = None,
        panels: Optional[List[Dict[str, Any]]] = None,
        draw_busbar: bool = True,
        preferred_dimensions: Optional[Tuple[float, float, float]] = None
    ) -> str:
        """
        Tạo file AutoCAD DXF bản vẽ kỹ thuật hoàn chỉnh:
        - Sinh duy nhất 1 file CAD DXF chuẩn kỹ thuật cho dự án (đa tủ hoặc đơn tủ)
        - Đầy đủ 7 hình chiếu cho mỗi tủ: cánh ngoài, cover/cánh trong,
          bố trí thiết bị, hai mặt hông, mặt nóc, mặt đáy; kèm bảng BOM.
        - Tham số draw_busbar: True (vẽ đầy đủ thanh cái đồng), False (chế độ Fit-check chỉ gá thiết bị kiểm tra diện tích)
        """
        if not output_dir:
            output_dir = settings.PROJECTS_DIR
        out_folder = Path(output_dir) / str(project_id)
        out_folder.mkdir(parents=True, exist_ok=True)

        # Dọn dẹp các file DXF tự sinh cũ để đảm bảo trên đĩa chỉ có duy nhất 1 file CAD
        for old_dxf in out_folder.glob("*.dxf"):
            try:
                old_dxf.unlink()
            except Exception:
                pass

        # Trích xuất danh sách tủ thực tế
        effective_panels = []
        if panels and len(panels) > 1:
            effective_panels = panels
        else:
            # Nhóm theo panel_code từ devices nếu có nhiều tủ
            panel_map: Dict[str, List[Dict[str, Any]]] = {}
            for d in devices:
                c = d.get("panel_code") or panel_code or DEFAULT_PANEL_CODE
                if c not in panel_map:
                    panel_map[c] = []
                panel_map[c].append(d)
            if len(panel_map) > 1:
                for c, devs in panel_map.items():
                    effective_panels.append({
                        "panel_code": c,
                        "panel_name": devs[0].get("panel_name") or f"TỦ ĐIỆN {c}",
                        "devices": devs
                    })

        doc = ezdxf.new(settings.EXPORT_DXF_VERSION, setup=True)
        setup_cad_layers(doc)
        msp = doc.modelspace()

        if effective_panels:
            for p_idx, p_data in enumerate(effective_panels):
                p_devs = p_data.get("devices", [])
                p_code = p_data.get("panel_code") or f"P-{p_idx+1}"
                p_name = p_data.get("panel_name") or f"TỦ ĐIỆN {p_code}"
                p_pref = None
                if p_data.get("dim_h") and p_data.get("dim_w") and p_data.get("dim_d"):
                    p_pref = (p_data["dim_h"], p_data["dim_w"], p_data["dim_d"])
                elif preferred_dimensions:
                    p_pref = preferred_dimensions
                p_specs = EnclosureCadGeneratorService.calculate_enclosure_specs(p_devs, preferred_dimensions=p_pref)
                if p_data.get("dim_h"):
                    p_specs["height"] = p_data["dim_h"]
                if p_data.get("dim_w"):
                    p_specs["width"] = p_data["dim_w"]
                if p_data.get("dim_d"):
                    p_specs["depth"] = p_data["dim_d"]

                p_w = p_specs["width"]
                p_d = p_specs["depth"]
                span_x = 3 * p_w + 2 * p_d + 1150 + 5 * 160
                x_offset = p_idx * span_x
                EnclosureCadGeneratorService._draw_single_panel(
                    msp=msp,
                    devices=p_devs,
                    panel_code=p_code,
                    panel_name=p_name,
                    specs=p_specs,
                    x_offset=x_offset,
                    draw_busbar=draw_busbar
                )

            suffix = "" if draw_busbar else "_FitCheck"
            master_path = out_folder / f"BanVe_TongThe_{len(effective_panels)}_TuDien{suffix}.dxf"
            doc.saveas(str(master_path))
            return str(master_path)
        else:
            specs = EnclosureCadGeneratorService.calculate_enclosure_specs(devices, preferred_dimensions=preferred_dimensions)
            p_code = panel_code or "TU_DIEN"
            clean_tag = re.sub(r'[^\w\-]', '_', clean_cad_text(p_code))
            EnclosureCadGeneratorService._draw_single_panel(
                msp=msp,
                devices=devices,
                panel_code=p_code,
                panel_name=f"TỦ ĐIỆN {p_code}",
                specs=specs,
                x_offset=0.0,
                draw_busbar=draw_busbar
            )
            suffix = "" if draw_busbar else "_FitCheck"
            file_path = out_folder / f"BanVe_TuDien_{clean_tag}_{specs['incomer_rating']}A{suffix}.dxf"
            doc.saveas(str(file_path))
            return str(file_path)
