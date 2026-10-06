"""Publish verified LS device/CAD evidence that is outside the price PDF.

These records are not price rows. Do not copy a 3P contactor CAD to a 2P SKU.
"""
import html
import json
from pathlib import Path

BASE=Path(__file__).resolve().parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/LS_D02_DU_LIEU_MOI'

items=[
    {
        'id':'LS-BKN-2P-CAD', 'name':'BKN · MCB 2P', 'type':'Cầu dao điện loại tép',
        'poles':2, 'visible_front_mm':[36,82], 'dimension_basis':'Khung nét nhìn thấy của trạng thái AutoCAD 2P; bản CAD chuẩn hóa D:data dùng trong tủ đo 36 × 81 mm.',
        'cad_dwg':'native/LS-D02-C3-I03-2P.dwg',
        'cad_dxf':'native/LS-D02-C3-I03-2P.dxf',
        'preview':'native/LS-D02-C3-I03-2P-crop.png',
        'views':'cad_views.html#LS-D02-C3-I03',
        'cad_basis':'Trạng thái 2P của block BKN vùng LS D02; không ghi dòng 16/32 A hoặc đặc tuyến cụ thể.',
        'official_source':'https://www.ls-electric.com/upload/customer/download/1483/MCB_E_180131.pdf',
        'price_2026':None,
        'note':'Bảng giá LS hiện dùng các dòng LA63; không ghép hình BKN cho mã LA63 hoặc tự gán giá.'
    },
    {
        'id':'LS-GMC-40P2-TSBS', 'name':'GMC-40P2 TSBS · contactor 2P 40A',
        'type':'Khởi động từ 2 cực', 'poles':2, 'outer_whd_mm':[49,74,62],
        'dimension_basis':'Bản kích thước GMC-40P2 TSBS của LS, trang 4. Biến thể TQBS cao 87,6 mm.',
        'cad_dwg':None, 'cad_dxf':None, 'preview':None, 'views':None,
        'cad_basis':'Chưa tìm được bản CAD gốc đúng GMC-40P2 trong thư viện. CAD MC-40a/3P hiện có không dùng thay.',
        'official_source':'https://www.ls-electric.com/upload/customer/download/1450/2-pole_ac_dc.pdf',
        'price_2026':None,
        'note':'Cần chốt điện áp cuộn hút và đúng biến thể trước khi mua hoặc lắp.'
    }
]
for item in items:
    for key in ('cad_dwg','cad_dxf','preview'):
        if item[key]:
            assert (BASE/item[key]).is_file(),(item['id'],key)
(BASE/'cad_bo_sung.json').write_text(json.dumps({
    'scope':'Thiết bị LS có bằng chứng CAD/catalog nhưng không có dòng giá tương ứng trong PDF LS 01-10-2026',
    'items':items},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def esc(value): return html.escape(str(value))
rows=[]
for n,item in enumerate(items,1):
    size=item.get('outer_whd_mm') or item.get('visible_front_mm')
    dim=' × '.join(map(str,size))+' mm' if size else '—'
    cad=(f'<a href="{esc(item["preview"])}"><img class="cad" src="{esc(item["preview"])}" alt="{esc(item["name"])}"></a>'
         f'<small><a href="{esc(item["cad_dwg"])}">DWG</a> · <a href="{esc(item["cad_dxf"])}">DXF</a> · '
         f'<a href="{esc(item["views"])}">Các góc nhìn</a></small>') if item['cad_dxf'] else '<span class="pending">Chưa có CAD sản phẩm đúng mã</span>'
    rows.append(f'<tr><td>{n}</td><td><strong>{esc(item["name"])}</strong><small>{esc(item["type"])}</small></td>'
                f'<td>{item["poles"]}</td><td>{dim}<small>{esc(item["dimension_basis"])}</small></td>'
                f'<td>{cad}</td><td>{esc(item["cad_basis"])}<small>{esc(item["note"])}</small></td>'
                f'<td>—<small>Không có dòng giá trong PDF đang dùng</small></td>'
                f'<td><a href="{esc(item["official_source"])}">Catalog LS</a></td></tr>')
page='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Thiết bị LS bổ sung · CAD và thông số</title><style>body{font:14px/1.5 system-ui;margin:0;background:#edf2f6;color:#173044}main{max-width:1500px;margin:auto;padding:20px}header,section{background:white;border:1px solid #cbd9e3;border-radius:9px;padding:16px;margin-bottom:14px}h1{margin:0 0 8px}table{width:100%;border-collapse:collapse}th,td{padding:9px;text-align:left;vertical-align:top;border-bottom:1px solid #dae4eb}th{background:#e5edf3}small{display:block;color:#536879;margin-top:5px}.cad{width:145px;height:155px;object-fit:contain;border:1px solid #d9e4ec}a{color:#075e9f}.pending{color:#805710;font-weight:600}@media(max-width:850px){section{overflow:auto}table{min-width:1000px}}</style>
<main><header><h1>Thiết bị LS bổ sung</h1><p>Bảng này ghi thiết bị có bằng chứng từ CAD hoặc catalog LS nhưng <b>không có dòng giá tương ứng</b> trong PDF giá hiện dùng. Không ghép CAD BKN cho LA63 và không dùng hình MC-40a 3P cho contactor 2P.</p><p>MCCB ABN52c 2P đã có ở <a href="index.html">dòng 1 bảng giá LS</a>; trạng thái CAD 2P có mặt trước 50 × 130 mm. <a href="cad_bo_sung.json">Dữ liệu máy đọc</a> · <a href="cad_views.html">Các trạng thái CAD gốc</a></p></header><section><table><thead><tr><th>STT</th><th>Thiết bị</th><th>Cực</th><th>Kích thước</th><th>CAD</th><th>Căn cứ và giới hạn</th><th>Giá 2026</th><th>Nguồn hãng</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></section></main></html>'''
(BASE/'cad_bo_sung.html').write_text(page,encoding='utf-8')
print(json.dumps({'supplemental_ls_devices':len(items)},ensure_ascii=False))
