"""Reproducible preliminary TDT layout from the supplied scanned schematic."""
from pathlib import Path
import json, shutil, html
import ezdxf
from ezdxf import bbox
from tu1_conductor_schedule import build_schedule
from tu1_installation_model import build_installation
from ezdxf.addons import Importer
from ezdxf.addons.drawing import RenderContext, Frontend, layout, config
from ezdxf.addons.drawing.svg import SVGBackend

ROOT = Path(__file__).resolve().parents[2]
CAT = ROOT / 'BE_AIDE/data/CatalogTB'
SELECTION_RULES=json.loads((CAT/'ai_selection_rules.json').read_text(encoding='utf-8'))
OUT = ROOT / 'output/Tu1_NhaNoiTru'
OUT.mkdir(parents=True, exist_ok=True)
(OUT/'cad_thiet_bi').mkdir(exist_ok=True)
sources = {
 'Rittal – thiết kế hệ tủ': 'https://webinfo.rittal.com/com-en/ri4power',
 'ABB – IEC 61439': 'https://library.e.abb.com/public/32f98df19e5849e1b6b5d6172e00be73/2CPC000313B0201.pdf',
 'Chọn tiết diện': 'https://www.electrical-installation.org/enwiki/Sizing_and_protection_of_conductors',
 'Thanh lược LS': 'https://www.ls-electric.com/upload/customer/download/1483/MCB_E_180131.pdf',
 'LS MCCB': 'https://www.ls-electric.com/ko/product/view/P01021',
 'LS MCB': 'https://www.ls-electric.com/upload/customer/download/1483/150905_MCB_E.pdf',
 'CHINT': 'https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/industrial-control/indicator-light/nd16/catalog/ND16-INDICATOR-LIGHT-Catalog.pdf',
 'HOBUT': 'https://www.hobut.co.uk/instrumentation-and-control-products/analogue-panel-meters/90-degree-din-panel-meter-range/moving-iron-panel-meters-2/',
 'Kraus & Naimer': 'https://ecat.krausnaimer.com/at_en/70009108',
}

def rect(m,x,y,w,h,layer='FRAME'):
 return m.add_lwpolyline([(x,y),(x+w,y),(x+w,y+h),(x,y+h)],close=True,dxfattribs={'layer':layer})
def text(m,t,x,y,h=7,layer='TEXT'):
 return m.add_text(t,dxfattribs={'height':h,'insert':(x,y),'layer':layer,'style':'REPORT'})
def newdoc():
 d=ezdxf.new('R2013');d.units=ezdxf.units.MM
 d.styles.new('REPORT',dxfattribs={'font':'arial.ttf'})
 for name,col in [('FRAME',7),('DEVICE',7),('TEXT',7),('DUCT',8),('RAIL',8),('RESERVED',3),('CUTOUT',1)]:
  d.layers.new(name,dxfattribs={'color':col})
 return d

definitions={}
def library(code,key,view_id):
 p=next(CAT.rglob(key+'/thong_tin_thiet_bi.json'))
 info=json.loads(p.read_text(encoding='utf-8-sig'))
 view=next(v for v in info['cad_don'] if v['id_hinh_goc']==view_id)
 assert view.get('bo_tri_trong_tu',{}).get('cho_phep_chen',True)
 src=p.parent/view['duong_dan'];dst=OUT/'cad_thiet_bi'/f'{code}.dxf';shutil.copy2(src,dst)
 ext=bbox.extents(ezdxf.readfile(dst).modelspace())
 definitions[code]={'file':str(dst.relative_to(OUT)).replace('\\','/'),'catalog_profile':str(p.relative_to(ROOT)).replace('\\','/'),
  'view_id':view_id,'face':view['huong_nhin'],'width_mm':round(ext.size.x,3),'height_mm':round(ext.size.y,3),
  'status':'CAD thư viện, đúng dòng/cỡ khung; không xác nhận mã đặt hàng bằng hình học'}

library('MCCB_TS250_3P','TS100_TS160_TS250','D02_cluster5-V003')
library('MCB_BKN_2P','BKN_2P','LS-D02-C3-I03-2P')
library('MCB_BKN_3P','BKN_3P','LS-D02-C3-I03-VIEW-3P-FRONT-VIEW')
library('SELECTOR_REFERENCE','ChuyenMachVon','C04_cluster5-V002')
definitions['SELECTOR_REFERENCE']['status']='CAD công tắc chọn vôn tham khảo; chưa xác nhận cùng kích thước CH10 A007'
library('LAMP_SIDE_REFERENCE','CHINT_DenBaoPha','C03_cluster6-V010')
library('FUSE_BANK_3P','Day3DeCauChi_KieuHop','C03_cluster4-V001')
library('PE_BAR','ThanhE_10x115','B_a9f51566bd67')
library('N_BAR','ThanhN_10x160','B_8ce86a6ae65d')
for code,role in [('PE_BAR','PE'),('N_BAR','N')]:
 p=ROOT/definitions[code]['catalog_profile'];identity=json.loads(p.read_text(encoding='utf-8'))['nhan_dien_ai']
 assert identity['vai_tro_dien']==role and identity['tu_dong_chon_theo_vai_tro']
 definitions[code]['role']=role
 definitions[code]['status']=identity['can_cu']+'; chưa kiểm tra đủ đầu dây và dòng cho tủ 19 nhánh'
library('VOLTMETER_OMEGA500','Omega_BE-96_500V','C04_cluster5-V010')
definitions['VOLTMETER_OMEGA500']['status']='CAD Omega BE-96 0–500 V trong thư viện; người dùng đồng ý dùng thay yêu cầu PDF 0–600 V cho bản thử'

# Clearly separate dimensional representations from manufacturer production CAD.
for code,w,h in [('LAMP_ND16_FRONT',30,30)]:
 d=newdoc();m=d.modelspace()
 if code=='LAMP_ND16_FRONT':
  m.add_circle((0,0),15);m.add_circle((0,0),12)
 elif code=='VOLTMETER_D96':
  rect(m,-48,-48,96,96);rect(m,-40,-30,80,60)
  m.add_arc((0,-24),36,30,150);m.add_line((0,-24),(22,4))
  text(m,'0 - 600 V AC',-31,-39,5)
 else:
  rect(m,-w/2,-h/2,w,h,'RESERVED');text(m,'FU',-6,-2,4)
 f=OUT/'cad_thiet_bi'/f'{code}.dxf';d.saveas(f)
 definitions[code]={'file':str(f.relative_to(OUT)).replace('\\','/'),'face':'Mặt trước','width_mm':w,'height_mm':h,
  'status':('Mặt trước dựng theo đường kính Ø30 của catalog CHINT, không phải CAD hãng' if code.startswith('LAMP') else
   'Biểu diễn bao mặt DIN96 theo dòng HOBUT; chưa có CAD hãng/chiều sâu' if code.startswith('VOLT') else
   'Ô dự trù kích thước gần đúng, không phải CAD sản phẩm; chưa chọn dòng cầu chì')}

loads=['Chiếu sáng hành lang, cầu thang','Ổ cắm hành lang, wifi','Tủ T1.1','Tủ T1.2','Tủ T1.3','Tủ T1.4',
 'Tủ T2.1','Tủ T2.2','Tủ T2.3','Tủ T3.1','Tủ T3.2','Tủ T3.3','Tủ T4.1','Tủ T4.2','Tủ T4.3','Tủ T5.1','Tủ T5.2','Tủ T5.3','Tủ nhà BV (TĐ-5)']
kw=[1,3,10.2,10.2,5.8,5.8]+[10.2]*12+[7]
branches=[]
for n,(load,power) in enumerate(zip(loads,kw),1):
 poles=2 if n in [1,2,5,6] else 3
 req=10 if n==1 else 30 if n in [5,6] else 20
 chosen=32 if req==30 else req
 cable='2x1.5 mm²' if n==1 else '2x2.5 + PE2.5 mm²' if n==2 else '2x6 + PE6 mm²' if n in [5,6] else '4x4 + PE4 mm²'
 branches.append({'id':f'L{n}','load':load,'power_kw':power,'poles':poles,'source_current_A':req,'proposed_current_A':chosen,
  'source_breaking_kA':6,'brand':'LS Electric','model':f'BKN {poles}P C{chosen}A','curve_status':'Đề xuất C; sơ đồ không ghi đường cong',
  'cable_source':cable,'cad':'MCB_BKN_2P' if poles==2 else 'MCB_BKN_3P',
  'status':'Cần phê duyệt thay 30 A bằng 32 A sau kiểm tra cáp và phối hợp bảo vệ' if req==30 else 'Phù hợp số cực/dòng/6 kA; chưa kiểm tra chọn lọc với MCCB tổng'})

bom=[
 {'name':'MCCB tổng','qty':1,'brand':'LS Electric','model':'Susol TS250H 3P, trip unit 200 A','requirement':'3P 200 A – 85 kA','cad':'MCCB_TS250_3P','note':'Chọn bộ trip và Icu 85 kA tại điện áp hệ thống; chưa chốt mã đặt hàng đầy đủ'},
 {'name':'Shunt trip tích hợp trong MCCB tổng','qty':1,'brand':'LS Electric','model':'SHT tương thích TS250, chọn kèm MCCB','requirement':'Nhận tín hiệu bộ phận giám sát cháy','cad':'MCCB_TS250_3P','note':'Phụ kiện bên trong MCCB, không chiếm một ô bố trí riêng; cần chọn đúng điện áp cuộn cắt và tín hiệu báo cháy'},
 {'name':'MCB nhánh L1','qty':1,'brand':'LS Electric','model':'BKN 2P C10A','requirement':'2P 10 A – 6 kA','cad':'MCB_BKN_2P','note':'Đường cong C đề xuất'},
 {'name':'MCB nhánh L2','qty':1,'brand':'LS Electric','model':'BKN 2P C20A','requirement':'2P 20 A – 6 kA','cad':'MCB_BKN_2P','note':'Đường cong C đề xuất'},
 {'name':'MCB nhánh L5–L6','qty':2,'brand':'LS Electric','model':'BKN 2P C32A (đề xuất có điều kiện)','requirement':'PDF: 2P 30 A – 6 kA','cad':'MCB_BKN_2P','note':'Giữ yêu cầu gốc 30 A trong dữ liệu; không tự chốt 32 A'},
 {'name':'MCB nhánh ba pha','qty':15,'brand':'LS Electric','model':'BKN 3P C20A','requirement':'3P 20 A – 6 kA','cad':'MCB_BKN_3P','note':'L3–L4, L7–L19; không phải 3P+N'},
 {'name':'Đèn báo ba pha R/Y/B','qty':3,'brand':'CHINT','model':'ND16-22C/2, AC/DC 230 V, R / Y / B','requirement':'3 đèn báo pha R/Y/B','cad':'LAMP_ND16_FRONT','note':'230 V giả định đấu pha–N. Nếu đấu pha–pha phải đổi 400 V; CAD trước dựng theo catalog'},
 {'name':'Vôn kế kim','qty':1,'brand':'Omega','model':'BE-96, AC 0–500 V','requirement':'PDF: 0–600 V; người dùng cho dùng 0–500 V trong bản thử','cad':'VOLTMETER_OMEGA500','note':'Dùng CAD Omega sẵn có theo yêu cầu người dùng; thay đổi dải đo được lưu rõ'},
 {'name':'Công tắc chọn vôn','qty':1,'brand':'Kraus & Naimer','model':'CH10 A007, OFF + 3 điện áp dây + 3 điện áp pha; item 70009108','requirement':'Ký hiệu công tắc chọn vôn trong PDF','cad':'SELECTOR_REFERENCE','note':'CAD thư viện tương tự chức năng; không dùng tọa độ này để khoan theo mã CH10'},
 {'name':'Dãy 3 đế cầu chì 1 cực kiểu hộp và dây chảy','qty':1,'brand':'Có thể chọn CHINT / Schneider; chưa xác nhận hãng của CAD','model':'Dãy 3 đế lắp ray, CAD 54 × 80 mm; dây chảy đề xuất 2 A gG','requirement':'PDF chỉ ghi Fuse, không ghi số lượng/dòng','cad':'FUSE_BANK_3P','note':'Dùng CAD dãy 3 đế có sẵn; chưa chốt chuẩn dây chảy và mã hãng, không suy ra 10x38 chỉ từ hình'},
 {'name':'Thanh tiếp địa PE','qty':1,'brand':'Chưa xác định hãng; có thể chọn hãng khác LS','model':'Thanh E CAD gốc 10 × 115 mm','requirement':'Đấu dây PE và liên kết vỏ tủ','cad':'PE_BAR','note':'Đúng hồ sơ E riêng, xoay 90° trong mặt lỗ đấu nối. Giữ nguyên CAD gốc, không kéo dài hoặc thêm lỗ; số lỗ vẫn không chứng minh dòng/đầu dây phù hợp'},
 {'name':'Thanh trung tính N','qty':1,'brand':'Chưa xác định hãng; có thể chọn hãng khác LS','model':'Thanh N CAD gốc 10 × 160 mm','requirement':'Đấu dây trung tính các nhánh','cad':'N_BAR','note':'Đúng hồ sơ N riêng, xoay 90° trong mặt lỗ đấu nối. Giữ nguyên CAD gốc, không kéo dài hoặc thêm lỗ; chưa xác nhận dòng/đầu dây, cần gá cách điện'},
 {'name':'Hệ phân phối ba pha','qty':1,'brand':'Gia công / chọn hãng phù hợp','model':'Theo dòng 200 A và kiểm tra chịu ngắn mạch','requirement':'Phân phối 19 nhánh','cad':None,'note':'Đường phân phối là vùng dự trù; cần thiết kế tiết diện, cách điện và gối đỡ'},
 {'name':'Vỏ tủ và vật tư bố trí','qty':1,'brand':'Nhà chế tạo tủ','model':'H1000 x W600 x D300 mm; tấm lắp dự kiến 900x500','requirement':'Kích thước PDF 1000x600x300','cad':None,'note':'Quy ước H-W-D giả định theo tủ đứng; ray DIN, máng dây, nhãn, đầu cốt cần chi tiết hóa'},
]

doc=newdoc();ms=doc.modelspace();instances=[]
for code,item in definitions.items():
 src=ezdxf.readfile(OUT/item['file']);block=doc.blocks.new(code)
 imp=Importer(src,doc);imp.import_entities(src.modelspace(),target_layout=block);imp.finalize()

def place(tag,code,x,y,area,label=None,rotation=0):
 ms.add_blockref(code,(x,y),dxfattribs={'layer':'DEVICE','rotation':rotation})
 item=definitions[code]
 w,h=(item['height_mm'],item['width_mm']) if rotation%180==90 else (item['width_mm'],item['height_mm'])
 instances.append({'id':tag,'definition':code,'x_mm':x,'y_mm':y,'rotation_deg':rotation,'scale':1,'area':area,'face':item['face'],
  'width_mm':w,'height_mm':h})
 # Equipment tags stay in BOM/JSON; no external device labels in drawing.

# Three separately readable views; coordinate origin of each is lower left.
for offset,title in [(0,'BEN TRONG - TAM LAP'),(800,'CANH NGOAI - DO LUONG'),(1600,'CANH TRONG - TAM CHE (DE XUAT)')]:
 rect(ms,offset,0,600,1000);text(ms,title,offset+35,1030,13)
 text(ms,'W600 x H1000 / D300 mm',offset+90,-35,10)
rect(ms,50,50,500,900)
# Two inward-facing stacks and schematic fishbone distribution.
for x in [65,495]:rect(ms,x,155,30,560,'DUCT')
rect(ms,80,915,440,25,'RESERVED');text(ms,'DU TRU DAU NOI NGUON VA KHONG GIAN CAP',90,922,6)
place('QF0','MCCB_TS250_3P',300,815,'ben_trong','QF0 TS250H 3P 200A / 85kA')

place('FU1-FU3','FUSE_BANK_3P',130,835,'ben_trong','FU1-FU3 / DAY 3 DE')
place('N','N_BAR',465,830,'ben_trong','N / GA CACH DIEN')
place('PE','PE_BAR',300,95,'ben_trong','PE / NOI VO TU',rotation=90)
bus_geometry=[]
for net,x,col in [('R',265,1),('S',295,2),('T',325,5),('N',355,6)]:
 layer='BUS_'+net
 doc.layers.new(layer,dxfattribs={'color':col})
 rect(ms,x-4,145,8,590,layer)
 text(ms,net,x-3,722,7)
 bus_geometry.append({'net':net,'trunk_center_x_mm':x,'y_range_mm':[145,735],'drawing_width_mm':8,'depth_mm':None,'status':'Schematic route only; not fabricated conductor dimensions'})
for net,x in [('R',265),('S',295),('T',325)]:
 ms.add_line((x,735),(x,715),dxfattribs={'layer':'BUS_'+net,'lineweight':50})
ordered=sorted(branches,key=lambda b:(-b['proposed_current_A'],-b['poles'],int(b['id'][1:])))
side_groups=[[],[]];side_heights=[0,0];side_currents=[0,0]
for branch in ordered:
 side=min(range(2),key=lambda i:(len(side_groups[i]),side_heights[i],side_currents[i],i))
 side_groups[side].append(branch);side_heights[side]+=definitions[branch['cad']]['width_mm']+8;side_currents[side]+=branch['proposed_current_A']
layout_order={'sort':'Descending proposed rated current; same rating grouped by poles','policy_status':'User layout preference, not mandatory IEC rule','left':[b['id'] for b in side_groups[0]],'right':[b['id'] for b in side_groups[1]],'side_count':[len(g) for g in side_groups],'rated_current_sum_A':side_currents,'connected_power_sum_kw':[round(sum(b['power_kw'] for b in g),2) for g in side_groups],'count_difference':abs(len(side_groups[0])-len(side_groups[1])),'phase_balance_note':'Giữ L1/L6 pha R, L2 pha S, L5 pha T theo PDF; tải 3P cần dữ liệu thực, không đổi pha theo vị trí trái/phải. Chưa có cos phi, tải đồng thời và dòng từng pha để kiểm tra cân bằng điện.', 'note':'Sum of breaker ratings is only a layout metric, not demand current or phase balance.'}
for group,x,rot in [(side_groups[0],170,-90),(side_groups[1],430,90)]:
 ms.add_line((x,145),(x,710),dxfattribs={'layer':'RAIL'})
 cursor=725
 for branch in group:
  height=definitions[branch['cad']]['width_mm'];cy=cursor-height/2
  place(branch['id'],branch['cad'],x,cy,'ben_trong',rotation=rot)
  
  phase_nets=['R','S','T'] if branch['poles']==3 else [{'L1':'R','L2':'S','L5':'T','L6':'R'}[branch['id']],'N']
  tap_x=x+41 if x<300 else x-41
  for j,net in enumerate(phase_nets):
   yy=cy+(j-(len(phase_nets)-1)/2)*18
   trunk_x={'R':265,'S':295,'T':325,'N':355}[net]
   ms.add_line((trunk_x,yy),(tap_x,yy),dxfattribs={'layer':'BUS_'+net,'lineweight':50})
   bus_geometry.append({'net':net,'branch':branch['id'],'route_xy_mm':[[trunk_x,yy],[tap_x,yy]],'depth_mm':None,'port_status':'Assumed visual inlet; manufacturer terminal map pending'})
  cursor-=height+8
text(ms,'DONG XUONG CA / TUYEN SO BO',210,125,6)
text(ms,'GIAO NHAU KHONG PHAI NOI DIEN - CHUA CHOT CHIEU SAU',75,45,5)
text(ms,'CAP VAO / CAP RA: DU TRU TU DAY TU',82,28,7)
for tag,x,color in [('R',1000,1),('Y',1100,2),('B',1200,5)]:
 place('HL_'+tag,'LAMP_ND16_FRONT',x,875,'canh_ngoai',tag)
 ms.add_circle((x,875),11,dxfattribs={'color':color})
place('PV','VOLTMETER_OMEGA500',1100,720,'canh_ngoai','PV OMEGA 0-500V')
place('SA','SELECTOR_REFERENCE',1100,585,'canh_ngoai','SA CHON VON*')
text(ms,'TDT - NHA NOI TRU',960,950,14)
text(ms,'MAT BEN DEN: XEM CAD THIET BI RIENG',875,180,8)
text(ms,'CHO SAU THAN / DAY NOI MEM QUA BAN LE',875,160,8)
text(ms,'*CAD THAM KHAO, CHUA CHOT LO KHOAN',875,140,8)
# Inner cover: boundaries denote reserved openings, not fabrication holes.
rect(ms,1650,50,500,900)
rect(ms,1820,735,120,135,'RESERVED');text(ms,'DU TRU CUA SO MCCB',1700,890,8)
for x in [1680,1950]:
 rect(ms,x,145,110,570,'RESERVED')
 text(ms,'CUA SO MCB HAI BEN',x,725,6)
text(ms,'THAN CB GAN TAM LAP, KHONG GAN TREN CANH',1635,145,7)
text(ms,'TAM CHE VA LO CAT CAN THIET KE CHI TIET',1660,120,7)
text(ms,'PHUONG AN BO TRI SO BO - DON VI mm - CAD THIET BI KHONG CO GIAN',30,-95,12)
doc.saveas(OUT/'Tu1_TDT_bo_tri.dxf')

checks=[]
internal=[v for v in instances if v['area']=='ben_trong']
for i,a in enumerate(instances):
 offset=0 if a['area']=='ben_trong' else 800
 assert offset <= a['x_mm']-a['width_mm']/2 and a['x_mm']+a['width_mm']/2 <= offset+600
 assert 0<=a['y_mm']-a['height_mm']/2 and a['y_mm']+a['height_mm']/2<=1000
 for b in instances[i+1:]:
  if a['area']==b['area']:
   assert abs(a['x_mm']-b['x_mm']) >= (a['width_mm']+b['width_mm'])/2 or abs(a['y_mm']-b['y_mm']) >= (a['height_mm']+b['height_mm'])/2, (a['id'],b['id'])
assert len(branches)==19 and sum(b['poles']==3 for b in branches)==15
for role in ['PE','N']:
 assert sum(definitions[v['definition']].get('role')==role for v in instances)==SELECTION_RULES['N_PE']['default_quantity_per_cabinet'][role]
assert all(v['scale']==1 for v in instances)
assert not doc.audit().has_errors
checks=['19 nhánh: 15 MCB 3P và 4 MCB 2P',f'{len(instances)} đối tượng bố trí không chồng bao và nằm trong mặt tủ','CAD thiết bị chèn tỷ lệ 1:1, đơn vị mm','DXF audit không có lỗi cấu trúc']

backend=SVGBackend();Frontend(RenderContext(doc),backend,config.Configuration(background_policy=config.BackgroundPolicy.WHITE,color_policy=config.ColorPolicy.BLACK,min_lineweight=0.25,lineweight_scaling=1.5)).draw_layout(ms,finalize=True)
svg=backend.get_string(layout.Page(0,0,layout.Units.mm),settings=layout.Settings())
(OUT/'bo_tri.svg').write_text(svg,encoding='utf-8')
notes=[
 'Tủ 1 được hiểu là tủ đầu tiên trong PDF: TĐT; tủ bơm phía dưới không nằm trong phạm vi.',
 'Kích thước 1000x600x300 được hiểu HxWxD, tấm lắp 900x500 và cánh trong là đề xuất, PDF không có bản vỏ tủ.',
 'L5/L6: yêu cầu gốc 30 A; LS BKN 32 A chỉ đề xuất có điều kiện. Chưa được coi là cấu hình đã duyệt.',
 'Vôn kế Omega BE-96 0–500 V được dùng theo yêu cầu người dùng cho bản thử, thay dải 0–600 V trên PDF.',
 '19 nhánh có tổng tải ghi từng hàng 165,4 kW, khác P_yc 162,0 kW ở đầu bảng. PDF ghi Kdt 0,6 và Ptt 97,2 kW; cần làm rõ trước tính chọn cuối cùng.',
 'Một nhánh dự phòng cuối sơ đồ không có số cực/dòng: chỉ để chỗ trống, chưa tính thêm CB vào 19 nhánh.',
 'PDF không có ampe kế/CT, contactor hay tụ bù cho TĐT, nên không thêm các thiết bị này.',
 'Điện áp mạng 400/230 V và 50 Hz là giả định chọn thiết bị. Chưa xác định IP, nhiệt độ, nguồn và logic báo cháy.',
 'Chưa kiểm tra dòng ngắn mạch thực tại nhánh 6 kA, phối hợp/cascading/chọn lọc tổng–nhánh, RCD cần thiết ở nhánh ổ cắm, sụt áp và bảo vệ cáp theo điều kiện lắp.',
 'Cầu chì và N/PE dùng CAD thật có sẵn trong CatalogTB; shunt trip nằm trong MCCB, không có ô thiết bị riêng. LS ưu tiên cho đóng cắt chính, phụ kiện có thể chọn hãng khác.',
 'Đã sửa thành một thanh PE theo hồ sơ E và một thanh N theo hồ sơ N. Không dùng CAD CauNPE chưa xác định vai trò. Thanh N/PE giữ nguyên CAD gốc. Chọn biến thể 8/13 vị trí khi có hồ sơ xác nhận; không coi tổng số lỗ CAD là số đầu dây. Tủ 19 nhánh còn cần xác nhận khả năng đấu nối; không tự thêm thanh hoặc lỗ.',
 'Chưa phải bản gia công: selector và mặt đèn là CAD tham khảo/dựng; cầu chì và N/PE đã lấy CAD thư viện nhưng cần xác nhận mã hãng, thông số điện, chiều sâu và kiểu gá.',
 'Thanh N phải cách điện với vỏ, thanh PE liên kết vỏ; không gộp N–PE bằng hình thức bố trí chung. Thanh phân phối pha còn là vùng dự trù. Chưa kiểm tra hệ thanh chịu ngắn mạch; không suy ra tủ chịu 85 kA chỉ từ Icu MCCB.',
]
wiring=build_schedule(branches)
(OUT/'danh_sach_chon_day.json').write_text(json.dumps(wiring,ensure_ascii=False,indent=2),encoding='utf-8')
wire_rows=''.join('<tr>'+''.join(f'<td>{html.escape(str(v[k]))}</td>' for k in ['device','from','to','conductor','size','status'])+'</tr>' for v in wiring)
package={'cabinet':'TĐT - Tủ 1 nhà nội trú','source_pdf':'E:/Downloads/2. SO DO TU DIEN (NHA NOI TRU).pdf','source_page':1,
 'units':'mm','size_mm':{'height':1000,'width':600,'depth':300},'status':'Phương án sơ bộ để xem và chỉnh bố trí, chưa duyệt chế tạo/thi công',
 'layout_order':layout_order,'layout_variant':'fishbone_two_sides','busbar_route_draft':bus_geometry,'conductors':wiring,'definitions':definitions,'instances':instances,'bom':bom,'branches':branches,'notes':notes,'sources':sources,'checks':checks}
installation=build_installation(package,OUT)
package['installation_model']='lap_dat_tu1.json'
(OUT/'thiet_ke_va_boc_tach.json').write_text(json.dumps(package,ensure_ascii=False,indent=2),encoding='utf-8')
rows=''.join('<tr>'+''.join(f'<td>{html.escape(str(b[k]))}</td>' for k in ['name','qty','brand','model','requirement','note'])+'</tr>' for b in bom)
branchrows=''.join('<tr>'+''.join(f'<td>{html.escape(str(b[k]))}</td>' for k in ['id','load','power_kw','poles','source_current_A','proposed_current_A','cable_source'])+'</tr>' for b in branches)
links=''.join(f'<li><a href="{html.escape(v)}" target="_blank">{html.escape(k)}</a></li>' for k,v in sources.items())
cadrows=''.join(f'<tr><td>{k}</td><td>{v["face"]}</td><td>{v["width_mm"]} × {v["height_mm"]}</td><td>{html.escape(v["status"])}</td><td><a href="{v["file"]}">DXF riêng</a></td></tr>' for k,v in definitions.items())
page=f'''<!doctype html><html lang="vi"><meta charset="utf-8"><title>Tủ 1 – TĐT nhà nội trú</title>
<style>body{{font:16px system-ui;background:#eef3f7;color:#16324b;margin:0}}main{{max-width:1450px;margin:auto;padding:28px}}section{{background:white;border-radius:14px;padding:24px;margin:18px 0}}h1{{margin:0}}table{{width:100%;border-collapse:collapse;font-size:14px}}td,th{{padding:10px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top}}th{{background:#e9f0f5}}li{{margin:10px 0}}.warn{{border-left:5px solid #e79b20}}a{{color:#0669a6}}.drawing{{overflow:auto}}.drawing img{{width:100%;min-width:900px}}button{{padding:8px 14px;margin:5px;border:1px solid #b9cbd8;border-radius:8px;background:white;cursor:pointer}}</style>
<main><h1>Tủ 1 · Tủ điện tổng TĐT</h1><p>Nhà nội trú · H1000 × W600 × D300 mm · Ưu tiên LS cho thiết bị đóng cắt</p>
<section class="warn"><b>Phương án bố trí sơ bộ</b><p>Đã bóc 19 nhánh và chọn CAD đơn theo mặt nhìn. Bản này để xem, điều chỉnh bố trí; các điểm chưa chốt được ghi bên dưới.</p>
<a href="Tu1_TDT_bo_tri.dxf">Tải DXF bố trí 1:1</a> · <a href="thiet_ke_va_boc_tach.json">Dữ liệu thiết bị và tọa độ</a></section>
<section><h2>Bố trí tủ</h2><p>Trái: bên trong. Giữa: cánh ngoài. Phải: cánh trong đề xuất. Mỗi thiết bị chèn một mặt trước riêng. Nhãn thiết bị được ẩn trên bản vẽ, vẫn giữ trong bảng và JSON. Thanh N và PE giữ nguyên CAD gốc. Hai dãy xếp theo dòng đề xuất từ cao xuống thấp, chia gần đều số CB và chiều cao chiếm chỗ.</p>
<button onclick="document.getElementById('drawing').style.width='100%'">Vừa màn hình</button><button onclick="document.getElementById('drawing').style.width='180%'">Phóng to</button>
<div class="drawing"><img id="drawing" src="bo_tri.svg" alt="Ba mặt bố trí tủ điện tổng"></div></section>
<section><h2>Tham khảo bố trí đồng xương cá</h2><p>Ảnh cho thấy MCCB trên, đồng giữa, hai dãy CB hai bên. Bản DXF hiện tại đã đổi sang hai dãy CB hai bên và tuyến đồng xương cá ở giữa. Tư thế xoay và tuyến đồng là đề xuất bố trí, chưa xác nhận để gia công.</p><div style="display:flex;gap:16px"><img src="anh_tham_khao/ben_trong.png" style="width:45%;object-fit:contain"><img src="anh_tham_khao/canh_ngoai.png" style="width:45%;object-fit:contain"></div><p>Ảnh dùng đèn đỏ/vàng/xanh lá và công tắc chọn vôn ngay dưới đồng hồ. Màu hiển thị được tách khỏi tên pha trong dữ liệu.</p><a href="lap_dat_tu1.json">JSON lắp đặt: thiết bị, điểm đấu, tư thế, dây và hệ đồng</a><p>Trạng thái: bố trí sơ bộ. Các giá trị chưa xác nhận để null; chưa dùng để tự động khoan, gia công đồng hoặc đấu dây.</p></section>
<section><h2>Thiết bị chọn</h2><table><tr><th>Thiết bị</th><th>SL</th><th>Hãng</th><th>Loại / cấu hình đề xuất</th><th>Yêu cầu từ sơ đồ</th><th>Ghi chú</th></tr>{rows}</table></section>
<section><h2>19 nhánh ra theo PDF</h2><table><tr><th>Nhánh</th><th>Phụ tải</th><th>kW</th><th>Cực</th><th>A theo PDF</th><th>A đề xuất</th><th>Cáp theo PDF</th></tr>{branchrows}</table></section>
<section><h2>Chọn dây và thanh đồng theo từng thiết bị</h2><p>Phương án có thể dùng đồng xương cá để phân phối nguồn. Dây ra tải và mạch đo/điều khiển chọn riêng theo từng kết nối. Tiết diện có nhãn dự trù chưa phải kết quả tính chọn cuối cùng; chiều dài chưa đo tuyến.</p><a href="danh_sach_chon_day.json">Tải danh sách chọn dây</a><table><tr><th>Thiết bị</th><th>Từ</th><th>Đến</th><th>Loại dây/thanh dẫn</th><th>Tiết diện</th><th>Căn cứ và điều kiện</th></tr>{wire_rows}</table></section>
<section><h2>CAD dùng trong bản bố trí</h2><p>CAD LS đúng dòng/cỡ khung; các mặt dựng hoặc tương tự chức năng có nhãn riêng. Không dùng CAD tham khảo để khoan cánh.</p><table><tr><th>CAD</th><th>Mặt</th><th>mm</th><th>Mức xác định</th><th>Tệp</th></tr>{cadrows}</table></section>
<section class="warn"><h2>Các điểm cần làm rõ trước chốt thiết kế</h2><ul>{''.join('<li>'+html.escape(n)+'</li>' for n in notes)}</ul></section>
<section><h2>Kiểm tra bản bố trí</h2><ul>{''.join('<li>'+n+'</li>' for n in checks)}</ul><h2>Tài liệu hãng đã đối chiếu</h2><ul>{links}</ul></section></main></html>'''
(OUT/'index.html').write_text(page,encoding='utf-8')
print(json.dumps({'output':str(OUT),'branches':len(branches),'instances':len(instances),'load_sum_kw':round(sum(kw),1),'checks':checks},ensure_ascii=False))
