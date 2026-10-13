"""Remove source Z offsets without changing XY outlines, colors or dimensions."""
import json,re
from pathlib import Path
import ezdxf
from ezdxf import bbox
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.config import Configuration
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page,Margins
from ezdxf.addons.drawing.properties import LayoutProperties
ROOT=Path(__file__).resolve().parents[1]/'data/CatalogTB/Form tủ'
def flat(v):return (v[0],v[1],0)
d=json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'));changed=0
for r in d['shells']:
 folder=ROOT/'Mau'/r['id'];doc=ezdxf.readfile(folder/'ban_ve.dxf');ext=bbox.extents(doc.modelspace(),fast=True)
 if not ext.has_data or max(abs(ext.extmin.z),abs(ext.extmax.z))<1e-7:continue
 for filename in ('ban_ve.dxf','ban_ve_co_khung_goc.dxf'):
  doc=ezdxf.readfile(folder/filename)
  for e in list(doc.entitydb.values()):
   if not e.is_alive:continue
   t=e.dxftype()
   if t=='LINE':e.dxf.start=flat(e.dxf.start);e.dxf.end=flat(e.dxf.end)
   elif t=='POINT':e.dxf.location=flat(e.dxf.location)
   elif t in ('INSERT','TEXT','ATTRIB','ATTDEF','MTEXT'):e.dxf.insert=flat(e.dxf.insert)
   elif t in ('CIRCLE','ARC','ELLIPSE'):e.dxf.center=flat(e.dxf.center)
   elif t=='LWPOLYLINE':e.dxf.elevation=0
   elif t=='BLOCK':e.dxf.base_point=flat(e.dxf.base_point)
   elif t=='VERTEX':e.dxf.location=flat(e.dxf.location)
   elif t=='POLYLINE':e.dxf.elevation=flat(e.dxf.elevation)
   elif t=='SPLINE':e.control_points=[flat(v) for v in e.control_points];e.fit_points=[flat(v) for v in e.fit_points]
  doc.saveas(folder/filename)
  if filename=='ban_ve_co_khung_goc.dxf':
   backend=SVGBackend();Frontend(RenderContext(doc),backend,config=Configuration()).draw_layout(doc.modelspace(),layout_properties=LayoutProperties('Model','#212830','#ffffff',units=4,dark_background=True));svg=backend.get_string(Page(0,0,margins=Margins(10,10,10,10)));svg=re.sub(r'stroke-width: ([0-9.]+)',lambda m:'stroke-width: '+str(max(1000,float(m[1]))),svg);(folder/'xem_truoc.svg').write_text(svg,encoding='utf-8')
 changed+=1
print('Flattened source Z offsets',changed)
