import os
import re
import json
from glob import glob

base = r"E:\duytristool\AIDE_website\BE_AIDE\data\thu_vien_tu_dien_v2"

print("Building complete database for thu_vien_tu_dien_v2...")

# 1. Brand Groups (Brand / Type / Series / Variant)
brand_groups = []
brands = ["ABB", "CHINT", "EMIC", "LS", "Mitsubishi", "Samwha", "Schneider"]

for b in brands:
    b_path = os.path.join(base, b)
    if not os.path.exists(b_path): continue
    for type_ in os.listdir(b_path):
        t_path = os.path.join(b_path, type_)
        if not os.path.isdir(t_path): continue
        for series in os.listdir(t_path):
            s_path = os.path.join(t_path, series)
            if not os.path.isdir(s_path): continue
            for variant in os.listdir(s_path):
                v_path = os.path.join(s_path, variant)
                data_path = os.path.join(v_path, "data.json")
                if os.path.exists(data_path):
                    with open(data_path, "r", encoding="utf-8") as f:
                        v_data = json.load(f)
                    
                    rel_dir = os.path.relpath(v_path, base).replace("\\", "/")
                    cad_file = "cad.dxf" if os.path.exists(os.path.join(v_path, "cad.dxf")) else ""
                    preview_file = "front.svg" if os.path.exists(os.path.join(v_path, "front.svg")) else ""
                    
                    skus = v_data.get("variants", [])
                    dims = v_data.get("dimensions", {})
                    
                    poles = None
                    if "P" in variant:
                        try:
                            poles = int(re.sub(r"[^\d]", "", variant))
                        except:
                            pass
                            
                    item = {
                        "id": f"group_{b}_{type_}_{series}_{variant}".replace(" ", "_"),
                        "name": f"{b} {series} {variant}",
                        "kind": "brand_groups",
                        "brand": b,
                        "category": type_,
                        "series": series,
                        "variant": variant,
                        "poles": poles,
                        "folder": rel_dir,
                        "cad": f"{rel_dir}/{cad_file}" if cad_file else "",
                        "preview": f"{rel_dir}/{preview_file}" if preview_file else "",
                        "dimensions": dims,
                        "sku_count": len(skus),
                        "skus": skus,
                        "source_ref": v_data.get("cad_source", "")
                    }
                    brand_groups.append(item)

print(f"Collected {len(brand_groups)} brand variant groups.")

# 2. Thiet bi CAD (Electrical Equipment CAD blocks)
thiet_bi_list = []
for mf in glob(os.path.join(base, "thiet_bi", "**", "metadata.json"), recursive=True):
    try:
        with open(mf, "r", encoding="utf-8") as f:
            m = json.load(f)
        folder = os.path.dirname(mf)
        rel_folder = os.path.relpath(folder, base).replace("\\", "/")
        
        geom = m.get("geometry", {})
        extent = geom.get("drawing_extent", {})
        
        item = {
            "id": m.get("id", os.path.basename(folder)),
            "name": m.get("name", os.path.basename(folder)),
            "kind": "thiet_bi",
            "brand": m.get("manufacturer", "Chưa xác định"),
            "category": m.get("category", "Thiết bị điện"),
            "poles": m.get("poles"),
            "view": m.get("view", "Mặt trước"),
            "folder": rel_folder,
            "cad": f"{rel_folder}/cad.dxf" if os.path.exists(os.path.join(folder, "cad.dxf")) else "",
            "preview": f"{rel_folder}/preview.svg" if os.path.exists(os.path.join(folder, "preview.svg")) else "",
            "reference_cad": f"{rel_folder}/ban_ve_nguon.dxf" if os.path.exists(os.path.join(folder, "ban_ve_nguon.dxf")) else "",
            "dimensions": {
                "w": round(extent.get("width", 0), 1),
                "h": round(extent.get("height", 0), 1),
                "d": round(extent.get("depth", 0), 1)
            },
            "entity_count": geom.get("entity_count", 0),
            "source_blocks": m.get("evidence", {}).get("source_blocks", [])
        }
        thiet_bi_list.append(item)
    except Exception as e:
        pass

print(f"Collected {len(thiet_bi_list)} CAD blocks for thiet_bi.")

# 3. Form tu (Empty cabinet shells)
form_tu_list = []
# Check both form_tu and dang_su_dung/form_tu
for mf in glob(os.path.join(base, "form_tu", "**", "metadata.json"), recursive=True):
    try:
        with open(mf, "r", encoding="utf-8") as f:
            m = json.load(f)
        folder = os.path.dirname(mf)
        rel_folder = os.path.relpath(folder, base).replace("\\", "/")
        
        dims = m.get("dimensions_mm_from_source_title") or m.get("dimensions_mm", {})
        specs = m.get("specifications", {})
        
        item = {
            "id": m.get("id", os.path.basename(folder)),
            "name": m.get("name") or os.path.basename(folder),
            "kind": "form_tu",
            "brand": "Sản xuất gia công vỏ tủ",
            "category": m.get("category", "Vỏ tủ điện"),
            "folder": rel_folder,
            "cad": f"{rel_folder}/cad.dxf" if os.path.exists(os.path.join(folder, "cad.dxf")) else "",
            "preview": f"{rel_folder}/preview.svg" if os.path.exists(os.path.join(folder, "preview.svg")) else "",
            "reference_cad": f"{rel_folder}/ban_ve_nguon.dxf" if os.path.exists(os.path.join(folder, "ban_ve_nguon.dxf")) else "",
            "dimensions": dims,
            "thickness": specs.get("sheet_thickness_source") or specs.get("sheet_thickness"),
            "door_layers": specs.get("door_layers", 1),
            "environment": specs.get("environment", "trong_nha" if "TRONG_NHA" in m.get("name","").upper() else "ngoai_troi")
        }
        form_tu_list.append(item)
    except Exception as e:
        pass

print(f"Collected {len(form_tu_list)} form_tu shell assets.")

# 4. Phu kien CAD (Accessories)
phu_kien_list = []
for mf in glob(os.path.join(base, "phu_kien", "**", "metadata.json"), recursive=True):
    try:
        with open(mf, "r", encoding="utf-8") as f:
            m = json.load(f)
        folder = os.path.dirname(mf)
        rel_folder = os.path.relpath(folder, base).replace("\\", "/")
        
        geom = m.get("geometry", {})
        extent = geom.get("drawing_extent", {})
        
        cat = m.get("category", "Phụ kiện")
        # Sub-category from folder
        parts = rel_folder.split("/")
        sub_cat = parts[2] if len(parts) > 2 else cat
        
        item = {
            "id": m.get("id", os.path.basename(folder)),
            "name": m.get("name", os.path.basename(folder)),
            "kind": "phu_kien",
            "brand": m.get("manufacturer", "Cơ khí phụ kiện"),
            "category": cat,
            "sub_category": sub_cat,
            "folder": rel_folder,
            "cad": f"{rel_folder}/cad.dxf" if os.path.exists(os.path.join(folder, "cad.dxf")) else "",
            "preview": f"{rel_folder}/preview.svg" if os.path.exists(os.path.join(folder, "preview.svg")) else "",
            "reference_cad": f"{rel_folder}/ban_ve_nguon.dxf" if os.path.exists(os.path.join(folder, "ban_ve_nguon.dxf")) else "",
            "dimensions": {
                "w": round(extent.get("width", 0), 1),
                "h": round(extent.get("height", 0), 1)
            }
        }
        phu_kien_list.append(item)
    except Exception as e:
        pass

print(f"Collected {len(phu_kien_list)} phu_kien CAD assets.")

# 5. Dang su dung (Curated active set)
dang_su_dung_list = []
for mf in glob(os.path.join(base, "dang_su_dung", "**", "metadata.json"), recursive=True):
    try:
        with open(mf, "r", encoding="utf-8") as f:
            m = json.load(f)
        folder = os.path.dirname(mf)
        rel_folder = os.path.relpath(folder, base).replace("\\", "/")
        
        item = {
            "id": m.get("id", os.path.basename(folder)),
            "name": m.get("name", os.path.basename(folder)),
            "kind": "dang_su_dung",
            "brand": m.get("manufacturer", "Chuẩn hóa"),
            "category": m.get("category", "Đang sử dụng"),
            "folder": rel_folder,
            "cad": f"{rel_folder}/cad.dxf" if os.path.exists(os.path.join(folder, "cad.dxf")) else "",
            "preview": f"{rel_folder}/preview.svg" if os.path.exists(os.path.join(folder, "preview.svg")) else "",
            "reference_cad": f"{rel_folder}/ban_ve_nguon.dxf" if os.path.exists(os.path.join(folder, "ban_ve_nguon.dxf")) else "",
            "status": "verified_standard"
        }
        dang_su_dung_list.append(item)
    except Exception as e:
        pass

print(f"Collected {len(dang_su_dung_list)} curated dang_su_dung assets.")

# 6. All Catalog Products (1498 SKUs)
products_list = []
catalog_data_path = os.path.join(base, "catalog_data.json")
if os.path.exists(catalog_data_path):
    with open(catalog_data_path, "r", encoding="utf-8") as f:
        cat_data = json.load(f)
    
    # Map each SKU to its variant folder if possible
    for idx, p in enumerate(cat_data):
        sku = p.get("ma", f"SKU_{idx}")
        brand_raw = p.get("brand_display") or p.get("brand", "Chưa rõ")
        series = p.get("series", "Default")
        cat = p.get("t", "Thiết bị")
        poles = p.get("p")
        
        # Link to brand group if available
        matched_group = None
        for g in brand_groups:
            if g["brand"].lower() in brand_raw.lower() or brand_raw.lower() in g["brand"].lower():
                if g["series"].lower() == series.lower():
                    if poles and f"{poles}P" == g["variant"]:
                        matched_group = g
                        break
                        
        products_list.append({
            "id": f"sku_{idx}",
            "sku": sku,
            "name": p.get("n", sku),
            "kind": "products",
            "brand": brand_raw,
            "category": cat,
            "series": series,
            "poles": poles,
            "in_A": p.get("in"),
            "icu_kA": p.get("icu"),
            "price_vnd": p.get("g", 0),
            "dimensions": {
                "w": p.get("w"),
                "h": p.get("h"),
                "d": p.get("d"),
                "pitch": p.get("pitch"),
                "pole_w": p.get("pole_w")
            },
            "cad": matched_group["cad"] if matched_group else "",
            "preview": matched_group["preview"] if matched_group else "",
            "folder": matched_group["folder"] if matched_group else ""
        })

print(f"Collected {len(products_list)} catalog product SKUs.")

# Construct master database
db = {
    "generated_at": "2026-09-26",
    "summary": {
        "brand_groups": len(brand_groups),
        "thiet_bi": len(thiet_bi_list),
        "form_tu": len(form_tu_list),
        "phu_kien": len(phu_kien_list),
        "dang_su_dung": len(dang_su_dung_list),
        "products": len(products_list),
        "total_cad_dxf": len(glob(os.path.join(base, "**", "*.dxf"), recursive=True)),
        "total_svg": len(glob(os.path.join(base, "**", "*.svg"), recursive=True))
    },
    "brand_groups": brand_groups,
    "thiet_bi": thiet_bi_list,
    "form_tu": form_tu_list,
    "phu_kien": phu_kien_list,
    "dang_su_dung": dang_su_dung_list,
    "products": products_list
}

# Save as data.js
js_content = "window.TUDIEN_DB = " + json.dumps(db, ensure_ascii=False, separators=(',', ':')) + ";"
data_js_path = os.path.join(base, "data.js")
with open(data_js_path, "w", encoding="utf-8") as f:
    f.write(js_content)
    
print(f"Written data.js ({os.path.getsize(data_js_path) / 1024:.1f} KB).")
