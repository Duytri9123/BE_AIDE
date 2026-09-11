"""
Quotation Builder Service - Xây dựng báo giá theo template chuẩn
Dựa trên template báo giá có sẵn (bảng vàng) và devices extracted
"""
import logging
from typing import List, Dict, Optional
from app.core.logging_config import get_logger
from app.core.constants import QuotationRowType
from app.services.export.dynamic_grouping import DynamicGroupingEngine

logger = get_logger(__name__)


class QuotationBuilderService:
    """
    Build quotation rows từ template
    Template format: Bảng vàng với các section
    """
    
    @staticmethod
    def build_rows_from_template(
        project_name: str,
        devices: List[Dict],
        enclosure_spec: Dict,
        template: Dict
    ) -> List[Dict]:
        """
        Build quotation rows theo template structure
        
        Args:
            project_name: Tên dự án (ví dụ: "TỦ ĐIỆN TSXD-630A")
            devices: List extracted devices
            enclosure_spec: Enclosure dimensions
            template: Template structure
        
        Returns:
            List of quotation rows với format:
            {
                "id": "unique_id",
                "row_type": "panel_header|section_header|item|subtotal|total",
                "tt": "TT|*|+",
                "name": "Mô tả chi tiết",
                "ma_hang": "Mã hàng/SKU",
                "xuat_xu": "VN|LS|Schneider|...",
                "don_vi": "Cái|Tủ|Bộ|...",
                "so_luong": 1.0,
                "don_gia": 0,
                "thanh_tien": 0,
                "ghi_chu": ""
            }
        """
        rows = []
        row_id = 0
        
        from app.services.bom.enclosure_sizer import EnclosureSizerService
        from app.services.bom.busbar_calculator import BusbarCalculatorService
        from app.services.bom.accessory_inference import AccessoryInferenceService
        from app.services.bom.labor_estimation import LaborEstimationService
        from app.core.config import settings

        # Tính toán kỹ thuật vỏ tủ, thanh cái, phụ kiện và nhân công
        enc_calc = EnclosureSizerService.calculate(devices)
        enclosure_height = enclosure_spec.get("height") or enc_calc.H
        enclosure_width = enclosure_spec.get("width") or enc_calc.W
        enclosure_depth = enclosure_spec.get("depth") or enc_calc.D
        enclosure_thickness = enclosure_spec.get("thickness") or enc_calc.tole_thickness_mm
        enclosure_plinth_height = enclosure_spec.get("plinth_height", settings.ENCLOSURE_DEFAULT_PLINTH_HEIGHT)
        enc_price = enc_calc.estimated_price

        # Tính incomer rating từ thiết bị thực tế
        incomer_rating = enclosure_spec.get("incomer_rating") or max([float(d.get("in_a") or 0) for d in devices if d.get("in_a")] + [0.0])
        need_busbar = BusbarCalculatorService.needs_busbar(incomer_rating, devices)
        bus_calc = BusbarCalculatorService.calculate(incomer_rating, enc_calc.__dict__, devices) if need_busbar else None
        bus_price = bus_calc.unit_price if bus_calc else 0
        bus_mass = bus_calc.mass_Cu_kg if bus_calc else 0.0

        acc_list = AccessoryInferenceService.infer(devices, enc_calc, bus_calc)
        acc_price = sum(a.quantity * a.unit_price for a in acc_list)

        lab_calc = LaborEstimationService.estimate(enc_calc, len(devices), bus_mass)
        hourly_rate = settings.DEFAULT_LABOR_HOURLY_RATE
        labor_price = round(lab_calc.T_total_hours * hourly_rate)
        
        # 1. PANEL HEADER
        clean_name = project_name.upper().replace("DỰ ÁN", "").replace("TỦ ĐIỆN", "").strip()
        rows.append({
            "id": f"p-{row_id}",
            "row_type": QuotationRowType.PANEL_HEADER,
            "tt": "TT",
            "name": f"TỦ ĐIỆN {clean_name}",
            "ma_hang": "MÃ HÀNG",
            "xuat_xu": "XUẤT XỨ",
            "don_vi": "ĐƠN VỊ",
            "so_luong": "SỐ LƯỢNG",
            "don_gia": "ĐƠN GIÁ",
            "thanh_tien": "THÀNH TIỀN",
            "ghi_chu": "GHI CHÚ"
        })
        row_id += 1
        
        # 2. VỎ TỦ + PHỤ KIỆN Section
        rows.append({
            "id": f"s-{row_id}",
            "row_type": QuotationRowType.SECTION_HEADER,
            "tt": "*",
            "name": "Vỏ tủ + phụ kiện",
            "ma_hang": "",
            "xuat_xu": "",
            "don_vi": "",
            "so_luong": "",
            "don_gia": "",
            "thanh_tien": "",
            "ghi_chu": ""
        })
        row_id += 1
        
        # Vỏ tủ
        enclosure_description = f"""Vỏ tủ điện sơn tĩnh điện công nghiệp.
+ KT : H{enclosure_height}xW{enclosure_width}xD{enclosure_depth}xT{enclosure_thickness}mm
+ Có chân đế cao {enclosure_plinth_height}mm"""
        
        rows.append({
            "id": f"i-{row_id}",
            "row_type": QuotationRowType.ITEM,
            "tt": "+",
            "name": enclosure_description,
            "ma_hang": "Sơn tĩnh điện",
            "xuat_xu": "VN",
            "don_vi": "Cái",
            "so_luong": 1.00,
            "don_gia": enc_price,
            "thanh_tien": enc_price,
            "ghi_chu": "Kích thước tính toán theo thiết bị"
        })
        row_id += 1
        
        # Thanh cái
        if bus_calc and bus_calc.mass_Cu_kg > 0:
            rows.append({
                "id": f"i-{row_id}",
                "row_type": QuotationRowType.ITEM,
                "tt": "+",
                "name": bus_calc.spec_title,
                "ma_hang": f"{bus_calc.profile}mm",
                "xuat_xu": "VN",
                "don_vi": "Tủ",
                "so_luong": 1.00,
                "don_gia": bus_price,
                "thanh_tien": bus_price,
                "ghi_chu": f"Đồng đỏ mạ thiếc co nhiệt (~{bus_calc.mass_Cu_kg}kg)"
            })
            row_id += 1
        
        # Vật tư phụ
        rows.append({
            "id": f"i-{row_id}",
            "row_type": QuotationRowType.ITEM,
            "tt": "+",
            "name": "Vật tư phụ tủ điện (đầu cosse SC, dây điều khiển, máng cáp nhựa, sứ đỡ...)",
            "ma_hang": "Vật tư phụ",
            "xuat_xu": "VN",
            "don_vi": "Tủ",
            "so_luong": 1.00,
            "don_gia": acc_price,
            "thanh_tien": acc_price,
            "ghi_chu": "Định mức theo số cực và kích thước tủ"
        })
        row_id += 1
        
        # Nhân công
        rows.append({
            "id": f"i-{row_id}",
            "row_type": QuotationRowType.ITEM,
            "tt": "+",
            "name": f"Nhân công gia công, lắp ráp và đấu nối tủ điện ({lab_calc.T_total_hours}h)",
            "ma_hang": f"~{lab_calc.estimated_days} công",
            "xuat_xu": "VN",
            "don_vi": "Tủ",
            "so_luong": 1.00,
            "don_gia": labor_price,
            "thanh_tien": labor_price,
            "ghi_chu": "Nghiệm thu tại xưởng"
        })
        row_id += 1
        
        # 3. ĐẦU VÀO Section
        incomers = [d for d in devices if "incomer" in d.get("name", "").lower() or 
                    "tổng" in d.get("name", "").lower() or
                    d.get("section") == "Đầu vào"]
        
        if incomers:
            rows.append({
                "id": f"s-{row_id}",
                "row_type": QuotationRowType.SECTION_HEADER,
                "tt": "*",
                "name": "Đầu vào",
                "ma_hang": "",
                "xuat_xu": "",
                "don_vi": "",
                "so_luong": "",
                "don_gia": "",
                "thanh_tien": "",
                "ghi_chu": ""
            })
            row_id += 1
            incomers = DynamicGroupingEngine.merge_duplicates(incomers)
            for inc in incomers:
                price = QuotationBuilderService._estimate_price(inc)
                d_name = inc.get("name") or f"{inc.get('category', 'Thiết bị')} {inc.get('in_a', '')}A".strip()
                d_sku = inc.get("part_number") or inc.get("sku") or "-"
                d_brand = inc.get("brand") or ""
                rows.append({
                    "id": f"i-{row_id}",
                    "row_type": QuotationRowType.ITEM,
                    "tt": "+",
                    "name": d_name,
                    "ma_hang": d_sku,
                    "xuat_xu": d_brand,
                    "don_vi": "Cái",
                    "so_luong": float(inc.get("quantity", 1)),
                    "don_gia": price,
                    "thanh_tien": price * inc.get("quantity", 1),
                    "ghi_chu": inc.get("notes", "")
                })
                row_id += 1

        # 4. ĐẦU RA Section
        feeders = [d for d in devices if d not in incomers and d.get("section") == "Đầu ra"]
        
        if feeders:
            rows.append({
                "id": f"s-{row_id}",
                "row_type": QuotationRowType.SECTION_HEADER,
                "tt": "*",
                "name": "Đầu ra",
                "ma_hang": "",
                "xuat_xu": "",
                "don_vi": "",
                "so_luong": "",
                "don_gia": "",
                "thanh_tien": "",
                "ghi_chu": ""
            })
            row_id += 1
            feeders = DynamicGroupingEngine.merge_duplicates(feeders)
            for feeder in feeders:
                price = QuotationBuilderService._estimate_price(feeder)
                d_name = feeder.get("name") or f"{feeder.get('category', 'Thiết bị')} {feeder.get('in_a', '')}A".strip()
                d_sku = feeder.get("part_number") or feeder.get("sku") or "-"
                d_brand = feeder.get("brand") or ""
                rows.append({
                    "id": f"i-{row_id}",
                    "row_type": QuotationRowType.ITEM,
                    "tt": "+",
                    "name": d_name,
                    "ma_hang": d_sku,
                    "xuat_xu": d_brand,
                    "don_vi": "Cái",
                    "so_luong": float(feeder.get("quantity", 1)),
                    "don_gia": price,
                    "thanh_tien": price * feeder.get("quantity", 1),
                    "ghi_chu": feeder.get("notes", "")
                })
                row_id += 1
        
        # 5. LÀM MÁT CHO NGĂN TỦ Section
        cooling_devices = [d for d in devices if d.get("category") == "COOLING"]
        
        if cooling_devices:
            rows.append({
                "id": f"s-{row_id}",
                "row_type": QuotationRowType.SECTION_HEADER,
                "tt": "*",
                "name": "Làm mát cho ngăn tủ rack",
                "ma_hang": "",
                "xuat_xu": "",
                "don_vi": "",
                "so_luong": "",
                "don_gia": "",
                "thanh_tien": "",
                "ghi_chu": ""
            })
            row_id += 1
            
            cooling_devices = DynamicGroupingEngine.merge_duplicates(cooling_devices)
            for cooling in cooling_devices:
                price = QuotationBuilderService._estimate_price(cooling)
                rows.append({
                    "id": f"i-{row_id}",
                    "row_type": QuotationRowType.ITEM,
                    "tt": "+",
                    "name": cooling.get("name", "Quạt làm mát tủ điện"),
                    "ma_hang": cooling.get("part_number") or cooling.get("sku") or "-",
                    "xuat_xu": cooling.get("brand") or "",
                    "don_vi": "Cái",
                    "so_luong": float(cooling.get("quantity", 1)),
                    "don_gia": price,
                    "thanh_tien": price * cooling.get("quantity", 1),
                    "ghi_chu": cooling.get("notes", "")
                })
                row_id += 1
        
        # 6. TOTALS
        # Calculate totals
        subtotal = sum(
            row.get("thanh_tien", 0) 
            for row in rows 
            if row["row_type"] == QuotationRowType.ITEM
        )
        
        vat_rate = settings.DEFAULT_VAT_RATE
        vat = subtotal * vat_rate
        vat_display_pct = int(round(vat_rate * 100)) if (vat_rate * 100).is_integer() else round(vat_rate * 100, 1)
        total = subtotal + vat
        
        # Subtotal row
        rows.append({
            "id": f"t-{row_id}",
            "row_type": QuotationRowType.SUBTOTAL,
            "tt": "",
            "name": "TỔNG GIÁ TRỊ TRƯỚC THUẾ",
            "ma_hang": "",
            "xuat_xu": "",
            "don_vi": "",
            "so_luong": "",
            "don_gia": "",
            "thanh_tien": subtotal,
            "ghi_chu": ""
        })
        row_id += 1
        
        # VAT row
        rows.append({
            "id": f"t-{row_id}",
            "row_type": QuotationRowType.ITEM,
            "tt": "",
            "name": f"THUẾ GTGT {vat_display_pct}%",
            "ma_hang": "",
            "xuat_xu": "",
            "don_vi": "",
            "so_luong": "",
            "don_gia": "",
            "thanh_tien": vat,
            "ghi_chu": ""
        })
        row_id += 1
        
        # Total row
        rows.append({
            "id": f"t-{row_id}",
            "row_type": QuotationRowType.TOTAL,
            "tt": "",
            "name": "TỔNG GIÁ TRỊ SAU THUẾ",
            "ma_hang": "",
            "xuat_xu": "",
            "don_vi": "",
            "so_luong": "",
            "don_gia": "",
            "thanh_tien": total,
            "ghi_chu": ""
        })
        
        logger.info(
            f"Built {len(rows)} quotation rows",
            extra={
                "row_count": len(rows),
                "subtotal": subtotal,
                "vat": vat,
                "total": total
            }
        )
        
        return rows
    
    @staticmethod
    def _estimate_price(device: Dict) -> float:
        """Estimate device price dựa trên catalog thực tế của hệ thống"""
        # 1. Nếu đã có giá từ catalog hoặc unit_price thực tế
        if device.get("catalog_price") and float(device["catalog_price"]) > 0:
            return float(device["catalog_price"])
        if device.get("unit_price") and float(device["unit_price"]) > 0:
            return float(device["unit_price"])

        # 2. Tra cứu từ catalog engine
        from app.services.device_catalog_engine import DeviceCatalogEngine
        eng = DeviceCatalogEngine.get_instance()
        sku = device.get("part_number") or device.get("sku")
        if sku:
            exact = eng.get_by_sku(sku)
            if exact and exact.get("g") and float(exact["g"]) > 0:
                return float(exact["g"])

        cat = device.get("category", "")
        in_a = device.get("in_a")
        poles = device.get("poles")
        name = device.get("name")
        matched = eng.lookup_device_info(category=cat, in_a=in_a, poles=poles, brand=brand, part_number=sku, name=name)
        if matched and matched.get("unit_price") and float(matched["unit_price"]) > 0:
            return float(matched["unit_price"])

        # 3. Không tự ý gán giá giả ma thuật
        return 0.0
