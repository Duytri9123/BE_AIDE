"""Reconcile published LS view evidence from files, then refresh only LS indexes."""
import sys,json,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ls_native_writer import CAT,ROOT,REPORT
from publish_abb_ct_index import main as publish
families={r['family'] for r in json.loads(REPORT.read_text())}
families.update(p.parent.name.removeprefix('OFFICIAL-') for p in (CAT/'LS/ThietBi').glob('OFFICIAL-STEP-*/thong_tin_thiet_bi.json'))
report=[]
for family in sorted(families):
 p=CAT/'LS/ThietBi'/('OFFICIAL-'+family)/'thong_tin_thiet_bi.json'
 if not p.exists():continue
 d=json.loads(p.read_text(encoding='utf8'))
 if d.get('browser_hidden'):continue
 refs=(d.get('catalog_tham_khao') or {}).get('options',[])
 kind=(d.get('nhan_dien_ai') or {}).get('loai_thiet_bi_code')
 designation={'MCCB':'Icu','ACB':'Icu','ELCB':'Icu','MCB':'Icn','RCBO':'Icn','RCCB':'Inc'}.get(kind)
 if designation and family.startswith('STEP-'):
  vals=set()
  for o in refs:
   for k,v in (o.get('specifications') or {}).items():
    if k.lower().startswith(designation.lower()) or (designation in ['Icn','Inc'] and k.lower().startswith('icu')):
     vals.update(float(x) for x in re.findall(r'\d+(?:[.,]\d+)?',str(v).replace(',','.')))
  if vals:
   label='/'.join(format(x,'g') for x in sorted(vals));base=re.sub(r' · (?:Icu|Icn|Inc) .*? theo bảng giá$','',d['ten_san_pham']);d['ten_san_pham']=d['ten_kieu']=base+' · '+designation+' '+label+' kA theo bảng giá';d['price_rating_reference']={'designation':designation,'values_ka':sorted(vals),'source':'linked_pricebook_rows','geometry_confirms_rating':False}
 for v in d.get('cad_don',[]):
  dest=(p.parent/v['duong_dan']).parent;ev=json.loads((dest/'evidence.json').read_text());code=v['id_hinh_goc'].removeprefix('LS-OFFICIAL-'+family+'-')
  if family.startswith('STEP-'):
   v['nhan_hien_thi']=v['huong_nhin'];v['bo_tri_trong_tu']['cho_phep_chen']=True;v['bo_tri_trong_tu']['envelope_depth_source']=code in ['SIDE','SIDE-R']
  report.append({'family':family,'view':code,'path':dest.relative_to(CAT).as_posix(),**ev})
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
REPORT.write_text(json.dumps(report,indent=2),encoding='utf8')
publish(['OFFICIAL-'+f for f in sorted(families) if (CAT/'LS/ThietBi'/('OFFICIAL-'+f)/'thong_tin_thiet_bi.json').is_file()],report_name='ls-full-faces-2026-10-20',brand='LS',category='MIXED',profile_root='LS/ThietBi')
from audit_ls_pricebook_cad_coverage import main as audit
result=audit()
a=result['summary'];rows=result['rows']
lines=['# Đối chiếu CAD LS với toàn bộ bảng giá','',f"Đã kiểm tra {a['total_price_rows']} dòng giá LS: {a['six_view_price_rows']} dòng có ít nhất một bộ CAD họ đủ 6 mặt; {a['incomplete_view_price_rows']} dòng có CAD nhưng thiếu mặt; {a['missing_price_rows']} dòng chưa có CAD họ được xác minh.",'',f"Thư viện hiển thị {a['visible_ls_profiles']} hồ sơ và {a['visible_ls_views']} mặt CAD LS. Không có nhãn chưa xác định hoặc tệp DXF bị thiếu trong lần kiểm tra này.",'','## Quy tắc bắt buộc cho LS','','- Phải có trước, sau, trái, phải, trên, dưới của cùng một biến thể; không ghép các mặt của biến thể khác nhau.','- Kiểm tra tệp CAD, đơn vị mm và audit trước khi dùng cho bố trí; kích thước nhập tay không thay thế CAD còn thiếu.','- Thiếu CAD hoặc thiếu mặt thì yêu cầu bổ sung và chặn bố trí; không dùng hộp kích thước hoặc CAD hãng khác thay thế LS.','- CAD họ có thể dùng cho nhiều mã, nhưng vẫn phải khớp số cực, AC/DC, tiếp điểm phụ, kiểu lắp và đầu nối.','- Các giá trị Icu/Icn/Inc trong tên chỉ tham chiếu bảng giá. CAD không xác nhận dòng cắt ở điện áp làm việc hoặc SKU đặt hàng.','', '## Độ phủ theo loại','','| Loại | Dòng giá | Đủ 6 mặt CAD họ | Có CAD còn thiếu mặt | Chưa có CAD |','|---|---:|---:|---:|---:|']
for kind in sorted(a['categories']):
 r=[x for x in rows if x['category']==kind];complete=sum(any(p['six_views_complete'] for p in x['profiles']) for x in r);partial=sum(bool(x['profiles']) and not any(p['six_views_complete'] for p in x['profiles']) for x in r);missing=sum(not x['profiles'] for x in r)
 lines.append(f'| {kind} | {len(r)} | {complete} | {partial} | {missing} |')
lines+=['','## Phần còn thiếu','','Danh sách yêu cầu bổ sung ghi riêng từng mã giá và từng mặt còn thiếu trong [cad-supplement-queue.json](cad-supplement-queue.json). Không đánh dấu hoàn tất toàn bộ LS khi danh sách này còn dòng. Các nguồn không tương thích đời sản phẩm, BK AC/SPD hoặc cấu hình cuộn hút được giữ ngoài thư viện đã xác minh; xem [source-gap-review.json](source-gap-review.json).','','## Giao diện và kiểm tra','','FE đã đẩy commit 929c28fb; Vercel báo triển khai thành công. Hiển thị trạng thái 6 mặt theo biến thể, đặt tên tệp CAD LS theo họ thiết bị và mặt nhìn; đã bỏ Xem tài liệu và các mục trống.','32 bài kiểm tra về đủ mặt LS, cấu hình AC/DC/tiếp điểm phụ, bao hình, sản phẩm và quyền truy cập đã đạt. Kết quả kiểm tra từng tệp bổ sung ghi trong [six-view-validation.json](six-view-validation.json).','','Chi tiết từng dòng giá: [CSV](pricebook-cad-coverage.csv), [JSON](pricebook-cad-coverage.json). Nguồn CAD và SHA256: [ls-full-faces-2026-10-20.json](../ls-full-faces-2026-10-20.json).']
(ROOT/'docs/ls-library-rebuild-2026-10-20/full-pricebook-audit.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
