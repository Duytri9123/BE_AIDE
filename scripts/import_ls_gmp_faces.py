"""Import GMP front/side pairs explicitly shared by LS 2P/3P/3PR title."""
import json,hashlib
import ezdxf
from ezdxf import bbox,disassemble
from ls_native_writer import CAT,ROOT,write_profile,price_option
from import_ls_acb_full import groups
p=CAT/'LS/NguonBenNgoai/46412/drawing-03';doc=ezdxf.readfile(p/'source.dxf');geometry=[]
dims=list(doc.modelspace().query('DIMENSION'));assert dims and all(abs(e.override().get('dimlfac',1)-1)<.0001 for e in dims)
assert any(abs(e.dxf.get('actual_measurement',0)-79.5)<.001 for e in dims)
for src in doc.modelspace():
 if src.dxftype() in {'DIMENSION','ACAD_TABLE','LEADER','MLEADER'}:continue
 for e in disassemble.recursive_decompose([src]):
  if e.dxftype() not in {'LINE','ARC','CIRCLE','SPLINE','ELLIPSE','LWPOLYLINE','POLYLINE'} or e.dxf.layer=='DIM':continue
  b=bbox.extents([e])
  if b.has_data:geometry.append((e,b))
bands=groups([(b.extmin.x,b.extmax.x) for e,b in geometry]);assert len(bands)==6
prices=[r for r in json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'] if r.get('brand') in ['LS','LS Electric']]
for frame,i in [('GMP22',2),('GMP40',4)]:
 views=[]
 for code,label,band in [('FRONT','Mặt trước',bands[i]),('SIDE','Mặt bên',bands[i+1])]:
  es=[e for e,b in geometry if b.extmin.x>=band[0]-.001 and b.extmax.x<=band[1]+.001];assert abs(bbox.extents(es).size.y-(79.5 if frame=='GMP22' else 78))<.001;views.append((code,label,es))
 selected=[r for r in prices if r['sku'].startswith((frame+'-2P (1a1b)',frame+'-3P (1a1b)'))];assert len(selected)==4
 source=json.loads((p/'source.json').read_text());source.update(source_dxf_sha256=hashlib.sha256((p/'source.dxf').read_bytes()).hexdigest(),unit_evidence='Native 79.5 dimension equals geometric 79.5; all dimension scale factors=1; legacy drawing units unspecified',projection_method='Separate middle/right front-side pair; source title explicitly shares 2P/3P/3PR,1a1b; dimensions excluded')
 write_profile(frame+'-2P-3P-1a1b','LS · Rơ le bảo vệ động cơ · '+frame+' · 2P/3P · 1a1b','RELAY',[frame+'-2P',frame+'-3P'],None,[price_option(r) for r in selected],views,source,{'Tiếp điểm phụ':'1a1b'})

