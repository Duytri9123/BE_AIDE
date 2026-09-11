"""
Equipment Catalog Multi-format Exporter
Generates:
1. Excel BOM (.xlsx) with styled sheets for each brand and summary.
2. CSV Catalog (.csv) UTF-8 with BOM.
3. SQL Migration Script (.sql) for direct DB execution.
4. JSON Catalog (.json) validated dataset.
"""
import json
import os
import csv
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

BRAND_DISPLAY = {
    "ls_standard": "LS (standard)",
    "ls": "LS (standard)",
    "ls_premium": "LS (premium)",
    "schneider": "Schneider Electric",
    "chint": "Chint",
    "abb": "ABB",
    "mitsubishi": "Mitsubishi",
    "emic": "EMIC",
    "samwha": "Samwha"
}

ALL_EXPORT_BRANDS = [
    "LS (standard)",
    "LS (premium)",
    "Schneider Electric",
    "Chint",
    "ABB",
    "Mitsubishi",
    "EMIC",
    "Samwha"
]

def export_all():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_json = os.path.join(base_dir, "..", "data", "catalog_data.json")
    export_dir = os.path.join(base_dir, "..", "data", "exports")
    os.makedirs(export_dir, exist_ok=True)

    if not os.path.exists(input_json):
        print(f"[ERROR] Input catalog not found: {input_json}")
        return

    with open(input_json, "r", encoding="utf-8") as f:
        items = json.load(f)

    print(f"[INFO] Loaded {len(items)} items. Exporting to multiple formats in {export_dir}...")

    # 1. Export Excel (.xlsx)
    export_excel(items, os.path.join(export_dir, "equipment_catalog.xlsx"))

    # 2. Export CSV (.csv)
    export_csv(items, os.path.join(export_dir, "equipment_catalog.csv"))

    # 3. Export SQL (.sql)
    export_sql(items, os.path.join(export_dir, "seed_equipment_catalog.sql"))

    # 4. Export JSON (.json)
    export_json(items, os.path.join(export_dir, "equipment_catalog.json"))

    print(f"[SUCCESS] All export formats generated successfully in {export_dir}")

def export_excel(items, filepath):
    wb = Workbook()
    wb.remove(wb.active)

    # Styles
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    alt_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    regular_font = Font(name="Arial", size=10)
    bold_font = Font(name="Arial", size=10, bold=True)
    border_thin = Side(style='thin', color='E2E8F0')
    cell_border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thin)

    headers = [
        ("STT", 6, "center"),
        ("Mã SKU", 22, "left"),
        ("Tên Thiết Bị", 42, "left"),
        ("Hãng", 18, "center"),
        ("Loại", 12, "center"),
        ("Dòng Series", 16, "center"),
        ("Số Cực (P)", 12, "center"),
        ("Dòng In / Dung lượng", 16, "right"),
        ("Cắt Icu (kA)", 12, "right"),
        ("Dòng Rò IΔ (mA)", 14, "right"),
        ("Kích Thước WxHxD (mm)", 22, "center"),
        ("Pitch (mm)", 12, "right"),
        ("Đơn Giá (VND)", 16, "right"),
    ]

    def write_sheet(ws, title, sheet_items):
        safe_title = title.replace("/", "-")[:30]
        ws.title = safe_title
        ws.views.sheetView[0].showGridLines = True

        # Header Row
        for col_idx, (h_name, width, align) in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=h_name)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = cell_border
            ws.column_dimensions[get_column_letter(col_idx)].width = width
        ws.row_dimensions[1].height = 28

        # Data Rows
        for row_idx, item in enumerate(sheet_items, 2):
            raw_brand = item.get("brand", "ls_standard").lower()
            brand_label = BRAND_DISPLAY.get(raw_brand, item.get("brand_display", raw_brand.upper() if raw_brand in ["emic", "abb"] else raw_brand.capitalize()))
            dims = f"{item.get('w', '-')} x {item.get('h', '-')} x {item.get('d', '-')}"
            price_val = item.get("g")
            price = price_val if price_val is not None else "Liên hệ"

            # In / kVA display
            in_val = item.get("in")
            kva_val = item.get("kva")
            if kva_val is not None:
                rating_str = f"{kva_val} kVAr"
            elif in_val is not None:
                rating_str = f"{in_val} A"
            else:
                rating_str = "-"

            row_data = [
                row_idx - 1,
                item.get("ma", ""),
                item.get("n", ""),
                brand_label,
                item.get("t", ""),
                item.get("series", "") or "-",
                item.get("p", "") if item.get("p") is not None else "-",
                rating_str,
                item.get("icu", 0) if item.get("icu") else "-",
                item.get("idelta", "-") if item.get("idelta") else "-",
                dims,
                item.get("pitch", "-") if item.get("pitch") else "-",
                price
            ]

            is_alt = (row_idx % 2 == 1)

            for col_idx, val in enumerate(row_data, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.font = regular_font
                cell.border = cell_border
                align = headers[col_idx - 1][2]
                cell.alignment = Alignment(horizontal=align, vertical="center")

                if is_alt:
                    cell.fill = alt_fill

                # Format price
                if col_idx == 13:
                    if isinstance(val, (int, float)):
                        cell.number_format = '#,##0 "₫"'
                        cell.font = bold_font
                    else:
                        cell.font = regular_font

            ws.row_dimensions[row_idx].height = 20

    # 1. Sheet All
    ws_all = wb.create_sheet("Tổng Hợp Toàn Bộ")
    write_sheet(ws_all, "Tổng Hợp Toàn Bộ", items)

    # 2. Sheet per brand in catalog
    for b_name in ALL_EXPORT_BRANDS:
        b_items = [it for it in items if BRAND_DISPLAY.get(it.get("brand", "").lower()) == b_name or it.get("brand_display") == b_name]
        if b_items:
            ws_b = wb.create_sheet(b_name)
            write_sheet(ws_b, b_name, b_items)

    wb.save(filepath)
    print(f"  + Exported Excel: {filepath}")

def export_csv(items, filepath):
    headers = ["SKU", "Name", "Brand", "Category", "Series", "Poles", "RatedCurrent_A", "Capacity_kVAr", "BreakingCapacity_kA", "LeakageCurrent_mA", "Width_mm", "Height_mm", "Depth_mm", "Pitch_mm", "Price_VND"]
    
    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for it in items:
            raw_b = it.get("brand", "ls_standard").lower()
            price_val = it.get("g")
            price = price_val if price_val is not None else 0
            writer.writerow([
                it.get("ma", ""),
                it.get("n", ""),
                BRAND_DISPLAY.get(raw_b, it.get("brand_display", raw_b.upper() if raw_b in ["emic", "abb"] else raw_b.capitalize())),
                it.get("t", ""),
                it.get("series", "") or "",
                it.get("p", ""),
                it.get("in", ""),
                it.get("kva", ""),
                it.get("icu", ""),
                it.get("idelta", ""),
                it.get("w", ""),
                it.get("h", ""),
                it.get("d", ""),
                it.get("pitch", ""),
                price
            ])
    print(f"  + Exported CSV: {filepath}")

def export_sql(items, filepath):
    lines = [
        "-- Equipment Catalog SQL Migration Script",
        "-- Auto-generated for SQLite / PostgreSQL / MySQL",
        "BEGIN TRANSACTION;\n"
    ]

    for b_name in ALL_EXPORT_BRANDS:
        lines.append(f"INSERT OR IGNORE INTO brands (name) VALUES ('{b_name}');")

    categories = sorted(list(set(it.get("t", "MCB").upper() for it in items)))
    for cat in categories:
        lines.append(f"INSERT OR IGNORE INTO device_categories (name) VALUES ('{cat}');")

    lines.append("\n-- Insert Device Series and Models")
    for it in items:
        raw_b = it.get("brand", "ls_standard").lower()
        b_name = BRAND_DISPLAY.get(raw_b, it.get("brand_display", raw_b.upper() if raw_b in ["emic", "abb"] else raw_b.capitalize()))
        cat = it.get("t", "MCB").upper()
        series = it.get("series") or "Standard"
        sku = it.get("ma", "").replace("'", "''")
        name = it.get("n", "").replace("'", "''")
        price_val = it.get("g")
        price = float(price_val) if price_val is not None else 0.0

        dims_json = json.dumps({
            "w": it.get("w"), "h": it.get("h"), "d": it.get("d"),
            "pitch": it.get("pitch"), "pole_w": it.get("pole_w"),
            "busbar_level": it.get("busbar_level")
        }, ensure_ascii=False).replace("'", "''")

        params_json = json.dumps({
            "p": it.get("p"), "in": it.get("in"), "icu": it.get("icu"),
            "idelta": it.get("idelta"), "kva": it.get("kva"),
            "meterKind": it.get("meterKind"),
            "busbar_holes": it.get("busbar_holes"),
            "mount_holes": it.get("mount_holes"),
            "note": it.get("note")
        }, ensure_ascii=False).replace("'", "''")

        sql = f"""INSERT INTO device_models (device_series_id, sku, name, price, discount_pct, dimensions, parameters)
VALUES (
    (SELECT id FROM device_series WHERE name = '{series}' AND brand_id = (SELECT id FROM brands WHERE name = '{b_name}') LIMIT 1),
    '{sku}', '{name}', {price}, 0.0, '{dims_json}', '{params_json}'
) ON CONFLICT(sku) DO UPDATE SET price = excluded.price, dimensions = excluded.dimensions, parameters = excluded.parameters;"""
        lines.append(sql)

    lines.append("\nCOMMIT;")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"  + Exported SQL: {filepath}")

def export_json(items, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({
            "catalog_version": "2.5.0",
            "total_items": len(items),
            "brands": ALL_EXPORT_BRANDS,
            "items": items
        }, f, ensure_ascii=False, indent=2)
    print(f"  + Exported JSON: {filepath}")

if __name__ == "__main__":
    export_all()
