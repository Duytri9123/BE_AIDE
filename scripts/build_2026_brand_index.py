"""Create a navigation and coverage page for source-backed 2026 catalogs."""
import html
import json
from pathlib import Path

base=Path(__file__).resolve().parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
brands=[
    ('LS','LS_D02_DU_LIEU_MOI','price_with_cad.json','PDF 01-10-2026','Giá và CAD đã đối chiếu từng dòng'),
    ('Mitsubishi','MITSUBISHI_D04_DU_LIEU_MOI','price_grouped.json','PDF 2026','Nhiều mức In được gộp cùng mã khi cùng giá và cấu hình'),
    ('Schneider','SCHNEIDER_D01_DU_LIEU_MOI','price_index.json','Master Pricebook 07/2026','MCB iK60N/iC60N và MCCB EZC250; trạng thái CAD theo số cực'),
    ('ABB','ABB_D03_DU_LIEU_MOI','price_index.json','Vietnam Master Price List 2026','Formula, XT1–XT3, MCB, RCCB, contactor; CAD ghép theo họ và số cực'),
    ('O-Sung','OSUNG_D05_DU_LIEU_MOI','price_index.json','ATS 15-03-2026','Toàn bộ 29 dòng trong PDF một trang; CAD chưa ghép'),
    ('Shihlin','SHIHLIN_D06_DU_LIEU_MOI','price_index.json','Bảng giá 03/2026','Các dòng đọc chắc từ trang 7, 8, 10, 11; BHL 4P đã ghép CAD'),
]
cards=[]
audit=[]
for name,folder,data_file,source,scope in brands:
    path=base/folder/data_file
    rows=json.loads(path.read_text(encoding='utf8'))
    count=len(rows)
    matched=sum(bool(row.get('cad_dwg')) for row in rows)
    extra=''
    if name=='LS':
        supplement=json.loads((base/folder/'cad_bo_sung.json').read_text(encoding='utf8'))
        extra=(f'<p><a href="{folder}/cad_bo_sung.html">{len(supplement["items"])} thiết bị LS bổ sung '
               'ngoài PDF giá →</a></p>')
    cards.append(f'<article><h2>{html.escape(name)}</h2><p>{html.escape(source)}</p><strong>{count} dòng</strong><small>{matched} dòng có CAD đã ghép</small><p>{html.escape(scope)}</p><a href="{folder}/index.html">Mở bảng giá và CAD →</a>{extra}</article>')
    audit.append({'brand':name,'folder':folder,'data_file':data_file,
                  'display_rows':count,'rows_with_cad':matched,'source':source,'scope':scope})
(base/'brand_prices_2026.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
device_data=json.loads((base/'THIET_BI_KHAC_2026/products.json').read_text(encoding='utf8'))
groups=[('do_luong','Đồng hồ và đo lường'),('bao_ve','Cầu dao và bảo vệ'),('bien_dong','Biến dòng'),
        ('dieu_khien','Điều khiển và nguồn'),('dau_noi','Đấu nối và bù điện'),
        ('lam_mat','Quạt và làm mát'),('phu_kien','Phụ kiện tủ điện'),
        ('rmu','Tủ trung thế RMU'),('chua_phan_loai','Chi tiết cần nhận dạng')]
other_cards=''.join(f'<article><h2>{html.escape(title)}</h2><strong>{sum(p["category"]==key for p in device_data["products"])} thiết bị</strong><p>Tên, chữ CAD, góc nhìn và thông số đối chiếu.</p><a href="THIET_BI_KHAC_2026/{key}.html">Mở bảng thiết bị →</a></article>'
                    for key,title in groups)
page='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bảng giá thiết bị điện 2026 và CAD gốc</title><style>*{box-sizing:border-box}body{margin:0;background:#edf2f6;color:#173044;font:15px system-ui}main{max-width:1500px;margin:auto;padding:24px}header,article{background:#fff;border:1px solid #cbd9e3;border-radius:10px;padding:18px}h1{margin:0 0 8px;font-size:27px}header p{line-height:1.5}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:12px;margin-top:15px}h2{margin:0 0 8px}article p{line-height:1.45}article strong{font-size:19px}small{display:block;color:#587083;margin-top:3px}a{color:#075e9f;font-weight:600}@media(max-width:700px){main{padding:10px}}</style><main><header><h1>Bảng giá thiết bị điện 2026 · CAD gốc</h1><p>Cùng mẫu bảng cho sáu vùng hãng D01–D06. Giá và thông số lấy từ PDF ghi ở từng bảng; hình CAD liên kết theo họ thiết bị và số cực đã đối chiếu với block AutoCAD. Nhãn dòng A in trong CAD gốc có thể là một mẫu khác với dòng giá; xem ghi chú ở từng dòng. Số dòng phản ánh phần đã lập chỉ mục, không hàm ý đã đọc hết mọi trang PDF.</p><a href="brand_prices_2026.json">Phạm vi dữ liệu từng hãng</a> · <a href="full_accessory_cad_library.html">Toàn bộ CAD từ DWG phụ kiện</a> · <a href="outside_cad_audit.html">167 block ứng viên ngoài D01–D06</a></header><div class="grid">__CARDS__</div></main></html>'''
page=page.replace('<a href="full_accessory_cad_library.html">Toàn bộ CAD từ DWG phụ kiện</a>',
                  '<a href="THU_VIEN_THIET_BI_AI_2026/index.html">Catalog thiết bị cho AI</a> · <a href="THIET_BI_KHAC_2026/index.html">Bảng các thiết bị khác</a>')
page=page.replace(' · <a href="outside_cad_audit.html">167 block ứng viên ngoài D01–D06</a>', '')
page=page.replace('</div></main></html>',
                  '</div><h2>Thiết bị khác từ thư viện CAD</h2><p>Các thiết bị như đồng hồ, biến dòng, bộ nguồn và phụ kiện được gom theo sản phẩm và góc nhìn. Giá chưa có PDF đối chiếu được để trống.</p><div class="grid">__OTHER__</div></main></html>')
(base/'index_2026.html').write_text(page.replace('__CARDS__',''.join(cards)).replace('__OTHER__',other_cards),encoding='utf8')
print(json.dumps(audit,ensure_ascii=False))
