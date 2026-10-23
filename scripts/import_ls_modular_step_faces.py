import sys,json,ezdxf,math
from pathlib import Path
from ezdxf.math import Matrix44
from ezdxf import bbox
sys.path.insert(0,'scripts')
from ls_native_writer import CAT,ROOT,write_profile,price_option
from project_ls_step_views import RCCB_AXES
prices=[r for r in json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'] if r.get('brand') in ['LS','LS Electric']]
LB40=[('FRONT','REAR',90),('REAR','FRONT',-90),('SIDE-L','TOP',-90),('SIDE','BOTTOM',-90),('TOP','SIDE-L',90),('BOTTOM','SIDE',90)]
def run(ident,models,poles):
 p=CAT/'LS/NguonBenNgoai'/ident
 prefix='hlr-reviewed-' if all((p/('hlr-reviewed-'+c+'.dxf')).exists() for c,*_ in RCCB_AXES) else 'hlr-poly-'
 if not all((p/(prefix+c+'.dxf')).exists() for c,*_ in RCCB_AXES):return
 rows=[r for r in prices if r['sku'] in models];assert rows
 views=[]
 mapping=LB40 if ident=='55490' else [(c,c,0) for c,*_ in RCCB_AXES]
 labels={c:l for c,l,*_ in RCCB_AXES}
 for code,origin,angle in mapping:
  d=ezdxf.readfile(p/(prefix+origin+'.dxf'));es=[]
  for e in d.modelspace():
   e=e.copy();e.transform(Matrix44.z_rotate(math.radians(angle)));e.doc=None;es.append(e)
  views.append((code,labels[code],es))
 # Verify paired silhouettes cover the same dimensions without inventing depth.
 bs={c:bbox.extents(es).size for c,l,es in views};assert abs(bs['FRONT'].x-bs['REAR'].x)<.1;assert abs(bs['FRONT'].y-bs['SIDE'].y)<.1;assert abs(bs['FRONT'].x-bs['TOP'].x)<.1
 source=json.loads((p/'source.json').read_text());source.update(projection_method=('Open CASCADE polygonal visible-edge HLR, original STEP; absolute mesh deflection 0.05 mm' if prefix=='hlr-poly-' else 'Open CASCADE visible-edge HLR, original STEP, six independent orthographic directions, 0.025 mm chord deflection'),unit_evidence='STEPControl imported in MM; CAD output INSUNITS=4',axis_mapping=[{'view':c,'source_projector':o,'rotation_degrees':a} for c,o,a in mapping],six_views_verified=True)
 name='LS · '+('RCCB' if ident in ['55499','55500','55503','55504'] else 'RCBO')+' · '+' / '.join(models)
 extra={'so_cuc':poles,'Cấu hình cực':poles}
 # Each manufacturer model is explicit; do not equate neutral with another live pole.
 profile_path=write_profile('STEP-'+ident,name,'RCCB' if ident in ['55499','55500','55503','55504'] else 'RCBO',models,None,[price_option(r) for r in rows],views,source,extra)
 profile=json.loads(profile_path.read_text(encoding='utf8'));profile['nhan_dien_ai'].update(so_cuc=int(poles[0]),neutral_pole=True);profile_path.write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':
 run('55499',['LC63N 1P+N'],'1P+N')
 run('55500',['LC63N 3P+N'],'3P+N')
 # Manufacturer publishes identical geometry separately under LC100H; preserve its own provenance.
 for target,origin,models,poles in [('55503','55499',['LC100H 1P+N'],'1P+N'),('55504','55500',['LC100H 3P+N'],'3P+N')]:
  p=CAT/'LS/NguonBenNgoai'/target;q=CAT/'LS/NguonBenNgoai'/origin
  assert (p/'source.step').read_bytes()==(q/'source.step').read_bytes()
  for c,*_ in RCCB_AXES:
   f=q/('hlr-reviewed-'+c+'.dxf')
   if f.exists():(p/f.name).write_bytes(f.read_bytes())
  run(target,models,poles)
 run('55490',['LB40NN 1P+N'],'1P+N')
 run('55497',['LB50HW 1P+N'],'1P+N')
 run('55498',['LB63HW 3P+N'],'3P+N')
