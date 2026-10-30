"""Import only inspected native LS source windows, preserving layers and colors."""
import sys,json,hashlib,re,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from ezdxf import bbox
from ls_native_writer import ROOT,CAT,write_profile,price_option
PRICES=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items']
JOBS=[
 ('RU-MT12','7ef2050575d8cf75','THERMAL_RELAY','MT-12',None,[('FRONT','Mặt trước',(200,130,270,220)),('SIDE','Mặt bên',(280,130,355,220))]),
 ('RU-MT32','5d12dade3d6f0b66','THERMAL_RELAY','MT-32',None,[('FRONT','Mặt trước',(500,620,580,720)),('SIDE','Mặt bên',(620,610,750,720))]),
 ('RU-MT63','5d12dade3d6f0b66','THERMAL_RELAY','MT-63',None,[('FRONT','Mặt trước',(500,470,590,590)),('SIDE','Mặt bên',(620,460,750,590))]),
 ('RU-MT95','5d12dade3d6f0b66','THERMAL_RELAY','MT-95',None,[('FRONT','Mặt trước',(500,300,600,435)),('SIDE','Mặt bên',(620,290,755,435))]),
 ('RU-MR6-AC','508363188383dd75','CONTACTOR','MR-6','AC',[('FRONT','Mặt trước',(-635,0,-570,100)),('SIDE','Mặt bên',(-510,0,-350,105)),('REAR','Mặt sau',(-280,0,-210,100))]),
 ('RU-MR8-AC','508363188383dd75','CONTACTOR','MR-8','AC',[('FRONT','Mặt trước',(-635,-215,-565,-110)),('SIDE','Mặt bên',(-510,-215,-350,-110)),('REAR','Mặt sau',(-280,-215,-210,-110))]),
 ('RU-MR6-DC','508363188383dd75','CONTACTOR','MR-6','DC',[('FRONT','Mặt trước',(30,0,95,105)),('SIDE','Mặt bên',(185,0,350,110)),('REAR','Mặt sau',(405,0,485,110))]),
 ('RU-MR8-DC','508363188383dd75','CONTACTOR','MR-8','DC',[('FRONT','Mặt trước',(30,-215,100,-110)),('SIDE','Mặt bên',(185,-215,350,-110)),('REAR','Mặt sau',(420,-215,485,-110))]),
]
def source_entities(doc,window):
 x,y,X,Y=window;es=[]
 for e in doc.modelspace():
  if e.dxftype() not in {'LINE','ARC','CIRCLE','SPLINE','ELLIPSE','LWPOLYLINE','POLYLINE'}:continue
  b=bbox.extents([e])
  if b.has_data and b.extmin.x>=x and b.extmin.y>=y and b.extmax.x<=X and b.extmax.y<=Y:es.append(e)
 assert len(es)>25,(window,len(es))
 return es

def main():
 reports=[];docs={}
 from app.services.catalog_product_sections import current_kinds
 for family,key,kind,model,coil,windows in JOBS:
  p=CAT/'LS/NguonBenNgoai'/('RU-'+key)
  if key not in docs:docs[key]=ezdxf.readfile(p/'source.dxf')
  doc=docs[key];assert doc.units==4 and not doc.audit().errors
  views=[(c,l,source_entities(doc,w)) for c,l,w in windows]
  rows=[r for r in PRICES if str(r.get('brand')).lower() in ('ls','ls electric') and r.get('category')==kind and re.match(re.escape(model)+r'(?![A-Za-z0-9])',r['sku'])]
  if coil:rows=[r for r in rows if current_kinds(' '.join([r['sku'],str(r.get('group') or ''),*[str(v) for v in (r.get('specifications') or {}).values()]]))=={coil}]
  assert rows,(family,'no exact model prices')
  ev=json.loads((p/'source.json').read_text(encoding='utf8'));ev.update(native_style_preserved=True,source_dxf_sha256=hashlib.sha256((p/'source.dxf').read_bytes()).hexdigest(),coordinate_scale_to_mm=1,unit_evidence='Original source INSUNITS=4, dimensioned source sheet reviewed against manufacturer Metasol outlines',reviewed_windows=[{'face':c,'window':w} for c,l,w in windows],six_views_verified=False)
  spec={'Loại cuộn hút':coil} if coil else {}
  if coil:spec['Số tiếp điểm']=('3NO + 3NC' if model=='MR-6' else '4NO + 4NC')
  profile=write_profile(family,'LS · '+('Rơ le nhiệt' if kind=='THERMAL_RELAY' else 'Rơ le trung gian')+' · '+model+(' · Cuộn '+coil if coil else ''),kind,[model],None,[price_option(r) for r in rows],views,ev,spec,native_document=doc)
  reports.append({'family':family,'profile':profile.relative_to(CAT).as_posix(),'model':model,'coil':coil,'price_ids':[r['id'] for r in rows],'views':len(views),'source':str(p.relative_to(CAT))})
 (ROOT/'docs/ls-all-cad-2026-10-24/native-supplements.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf8')
 return reports
if __name__=='__main__':main()
