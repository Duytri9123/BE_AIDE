"""Retain source occurrences separately from clean CAD; evidence based separation review."""
import json,re
from collections import defaultdict,Counter
import ezdxf
from ezdxf import bbox,dynblkhelper
from extract_project_helpers import ROOT,OUT,save
from project_form_rejections import norm
REFERENCES=['https://cache.industry.siemens.com/dl/files/936/107113936/att_1342112/v1/TIP_Planning_manual_SIVACON_S8_2025-02_EN.pdf','https://www.se.com/es/es/faqs/FA384628/']
CRITERIA={
 '1':{'internal_separation':False},
 '2a':{'busbars_from_units':True,'terminals_from_busbars':False},
 '2b':{'busbars_from_units':True,'terminals_from_busbars':True},
 '3a':{'busbars_from_units':True,'units_from_each_other':True,'terminals_and_external_conductors_from_units':True,'terminals_from_busbars':False},
 '3b':{'busbars_from_units':True,'units_from_each_other':True,'terminals_and_external_conductors_from_units':True,'terminals_from_busbars':True},
 '4a':{'busbars_from_units':True,'units_from_each_other':True,'terminals_from_busbars':True,'terminals_per_unit_separated':True,'terminals_compartment':'same_as_associated_unit'},
 '4b':{'busbars_from_units':True,'units_from_each_other':True,'terminals_from_busbars':True,'terminals_per_unit_separated':True,'terminals_compartment':'separate_from_associated_unit'}}
def role(name):
 n=norm(name)
 for key,pattern in [('lamp',r'LIGHT|PILOT|DEN BAO|^DEN (DO|VANG|XANH)'),('lock',r'KHOA|LOCK|LATCH|MS406|AB301'),('busbar',r'THANH DONG|BUSBAR|CU\s*\d+\s*[X×]'),('terminal',r'CAU DAU|CAU TIEP DIA|TERMINAL|PNE.?BAR'),('device',r'MCCB|MCB|ACB|RCBO|RCCB|METASOL|BKN|ABN|CONTACTOR|PLC|ATS|FUSE|VOLTMET|AMPERE|METER|DONG HO'),('duct',r'DUCT|MANG (CAP|DAY|NHUA)'),('partition_candidate',r'VACH NGAN|PARTITION|BARRIER|KHOANG'),('mechanical',r'TAI TREO|BAN LE|HINGE|^HL\d|^BASE|ISOLATE|SU KEP|THANH U|PANEL')]:
  if re.search(pattern,n):return key
 return 'unidentified'
d=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'));groups=defaultdict(list)
for row in d['shells']:groups[row['original_dxf']].append(row)
analyses=[]
for path,rows in groups.items():
 doc=ezdxf.readfile(ROOT/path);occurrences=[];texts=[]
 for e in doc.modelspace().query('INSERT'):
  parent=dynblkhelper.get_dynamic_block_definition(e);name=parent.name if parent else e.dxf.name
  occurrences.append({'source_handle':e.dxf.handle,'block_name':name,'role':role(name),'insertion_point_source':[float(v) for v in e.dxf.insert],'rotation_deg':float(e.dxf.rotation),'scale':[float(e.dxf.xscale),float(e.dxf.yscale),float(e.dxf.zscale)],'attributes':{a.dxf.tag:a.dxf.text for a in e.attribs}})
 for e in doc.modelspace().query('TEXT MTEXT'):
  text=e.dxf.text if e.dxftype()=='TEXT' else e.plain_text()
  if re.search(r'FORM\s*[-:=]?\s*(?:[234][AB]|1)\b',norm(text)):texts.append((e.dxf.insert,text,e.dxf.handle))
 for row in rows:
  frame=doc.entitydb.get(row['source_handle']);ext=bbox.extents([frame],fast=True)
  if not ext.has_data:continue
  r=[ext.extmin.x,ext.extmin.y,ext.extmax.x,ext.extmax.y]
  contained=[{**o,'position_relative_to_sheet_origin_mm':[o['insertion_point_source'][0]-r[0],o['insertion_point_source'][1]-r[1]]} for o in occurrences if r[0]<=o['insertion_point_source'][0]<=r[2] and r[1]<=o['insertion_point_source'][1]<=r[3] and not o['attributes'].get('DRAWING_NAME') and not o['attributes'].get('MATERIAL')]
  evidence=[{'text':text,'source_handle':handle} for point,text,handle in texts if r[0]<=point.x<=r[2] and r[1]<=point.y<=r[3]]
  spec=row['source_specification'];m=re.search(r'FORM\s*[-:=]?\s*([234][AB]|1)\b',norm(spec.get('FORM','')))
  labels=set(re.findall(r'FORM\s*[-:=]?\s*([234][AB]|1)\b',norm(' '.join(e['text'] for e in evidence))))
  if m:labels.add(m.group(1))
  declared=next(iter(labels)).lower() if len(labels)==1 else None
  classification={'declared_form':declared,'verified_form':None,'status':'source_declared_needs_partition_verification' if declared else 'insufficient_evidence','source_label_evidence':evidence,'criteria_observations':{key:None for key in ('internal_separation','busbars_from_units','units_from_each_other','terminals_and_external_conductors_from_units','terminals_from_busbars','terminals_per_unit_separated','terminals_compartment')},'required_checks':CRITERIA[declared] if declared else CRITERIA,'references':REFERENCES,'notes':['Hai lớp cánh không có nghĩa Form 2.','Máng dây, khoảng trống và nét gạch chéo không chứng minh vách phân khoang.','Không thấy vách trên CAD 2D không đủ xác nhận Form 1.']}
  analysis={'form_id':row['id'],'cabinet_name':row['name'],'material_from_source':row['material_from_source'],'source_file':row['source_file'],'source_sheet_handle':row['source_handle'],'source_sheet_bounds':r,'layout_occurrences':contained,'occurrence_counts_by_role':dict(Counter(o['role'] for o in contained)),'count_policy':'Số lần xuất hiện trên tờ nhiều mặt, không phải số lượng BOM; chưa ghép cùng thiết bị giữa các mặt.','busbar_and_wire_routes':{'verified':False,'route_geometry':None,'notes':['Điểm chèn block không đại diện đầy đủ đường đồng/dây rã thành LINE; cần đối chiếu nguồn.','Không suy tiết diện, dòng cho phép hoặc chiều dài gia công từ tên block.']},'separation_review':classification}
  save(OUT/'Mau'/row['id']/'bo_tri_goc.json',analysis);analyses.append(analysis);row['layout_analysis_json']=f"Mau/{row['id']}/bo_tri_goc.json";row['separation_review']=classification;save(OUT/'Mau'/row['id']/'thong_tin.json',row)
 save(OUT/'catalog.json',d);save(OUT/'phan_tich_bo_tri_va_form.json',{'forms_criteria':CRITERIA,'references':REFERENCES,'items':analyses});print(path,len(rows),'analyzed',flush=True)
print('Analyzed',len(analyses))
