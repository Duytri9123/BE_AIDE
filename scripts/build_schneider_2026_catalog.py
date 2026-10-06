"""Read the Schneider 2026 official MCB table by aligned PDF columns."""
import json
import re
from pathlib import Path

import pdfplumber
from render_mitsubishi_catalog import CSS

root=Path(__file__).resolve().parents[2]
base=root/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/SCHNEIDER_D01_DU_LIEU_MOI'
pdf=base/'source/Schneider_MasterPriceBook_07-2026.pdf'
source='https://www.se.com/vn/vi/download/document/MasterPriceBook/'
pattern=re.compile(r'^A9(?P<family>[KF])(?P<series>271|272|241|242|243|244|741|742|743|744)(?P<amps>06|10|16|20|25|32|40|50|63)$')
prices=re.compile(r'^\d{1,3}(?:\.\d{3})+$')
poles={'271':'1P','272':'2P','241':'1P','242':'2P','243':'3P','244':'4P',
       '741':'1P','742':'2P','743':'3P','744':'4P'}
rows=[]
with pdfplumber.open(pdf) as book:
    assert len(book.pages)==282
    page=book.pages[43]
    words=page.extract_words()
    money=[word for word in words if prices.fullmatch(word['text'])]
    for word in words:
        match=pattern.fullmatch(word['text'])
        if not match or not 190<word['top']<690:
            continue
        aligned=[item for item in money if 55<item['x0']-word['x1']<155
                 and abs(item['top']-word['top'])<1.5]
        if len(aligned)!=1:
            raise ValueError(('price column ambiguous',word['text'],aligned))
        code=word['text'];pole=poles[match['series']]
        rows.append({'row_id':len(rows)+1,'model':'iK60N' if match['family']=='K' else 'iC60N',
                     'material_code':code,'category':'MCB','pole_display':pole,
                     'current_display':str(int(match['amps']))+'A',
                     'icu_ka_pdf':'6','icu_voltage_pdf':'230V' if pole in ('1P','2P') else '400V',
                     'price_vnd':int(aligned[0]['text'].replace('.','')),
                     'price_includes_vat':True,'source_pdf':pdf.name,'source_url':source,
                     'page':44,'printed_page':42,
                     'pdf_position':{'x':word['x0'],'y':word['top']},
                     'cad_dwg':None,'cad_dxf':None,'cad_preview':None,'cad_basis':None})
assert len(rows)==72,len(rows)
ezc=re.compile(r'^EZC250(?P<type>[FNH])(?P<pole>[234])(?P<amps>\d{3})$')
with pdfplumber.open(pdf) as book:
    words=book.pages[55].extract_words()
    money=[word for word in words if prices.fullmatch(word['text'])]
    for word in words:
        found=ezc.fullmatch(word['text'])
        if not found or not 165<word['top']<415:
            continue
        aligned=[item for item in money if 10<item['x0']-word['x1']<80
                 and abs(item['top']-word['top'])<1.5]
        if len(aligned)!=1:
            raise ValueError(('EZC250 price column ambiguous',word['text'],aligned))
        pole=found['pole']+'P'
        icu={'F':'18','N':'25','H':'85' if pole=='2P' else '36'}[found['type']]
        rows.append({'row_id':len(rows)+1,'model':'EZC250'+found['type'],
                     'material_code':word['text'],'category':'MCCB','pole_display':pole,
                     'current_display':str(int(found['amps']))+'A',
                     'icu_ka_pdf':icu,'icu_voltage_pdf':'230/240V' if pole=='2P' else '415V',
                     'price_vnd':int(aligned[0]['text'].replace('.','')),
                     'price_includes_vat':True,'source_pdf':pdf.name,'source_url':source,
                     'page':56,'printed_page':54,
                     'pdf_position':{'x':word['x0'],'y':word['top']},
                     'cad_dwg':None,'cad_dxf':None,'cad_preview':None,'cad_basis':None})
assert len(rows)>105,len(rows)

# Match only the native block family and the exact number of visible poles.
# The rating printed inside each original block is retained as a sample.
native=base/'native'
for row in rows:
    if row['model']=='iC60N': source_id='SCH-D01-C3-I02'
    elif row['model']=='iK60N': source_id='SCH-D01-C3-I03'
    elif row['model'].startswith('EZC250'): source_id='SCH-D01-C5-I02'
    else: continue
    pole=row['pole_display']
    key=source_id if pole=='3P' else source_id+'-VIEW-'+pole+'-FRONT-VIEW'
    image=native/(key+'-verified.png')
    dwg=native/(key+'.dwg')
    dxf=native/(key+'.dxf')
    if not all(path.exists() for path in (image,dwg,dxf)): continue
    sample='63A' if row['model'].startswith('i') else '250A'
    row.update(cad_source_id=source_id,cad_state_id=key,
               cad_dwg='native/'+dwg.name,cad_dxf='native/'+dxf.name,
               cad_preview='native/'+image.name,
               cad_basis=f'Cùng dòng/khung {row["model"] if row["model"].startswith("i") else "EZC250"} và {pole} trong CAD gốc; nhãn hình mẫu {sample}')

(base/'price_index.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
js='''const rows=__DATA__,e=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const q=document.querySelector('#q'),m=document.querySelector('#model');
function render(){const term=q.value.toUpperCase().trim(),list=rows.filter(r=>(!m.value||r.model===m.value)&&(!term||[r.material_code,r.current_display,r.pole_display].join(' ').toUpperCase().includes(term)));document.querySelector('#count').textContent=`${list.length} / ${rows.length} dòng đã đọc`;
document.querySelector('#body').innerHTML=list.map(r=>`<tr><td>${r.row_id}</td><td><strong>${e(r.material_code)}</strong><small>${e(r.model)} · ${r.category}</small></td><td>${e(r.pole_display)}</td><td>${e(r.current_display)}</td><td>${e(r.icu_ka_pdf)} @ ${e(r.icu_voltage_pdf)}</td><td>${Number(r.price_vnd).toLocaleString('vi-VN')}</td><td>${r.cad_dwg?`<a href="${e(r.cad_preview)}" target="_blank"><img class="cad" src="${e(r.cad_preview)}" loading="lazy" alt="CAD ${e(r.model)}"></a><small><a href="${e(r.cad_dwg)}" download>DWG</a> · <a href="${e(r.cad_dxf)}" download>DXF</a> · <a href="cad_gallery.html?state=${encodeURIComponent(r.cad_state_id)}#${e(r.cad_source_id)}">Các góc nhìn</a></small>`:'<span class="muted">Chưa xác nhận CAD đầy đủ</span>'}</td><td>—</td><td>${r.cad_basis?`<span class="status">${e(r.cad_basis)}</span>`:'<span class="muted">Chờ đối chiếu trực tiếp trạng thái block D01</span>'}</td><td>${r.page}</td></tr>`).join('')}
q.oninput=render;m.onchange=render;render();'''.replace('__DATA__',json.dumps(rows,ensure_ascii=False).replace('</','<\\/'))
page='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bảng giá Schneider 2026 · CAD gốc</title><style>__CSS__</style><main><section class="intro"><h1>Bảng giá Schneider 2026 · CAD thiết bị từ bản vẽ gốc</h1><p>Giá và thông số đọc từ <a href="source/Schneider_MasterPriceBook_07-2026.pdf">Master Pricebook 07/2026 chính thức</a> (<a href="__SOURCE__">trang hãng</a>). Giá <strong>đã gồm VAT</strong>. Bảng hiện gồm 72 mã MCB iK60N/iC60N ở trang PDF 44 (số in trên trang: 42); 282 trang PDF còn lại chưa lập chỉ mục đầy đủ.</p><p>Mã, dòng, cực và giá được đối chiếu theo cùng hàng và cột trên PDF. CAD vùng D01 cần kiểm tra các trạng thái block trong AutoCAD trước khi liên kết tới mã; hình chưa xác nhận được để trống.</p><p><a href="price_index.json">Dữ liệu giá kèm tọa độ PDF</a> · <a href="../SHIHLIN_D06_DU_LIEU_MOI/index.html">Bảng Shihlin</a> · <a href="../MITSUBISHI_D04_DU_LIEU_MOI/index.html">Bảng Mitsubishi</a> · <a href="../LS_D02_DU_LIEU_MOI/index.html">Bảng LS</a></p></section><div class="tools"><input id="q" placeholder="Tìm mã, dòng A, số cực..."><select id="model"><option value="">Mọi dòng</option><option>iK60N</option><option>iC60N</option></select><span id="count"></span></div><div class="wrap"><table><thead><tr><th>STT</th><th>Tên hàng theo PDF</th><th>Số cực</th><th>In (A)</th><th>Icu (kA)</th><th>Giá theo PDF (VNĐ)</th><th>CAD nguyên bản</th><th>Kích thước ghi trong CAD</th><th>Đối chiếu CAD</th><th>Trang PDF</th></tr></thead><tbody id="body"></tbody></table></div></main><script>__JS__</script></html>'''
page=page.replace('Bảng hiện gồm 72 mã MCB iK60N/iC60N ở trang PDF 44 (số in trên trang: 42); 282 trang PDF còn lại chưa lập chỉ mục đầy đủ.',
                  'Bảng hiện gồm 72 mã MCB iK60N/iC60N ở trang PDF 44 và 45 mã MCCB EZC250 ở trang PDF 56; các trang khác chưa lập chỉ mục đầy đủ.')
page=page.replace('CAD vùng D01 cần kiểm tra các trạng thái block trong AutoCAD trước khi liên kết tới mã; hình chưa xác nhận được để trống.',
                  'CAD được ghép theo dòng/khung và số cực từ block AutoCAD gốc. Nhãn dòng A in trên hình là mẫu có sẵn; giá và thông số mỗi mã theo PDF.')
page=page.replace('<a href="price_index.json">Dữ liệu giá kèm tọa độ PDF</a>',
                  '<a href="cad_gallery.html">Góc nhìn CAD gốc</a> · <a href="price_index.json">Dữ liệu giá kèm tọa độ PDF</a>')
page=page.replace('<option>iC60N</option>',
                  '<option>iC60N</option><option>EZC250F</option><option>EZC250N</option><option>EZC250H</option>')
page=page.replace('<a href="cad_gallery.html">Góc nhìn CAD gốc</a>',
                  '<a href="cad_gallery.html">Góc nhìn CAD gốc</a> · <a href="../THIET_BI_KHAC_2026/index.html">Bảng thiết bị khác</a>')
(base/'index.html').write_text(page.replace('__CSS__',CSS).replace('__SOURCE__',source).replace('__JS__',js),encoding='utf8')
print(json.dumps({'pdf_pages':282,'indexed_rows':len(rows),
                  'with_cad':sum(bool(row['cad_dwg']) for row in rows)},ensure_ascii=False))

