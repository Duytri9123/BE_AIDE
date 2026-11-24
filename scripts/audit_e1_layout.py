"""Read saved E1 state, verify source identities/geometry, export a full inventory."""
import csv
import io
import json
from pathlib import Path
import sys
import urllib.request
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.security import create_access_token

root = Path(__file__).resolve().parents[2]
out = root / 'outputs/e1-design-review-20261124'
url = 'http://127.0.0.1:8000/api/v1/projects/51/cabinet-designs'
headers = {'Authorization': 'Bearer ' + create_access_token('23'), 'Content-Type': 'application/json'}
with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as response:
    payload = json.load(response)
s = payload['designs'][0]['state']
if '--labels' in sys.argv:
    for a in s['annotations']:
        if a['id'] in ['X1','X2','X3','X4','X5','X6']:
            i=int(a['id'][1:])-1
            a.update(text=a['id'],x=154+36*i)
    if not any(a['id']=='MAIN-CHECK' for a in s['annotations']):
        s['annotations'].append(dict(id='MAIN-CHECK',text='32A: KIỂM TRA TẢI ĐỒNG THỜI',x=145,y=408,owner='mounting_plate'))
    req=urllib.request.Request(url,headers=headers,data=json.dumps(dict(designs=payload['designs'],revision=payload['revision'])).encode(),method='PUT')
    with urllib.request.urlopen(req) as response: json.load(response)
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers)) as response: payload=json.load(response)
    s=payload['designs'][0]['state']
(out/'after-api.json').write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
ds={d['id']:d for d in s['customDevices']}
ps=s['placements']
assert len(ps)==36 and len({p['id'] for p in ps})==36
mcbs=sorted([p for p in ps if ds[p['sourceId']].get('product',{}).get('category')=='MCB'],key=lambda p:p['x'])
assert [ds[p['sourceId']]['product']['tag'] for p in mcbs]==[f'MCB-{i:02d}' for i in range(1,7)]
assert [ds[p['sourceId']]['product']['in_a'] for p in mcbs]==[20,30,20,30,20,20]
assert len({ds[p['sourceId']]['source_references'][0]['occurrence_id'] for p in mcbs})==6
assert all(abs(b['x']-a['x']-ds[a['sourceId']]['width'])<.01 for a,b in zip(mcbs,mcbs[1:]))
assert all(p['y']==235 for p in mcbs)
categories=[ds[p['sourceId']].get('product',{}).get('category') for p in ps]
assert categories.count('DUCT')==5 and categories.count('TERMINAL')==12
assert categories.count('N_BAR')==categories.count('PE_BAR')==1
assert len(s['supports'])==3
# Actual useful panel contour is [32,32]..[468,668] in source CAD, not full 500x700 body.
plate=[p for p in ps if p['owner']=='mounting_plate']
for p in plate:
    d=ds[p['sourceId']]
    assert 32<=p['x'] and 32<=p['y'] and p['x']+d['width']<=468 and p['y']+d['height']<=668,p['id']
for i,a in enumerate(plate):
    da=ds[a['sourceId']]
    for b in plate[i+1:]:
        db=ds[b['sourceId']]
        ox=min(a['x']+da['width'],b['x']+db['width'])-max(a['x'],b['x'])
        oy=min(a['y']+da['height'],b['y']+db['height'])-max(a['y'],b['y'])
        assert ox<=.01 or oy<=.01,(a['id'],b['id'],ox,oy)
rows=[]
for p in ps:
    d=ds[p['sourceId']];product=d.get('product',{})
    rows.append(dict(id=p['id'],name=d['name'],category=product.get('category',''),owner=p['owner'],x_mm=p['x'],y_mm=p['y'],z_mm=p['standoff'],w_mm=d['width'],h_mm=d['height'],d_mm=d['depth'],support=p.get('mountedSupportId',''),status=d.get('geometry_status',''),source_tags=';'.join(r.get('tag','') for r in product.get('source_references',[]))))
with (out/'all-positions.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
report='''# Kiểm tra và sửa bố trí E1 — 24/11/2026

Phương án tham khảo trong dự án 51, tab **Tủ thiết kế**. Chưa duyệt điện, chưa dùng làm mẫu học đã duyệt. Người dùng đã chọn giữ nguồn vào chưa xác nhận.

## Các lỗi tìm thấy

- Thiếu máng dây, đầu ra L/N, N/PE và chặn DIN; trước đây có 11 thiết bị nguồn nhưng chưa đủ phụ kiện lắp tủ.
- MCB cách mép 24 mm không có căn cứ; xếp nhóm theo mã làm sai thứ tự nhánh. Đã xếp 01–06 theo A/B/C/A/B/C, định mức 20/30/20/30/20/20 A; mỗi thiết bị giữ đúng một occurrence nguồn.
- CAD MCCB là họ CVS100 có nhãn In 100A; lựa chọn báo giá LV510302/nguồn 32A chưa đồng nghĩa CAD đúng bộ trip 32A. Không đổi nhãn CAD thành 32A để che khác biệt. Khung 100A và trip 32A phải phân biệt.
- Nguồn ghi MCCB 3P, tải 3 pha nhưng cáp vào 2×6 + E6 mm². Chưa xác nhận số dây N, hướng vào và kết cấu đầu nối; không khoan lỗ cáp.
- Tổng công suất 23.200 W. Theo nhãn tải: A=8.300 W, B=8.300 W, C=6.600 W. Ở 220 V pha–N, tải đồng thời và cosφ=1: 37,73/37,73/30 A. Pha A/B vượt 32A danh định; cần hệ số đồng thời, tính chất tải, cosφ/khởi động, điều kiện cáp và phối hợp bảo vệ trước khi chốt. Không tự tăng CB.

## Vùng lắp và khoảng cách đã đặt

Đơn vị mm, X/Y từ góc trái dưới mặt CAD. Vỏ 500×700×250; vùng contour hữu ích thực tế x=32..468, y=32..668. Không lấy kích thước vỏ làm vùng đặt phụ kiện.

| Hạng mục | Vị trí / khoảng cách thực đặt | Trạng thái |
|---|---|---|
| Q0 MCCB | x197,5 y435; 105×161; đỉnh596 | CAD họ thiết bị, kiểm tra đúng variant |
| Q0 đến máng trên / giữa | 39 / 55 | Vùng dự kiến, chưa chứng nhận khoảng cách hãng |
| FU1 2A | x100 y460; 18×80; DIN riêng | Chưa chọn mã/kiểu đế và bảo vệ từng pha đèn |
| MCB01..06 | x142/178/214/250/286/322, y235; mỗi 36×81 | MCB30A chưa chọn mã; CAD20A cần đối chiếu kích thước thực |
| Khe MCB cạnh nhau | 0; cả nhóm216 | Phương án môđun ghép cạnh, cần kiểm tra nhiệt/điều kiện lắp hãng, không phải quy định chung |
| MCB đến máng phía trên / dưới | 39 / 55 | Vùng đấu dây dự kiến |
| Máng dọc | x35 và440, y80; 25×580, sâu40 | 2 đoạn tham khảo |
| Máng ngang | x60, y635/355/155; 380×25, sâu40 | 3 đoạn; tổng dài máng2300mm chưa gồm hao hụt |
| Cầu đấu X1..X6 | mỗi cặp L/N rộng16, y65 cao50; bước36 | 12 cực dự kiến, chưa chọn mã/tiết diện/định mức |
| Cầu đấu đến máng trên | 40 | Chưa có bán kính uốn/đường kính cáp thực |
| N / PE | x330, y475 /550; 90×20 | N có đế cách điện, PE cần liên kết vỏ/cánh; mô hình bao hình chưa có chi tiết vít |
| Đèn HL-A/B/C | x170/235/300, y610, cánh trong | Bước tâm65; khe35; lỗ22 là phương án chưa được duyệt chế tạo |
| Chặn DIN | 6; mỗi hàng2 | Chưa chọn mã; đã thể hiện trên 3 thanh DIN |

## Phần còn thiếu để phát hành chế tạo

Chưa có sơ đồ đấu dây từng chân, tuyến dây điện thực, tiết diện dây trong tủ, đầu cốt, cầu phân phối pha, nhãn dây, xác nhận bảo vệ mạch 3 đèn, tiếp địa cánh/vỏ, vật tư đầu cáp, đường kính/bán kính uốn, kiểm tra hệ số lấp máng, tản nhiệt, Icu/Ics, chọn lọc bảo vệ và bản lỗ gá theo SKU. N/PE/cầu đấu đã có vị trí dự kiến không đồng nghĩa đã được đấu hoặc chọn đủ định mức. Không tự thêm contactor/rơ-le ngoài sơ đồ nguồn.

Khoảng cách trong bảng là khoảng cách hình học đang đặt, không phải khoảng cách điện tối thiểu đã kiểm chứng. Máng25×40 là tham khảo; thành1,5, bước rãnh10, rộng6 và hình rãnh là tham số mô phỏng.

## Kiểm chứng hệ thống

- 36 thiết bị/phụ kiện = 11 thiết bị nguồn +5 máng +12 cực cầu đấu +2 thanh N/PE +6 chặn. 3 DIN được tính riêng.
- Script kiểm tra thứ tự 6 nhánh, 6 occurrence riêng, định mức30A giữ nguyên, số phụ kiện, tất cả bao hình trong contour nguồn, không chồng nhau trên panel (cho phép tiếp giáp).
- Giao diện kiểm tra 3D và trạng thái đóng; báo “bao hình không va chạm” đi kèm “chưa xác nhận đấu dây, nhiệt và khoảng cách theo mã thiết bị”. Không biến kiểm tra va chạm thành chứng nhận thiết kế hoàn chỉnh.
- Danh sách đầy đủ từng chi tiết: `all-positions.csv`; trạng thái lưu có revision trong `after-api.json`; ảnh xác nhận lấy từ tab thiết kế thật.

## Tài liệu tham chiếu

- Schneider, instruction sheet EasyPact CVS100–250 & Acc., S1A19928, version09, ngày01/07/2026: https://www.se.com/il/en/download/document/S1A19928/ . Dùng làm đầu mối đối chiếu theo đúng cấu hình, chưa suy ra bảng khoảng cách cho phương án này.
- Máng HTWD-PN25×40: https://www.hellermanntyton.com/products/wiring-ducts-and-accessories/htwd-pn-25x40/184-10068 . Không coi tham số mô phỏng là bản vẽ chế tạo của mã này.
'''
(out/'Kiem-tra-E1.md').write_text(report,encoding='utf-8')
(out/'verification.json').write_text(json.dumps(dict(revision=payload['revision'],count=len(ps),supports=len(s['supports']),checks=['unique circuit source identities','source circuit order and currents','module edge gaps','accessory inventory','actual source contour','no panel footprint overlaps'],electrical_approved=False),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(revision=payload['revision'],checked=len(ps),supports=len(s['supports']),electrical_approved=False)))
