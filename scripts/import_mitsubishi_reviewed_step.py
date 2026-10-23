"""Import source-reviewed manufacturer bodies; keep poles and terminal states separate."""
import hashlib,json,sys,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from import_ls_step_family import entities,LABELS
from ls_native_writer import write_profile,price_option,ROOT,CAT
from publish_abb_ct_index import main as publish
from app.services.catalog_family_matching import row_poles
import ezdxf
SRC=CAT/'Mitsubishi/NguonBenNgoai/PRIMARY-20261022'
SMALL=[('FRONT','SIDE-L',90),('REAR','SIDE',-90),('SIDE-L','TOP',180),('SIDE','BOTTOM',0),('TOP','FRONT',90),('BOTTOM','REAR',90)]
XDOWN=[('FRONT','SIDE-L',0),('REAR','SIDE',0),('SIDE-L','REAR',0),('SIDE','FRONT',0),('TOP','TOP',90),('BOTTOM','BOTTOM',-90)]
IDENTITY=[(c,c,0) for c in LABELS]
# The S-N150 native file uses +Y as the front and -Z as installed up.
# Its official BH782D801-A outline confirms terminal rows above/below the cover.
SN150=[('FRONT','FRONT',90),('REAR','REAR',-90),('SIDE-L','TOP',90),('SIDE','BOTTOM',90),('TOP','SIDE',90),('BOTTOM','SIDE-L',90)]
HELD={'nv63cv_2p_m5','nv63cv_2p_m8','nv63sv_2p_m5','nv63sv_2p_m8'}

def main():
 rows={r['id']:r for r in json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items']}
 manifest=sys.argv[1] if len(sys.argv)>1 else 'downloads.json'
 downloaded=json.loads((SRC/manifest).read_text(encoding='utf8'))['downloaded']
 paths=[];held=[]
 for item in sorted(downloaded,key=lambda x:x['file_name']):
  ident=Path(item['file_name']).stem;folder=SRC/ident
  if ident in HELD:
   held.append({**item,'reason':'Manufacturer names this 2P but projected body shows three terminal pairs; hold until native 2D and terminal wiring reconcile.'});continue
  models=item['models'];kind=item['kind'];poles=item.get('poles') or '3P'
  if models[0].startswith(('BV-D','BVW-T')):kind='RCCB'
  mapping=IDENTITY if ident.startswith(('bh-d6','bh_d6','bh-dn','bv-d','bvw-t','cp30ba_')) else XDOWN if ident.startswith('bhw-t10') else SMALL
  if ident=='S-N150_step':mapping=SN150
  views,prefix=entities('PRIMARY-20261022/'+ident,mapping,'Mitsubishi');assert views,ident
  source={**item,'step_sha256':hashlib.sha256((folder/'source.step').read_bytes()).hexdigest(),
   'projection_method':'Open CASCADE original complete STEP visible-edge HLR; no geometry removed; no scaling',
   'unit_evidence':'Manufacturer STEP millimetres; STEPControl import MM; output INSUNITS=4',
   'axis_mapping':mapping,'six_views_verified':True,'complete_manufacturer_step_projection':True,
   'review':'All native six-view contact sheets visually checked: terminal rows, actuator side and mounting back. Opposed extents agree within 0.2 mm. Official simplified representations retained.',
   'technical_source_url':'https://www.mitsubishielectric.com/dl/fa/document/catalog/lvcb/yn-c-0720/y0720j2309.pdf'}
  options=[]
  for rid in item['price_row_ids']:
   r=rows[rid];assert r['brand']=='Mitsubishi Electric' and (row_poles(r)==poles or (kind in {'CONTACTOR','THERMAL_RELAY'} and row_poles(r) is None))
   assert any(re.match(re.escape(m)+r'(?=$|\s|/)',r['item_name'],re.I) for m in models)
   o=price_option(r,brand='Mitsubishi Electric');o.update(price='---',basis='exact_named_manufacturer_step_family',exact_cad_match=False)
   if kind in {'CONTACTOR','THERMAL_RELAY'}:o['specifications']['Số cực']='3P'
   if kind=='CONTACTOR':o['specifications']['Loại cuộn hút']='DC' if models[0].startswith('SD-') else 'AC'
   options.append(o)
  assert options
  current=sorted({float((r.get('specifications') or {}).get('In (A)') or 0) for r in (rows[x] for x in item['price_row_ids'])}-{0})
  spec={'Vị trí thường lắp':'Ngăn khởi động và bảo vệ động cơ' if kind in {'CONTACTOR','THERMAL_RELAY'} else 'Ngăn phân phối và bảo vệ nguồn' if kind=='ACB' else 'Ngăn phân phối và bảo vệ mạch'}
  if kind=='CB':spec['Vị trí thường lắp']='Ngăn điều khiển, bảo vệ mạch phụ'
  if poles=='1P+N':spec['Cấu hình cực']='1 pha và trung tính (1P+N)'
  if '4(3+n)' in ident:spec['Cấu hình cực']='3 pha và trung tính (3P+N), tổng cộng 4 cực'
  suffix=[]
  if current:
   fmt=lambda n:format(n,'g')
   suffix.append((fmt(current[0])+'–'+fmt(current[-1]) if len(current)>1 else fmt(current[0]))+' A')
  if kind=='ACB':
   assert '_fix' in ident or '_dr' in ident
   fixed='_fix' in ident
   spec['Kiểu lắp']='Cố định' if fixed else 'Rút kéo';suffix.append('FIX' if fixed else 'DR')
   source['mounting_family']='FIX' if fixed else 'DR'
   if '-vt' in ident:spec['Kiểu đầu nối']='Đầu nối đứng';suffix.append('VT')
   if ident.endswith(('_hn','_fn')):
    spec['Cực trung tính']='Nửa định mức (HN)' if ident.endswith('_hn') else 'Toàn định mức (FN)';suffix.append(ident[-2:].upper())
    source['neutral_evidence_url']='https://www.mitsubishielectric.com/dl/fa/document/catalog/lvcb/yn-c-0622/y0622j1912.pdf'
  elif kind in {'MCB','RCCB','RCBO'}:spec['Kiểu lắp']='Ray DIN'
  elif kind not in {'CONTACTOR','THERMAL_RELAY','CB'}:spec['Kiểu lắp']='Gá vít, đầu nối phía trước'
  if kind=='CONTACTOR':
   spec['Nguồn cuộn hút']='DC' if models[0].startswith('SD-') else 'AC'
   suffix.append(spec['Nguồn cuộn hút'])
   source['coil_family_evidence']='Manufacturer navigation: S-T/S-N non-reversing AC-operated; SD-T/SD-N non-reversing DC-operated. Voltage is selected separately per ordering row.'
   if any(m.startswith(('S-N125','S-N150','S-N180','S-N220','S-N300','S-N400','S-N600','S-N800','SD-N')) for m in models):spec['Kiểu lắp']='Gá vít trên tấm lắp'
   if all(m.endswith('SQ') for m in models):spec['Kiểu đầu nối']='Kẹp lò xo (SQ)'
  if kind=='THERMAL_RELAY':source['pole_evidence']='Original CAD shows three thermal current paths; KP/SQ variants retained only where manufacturer explicitly serves the same source file for both named models.'
  if kind in {'CONTACTOR','THERMAL_RELAY'}:
   source['technical_source_url']='https://www.mitsubishielectric.com/dl/fa/document/catalog/lvsw/l02031eng/L%28NA%2902031ENG-L_21B.pdf'
  if kind=='THERMAL_RELAY' and any(m.startswith('TH-N') for m in models):
   source['mounting_evidence_pages']=[139,144,152,153,154]
   if models[0]=='TH-N120':spec['Kiểu lắp']='Ghép contactor hoặc gá độc lập bằng vít'
   elif models[0].startswith(('TH-N120TA','TH-N220RH','TH-N400RH')):spec['Kiểu lắp']='Ghép contactor, dùng bộ nối tương ứng'
   elif models[0].startswith('TH-N600'):
    spec['Kiểu lắp']='Gá vít trên tấm lắp';spec['Đầu vào đo dòng']='Qua biến dòng ngoài, thứ cấp 5 A'
    spec['Vị trí thường lắp']='Ngăn bảo vệ động cơ, nối với biến dòng ngoài'
    source['pole_evidence']='Three CT-secondary measuring circuits, not direct motor-current terminals. Manufacturer catalogue PDF pp.139/154 requires separate 5 A secondary CTs.'
  if ident.endswith(('_m5','_m8')):
   screw=ident[-2:].upper();spec['Vít đầu nối']=screw;suffix.append(screw)
   source['terminal_evidence']='WS-V catalogue PDF pages 149 and 186–187: M5 up to 50 A; M8 at 60/63 A'
  family='STEP-'+ident.upper()+item.get('variant_suffix','')
  path=CAT/'Mitsubishi/ThietBi'/('OFFICIAL-'+family)/'thong_tin_thiet_bi.json'
  if not path.exists():
   path=write_profile(family,'Mitsubishi · '+kind+' · '+' / '.join(models)+' · '+poles+(' · '+' · '.join(suffix) if suffix else ''),kind,models,poles,options,views,source,spec,brand='Mitsubishi Electric')
  else:print('Already imported',family,flush=True)
  paths.append(path)
 ledger=ROOT/'app/data/catalog_verified_view_health.json';health=json.loads(ledger.read_text(encoding='utf8'))
 for path in paths:
  for f in path.parent.glob('CadDon/*/ban_ve.dxf'):
   d=ezdxf.readfile(f);a=d.audit();assert d.units==4 and not a.errors and not a.fixes
   health['files'][f.relative_to(CAT).as_posix()]={'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'preview_sha256':hashlib.sha256(f.with_name('xem_truoc.svg').read_bytes()).hexdigest()}
 ledger.write_text(json.dumps(health,ensure_ascii=False,indent=2),encoding='utf8')
 (ROOT/('docs/mitsubishi-held-'+Path(manifest).stem+'-2026-10-22.json')).write_text(json.dumps(held,ensure_ascii=False,indent=2),encoding='utf8')
 publish([p.parent.name for p in paths],report_name='mitsubishi-full-faces-2026-10-22',brand='Mitsubishi Electric',category='MCCB',profile_root='Mitsubishi/ThietBi',refresh=False)
 print('Complete',len(paths),'held',len(held),flush=True)
if __name__=='__main__':main()
