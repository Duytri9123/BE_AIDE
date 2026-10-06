"""Index the verified 15 March 2026 O-Sung ATS price table."""
import json
import re
from pathlib import Path

from pypdf import PdfReader
from render_mitsubishi_catalog import CSS

root = Path(__file__).resolve().parents[2]
base = root / 'Tudien/CATALOG_PHU_KIEN_DOC_LAP/OSUNG_D05_DU_LIEU_MOI'
base.mkdir(parents=True, exist_ok=True)
source = 'https://dienthaiduong.com.vn/upload/file/05-bang-gia-ats-osemco-15-03-2026-1773654045.pdf'
pdf=base/'source/Osung_15-03-2026.pdf'
pdf_text=PdfReader(pdf).pages[0].extract_text()
device=re.compile(r'ATS (?P<pole>[34])P (?P<amps>\d+)A\s+(?P<sku>OSS-[A-Z0-9-]+)\s+(?P<price>\d{1,3}(?:,\d{3})+)',re.S)
rows = []
for found in device.finditer(pdf_text):
    sku=found['sku'];model=sku.split('-3P')[0].split('-4P')[0]
    rows.append({'row_id':len(rows)+1,'model':model,'material_code':sku,
                 'category':'ATS','pole_display':found['pole']+'P',
                 'current_display':found['amps']+'A',
                 'cycle_pdf':'ON-OFF-ON' if '-TN' in model else 'ON-ON',
                 'price_vnd':int(found['price'].replace(',','')),'price_includes_vat':False,
                 'page':1,'source_line':' '.join(found.group(0).split()),'source_url':source,
                 'cad_state':'unverified','cad_dwg':None,'cad_dxf':None,
                 'cad_preview':None,'cad_basis':None})
assert len(rows)==28,len(rows)
rows.append({'row_id':len(rows)+1,'model':'ACD-M','material_code':'ACD-M',
             'category':'Bộ điều khiển ATS','pole_display':None,
             'current_display':None,'cycle_pdf':None,'price_vnd':5000000,
             'price_includes_vat':False,'page':1,'source_line':'Bộ điều khiển ATS ACD-M 5,000,000','source_url':source,
             'cad_state':'not_found','cad_dwg':None,'cad_dxf':None,
             'cad_preview':None,'cad_basis':None})
(base/'price_index.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

js = '''const rows=__DATA__;const e=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const q=document.querySelector('#q'),pole=document.querySelector('#pole');let limit=100;
function render(){const term=q.value.toUpperCase().trim();const found=rows.filter(r=>(!pole.value||r.pole_display===pole.value)&&(!term||[r.model,r.material_code,r.current_display,r.cycle_pdf].join(' ').toUpperCase().includes(term)));document.querySelector('#count').textContent=`${found.length} / ${rows.length} dòng giá`;
document.querySelector('#body').innerHTML=found.slice(0,limit).map(r=>`<tr><td>${r.row_id}</td><td><strong>${e(r.material_code)}</strong><small>${r.category==='ATS'?'Bộ chuyển nguồn tự động ATS · '+e(r.cycle_pdf):'Bộ điều khiển ATS'}</small></td><td>${e(r.pole_display||'—')}</td><td>${e(r.current_display||'—')}</td><td>—</td><td>${Number(r.price_vnd).toLocaleString('vi-VN')}</td><td><span class="muted">Chưa xác nhận CAD đúng hình</span></td><td>—</td><td><span class="muted">Không ghép từ nhãn ngoài block</span></td><td>${r.page}</td></tr>`).join('')}
q.oninput=render;pole.onchange=render;render();'''.replace('__DATA__',json.dumps(rows,ensure_ascii=False).replace('</','<\\/'))
html = '''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bảng giá O-Sung 2026 · CAD gốc</title><style>__CSS__</style><main><section class="intro"><h1>Bảng giá O-Sung 2026 · CAD thiết bị từ bản vẽ gốc</h1><p>Giá và mã vật tư từ <a href="source/Osung_15-03-2026.pdf">bảng giá ATS O-Sung áp dụng 15-03-2026</a> (<a href="__SOURCE__">nguồn công bố</a>), trang 1; <strong>chưa gồm VAT</strong>. Mỗi mã 3P/4P là một dòng PDF riêng.</p><p>Vùng D05 có một block ứng viên gần nhãn “OSS-612-PC-4P”. Hình xuất từ DXF chỉ thể hiện khung dạng hộp, chưa đủ chi tiết để xác nhận đúng thiết bị và đầu cực. Bảng giá chưa gắn block này vào dòng hàng.</p><p><a href="price_index.json">Dữ liệu dòng giá</a> · <a href="../MITSUBISHI_D04_DU_LIEU_MOI/index.html">Bảng Mitsubishi</a> · <a href="../LS_D02_DU_LIEU_MOI/index.html">Bảng LS</a></p></section><div class="tools"><input id="q" placeholder="Tìm mã, dòng A, chu kỳ..."><select id="pole"><option value="">Mọi số cực</option><option>3P</option><option>4P</option></select><span id="count"></span></div><div class="wrap"><table><thead><tr><th>STT</th><th>Tên hàng theo PDF</th><th>Số cực</th><th>In (A)</th><th>Icu (kA)</th><th>Giá theo PDF (VNĐ)</th><th>CAD nguyên bản</th><th>Kích thước ghi trong CAD</th><th>Đối chiếu CAD</th><th>Trang PDF</th></tr></thead><tbody id="body"></tbody></table></div><footer>“—” nghĩa là PDF hoặc CAD chưa cho thông số xác nhận được. Tên mã và cấu hình 3P/4P giữ đúng theo dòng PDF.</footer></main><script>__JS__</script></html>'''
html=html.replace('<a href="price_index.json">Dữ liệu dòng giá</a>',
                  '<a href="price_index.json">Dữ liệu dòng giá</a> · <a href="../THIET_BI_KHAC_2026/index.html">Bảng thiết bị khác</a>')
(base/'index.html').write_text(html.replace('__CSS__',CSS).replace('__SOURCE__',source).replace('__JS__',js),encoding='utf8')
print(json.dumps({'rows':len(rows),'source':source,'cad_linked':0},ensure_ascii=False))

