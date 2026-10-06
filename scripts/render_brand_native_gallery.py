"""Show only visibly checked native CAD states for a 2026 brand table."""
import html
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CAT=ROOT/'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
FOLDERS={'schneider':'SCHNEIDER_D01_DU_LIEU_MOI',
         'abb':'ABB_D03_DU_LIEU_MOI',
         'shihlin':'SHIHLIN_D06_DU_LIEU_MOI'}
base=CAT/FOLDERS[sys.argv[1].lower()]
native=base/'native'
manifest=json.loads((native/'manifest.json').read_text(encoding='utf8'))
views=json.loads((native/'views.json').read_text(encoding='utf8')) if (native/'views.json').exists() else []

def asset(vid,label):
    image=native/(vid+'-verified.png')
    if not image.exists() and base.name.startswith('SHIHLIN'):
        image=native/(vid+'-crop.png')
    dwg=native/(vid+'.dwg')
    dxf=native/(vid+'.dxf')
    if not all(p.exists() for p in (image,dwg,dxf)):
        return None
    return {'id':vid,'label':label,'image':'native/'+image.name,
            'dwg':'native/'+dwg.name,'dxf':'native/'+dxf.name}

cards=[]
for item in manifest:
    typ=next((x['text'] for x in item['attributes'] if x['tag'].upper()=='TYPE'),None)
    name=typ or item['view_name']
    if item['view_name'].startswith('BHL '): name=item['view_name']
    default=next((p['value'] for p in item['dynamic_properties'] if p['name'] in ('Options','Visibility1')),'CAD gốc')
    choices=[asset(item['id'],default)]
    choices += [asset(v['id'],v['option']) for v in views if v['source_id']==item['id']]
    choices=[c for c in choices if c]
    if not choices: continue
    first=choices[0]
    opts=''.join(f'<option value="{html.escape(c["id"])}" data-img="{c["image"]}" data-dwg="{c["dwg"]}" data-dxf="{c["dxf"]}">{html.escape(c["label"])}</option>' for c in choices)
    cards.append(f'<article id="{html.escape(item["id"])}"><h2>{html.escape(name)}</h2><small>{item["id"]} · {len(choices)} trạng thái</small><label>Góc nhìn / trạng thái<select class="state">{opts}</select></label><a class="picture" href="{first["image"]}" target="_blank"><img src="{first["image"]}" loading="lazy" alt="CAD {html.escape(name)}"></a><p><a class="dwg" href="{first["dwg"]}" download>Tải DWG</a> · <a class="dxf" href="{first["dxf"]}" download>Tải DXF</a></p></article>')

brand={'ABB':'ABB','SCHNEIDER':'Schneider','SHIHLIN':'Shihlin'}[base.name.split('_')[0]]
page='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Trạng thái CAD __BRAND__</title><style>*{box-sizing:border-box}body{margin:0;background:#edf2f6;color:#183044;font:14px system-ui}header,.grid{max-width:1550px;margin:auto}header{padding:20px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:13px;padding:0 18px 25px}article{background:white;border:1px solid #cbd9e3;border-radius:9px;padding:13px;scroll-margin-top:20px}article:target{outline:3px solid #2680b7}h1{margin:0 0 9px}h2{font-size:17px;margin:0 0 4px}p{line-height:1.5}small{display:block;color:#5c7282}label{display:block;margin:12px 0 8px;font-weight:650}select{display:block;margin-top:5px;width:100%;padding:8px;background:#fff;border:1px solid #aabeca;border-radius:5px;font:inherit}.picture{display:block;background:#202830;border:1px solid #d5dee5}.picture img{width:100%;height:285px;object-fit:contain}a{color:#075e9f}</style><header><h1>Góc nhìn CAD __BRAND__ từ block AutoCAD gốc</h1><p>Ảnh xem trước hiển thị nét CAD và ẩn lớp WIPEOUT che hình. DWG và DXF giữ nguyên các đối tượng của block; không thêm hình hay đầu cực.</p><p><a href="index.html">← Bảng giá __BRAND__</a></p></header><div class="grid">__CARDS__</div><script>function update(select){const o=select.selectedOptions[0],card=select.closest('article');card.querySelector('.picture').href=o.dataset.img;card.querySelector('img').src=o.dataset.img;card.querySelector('.dwg').href=o.dataset.dwg;card.querySelector('.dxf').href=o.dataset.dxf}document.querySelectorAll('select.state').forEach(select=>select.onchange=()=>update(select));const selected=new URLSearchParams(location.search).get('state');if(selected){const target=[...document.querySelectorAll('select.state')].find(select=>[...select.options].some(o=>o.value===selected));if(target){target.value=selected;update(target)}};</script></html>'''
page=page.replace('__BRAND__',brand).replace('__CARDS__',''.join(cards))
(base/'cad_gallery.html').write_text(page,encoding='utf8')
print(json.dumps({'brand':brand,'devices':len(cards),'states':sum(c.count('<option ') for c in cards)},ensure_ascii=False))
