import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from app.services.export.dynamic_grouping import DynamicGroupingEngine
from app.core.config import settings

class QuotationExporterService:
    @staticmethod
    def export(
        devices: list,
        project_name: str = "Tủ Điện",
        brand_preference: str = "Theo thiết kế",
        proposals: Optional[list] = None,
        vat_percent: Optional[float] = None,
        filename_suffix: Optional[str] = None,
        manufacturer_discounts: Optional[dict] = None,
        include_technical_proposals: bool = False,
    ) -> str:
        """Xuất bảng báo giá thiết bị tủ điện chuẩn kỹ thuật ra file Excel (.xlsx)."""
        from app.services.export.quotation_names import quotation_display_rows
        devices = quotation_display_rows(devices)
        wb = Workbook()
        discounts = {}
        import math
        for brand, value in (manufacturer_discounts or {}).items():
            rate = float(value)
            if not math.isfinite(rate) or not 0 <= rate <= 100:
                raise ValueError("Chiết khấu hãng phải từ 0 đến 100%")
            discounts[str(brand).strip().casefold()] = rate
        ws = wb.active
        ws.title = "Bảng Báo Giá"
        ws.views.sheetView[0].showGridLines = True

        # Styles definition (Times New Roman)
        font_header = Font(name="Times New Roman", size=13, bold=True, color="000000")
        font_data = Font(name="Times New Roman", size=12, color="000000")
        font_data_bold = Font(name="Times New Roman", size=12, bold=True, color="000000")
        font_panel = Font(name="Times New Roman", size=12, bold=True, color="000000")
        font_section = Font(name="Times New Roman", size=12, bold=True, color="000000")
        font_grand_total = Font(name="Times New Roman", size=11, bold=True, color="000000")

        fill_header = PatternFill(start_color="FFC000", end_color="FFC000", fill_type="solid") # Gold Yellow
        fill_panel = PatternFill(start_color="92D050", end_color="92D050", fill_type="solid")
        fill_section = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
        fill_total = PatternFill(start_color="FFC000", end_color="FFC000", fill_type="solid")   # Gold Yellow

        align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
        align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)
        align_right = Alignment(horizontal="right", vertical="center")

        thin_side = Side(style="thin", color="000000")
        border_all = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

        # 1. Table Headers (Gold Yellow #FFC000)
        headers = [
            "TT",
            "MÔ TẢ CHI TIẾT",
            "MÃ HÀNG",
            "XUẤT XỨ",
            "ĐƠN VỊ",
            "SỐ LƯỢNG",
            "ĐƠN GIÁ",
            "THÀNH TIỀN",
            "GHI CHÚ",
            "GIÁ NIÊM YẾT",
            "CHIẾT KHẤU HÃNG (%)"
        ]

        header_row = 1
        for col_idx, h_text in enumerate(headers, 1):
            cell = ws.cell(row=header_row, column=col_idx, value=h_text)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = align_center
            cell.border = border_all
            ws.row_dimensions[header_row].height = 42

        current_row = 2
        item_rows_indices = []
        panel_item_rows = {}
        has_pending_items = False

        def write_section(title: str):
            nonlocal current_row
            sec_cell_tt = ws.cell(row=current_row, column=1, value="*")
            sec_cell_tt.font = font_section
            sec_cell_tt.fill = fill_section
            sec_cell_tt.alignment = align_center
            sec_cell_tt.border = border_all

            sec_cell_title = ws.cell(row=current_row, column=2, value=title)
            sec_cell_title.font = font_section
            sec_cell_title.fill = fill_section
            sec_cell_title.alignment = align_left
            sec_cell_title.border = border_all

            for c in range(3, 10):
                empty_c = ws.cell(row=current_row, column=c, value="")
                empty_c.fill = fill_section
                empty_c.border = border_all
            ws.row_dimensions[current_row].height = 16
            current_row += 1

        def write_item(name: str, sku: str, origin: str, unit: str, qty: float, price: int, notes: str = "", tt: str = "+", assembly_heading: bool = False):
            nonlocal current_row, has_pending_items
            has_pending_items = has_pending_items or price is None or not isinstance(qty, (int, float))
            discount = discounts.get(origin.strip().casefold(), 0)
            net_price = f"=J{current_row}*(1-K{current_row}/100)" if price is not None else 'Chờ báo giá'
            item_cells = [
                (tt, align_center, False),
                (name, align_left, False),
                (sku, align_center, False),
                (origin, align_center, False),
                (unit, align_center, False),
                (qty, align_center, False),
                (net_price, align_right, False),
                (f"=F{current_row}*G{current_row}" if price is not None and isinstance(qty, (int,float)) else 'Chưa xác nhận', align_right, True),
                (notes, align_left, False),
                (price, align_right, False),
                (discount, align_right, False),
            ]
            for col_idx, (val, al, is_b) in enumerate(item_cells, 1):
                cell = ws.cell(row=current_row, column=col_idx, value=val)
                cell.font = font_data_bold if is_b or assembly_heading else font_data
                cell.alignment = al
                cell.border = border_all
                if col_idx in (7, 8):
                    cell.number_format = '#,##0'
                if col_idx == 6:
                    cell.number_format = '#,##0.00'
            # Wrapped descriptions and pending-selection notes must remain
            # readable in Excel, not only in the web preview.
            wrapped_lines = max(
                sum(max(1, math.ceil(len(line) / width)) for line in str(value or '').split('\n'))
                for value, width in ((name, 42), (sku, 20), (notes, 25)))
            ws.row_dimensions[current_row].height = max(16, wrapped_lines * 15.75)
            item_rows_indices.append(current_row)
            panel_item_rows.setdefault(panel_row_idx, []).append(current_row)
            current_row += 1

        # Check if devices is already a full structured spreadsheet rows list
        has_row_types = any(isinstance(d, dict) and d.get("row_type") for d in devices)

        panel_row_idx = 2
        clean_p_name = project_name.upper().replace("DỰ ÁN", "").strip() or "TSXĐ-630A"

        if has_row_types:
            for r in devices:
                r_type = r.get("row_type")
                if r_type == "panel_header":
                    p_name = str(r.get("name") or f"TỦ ĐIỆN {clean_p_name}")
                    if not p_name.upper().startswith('TỦ'):
                        p_name = 'TỦ ĐIỆN ' + p_name
                    p_origin = str(r.get("origin") or "")
                    p_unit = str(r.get("unit") or "Tủ")
                    p_qty = float(r.get("quantity") or 1.0)
                    panel_cells = [
                        (str(r.get("tt") or "1"), align_center, font_panel),
                        (p_name, align_left, font_panel),
                        (str(r.get("sku") or ""), align_center, font_panel),
                        (p_origin, align_center, font_panel),
                        (p_unit, align_center, font_panel),
                        (p_qty, align_center, font_panel),
                        (0, align_right, font_panel),
                        (0, align_right, font_panel),
                        (str(r.get("notes") or ""), align_left, font_panel),
                    ]
                    panel_row_idx = current_row
                    for col_idx, (val, al, fn) in enumerate(panel_cells, 1):
                        cell = ws.cell(row=current_row, column=col_idx, value=val)
                        cell.font = fn
                        cell.fill = fill_panel
                        cell.alignment = al
                        cell.border = border_all
                        if col_idx in (7, 8):
                            cell.number_format = '#,##0'
                    ws.cell(row=current_row, column=6).number_format = '0.00'
                    ws.row_dimensions[current_row].height = 16
                    current_row += 1

                elif r_type == "section_header":
                    write_section(str(r.get("name") or "Mục phân nhóm"))

                elif r_type in ["item", "accessory"]:
                    name = str(r.get("name") or "Thiết bị")
                    specification = str(r.get("spec") or "").strip()
                    if specification and specification not in name:
                        name += (" " if r.get('commercial_display') and not r.get('commercial_package') else "\n") + specification
                    proposal = r.get('selection_analysis') or {}
                    if proposal.get('meter_kind') == 'AMMETER' and proposal.get('ct_ratio') and proposal.get('proposed_spec'):
                        name += "\nĐề xuất · " + proposal['proposed_spec']
                    sku = str(r.get("sku") or "")
                    origin = str(r.get("origin") or "")
                    unit = str(r.get("unit") or "Cái")
                    pending = r.get('quantity') is None or r.get('unit_price') is None or r.get('inclusion_status') == 'needs_confirmation'
                    has_pending_items = has_pending_items or pending
                    qty = float(r['quantity']) if r.get('quantity') is not None else 'Theo thiết kế'
                    price = None if pending else int(r.get('unit_price') or 0)
                    notes = str(r.get("notes") or "")
                    tt = str(r.get("tt") or ("↳" if r_type == "accessory" or r.get("is_accessory") else "+"))
                    write_item(name, sku, origin, unit, qty, price, notes, tt=tt, assembly_heading=bool(r.get('assembly_heading')))
        else:
            # Write Main Panel Row
            panel_cells = [
                ("1", align_center, font_panel),
                (f"TỦ ĐIỆN {clean_p_name}", align_left, font_panel),
                ("", align_center, font_panel),
                ("VN", align_center, font_panel),
                ("Tủ", align_center, font_panel),
                (1.0, align_center, font_panel),
                (0, align_right, font_panel),
                (0, align_right, font_panel),
                ("", align_left, font_panel),
            ]
            panel_row_idx = current_row
            for col_idx, (val, al, fn) in enumerate(panel_cells, 1):
                cell = ws.cell(row=current_row, column=col_idx, value=val)
                cell.font = fn
                cell.fill = fill_panel
                cell.alignment = al
                cell.border = border_all
                if col_idx in (7, 8):
                    cell.number_format = '#,##0'
            ws.cell(row=current_row, column=6).number_format = '0.00'
            ws.row_dimensions[current_row].height = 16
            current_row += 1

            # Group raw devices dynamically
            sections_map = {}
            for dev in devices:
                sec = str(dev.get("section") or "").strip()
                if not sec:
                    cat = str(dev.get("category") or "").upper()
                    d_name = str(dev.get("name") or "").lower()
                    in_a = dev.get("in_a") or 0
                    if "ACB" in cat or in_a >= 400 or "incomer" in d_name or "tổng" in d_name:
                        sec = "Đầu vào"
                    elif "QUẠT" in d_name.upper() or "NHIỆT" in d_name.upper() or "LÀM MÁT" in d_name.upper():
                        sec = "Làm mát cho ngăn tủ rack"
                    elif "ĐÈN" in d_name.upper() or "ĐỒNG HỒ" in d_name.upper() or "VOLT" in d_name.upper() or "AMPE" in d_name.upper():
                        sec = "Đo lường & Giám sát"
                    elif "TỤ BÙ" in d_name.upper() or "BÙ" in d_name.upper() or "CAPACITOR" in cat:
                        sec = "Bù công suất"
                    elif "TIMER" in cat or "CONTACTOR" in cat or "RELAY" in cat:
                        sec = "Điều khiển & Phụ trợ"
                    else:
                        sec = "Đầu ra"
                if sec not in sections_map:
                    sections_map[sec] = []
                sections_map[sec].append(dev)

            # Section 1: Vỏ tủ + phụ kiện
            from app.services.bom.bom_orchestrator import BomOrchestratorService
            from app.services.bom.busbar_calculator import BusbarCalculatorService
            from app.services.device_catalog_engine import DeviceCatalogEngine

            eng = DeviceCatalogEngine.get_instance()
            bom_calc = BomOrchestratorService.calculate_full_bom("1", devices)
            enc_calc = bom_calc.enclosure
            busbar_calc = bom_calc.busbar
            labor_calc = bom_calc.labor

            enc_desc = (
                f"Vỏ tủ điện sơn tĩnh điện tiêu chuẩn công nghiệp\n"
                f"+ KT : H{enc_calc.get('H')}xW{enc_calc.get('W')}xD{enc_calc.get('D')}xT{enc_calc.get('tole_thickness_mm')}mm\n"
                f"+ Cấp bảo vệ IP54"
            )
            write_section("Vỏ tủ + phụ kiện")
            write_item(enc_desc, "Sơn tĩnh điện", "VN", "Cái", 1.0, enc_calc.get("estimated_price", 0), "Sơn tĩnh điện RAL 7035")

            incomer_a = max([float(d.get("in_a") or 0) for d in devices] or [63.0])
            need_busbar_exp = BusbarCalculatorService.needs_busbar(incomer_a, devices)
            if need_busbar_exp:
                write_item(
                    f"Đồng thanh cái mạ thiếc bọc co nhiệt (Định mức In={int(incomer_a)}A, {busbar_calc.get('section_mm2')}mm2)",
                    "Đồng đỏ 99.9%",
                    "VN",
                    "Hệ",
                    1.0,
                    busbar_calc.get("unit_price", 0),
                    f"Giá đồng: {int(settings.BUSBAR_PRICE_PER_KG):,} đ/kg · KL ~{busbar_calc.get('mass_Cu_kg')}kg".replace(",", ".")
                )
            
            acc_total = sum(float(a.get("quantity", 1)) * float(a.get("unit_price", 0)) for a in bom_calc.accessories)
            acc_name_exp = "Vật tư phụ tủ điện (đầu cosse SC động lực, dây điều khiển Cadivi VSF, máng cáp nhựa PVC, sứ đỡ thanh cái SM)" if need_busbar_exp else "Vật tư phụ tủ điện (Cầu lược 3P/1P phân phối MCB, đầu cosse ghim, dây điều khiển Cadivi VSF, máng cáp nhựa PVC, kẹp tiếp địa)"
            write_item(acc_name_exp, "Trọn gói", "VN", "Tủ", 1.0, int(acc_total))

            hourly_rate = settings.DEFAULT_LABOR_HOURLY_RATE
            labor_cost = int(float(labor_calc.get("T_total_hours", 0)) * hourly_rate)
            write_item("Nhân công lắp ráp, đấu nối & kiểm tra xuất xưởng (QC)", "QC-LABOR", "VN", "Tủ", 1.0, labor_cost)

            from app.services.ai.procurement_review import quotation_section
            sections = sorted(sections_map, key=lambda name: {'Đầu vào': 0, 'Đầu ra': 1}.get(
                quotation_section({'section': name}), 2))
            for sec_name in sections:
                dev_list = sections_map[sec_name]
                write_section(sec_name)
                merged_list = DynamicGroupingEngine.merge_duplicates(dev_list)
                for d in merged_list:
                    d_cat = str(d.get("category") or "")
                    d_in = d.get("in_a")
                    d_poles = d.get("poles")
                    d_price = int(d.get("unit_price") or d.get("price") or 0)
                    write_item(
                        str(d.get("name") or "Thiết bị đóng cắt"),
                        str(d.get("sku") or d.get("part_number") or d.get("spec") or ""),
                        str(d.get("brand") or brand_preference).replace(" Electric", ""),
                        str(d.get("unit") or "Cái"),
                        float(d.get("quantity") or 1.0),
                        d_price,
                        str(d.get("notes") or "")
                    )

        # 4. Summary Rows (Matching template)
        # Each panel totals only its own detail rows. Referencing the grand
        # total here creates a cycle when a later panel lies in its SUM range.
        for panel_row, detail_rows in panel_item_rows.items():
            refs = f"H{detail_rows[0]}:H{detail_rows[-1]}"
            pending_panel = any(ws.cell(row=row, column=8).value == 'Chưa xác nhận' for row in detail_rows)
            ws.cell(row=panel_row, column=7, value='Chưa đủ dữ liệu' if pending_panel else f"=SUM({refs})")
            ws.cell(row=panel_row, column=8, value='Chưa đủ dữ liệu' if pending_panel else f"=F{panel_row}*G{panel_row}")

        # Row: TỔNG GIÁ TRỊ TRƯỚC THUẾ
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=7)
        c_sub = ws.cell(row=current_row, column=1, value="TỔNG GIÁ TRỊ TRƯỚC THUẾ")
        c_sub.font = font_grand_total
        c_sub.alignment = align_right

        panel_refs = ",".join(f"H{row}" for row in panel_item_rows)
        tot_formula = 'Chưa đủ dữ liệu' if has_pending_items else (f"=SUM({panel_refs})" if panel_refs else "=0")
        c_sub_val = ws.cell(row=current_row, column=8, value=tot_formula)
        c_sub_val.font = font_grand_total
        c_sub_val.alignment = align_right
        c_sub_val.number_format = '#,##0'

        for c in range(1, 10):
            ws.cell(row=current_row, column=c).border = border_all
        ws.row_dimensions[current_row].height = 24
        before_vat_row = current_row
        current_row += 1

        # Dynamic VAT calculation & display
        effective_vat_rate = (float(vat_percent) / 100.0) if vat_percent is not None else settings.DEFAULT_VAT_RATE
        vat_display_pct = int(round(effective_vat_rate * 100)) if (effective_vat_rate * 100).is_integer() else round(effective_vat_rate * 100, 1)

        # Row: THUẾ GTGT (Dynamic %)
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=7)
        c_vat = ws.cell(row=current_row, column=1, value=f"THUẾ GTGT {vat_display_pct}%")
        c_vat.font = font_grand_total
        c_vat.alignment = align_right

        vat_formula = 'Chưa đủ dữ liệu' if has_pending_items else f"=H{before_vat_row}*{effective_vat_rate}"
        c_vat_val = ws.cell(row=current_row, column=8, value=vat_formula)
        c_vat_val.font = font_grand_total
        c_vat_val.alignment = align_right
        c_vat_val.number_format = '#,##0'

        for c in range(1, 10):
            ws.cell(row=current_row, column=c).border = border_all
        ws.row_dimensions[current_row].height = 24
        vat_row = current_row
        current_row += 1

        # Row: TỔNG GIÁ TRỊ SAU THUẾ (Gold Yellow #FFC000)
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=7)
        c_tot = ws.cell(row=current_row, column=1, value="TỔNG GIÁ TRỊ SAU THUẾ")
        c_tot.font = font_grand_total
        c_tot.alignment = align_right

        grand_tot_formula = 'Chưa đủ dữ liệu' if has_pending_items else f"=H{before_vat_row}+H{vat_row}"
        c_tot_val = ws.cell(row=current_row, column=8, value=grand_tot_formula)
        c_tot_val.font = font_grand_total
        c_tot_val.alignment = align_right
        c_tot_val.number_format = '#,##0'

        for c in range(1, 10):
            ws.cell(row=current_row, column=c).border = border_all
            ws.cell(row=current_row, column=c).fill = fill_total
        ws.row_dimensions[current_row].height = 26
        current_row += 1

        # 5. Dedicated Technical Proposals Table (BẢNG ĐỀ XUẤT PHƯƠNG ÁN KỸ THUẬT & THIẾT BỊ TƯƠNG THÍCH DO AI PHÂN TÍCH)
        if proposals is None:
            proposals = []
            for d in devices:
                if isinstance(d, dict) and (d.get("compatible_proposal") or d.get("is_alternative_recommended")):
                    cp = d.get("compatible_proposal") or {}
                    proposals.append({
                        "original_device": cp.get("original_device") or d.get("name") or "",
                        "original_spec": cp.get("original_spec") or d.get("spec") or "",
                        "ai_analysis": cp.get("ai_analysis") or d.get("notes") or "",
                        "proposed_device": cp.get("proposed_device") or d.get("sku") or "",
                        "proposed_spec": cp.get("proposed_spec") or d.get("spec") or "",
                        "suggested_brand": cp.get("suggested_brand") or d.get("origin") or "",
                        "technical_reason": cp.get("technical_reason") or d.get("compatibility_note") or "Bảo toàn 100% sơ đồ nguyên lý"
                    })

        if proposals and include_technical_proposals:
            current_row += 1  # Dòng trống phân cách

            # Title banner
            fill_prop_title = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
            font_prop_title = Font(name="Times New Roman", size=11, bold=True, color="FFFFFF")
            ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=9)
            c_prop_title = ws.cell(row=current_row, column=1, value="BẢNG ĐỀ XUẤT PHƯƠNG ÁN KỸ THUẬT & THIẾT BỊ TƯƠNG THÍCH (DO AI PHÂN TÍCH)")
            c_prop_title.font = font_prop_title
            c_prop_title.fill = fill_prop_title
            c_prop_title.alignment = align_center
            for c in range(1, 10):
                ws.cell(row=current_row, column=c).border = border_all
                ws.cell(row=current_row, column=c).fill = fill_prop_title
            ws.row_dimensions[current_row].height = 28
            current_row += 1

            # Subtitle commitment banner
            fill_prop_sub = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
            font_prop_sub = Font(name="Times New Roman", size=10, italic=True, bold=True, color="1F4E79")
            ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=9)
            c_sub_note = ws.cell(row=current_row, column=1, value="Cam kết kỹ thuật: Bảo toàn 100% sơ đồ nguyên lý 1 sợi (SLD), số cực, dòng ngắn mạch Icu và tính chọn lọc bảo vệ.")
            c_sub_note.font = font_prop_sub
            c_sub_note.fill = fill_prop_sub
            c_sub_note.alignment = align_center
            for c in range(1, 10):
                ws.cell(row=current_row, column=c).border = border_all
                ws.cell(row=current_row, column=c).fill = fill_prop_sub
            ws.row_dimensions[current_row].height = 22
            current_row += 1

            # Table Header for Proposals
            fill_prop_head = PatternFill(start_color="8EA9DB", end_color="8EA9DB", fill_type="solid")
            font_prop_head = Font(name="Times New Roman", size=10, bold=True, color="000000")

            ws.cell(row=current_row, column=1, value="TT").font = font_prop_head
            ws.cell(row=current_row, column=2, value="THIẾT BỊ GỐC (BẢN VẼ)").font = font_prop_head
            ws.cell(row=current_row, column=3, value="QUY CÁCH GỐC").font = font_prop_head
            ws.merge_cells(start_row=current_row, start_column=4, end_row=current_row, end_column=5)
            ws.cell(row=current_row, column=4, value="PHÂN TÍCH KỸ THUẬT AI").font = font_prop_head
            ws.merge_cells(start_row=current_row, start_column=6, end_row=current_row, end_column=7)
            ws.cell(row=current_row, column=6, value="THIẾT BỊ ĐỀ XUẤT TƯƠNG THÍCH").font = font_prop_head
            ws.cell(row=current_row, column=8, value="HÃNG SX").font = font_prop_head
            ws.cell(row=current_row, column=9, value="CAM KẾT SLD").font = font_prop_head

            for c in range(1, 10):
                ws.cell(row=current_row, column=c).border = border_all
                ws.cell(row=current_row, column=c).fill = fill_prop_head
                ws.cell(row=current_row, column=c).alignment = align_center
            ws.row_dimensions[current_row].height = 26
            current_row += 1

            # Data rows
            for p_idx, prop in enumerate(proposals, 1):
                ws.cell(row=current_row, column=1, value=str(p_idx)).alignment = align_center
                ws.cell(row=current_row, column=2, value=str(prop.get("original_device") or "")).alignment = align_left
                ws.cell(row=current_row, column=3, value=str(prop.get("original_spec") or "")).alignment = align_center

                ws.merge_cells(start_row=current_row, start_column=4, end_row=current_row, end_column=5)
                ws.cell(row=current_row, column=4, value=str(prop.get("ai_analysis") or "")).alignment = align_left

                ws.merge_cells(start_row=current_row, start_column=6, end_row=current_row, end_column=7)
                prop_dev_text = str(prop.get("proposed_device") or "")
                if prop.get("proposed_spec"):
                    prop_dev_text += f"\n({prop.get('proposed_spec')})"
                ws.cell(row=current_row, column=6, value=prop_dev_text).alignment = align_left

                ws.cell(row=current_row, column=8, value=str(prop.get("suggested_brand") or "")).alignment = align_center
                ws.cell(row=current_row, column=9, value=str(prop.get("technical_reason") or "Bảo toàn 100% SLD")).alignment = align_left

                for c in range(1, 10):
                    ws.cell(row=current_row, column=c).font = font_data
                    ws.cell(row=current_row, column=c).border = border_all
                ws.row_dimensions[current_row].height = 36
                current_row += 1

        # Column widths auto-adjustment
        col_widths = {
            1: 5.285,
            2: 47.426,
            3: 20.57,
            4: 13.57,
            5: 8.71,
            6: 10.285,
            7: 16.14,
            8: 14.71,
            9: 17.855,
        }
        col_widths.update({10: 18, 11: 20})
        for col_idx, width in col_widths.items():
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = width

        # Match the customer-facing nine-column quotation while retaining the
        # price/discount inputs used by the unit-price formulas.
        ws.column_dimensions['J'].hidden = True
        ws.column_dimensions['K'].hidden = True
        ws.column_dimensions['I'].hidden = False
        ws.freeze_panes = 'C2'
        ws.print_area = f'A1:I{current_row - 1}'
        ws.print_title_rows = '1:1'
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.orientation = 'landscape'
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0

        # 7. Save file to exports directory
        out_dir = Path(settings.EXPORT_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)
        clean_proj = "".join(c for c in project_name if c.isalnum() or c in ("-", "_", " ")).strip().replace(" ", "_")
        clean_suffix = "".join(c for c in (filename_suffix or "") if c.isalnum() or c in ("-", "_", " ")).strip().replace(" ", "_")
        suffix_part = f"_{clean_suffix}" if clean_suffix else ""
        filename = f"BaoGia_{clean_proj}{suffix_part}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:10]}.xlsx"
        file_path = out_dir / filename
        wb.save(file_path)
        return str(file_path)

    @staticmethod
    def match_devices_multi_brand(devices: list, default_brand: str = "Theo thiết kế") -> list:
        """Đối chiếu các thiết bị bóc tách với tất cả các hãng trong Catalog DB."""
        from app.services.ai.quotation_selection import replacement_candidates, select_quotation_devices
        from app.services.ai.takeoff_pricebook import match_device, published_rows
        from app.services.ai.manufacturer_registry import canonical_brand
        from app.services.library_review_scope import MAIN_DEVICE_TYPES

        price_rows = published_rows()
        rows_by_brand = {}
        for row in price_rows:
            rows_by_brand.setdefault(canonical_brand(row.get('brand')), []).append(row)
        selected = select_quotation_devices(devices, default_brand, price_rows)
        matched_items = []
        for idx, dev in enumerate(DynamicGroupingEngine.merge_duplicates(selected), 1):
            match = match_device(dev, price_rows)
            product = match.get('row') if match['status'] == 'matched' else None
            cat = str(dev.get('category') or '').upper()
            spec = str(dev.get('spec') or '').strip()
            name = ' · '.join(filter(None, [cat, spec])) if cat in MAIN_DEVICE_TYPES else str(dev.get('name') or 'Thiết bị').splitlines()[0]
            qty = dev.get('procurement_quantity') if dev.get('procurement_quantity') is not None else dev.get('quantity', 1)
            price = product.get('price') if product else None
            brand_options = {}
            for maker, maker_rows in rows_by_brand.items() if cat in MAIN_DEVICE_TYPES else ():
                trial = {**dev, 'brand': maker, 'detected_brand': '', 'part_number': '', 'sku': '',
                         'selection_source': 'default_brand', 'selected_product': None}
                options = match_device(trial, maker_rows)['candidates'] or replacement_candidates(trial, maker_rows)
                if options:
                    brand_options[maker] = options[0]
            replacement = (dev.get('source_observations') or {}).get('quotation_replacement') or {}
            description = f"{name} => {replacement['proposed_spec']}" if replacement else name
            matched_items.append({
                **dev, 'id': idx, 'name': name, 'description': description, 'brand_switchable': cat in MAIN_DEVICE_TYPES,
                'selected_brand': dev.get('brand') or dev.get('detected_brand') or '',
                'sku': product['sku'] if product else dev.get('part_number') or '',
                'quantity': qty, 'unit': dev.get('unit') or 'Cái',
                'unit_price': price, 'line_total': qty * price if qty is not None and price is not None else None,
                'price_status': 'confirmed' if price is not None else 'pending',
                'discount_percent': 0, 'brand_options': brand_options,
                'catalog_matched': product is not None, 'pricebook_match': match,
                'notes': replacement.get('reason', ''),
            })
        return matched_items
