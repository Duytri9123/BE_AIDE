import json,hashlib,sys
import ezdxf
from ezdxf import bbox,disassemble
from ls_native_writer import CAT,ROOT,write_profile,price_option
p=CAT/'LS/NguonBenNgoai/46412/drawing-06';d=ezdxf.readfile(p/'source.dxf');assert d.units==4;g=[]
for src in d.modelspace():
 if src.dxftype() in ['DIMENSION','LEADER','MLEADER','ACAD_TABLE']:continue
 for e in disassemble.recursive_decompose([src]):
  if e.dxftype() not in ['LINE','ARC','CIRCLE','SPLINE','LWPOLYLINE','POLYLINE','ELLIPSE']:continue
  c=e.dxf.color;c=7 if c==0 else (d.layers.get(e.dxf.layer).dxf.color if c==256 else c)
  if c!=7:continue
  b=bbox.extents([e]);g.append((e,b))
def crop(x1,x2,y1,y2):return [e for e,b in g if b.extmin.x>=x1-.001 and b.extmax.x<=x2+.001 and b.extmin.y>=y1-.001 and b.extmax.y<=y2+.001]
views=[('FRONT','Mặt trước',crop(232.9697,288.2589,277.7356,356.2357)),('SIDE-R','Mặt bên phải',crop(416.4079,493.7080,277.7356,356.2357)),('SIDE-L','Mặt bên trái',crop(79.3362,156.6363,277.7356,356.2357)),('REAR','Mặt sau',crop(605.4704,660.7596,277.7356,356.2357)),('TOP','Mặt trên',crop(232.9697,288.2589,416.1854,519.7114)),('BOTTOM','Mặt dưới',crop(232.9697,288.2589,110.3615,187.6616))]
assert all(len(es)>5 for _,_,es in views)
rows=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'];selected=[r for r in rows if r.get('brand') in ['LS','LS Electric'] and r['sku']=='GMP60-T (1c)'];assert len(selected)==2
s=json.loads((p/'source.json').read_text());s.update(source_dxf_sha256=hashlib.sha256((p/'source.dxf').read_bytes()).hexdigest(),unit_evidence='Supplier native INSUNITS=4 (mm)',projection_method='Native DIN-rail model six orthographic white projections; cyan dimensions and isometric excluded')
write_profile('GMP60T-DIN','LS · Rơ le bảo vệ động cơ · GMP60-T · DIN rail','RELAY',['GMP60-T'],None,[price_option(r) for r in selected],views,s,{'Kiểu lắp':'DIN rail'})
