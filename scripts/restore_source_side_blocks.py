"""Retain anonymous source ventilation/lifting blocks in SIDE VIEW."""
import json,re,logging
from collections import defaultdict
import ezdxf
from ezdxf import bbox,dynblkhelper
from ezdxf.addons import Importer
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.config import Configuration
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page,Margins
from ezdxf.addons.drawing.properties import LayoutProperties
from extract_project_helpers import ROOT,OUT,save,inside
from project_form_rejections import norm
logging.getLogger('ezdxf').setLevel(logging.ERROR)
ELECTRICAL=re.compile(r'MCCB|MCB|ACB|RCBO|RCCB|BKN|ABN|CONTACTOR|VOLTMET|AMPERE|DEN BAO|PILOT|FAN|QUAT|CUON|BUSBAR|THANH DONG')
d=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'));groups=defaultdict(list)
exclusions=json.loads((OUT/'form_source_exclusions.json').read_text(encoding='utf-8')) if (OUT/'form_source_exclusions.json').exists() else {}
for r in d['shells']:groups[r['original_dxf']].append(r)
changed=0
for path,rows in groups.items():
 src=ezdxf.readfile(ROOT/path)
 for r in rows:
  folder=OUT/'Mau'/r['id'];regions=[];dims=r.get('dimensions_mm') or {}
  for f in r.get('faces',[]):
   if f['source_label'].strip().upper()!='SIDE VIEW':continue
   b=f.get('source_bounds')
   if b:regions.append((b[0]-60,b[3]-(dims.get('height') or b[3]-b[1])-100,b[2]+60,b[3]+150))
  if not regions:continue
  chosen=[];audit=[]
  for e in src.modelspace().query('INSERT'):
   if not any(a<=e.dxf.insert.x<=c and b<=e.dxf.insert.y<=z for a,b,c,z in regions):continue
   definition=dynblkhelper.get_dynamic_block_definition(e);name=definition.name if definition else e.dxf.name
   if e.dxf.handle in exclusions.get(r['id'],{}).get('source_handles',[]) or name in exclusions.get(r['id'],{}).get('block_names',[]):continue
   if ELECTRICAL.search(norm(name)):continue
   ext=bbox.extents([e],fast=True)
   if ext.has_data and any(inside((ext.extmin.x,ext.extmin.y,ext.extmax.x,ext.extmax.y),region) for region in regions):chosen.append(e);audit.append({'source_handle':e.dxf.handle,'source_block_name':name,'basis':'original_SIDE_VIEW_source_block_preserved_per_user'})
  if not chosen:continue
  added=0
  for filename in ('ban_ve.dxf','ban_ve_co_khung_goc.dxf'):
   doc=ezdxf.readfile(folder/filename);positions={tuple(round(v,4) for v in e.dxf.insert) for e in doc.modelspace().query('INSERT')}
   missing=[e for e in chosen if tuple(round(v,4) for v in e.dxf.insert) not in positions]
   if missing:
    imp=Importer(src,doc);imp.import_entities(missing);imp.finalize();doc.saveas(folder/filename);added=len(missing)
   if filename=='ban_ve_co_khung_goc.dxf' and missing:
    backend=SVGBackend();Frontend(RenderContext(doc),backend,config=Configuration()).draw_layout(doc.modelspace(),layout_properties=LayoutProperties('Model','#212830','#ffffff',units=4,dark_background=True))
    svg=backend.get_string(Page(0,0,margins=Margins(10,10,10,10)));svg=re.sub(r'stroke-width: ([0-9.]+)',lambda m:'stroke-width: '+str(max(1000,float(m[1]))),svg);(folder/'xem_truoc.svg').write_text(svg,encoding='utf-8')
  r['side_view_source_blocks']=audit;save(folder/'thong_tin.json',r);changed+=bool(added)
 save(OUT/'catalog.json',d);print('SIDE VIEW blocks',changed,flush=True)
print('Updated',changed,'side views')
