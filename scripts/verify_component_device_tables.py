"""Check the device table build against the source CAD inventory."""
import json
import re
from pathlib import Path
from urllib.parse import unquote

base = Path(__file__).resolve().parents[2] / 'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
out = base / 'THIET_BI_KHAC_2026'
inventory = json.loads((base / 'full_accessory_cad_inventory.json').read_text(encoding='utf8'))
result = json.loads((out / 'products.json').read_text(encoding='utf8'))
products = result['products']
source_ids = {r['id'] for r in inventory['records'] if r['kind']=='view' and
              r['zone'] not in {'D01','D02','D03','D04','D05','D06'} and r['zone'] in
              {'A01','A02','A03','A04','A05','A06','A07','A08','A09','A10','A11','A12','A13','A15','A16',
               'B01','B02','B04','B05','B06','B07','C01','C02','C03','C04','C05','C06','C07','C08','C09','C10','C11','C12','C15',
               'D07','D08','D09','E01','E02','E03','E04','E05','E06','E07','E08','F01','F02','F03','F04','F05','F06','F07'}}
used = [source_id for p in products for v in p['views'] for source_id in v['source_ids']]
used_source=[source_id for source_id in used if source_id in source_ids]
assert len(used_source)==len(set(used_source)) and set(used_source)==source_ids, 'A source view was lost or repeated'
extra_ids=set(used)-source_ids
assert extra_ids=={'B_8ce86a6ae65d','B_a9f51566bd67','DATA-PNE-BAR-7','DATA-RED-LIGHT'}, extra_ids
def view_names(model):
    matches = [p for p in products if p['zone']=='C08' and p['model']==model]
    assert len(matches)==1, (model, len(matches))
    return {v['name'] for v in matches[0]['views']}
assert view_names('CML250A') == {'CML250A-2', 'CML250A-3'}
assert view_names('CML3200A') == {'CML3200A-1', 'CML3200A-2', 'CML3200A-3'}
assert view_names('BD1200A') == {'BD1200A-T', 'BD1200A-F', 'BD1200A-S'}
a02 = [p for p in products if p['zone']=='A02']
assert {v['name'] for p in a02 if p['model']=='CT 100/5 A' for v in p['views']} == {'Mặt bằng', 'Mặt hông', 'Mặt đứng'}
assert len([p for p in a02 if p['model']=='CT-600A-VUONG — bố trí các hình']) == 1
assert all('chưa xác định model' in p['model'] and p.get('cad_info')
           for p in a02 if p['id'] in {'A02_abb-V002', 'A02_abb-V003'})
c08_by_view = {v['id']: p for p in products if p['zone']=='C08' for v in p['views']}
assert c08_by_view['C08_cluster4-V001']['brand'] == 'MITEX'
assert c08_by_view['C08_cluster4-V001']['model'] == 'BD01-150/5A'
assert c08_by_view['C08_cluster4-V002']['brand'] == 'MITEX'
assert c08_by_view['C08_cluster7-V003']['brand'] == 'MORELE'
assert c08_by_view['C08_cluster7-V004']['model'] == 'MSQ-40 · 300-600/5A'
assert c08_by_view['C08_cluster7-V001']['brand'] == ''
assert c08_by_view['C08_cluster7-V002']['brand'] == ''
assert {v['id'] for v in c08_by_view['C08_cluster8-V017']['views']} == {
    'C08_cluster8-V015', 'C08_cluster8-V016', 'C08_cluster8-V017'}
assert c08_by_view['C08_cluster8-V017']['brand'] == 'MORELE'
broken_cad = [(p['model'],v['dxf']) for p in products for v in p['views'] if not (out/v['dxf']).exists()]
broken_images = [(p['model'],v['preview']) for p in products for v in p['views'] if v['preview'] and not (out/v['preview']).exists()]
assert not broken_cad and not broken_images, (broken_cad[:3],broken_images[:3])
analysis=json.loads((out/'cad_view_analysis.json').read_text(encoding='utf8'))['views']
assert all(v['id'] in analysis for p in products for v in p['views'] if v['id'] in source_ids)
audit=json.loads((out/'cad_evidence_audit.json').read_text(encoding='utf8'))
assert audit['views_audited']==len(source_ids)
assert {entry['view_id'] for entry in audit['view_evidence']}==source_ids
assert all((base/entry['source_dxf']).exists() for entry in audit['view_evidence'])
full_audit=json.loads((base/'all_cad_view_evidence_audit.json').read_text(encoding='utf8'))
all_view_ids={r['id'] for r in inventory['records'] if r['kind']=='view'}
assert full_audit['views_audited']==len(all_view_ids)==1049
assert {entry['view_id'] for entry in full_audit['view_evidence']}==all_view_ids
pages=list(out.glob('*.html'))+[base/'index_2026.html']
broken_links=[]
for path in pages:
    for href in re.findall(r'(?:href|src)="([^"]+)"',path.read_text(encoding='utf8')):
        if href.startswith(('http:','https:','#','data:')):
            continue
        raw_target, _, fragment = href.partition('#')
        target=path.parent/unquote(raw_target.split('?')[0])
        if not target.exists():
            broken_links.append((path.name,href))
        elif fragment and f'id="{fragment}"' not in target.read_text(encoding='utf8'):
            broken_links.append((path.name,href,'missing anchor'))
assert not broken_links, broken_links[:10]
html_view_cards = sum(path.read_text(encoding='utf8').count('class="cad-view"')
                      for path in out.glob('*.html'))
assert html_view_cards == sum(len(p['views']) for p in products)
dynamic_views=sum(bool(v['analysis'].get('dynamic_visibility_states')) for p in products for v in p['views'])
dynamic_sections=sum(path.read_text(encoding='utf8').count('trạng thái động trong AutoCAD')
                     for path in out.glob('*_goc_nhin.html'))
assert dynamic_sections==dynamic_views
assert all((out/f'{p["category"]}_goc_nhin.html').exists() for p in products)
print(json.dumps({'products':len(products),'views':len(used),'pages':len(pages),
                  'distinct_view_cards':html_view_cards,
                  'views_with_dynamic_state_names':dynamic_views,
                  'external_source_rows':sum(bool(p['external']) for p in products),
                  'unidentified_rows':sum(p['model']=='Chưa đọc được model' for p in products),
                  'broken_links':len(broken_links)},ensure_ascii=False))
