"""Build a conservative Shihlin price index from directly readable PDF rows."""
import json
import re
from pathlib import Path

from pypdf import PdfReader
from render_mitsubishi_catalog import CSS

root=Path(__file__).resolve().parents[2]
base=root/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/SHIHLIN_D06_DU_LIEU_MOI'
pdf=base/'source/Shihlin_03-2026.pdf'
source='https://vinaelectrics.vn/wp-content/uploads/2026/03/BANG-GIA-SHIHLIN-T3.2026.pdf'
reader=PdfReader(pdf)
assert len(reader.pages)==18
money=re.compile(r'(?<!\d)(\d{1,3}(?:,\d{3})+)(?!\d)\s*$')
model_pole=re.compile(r'^(?P<model>(?:BM\s*\d+|BHA(?:125|-B[34])|BHL(?:-A)?|BHR-A|RPC(?:-H)?|RPL|RPV|NVB-[\w-]+)(?:-[A-Z]+)?)\s+(?P<pole>[1-4]P(?:\+N)?)\b',re.I)
rows=[]

def add(page,line,model,pole,current,price,category,icu=None,power=None,aux=None):
    rows.append({'row_id':len(rows)+1,'model':model.strip().upper().replace('BM ','BM'),
                 'category':category,'pole_display':pole,'current_display':current,
                 'icu_ka_pdf':icu,'ac3_kw_pdf':power,'auxiliary_contacts_pdf':aux,
                 'price_vnd':price,'source_pdf':pdf.name,'source_url':source,
                 'page':page,'source_line':line,'cad_dwg':None,'cad_dxf':None,
                 'cad_preview':None,'cad_basis':None})

# Page 8: contactor model and its listed price occur on the same text line.
for line in reader.pages[7].extract_text().splitlines():
    if not (line.startswith('S-P') and (match:=money.search(line))):
        continue
    model=line.split()[0]
    if not re.fullmatch(r'S-P\d+[A-Z]?',model,re.I):
        continue
    body=line[len(model):match.start()].strip()
    numbers=re.match(r'(?P<kw>\d+(?:\.\d+)?)\s+(?P<hp>\d+(?:\.\d+)?)\s+(?P<amp>\d+)\b',body)
    aux=re.search(r'\b\d+a(?:\d+b)?\b|\b\d+b\b',body)
    add(8,line,model,'3P',numbers['amp']+'A' if numbers else None,
        int(match[1].replace(',','')),'Contactor',power=numbers['kw'] if numbers else None,
        aux=aux.group(0) if aux else None)

# Pages 7, 10 and 11: table rows that retain both the model/pole and price.
for page in (7,10,11):
    for line in reader.pages[page-1].extract_text().splitlines():
        match=money.search(line)
        head=model_pole.match(line)
        if not (match and head):
            continue
        model=head['model'].upper().replace('BM ','BM')
        pole=head['pole'].upper()
        middle=line[head.end():match.start()].strip()
        current=re.search(r'(?:\d+[.\-/]){1,}\d+A|\b\d+A\b',middle)
        category=('MCCB' if model.startswith('BM') else
                  'RCBO' if model.startswith(('BHL','RPL','NVB')) else
                  'RCCB' if model.startswith(('BHR','RPV')) else 'MCB')
        icu=None
        if model.startswith('RPC-H') or model=='BHA-B4': icu='10'
        elif model=='RPC' or model=='BHA-B3': icu='6'
        elif page==7:
            tail=middle[current.end():] if current else middle
            ka=re.search(r'(?<!\d)(\d+(?:\.\d+)?)\s*$',tail)
            if ka: icu=ka[1]
        add(page,line,model,pole,current.group(0) if current else None,
            int(match[1].replace(',','')),category,icu)

# On page 10 the model/pole is printed once above two or three price bands.
active=None
for line in reader.pages[9].extract_text().splitlines():
    head=model_pole.match(line)
    if head:
        active=(head['model'].upper(),head['pole'].upper())
    match=money.search(line)
    if not (active and match) or head:
        continue
    current=re.match(r'\s*((?:\d+[.\-/]){1,}\d+A|\d+A)\b',line)
    if not current:
        continue
    model,pole=active
    category='MCB' if model.startswith('RPC') else ('RCBO' if model=='RPL' else 'RCCB')
    icu='10' if model=='RPC-H' else ('6' if model=='RPC' else None)
    add(10,line,model,pole,current[1],int(match[1].replace(',','')),category,icu)

# The original D06 BHL 4P block visibly has four breaker poles and a TEST
# module, with BHL 33 / C20 lettering. This is the same listed BHL 4P family;
# its 20 A label is retained in the native drawing for the whole price band.
native=base/'native'
for row in rows:
    if row['model']=='BHL' and row['pole_display']=='4P':
        stem='SHI-D06-C3-I01'
        required=[native/(stem+suffix) for suffix in ('.dwg','.dxf','-crop.png')]
        if all(path.exists() for path in required):
            row.update(cad_source_id=stem,cad_state_id=stem,
                       cad_dwg='native/'+stem+'.dwg',
                       cad_dxf='native/'+stem+'.dxf',
                       cad_preview='native/'+stem+'-crop.png',
                       cad_basis='BHL 4P trong CAD gốc; nhãn trên hình là BHL 33 C20')

(base/'price_index.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
js='''const rows=__DATA__,e=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const q=document.querySelector('#q'),cat=document.querySelector('#cat');
for(const c of [...new Set(rows.map(r=>r.category))].sort())cat.insertAdjacentHTML('beforeend',`<option>${e(c)}</option>`);
function render(){const term=q.value.toUpperCase().trim(),list=rows.filter(r=>(!cat.value||r.category===cat.value)&&(!term||[r.model,r.current_display,r.source_line].join(' ').toUpperCase().includes(term)));document.querySelector('#count').textContent=`${list.length} / ${rows.length} dòng đã đọc`;
document.querySelector('#body').innerHTML=list.map(r=>`<tr><td>${r.row_id}</td><td><strong>${e(r.model)}</strong><small>${e(r.category)}${r.ac3_kw_pdf?' · AC-3: '+e(r.ac3_kw_pdf)+' kW':''}${r.auxiliary_contacts_pdf?' · tiếp điểm phụ '+e(r.auxiliary_contacts_pdf):''}</small><details><summary>Chữ trong PDF</summary><small>${e(r.source_line)}</small></details></td><td>${e(r.pole_display||'—')}</td><td>${e(r.current_display||'—')}</td><td>${e(r.icu_ka_pdf||'—')}</td><td>${Number(r.price_vnd).toLocaleString('vi-VN')}</td><td>${r.cad_dwg?`<a href="${e(r.cad_preview)}" target="_blank"><img class="cad" src="${e(r.cad_preview)}" alt="CAD ${e(r.model)}"></a><small><a href="${e(r.cad_dwg)}" download>DWG</a> · <a href="${e(r.cad_dxf)}" download>DXF</a> · <a href="cad_gallery.html?state=${encodeURIComponent(r.cad_state_id)}#${e(r.cad_source_id)}">Các góc nhìn</a></small>`:'<span class="muted">Chưa xác nhận CAD đầy đủ</span>'}</td><td>—</td><td>${r.cad_basis?`<span class="status">${e(r.cad_basis)}</span>`:'<span class="muted">Chờ đối chiếu trực tiếp block gốc</span>'}</td><td>${r.page}</td></tr>`).join('')}
q.oninput=render;cat.onchange=render;render();'''.replace('__DATA__',json.dumps(rows,ensure_ascii=False).replace('</','<\\/'))
page='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bảng giá Shihlin 2026 · CAD gốc</title><style>__CSS__</style><main><section class="intro"><h1>Bảng giá Shihlin 2026 · CAD thiết bị từ bản vẽ gốc</h1><p>Giá và thông số được đọc từ <a href="source/Shihlin_03-2026.pdf">bảng giá Shihlin 03/2026</a> (<a href="__SOURCE__">nguồn công bố</a>). Bảng này mới gồm các dòng PDF có mã và giá đọc được cùng một dòng trên trang 7, 8, 10, 11; chưa phải toàn bộ 18 trang.</p><p>Thông số trống được giữ trống. CAD BHL 4P đã được đối chiếu trực tiếp với block AutoCAD và số cực; các mã khác chỉ ghép khi hình đầy đủ và đúng.</p><p><a href="cad_gallery.html">Góc nhìn CAD gốc</a> · <a href="price_index.json">Dữ liệu giá có dòng PDF gốc</a> · <a href="../MITSUBISHI_D04_DU_LIEU_MOI/index.html">Bảng Mitsubishi</a> · <a href="../LS_D02_DU_LIEU_MOI/index.html">Bảng LS</a></p></section><div class="tools"><input id="q" placeholder="Tìm mã, dòng A, thông số..."><select id="cat"><option value="">Mọi nhóm</option></select><span id="count"></span></div><div class="wrap"><table><thead><tr><th>STT</th><th>Tên hàng theo PDF</th><th>Số cực</th><th>In (A)</th><th>Icu (kA)</th><th>Giá theo PDF (VNĐ)</th><th>CAD nguyên bản</th><th>Kích thước ghi trong CAD</th><th>Đối chiếu CAD</th><th>Trang PDF</th></tr></thead><tbody id="body"></tbody></table></div></main><script>__JS__</script></html>'''
page=page.replace('<a href="cad_gallery.html">Góc nhìn CAD gốc</a>',
                  '<a href="cad_gallery.html">Góc nhìn CAD gốc</a> · <a href="../THIET_BI_KHAC_2026/index.html">Bảng thiết bị khác</a>')
(base/'index.html').write_text(page.replace('__CSS__',CSS).replace('__SOURCE__',source).replace('__JS__',js),encoding='utf8')
print(json.dumps({'pdf_pages':len(reader.pages),'indexed_rows':len(rows),'by_page':{str(p):sum(r['page']==p for r in rows) for p in (7,8,10,11)}},ensure_ascii=False))

