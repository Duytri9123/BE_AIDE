"""Build an interactive selector for the real AutoCAD dynamic views."""
import html
import json
from pathlib import Path

BASE=Path(__file__).resolve().parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/LS_D02_DU_LIEU_MOI'
NATIVE=BASE/'native'
devices={x['id']:x for x in json.loads((BASE/'devices.json').read_text(encoding='utf8'))}
sources=json.loads((NATIVE/'manifest.json').read_text(encoding='utf8'))
variants=json.loads((NATIVE/'variants.json').read_text(encoding='utf8'))
views=json.loads((NATIVE/'views.json').read_text(encoding='utf8'))

def option(vid,label):
    image=NATIVE/(vid+'-crop.png')
    dwg=NATIVE/(vid+'.dwg')
    dxf=NATIVE/(vid+'.dxf')
    if not (image.exists() and dwg.exists() and dxf.exists()): return ''
    return f'<option value="{html.escape(vid)}" data-img="native/{image.name}" data-dwg="native/{dwg.name}" data-dxf="native/{dxf.name}">{html.escape(label)}</option>'

cards=[]
for source in sources:
    sid=source['id']
    option_prop=next((p for p in source['dynamic_properties'] if p['name']=='Options'),None)
    base_label=option_prop['value'] if option_prop else 'CAD gốc'
    choices=[option(sid,base_label)]
    for variant in variants:
        if variant['source_id']==sid:
            choices.append(option(variant['id'],variant['option']))
    for view in views:
        if view['source_id']==sid:
            choices.append(option(view['id'],view['option']))
    choices=[c for c in choices if c]
    if not choices: continue
    preview='native/'+sid+'-crop.png'
    title=devices[sid]['name']
    cards.append(f'<article id="{sid}"><h2>{html.escape(title)}</h2><small>{sid} · {len(choices)} trạng thái</small><label>Góc nhìn / trạng thái<select class="state">{"".join(choices)}</select></label><a class="picture" href="{preview}" target="_blank"><img src="{preview}" loading="lazy" alt="{html.escape(title)}"></a><p><a class="dwg" href="native/{sid}.dwg" download>Tải DWG</a> · <a class="dxf" href="native/{sid}.dxf" download>Tải DXF</a></p></article>')

page='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Trạng thái CAD LS trong AutoCAD</title><style>*{box-sizing:border-box}body{margin:0;background:#edf2f6;color:#183044;font:14px system-ui}header,.grid{max-width:1550px;margin:auto}header{padding:20px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:13px;padding:0 18px 25px}article{background:white;border:1px solid #cbd9e3;border-radius:9px;padding:13px;scroll-margin-top:20px}article:target{outline:3px solid #2680b7}h1{margin:0 0 9px}h2{font-size:17px;margin:0 0 4px}p{line-height:1.5}small{display:block;color:#5c7282}label{display:block;margin:12px 0 8px;font-weight:650}select{display:block;margin-top:5px;width:100%;padding:8px;background:#fff;border:1px solid #aabeca;border-radius:5px;font:inherit}.picture{display:block;background:#fff;border:1px solid #d5dee5}.picture img{width:100%;height:285px;object-fit:contain}a{color:#075e9f}</style><header><h1>Các trạng thái CAD LS có sẵn trong AutoCAD</h1><p>Chọn góc nhìn theo menu Options của block gốc. Mỗi lựa chọn là một bản DWG/DXF xuất từ trạng thái động có sẵn. Đầu cực và hình học của thiết bị không được vẽ thêm.</p><p><a href="index.html">← Bảng giá LS</a> · <a href="cad_gallery.html">33 hình nguồn</a></p></header><div class="grid">__CARDS__</div><script>document.querySelectorAll('select.state').forEach(select=>select.onchange=()=>{const o=select.selectedOptions[0],card=select.closest('article');card.querySelector('.picture').href=o.dataset.img;card.querySelector('img').src=o.dataset.img;card.querySelector('.dwg').href=o.dataset.dwg;card.querySelector('.dxf').href=o.dataset.dxf});</script></html>'''.replace('__CARDS__',''.join(cards))
(BASE/'cad_views.html').write_text(page,encoding='utf8')
index=BASE/'index.html'
content=index.read_text(encoding='utf8')
content=content.replace('<a href="cad_gallery.html">Xem 33 CAD nguồn</a>','<a href="cad_gallery.html">Xem 33 CAD nguồn</a> · <a href="cad_views.html">Xem các trạng thái AutoCAD</a>')
index.write_text(content,encoding='utf8')
gallery=BASE/'cad_gallery.html'
content=gallery.read_text(encoding='utf8')
content=content.replace('<a href="index.html">← Bảng giá</a>','<a href="index.html">← Bảng giá</a> · <a href="cad_views.html">Các trạng thái AutoCAD</a>')
gallery.write_text(content,encoding='utf8')
print(json.dumps({'devices':len(cards),'exported_views':len(views)},ensure_ascii=False))
