import os
import json
import re

def main():
    base_dir = r"E:\duytristool\AIDE_website\BE_AIDE\data\thu_vien_tu_dien_v2"
    
    # Load existing forms if available to not lose them
    forms = []
    catalog_path = os.path.join(base_dir, "catalog.json")
    if os.path.exists(catalog_path):
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                cat = json.load(f)
                forms = cat.get("forms", [])
                
                # Format forms for DB
                formatted_forms = []
                for item in forms:
                    asset = {
                        "id": item.get("id"),
                        "name": item.get("name") or item.get("standard_name", ""),
                        "kind": "form_tu",
                        "category": item.get("category",""),
                        "manufacturer": item.get("manufacturer","chua_xac_dinh"),
                        "poles": None,
                        "view": item.get("view","nhieu_mat_vo_tu"),
                        "cad": item.get("cad",""),
                        "preview": item.get("preview",""),
                        "sku_ids": [],
                        "dimensions_mm": item.get("dimensions_mm", {}),
                    }
                    formatted_forms.append(asset)
                forms = formatted_forms
        except Exception as e:
            print("Error loading forms:", e)

    brands = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d)) and d not in ["bo_tri_da_lap", "cho_doi_chieu", "dang_su_dung", "form_tu", "nguon", "phu_kien", "san_pham", "thiet_bi", "tudien"]]

    assets = list(forms)

    for brand in brands:
        brand_path = os.path.join(base_dir, brand)
        for type_ in os.listdir(brand_path):
            type_path = os.path.join(brand_path, type_)
            if not os.path.isdir(type_path): continue
            for series in os.listdir(type_path):
                series_path = os.path.join(type_path, series)
                if not os.path.isdir(series_path): continue
                for variant in os.listdir(series_path):
                    variant_path = os.path.join(series_path, variant)
                    data_file = os.path.join(variant_path, "data.json")
                    if os.path.exists(data_file):
                        with open(data_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        poles = None
                        if "P" in variant:
                            try:
                                poles = int(variant.replace("P", ""))
                            except:
                                pass
                        
                        asset = {
                            "id": f"{brand}_{type_}_{series}_{variant}",
                            "name": f"{brand} {series} {variant} ({type_})",
                            "kind": "thiet_bi" if "Phụ_kiện" not in type_ else "phu_kien",
                            "category": type_,
                            "manufacturer": brand,
                            "series": series,
                            "poles": poles,
                            "cad": "",
                            "preview": "",
                            "sku_ids": [v.get("sku") for v in data.get("variants", [])],
                            "sku_count": len(data.get("variants", [])),
                            "skus": data.get("variants", []),
                            "dimensions_mm": data.get("dimensions", {})
                        }
                        assets.append(asset)

    db = {
        "active": True,
        "schema_version": 4,
        "summary": {
            "catalog_products": sum(a.get("sku_count", 0) for a in assets),
            "cad_assets": len(assets)
        },
        "assets": assets
    }

    index_path = os.path.join(base_dir, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    db_json = json.dumps(db, ensure_ascii=False, separators=(',',':'))
    
    # Try regex first
    new_html = re.sub(r'const DB=\{[^;]+\};', f'const DB={db_json};', html, count=1)
    
    if new_html == html:
        print("Regex failed. Using manual extraction.")
        idx = html.find('const DB={')
        if idx != -1:
            depth = 0
            end_idx = idx
            in_string = False
            escape = False
            for i, c in enumerate(html[idx:], idx):
                if escape:
                    escape = False
                    continue
                if c == '\\' and in_string:
                    escape = True
                    continue
                if c == '"' and not escape:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        end_idx = i + 1
                        break
            if html[end_idx] == ';':
                end_idx += 1
            new_html = html[:idx] + f'const DB={db_json};' + html[end_idx:]
        else:
            print("Could not find DB in HTML.")
            return

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(new_html)
        
    print(f"Successfully updated index.html with {len(assets)} assets (including {len(forms)} forms).")

if __name__ == '__main__':
    main()
