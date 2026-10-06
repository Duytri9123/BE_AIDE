"""Build one machine-readable equipment/CAD catalog from all published tables.

Price rows remain distinct from CAD-only devices and source CAD candidates.
Manufacturer identity is never inferred from a drawing's neighboring region.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
OUT=ROOT/'THU_VIEN_THIET_BI_AI_2026'
OUT.mkdir(exist_ok=True)
PUBLISHED_SOURCES=json.loads((ROOT/'brand_prices_2026.json').read_text(encoding='utf-8'))
SOURCES=[(entry['brand'],entry['folder'],entry['data_file'],'index.html')
         for entry in PUBLISHED_SOURCES]

def read(rel): return json.loads((ROOT/rel).read_text(encoding='utf-8'))
def write(name,value):
    target=OUT/name
    temp=target.with_suffix(target.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temp.replace(target)
def jsonl(name,items):
    target=OUT/name; temp=target.with_suffix(target.suffix+'.tmp')
    with temp.open('w',encoding='utf-8',newline='\n') as file:
        for item in items: file.write(json.dumps(item,ensure_ascii=False,separators=(',',':'))+'\n')
    temp.replace(target)
def normalized(s):
    return ''.join(c for c in unicodedata.normalize('NFD',str(s or '')) if unicodedata.category(c)!='Mn').casefold()
def path_ref(folder,value):
    if not value or not isinstance(value,str) or value.startswith(('http://','https://')):
        return None
    path=(ROOT/folder/value.replace('\\','/')).resolve()
    try: return path.relative_to(ROOT.resolve()).as_posix()
    except ValueError: return None
def file_asset(folder,value):
    ref=path_ref(folder,value)
    return {'path':ref,'exists':bool(ref and (ROOT/ref).is_file())} if ref else None
def pole_count(value):
    if isinstance(value,int):return value
    m=re.search(r'\b([1-4])\s*P\b',str(value or ''),re.I)
    return int(m.group(1)) if m else None
def amperes(value):
    s=str(value or '').strip()
    return float(re.fullmatch(r'(\d+(?:[.,]\d+)?)\s*A?',s,re.I).group(1).replace(',','.')) if re.fullmatch(r'\d+(?:[.,]\d+)?\s*A?',s,re.I) else None
def text_of(*values):
    return ' '.join(str(x) for x in values if x is not None and str(x).strip())

records=[]
inputs=['index_2026.html','brand_prices_2026.json']
for brand,folder,filename,page in SOURCES:
    dataset=f'{folder}/{filename}'; inputs.append(dataset)
    rows=read(dataset)
    published=next(entry for entry in PUBLISHED_SOURCES if entry['brand']==brand)
    if len(rows)!=published['display_rows']:
        raise ValueError(f'{dataset}: {len(rows)} rows, index declares {published["display_rows"]}')
    for index,row in enumerate(rows,1):
        model=str(row.get('model') or row.get('name_pdf') or '').strip()
        category=str(row.get('category') or row.get('section_pdf') or '').strip()
        name=str(row.get('name_pdf') or row.get('description_display') or model).strip()
        current=row.get('in_a_pdf') or row.get('current_a_pdf') or row.get('current_display')
        poles=pole_count(row.get('poles_pdf') or row.get('pole_display'))
        material=row.get('material_code')
        price_amount=row.get('price_vnd_ex_vat') if brand=='LS' else row.get('price_vnd')
        vat=False if brand=='LS' else row.get('price_includes_vat')
        cad_dwg=file_asset(folder,row.get('cad_dwg'))
        cad_dxf=file_asset(folder,row.get('cad_dxf'))
        cad_preview=file_asset(folder,row.get('cad_preview'))
        has_cad=bool(cad_dxf and cad_dxf['exists'])
        basis=row.get('cad_match_basis') or row.get('cad_basis')
        level=row.get('cad_match_level')
        status=('exact_model_cad' if has_cad and level=='exact' else
                'family_or_frame_cad' if has_cad and basis else
                'cad_present_match_unstated' if has_cad else
                'manufacturer_data_no_cad' if row.get('product_evidence_url') else 'no_verified_cad')
        warnings=[]
        if status=='family_or_frame_cad':warnings.append('CAD matches a family/frame/state; the drawing label may differ from this price SKU.')
        if not has_cad:warnings.append('No verified CAD is linked to this price row.')
        if cad_dxf and not cad_dxf['exists']:warnings.append('Linked CAD DXF is missing.')
        source_url=row.get('source_url') or row.get('product_evidence_url')
        rec={'catalog_id':f'{brand.upper().replace("-","")}-PRICE-{int(row.get("row_id") or index):05}',
             'record_type':'priced_variant','brand':brand,'brand_status':'price_document',
             'category':category,'model':model,'material_code':material,'display_name':name,
             'description':text_of(row.get('product_description'),row.get('description_display'),row.get('detail_pdf'),row.get('spec_display')),
             'specifications':{'poles':poles,'current_a':amperes(current),'current_display':current,
                               'breaking_capacity_ka':row.get('icu_ka_pdf'),
                               'voltage_display':row.get('icu_voltage_pdf'),
                               'dimensions_mm':{'visible_front':row.get('cad_visible_front_mm')} if row.get('cad_visible_front_mm') else None},
             'price':{'amount_vnd':price_amount,'vat_included':vat,'effective_date':row.get('effective_date'),
                      'source_document':row.get('source_pdf') or row.get('source'),
                      'source_url':source_url,'page':row.get('page')} if price_amount is not None else None,
             'cad':{'status':status,'match_basis':basis,'source_id':row.get('cad_source_id') or row.get('cad_device_id'),
                    'state_id':row.get('cad_state_id') or row.get('cad_variant_id'),
                    'dwg':cad_dwg,'dxf':cad_dxf,'preview':cad_preview,'views':[]},
             'source_record':{'dataset':dataset,'row_id':row.get('row_id') or index,'table_page':f'{folder}/{page}'},
             'evidence':{'product_url':row.get('product_evidence_url'),'cad_url':row.get('cad_evidence_url'),
                         'price_url':source_url},'warnings':warnings,'source_data':row}
        records.append(rec)

for published in PUBLISHED_SOURCES:
    linked=sum(rec['brand']==published['brand'] and rec['record_type']=='priced_variant'
               and rec['cad']['status'] in ('exact_model_cad','family_or_frame_cad','cad_present_match_unstated')
               for rec in records)
    if linked!=published['rows_with_cad']:
        raise ValueError(f'{published["brand"]}: {linked} linked CAD rows, index declares {published["rows_with_cad"]}')

ls_supp='LS_D02_DU_LIEU_MOI/cad_bo_sung.json';inputs.append(ls_supp)
for item in read(ls_supp)['items']:
    has_cad=bool(item.get('cad_dxf'))
    records.append({'catalog_id':item['id'],'record_type':'manufacturer_or_cad_reference','brand':'LS',
        'brand_status':'manufacturer_catalog_and_source_drawing','category':item['type'],
        'model':item['name'].split(' · ')[0],'material_code':None,'display_name':item['name'],
        'description':item['note'],'specifications':{'poles':item.get('poles'),'current_a':40 if item['id']=='LS-GMC-40P2-TSBS' else None,
            'current_display':'40A' if item['id']=='LS-GMC-40P2-TSBS' else None,
            'breaking_capacity_ka':None,'voltage_display':None,
            'dimensions_mm':{'outer_whd':item.get('outer_whd_mm'),'visible_front':item.get('visible_front_mm'),
                             'basis':item.get('dimension_basis')}},
        'price':None,'cad':{'status':'source_cad_family' if has_cad else 'manufacturer_dimensions_no_cad',
            'match_basis':item['cad_basis'],'source_id':item['id'],'state_id':None,
            'dwg':file_asset('LS_D02_DU_LIEU_MOI',item.get('cad_dwg')),
            'dxf':file_asset('LS_D02_DU_LIEU_MOI',item.get('cad_dxf')),
            'preview':file_asset('LS_D02_DU_LIEU_MOI',item.get('preview')),
            'views':[{'page':'LS_D02_DU_LIEU_MOI/'+item['views']}] if item.get('views') else []},
        'source_record':{'dataset':ls_supp,'row_id':item['id'],'table_page':'LS_D02_DU_LIEU_MOI/cad_bo_sung.html'},
        'evidence':{'product_url':item['official_source'],'cad_url':None,'price_url':None},
        'warnings':[item['cad_basis'],item['note']],'source_data':item})

other_file='THIET_BI_KHAC_2026/products.json';inputs.append(other_file)
for product in read(other_file)['products']:
    views=[]
    for view in product['views']:
        analysis=view.get('analysis') or {}
        views.append({'id':view['id'],'name':view['name'],'state':view.get('state'),
                      'face_evidence':analysis.get('face_evidence'),
                      'drawing_bounds':analysis.get('bounds_drawing_units'),
                      'dynamic_states':analysis.get('dynamic_visibility_states') or [],
                      'dxf':file_asset('THIET_BI_KHAC_2026',view.get('dxf')),
                      'preview':file_asset('THIET_BI_KHAC_2026',view.get('preview'))})
    first=views[0] if views else {}
    rec={'catalog_id':'OTHER-'+product['id'],'record_type':'source_cad_device_or_assembly',
         'brand':product.get('brand') or None,'brand_status':product.get('brand_evidence') or 'unverified',
         'category':product['category'],'model':product['model'],'material_code':None,
         'display_name':text_of(product['type'],product['model']),
         'description':product.get('cad_info') or product.get('source_group') or '',
         'specifications':{'poles':None,'current_a':None,'current_display':None,
                           'breaking_capacity_ka':None,'voltage_display':None,'dimensions_mm':None},
         'price':None,'cad':{'status':'source_cad_unverified_sku','match_basis':product['status'],
                            'source_id':product['id'],'state_id':None,'dwg':None,
                            'dxf':first.get('dxf'),'preview':first.get('preview'),'views':views},
         'source_record':{'dataset':other_file,'row_id':product['id'],
                          'table_page':f'THIET_BI_KHAC_2026/{product["category"]}.html'},
         'evidence':{'product_url':(product.get('external') or {}).get('url'),
                     'cad_url':None,'price_url':None},
         'warnings':['CAD geometry is not proof of an exact manufacturer SKU.'] if not product.get('external') else [],
         'source_data':product}
    records.append(rec)

ids=[r['catalog_id'] for r in records]
assert len(ids)==len(set(ids)), 'Catalog IDs must be unique'
jsonl('equipment_catalog.jsonl',records)

grouped=defaultdict(list)
for rec in records:
    key=(rec['brand'] or 'UNVERIFIED',normalized(rec['category']),normalized(rec['model']))
    grouped[key].append(rec)
groups=[]
for (brand,_,_),items in sorted(grouped.items()):
    prices=[x['price']['amount_vnd'] for x in items if x['price'] and isinstance(x['price']['amount_vnd'],(int,float))]
    groups.append({'group_id':'GROUP-'+hashlib.sha1('|'.join((brand,items[0]['category'],items[0]['model'])).encode()).hexdigest()[:14],
        'brand':None if brand=='UNVERIFIED' else brand,'category':items[0]['category'],'model':items[0]['model'],
        'variant_count':len(items),'catalog_ids':[x['catalog_id'] for x in items],
        'price_range_vnd':[min(prices),max(prices)] if prices else None,
        'cad_statuses':sorted({x['cad']['status'] for x in items})})
jsonl('equipment_groups.jsonl',groups)

inventory_file='full_accessory_cad_inventory.json';inputs.append(inventory_file)
inventory=read(inventory_file)
by_path=defaultdict(list)
for rec in records:
    cad=rec['cad']
    for kind in ('dwg','dxf','preview'):
        asset=cad.get(kind)
        if asset and asset['path']:by_path[asset['path']].append(rec['catalog_id'])
    for view in cad['views']:
        for kind in ('dxf','preview'):
            asset=view.get(kind)
            if isinstance(asset,dict) and asset['path']:by_path[asset['path']].append(rec['catalog_id'])
asset_rows={}
for entry in inventory['records']:
    p=entry.get('cad_dxf')
    if not p:continue
    ref=path_ref('',p)
    if not ref:continue
    asset_rows[ref]={'asset_id':'CAD-'+hashlib.sha1(ref.encode()).hexdigest()[:16],
        'path':ref,'exists':(ROOT/ref).is_file(),'kind':entry['kind'],'zone':entry.get('zone'),
        'brand_claim':entry.get('brand'),'name_in_drawing':entry.get('name'),
        'source_inventory_id':entry['id'],'status':entry.get('status'),
        'matched_catalog_ids':sorted(set(by_path.get(ref,[])))}
for ref,linked in by_path.items():
    if ref not in asset_rows:
        asset_rows[ref]={'asset_id':'CAD-'+hashlib.sha1(ref.encode()).hexdigest()[:16],
            'path':ref,'exists':(ROOT/ref).is_file(),
            'kind':Path(ref).suffix.lower().lstrip('.'),'zone':None,'brand_claim':None,
            'name_in_drawing':None,'source_inventory_id':None,'status':'linked_from_equipment_record',
            'matched_catalog_ids':sorted(set(linked))}
jsonl('cad_assets.jsonl',sorted(asset_rows.values(),key=lambda x:x['path']))

schema={'$schema':'https://json-schema.org/draft/2020-12/schema','title':'AIDE equipment catalog record',
    'type':'object','required':['catalog_id','record_type','brand','model','specifications','price','cad','source_record','evidence','warnings'],
    'properties':{'catalog_id':{'type':'string'},'record_type':{'enum':['priced_variant','manufacturer_or_cad_reference','source_cad_device_or_assembly']},
        'brand':{'type':['string','null']},'category':{'type':'string'},'model':{'type':'string'},
        'material_code':{'type':['string','null']},'display_name':{'type':'string'},
        'specifications':{'type':'object'},'price':{'type':['object','null']},
        'cad':{'type':'object','required':['status','views']},'source_record':{'type':'object'},
        'evidence':{'type':'object'},'warnings':{'type':'array','items':{'type':'string'}},
        'source_data':{'type':'object'}}}
write('equipment_catalog.schema.json',schema)

db_path=OUT/'equipment_catalog.sqlite';temp_db=OUT/'equipment_catalog.sqlite.tmp'
if temp_db.exists():temp_db.unlink()
con=sqlite3.connect(temp_db)
con.executescript('''CREATE TABLE equipment(catalog_id TEXT PRIMARY KEY,brand TEXT,category TEXT,model TEXT,
display_name TEXT,record_type TEXT,price_vnd INTEGER,cad_status TEXT,record_json TEXT NOT NULL);
CREATE VIRTUAL TABLE equipment_fts USING fts5(catalog_id UNINDEXED,brand,category,model,display_name,description,tokenize='unicode61 remove_diacritics 2');
CREATE TABLE cad_assets(asset_id TEXT PRIMARY KEY,path TEXT,kind TEXT,status TEXT,asset_json TEXT NOT NULL);
CREATE INDEX equipment_brand_model ON equipment(brand,model);''')
for rec in records:
    price=rec['price']['amount_vnd'] if rec['price'] else None
    con.execute('INSERT INTO equipment VALUES(?,?,?,?,?,?,?,?,?)',
        (rec['catalog_id'],rec['brand'],rec['category'],rec['model'],rec['display_name'],rec['record_type'],
         price,rec['cad']['status'],json.dumps(rec,ensure_ascii=False)))
    con.execute('INSERT INTO equipment_fts VALUES(?,?,?,?,?,?)',
        (rec['catalog_id'],rec['brand'],rec['category'],rec['model'],rec['display_name'],rec['description']))
for asset in asset_rows.values():
    con.execute('INSERT INTO cad_assets VALUES(?,?,?,?,?)',
                (asset['asset_id'],asset['path'],asset['kind'],asset['status'],json.dumps(asset,ensure_ascii=False)))
con.commit();con.close();temp_db.replace(db_path)

source_hashes={rel:hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in inputs}
counts=Counter(rec['brand'] or 'Unverified' for rec in records)
record_types=Counter(rec['record_type'] for rec in records)
cad_statuses=Counter(rec['cad']['status'] for rec in records)
manifest={'schema_version':'1.0.0','generated_at_utc':datetime.now(timezone.utc).isoformat(),
    'path_base':'Tudien/CATALOG_PHU_KIEN_DOC_LAP','equipment_records':len(records),
    'product_groups':len(groups),'cad_asset_records':len(asset_rows),
    'price_rows_by_brand':{brand:sum(r['brand']==brand and r['record_type']=='priced_variant' for r in records) for brand,_,_,_ in SOURCES},
    'records_by_brand':dict(counts),'records_by_type':dict(record_types),
    'cad_status_counts':dict(cad_statuses),'missing_asset_paths':[a['path'] for a in asset_rows.values() if not a['exists']],
    'source_sha256':source_hashes,'files':{'equipment':'equipment_catalog.jsonl','groups':'equipment_groups.jsonl',
        'cad_assets':'cad_assets.jsonl','sqlite':'equipment_catalog.sqlite','schema':'equipment_catalog.schema.json'}}
write('manifest.json',manifest)

summaries=[{'id':r['catalog_id'],'brand':r['brand'] or 'Chưa xác minh','model':r['model'],
            'category':r['category'],'price':r['price']['amount_vnd'] if r['price'] else None,
            'cad':r['cad']['status'],'cad_path':(r['cad']['dxf'] or {}).get('path'),
            'table':r['source_record']['table_page']} for r in records]
embedded=json.dumps(summaries,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
page='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Thư viện thiết bị AIDE 2026</title>
<style>body{margin:0;background:#edf3f7;color:#17344a;font:14px/1.5 system-ui}main{max-width:1500px;margin:auto;padding:18px}header,.panel{background:white;border:1px solid #cbdbe5;border-radius:9px;padding:16px;margin-bottom:12px}h1{margin:0 0 7px}a{color:#075e9f}input,select{padding:9px;border:1px solid #adc4d3;border-radius:5px;font:inherit}.filters{display:flex;gap:8px;flex-wrap:wrap}.filters input{min-width:270px;flex:1}table{width:100%;border-collapse:collapse}th,td{border-bottom:1px solid #d9e4ec;padding:8px;text-align:left;vertical-align:top}th{background:#e5edf3;position:sticky;top:0}.muted{color:#667f90}small{display:block;color:#607589}</style>
<main><header><h1>Thư viện thiết bị và CAD dùng chung</h1><p>Sáu bảng hãng, các thiết bị CAD khác và hai mục LS bổ sung trong một catalog máy đọc. Mỗi dòng giữ đường dẫn nguồn, căn cứ ghép CAD và trạng thái xác minh. Bản ghi CAD chưa rõ SKU được tách khỏi dòng giá.</p><p><a href="equipment_catalog.jsonl">Tải JSONL thiết bị</a> · <a href="equipment_groups.jsonl">Nhóm model</a> · <a href="cad_assets.jsonl">Chỉ mục mọi CAD</a> · <a href="equipment_catalog.sqlite">SQLite tìm kiếm</a> · <a href="equipment_catalog.schema.json">Schema</a> · <a href="manifest.json">Manifest</a> · <a href="README.md">Hướng dẫn AI</a> · <a href="../index_2026.html">Các bảng gốc</a></p><p id="count"></p></header>
<section class="panel"><div class="filters"><input id="q" placeholder="Tìm model, mã hoặc loại thiết bị…"><select id="brand"><option value="">Mọi hãng</option></select><select id="cad"><option value="">Mọi trạng thái CAD</option><option value="has">Có CAD</option><option value="none">Chưa có CAD</option></select></div><table><thead><tr><th>Hãng</th><th>Thiết bị/model</th><th>Loại</th><th>Giá VNĐ</th><th>CAD</th><th>Nguồn</th></tr></thead><tbody id="rows"></tbody></table></section></main>
<script>const data=__DATA__;const q=document.querySelector('#q'),b=document.querySelector('#brand'),c=document.querySelector('#cad'),body=document.querySelector('#rows'),count=document.querySelector('#count');const esc=s=>String(s??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));const norm=s=>String(s??'').normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();[...new Set(data.map(x=>x.brand))].sort().forEach(x=>b.insertAdjacentHTML('beforeend',`<option>${esc(x)}</option>`));function render(){let list=data.filter(x=>(!b.value||x.brand===b.value)&&(!c.value||(c.value==='has'?!!x.cad_path:!x.cad_path))&&norm([x.brand,x.model,x.category,x.id].join(' ')).includes(norm(q.value)));count.textContent=`${list.length} / ${data.length} bản ghi · hiển thị tối đa 150 dòng`;body.innerHTML=list.slice(0,150).map(x=>`<tr><td>${esc(x.brand)}</td><td><b>${esc(x.model)}</b><small>${esc(x.id)}</small></td><td>${esc(x.category)}</td><td>${x.price==null?'—':Number(x.price).toLocaleString('vi-VN')}</td><td>${x.cad_path?`<a href="../${esc(x.cad_path)}">DXF</a>`:'—'}<small>${esc(x.cad)}</small></td><td><a href="../${esc(x.table)}">Bảng gốc</a></td></tr>`).join('')};q.oninput=b.onchange=c.onchange=render;render()</script></html>'''.replace('__DATA__',embedded)
(OUT/'index.html').write_text(page,encoding='utf-8')
readme='''# Thư viện thiết bị AIDE 2026 cho AI

`equipment_catalog.jsonl` là bản sao máy đọc được của `index_2026.html` và các bảng dữ liệu mà trang này dẫn tới. Mỗi dòng có `catalog_id` bền vững. Mitsubishi dùng 1.976 dòng hiển thị đã gộp; `source_data.source_variants` giữ các biến thể gốc. `equipment_groups.jsonl` nhóm các dòng theo hãng/loại/model. `cad_assets.jsonl` lập chỉ mục CAD được bảng thiết bị dẫn tới.

Đường dẫn `path` đều tương đối với `Tudien/CATALOG_PHU_KIEN_DOC_LAP`. AI nên dùng `record_type`, `cad.status`, `cad.match_basis` và `warnings` trước khi chọn thiết bị. `family_or_frame_cad` không chứng minh đúng SKU; `source_cad_unverified_sku` chỉ chứng minh bản vẽ nguồn. Giá `null` nghĩa là chưa có dòng giá trong tài liệu đang dùng.

SQLite có bảng `equipment`, `cad_assets` và chỉ mục toàn văn `equipment_fts`. Ví dụ: `SELECT e.catalog_id,e.model,e.cad_status FROM equipment_fts f JOIN equipment e ON e.catalog_id=f.catalog_id WHERE equipment_fts MATCH 'BKN';`. Xem `manifest.json` để kiểm tra phiên bản, số bản ghi và SHA-256 của từng dữ liệu nguồn.

Tra cứu cho AI: `python BE_AIDE/scripts/query_equipment_library.py BKN --brand LS --cad available --limit 10` trả về JSON chứa đầy đủ thông số, giá, căn cứ CAD và đường dẫn nguồn. Kiểm tra: `python BE_AIDE/scripts/verify_equipment_library.py`.

Backend đọc trực tiếp SQLite qua `app.services.equipment_library`. API: `GET /api/v1/equipment-library/manifest`, `GET /api/v1/equipment-library/search?q=BKN&brand=LS` và `GET /api/v1/equipment-library/{catalog_id}`. Bộ xử lý giá chỉ dùng dòng PDF 2026 khi mã và các thông số yêu cầu dẫn tới đúng một biến thể; các dòng còn mơ hồ giữ nguyên trạng thái cần đối chiếu. Trường `cad.status` luôn đi kèm kết quả.

Các file `BE_AIDE/data/catalog_data.json`, `catalog_accessories.json`, `cad_device_registry.json` và dữ liệu `device_layouts` là nguồn cũ; không dùng để tự chọn mã, giá, kích thước hay hình chèn. API CAD cũ chỉ công bố các bản ghi có `exact_model_cad` từ catalog 2026 và có file nguồn hiện diện.

Bản sao dữ liệu máy đọc được và các CAD mà catalog tham chiếu được lưu trong `BE_AIDE/data/equipment_library_2026` để backend vẫn tra cứu và mở CAD khi chỉ checkout repository backend. API bổ sung `available_now` trên mỗi đường dẫn CAD để báo tệp có thực sự hiện diện ở môi trường đang chạy hay không.

Chạy lại: `python BE_AIDE/scripts/build_equipment_library.py` sau khi cập nhật các bảng hãng hoặc `THIET_BI_KHAC_2026/products.json`.
'''
(OUT/'README.md').write_text(readme,encoding='utf-8')

# Keep a portable catalog snapshot and its referenced CAD in the backend.
backend_out=Path(__file__).resolve().parents[1]/'data/equipment_library_2026'
backend_out.mkdir(exist_ok=True)
for filename in ('equipment_catalog.jsonl','equipment_groups.jsonl','cad_assets.jsonl',
                 'equipment_catalog.sqlite','equipment_catalog.schema.json','manifest.json','README.md'):
    shutil.copy2(OUT/filename,backend_out/filename)
shutil.copy2(ROOT/'index_2026.html',backend_out/'source_index_2026.html')

# Bundle every CAD file referenced by the published catalog so the backend
# can serve the same drawings without a sibling Tudien checkout.
referenced_paths=set()
for rec in records:
    cad=rec['cad']
    for ref in (cad.get('dwg'),cad.get('dxf'),cad.get('preview')):
        if ref:referenced_paths.add(ref['path'])
    for view in cad.get('views',[]):
        for ref in (view.get('dxf'),view.get('preview')):
            if isinstance(ref,dict):referenced_paths.add(ref['path'])
archive=backend_out/'source_cad_assets.zip'
archive_tmp=backend_out/'source_cad_assets.zip.tmp'
with ZipFile(archive_tmp,'w',compression=ZIP_DEFLATED,compresslevel=6) as bundle:
    for relative in sorted(referenced_paths):
        source=ROOT/relative
        if not source.is_file():raise FileNotFoundError(source)
        bundle.write(source,arcname=relative)
archive_tmp.replace(archive)
print(json.dumps({'records':len(records),'groups':len(groups),'cad_assets':len(asset_rows),
                  'missing_assets':len(manifest['missing_asset_paths']),
                  'bundled_cad_assets':len(referenced_paths)},ensure_ascii=False))
