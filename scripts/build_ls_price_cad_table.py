"""Join LS PDF prices to native CAD exports with a recorded basis for each match."""
import html
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / 'Tudien/CATALOG_PHU_KIEN_DOC_LAP/LS_D02_DU_LIEU_MOI'
NATIVE = BASE / 'native'
prices = json.loads((BASE/'price_index.json').read_text(encoding='utf8'))
devices = {d['id']: d for d in json.loads((BASE/'devices.json').read_text(encoding='utf8'))}
manifest = {d['id']: d for d in json.loads((NATIVE/'manifest.json').read_text(encoding='utf8'))}
variants = {d['id']: d for d in json.loads((NATIVE/'variants.json').read_text(encoding='utf8'))}
dwf_audit_path=BASE/'recover_dwf_audit.json'
dwf_text_by_row={entry['row_id']:entry['dwf_text_labels'] for entry in json.loads(dwf_audit_path.read_text(encoding='utf8'))['matches']} if dwf_audit_path.exists() else {}

FRAMES = {
    'ABN': {50:1,60:1,100:1,200:3,250:3,400:4,800:5},
    'ABS': {30:1,50:1,60:1,100:2,125:2,200:3,250:3,400:4,800:5,1000:7,1200:7},
    'ABH': {50:2,125:2,200:3,250:3,400:4},
    'EBN': {50:1,60:1,100:1,200:3,250:3,400:4,800:5},
    'EBS': {30:1,50:1,60:1,100:2,125:2,200:3,250:3,400:4,800:5,1000:6,1200:6},
    'EBH': {50:2,125:2,200:3,250:3,400:4},
}

def poles(row):
    m = re.search(r'\b([1234])P\b',row['name_pdf'],re.I)
    if m: return int(m[1])
    m = re.search(r'CONTACTOR\s+([34])\s+POLES\b',row['section_pdf'],re.I)
    if m: return int(m[1])
    m = re.fullmatch(r'(?:ABN|ABS|ABH|EBN|EBS|EBH|BS)(\d{2,4})[A-Z]*',row['model'],re.I)
    if m and m[1][-1] in '234': return int(m[1][-1])
    if 'loại khối 2 Pha' in row['section_pdf']: return 2
    return None

def match(row):
    code = row['model'].upper()
    p = poles(row)
    if code.startswith('MC-') and ('VDC' in row['name_pdf'].upper() or 'DC COIL' in row['section_pdf'].upper() or '4 PHA' in row['section_pdf'].upper()):
        return None
    m = re.fullmatch(r'(ABN|ABS|ABH|EBN|EBS|EBH)(\d{2,4})([CB])',code)
    if m:
        frame = int(m[2][:-1])*10
        n = FRAMES[m[1]].get(frame)
        if n and p in (2,3,4) and not (n==6 and p!=3) and not (n==7 and p==2):
            return f'LS-D02-C6-I{n:02}',p,'Họ và khung ghi trong CAD gốc','family'
    if code=='BS32C' and 'không vỏ' in row['name_pdf'].lower():
        return 'LS-D02-C3-I07',2,'Mã và kiểu không vỏ trùng hình CAD','exact'
    if code in ('32KGRD','32GRC'):
        return 'LS-D02-C3-I05',None,'Họ 32 KGRc/d ghi trong CAD','family'
    m = re.fullmatch(r'(TD|TS)(100|160|250|400|630|800)N',code)
    if m and p in (2,3,4):
        n = (1 if m[2] in ('100','160') else None) if m[1]=='TD' else {'100':3,'160':3,'250':3,'400':4,'630':4,'800':5}.get(m[2])
        if n: return f'LS-D02-C5-I{n:02}',p,'Dòng TD/TS và khung ghi trong CAD','family'
    if code.startswith('TS1000') and p in (3,4):
        return ('LS-D02-C5-I06' if p==3 else 'LS-D02-C5-I07'),p,'Mặt trước TS1000 đúng số cực','family'
    if code in ('TS1250N','TS1250H') and p==4:
        return 'LS-D02-C5-I07',4,'Cùng khung 1600AF 4P: hình gốc TS1000, bao hình 280×327 theo tài liệu LS','family'
    exact={'MC-9A':'LS-D02-C2-I02','MC-12A':'LS-D02-C2-I02','MT-32':'LS-D02-C2-I06','MT-63':'LS-D02-C2-I07','UA-1':'LS-D02-C2-I01'}
    if code in exact: return exact[code],None,'Mã trên CAD trùng bảng giá','exact'
    return None

rows=[]
for price in prices:
    r={**price,'poles_pdf':poles(price),'cad_device_id':None,'cad_variant_id':None,'cad_preview':None,'cad_dwg':None,'cad_dxf':None,'cad_match_basis':None,'cad_match_level':None,'cad_label':None,'cad_size_note':None,'cad_model_on_drawing':None,'cad_pole_on_drawing':None,'cad_evidence_url':None,'cad_connection_points':None,'product_evidence_url':None,'product_evidence_note':None,'dwf_text_labels':dwf_text_by_row.get(price['row_id'],[])}
    if price['model'].upper() in ('LA63N', 'LA63H'):
        r['product_evidence_url']='https://www.lselectricamerica.com/wp-content/uploads/MCBL-Series_MCB_RCD_EN_C015S2-05-202505.pdf'
        r['product_evidence_note']='LS xác nhận dòng LA63N/LA63H và số cực trong catalog; chưa tìm được CAD nguyên bản đúng mã.'
    found=match(price)
    if found:
        source_id,p,basis,level=found
        native=manifest[source_id]
        native_p=next((int(m[1]) for a in native['attributes'] if a['tag']=='POLES' if (m:=re.match(r'([234])P',a['text'],re.I))),None)
        variant_id=source_id if not (p and native_p and p!=native_p) else f'{source_id}-{p}P'
        if price['model'].upper()=='MC-12A':
            variant_id='LS-D02-C2-I02-VIEW-12A-FRONT-VIEW'
        if variant_id==source_id or variant_id in variants or (NATIVE/(variant_id+'.dwg')).exists():
            preview=NATIVE/(variant_id+'-crop.png')
            dwg=NATIVE/(variant_id+'.dwg')
            dxf=NATIVE/(variant_id+'.dxf')
            if preview.exists() and dwg.exists():
                annotations=devices[source_id].get('source_dwg_annotation_text',[])
                dimensions=[a for a in annotations if 'Size:' in a or 'Size%%' in a]
                source_attrs={a['tag']:a['text'] for a in native['attributes']}
                variant_attrs={a['tag']:a['text'] for a in variants.get(variant_id,{}).get('attributes',[])} if isinstance(variants.get(variant_id,{}).get('attributes',[]),list) else variants.get(variant_id,{}).get('attributes',{})
                cad_attrs={**source_attrs,**variant_attrs}
                r.update(cad_device_id=source_id,cad_variant_id=variant_id,cad_preview='native/'+preview.name,cad_dwg='native/'+dwg.name,cad_dxf=('native/'+dxf.name if dxf.exists() else None),cad_match_basis=basis,cad_match_level=level,cad_label=devices[source_id]['name'],cad_size_note='; '.join(dimensions) or None,cad_model_on_drawing=cad_attrs.get('TYPE') or cad_attrs.get('MODEL'),cad_pole_on_drawing=cad_attrs.get('POLES'))
    if r['cad_dwg'] is None and r['model'].upper() in ('TS1250N','TS1250H') and r['poles_pdf']==3:
        # Independently inspected D:\data's TS1250A3P source block: complete
        # 3-pole device and terminals, same 210 x 327 outline as D02 TS1000.
        # The drawing has no printed N/H trip rating, so this is a frame match.
        stem='LS-DATA-TS1250A3P'
        if all((NATIVE/(stem+ext)).is_file() for ext in ('.dwg','.dxf','-verified.png')):
            r.update(cad_device_id=stem,cad_variant_id=stem,
                     cad_preview=f'native/{stem}-verified.png',
                     cad_dwg=f'native/{stem}.dwg',cad_dxf=f'native/{stem}.dxf',
                     cad_match_basis='Cùng khung 3P: block TS1250A3P trong D:\\data; nhãn N/H không có trong CAD',
                     cad_match_level='family',cad_label='TS1250A3P (bản vẽ tủ nguồn)',
                     cad_size_note=None,cad_model_on_drawing=None,
                     cad_pole_on_drawing='3P; ba đầu cực trên và dưới')
    if r['cad_dwg'] is None and r['model'].upper()=='MC-32A' and '3 PHA' in r['section_pdf'] and 'AC COIL' in r['section_pdf'].upper():
        stem='LS-DATA-MC32AF-3P'
        if all((NATIVE/(stem+ext)).is_file() for ext in ('.dwg','.dxf','-verified.png')):
            r.update(cad_device_id=stem,cad_variant_id=stem,
                     cad_preview=f'native/{stem}-verified.png',
                     cad_dwg=f'native/{stem}.dwg',cad_dxf=f'native/{stem}.dxf',
                     cad_match_basis='CAD nguồn D:\\data ghi LS, MC 32AF/3P; cùng khung cho MC-32a 3 pha AC',
                     cad_match_level='family',cad_label='MC 32AF/3P Series',
                     cad_size_note=None,cad_model_on_drawing='MC 32AF/3P Series',
                     cad_pole_on_drawing='3P; ba đầu cực trên và dưới')
    if r['cad_dwg'] is None and r['model'].upper() in ('TS1600N','TS1600H') and r['poles_pdf'] in (3,4):
        p=r['poles_pdf']
        stem=f'LS-DATA-TS1600AF-{p}P'
        if all((NATIVE/(stem+ext)).is_file() for ext in ('.dwg','.dxf','-verified.png')):
            r.update(cad_device_id=stem,cad_variant_id=stem,
                     cad_preview=f'native/{stem}-verified.png',
                     cad_dwg=f'native/{stem}.dwg',cad_dxf=f'native/{stem}.dxf',
                     cad_match_basis=f'Cùng khung: CAD gốc D:\\data ghi TS 1600AF, LS và {p}P; không ghi cấp N/H',
                     cad_match_level='family',cad_label=f'TS 1600AF {p}P · LS Susol',
                     cad_size_note=None,cad_model_on_drawing='TS 1600AF',
                     cad_pole_on_drawing=f'{p}P; {p} đầu cực trên và dưới')
    ac_contactor_frames={
        'MC-185A':('LS-DATA-MC185-225-3P','MC-185a/225a'),
        'MC-225A':('LS-DATA-MC185-225-3P','MC-185a/225a'),
        'MC-265A':('LS-DATA-MC265-400-3P','MC-265a/330a/400a'),
        'MC-330A':('LS-DATA-MC265-400-3P','MC-265a/330a/400a'),
        'MC-400A':('LS-DATA-MC265-400-3P','MC-265a/330a/400a'),
        'MC-500A':('LS-DATA-MC500-800-3P','MC-500a/630a/800a'),
        'MC-630A':('LS-DATA-MC500-800-3P','MC-500a/630a/800a'),
        'MC-800A':('LS-DATA-MC500-800-3P','MC-500a/630a/800a'),
    }
    if r['cad_dwg'] is None and r['model'].upper() in ac_contactor_frames and r['poles_pdf']==3 and 'AC COIL' in r['section_pdf'].upper():
        stem,label=ac_contactor_frames[r['model'].upper()]
        if all((NATIVE/(stem+ext)).is_file() for ext in ('.dwg','.dxf','-verified.png')):
            labels={'power_in':['R/1/L1','S/3/L2','T/5/L3'],
                    'power_out':['U/2/T1','V/4/T2','W/6/T3'],
                    'auxiliary_markings':['13','14','21','22','31','32','43','44']}
            if stem=='LS-DATA-MC185-225-3P': labels['coil_markings']=['A1','A2']
            r.update(cad_device_id=stem,cad_variant_id=stem,
                     cad_preview=f'native/{stem}-verified.png',
                     cad_dwg=f'native/{stem}.dwg',cad_dxf=f'native/{stem}.dxf',
                     cad_match_basis=f'Chữ CAD gốc ghi {label}; ba cực và đầu nối đúng họ MC',
                     cad_match_level='family',cad_label=label,
                     cad_size_note=None,cad_model_on_drawing=label,
                     cad_pole_on_drawing='3P; R/S/T vào, U/V/W ra',
                     cad_connection_points=labels)
    if r['cad_dwg'] and r['model'].upper() in ('TS1250N','TS1250H','TS1600N','TS1600H'):
        r['cad_evidence_url']='https://www.ls-electric.com/upload/customer/download/1573/1600AF_Susol%20MCCB.pdf'
    if r['model'].upper()=='ABN52C' and r['poles_pdf']==2 and r['cad_variant_id']=='LS-D02-C6-I01-2P':
        r['cad_visible_front_mm']=[50,130]
        r['cad_size_note']=(r['cad_size_note'] or '')+'; mặt trước trạng thái 2P đo trong CAD: 50 × 130 mm'
    rows.append(r)
(BASE/'price_with_cad.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
data=json.dumps(rows,ensure_ascii=False).replace('</','<\\/')
css='''*{box-sizing:border-box}body{margin:0;background:#edf2f6;color:#173044;font:14px system-ui}main{max-width:1800px;margin:auto;padding:18px}h1{margin:0 0 7px;font-size:26px}.intro{background:#fff;border:1px solid #cbd9e3;border-radius:10px;padding:16px 20px;line-height:1.5}.intro p{margin:7px 0}.tools{position:sticky;top:0;z-index:5;display:flex;gap:8px;align-items:center;flex-wrap:wrap;background:#edf2f6;padding:10px 0}input,select{border:1px solid #afc4d5;border-radius:6px;padding:9px;font:inherit;background:#fff}input{min-width:250px;flex:1}.wrap{overflow:auto;background:white;border:1px solid #cbd9e3;border-radius:9px}table{width:100%;min-width:1400px;border-collapse:collapse}th,td{border-bottom:1px solid #dae4eb;padding:8px 9px;vertical-align:top;text-align:left}th{background:#e5edf3;position:sticky;top:0;z-index:2}td:first-child,td:nth-child(3),td:nth-child(10){white-space:nowrap}td:nth-child(6){font-weight:700;text-align:right;white-space:nowrap}.cad{width:145px;height:155px;object-fit:contain;background:#fff;border:1px solid #d9e4ec}.muted{color:#718495}.status{display:block;color:#20643c;font-weight:650;max-width:235px}.status.family{color:#79550f}small{display:block;line-height:1.35;margin-top:4px;color:#536879;max-width:235px}a{color:#075e9f}footer{padding:14px 0;color:#536879}@media(max-width:700px){main{padding:8px}h1{font-size:20px}}'''
page='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bảng giá LS và CAD gốc</title><style>__CSS__</style><main><section class="intro"><h1>Bảng giá LS · CAD thiết bị từ bản vẽ gốc</h1><p>Bảng giá áp dụng 01-10-2026; tên hàng, In, Icu và giá lấy theo PDF. Hình, DWG và DXF xuất từ block CAD: giữ nguyên thiết bị, đầu cực đồng gốc và chữ bên trong; chỉ bỏ title ngoài block.</p><p>CAD dùng chung cho nhiều mã khi họ, khung và số cực phù hợp. Dòng “cùng họ và khung” là hình CAD mẫu, mã in trên hình có thể khác mã giá. Bản 2P/4P là trạng thái động có sẵn trong AutoCAD. Ô không đủ bằng chứng vẫn để trống.</p><p><a href="cad_gallery.html">33 CAD nguồn</a> · <a href="cad_views.html">Các góc nhìn gốc</a> · <a href="price_with_cad.json">Dữ liệu đối chiếu</a> · <a href="../MITSUBISHI_D04_DU_LIEU_MOI/index.html">Bảng Mitsubishi</a></p></section><div class="tools"><input id="q" placeholder="Tìm mã, dòng A, loại thiết bị..."><select id="page"><option value="">Mọi trang PDF</option></select><select id="state"><option value="">Tất cả dòng giá</option><option value="matched">Có CAD</option><option value="exact">Trùng mã trên hình</option><option value="unmatched">Chưa ghép CAD</option></select><span id="count"></span></div><div class="wrap"><table><thead><tr><th>STT</th><th>Tên hàng theo PDF</th><th>Số cực</th><th>In (A)</th><th>Icu (kA)</th><th>Giá theo PDF (VNĐ)</th><th>CAD nguyên bản</th><th>Kích thước ghi trong CAD</th><th>Đối chiếu CAD</th><th>Trang PDF</th></tr></thead><tbody id="body"></tbody></table></div><footer>Đối chiếu số cực theo hình CAD gốc; không tạo thêm hình đầu cực hoặc thanh đồng.</footer></main><script>const rows=__DATA__;const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const q=document.querySelector('#q'),pg=document.querySelector('#page'),st=document.querySelector('#state');for(let i=1;i<=8;i++)pg.insertAdjacentHTML('beforeend',`<option value="${i}">Trang ${i}</option>`);function render(){let query=q.value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();let list=rows.filter(r=>(!pg.value||r.page==pg.value)&&(!st.value||(st.value==='matched'&&r.cad_dwg)||(st.value==='exact'&&r.cad_match_level==='exact')||(st.value==='unmatched'&&!r.cad_dwg))&&[r.model,r.name_pdf,r.in_a_pdf,r.section_pdf,r.cad_label].join(' ').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().includes(query));document.querySelector('#count').textContent=`${list.length} / ${rows.length} dòng`;document.querySelector('#body').innerHTML=list.map(r=>`<tr><td>${r.row_id}</td><td><strong>${esc(r.name_pdf)}</strong><small>${esc(r.section_pdf)}</small></td><td>${r.poles_pdf??'—'}</td><td>${esc(r.in_a_pdf??'—')}</td><td>${esc(r.icu_ka_pdf??'—')}</td><td>${Number(r.price_vnd_ex_vat).toLocaleString('vi-VN')}</td><td>${r.cad_dwg?`<a href="${r.cad_preview}" target="_blank"><img class="cad" loading="lazy" src="${r.cad_preview}" alt="CAD ${esc(r.cad_label)}"></a><small><a href="${r.cad_dwg}" download>DWG</a>${r.cad_dxf?` · <a href="${r.cad_dxf}" download>DXF</a>`:''} · ${esc(r.cad_variant_id)}</small>`:'<span class="muted">Chưa xác định</span>'}</td><td>${esc(r.cad_size_note??'—')}</td><td>${r.cad_dwg?`<span class="status ${r.cad_match_level}">${esc(r.cad_match_basis)}</span><small>${esc(r.cad_label)}${r.cad_model_on_drawing?' · chữ CAD: '+esc(r.cad_model_on_drawing):''}</small>`:'<span class="muted">Chưa có block đúng để ghép</span>'}</td><td>${r.page}</td></tr>`).join('')}q.oninput=render;pg.onchange=render;st.onchange=render;render();</script></html>'''.replace('__CSS__',css).replace('__DATA__',data)
page=page.replace('''${esc(r.cad_label)}${r.cad_model_on_drawing?' · chữ CAD: '+esc(r.cad_model_on_drawing):''}</small>''',
                  '''${esc(r.cad_label)}${r.cad_model_on_drawing?' · chữ CAD: '+esc(r.cad_model_on_drawing):''}</small>${r.cad_evidence_url?`<small><a href="${r.cad_evidence_url}" target="_blank">Kích thước khung theo LS</a></small>`:''}${r.cad_connection_points?`<small>Điểm ghi trong CAD: ${Object.values(r.cad_connection_points).flat().map(esc).join(' · ')}</small>`:''}''')
page=page.replace(' · ${esc(r.cad_variant_id)}</small>', ' · ${r.cad_device_id?.startsWith("LS-D02-")?`<a href="cad_views.html#${esc(r.cad_device_id)}">Các góc nhìn</a>`:esc(r.cad_variant_id)}</small>')
page=page.replace('<span class="muted">Chưa có block đúng để ghép</span>', '<span class="muted">${r.product_evidence_note?esc(r.product_evidence_note):"Chưa có block đúng để ghép"}</span>${r.product_evidence_url?`<small><a href="${r.product_evidence_url}" target="_blank">Catalog LS chính hãng</a></small>`:""}')
page=page.replace("'<span class=\"muted\">Chưa xác định</span>'", "`<span class=\"muted\">${r.product_evidence_note?'Chưa có CAD gốc đã kiểm chứng':'Chưa xác định'}</span>`")
page=page.replace('33 CAD nguồn</a>', 'CAD nguồn LS và D:\\data</a>')
page=page.replace('Bảng Mitsubishi</a></p></section>',
                  'Bảng Mitsubishi</a> · <a href="../SCHNEIDER_D01_DU_LIEU_MOI/index.html">Bảng Schneider 2026</a> · <a href="../ABB_D03_DU_LIEU_MOI/index.html">Bảng ABB 2026</a> · <a href="../SHIHLIN_D06_DU_LIEU_MOI/index.html">Bảng Shihlin 2026</a> · <a href="../OSUNG_D05_DU_LIEU_MOI/index.html">Bảng O-Sung 2026</a></p></section>')
page=page.replace('Các góc nhìn gốc</a> · <a href="price_with_cad.json">',
                  'Các góc nhìn gốc</a> · <a href="cad_bo_sung.html">Thiết bị LS bổ sung ngoài PDF giá</a> · <a href="price_with_cad.json">')
page=page.replace('Bảng O-Sung 2026</a></p></section>',
                  'Bảng O-Sung 2026</a> · <a href="../index_2026.html">Tất cả hãng</a></p></section>')
page=page.replace('Tất cả hãng</a></p></section>',
                  'Tất cả hãng</a> · <a href="../THIET_BI_KHAC_2026/index.html">Bảng thiết bị khác</a></p></section>')
page=page.replace('Dữ liệu đối chiếu</a> ·', 'Dữ liệu đối chiếu</a> · <a href="recover_dwf_audit.json">Kiểm tra DWF</a> · <a href="source/@LS_recover.dwf" download>DWF gốc</a> ·')
page=page.replace('"Chưa có block đúng để ghép"}</span>',
                  '"Chưa có block đúng để ghép"}</span>${r.dwf_text_labels?.length?`<small>DWF có chữ: ${r.dwf_text_labels.map(esc).join(" · ")}. Chưa xác định được block CAD tương ứng.</small>`:""}')
(BASE/'index.html').write_text(page,encoding='utf8')
cards=[]
for source_id,device in devices.items():
    all_ids=[source_id]+[v['id'] for v in variants.values() if v['source_id']==source_id]
    links=' · '.join(f'{html.escape(vid.removeprefix(source_id) or "CAD gốc")}: <a href="native/{vid}.dwg" download>DWG</a>'+(f' / <a href="native/{vid}.dxf" download>DXF</a>' if (NATIVE/(vid+'.dxf')).exists() else '') for vid in all_ids if (NATIVE/(vid+'.dwg')).exists())
    preview='native/'+source_id+'-crop.png'
    cards.append(f'<article><a href="{preview}" target="_blank"><img src="{preview}" loading="lazy"></a><h2>{html.escape(device["name"])}</h2><p>{links}</p></article>')
stem='LS-DATA-TS1250A3P'
if (NATIVE/(stem+'.dwg')).is_file():
    cards.append(f'<article><a href="native/{stem}-verified.png" target="_blank"><img src="native/{stem}-verified.png" loading="lazy"></a><h2>TS1250A3P · nguồn D:\\data</h2><p>Mặt trước 3P, cùng khung cho TS1250N/H 3P. Nhãn N/H không có trong CAD.</p><p><a href="native/{stem}.dwg" download>DWG</a> · <a href="native/{stem}.dxf" download>DXF</a> · <a href="native/{stem}-source.json">Nguồn và đối chiếu</a></p></article>')
stem='LS-DATA-MC32AF-3P'
if (NATIVE/(stem+'.dwg')).is_file():
    cards.append(f'<article><a href="native/{stem}-verified.png" target="_blank"><img src="native/{stem}-verified.png" loading="lazy"></a><h2>MC 32AF/3P · nguồn D:\\data</h2><p>Block LS 3P nguyên hình, dùng theo họ cho MC-32a 3 pha AC.</p><p><a href="native/{stem}.dwg" download>DWG</a> · <a href="native/{stem}.dxf" download>DXF</a> · <a href="native/{stem}-source.json">Nguồn và đối chiếu</a></p></article>')
for p in (3,4):
    stem=f'LS-DATA-TS1600AF-{p}P'
    if (NATIVE/(stem+'.dwg')).is_file():
        cards.append(f'<article><a href="native/{stem}-verified.png" target="_blank"><img src="native/{stem}-verified.png" loading="lazy"></a><h2>TS 1600AF {p}P · nguồn D:\\data</h2><p>Block LS Susol gốc, đủ {p} đầu cực trên/dưới; cùng khung cho TS1600N/H {p}P, không có nhãn N/H.</p><p><a href="native/{stem}.dwg" download>DWG</a> · <a href="native/{stem}.dxf" download>DXF</a> · <a href="native/{stem}-source.json">Nguồn và đối chiếu</a></p></article>')
for stem,label in (('LS-DATA-MC185-225-3P','MC-185a/225a'),
                   ('LS-DATA-MC265-400-3P','MC-265a/330a/400a'),
                   ('LS-DATA-MC500-800-3P','MC-500a/630a/800a')):
    if (NATIVE/(stem+'.dwg')).is_file():
        cards.append(f'<article><a href="native/{stem}-verified.png" target="_blank"><img src="native/{stem}-verified.png" loading="lazy"></a><h2>{label} · nguồn D:\\data</h2><p>CAD 3P đủ thân, đầu cực và ký hiệu nối dây gốc.</p><p><a href="native/{stem}.dwg" download>DWG</a> · <a href="native/{stem}.dxf" download>DXF</a> · <a href="native/{stem}-source.json">Nguồn và đối chiếu</a></p></article>')
gallery='<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CAD LS gốc</title><style>body{margin:0;padding:20px;background:#edf2f6;color:#183044;font:14px system-ui}header,.grid{max-width:1500px;margin:auto}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px}article{background:white;border:1px solid #cbd9e3;border-radius:8px;padding:12px}img{width:100%;height:250px;object-fit:contain;background:white;border:1px solid #ddd}h2{font-size:16px}p{line-height:1.4}a{color:#075e9f}</style><header><h1>CAD nguồn vùng LS và D:\\data</h1><p>Ảnh từ CAD nguồn, giữ thiết bị và đầu cực; bỏ title ngoài block. Bản 2P/4P dùng trạng thái động có sẵn khi có. Block bổ sung từ D:\\data được ghi rõ nguồn.</p><p><a href="index.html">← Bảng giá</a></p></header><div class="grid">'+''.join(cards)+'</div></html>'
(BASE/'cad_gallery.html').write_text(gallery,encoding='utf8')
print(json.dumps({'price_rows':len(rows),'with_cad':sum(bool(r['cad_dwg']) for r in rows),'exact':sum(r['cad_match_level']=='exact' for r in rows)},ensure_ascii=False))

