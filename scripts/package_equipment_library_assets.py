"""Bundle CAD previews/DXFs referenced by the active 2026 equipment catalog."""
import json
import re
from html import unescape
import sqlite3
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'Tudien' / 'CATALOG_PHU_KIEN_DOC_LAP'
DATA = ROOT / 'BE_AIDE' / 'data' / 'equipment_library_2026'

with sqlite3.connect(DATA / 'equipment_catalog.sqlite') as db:
    records = [json.loads(row[0]) for row in db.execute('SELECT record_json FROM equipment')]
ls_root = 'LS_D02_DU_LIEU_MOI/'
views_html = (SOURCE / ls_root / 'cad_views.html').read_text(encoding='utf-8')
view_index = {}
for source_id, article in re.findall(r'<article id="([^"]+)">(.*?)</article>', views_html, re.S):
    states = []
    for attrs, label in re.findall(r'<option ([^>]+)>([^<]+)</option>', article):
        attributes = dict(re.findall(r'([\w-]+)="([^"]*)"', attrs))
        if not {'value', 'data-img', 'data-dwg', 'data-dxf'} <= attributes.keys():
            raise ValueError(f'Incomplete CAD view in {source_id}')
        states.append({'id': attributes['value'], 'name': unescape(label),
                       'preview': {'path': ls_root + attributes['data-img']},
                       'dwg': {'path': ls_root + attributes['data-dwg']},
                       'dxf': {'path': ls_root + attributes['data-dxf']}})
    if states:
        view_index[source_id] = states
(DATA / 'manufacturer_cad_views.json').write_text(
    json.dumps(view_index, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
paths = {ref['path'] for record in records
         for ref in (record['cad'].get('preview'), record['cad'].get('dxf'), record['cad'].get('dwg')) if ref}
paths.update(ref['path'] for views in view_index.values() for view in views
             for ref in (view['preview'], view['dxf'], view['dwg']))
paths = sorted(paths)
archive = DATA / 'source_cad_assets.zip'
with ZipFile(archive, 'w', compression=ZIP_DEFLATED, compresslevel=8) as output:
    for relative in paths:
        path = (SOURCE / relative).resolve()
        if not path.is_relative_to(SOURCE.resolve()) or not path.is_file():
            raise FileNotFoundError(relative)
        output.write(path, relative)
print(f'{len(paths)} CAD files copied to {archive} ({archive.stat().st_size:,} bytes)')
print(f'{sum(map(len, view_index.values()))} manufacturer CAD views indexed across {len(view_index)} devices')

# Link a source drawing to a manufacturer's preview only when the text read
# from that drawing matches the source model exactly. This is frame evidence,
# not proof that a priced SKU is the same device.
ls_prices = json.loads((SOURCE / 'LS_D02_DU_LIEU_MOI' / 'price_with_cad.json').read_text(encoding='utf-8'))
price_records = {record['source_record']['row_id']: record for record in records
                 if record['record_type'] == 'priced_variant'
                 and record['source_record']['dataset'] == 'LS_D02_DU_LIEU_MOI/price_with_cad.json'}
normalize = lambda value: re.sub(r'[^a-z0-9]', '', str(value or '').casefold())
links = {}
for record in records:
    if record['record_type'] != 'source_cad_device_or_assembly' or record['brand'] != 'LS':
        continue
    model = normalize(record['model'])
    series = re.match(r'[a-z]+', model)
    candidates = [row for row in ls_prices
                  if normalize(row.get('cad_model_on_drawing')) == model
                  and normalize(row.get('name_pdf')).startswith(series.group() if series else '#')
                  and row.get('row_id') in price_records]
    candidates.sort(key=lambda row: (row.get('poles_pdf') != 3, row['row_id']))
    if candidates:
        related = price_records[candidates[0]['row_id']]
        if related['cad'].get('preview'):
            links[record['catalog_id']] = {'catalog_id': related['catalog_id'],
                                           'model_on_drawing': candidates[0]['cad_model_on_drawing'],
                                           'match_basis': 'Chữ model trên CAD hãng trùng tên khung CAD nguồn; chưa xác minh SKU'}
# These two views were inspected in the original drawing: F01 is the front
# and F02 is the side of the same ABN 400c frame.
for source_id, face in {'OTHER-F01_cluster1-V001': 'Mặt trước CAD nguồn',
                        'OTHER-F02_cluster1-V002': 'Mặt bên CAD nguồn'}.items():
    if source_id in links:
        links[source_id]['source_face_label'] = face
(DATA / 'source_manufacturer_cad_links.json').write_text(
    json.dumps(links, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'{len(links)} source-to-manufacturer frame preview links written')
