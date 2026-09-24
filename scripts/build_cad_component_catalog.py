"""Promote explicitly named CAD components to browsable, unpriced catalog entries."""
import json
import re
import hashlib
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.cad.library_taxonomy import classify, explicit_brands
from app.services.cad.device_families import usable_component
from app.services.cad.recognition import evidence

def component_type(name):
    key = name.casefold()
    for pattern, category in (
        (r'^(banlela|bl012-front|bl012-side|bl036-side|tv-\w*bl)', 'Bản lề'),
        (r'^(den (do|vang|xanh)|warning light)', 'Đèn báo'),
        (r'^(ampere-meter|von-to|von-nho|am-nho|congto)', 'Đồng hồ'),
        (r'^(khoa |khoa[Vv]|khoado|ms722|ms303|ms308|ms325)', 'Khóa tủ'),
        (r'^(bulong|bulon|ecu|tai cau|tai treo|moccau)', 'Phụ kiện cơ khí'),
        (r'^(domino|tb-)', 'Cầu đấu'),
    ):
        if re.search(pattern, key): return category
    for pattern, category in (
        (r'(mccb|mcb|acb|rccb|rcbo|elcb|\bcb\b|\bls \d+af)', 'Thiết bị đóng cắt'),
        (r'(contactor|\bmc ?\d|lc1|ctt)', 'Contactor'),
        (r'(relay|ro le|rơ le|\bmt[- ]?\d)', 'Rơ le'),
        (r'(fan|quat|quạt|filter)', 'Quạt / Tấm lọc'),
        (r'(button|nut|nút|emergency|coi|còi)', 'Nút nhấn / Còi'),
        (r'(fuse|cau chi|cầu chì)', 'Cầu chì'),
        (r'(bien dong|biến dòng|\bct\b)', 'Biến dòng'),
        (r'(ats|apfc|controller|dieu khien)', 'Bộ điều khiển'),
        (r'(meter|dong ho|đồng hồ)', 'Đồng hồ'),
        (r'(busbar|thanh dong|thanh đồng)', 'Busbar'),
    ):
        if re.search(pattern, key): return category
    return 'CAD khác'

if __name__ == '__main__':
    import ezdxf
    from ezdxf.addons.drawing import RenderContext, Frontend, svg, layout
    cache_file = ROOT / 'tmp/cad_geometry_fingerprints.json'
    cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}
    canonical = {}
    rows = []
    for file in sorted((ROOT/'data/device_layouts').glob('*/manifest.json')):
        document = json.loads(file.read_text(encoding='utf8'))
        for item in document['items']:
            category = item.get('category') or component_type(item['name'])
            if not category: continue
            classification = classify(item['name'], category)
            recognition = evidence({**item, **classification})
            classification = {k:recognition.get(k, classification[k]) for k in ('kind','group')}
            if not usable_component({**item, **classification, 'library': file.parent.name, 'category': category}): continue
            brands = explicit_brands(item.get('category', '') + ' ' + item['name'])
            brand = recognition['brand']
            path = file.parent / item['filename']
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest not in cache:
                doc = ezdxf.readfile(path)
                backend = svg.SVGBackend()
                Frontend(RenderContext(doc), backend).draw_layout(doc.modelspace(), finalize=True)
                drawing = backend.get_string(layout.Page(0, 0, layout.Units.mm))
                cache[digest] = hashlib.sha256(drawing.encode()).hexdigest()
            item['geometry_fingerprint'] = cache[digest]
            # Preserve every original entry but point identical drawings to one asset.
            key = (cache[digest], item.get('units'), classification['group'])
            canonical.setdefault(key, item['id'])
            asset_id = item['id']  # Keep identity; family grouping handles duplicate drawings.
            rows.append(dict(ma='CAD:'+item['id'], n=recognition.get('name') or item['name'],
                brand='unspecified' if brand=='Chưa xác định hãng' else brand,
                brand_display=brand, series='Linh kiện CAD · '+file.parent.name,
                t=classification['group'], g=None, _verified=False,
                library_kind=classification['kind'], library_group=classification['group'],
                cad={'asset_id':asset_id}, source={'file':item['source_file'],'block':item['name']},
                note='Hình học CAD nguồn; chưa xác minh model, hướng nhìn và thông số đặt hàng.'))
        file.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding='utf8')
    (ROOT/'data/catalog_cad_components.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
    cache_file.write_text(json.dumps(cache), encoding='utf8')
    print(f'{len(rows)} entries, {len(canonical)} distinct drawings')
