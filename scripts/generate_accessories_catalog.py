import json
import os

busbar_sizes = [
    {"w": 1.2, "h": 15, "s": 18, "i": 27, "hole": 6},
    {"w": 2.0, "h": 15, "s": 30, "i": 45, "hole": 6},
    {"w": 2.0, "h": 20, "s": 40, "i": 60, "hole": 6},
    {"w": 3.0, "h": 20, "s": 60, "i": 90, "hole": 6},
    {"w": 3.0, "h": 25, "s": 75, "i": 112, "hole": 8},
    {"w": 4.0, "h": 25, "s": 100, "i": 150, "hole": 8},
    {"w": 3.0, "h": 30, "s": 90, "i": 135, "hole": 8},
    {"w": 4.0, "h": 30, "s": 120, "i": 180, "hole": 8},
    {"w": 5.0, "h": 30, "s": 150, "i": 225, "hole": 8},
    {"w": 4.0, "h": 40, "s": 160, "i": 240, "hole": 10},
    {"w": 5.0, "h": 40, "s": 200, "i": 300, "hole": 10},
    {"w": 5.0, "h": 50, "s": 250, "i": 375, "hole": 10},
    {"w": 6.0, "h": 50, "s": 300, "i": 450, "hole": 10},
    {"w": 8.0, "h": 50, "s": 400, "i": 600, "hole": 12},
    {"w": 10.0, "h": 50, "s": 500, "i": 750, "hole": 12},
    {"w": 5.0, "h": 60, "s": 300, "i": 450, "hole": 10},
    {"w": 6.0, "h": 60, "s": 360, "i": 540, "hole": 12},
    {"w": 8.0, "h": 60, "s": 480, "i": 720, "hole": 12},
    {"w": 10.0, "h": 60, "s": 600, "i": 900, "hole": 12},
    {"w": 8.0, "h": 80, "s": 640, "i": 960, "hole": 12},
    {"w": 10.0, "h": 80, "s": 800, "i": 1200, "hole": 14},
]

phases = [
    {"phase": "L1", "color": "#e53935", "label": "Pha L1 (Đỏ)"},
    {"phase": "L2", "color": "#f9a825", "label": "Pha L2 (Vàng)"},
    {"phase": "L3", "color": "#1565c0", "label": "Pha L3 (Xanh)"},
    {"phase": "N", "color": "#212121", "label": "Trung tính N (Đen)"},
]

busbar_items = []
for sz in busbar_sizes:
    size_label = f"{sz['h']}x{sz['w']}".replace(".", "_")
    disp_size = f"{sz['h']}×{sz['w']}"
    for p in phases:
        busbar_items.append({
            "id": f"bb_{size_label}_{p['phase']}",
            "name": f"Busbar {disp_size} {p['phase']}",
            "phase": p["phase"],
            "color": p["color"],
            "w_mm": sz["w"],
            "h_mm": sz["h"],
            "len_mm": 400,
            "section_mm2": sz["s"],
            "I_rated": sz["i"],
            "hole_dia_mm": sz["hole"],
            "hole_pitch_mm": 50,
            "note": f"I = 1.5 × {sz['s']} = {sz['i']}A"
        })

accessories = [
    {"category": "din_rail", "id": "din_35_400", "name": "DIN Rail 35×7.5 (400mm)", "color": "#9e9e9e", "w_mm": 400, "h_mm": 35, "d_mm": 7.5, "len_mm": 400, "type": "TH35-7.5"},
    {"category": "din_rail", "id": "din_35_1000", "name": "DIN Rail 35×7.5 (1000mm)", "color": "#9e9e9e", "w_mm": 1000, "h_mm": 35, "d_mm": 7.5, "len_mm": 1000, "type": "TH35-7.5"},
    {"category": "din_rail", "id": "din_35_deep_400", "name": "DIN Rail sâu 35×15 (400mm)", "color": "#9e9e9e", "w_mm": 400, "h_mm": 35, "d_mm": 15, "len_mm": 400, "type": "TH35-15"},
    {"category": "strut", "id": "strut_40x40_400", "name": "Thanh tiêu chuẩn 40×40 (400mm)", "color": "#1e3a8a", "w_mm": 40, "h_mm": 400, "d_mm": 40, "len_mm": 400, "hole_mm": 10, "pitch_mm": 25},
    {"category": "strut", "id": "strut_20x40_400", "name": "Thanh tiêu chuẩn 20×40 (400mm)", "color": "#1e3a8a", "w_mm": 40, "h_mm": 400, "d_mm": 20, "len_mm": 400, "hole_mm": 10, "pitch_mm": 25},
    {"category": "strut", "id": "strut_40x40_1000", "name": "Thanh tiêu chuẩn 40×40 (1000mm)", "color": "#1e3a8a", "w_mm": 40, "h_mm": 1000, "d_mm": 40, "len_mm": 1000, "hole_mm": 10, "pitch_mm": 25},
    {"category": "cable_duct", "id": "duct_25x25", "name": "Máng cáp 25×25 (400mm)", "color": "#bdbdbd", "w_mm": 25, "h_mm": 25, "len_mm": 400},
    {"category": "cable_duct", "id": "duct_33x33", "name": "Máng cáp 33×33 (400mm)", "color": "#bdbdbd", "w_mm": 33, "h_mm": 33, "len_mm": 400},
    {"category": "cable_duct", "id": "duct_40x40", "name": "Máng cáp 40×40 (400mm)", "color": "#bdbdbd", "w_mm": 40, "h_mm": 40, "len_mm": 400},
    {"category": "cable_duct", "id": "duct_60x40", "name": "Máng cáp 60×40 (400mm)", "color": "#bdbdbd", "w_mm": 60, "h_mm": 40, "len_mm": 400},
    {"category": "cable_duct", "id": "duct_60x60", "name": "Máng cáp 60×60 (400mm)", "color": "#bdbdbd", "w_mm": 60, "h_mm": 60, "len_mm": 400},
    {"category": "cable_duct", "id": "duct_80x60", "name": "Máng cáp 80×60 (400mm)", "color": "#bdbdbd", "w_mm": 80, "h_mm": 60, "len_mm": 400},
    {"category": "cable_duct", "id": "duct_80x80", "name": "Máng cáp 80×80 (400mm)", "color": "#bdbdbd", "w_mm": 80, "h_mm": 80, "len_mm": 400},
    {"category": "cable_duct", "id": "duct_100x60", "name": "Máng cáp 100×60 (400mm)", "color": "#bdbdbd", "w_mm": 100, "h_mm": 60, "len_mm": 400},
    {"category": "cable_duct", "id": "duct_100x100", "name": "Máng cáp 100×100 (400mm)", "color": "#bdbdbd", "w_mm": 100, "h_mm": 100, "len_mm": 400},
    {"category": "mounting_plate", "id": "mp_100x150", "name": "Tấm kê AT 100×150", "color": "#e0e0e0", "w_mm": 100, "h_mm": 150, "d_mm": 2},
    {"category": "mounting_plate", "id": "mp_150x200", "name": "Tấm kê AT 150×200", "color": "#e0e0e0", "w_mm": 150, "h_mm": 200, "d_mm": 2},
    {"category": "mounting_plate", "id": "mp_200x300", "name": "Tấm kê AT 200×300", "color": "#e0e0e0", "w_mm": 200, "h_mm": 300, "d_mm": 2},
    {"category": "mounting_plate", "id": "mp_300x400", "name": "Tấm kê AT 300×400", "color": "#e0e0e0", "w_mm": 300, "h_mm": 400, "d_mm": 2},
]

door_accessories = [
    {"id": "door_pilot_l1_red", "name": "Đèn báo pha L1 Đỏ (Ø22)", "type": "pilot_lamp", "color": "#e53935", "icon": "pilot_lamp", "cut_dia_mm": 22, "outer_dia_mm": 29, "voltage": "220VAC", "note": "Đèn LED báo pha Đỏ phi 22"},
    {"id": "door_pilot_l2_yellow", "name": "Đèn báo pha L2 Vàng (Ø22)", "type": "pilot_lamp", "color": "#fbc02d", "icon": "pilot_lamp", "cut_dia_mm": 22, "outer_dia_mm": 29, "voltage": "220VAC", "note": "Đèn LED báo pha Vàng phi 22"},
    {"id": "door_pilot_l3_blue", "name": "Đèn báo pha L3 Xanh (Ø22)", "type": "pilot_lamp", "color": "#1976d2", "icon": "pilot_lamp", "cut_dia_mm": 22, "outer_dia_mm": 29, "voltage": "220VAC", "note": "Đèn LED báo pha Xanh dương phi 22"},
    {"id": "door_btn_green", "name": "Nút nhấn Start ON Xanh (Ø22)", "type": "push_button", "color": "#2e7d32", "icon": "push_button", "cut_dia_mm": 22, "outer_dia_mm": 29, "contact": "1NO", "voltage": "600V/10A", "note": "Nút nhấn nhả có viền kim loại, tiếp điểm 1NO"},
    {"id": "door_btn_red", "name": "Nút nhấn Stop OFF Đỏ (Ø22)", "type": "push_button", "color": "#c62828", "icon": "push_button", "cut_dia_mm": 22, "outer_dia_mm": 29, "contact": "1NC", "voltage": "600V/10A", "note": "Nút nhấn nhả màu đỏ, tiếp điểm thường đóng 1NC"},
    {"id": "door_btn_estop", "name": "Nút dừng khẩn cấp E-Stop (Ø22)", "type": "estop_button", "color": "#b71c1c", "icon": "estop_button", "cut_dia_mm": 22, "outer_dia_mm": 40, "contact": "1NO+1NC", "voltage": "600V/10A", "note": "Nút nấm đỏ Ø40 xoay nhả viền vàng"},
    {"id": "door_meter_volt", "name": "Đồng hồ đo Volt kim (96×96mm)", "type": "analog_meter", "color": "#eceff1", "icon": "analog_meter", "w_mm": 96, "h_mm": 96, "cut_w_mm": 92, "cut_h_mm": 92, "scale": "0 - 500V AC", "note": "Đồng hồ chỉ thị kim gián tiếp / trực tiếp 500V"},
    {"id": "door_meter_amp", "name": "Đồng hồ đo Ampe kim (96×96mm)", "type": "analog_meter", "color": "#eceff1", "icon": "analog_meter", "w_mm": 96, "h_mm": 96, "cut_w_mm": 92, "cut_h_mm": 92, "scale": "0 - 600A / 5A", "note": "Đồng hồ kim đo dòng thứ cấp qua biến dòng CT"},
    {"id": "door_meter_multi", "name": "Đồng hồ đa năng kỹ thuật số (96×96mm)", "type": "digital_meter", "color": "#263238", "icon": "digital_meter", "w_mm": 96, "h_mm": 96, "cut_w_mm": 92, "cut_h_mm": 92, "display": "Màn hình LCD/LED 3 dòng", "voltage": "V, A, Hz, PF, kW, kVA, kWh", "note": "Đo giám sát đa chỉ tiêu kèm cổng RS485 Modbus"},
    {"id": "door_sel_volt", "name": "Chuyển mạch Volt 7 vị trí", "type": "selector_switch", "color": "#37474f", "icon": "selector_switch", "cut_dia_mm": 22, "w_mm": 48, "h_mm": 48, "positions": "OFF-RS-ST-TR-RN-SN-TN", "note": "Công tắc xoay đo điện áp dây và điện áp pha"},
    {"id": "door_sel_amp", "name": "Chuyển mạch Ampe 4 vị trí", "type": "selector_switch", "color": "#37474f", "icon": "selector_switch", "cut_dia_mm": 22, "w_mm": 48, "h_mm": 48, "positions": "OFF-R-S-T", "note": "Công tắc xoay chuyển đổi đo dòng 3 pha"},
    {"id": "door_lock_handle", "name": "Khóa tay nắm gạt tủ điện (MS818)", "type": "cabinet_lock", "color": "#78909c", "icon": "cabinet_lock", "w_mm": 32, "h_mm": 140, "cut_w_mm": 25, "cut_h_mm": 100, "note": "Khóa tay bật nẹp tủ điện công nghiệp có chìa"},
    {"id": "door_fan_filter", "name": "Quạt làm mát + Lưới lọc bụi (204×204mm)", "type": "fan_filter", "color": "#cfd8dc", "icon": "fan_filter", "w_mm": 204, "h_mm": 204, "cut_w_mm": 177, "cut_h_mm": 177, "airflow": "160 m³/h", "voltage": "220VAC 50/60Hz", "note": "Cụm quạt tản nhiệt thông gió gắn cánh tủ kèm màng lọc bụi IP54"},
]

catalog = {
    "busbar": {
        "name": "Busbar",
        "title": "Thanh đồng Busbar",
        "icon": "zap",
        "badge": len(busbar_items),
        "items": busbar_items
    },
    "accessories": {
        "name": "Phụ kiện",
        "title": "Phụ kiện cơ khí tủ điện",
        "icon": "puzzle",
        "badge": len(accessories),
        "items": accessories
    },
    "door_accessories": {
        "name": "Phụ kiện mặt cánh",
        "title": "Phụ kiện gắn mặt cánh tủ",
        "icon": "door_closed",
        "badge": len(door_accessories),
        "items": door_accessories
    }
}

output_path = os.path.join(os.path.dirname(__file__), "..", "data", "catalog_accessories.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(catalog, f, ensure_ascii=False, indent=2)

print(f"Exported successfully to {output_path}")
print(f"Busbar items count: {len(busbar_items)}")
print(f"Accessories count: {len(accessories)}")
print(f"Door accessories count: {len(door_accessories)}")
