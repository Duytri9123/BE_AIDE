import json
import os
import re
from collections import defaultdict

def sanitize_filename(name):
    if not name:
        return "Unknown"
    return re.sub(r'[<>:"/\\|?*]', '_', str(name)).strip()

def normalize_brand(brand):
    if not brand: return "Unknown"
    b = brand.lower()
    if 'ls' in b: return "LS"
    if 'chint' in b: return "CHINT"
    if 'schneider' in b: return "Schneider"
    if 'mitsubishi' in b: return "Mitsubishi"
    if 'cnc' in b: return "CNC"
    return sanitize_filename(brand)

def main():
    catalog_path = r'e:\duytristool\AIDE_website\BE_AIDE\data\catalog_data.json'
    out_dir = r'e:\duytristool\AIDE_website\BE_AIDE\data\thu_vien_tu_dien_v2\tudien'
    
    with open(catalog_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # Group items
    # Structure: Brand -> Type -> Series -> Variant -> { "items": [], "dimensions": {...} }
    catalog_tree = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))
    
    for item in data:
        brand = normalize_brand(item.get('brand_display', item.get('brand')))
        type_ = sanitize_filename(item.get('t', 'Khac'))
        series = sanitize_filename(item.get('series', 'Default_Series'))
        
        # Determine variant
        variant = "Default"
        if 'p' in item and item['p']:
            variant = f"{item['p']}P"
        elif 'Phụ kiện' in type_ or type_ in ['Máng dây', 'Ray DIN']:
            variant = sanitize_filename(item.get('ma', 'Default'))
        else:
            # Fallback if no pole
            if 'w' in item and 'h' in item:
                variant = f"Size_{item['w']}x{item['h']}"
            else:
                variant = sanitize_filename(item.get('ma', 'Default'))
                
        catalog_tree[brand][type_][series][variant].append(item)
        
    # Create directories and write data.json
    for brand, types in catalog_tree.items():
        for type_, series_dict in types.items():
            for series, variants in series_dict.items():
                for variant, items in variants.items():
                    dir_path = os.path.join(out_dir, brand, type_, series, variant)
                    os.makedirs(dir_path, exist_ok=True)
                    
                    # Consolidate data
                    # Assuming items in the same variant share physical size
                    rep = items[0]
                    physical_data = {
                        "w": rep.get("w"),
                        "h": rep.get("h"),
                        "d": rep.get("d"),
                        "pitch": rep.get("pitch"),
                        "pole_w": rep.get("pole_w")
                    }
                    
                    node_data = {
                        "dimensions": physical_data,
                        "variants": [
                            {
                                "sku": it.get("ma"),
                                "name": it.get("n"),
                                "in": it.get("in"),
                                "icu": it.get("icu"),
                                "price": it.get("g")
                            } for it in items
                        ]
                    }
                    
                    with open(os.path.join(dir_path, 'data.json'), 'w', encoding='utf-8') as f:
                        json.dump(node_data, f, ensure_ascii=False, indent=2)

    print(f"Migration completed. Checked {len(data)} items and created structure in {out_dir}")

if __name__ == '__main__':
    main()
