"""Index unambiguous ABB Vietnam 2026 price lines with PDF provenance."""
import json
import re
from pathlib import Path

from pypdf import PdfReader
from render_mitsubishi_catalog import CSS

root=Path(__file__).resolve().parents[2]
base=root/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/ABB_D03_DU_LIEU_MOI'
pdf=base/'source/ABB_Vietnam_MasterPriceList_2026.pdf'
source='https://library.e.abb.com/public/8fa0d161aec14871ae110caa57108c49/9AKK108472A7059_vi_B_EL%20Vietnam%20Master%20price%20list%202026%20%28VIE%29.pdf'
reader=PdfReader(pdf)
assert len(reader.pages)==218
money=re.compile(r'(\d{1,3}(?:,\d{3})+)\s*$')
mcb=re.compile(r'\b(?P<model>(?:SH|SY|S)20[1-4][LM]?-C(?P<amp>\d+))\s+(?P<sku>2CDS\w+)\s+(?P<price>\d{1,3}(?:,\d{3})+)\s*$')
rccb=re.compile(r'\b(?P<model>F?H?20[24])\s+AC-(?P<amp>\d+)/(?P<residual>0\.\d+)\s+(?P<sku>2CSF\w+)\s+(?P<price>\d{1,3}(?:,\d{3})+)\s*$')
contactor=re.compile(r'\b(?P<model>AX\d{2,3}-\d+-\d+-\d+)\s+(?P<sku>1SBL\w+)\s+(?P<price>\d{1,3}(?:,\d{3})+)\s*$')
rows=[]

def add(page,line,model,sku,category,pole,amps,price,icu=None,detail=None):
    rows.append({'row_id':len(rows)+1,'model':model,'material_code':sku,
                 'category':category,'pole_display':pole,'current_display':amps+'A' if amps else None,
                 'icu_ka_pdf':icu,'detail_pdf':detail,'price_vnd':price,
                 'price_includes_vat':False,'source_url':source,'source_pdf':pdf.name,
                 'page':page,'source_line':line,'cad_dwg':None,'cad_dxf':None,
                 'cad_preview':None,'cad_basis':None})

for page in (141,142,143):
    for line in reader.pages[page-1].extract_text().splitlines():
        found=mcb.search(line)
        if not found:
            continue
        model=found['model']
        pole=re.search(r'20([1-4])',model)[1]+'P'
        add(page,line,model,found['sku'],'MCB',pole,found['amp'],
            int(found['price'].replace(',','')),str({141:4.5,142:6,143:10}[page]))

for line in reader.pages[148].extract_text().splitlines():
    found=rccb.search(line)
    if not found:
        continue
    model=found['model']
    add(149,line,model,found['sku'],'RCCB',model[-1]+'P',found['amp'],
        int(found['price'].replace(',','')),detail='Dòng rò '+found['residual']+' A')

for page in (113,114,115,116,117):
    for line in reader.pages[page-1].extract_text().splitlines():
        found=contactor.search(line)
        if not found:
            continue
        model=found['model']
        add(page,line,model,found['sku'],'Contactor',None,
            str(int(re.search(r'AX(\d+)',model)[1])),int(found['price'].replace(',','')),
            detail='AC-3 380/400 V; biến thể cuộn hút và tiếp điểm phụ theo mã PDF')

# Formula and Tmax XT1–XT3 tables print adjacent 3P and 4P ordering codes.
# Index only rows where both code/price pairs and the frame/current are explicit.
for page in (29,30,31,35,36,37,38):
    for line in reader.pages[page-1].extract_text().splitlines():
        pairs=re.findall(r'\b(1SDA\w+)\s+(\d{1,3}(?:,\d{3})+)\b',line)
        if len(pairs)!=2:
            continue
        before=line.split(pairs[0][0],1)[0]
        frames=list(re.finditer(r'\b(A[0-3][A-Z]|XT[1-3][A-Z])\b',before))
        current=re.search(r'\b(?:TMF|TMD|TMA)\s+(\d+)-',before)
        if not (frames and current):
            continue
        model=frames[-1].group(0)
        category='MCCB Formula' if model.startswith('A') else 'MCCB Tmax XT'
        for pole,(sku,price) in zip(('3P','4P'),pairs):
            add(page,line,model,sku,category,pole,current[1],int(price.replace(',','')),
                detail='Trip '+re.search(r'\b(TMF|TMD|TMA)\b',before)[1])

assert rows
keys=[(r['material_code'],r['price_vnd']) for r in rows]
assert len(keys)==len(set(keys)), 'Repeated code/price; audit source lines'

native=base/'native'
source_by_family={'XT1':'ABB-D03-C4-I01','XT2':'ABB-D03-C4-I02',
                  'XT3':'ABB-D03-C4-I03','A1':'ABB-D03-C6-I01',
                  'A2':'ABB-D03-C6-I02','A3':'ABB-D03-C6-I03'}
sample_rate={'XT1':'160A','XT2':'160A','XT3':'250A',
             'A1':'125A','A2':'250A','A3':'630A'}
for row in rows:
    model=row['model'];pole=row['pole_display']
    contactor_source={'AX25-30-10':'ABB-D03-C2-I03',
                      'AX32-30-10':'ABB-D03-C2-I04',
                      'AX50-30-11':'ABB-D03-C2-I05'}
    contactor=next((name for name in contactor_source if model.startswith(name+'-')),None)
    if contactor:
        source_id=contactor_source[contactor];key=source_id
        basis=f'Đúng mã thân {contactor} trên CAD gốc; biến thể cuộn hút theo mã PDF'
    elif re.fullmatch(r'S20[1-4]M-C(?:6|10|16|20|25|32|40|50|63)',model) and pole in ('1P','2P','3P','4P'):
        source_id='ABB-D03-C3-I01'
        key=source_id if pole=='1P' else source_id+'-VIEW-'+pole+'-FRONT-VIEW'
        basis=f'CAD gốc ghi S200/S200M, cùng {pole}; nhãn hình mẫu 63A'
    elif re.fullmatch(r'SH20[1-4]L?-C\d+',model) and pole in ('1P','2P','3P','4P'):
        source_id='ABB-D03-C3-I03'
        key=source_id if pole=='1P' else source_id+'-VIEW-'+pole+'-FRONT-VIEW'
        basis=f'CAD gốc ghi SH200/SH200L, cùng {pole}; nhãn hình mẫu 63A'
    elif model=='FH202' and pole=='2P':
        source_id='ABB-D03-C3-I06';key=source_id
        basis='Đúng họ FH202 và 2P trong CAD gốc; nhãn hình mẫu 63A'
    elif model=='FH204' and pole=='4P':
        source_id='ABB-D03-C3-I06';key=source_id+'-VIEW-4P-FRONT-VIEW'
        basis='Trạng thái FH204 4P của block FH202/FH204 gốc; nhãn hình mẫu 63A'
    else:
        family=next((f for f in source_by_family if model.startswith(f)),None)
        if family is None or pole not in ('3P','4P'): continue
        source_id=source_by_family[family]
        key=source_id if pole=='3P' else source_id+'-VIEW-4P-FRONT-VIEW'
        basis=f'Cùng họ khung {family} và {pole} trong CAD gốc; nhãn hình mẫu {sample_rate[family]}'
    image=native/(key+'-verified.png')
    dwg=native/(key+'.dwg')
    dxf=native/(key+'.dxf')
    if not all(p.exists() for p in (image,dwg,dxf)): continue
    row.update(cad_source_id=source_id,cad_state_id=key,
               cad_dwg='native/'+dwg.name,cad_dxf='native/'+dxf.name,
               cad_preview='native/'+image.name,cad_basis=basis)

(base/'price_index.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
js='''const rows=__DATA__,e=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const q=document.querySelector('#q'),cat=document.querySelector('#cat');for(const c of [...new Set(rows.map(r=>r.category))])cat.insertAdjacentHTML('beforeend',`<option>${e(c)}</option>`);
let limit=150;function render(){const term=q.value.toUpperCase().trim(),list=rows.filter(r=>(!cat.value||r.category===cat.value)&&(!term||[r.model,r.material_code,r.current_display,r.source_line].join(' ').toUpperCase().includes(term)));document.querySelector('#count').textContent=`${list.length} / ${rows.length} dòng đã đọc`;document.querySelector('#more').hidden=list.length<=limit;
document.querySelector('#body').innerHTML=list.slice(0,limit).map(r=>`<tr><td>${r.row_id}</td><td><strong>${e(r.model)}</strong><small>${e(r.category)} · Mã vật tư: ${e(r.material_code)}</small>${r.detail_pdf?`<small>${e(r.detail_pdf)}</small>`:''}<details><summary>Chữ trong PDF</summary><small>${e(r.source_line)}</small></details></td><td>${e(r.pole_display||'—')}</td><td>${e(r.current_display||'—')}</td><td>${e(r.icu_ka_pdf||'—')}</td><td>${Number(r.price_vnd).toLocaleString('vi-VN')}</td><td>${r.cad_dwg?`<a href="${e(r.cad_preview)}" target="_blank"><img class="cad" loading="lazy" src="${e(r.cad_preview)}" alt="CAD ${e(r.model)}"></a><small><a href="${e(r.cad_dwg)}" download>DWG</a> · <a href="${e(r.cad_dxf)}" download>DXF</a> · <a href="cad_gallery.html?state=${encodeURIComponent(r.cad_state_id)}#${e(r.cad_source_id)}">Các góc nhìn</a></small>`:'<span class="muted">Chưa xác nhận CAD đầy đủ</span>'}</td><td>—</td><td>${r.cad_basis?`<span class="status">${e(r.cad_basis)}</span>`:'<span class="muted">Chờ đối chiếu block D03 gốc</span>'}</td><td>${r.page}</td></tr>`).join('')}
q.oninput=()=>{limit=150;render()};cat.onchange=()=>{limit=150;render()};document.querySelector('#more').onclick=()=>{limit+=150;render()};render();'''.replace('__DATA__',json.dumps(rows,ensure_ascii=False).replace('</','<\\/'))
page='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bảng giá ABB 2026 · CAD gốc</title><style>__CSS__</style><main><section class="intro"><h1>Bảng giá ABB 2026 · CAD thiết bị từ bản vẽ gốc</h1><p>Giá VNĐ và thông số lấy từ <a href="source/ABB_Vietnam_MasterPriceList_2026.pdf">bảng giá Việt Nam 2026 trong thư viện ABB</a> (<a href="__SOURCE__">nguồn hãng</a>). Giá <strong>chưa gồm VAT</strong>. Bảng hiện lập chỉ mục các dòng MCB trang 141–143, RCCB trang 149 và contactor trang 113–117 có mã vật tư cùng giá rõ trên một dòng; chưa phải toàn bộ 218 trang.</p><p>Mã CAD vùng D03 còn phải kiểm tra hình và trạng thái động trực tiếp trong AutoCAD. Chưa gắn hình theo họ hoặc kích thước suy đoán.</p><p><a href="price_index.json">Dữ liệu kèm dòng PDF gốc</a> · <a href="../SCHNEIDER_D01_DU_LIEU_MOI/index.html">Bảng Schneider</a> · <a href="../SHIHLIN_D06_DU_LIEU_MOI/index.html">Bảng Shihlin</a> · <a href="../MITSUBISHI_D04_DU_LIEU_MOI/index.html">Bảng Mitsubishi</a> · <a href="../LS_D02_DU_LIEU_MOI/index.html">Bảng LS</a></p></section><div class="tools"><input id="q" placeholder="Tìm mã, dòng A, thông số..."><select id="cat"><option value="">Mọi nhóm</option></select><span id="count"></span></div><div class="wrap"><table><thead><tr><th>STT</th><th>Tên hàng theo PDF</th><th>Số cực</th><th>In (A)</th><th>Icu (kA)</th><th>Giá theo PDF (VNĐ)</th><th>CAD nguyên bản</th><th>Kích thước ghi trong CAD</th><th>Đối chiếu CAD</th><th>Trang PDF</th></tr></thead><tbody id="body"></tbody></table></div><button id="more" type="button">Xem thêm 150 dòng</button></main><script>__JS__</script></html>'''
page=page.replace('Bảng hiện lập chỉ mục các dòng MCB trang 141–143, RCCB trang 149 và contactor trang 113–117 có mã vật tư cùng giá rõ trên một dòng; chưa phải toàn bộ 218 trang.',
                  'Bảng hiện lập chỉ mục Formula trang 29–31, Tmax XT1–XT3 trang 35–38, contactor trang 113–117, MCB trang 141–143 và RCCB trang 149. Với MCCB, chỉ lấy những dòng có đủ cặp mã và giá 3P/4P trên cùng hàng; chưa phải toàn bộ 218 trang.')
page=page.replace('Mã CAD vùng D03 còn phải kiểm tra hình và trạng thái động trực tiếp trong AutoCAD. Chưa gắn hình theo họ hoặc kích thước suy đoán.',
                  'CAD ghép theo họ khung và số cực sau khi xem block AutoCAD gốc. Nhãn dòng A trong hình là mẫu có sẵn; giá và thông số theo PDF từng mã.')
page=page.replace('<a href="price_index.json">Dữ liệu kèm dòng PDF gốc</a>',
                  '<a href="cad_gallery.html">Góc nhìn CAD gốc</a> · <a href="price_index.json">Dữ liệu kèm dòng PDF gốc</a>')
page=page.replace('<a href="cad_gallery.html">Góc nhìn CAD gốc</a>',
                  '<a href="cad_gallery.html">Góc nhìn CAD gốc</a> · <a href="../THIET_BI_KHAC_2026/index.html">Bảng thiết bị khác</a>')
(base/'index.html').write_text(page.replace('__CSS__',CSS).replace('__SOURCE__',source).replace('__JS__',js),encoding='utf8')
print(json.dumps({'pdf_pages':218,'indexed_rows':len(rows),'by_category':{c:sum(r['category']==c for r in rows) for c in sorted(set(r['category'] for r in rows))}},ensure_ascii=False))

