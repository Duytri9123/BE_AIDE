"""Build customer facts for ABB/LS/CHINT from exact references and verified CAD."""
import json,re,hashlib,collections,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from ezdxf import bbox
from app.services.ai.manufacturer_registry import canonical_brand
from app.services.catalog_family_matching import category_key
from app.services.catalog_product_sections import device_poles,coil_compatible,aux_contacts_compatible
from app.services.catalog_device_names import _row_poles
from app.services.cad.catalogtb_assets import normalized_source
from app.services.customer_equipment_information import product_specs
from app.services.customer_technical_specs import qualified_breaking_specs
ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB'
LOCATIONS={'MCB':'Ngăn phân phối nhánh','RCBO':'Ngăn phân phối nhánh','RCCB':'Ngăn phân phối và bảo vệ dòng rò','MCCB':'Ngăn đóng cắt nguồn hoặc xuất tuyến','ACB':'Ngăn máy cắt tổng hoặc liên lạc thanh cái','CONTACTOR':'Ngăn điều khiển tải, động cơ','THERMAL_RELAY':'Ngăn điều khiển động cơ, ghép với contactor','CT':'Khoang đo lường, tại tuyến cáp hoặc thanh cái','ZCT':'Khoang đo dòng rò, bao quanh nhóm dây dẫn cần đo','SPD':'Ngăn bảo vệ chống quá áp của tủ điện','PUSHBUTTON':'Cánh tủ hoặc bảng điều khiển','PUSH':'Cánh tủ hoặc bảng điều khiển','LIGHT':'Cánh tủ hoặc bảng hiển thị','INDICATOR':'Cánh tủ hoặc bảng hiển thị','SELECTOR':'Cánh tủ hoặc bảng điều khiển','SELECTOR_SWITCH':'Cánh tủ hoặc bảng điều khiển','METER':'Cánh tủ đo lường','TIMER':'Ngăn điều khiển','RELAY':'Ngăn điều khiển','PHASE_RELAY':'Ngăn điều khiển, bảo vệ nguồn ba pha','PHASERELAY':'Ngăn điều khiển, bảo vệ nguồn ba pha','TRANSFORMER':'Ngăn nguồn điều khiển','ATS':'Ngăn chuyển nguồn'}

def nums(value):
 text=str(value)
 # Manufacturer current lists use commas as separators (15,20,30...),
 # while adjustable-current ranges can use decimal commas (0,16–0,25).
 if ',' in text:
  if text.count(',')>1 and not re.search(r'[-–~]',text):text=text.replace(',',' ')
  else:
   text=re.sub(r'(?<![\d.])0,(\d+)',r'0.\1',text)
   text=re.sub(r'(\d+),(\d)(?!\d)',r'\1.\2',text)
   text=text.replace(',',' ')
 return [float(x) for x in re.findall(r'\d+(?:\.\d+)?',text)]
def text_values(values):return sorted({str(v).strip() for v in values if v is not None and str(v).strip()})

def exact_options(device):
 model=str(device.get('product_code') or '').strip()
 if not model:return []
 models=re.split(r'\s+/\s+',model);patterns=[re.compile(r'(?<![A-Z0-9])'+re.escape(m)+r'(?![A-Z0-9-])',re.I) for m in models if m]
 wanted=device_poles(device);kind=category_key(device.get('type'));selected=[]
 for o in (device.get('catalog_references') or {}).get('options',[]):
  if canonical_brand(o.get('brand'))!=canonical_brand(device.get('brand')):continue
  spec=o.get('specifications') or {};row={'sku':o.get('model'),'specifications':spec,'category':kind}
  if wanted and _row_poles(o)!=wanted:continue
  if kind in {'MCB','MCCB','RCBO','RCCB','ACB'} and not wanted:continue
  family=spec.get('Họ thiết bị') or spec.get('Dòng sản phẩm')
  hay=' '.join(str(x or '') for x in [o.get('model'),spec.get('Tên hàng')])
  explicit_native_link=o.get('source_row_id') and o.get('basis') in {'ls_full_pricebook_native_family','chint_full_pricebook_native_family'}
  if not explicit_native_link and not any(p.search(hay) for p in patterns) and str(family or '').casefold() not in {m.casefold() for m in models}:continue
  if not coil_compatible(device,row) or not aux_contacts_compatible(device,row):continue
  selected.append(o)
 # Descriptive family-only entries do not invalidate facts shared by the
 # concrete ordering codes (e.g. NXB-63 plus its nine C-curve current options).
 concrete=[o for o in selected if o.get('source_row_id') or any(k.strip().lower() in {'in','in (a)','dòng định mức (a)','dòng định mức'} for k in (o.get('specifications') or {}))]
 return concrete or selected

def reference_facts(device,options):
 facts={};evidence=[];current=set();values=collections.defaultdict(list)
 for o in options:
  specs=product_specs(o.get('specifications'))
  for k,v in specs.items():
   if k.strip().lower() in {'in','in (a)','dòng định mức (a)','dòng định mức'}:current.update(nums(v))
   elif re.search(r'kích thước|dimensions|^Ue$|^Ui$|^Uimp$|tần số|lắp đặt|^kiểu lắp$|^tiếp điểm$|^điện áp cuộn hút$',k,re.I):values[k].append(v)
   elif re.search(r'^I(?:cu|cs|cn|nc).*\d+\s*V',k,re.I):values[k].append(v)
  evidence.append({'model':o['model'],'source_row_id':o.get('source_row_id'),'source_url':o.get('source_url')})
 if current:
  low,high=min(current),max(current);facts['Dòng định mức In (A)' if low==high else 'Dải dòng định mức In (A)']=format(low,'g') if low==high else format(low,'g')+'–'+format(high,'g')
 for k,vs in values.items():
  unique=text_values(vs)
  # Absence/conflict in another matched configuration is not a shared fact.
  if len(unique)==1 and len(vs)==len(options):facts[k]=unique[0]
 return facts,evidence

def measured_dimensions(raw,path):
 if raw.get('browser_hidden') or str((raw.get('nhan_dien_ai') or {}).get('loai_thiet_bi_code')).upper() in {'ASSEMBLY_REFERENCE','SOURCE_REFERENCE'}:return None
 if any('trục' in k.lower() or 'khoảng cách cửa' in k.lower() for k in (raw.get('thong_so') or {})):return None
 groups=collections.defaultdict(list)
 for v in raw.get('cad_don',[]):groups[v.get('bien_the_cad') or v.get('bien_the') or 'default'].append(v)
 sizes=[];proof=[]
 for variant,views in groups.items():
  front=[v for v in views if str(v.get('huong_nhin') or '').split(' · ')[0] in {'Mặt trước','Mặt xuyên dây'}]
  side=[v for v in views if str(v.get('huong_nhin') or '').split(' · ')[0] in {'Mặt bên','Mặt bên phải','Mặt bên trái'} and (v.get('bo_tri_trong_tu') or {}).get('envelope_depth_source') is not False]
  if len(front)!=1 or len(side)!=1:return None
  bs=[]
  for v in [front[0],side[0]]:
   ev=v.get('unit_verification') or {}
   if ev.get('coordinate_scale_to_mm')!=1:return None
   f=normalized_source(path.parent/v['duong_dan']);doc=ezdxf.readfile(f)
   if doc.units!=4 or doc.audit().errors or any(e.dxftype() in {'TEXT','MTEXT','DIMENSION','LEADER','MLEADER'} for e in doc.modelspace()):return None
   b=bbox.extents(doc.modelspace()).size;bs.append(b);proof.append({'view':v['id_hinh_goc'],'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'source_url':ev.get('source_url')})
  if abs(bs[0].y-bs[1].y)>.2:return None
  size=tuple(round(x,2) for x in [bs[0].x,bs[0].y,bs[1].x]);sizes.append(size)
 if not sizes or len(set(sizes))!=1:return None
 return {'value':' × '.join(format(x,'g') for x in sizes[0]),'evidence':proof}

def verified_view_dimensions(raw,path):
 """Keep different manufacturer mounting variants separate in the UI."""
 groups=collections.defaultdict(list);result={}
 for v in raw.get('cad_don',[]):
  if v.get('bien_the_cad'):groups[v['bien_the_cad']].append(v)
 for variant,views in groups.items():
  front=[v for v in views if v.get('huong_nhin')=='Mặt trước'];side=[v for v in views if v.get('huong_nhin') in {'Mặt bên','Mặt bên phải'}]
  if len(front)!=1 or len(side)!=1:continue
  sizes=[];valid=True
  for v in [front[0],side[0]]:
   ev=v.get('unit_verification') or {};f=path.parent/v['duong_dan']
   if not ev.get('width_mm') or not ev.get('height_mm') or not ev.get('sha256') or not f.is_file():valid=False;break
   if hashlib.sha256(f.read_bytes()).hexdigest()!=ev['sha256']:valid=False;break
   doc=ezdxf.readfile(f)
   if doc.units!=4 or doc.audit().errors:valid=False;break
   size=bbox.extents(doc.modelspace()).size
   if abs(size.x-ev['width_mm'])>.01 or abs(size.y-ev['height_mm'])>.01:valid=False;break
   sizes.append(size)
  if not valid or abs(sizes[0].y-sizes[1].y)>.2:continue
  value=' × '.join(format(round(x,2),'g') for x in [sizes[0].x,sizes[0].y,sizes[1].x])
  for v in views:result[v['id_hinh_goc']]={'Kích thước CAD W×H×D (mm)':value}
 return result

def main():
 data=json.loads((CAT/'_agent_index/browser_display_v5.json').read_text(encoding='utf8'));devices=[d for d in data['items'] if canonical_brand(d.get('brand')) in {'ABB','LS Electric','CHINT','Schneider Electric','INVT','Mitsubishi Electric','Shihlin'}]
 wanted={d['id'] for d in devices};profiles={}
 for p in CAT.rglob('thong_tin_thiet_bi.json'):
  cid='TB-'+hashlib.sha1(p.relative_to(CAT).as_posix().encode()).hexdigest()[:16]
  if cid in wanted:profiles[cid]=(p,json.loads(p.read_text(encoding='utf-8-sig')))
 previous_path=ROOT/'app/data/catalog_customer_technical_facts.json'
 previous=json.loads(previous_path.read_text(encoding='utf8')).get('items',{}) if '--reuse-cad' in sys.argv and previous_path.exists() else {}
 result={};counts=collections.defaultdict(collections.Counter)
 for index,d in enumerate(devices):
  maker=canonical_brand(d.get('brand'));kind=category_key(d.get('type'));options=exact_options(d);facts,evidence=reference_facts(d,options)
  qualified=qualified_breaking_specs(maker,d.get('product_code'))
  facts.update(qualified)
  if qualified and maker=='Mitsubishi Electric':
   if d.get('product_code') in {'BV-DN','BV-DN6'}:evidence.append({'source_url':'https://www.mitsubishielectric.com/dl/fa/document/catalog/lvcb/yn-c-0713/y0713c2303.pdf','basis':'Exact RCBO model, IEC 61009-1 Icn at 230 V AC'})
   else:evidence.append({'source_url':'https://www.mitsubishielectric.com/dl/fa/document/catalog/lvcb/yn-c-0720/y0720j2309.pdf','pages':[150,154],'basis':'Exact standard NF125/NF250 CV/SV/HV model; 400/415/440 V AC Icu and Ics, no MB or UL extrapolation'})
  if device_poles(d):facts['Số cực']=device_poles(d)
  if kind in LOCATIONS:facts['Vị trí thường lắp']=LOCATIONS[kind]
  if d['id'] in profiles:
   path,raw=profiles[d['id']];old=previous.get(d['id'],{});cached=old.get('facts',{}).get('Kích thước CAD W×H×D (mm)')
   if path.parent.name.startswith('OFFICIAL-'):
    location=product_specs(raw.get('thong_so') or {}).get('Vị trí thường lắp')
    if location:facts['Vị trí thường lắp']=location
    native=(raw.get('cad_don') or [{}])[0].get('unit_verification') or {}
    if maker=='Shihlin' and native.get('six_views_verified') and native.get('complete_manufacturer_step_projection') and native.get('technical_source_url'):
     facts.update(product_specs(raw.get('thong_so') or {}))
     evidence.append({'source_url':native.get('technical_source_download_url') or native['technical_source_url'],'source_sha256':native.get('technical_source_sha256'),'source_page':native.get('technical_source_page'),'basis':'Reviewed exact Shihlin model and pole-specific native body; voltage-qualified electrical facts from manufacturer technical source'})
   proofs=[e for e in old.get('evidence',[]) if e.get('view')]
   entries={v['id_hinh_goc']:v for v in raw.get('cad_don',[])}
   valid_cached=cached and proofs and all(e['view'] in entries and hashlib.sha256(normalized_source(path.parent/entries[e['view']]['duong_dan']).read_bytes()).hexdigest()==e['sha256'] for e in proofs)
   measured={'value':cached,'evidence':proofs} if valid_cached else (None if '--reuse-cad' in sys.argv and not path.parent.name.startswith('OFFICIAL-') else measured_dimensions(raw,path))
   if measured:facts['Kích thước CAD W×H×D (mm)']=measured['value'];evidence+=measured['evidence']
  # Official Metasol table, exact c-series models. Pricebook Icu columns
  # have no single voltage convention, so never relabel those as "at 415 V".
  if maker=='LS Electric' and kind=='MCCB':
   rating_map={}
   for prefix,frames,ratings in [('ABN',[52,53,54],(14,18,30)),('ABN',[102,103,104],(18,22,35)),('ABS',[102,103,104],(37,42,85)),('ABH',[102,103,104],(50,50,100))]:
    for frame in frames:rating_map[prefix+str(frame)+'c']=ratings
   codes=[o['model'] for o in options if o['model'] in rating_map or any(re.match(r'^Icu|^In(?:\s*\(A\))?$',k,re.I) for k in (o.get('specifications') or {}))]
   pole=device_poles(d)
   frame_aliases={'ABN50c':'ABN5','ABN100c':'ABN10','ABS100c':'ABS10','ABH100c':'ABH10'}
   if pole in {'2P','3P','4P'}:codes=[frame_aliases[c]+pole[0]+'c' if c in frame_aliases else c for c in codes]
   qualified=[rating_map[c] for c in codes if c in rating_map]
   if codes and len(qualified)==len(codes) and len(set(qualified))==1:
    for voltage,value in zip(['415/460','380','220/250'],qualified[0]):facts['Icu tại '+voltage+' V AC (kA)']=str(value)
    facts['Lắp đặt']='Bắt vít lên bản gá';evidence.append({'source_url':'https://www.ls-electric.com/upload/customer/download/1213/Metasol_MCCB-ELCB_Technical%20Manual_E.pdf','pdf_pages':[8,9],'scope':'Exact ABN/ABS/ABH c-series model, separate voltage rows; no pricebook voltage inference.'})
  # Exact NXM S frames reviewed in the manufacturer's dimensional table.
  if maker=='CHINT' and d.get('product_code') in {'NXM-160S','NXM-250S'} and device_poles(d) in {'2P','3P','4P'}:
   frame=d['product_code'];poles=device_poles(d);width={'NXM-160S':{'2P':63,'3P':90,'4P':120},'NXM-250S':{'2P':78,'3P':105,'4P':140}}[frame][poles]
   height,depth=(155,75.5) if frame=='NXM-160S' else (165,77)
   facts.update({'Kích thước thân W×H×D (mm)':f'{width} × {height} × {depth:g}','Icu tại 380/400/415 V AC (kA)':'36','Kiểu lắp':'Cố định; đấu nối phía trước'})
   evidence.append({'source_url':'https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/secondary-power-distribution/mccb/nxm/catalog/NXM-MCCB-Catalog.pdf','pdf_page':27,'scope':'S frame body dimensions and Icu only; Ics omitted because general and ordering tables differ.'})
  view_facts={}
  if maker=='ABB' and d['id'] in profiles:
   path,raw=profiles[d['id']];old=previous.get(d['id'],{});cached_views=old.get('view_facts',{});entries={v['id_hinh_goc']:v for v in raw.get('cad_don',[])}
   cached_ok=cached_views and old.get('model')==d.get('product_code') and all(vid in entries and hashlib.sha256((path.parent/entries[vid]['duong_dan']).read_bytes()).hexdigest()==(entries[vid].get('unit_verification') or {}).get('sha256') for vid in cached_views)
   view_facts=cached_views if cached_ok else verified_view_dimensions(raw,path)
  from scripts.measure_customer_cad_views import cached_view_facts
  for vid,measurement in cached_view_facts([v['id'] for v in d['views']],device_id=d['id']).items():
   view_facts.setdefault(vid,{}).update(measurement)
  result[d['id']]={'brand':maker,'model':d.get('product_code'),'view_ids':sorted(v['id'] for v in d['views']),'facts':facts,'view_facts':view_facts,'evidence':evidence}
  counts[maker]['items']+=1;counts[maker]['with_dimensions']+=any('thước' in k for k in facts);counts[maker]['with_current']+=any('In (A)' in k for k in facts);counts[maker]['with_voltage_qualified_breaking']+=any(k.startswith('Icu tại') for k in facts);counts[maker]['with_location']+='Vị trí thường lắp' in facts
  counts[maker]['with_variant_cad_dimensions']+=any('Kích thước CAD W×H×D (mm)' in vf for vf in view_facts.values())
  counts[maker]['with_2d_cad_dimensions']+=any('Kích thước mặt CAD ngang×cao (mm)' in vf for vf in view_facts.values())
  if index%75==0:print('Reviewed facts',index,'/',len(devices),flush=True)
 out=ROOT/'app/data/catalog_customer_technical_facts.json';out.write_text(json.dumps({'version':1,'items':result},ensure_ascii=False,indent=2),encoding='utf8')
 report=ROOT/'docs/technical-facts-2026-10-21';report.mkdir(exist_ok=True);(report/'summary.json').write_text(json.dumps(counts,indent=2),encoding='utf8');print(json.dumps(counts),flush=True)
if __name__=='__main__':main()
