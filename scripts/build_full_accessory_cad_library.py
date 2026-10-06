"""Publish every extracted view and named block from the accessory DWG.

This is a source CAD inventory, not an automatic price-to-product match.
"""
import json
import hashlib
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CAT = ROOT / 'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
SOURCE_DWG = ROOT / 'Tudien/THƯ VIỆN PHỤ KIỆN( Mới nhất).dwg'
VIEWS = CAT / '04_BO_THIET_BI_DXF'
BLOCKS = CAT / '02_BLOCK_VA_THIET_BI'
REGIONS = CAT / '01_THEO_VUNG'
BRAND_ZONES = {'D01': 'Schneider', 'D02': 'LS', 'D03': 'ABB',
               'D04': 'Mitsubishi', 'D05': 'O-Sung', 'D06': 'Shihlin'}


def relative_file(raw):
    if not raw:
        return None
    rel = Path(raw.replace('\\', '/'))
    return rel.as_posix() if (CAT / rel).is_file() else None


rows = []
by_handle = defaultdict(list)
groups = 0
listed_cad = set()
for path in sorted(VIEWS.glob('*/*/thong_tin.json')):
    group = json.loads(path.read_text(encoding='utf8'))
    groups += 1
    zone = group['zone']
    for number, view in enumerate(group.get('views', []), 1):
        cad = relative_file(view.get('file'))
        if not cad:
            raise FileNotFoundError((path, view.get('file')))
        listed_cad.add(cad)
        preview = relative_file(view.get('preview'))
        record = {'id': f"{group['id']}-V{number:03}", 'kind': 'view',
                  'zone': zone, 'brand': BRAND_ZONES.get(zone),
                  'group': group['name'], 'name': view['name'],
                  'cad_dxf': cad, 'preview': preview,
                  'source_group': relative_file(str(path.relative_to(CAT))),
                  'source_handles': view.get('source_handles') or [],
                  'status': view.get('status', 'candidate_view_needs_review'),
                  'entity_count': view.get('entity_count'),
                  'removed_external_title': view.get('removed', {}),
                  'source_block_id': None}
        rows.append(record)
        for handle in record['source_handles']:
            by_handle[handle.upper()].append(record)
    complete = relative_file((group.get('complete_set') or {}).get('file'))
    if complete:
        rows.append({'id': group['id'] + '-COMPLETE', 'kind': 'group',
                     'zone': zone, 'brand': BRAND_ZONES.get(zone),
                     'group': group['name'], 'name': group['name'] + ' · cụm đầy đủ',
                     'cad_dxf': complete, 'preview': None,
                     'source_group': relative_file(str(path.relative_to(CAT))),
                     'source_handles': (group['complete_set'].get('source_handles') or []),
                     'status': 'Cụm gốc đầy đủ, gồm cả chữ và kích thước bối cảnh; chưa coi là một SKU',
                     'entity_count': group['complete_set'].get('entity_count'),
                     'removed_external_title': None, 'source_block_id': None})

for cad_file in sorted(VIEWS.glob('*/*/*_thiet_bi.dxf')):
    cad = cad_file.relative_to(CAT).as_posix()
    if cad in listed_cad:
        continue
    zone = cad_file.relative_to(VIEWS).parts[0]
    preview_file = cad_file.with_suffix('.svg')
    rows.append({'id': f'UNLISTED-{zone}-{cad_file.stem}', 'kind': 'view',
                 'zone': zone, 'brand': BRAND_ZONES.get(zone),
                 'group': cad_file.parent.name, 'name': cad_file.stem,
                 'cad_dxf': cad, 'preview': (preview_file.relative_to(CAT).as_posix()
                                              if preview_file.is_file() else None),
                 'source_group': relative_file(str((cad_file.parent / 'thong_tin.json').relative_to(CAT))),
                 'source_handles': [], 'status': 'DXF đã bóc tách nhưng chưa có dòng view trong metadata cụm',
                 'entity_count': None, 'removed_external_title': None,
                 'source_block_id': None})

region_count = 0
for folder in sorted(REGIONS.iterdir()):
    cad_file = folder / 'hinh_roi_va_chu_nguon.dxf'
    meta_file = folder / 'vung.json'
    if not (cad_file.is_file() and meta_file.is_file()):
        continue
    meta = json.loads(meta_file.read_text(encoding='utf8'))
    zone = meta['zone']
    region_count += 1
    rows.append({'id': zone + '-LOOSE-CONTEXT', 'kind': 'region',
                 'zone': zone, 'brand': BRAND_ZONES.get(zone),
                 'group': folder.name, 'name': 'Hình rời và chữ nguồn · ' + folder.name,
                 'cad_dxf': cad_file.relative_to(CAT).as_posix(), 'preview': None,
                 'source_group': meta_file.relative_to(CAT).as_posix(),
                 'source_handles': [],
                 'status': 'Hình và chữ rời nguyên vùng; dùng để đối chiếu bối cảnh, không coi là CAD một thiết bị',
                 'entity_count': meta.get('loose_entities'),
                 'removed_external_title': None, 'source_block_id': None})

block_count = 0
for path in sorted(BLOCKS.glob('*/thong_tin.json')):
    item = json.loads(path.read_text(encoding='utf8'))
    cad = relative_file(item.get('cad', {}).get('path'))
    if not cad:
        raise FileNotFoundError((path, item.get('cad', {}).get('path')))
    block_count += 1
    zones = item.get('zones') or []
    zone = zones[0] if zones else None
    mentions = [x['name'] for x in item.get('brand_mentions', [])
                if isinstance(x, dict) and x.get('name')]
    brand = BRAND_ZONES.get(zone) or (mentions[0] if len(set(mentions)) == 1 else None)
    matches = []
    for occurrence in item.get('occurrences') or []:
        matches += by_handle.get(str(occurrence.get('handle', '')).upper(), [])
    matches = list({m['id']: m for m in matches}.values())
    preview = next((m['preview'] for m in matches if m['preview']), None)
    rows.append({'id': item['id'], 'kind': 'block', 'zone': zone,
                 'brand': brand, 'group': ', '.join(zones),
                 'name': item.get('display_name') or item.get('source_block_name'),
                 'cad_dxf': cad, 'preview': preview,
                 'source_group': relative_file(str(path.relative_to(CAT))),
                 'source_handles': [o.get('handle') for o in item.get('occurrences') or []],
                 'status': 'CAD block nguồn; chưa tự động ghép SKU',
                 'entity_count': item.get('definition_entities'),
                 'removed_external_title': None,
                 'source_block_id': item.get('source_block_name'),
                 'text_evidence': item.get('text_evidence', [])[:12],
                 'brand_mentions': mentions,
                 'matched_view_ids': [m['id'] for m in matches],
                 'placed_count': item.get('placed_count', 0)})

assert groups == 284 and block_count == 1171, (groups, block_count)
view_count = sum(r['kind'] == 'view' for r in rows)
complete_count = sum(r['kind'] == 'group' for r in rows)
assert view_count == 1049 and complete_count == 267 and region_count == 52, (view_count, complete_count, region_count)
assert len({r['id'] for r in rows}) == len(rows)

inventory = {'source_dwg': str(SOURCE_DWG),
             'source_dwg_sha256': hashlib.sha256(SOURCE_DWG.read_bytes()).hexdigest(),
             'scope': 'DXF views and named blocks extracted from the original DWG',
             'spatial_groups': groups, 'source_regions': 64,
             'loose_region_drawings': region_count, 'views': view_count,
             'complete_group_drawings': complete_count, 'named_blocks': block_count,
             'total_records': len(rows),
             'by_zone': dict(sorted(Counter(r['zone'] or 'Không gán vùng' for r in rows).items())),
             'by_brand': dict(sorted(Counter(r['brand'] for r in rows if r['brand']).items())),
             'records': rows}
(CAT / 'full_accessory_cad_inventory.json').write_text(
    json.dumps(inventory, ensure_ascii=False, indent=2) + '\n', encoding='utf8')

data = json.dumps(rows, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
page = '''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Toàn bộ CAD thư viện phụ kiện</title>
<style>*{box-sizing:border-box}body{margin:0;background:#edf2f6;color:#173044;font:14px system-ui}main{max-width:1700px;margin:auto;padding:18px}header{background:white;border:1px solid #cbd9e3;border-radius:10px;padding:18px}h1{margin:0 0 8px}p{line-height:1.5}.controls{display:flex;gap:8px;flex-wrap:wrap;padding:12px 0;position:sticky;top:0;background:#edf2f6;z-index:4}input,select{font:inherit;padding:9px;border:1px solid #afc4d5;border-radius:6px;background:white}input{flex:1;min-width:260px}a{color:#075e9f}.wrap{overflow:auto;background:white;border:1px solid #cbd9e3;border-radius:8px}table{width:100%;border-collapse:collapse}th,td{padding:8px;border-bottom:1px solid #dae4eb;vertical-align:top;text-align:left}th{background:#e5edf3}small{display:block;color:#566b7a;line-height:1.4;margin-top:4px}.thumb{width:112px;height:90px;object-fit:contain;background:white;border:1px solid #d9e4ec}.muted{color:#718495}.pager{display:flex;align-items:center;gap:12px;padding:12px 0}button{padding:8px 13px;border:1px solid #a9becd;background:white;border-radius:6px;cursor:pointer}</style>
<main><header><h1>CAD từ “THƯ VIỆN PHỤ KIỆN( Mới nhất).dwg”</h1><p>64 vùng, 284 cụm theo không gian, 1.049 góc nhìn DXF, 267 bản vẽ cụm đầy đủ, 1.171 block và 52 bản DXF hình rời theo vùng. Mỗi dòng dẫn tới DXF đã bóc tách và metadata truy nguồn. “Góc nhìn” chỉ bỏ chữ/title bên ngoài khi bóc tách; hình, đầu cực và chữ nằm trong block được giữ nguyên. Block có thể lặp lại ở nhiều vùng hoặc là chi tiết, ký hiệu, góc nhìn khác của một thiết bị.</p><p>Danh mục nguồn này không tự gán giá hay mã SKU. Chỉ những CAD được đối chiếu hình, chữ và số cực mới ghép vào bảng giá.</p><a href="index_2026.html">← Bảng giá các hãng</a> · <a href="../THƯ VIỆN PHỤ KIỆN( Mới nhất).dwg" download>DWG nguồn</a> · <a href="../bao_cao_thu_vien_phu_kien/thu_vien_phu_kien.dxf" download>DXF toàn bản vẽ</a> · <a href="full_accessory_cad_inventory.json">Dữ liệu kiểm kê</a></header>
<div class="controls"><input id="q" placeholder="Tìm model, block, cụm, chữ CAD..."><select id="brand"><option value="">Mọi hãng</option></select><select id="zone"><option value="">Mọi vùng</option></select><select id="kind"><option value="">Mọi loại CAD</option><option value="view">Góc nhìn DXF</option><option value="group">Cụm đầy đủ</option><option value="block">Block nguồn</option><option value="region">Hình rời từng vùng</option></select><span id="count"></span></div>
<div class="wrap"><table><thead><tr><th>STT</th><th>Vùng / hãng</th><th>Tên trong bản vẽ</th><th>Loại</th><th>Hình gốc</th><th>Tệp nguồn</th><th>Trạng thái</th></tr></thead><tbody id="body"></tbody></table></div><div class="pager"><button id="prev">← Trước</button><span id="pageinfo"></span><button id="next">Sau →</button></div></main>
<script>const rows=__DATA__,e=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const $=s=>document.querySelector(s),q=$('#q'),zone=$('#zone'),brand=$('#brand'),kind=$('#kind');for(const v of [...new Set(rows.map(r=>r.zone).filter(Boolean))].sort())zone.insertAdjacentHTML('beforeend',`<option>${e(v)}</option>`);for(const v of [...new Set(rows.map(r=>r.brand).filter(Boolean))].sort())brand.insertAdjacentHTML('beforeend',`<option>${e(v)}</option>`);const params=new URLSearchParams(location.search);zone.value=params.get('zone')||'';brand.value=params.get('brand')||'';let page=0;function render(){const term=q.value.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();const list=rows.filter(r=>(!zone.value||r.zone===zone.value)&&(!brand.value||r.brand===brand.value)&&(!kind.value||r.kind===kind.value)&&(!term||[r.name,r.group,r.source_block_id,(r.text_evidence||[]).join(' ')].join(' ').normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase().includes(term)));const pages=Math.max(1,Math.ceil(list.length/100));page=Math.min(page,pages-1);$('#count').textContent=`${list.length} / ${rows.length} bản ghi`;$('#pageinfo').textContent=`Trang ${page+1}/${pages}`;$('#prev').disabled=page===0;$('#next').disabled=page>=pages-1;$('#body').innerHTML=list.slice(page*100,page*100+100).map((r,i)=>`<tr><td>${page*100+i+1}</td><td><strong>${e(r.zone||'—')}</strong><small>${e(r.brand||'Chưa xác định hãng')}</small></td><td><strong>${e(r.name)}</strong><small>${e(r.group||'')}</small>${r.text_evidence?.length?`<small>Chữ nguồn: ${e(r.text_evidence.join(' · '))}</small>`:''}</td><td>${r.kind==='view'?'Góc nhìn':r.kind==='group'?'Cụm đầy đủ':r.kind==='region'?'Hình rời vùng':'Block'}</td><td>${r.preview?`<a href="${e(r.preview)}" target="_blank"><img class="thumb" loading="lazy" src="${e(r.preview)}"></a>`:'<span class="muted">Chưa có ảnh xác minh</span>'}</td><td><a href="${e(r.cad_dxf)}" download>DXF</a> · <a href="${e(r.source_group)}" target="_blank">Metadata</a><small>${e(r.id)}</small></td><td>${e(r.status)}${r.kind==='block'&&r.matched_view_ids?.length?`<small>Có ${r.matched_view_ids.length} góc nhìn cùng handle</small>`:''}</td></tr>`).join('')}for(const el of [q,zone,brand,kind])el.addEventListener(el===q?'input':'change',()=>{page=0;render()});$('#prev').onclick=()=>{page--;render()};$('#next').onclick=()=>{page++;render()};render();</script></html>'''.replace('__DATA__', data)
(CAT / 'full_accessory_cad_library.html').write_text(page, encoding='utf8')
print(json.dumps({'regions': region_count, 'groups': groups, 'views': view_count, 'complete_groups': complete_count,
                  'blocks': block_count,
                  'records': len(rows), 'preview_links': sum(bool(r['preview']) for r in rows),
                  'zones': len(inventory['by_zone'])}, ensure_ascii=False))
