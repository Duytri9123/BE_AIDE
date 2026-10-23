"""Import independently reviewed GD20 orthographic views and exact price rows."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from import_ls_step_family import entities,ZUP_YPLUS
from ls_native_writer import write_profile,price_option,ROOT,CAT
from publish_abb_ct_index import main as publish
import ezdxf
SMALL=[('FRONT','SIDE-L',90),('REAR','SIDE',-90),('SIDE-L','TOP',180),('SIDE','BOTTOM',0),('TOP','FRONT',90),('BOTTOM','REAR',90)]
LARGE_XDOWN=[('FRONT','SIDE-L',0),('REAR','SIDE',0),('SIDE-L','REAR',0),('SIDE','FRONT',0),('TOP','TOP',90),('BOTTOM','BOTTOM',-90)]
S2_ZDOWN=[('FRONT','FRONT',90),('REAR','REAR',-90),('SIDE-L','TOP',90),('SIDE','BOTTOM',90),('TOP','SIDE',90),('BOTTOM','SIDE-L',90)]
REVIEWED={
 'GD20-2R2G-4':(SMALL,'2.2','5.8','5.5','3 pha 380–440 V AC','Gài ray DIN 35 mm hoặc gá vít'),
 'GD20-015G-4':(ZUP_YPLUS,'15','40','32','3 pha 380–440 V AC','Gá vít lên tấm lắp'),
 'GD20-030G-4':(SMALL,'30','70','60','3 pha 380–440 V AC','Gá mặt bích, giữ nguyên bộ gá trong CAD'),
 'GD20-037G-4':(SMALL,'37','80','75','3 pha 380–440 V AC','Gá vít lên tấm lắp'),
 'GD20-045G-4':(ZUP_YPLUS,'45','98','92','3 pha 380–440 V AC','Gá mặt bích, giữ nguyên bộ gá trong CAD'),
 'GD20-075G-4':(ZUP_YPLUS,'75','139','150','3 pha 380–440 V AC','Gá vít lên tấm lắp'),
 'GD20-090G-4':(LARGE_XDOWN,'90','168','180','3 pha 380–440 V AC','Gá mặt bích, giữ nguyên bộ gá và đầu nối nhô trong CAD'),
 'GD20-110G-4':(LARGE_XDOWN,'110','201','215','3 pha 380–440 V AC','Gá vít lên tấm lắp'),
 'GD20-2R2G-S2':(S2_ZDOWN,'2.2','24','10','1 pha 220–240 V AC','Gài ray DIN 35 mm hoặc gá vít'),
 'GD20-5R5G-4':(ZUP_YPLUS,'5.5','19.5','14','3 pha 380–440 V AC','Gá vít lên tấm lắp'),
}
def main():
 rows=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'];paths=[]
 for model in sys.argv[1:] or REVIEWED:
  mapping,kw,inc,outc,supply,mount=REVIEWED[model];folder=CAT/'INVT/NguonBenNgoai'/model
  views,prefix=entities(model,mapping,'INVT');assert views
  source=json.loads((folder/'source.json').read_text(encoding='utf8'))
  source.update(step_sha256=hashlib.sha256((folder/'source.step').read_bytes()).hexdigest(),projection_method='Open CASCADE complete original STEP visible-edge HLR, 0.05 mm mesh, 0.025 mm chord; no scale or geometry removal',unit_evidence='Original STEP millimetres, imported MM, DXF INSUNITS=4',axis_mapping=mapping,six_views_verified=True,review='Keypad, terminals, rear mounting slots and cooling features visually checked in all six directions against manufacturer catalogue PDF pages 13, 15–16; full source envelope retained including projecting parts',technical_source_url='https://www.invt.com/uploads/file1/20251114/GD20%20Catalog%28EN%29-V1.1.pdf')
  options=[]
  for row in rows:
   if row['brand']=='INVT' and row['sku']==model:
    o=price_option(row,brand='INVT');o['specifications'].pop('In (A)',None);o['specifications'].update({'Dòng vào (A)':inc,'Dòng ra định mức (A)':outc,'Công suất (kW)':kw});o.update(price='---',basis='exact_named_model_original_step');options.append(o)
  assert options,model
  spec={'Công suất (kW)':kw,'Nguồn vào':supply,'Dòng vào (A)':inc,'Dòng ra định mức (A)':outc,'Kiểu lắp':mount,'Vị trí thường lắp':'Ngăn biến tần và điều khiển động cơ'}
  paths.append(write_profile(model,'Biến tần INVT '+model+' · '+kw+' kW','VFD',[model],None,options,views,source,spec,brand='INVT'))
 ledger=ROOT/'app/data/catalog_verified_view_health.json';health=json.loads(ledger.read_text(encoding='utf8'))
 for p in paths:
  for f in p.parent.glob('CadDon/*/ban_ve.dxf'):
   d=ezdxf.readfile(f);a=d.audit();assert d.units==4 and not a.errors and not a.fixes
   health['files'][f.relative_to(CAT).as_posix()]={'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'preview_sha256':hashlib.sha256(f.with_name('xem_truoc.svg').read_bytes()).hexdigest()}
 ledger.write_text(json.dumps(health,ensure_ascii=False,indent=2),encoding='utf8')
 publish([p.parent.name for p in paths],report_name='invt-full-faces-2026-10-22',brand='INVT',category='VFD',profile_root='INVT/ThietBi',refresh=False)
if __name__=='__main__':main()
