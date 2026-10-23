"""Publish only reviewed source families; electrical and price variants remain separate."""
import hashlib,json,re,sys
from pathlib import Path
import ezdxf
from ezdxf import bbox
from import_ls_step_family import entities
from ls_native_writer import write_profile,price_option,ROOT,CAT
from publish_abb_ct_index import main as publish
OUT=ROOT/'docs/four-brands-additions-2026-10-22'
ABB_MAP=[('FRONT','FRONT',180),('REAR','REAR',180),('SIDE-L','SIDE',180),('SIDE','SIDE-L',180),('TOP','BOTTOM',180),('BOTTOM','TOP',180)]
IDENTITY=[(c,c,0) for c in ['FRONT','REAR','SIDE-L','SIDE','TOP','BOTTOM']]
def save(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
def add(brand,folder,ident,mapping,family,name,kind,models,poles,options,spec,review):
 path=CAT/folder/'ThietBi'/('OFFICIAL-'+family)/'thong_tin_thiet_bi.json'
 if path.exists():return path
 views,prefix=entities(ident,mapping,folder);assert views,ident
 source=json.loads((CAT/folder/'NguonBenNgoai'/ident/'source.json').read_text(encoding='utf8'))
 source.update(projection_method='Open CASCADE polygonal visible-edge HLR from complete original STEP; 0.05 mm mesh, 0.025 mm chord deflection',unit_evidence='Original STEP millimetres; STEPControl import MM; output INSUNITS=4; no geometry resize',axis_mapping=[{'view':c,'source_projector':o,'rotation_degrees':a} for c,o,a in mapping],six_views_verified=True,family_compatibility_evidence=review)
 return write_profile(family,name,kind,models,poles,options,views,source,spec,brand=brand)
def finalize(brand,folder,paths,master_report):
 ledger=ROOT/'app/data/catalog_verified_view_health.json';health=json.loads(ledger.read_text(encoding='utf8'))
 for p in paths:
  for f in p.parent.glob('CadDon/*/ban_ve.dxf'):
   d=ezdxf.readfile(f);a=d.audit();assert d.units==4 and not a.errors and not a.fixes
   health['files'][f.relative_to(CAT).as_posix()]={'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'preview_sha256':hashlib.sha256(f.with_name('xem_truoc.svg').read_bytes()).hexdigest()}
 save(ledger,health)
 report_name='four-brands-'+folder.lower()+'-additions-2026-10-22'
 families={p.parent.name.removeprefix('OFFICIAL-') for p in paths}
 report=[r for r in json.loads((ROOT/master_report).read_text(encoding='utf8')) if r['family'] in families]
 save(ROOT/('docs/'+report_name+'.json'),report)
 publish([p.parent.name for p in paths],report_name=report_name,brand=brand,category='MCB',profile_root=folder+'/ThietBi',refresh=False)
 save(OUT/(folder.lower()+'-profiles.json'),[p.relative_to(CAT).as_posix() for p in paths])
def main():
 rows=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items']
 if 'ABB' in sys.argv:
  paths=[]
  for pole,uid in [('1P','9AKK106930A4834'),('2P','9AKK106930A4835'),('3P','9AKK106930A4836'),('4P','9AKK106930A4837')]:
   model='S20'+pole[0]+'M';selected=[r for r in rows if r['brand']=='ABB' and re.match(re.escape(model)+r'-',r['item_name']) and 0<float(r.get('specifications',{}).get('In (A)',0))<=63]
   assert len(selected)==9,(model,len(selected))
   opts=[price_option(r,brand='ABB') for r in selected]
   for o in opts:o['basis']='abb_source_s200m_same_pole_family';o['family_model']=model
   paths.append(add('ABB','ABB',uid,ABB_MAP,'S200-'+uid,'MCB ABB '+model+' · '+pole+' · 6–63 A','MCB',[model],pole,opts,{'Dải dòng tham chiếu (A)':'6–63','Kiểu lắp':'Gài ray DIN','Vị trí thường lắp':'Ngăn phân phối nhánh'},{'source_title_includes':'S200, S200M, S200L, SC200, SZ200','price_scope':model+' only, In <=63 A; excludes S200 80/100 A and neutral variants','orientation':'Front handle and rear DIN clip visually reviewed; X-positive is upward, front +Y, horizontal +Z. All six independent source directions retained.'}))
  finalize('ABB','ABB',paths,'docs/abb-s200-faces-2026-10-22.json')
 if 'LS' in sys.argv:
  paths=[]
  for sid,pole in [('55466','1P'),('55467','1P+N'),('55468','2P'),('55469','3P'),('55470','3P+N'),('55471','4P')]:
   paths.append(add('LS','LS',sid,IDENTITY,'LA63Hd-'+sid,'MCB LS LA63Hd · '+pole,'MCB',['LA63Hd'],pole,[],{'Kiểu lắp':'Gài ray DIN','Vị trí thường lắp':'Ngăn phân phối nhánh'},{'source_file_poles':pole,'price_scope':'No verified LA63Hd row in current Vietnamese pricebook; not linked to LA63N, LA63H, LA63L or LA125H. No inferred kA or current selected.','orientation':'Native front shows actuator and opposing screw terminals; rear shows DIN clip; top/bottom and sides retained separately.'}))
  finalize('LS','LS',paths,'docs/ls-full-faces-2026-10-20.json')
 if 'CHINT' in sys.argv:
  paths=[]
  nkg=[('FRONT','SIDE-L',90),('REAR','SIDE',-90),('SIDE-L','TOP',180),('SIDE','BOTTOM',0),('TOP','FRONT',90),('BOTTOM','REAR',90)]
  for ident,mapping in [('KG316T',IDENTITY),('NKG1',nkg)]:
   selected=[r for r in rows if r['brand'].upper()=='CHINT' and r['sku']=='KG316T AC220V'] if ident=='KG316T' else []
   opts=[price_option(r,brand='CHINT') for r in selected]
   for o in opts:
    o['basis']='manufacturer_kg316t_screw_mount_code_309010';o['specifications'].update({'Điện áp điều khiển':'AC220V','Khả năng tiếp điểm tại 240 V (A)':'3'})
   spec={'Kiểu lắp':'Gá vít' if ident=='KG316T' else 'Theo các vị trí gá trên thân','Vị trí thường lắp':'Ngăn điều khiển chiếu sáng và lịch đóng cắt'}
   if ident=='KG316T':spec.update({'Điện áp điều khiển':'AC220V','Số nhóm lập trình':'16'})
   review={'catalogue':'catalog.pdf','pdf_page':3 if ident=='KG316T' else 2,'price_scope':'KG316T screw-mount AC220V, catalogue ordering code 309010; excludes KG316T-D DIN rail variant' if ident=='KG316T' else 'NKG1 absent from current pricebook; no price or supply voltage guessed','orientation':'Display, button text, terminal row and rear mounting features visually matched to manufacturer dimensional drawing; each independent direction mapped separately.'}
   paths.append(add('CHINT','Chint',ident,mapping,'TIMER-'+ident,'Công tắc thời gian CHINT '+ident+(' · AC220V' if ident=='KG316T' else ''),'TIMER',[ident],None,opts,spec,review))
  finalize('CHINT','Chint',paths,'docs/chint-full-faces-2026-10-21.json')
if __name__=='__main__':main()
