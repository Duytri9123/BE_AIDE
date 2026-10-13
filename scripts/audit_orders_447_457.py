"""Reproducible evidence audit. PDF facts are visually transcribed, not OCR claims."""
from pathlib import Path
import sys,json,csv,html,re,hashlib
from collections import Counter
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'BE_AIDE'),str(ROOT/'tmp/tudien_deps')]
from app.services.ai.source_reconciliation import quote_spec
from app.services.cad.catalogtb_assets import inventory_diagnostics
OUT=ROOT/'outputs/order-447-457-audit'

def read(path):return json.loads(path.read_text(encoding='utf8'))
def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def breaker(panel,tag,poles,current,ka,category='MCB',phase=None,load=None):
 return dict(panel=panel,tag=tag,category=category,quantity=1,poles=poles,current_a=current,breaking_capacity_ka=ka,residual_current_ma=30 if category=='RCBO' else None,phase=phase,load=load,evidence='PDF sơ đồ nguyên lý; trang 1' if panel.startswith(('BV','DB')) else 'PDF sơ đồ nguyên lý; trang '+('1' if panel=='PX1' else '2'),extraction_method='visual_transcription')

pdf=[]
for p in ['BV1','BV2']:
 pdf.append(breaker(p,'Q0',3,32,10))
 specs=[('L1',1,10,6,'MCB','B'),('S1',2,16,4.5,'RCBO','A'),('L2',1,16,6,'MCB','A'),('L3',1,16,6,'MCB','C'),('DC',2,20,6,'MCB','B')]
 if p=='BV1':specs+=[('S2',2,20,6,'MCB','A')]
 specs+=[('TTLL',1,16,6,'MCB','C' if p=='BV1' else None),('DP',1,16,6,'MCB','C' if p=='BV1' else None)]
 pdf.extend(breaker(p,*s) for s in specs)
pdf.extend([breaker('DB.HT','Q0',2,25,6),breaker('DB.HT','L1',1,10,6,'MCB','A'),breaker('DB.HT','S1',2,16,4.5,'RCBO','B'),breaker('DB.HT','AC1',1,20,6,'MCB','C')])
for p,n,start,main in [('PX1',6,1,3),('PX2',3,7,2)]:
 pdf.append(breaker(p,'Q0',main,20,10))
 for i in range(start,start+n):
  pdf.append(breaker(p,'P'+str(i),1,16,10,load='Bơm'))
  pdf.append(breaker(p,'V'+str(i).zfill(2),1,10,10,load='Van điện từ'))
 pdf.append(breaker(p,'MDK',2,10,4.5,load='Mạch điều khiển'))
 for i in [1,2]:pdf.append(breaker(p,'SPARE'+str(i),1,16,10,load='Dự phòng'))
assert len(pdf)==47

quote=[]
for order in ['447','457']:
 sheet=next(s for s in read(OUT/order/'quote-cells.json') if s['sheet'].strip()=='Code')
 ranges=[('BV1',19,37),('BV2',38,56),('DB.HT',57,65)] if order=='447' else [('PX1',19,36),('PX2',37,54)]
 for row in sheet['rows']:
  panel=next((p for p,a,b in ranges if a<=row['row']<=b),None)
  if not panel:continue
  cells={re.sub(r'\d','',c['cell']):c['cached'] for c in row['cells']}
  if not isinstance(cells.get('G'),(int,float)) or not cells.get('C'):continue
  text=str(cells['C']);spec=quote_spec(text)
  quote.append({**spec,'order':order,'panel':panel,'quantity':cells['G'],'model':cells.get('D'),'brand':cells.get('E'),'unit':cells.get('F'),'evidence':f"Code !C{row['row']}:G{row['row']}",'row':row['row']})

cad=[]
for order in ['447','457']:
 for r in read(OUT/order/'cad-visible-occurrences.json'):
  b=r.get('visible_bounds_mm')
  if not b:continue
  x,y=(b[0]+b[2])/2,(b[1]+b[3])/2
  if order=='447':
   panel='BV1' if y>-3500 else 'BV2'
   face='mounting_plate' if -5500<x<-4900 else 'outer_door' if -6300<x<-5700 else 'inner_door' if -7200<x<-6500 else 'side_projection' if -4750<x<-4250 else None
  else:
   panel='PX1' if y>11000 else 'PX2'
   face='mounting_plate' if -96400<x<-95500 else 'inner_door' if -97300<x<-96450 else 'outer_door' if -98200<x<-97400 else 'side_projection' if -95400<x<-94800 else None
  # Ownership windows are audit sheet zones, not drilling/mounting boundaries.
  r.update(order=order,panel=panel,owner_face=face,ownership_basis='Visible geometry centre in reviewed source-sheet view zone; not INSERT origin',exact_model_verified=False)
  cad.append(r)
write(OUT/'cad-face-occurrences.json',cad)
write(OUT/'pdf-protection-transcription.json',pdf)
write(OUT/'quote-itemized.json',quote)

auxiliary=[]
for p in ['BV1','BV2']:
 for category,qty,note in [('LIGHT',3,'RYB → RST, 220V/5W ghi trong BOM'),('FUSE',4,'SLD có 3 bảo vệ đèn + 1 điều khiển; BOM chỉ ghi 3'),('CONTACTOR',2,'SLD/BOM 1P 16A'),('RELAY',2,'BOM in PDF'),('TIMER',1,'24h'),('SELECTOR_3_POSITION',1,'Auto-Off-Manual'),('SWITCH_2_POSITION',2,'CT1/CT2 là công tắc')]:
  auxiliary.append({'panel':p,'category':category,'quantity':qty,'evidence':'PDF 447 trang 1: SLD / bảng BOM','note':note})
for p,n in [('PX1',6),('PX2',3)]:
 auxiliary.extend([{'panel':p,'category':'CONTACTOR','quantity':2*n,'evidence':'PDF 457 trang '+('1' if p=='PX1' else '2'),'note':f'{n} bơm 2P16A + {n} van 2P10A'}, {'panel':p,'category':'TIMER','quantity':n//3,'evidence':'PDF 457 trang '+('1' if p=='PX1' else '2'),'note':'Timer 24h'}])
write(OUT/'pdf-auxiliary-transcription.json',auxiliary)

import ezdxf
from ezdxf import bbox
exploded=[]
source=ezdxf.readfile(ROOT/'tmp/order_audit/457/source.dxf')
for e in source.modelspace().query('LWPOLYLINE'):
 b=bbox.extents([e]);x,y=(b.extmin.x+b.extmax.x)/2,(b.extmin.y+b.extmax.y)/2
 if not (-96400<x<-95500 and abs(b.size.y-82)<.01 and (abs(b.size.x-216)<.01 or abs(b.size.x-108)<.01)):continue
 n=round(b.size.x/18);splits=[]
 for line in source.modelspace().query('LINE'):
  a,z=line.dxf.start,line.dxf.end
  if abs(a.x-z.x)<.01 and b.extmin.x+.01<a.x<b.extmax.x-.01 and abs(min(a.y,z.y)-b.extmin.y)<.01 and abs(max(a.y,z.y)-b.extmax.y)<.01:splits.append(line.dxf.handle)
 exploded.append({'panel':'PX1' if y>11000 else 'PX2','outline_handle':e.dxf.handle,'internal_divider_handles':splits,'candidate_slots':n,'divider_count':len(splits),'pitch_mm':18,'height_mm':82,'model_identification':'unresolved','candidate_interpretation':'NCH8-20 row matching quotation quantity; geometry alone does not prove contactor type/rating'})
assert sorted(r['candidate_slots'] for r in exploded)==[6,12]
assert all(r['divider_count']==r['candidate_slots']-1 for r in exploded)
write(OUT/'457/exploded-row-geometry.json',exploded)

comparison=[]
for d in pdf:
 q=[r for r in quote if r['panel']==d['panel'] and r['category']==d['category'] and r['poles']==d['poles'] and r['current_a']==d['current_a']]
 physical=[r for r in cad if r['panel']==d['panel'] and r['owner_face']=='mounting_plate' and r['effective_name']=='BKN-LS' and r['properties'].get('Visibility1')==f"{d['poles']}P-BKN"]
 match=q[0] if len(q)==1 else None
 differences=[]
 if match and match['breaking_capacity_ka']!=d['breaking_capacity_ka']:differences.append('Khả năng cắt khác PDF')
 if d['category']=='RCBO':differences.append('CAD dùng hình BKN; chưa chứng minh RCBO và cực bảo vệ 1P+N')
 if not physical:differences.append('Chưa tìm thấy CAD thân thiết bị trên mặt lắp tương ứng')
 comparison.append({'key':d['panel']+'.'+d['tag'],'pdf':d,'quote_group':match,'candidate_cad_handles':[r['handle'] for r in physical],
  'cad_tag_binding':'unresolved: candidate group is not individual circuit identification','status':'different' if differences else 'needs_model_and_tag_binding','issues':differences,'release_ready':False})

issues=[
 {'order':'447','item':'BV1/BV2 contactor','pdf':'2 × 1P 16A / tủ','quote':'1 × MC-18b 3P 18A / tủ','cad':'1 × MC-12a; trạng thái 12A / tủ','action':'Đối chiếu thiết kế điều khiển và mã contactor; không đổi hình rồi coi đủ 2 contactor.'},
 {'order':'447','item':'Cầu chì','pdf':'SLD: 3 cầu chì đèn + 1 điều khiển; BOM: 3 / tủ','quote':'4 / tủ','cad':'4 thân / tủ','action':'Giữ bất đồng SLD/BOM; báo giá và CAD trùng số lượng 4.'},
 {'order':'447','item':'Relay và công tắc 2 vị trí','pdf':'BOM: 2 relay + 2 công tắc / tủ BV','quote':'Không có dòng riêng','cad':'Chưa thấy đủ thiết bị tương ứng','action':'Làm rõ phương án điều khiển đã thay đổi; không tự xóa khỏi sơ đồ.'},
 {'order':'447','item':'DB.HT','pdf':'SLD tổng 25A; BOM 20A; đầu vào từ BV1 một pha nhưng nhánh ghi A/B/C','quote':'Tổng 2P 25A','cad':'Chưa xác định được bộ bố trí DB.HT trong DWG','action':'Không suy nguồn ba pha từ chữ pha; cần đồng bộ SLD/BOM và bổ sung bản bố trí DB.HT.'},
 {'order':'447','item':'Vỏ BV','pdf':'H600 W400 D250 t1.5 ngoài trời','quote':'H700 W500 D250 t1.2 trong nhà','cad':'H700 W500 D250; bảng vật liệu t1.2 trong nhà','action':'Ghi nhận thay đổi kích thước, vật liệu và môi trường; không ép các nguồn thành một giá trị.'},
 {'order':'457','item':'Contactor','pdf':'12 PX1 / 6 PX2; 2P 16A bơm, 2P 10A van','quote':'18 tổng NCH8-20 2P 20A','cad':'Hình rời: hàng 216×82 có 12 ô, hàng 108×82 có 6 ô, bước 18; chưa có định danh NCH8-20','action':'Đã rà LINE/LWPOLYLINE và số ô; chưa chứng minh chức năng, model và dòng điện từ hình giản lược.'},
 {'order':'457','item':'Vỏ và chân đế','pdf':'PX1 W400 H600 D250; PX2 kích thước cần đọc lại ảnh','quote':'Thân H900 W600 / H700 W500, D250; treo tường','cad':'Thân 900/700 + chân 100; tổng 1000/800; đặt bệ','action':'Tách chiều cao thân và chân; kiểu lắp treo/đặt bệ vẫn khác.'},
 {'order':'457','item':'Nguồn 24VDC','pdf':'Bộ đổi nguồn 220/24V bên tải; chưa xác nhận số bộ trong tủ','quote':'Asia 1 / tủ','cad':'S8FS-C05024J; CAD Side trên mặt thiết bị, 1 / tủ','action':'Không bỏ sót vì tên mặt Side; cần đối chiếu công suất, điện áp và model.'},
 {'order':'nguon','item':'A và CT','pdf':'A thang 0–50 A; 3 CT 63/5','quote':'Không thuộc hai báo giá này','cad':'Đã có A và 3 CT thực; A thang CAD 0–500, CT MSQ-30 chưa xác nhận tỷ số','action':'Đã sửa thiếu thư viện; thang đo và tỷ số còn cần chọn đúng biến thể.'},
]
inventory=inventory_diagnostics();write(OUT/'catalog-inventory-diagnostics.json',inventory)
counts={p:sum(d['quantity'] for d in pdf if d['panel']==p) for p in ['BV1','BV2','DB.HT','PX1','PX2']}
quote_counts={p:sum(q['quantity'] for q in quote if q['panel']==p and q['category'] in ('MCB','RCBO')) for p in counts}
cad_counts={p:sum(1 for r in cad if r['panel']==p and r['owner_face']=='mounting_plate' and r['effective_name']=='BKN-LS' and r['properties'].get('Visibility1','').endswith('-BKN')) for p in counts}
assert counts=={'BV1':9,'BV2':8,'DB.HT':4,'PX1':16,'PX2':10}
assert counts==quote_counts
assert cad_counts=={'BV1':9,'BV2':8,'DB.HT':0,'PX1':16,'PX2':10}
review={'release_ready':False,'pdf_extraction_method':'Manual visual transcription of rendered scanned PDFs; not an end-to-end AI/OCR accuracy certificate','counts_pdf':counts,'counts_quote':quote_counts,'counts_cad_bodies':cad_counts,'issues':issues,'protection_rows':comparison,'unanalysed':['Exploded NCH8 geometry identity','Terminal/wire/busbar schedules and exact ratings','Full per-circuit CAD handle bindings','Missing DB.HT view','Control scheme revisions and drilling/E-view verification']}
write(OUT/'reconciliation.json',review)
with (OUT/'protection-comparison.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['Tủ','Tag','Loại','Cực PDF','A PDF','kA PDF','Pha PDF','Ô báo giá','kA báo giá','Model báo giá','CAD ứng viên','Kết luận'])
 for r in comparison:
  d=r['pdf'];q=r['quote_group'] or {};w.writerow([d['panel'],d['tag'],d['category'],d['poles'],d['current_a'],d['breaking_capacity_ka'],d['phase'],q.get('evidence'),q.get('breaking_capacity_ka'),q.get('model'),','.join(r['candidate_cad_handles']),'; '.join(r['issues']) or 'Chưa xác nhận model và liên kết tag'])

def esc(v):return html.escape(str(v if v is not None else 'Chưa xác nhận'))
parts=['<!doctype html><meta charset="utf-8"><title>Đối chiếu đơn 447 – 457</title><style>body{font:15px Arial;margin:28px;color:#203342}table{border-collapse:collapse;width:100%;margin:16px 0}th,td{padding:8px;border:1px solid #ccd5dc;text-align:left}th{background:#eaf1f5}img{width:100%;border:1px solid #ccd5dc}summary{cursor:pointer;padding:12px;background:#edf3f6}a{color:#126588}.notice{padding:18px;background:#fff0cc}input{padding:10px;width:350px}</style><h1>Đối chiếu PDF • Báo giá • CAD: đơn 447 và 457</h1><p class="notice">Bản kiểm tra kỹ thuật, chưa đủ điều kiện sản xuất. 47 thiết bị bảo vệ đã được bóc riêng từng tag. Số lượng trùng chưa chứng minh đúng model, cực bảo vệ, kA, lỗ khoét hoặc mạch điều khiển.</p><p>PDF là bản scan, được đọc trực quan; bảng này không phải chứng nhận AI tự đọc đúng toàn bộ. CAD đọc qua AutoCAD, lấy trạng thái block hiện hành và biên hình nhìn thấy; không đếm nắp và mặt bên thành thiết bị mới.</p><p><a href="protection-comparison.csv">CSV từng thiết bị</a> · <a href="reconciliation.json">JSON kết quả</a> · <a href="quote-itemized.json">Toàn bộ dòng báo giá thuộc các tủ</a> · <a href="cad-face-occurrences.json">CAD: handle, mặt và trạng thái</a></p><table><tr><th>Tủ</th><th>PDF</th><th>Báo giá</th><th>Thân CB CAD</th></tr>']
for p in counts:parts.append(f'<tr><td>{p}</td><td>{counts[p]}</td><td>{quote_counts[p]}</td><td>{cad_counts[p]}</td></tr>')
parts.append('</table><h2>Các điểm phải xử lý</h2><table><tr><th>Đơn / mục</th><th>PDF</th><th>Báo giá</th><th>CAD</th><th>Xử lý</th></tr>')
for r in issues:parts.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in [r['order']+' / '+r['item'],r['pdf'],r['quote'],r['cad'],r['action']])+'</tr>')
parts.append('</table><h2>Đối chiếu từng thiết bị bảo vệ</h2><input placeholder="Lọc theo tủ, tag, RCBO…" oninput="document.querySelectorAll(\'#items tr[data-item]\').forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(this.value.toLowerCase()))"><table id="items"><tr><th>Tủ / tag</th><th>PDF</th><th>Báo giá</th><th>CAD / kết luận</th></tr>')
for r in comparison:
 d=r['pdf'];q=r['quote_group'] or {};parts.append('<tr data-item><td>'+esc(r['key'])+'</td><td>'+esc(f"{d['category']} {d['poles']}P {d['current_a']}A {d['breaking_capacity_ka']}kA")+'</td><td>'+esc(q.get('original_text'))+'<br>'+esc(q.get('evidence'))+'</td><td>'+esc('; '.join(r['issues']) or 'Nhóm hình có đủ số cực; chưa xác nhận model/tag')+'</td></tr>')
parts.append('</table><h2>Các mặt CAD nguồn</h2>')
parts.append('<details><summary>Thiết bị phụ trên PDF, đọc độc lập với báo giá</summary><table><tr><th>Tủ</th><th>Loại</th><th>SL</th><th>Ghi chú</th></tr>')
for r in auxiliary:parts.append('<tr>'+''.join('<td>'+esc(r[k])+'</td>' for k in ['panel','category','quantity','note'])+'</tr>')
parts.append('</table></details>')
for o in ['447','457']:
 for i in [1,2]:parts.append(f'<details open><summary>Đơn {o} — bộ {i}: cánh trong, cánh ngoài, mặt thiết bị và mặt bên</summary><img src="{o}/cad-panel-{i}.png"></details>')
parts.append('<h2>Thư viện đã sửa</h2><p>'+esc(f"{inventory['assets']} hình CAD được lập chỉ mục. {len(inventory['unclassified_profiles'])} hồ sơ chưa phân loại vẫn được liệt kê riêng, không bị báo thành thiết bị không có CAD.")+'</p><a href="../nguon-catalogtb-review/review.html">Xem lại nguồn: đã bố trí CAD A và 3 CT</a>')
parts.append('<h2>CAD nguồn dùng làm chuẩn rà soát</h2><p>Các bản bên dưới giữ bản vẽ nguồn và thêm ghi chú audit; chưa phải bản tự sinh mới đã sửa hết mạch điện.</p><p><a href="447/ORDER-447-source-review.dwg">447 DWG</a> · <a href="447/ORDER-447-source-review.dxf">447 DXF</a> · <a href="457/ORDER-457-source-review.dwg">457 DWG</a> · <a href="457/ORDER-457-source-review.dxf">457 DXF</a></p>')
(OUT/'review.html').write_text('\n'.join(parts),encoding='utf8')
# Preserve all source views as a measurable review baseline; no inferred substitutions.
import ezdxf
for o in ['447','457']:
 doc=ezdxf.readfile(ROOT/f'tmp/order_audit/{o}/source.dxf');doc.layers.new('AIDE_AUDIT_NOT_RELEASED',dxfattribs={'color':1})
 x,y=(-7350,-1000) if o=='447' else (-98200,13500)
 doc.modelspace().add_mtext('AUDIT REFERENCE - NOT RELEASED FOR PRODUCTION\\PSource geometry preserved. See reconciliation.json for independent PDF/quote/CAD discrepancies.',dxfattribs={'insert':(x,y),'char_height':25,'width':3500,'layer':'AIDE_AUDIT_NOT_RELEASED'})
 doc.saveas(OUT/o/f'ORDER-{o}-source-review.dxf')
manifest=read(OUT/'source-manifest.json')
checks=[{'order':o,'kind':k,'unchanged':hashlib.sha256(Path(v['path']).read_bytes()).hexdigest()==v['sha256']} for o,files in manifest.items() for k,v in files.items()]
assert all(r['unchanged'] for r in checks);write(OUT/'source-integrity-check.json',checks)
print(json.dumps({'pdf':counts,'quote':quote_counts,'cad_bodies':cad_counts,'indexed_views':inventory['assets'],'release_ready':False}))
