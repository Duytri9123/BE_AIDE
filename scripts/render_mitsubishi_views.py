"""Show original Mitsubishi AutoCAD states with an LS-style selector."""
import html


NAMES={
    'MIT-D04-C2-I01':'S-T10',
    'MIT-D04-C2-I02':'S-T12 / S-T20',
    'MIT-D04-C2-I03':'S-T21 / S-T25',
    'MIT-D04-C2-I04':'S-T35 / S-T50',
    'MIT-D04-C3-I01':'BH-D6 2P',
    'MIT-D04-C3-I02':'BH-D6 3P',
    'MIT-D04-C3-I03':'BH-D6 4P',
    'MIT-D04-C3-I04':'BH-D6 1P',
    'MIT-D04-C5-I01':'NF800-CEW',
    'MIT-D04-C5-I02':'NF1000-SEW',
    'MIT-D04-C5-I03':'NF1600-SEW',
    'MIT-D04-C6-I01':'NF30-CS',
    'MIT-D04-C6-I02':'NF125-CV',
    'MIT-D04-C6-I03':'NF250-CV',
    'MIT-D04-C6-I04':'NF400-CW',
    'MIT-D04-C6-I05':'NF630-CW',
    'MIT-D04-C6-I06':'NF63-SV / NF32-SV',
}


def render_views(base, manifest, views):
    native=base/'native'

    def belongs_to_device(source, state):
        source_id=source['id']
        if source_id.startswith('MIT-D04-C2-'):
            own=source['dynamic_properties'][0]['value'].split(':')[0]
            return state==own+': Side View'
        if source_id.startswith('MIT-D04-C3-'):
            own=source['dynamic_properties'][0]['value'].split(':')[0]
            return state in ('Side View',own+': Cover')
        return True

    def option(view_id, label):
        image=native/(view_id+'-crop.png')
        dwg=native/(view_id+'.dwg')
        dxf=native/(view_id+'.dxf')
        if not (image.exists() and dwg.exists() and dxf.exists()):
            return ''
        return (f'<option value="{html.escape(view_id)}" '
                f'data-img="native/{image.name}" data-dwg="native/{dwg.name}" '
                f'data-dxf="native/{dxf.name}">{html.escape(label)}</option>')

    cards=[]
    for source in sorted(manifest,key=lambda item:item['id']):
        source_id=source['id']
        prop=source['dynamic_properties'][0] if source['dynamic_properties'] else None
        choices=[option(source_id, prop['value'] if prop else 'CAD gốc')]
        choices += [option(v['id'],v['option']) for v in views
                    if v['source_id']==source_id and belongs_to_device(source,v['option'])]
        choices=[item for item in choices if item]
        if not choices:
            continue
        name=NAMES.get(source_id,source_id)
        preview='native/'+source_id+'-crop.png'
        cards.append(
            f'<article id="{source_id}">'
            f'<h2>{html.escape(name)}</h2><small>{source_id} · {len(choices)} trạng thái</small>'
            f'<label>Góc nhìn / trạng thái<select class="state">{"".join(choices)}</select></label>'
            f'<a class="picture" href="{preview}" target="_blank">'
            f'<img src="{preview}" loading="lazy" alt="CAD {html.escape(name)}"></a>'
            f'<p><a class="dwg" href="native/{source_id}.dwg" download>Tải DWG</a>'
            f' · <a class="dxf" href="native/{source_id}.dxf" download>Tải DXF</a></p>'
            '</article>')

    page='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Trạng thái CAD Mitsubishi trong AutoCAD</title><style>*{box-sizing:border-box}body{margin:0;background:#edf2f6;color:#183044;font:14px system-ui}header,.grid{max-width:1550px;margin:auto}header{padding:20px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:13px;padding:0 18px 25px}article{background:white;border:1px solid #cbd9e3;border-radius:9px;padding:13px;scroll-margin-top:20px}article:target{outline:3px solid #2680b7}h1{margin:0 0 9px}h2{font-size:17px;margin:0 0 4px}p{line-height:1.5}small{display:block;color:#5c7282}label{display:block;margin:12px 0 8px;font-weight:650}select{display:block;margin-top:5px;width:100%;padding:8px;background:#fff;border:1px solid #aabeca;border-radius:5px;font:inherit}.picture{display:block;background:#fff;border:1px solid #d5dee5}.picture img{width:100%;height:285px;object-fit:contain}a{color:#075e9f}</style><header><h1>Các trạng thái CAD Mitsubishi có sẵn trong AutoCAD</h1><p>Chọn góc nhìn theo menu động của block gốc. Ảnh, DWG và DXF bên dưới thay đổi theo lựa chọn. Không vẽ thêm đầu cực hay thanh đồng.</p><p><a href="index.html">← Bảng giá Mitsubishi</a> · <a href="../LS_D02_DU_LIEU_MOI/cad_views.html">Trạng thái CAD LS</a></p></header><div class="grid">__CARDS__</div><script>function update(select){const o=select.selectedOptions[0],card=select.closest('article');card.querySelector('.picture').href=o.dataset.img;card.querySelector('img').src=o.dataset.img;card.querySelector('.dwg').href=o.dataset.dwg;card.querySelector('.dxf').href=o.dataset.dxf}document.querySelectorAll('select.state').forEach(select=>select.onchange=()=>update(select));const selected=new URLSearchParams(location.search).get('state');if(selected){const target=[...document.querySelectorAll('select.state')].find(select=>[...select.options].some(o=>o.value===selected));if(target){target.value=selected;update(target)}};</script></html>'''.replace('__CARDS__',''.join(cards))
    (base/'cad_gallery.html').write_text(page,encoding='utf8')
    (base/'cad_views.html').write_text(page,encoding='utf8')
    return {'devices':len(cards),'choices':sum(card.count('<option ') for card in cards)}
