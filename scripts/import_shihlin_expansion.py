"""Import explicitly named native Shihlin bodies; archive/page aliases stay pending."""
import hashlib,json,sys,shutil
from pathlib import Path
from import_shihlin_bm250 import installed_axes
from project_ls_step_views import read_shape,project
from import_ls_step_family import entities,LABELS
from ls_native_writer import CAT,ROOT,write_profile,price_option
import ezdxf
from ezdxf import bbox

BASE=CAT/'Shihlin/NguonBenNgoai'
SOURCE=BASE/'PRIMARY-EXPANSION-20261023'
TARGETS=[('BM30-CN',2,'BM30-CN_2P.STEP'),('BM30-CN',3,'BM30-CN_3P.STEP'),('BM1000-HS',3,'BM1000-HS 3P.STEP')]
TARGETS += [(m,p,f'[官网]630s-AF {p}P.STEP') for m in ['BM630s-STA','BM630s-LTA','BM630s-HTA','BM630s-RTA'] for p in ([3,4] if m in ['BM630s-LTA','BM630s-HTA'] else [3])]
REPORT=ROOT/'docs/catalog-completion-2026-10-23/shihlin-expansion-import.json'

def prepare():
 from OCP.BRepMesh import BRepMesh_IncrementalMesh
 from ezdxf.addons.drawing import matplotlib
 for model,pole,member in TARGETS:
  group=SOURCE/('BM630s-STA' if model.startswith('BM630s-') else model)
  native=next(p for p in group.rglob('*.STEP') if p.name==member);folder=BASE/f'{model}-{pole}P-INSTALLED-20261023';folder.mkdir(exist_ok=True)
  shutil.copyfile(native,folder/'source.step')
  shape=read_shape(folder/'source.step');r,u,f=installed_axes(shape);neg=lambda a:tuple(-v for v in a)
  # BM30 native terminal/lever face is +Y, with installed up along -Z.
  # BM1000 terminal/lever face is +Z, installed up +Y. Verified visually.
  if model=='BM30-CN':u,f=neg(f),u
  if model.startswith('BM630s-'):r,u,f=neg(f),neg(r),u
  axes=[('FRONT',f,r),('REAR',neg(f),neg(r)),('SIDE-L',neg(r),f),('SIDE',r,neg(f)),('TOP',u,r),('BOTTOM',neg(u),r)]
  previous=json.loads((folder/'source.json').read_text(encoding='utf8')) if (folder/'source.json').exists() else {}
  axes_unchanged=previous.get('axes')==json.loads(json.dumps(axes))
  mesh=BRepMesh_IncrementalMesh(shape,.05,False,.5,False);assert mesh.IsDone()
  for code,n,x in axes:
   target=folder/f'hlr-poly-all-{code}.dxf'
   if not target.exists() or not axes_unchanged:
    d=project(shape,n,x,polygonal=True,all_visible=True);d.saveas(target)
    matplotlib.qsave(d.modelspace(),folder/(code+'.png'),dpi=85)
   print(model,pole,code,flush=True)
  source=json.loads((group/'source.json').read_text(encoding='utf8'))
  assert any(p['model']==model for p in source['pages']),model
  source.update(source_url=source['url'],native_member=native.relative_to(group).as_posix(),step_sha256=hashlib.sha256(native.read_bytes()).hexdigest(),axes=axes,
                projection_method='Complete native STEP visible-edge projection, 0.05 mm mesh and 0.025 mm curve chord; no scaling, trimming or invented faces',
                unit_evidence='Original STEP imported in MM; final DXF INSUNITS=4',review_status='six native projections pending visual review')
  source['family_compatibility_evidence']='The manufacturer product page for this exact model links the original archive and the named pole-specific member. Family geometry only; electrical trip/rating selection remains separate.'
  (folder/'source.json').write_text(json.dumps(source,ensure_ascii=False,indent=2),encoding='utf8')

def publish():
 from app.services.catalog_family_matching import row_poles
 from publish_abb_ct_index import main as publish_index
 rows=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'];paths=[];report=[]
 for model,pole,member in TARGETS:
  ident=f'{model}-{pole}P-INSTALLED-20261023';folder=BASE/ident
  source=json.loads((folder/'source.json').read_text(encoding='utf8'))
  assert source.get('review_status')=='six native projections visually verified',ident
  views,_=entities(ident,[(c,c,0) for c in LABELS],'Shihlin');assert len(views)==6
  sizes={c:bbox.extents(es).size for c,l,es in views}
  dimensions=' × '.join(format(round(v,2),'g') for v in [sizes['FRONT'].x,sizes['FRONT'].y,sizes['SIDE'].x])
  matched=[r for r in rows if r['brand']=='Shihlin' and r['sku']==model and row_poles(r)==f'{pole}P'];assert matched
  # Page 7 separately prices bare terminals and the busbar-equipped assembly.
  # The source STEP retains the factory terminal extensions; never remove them
  # or pair this geometry with the cheaper "Khong thanh dong" rows.
  bare_ids={'extra-pdf:97ccb812a44626321520','extra-pdf:2241bdb1af5c1de163b8','extra-pdf:192c8ac6886405862951','extra-pdf:853de19d60cb0770a4bc'}
  if model.startswith('BM630s-'):matched=[r for r in matched if r['id'] not in bare_ids]
  assert matched
  options=[{**price_option(r,brand='Shihlin'),'price':'---','basis':'exact_named_manufacturer_step_family','exact_cad_match':False} for r in matched]
  source.update(six_views_verified=True,complete_manufacturer_step_projection=True)
  spec={'Kích thước CAD W×H×D (mm)':dimensions,'Kiểu lắp':'Cố định, gá vít trên tấm lắp','Kiểu đầu nối':'Đấu nối phía trước','Vị trí thường lắp':'Ngăn đóng cắt nguồn hoặc xuất tuyến'}
  if model=='BM30-CN':
   spec.update({'Dải dòng định mức In (A)':'3–30','Icu tại 220 V AC (kA)':'2.5','Icu tại 380 V AC (kA)':'1.5','Ics tại 220 V AC (kA)':'1.25','Ics tại 380 V AC (kA)':'0.75'})
   source['technical_source_url']='https://en.seec.com.tw/Content/Goods/GCont.aspx?CatId=2016011810170115935&MSID=707056742201325316&MmmID=707031024777534630&SiteID=30'
  elif model=='BM1000-HS':
   spec.update({'Dòng định mức In (A)':'1000','Icu tại 220–240 V AC (kA)':'130','Icu tại 380 V AC (kA)':'100','Icu tại 440 V AC (kA)':'85','Icu tại 500 V AC (kA)':'65'})
   source['technical_source_url']='https://global.seec.com.tw/en/product/1040.html'
  elif model.startswith('BM630s-'):
   source['technical_source_url']=(SOURCE/'catalog-2026-09.pdf').relative_to(CAT).as_posix()
   source['technical_source_download_url']=(ROOT/'tmp/shihlin-catalog-latest-url.txt').read_text(encoding='utf8')
   source['technical_source_sha256']=hashlib.sha256((SOURCE/'catalog-2026-09.pdf').read_bytes()).hexdigest()
   source['technical_source_page']=14 if model.endswith(('STA','LTA')) else 15
   ratings={'STA':(36,25,25,20),'LTA':(65,36,36,20),'HTA':(85,50,50,35),'RTA':(100,70,65,50)}[model.rsplit('-',1)[1]]
   spec['Dải dòng định mức In (A)']='400–630'
   spec.update({f'Icu tại {voltage} V AC (kA)':str(ka) for voltage,ka in zip(['220–240','380','440','500'],ratings)})
  p=write_profile(f'{model}-{pole}P',f'Shihlin · MCCB · {model} · {pole}P','MCCB',[model],f'{pole}P',options,views,source,spec,brand='Shihlin');paths.append(p)
  raw=json.loads(p.read_text(encoding='utf8'));raw['catalog_tham_khao']['source_row_scope']='explicit_only'
  if model.startswith('BM630s-'):
   raw['thong_so']['Kiểu đầu nối']='Đấu nối phía trước, có thanh nối đầu cực'
   raw['catalog_tham_khao']['geometry_variant']='factory_terminal_extensions_present'
   raw['catalog_tham_khao']['price_variant_evidence']={'source_url':matched[0]['source_url'],'source_page':7,'excluded_bare_terminal_row_ids':sorted(bare_ids),'review':'Original price page separately lists Khong thanh dong and equipped terminal variants; only equipped rows linked.'}
  p.write_text(json.dumps(raw,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
  report.append({'profile':p.relative_to(CAT).as_posix(),'model':model,'poles':f'{pole}P','dimensions_mm':dimensions,'price_rows':[r['id'] for r in matched]})
 ledger=ROOT/'app/data/catalog_verified_view_health.json';health=json.loads(ledger.read_text(encoding='utf8'))
 for path in paths:
  for f in path.parent.glob('CadDon/*/ban_ve.dxf'):
   d=ezdxf.readfile(f);a=d.audit();assert d.units==4 and not a.errors and not a.fixes
   health['files'][f.relative_to(CAT).as_posix()]={'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'preview_sha256':hashlib.sha256(f.with_name('xem_truoc.svg').read_bytes()).hexdigest()}
 ledger.write_text(json.dumps(health,ensure_ascii=False,indent=2),encoding='utf8')
 REPORT.write_text(json.dumps({'items':report,'families':len(paths),'views':6*len(paths),'price_rows':sum(len(r['price_rows']) for r in report)},ensure_ascii=False,indent=2),encoding='utf8')
 publish_index([p.parent.name for p in paths],report_name='shihlin-full-faces-2026-10-23',brand='Shihlin',category='MCCB',profile_root='Shihlin/ThietBi',refresh=False)

if __name__=='__main__':prepare() if sys.argv[1]=='project' else publish()
