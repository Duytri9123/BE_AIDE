"""Import reviewed six-view STEP families without merging poles, coils or mounting variants."""
import json,math,hashlib
from pathlib import Path
import ezdxf
from ezdxf import bbox
from ezdxf.math import Matrix44
from ls_native_writer import CAT,ROOT,write_profile,price_option
import sys
sys.path.insert(0,str(ROOT))
LABELS={'FRONT':'Mặt trước','REAR':'Mặt sau','SIDE-L':'Mặt bên trái','SIDE':'Mặt bên phải','TOP':'Mặt trên','BOTTOM':'Mặt dưới'}
ZUP_YPLUS=[('FRONT','FRONT',-90),('REAR','REAR',90),('SIDE-L','BOTTOM',-90),('SIDE','TOP',-90),('TOP','SIDE-L',-90),('BOTTOM','SIDE',-90)]
PRICES=[r for r in json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'] if r.get('brand') in ['LS','LS Electric']]
def entities(ident,mapping,source_brand='LS'):
 p=CAT/source_brand/'NguonBenNgoai'/ident
 prefix=next((candidate for candidate in ['hlr-all-','hlr-reviewed-','hlr-poly-all-','hlr-poly-'] if all((p/(candidate+c+'.dxf')).exists() for c in LABELS)),None)
 if prefix is None:return None,None
 views=[]
 for code,original,angle in mapping:
  doc=ezdxf.readfile(p/(prefix+original+'.dxf'));assert not doc.audit().errors
  from ls_projection_compaction import compact_lines
  doc=compact_lines(doc)
  es=[]
  for e in doc.modelspace():
   q=e.copy();q.transform(Matrix44.z_rotate(math.radians(angle)));q.doc=None;es.append(q)
  views.append((code,LABELS[code],es))
  del e,doc
  import gc;gc.collect()
 b={c:bbox.extents(es).size for c,l,es in views}
 for a,c,axis in [('FRONT','REAR','x'),('FRONT','REAR','y'),('FRONT','SIDE','y'),('FRONT','SIDE-L','y'),('FRONT','TOP','x'),('FRONT','BOTTOM','x'),('SIDE','TOP','x')]:
  lhs=getattr(b[a],axis);rhs=(b[c].y if a=='SIDE' and c=='TOP' else getattr(b[c],axis));assert abs(lhs-rhs)<.2,(ident,a,c,lhs,rhs)
 return views,prefix

def import_family(ident,kind,models,poles,choose,mapping=ZUP_YPLUS,spec=None,family=None,name=None,evidence=None):
 views,prefix=entities(ident,mapping)
 if not views:print('Pending',ident,flush=True);return
 rows=[r for r in PRICES if choose(r)];assert rows,(ident,models)
 p=CAT/'LS/NguonBenNgoai'/ident;source=json.loads((p/'source.json').read_text());source.update(projection_method=('Open CASCADE polygonal visible-edge HLR; absolute mesh deflection 0.05 mm' if prefix.startswith('hlr-poly') else 'Open CASCADE exact visible-edge HLR; curve approximation 0.025 mm'),unit_evidence='Manufacturer STEP; STEPControl import in MM; output INSUNITS=4',step_sha256=hashlib.sha256((p/'source.step').read_bytes()).hexdigest(),axis_mapping=[{'view':c,'source_projector':o,'rotation_degrees':a} for c,o,a in mapping],six_views_verified=True)
 if evidence:source['family_compatibility_evidence']=evidence
 return write_profile(family or 'STEP-'+ident.replace('/','-'),name or 'LS · '+kind+' · '+' / '.join(models),kind,models,poles,[price_option(r) for r in rows],views,source,spec)
if __name__=='__main__':
 for ident,model in [('50483','MMS-32S'),('50486','MMS-63S'),('50488','MMS-100S')]:
  import_family(ident,'MOTOR_PROTECTION',[model],'3P',lambda r,m=model:r['sku']==m,spec={'Kiểu lắp':'Theo mô hình gốc; kiểm tra phụ kiện gá trước gia công'})
