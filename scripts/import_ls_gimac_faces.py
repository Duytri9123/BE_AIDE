import json,hashlib
import ezdxf
from ezdxf import bbox,disassemble
from ls_native_writer import CAT,ROOT,write_profile,price_option
p=CAT/'LS/NguonBenNgoai/55455';doc=ezdxf.readfile(p/'source.dxf');assert doc.units==4
geo=[]
for src in doc.modelspace():
 if src.dxftype() in {'DIMENSION','ACAD_TABLE','LEADER','MLEADER'}:continue
 for e in disassemble.recursive_decompose([src]):
  if e.dxftype() not in {'LINE','ARC','CIRCLE','SPLINE','ELLIPSE','LWPOLYLINE','POLYLINE'}:continue
  c=e.dxf.color;c=7 if c==0 else (doc.layers.get(e.dxf.layer).dxf.color if c==256 else c)
  if c!=7:continue
  b=bbox.extents([e])
  if b.has_data:geo.append((e,b))
def crop(x1,x2,y1,y2):
 return [e for e,b in geo if b.extmin.x>=x1-.01 and b.extmax.x<=x2+.01 and b.extmin.y>=y1-.01 and b.extmax.y<=y2+.01]
views=[('FRONT','Mặt trước',crop(101.91838,211.91839,769.12574,879.12575)),('SIDE-L','Mặt bên trái',crop(-62.5086,45.9916,769.12574,879.12575)),('SIDE-R','Mặt bên phải',crop(322.7875,431.2877,769.12574,879.12575)),('REAR','Mặt sau',crop(523.7634,633.7636,769.12574,879.12575)),('TOP','Mặt trên',crop(101.91838,211.91839,970.26449,1056.76450)),('BOTTOM','Mặt dưới',crop(101.91838,211.91839,614.4338,715.2361))]
assert all(len(es)>5 for _,_,es in views)
assert abs(bbox.extents(views[0][2]).size.x-110)<.01
rows=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'];selected=[r for r in rows if r.get('brand') in ['LS','LS Electric'] and r['sku'].startswith('GIMAC-1000 NO,M485')];assert len(selected)==1
source=json.loads((p/'source.json').read_text());source.update(source_dxf_sha256=hashlib.sha256((p/'source.dxf').read_bytes()).hexdigest(),unit_evidence='Supplier INSUNITS=4; front projection 110 x 110 mm',projection_method='Upper native NO,M485 row only; exclude ETHERNET row, text and dimensions')
write_profile('GIMAC1000-NO-M485','LS · Đồng hồ GIMAC-1000 · NO · M485','METER',['GIMAC-1000 NO,M485'],None,[price_option(r) for r in selected],views,source,{'Giao tiếp':'M485','Biến thể':'NO'})
