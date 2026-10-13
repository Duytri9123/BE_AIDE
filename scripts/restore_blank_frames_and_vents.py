"""Preserve source title-grid geometry, side views and repeated ventilation geometry."""
import json,logging,re,os
from collections import defaultdict
import ezdxf
from ezdxf.addons import Importer
from ezdxf import dynblkhelper
from extract_project_helpers import ROOT,OUT,save,inside,bounds
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.config import Configuration
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page,Margins
from ezdxf.addons.drawing.properties import LayoutProperties
logging.getLogger('ezdxf').setLevel(logging.ERROR)
def render(doc,path):
 backend=SVGBackend();Frontend(RenderContext(doc),backend,config=Configuration()).draw_layout(doc.modelspace(),layout_properties=LayoutProperties('Model','#212830','#ffffff',units=4,dark_background=True))
 svg=backend.get_string(Page(0,0,margins=Margins(10,10,10,10)));svg=re.sub(r'stroke-width: ([0-9.]+)',lambda m:'stroke-width: '+str(max(1000,float(m[1]))),svg);path.write_text(svg,encoding='utf-8')
d=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'));groups=defaultdict(list)
for r in d['shells']:groups[r['original_dxf']].append(r)
for path,rows in groups.items():
 src=ezdxf.readfile(ROOT/path)
 primitives=[(e,bounds(e)) for e in src.modelspace().query('LINE LWPOLYLINE POLYLINE ARC CIRCLE ELLIPSE SPLINE')]
 for r in rows:
  if os.environ.get('FORM_REPAIR_ONLY') and not r.get('source_boundary_repaired'):continue
  folder=OUT/'Mau'/r['id'];doc=ezdxf.readfile(folder/'ban_ve.dxf');offset=r['cleaning'].get('accessory_alignment_translation');dims=r.get('dimensions_mm') or {};vent=[];shell=[]
  if dims.get('depth') and dims.get('height'):
   side=[f for f in r.get('faces',[]) if f['source_label'].strip().upper()=='SIDE VIEW'];vertical=[f['source_bounds'] for f in r.get('faces',[]) if f.get('source_bounds') and f['source_bounds'][3]-f['source_bounds'][1]>400]
   if vertical:
    top=max(b[3] for b in vertical)
    for f in [f for f in r.get('faces',[]) if 'SIDE' in f['source_label'].upper()]:
     label=src.entitydb.get(f.get('source_label_handle'))
     if label is None:continue
     x=label.dxf.insert.x;depth=dims['depth'];region=(x-depth/2-40,top-dims['height']-30,x+depth/2+40,top+50)
     for e,b in primitives:
      if not b or not inside(b,region):continue
      width=b[2]-b[0];height=b[3]-b[1]
      if height>400 and (width>depth*.75 or min(abs(b[0]-(x-depth/2)),abs(b[2]-(x+depth/2)))<40):shell.append(e)
    for face in r.get('faces',[]):
     b=face.get('source_bounds')
     if not b or b[3]-b[1]<400:continue
     region=(b[0]-35,b[3]-dims['height']-35,b[2]+35,b[1]+1)
     for e,box in primitives:
      if box and inside(box,region):shell.append(e)
    for f in side:
     label=src.entitydb.get(f.get('source_label_handle'))
     if label is None:continue
     x=label.dxf.insert.x;region=(x-dims['depth']/2-40,top-dims['height']-100,x+dims['depth']/2+40,top+150);slots=defaultdict(list)
     shell.extend(e for e,b in primitives if b and inside(b,region))
     for e in src.modelspace().query('INSERT'):
      definition=dynblkhelper.get_dynamic_block_definition(e);name=definition.name if definition else e.dxf.name
      if re.search(r'MOC|MÓC|TAI|EYEBOLT|LIFT|RING.?BOLT',name.upper()) and (b:=bounds(e)) and inside(b,region):shell.append(e)
     for e in src.modelspace().query('LINE'):
      a,b=e.dxf.start,e.dxf.end
      if abs(a.y-b.y)<.01 and 8<=abs(a.x-b.x)<=150 and inside((min(a.x,b.x),a.y,max(a.x,b.x),a.y),region):slots[(round(min(a.x,b.x),1),round(max(a.x,b.x),1))].append(e)
     for group in slots.values():
      ordered=sorted(group,key=lambda e:e.dxf.start.y)
      if len(ordered)>=5 and all(0<ordered[i+1].dxf.start.y-ordered[i].dxf.start.y<=20 for i in range(len(ordered)-1)):vent.extend(ordered)
  if vent or shell:
   existing={tuple(round(v,3) for v in b) for e in doc.modelspace() if (b:=bounds(e))}
   additions=[]
   for e in vent+shell:
    b=bounds(e);key=tuple(round(v,3) for v in b) if b else None
    if key and key not in existing:additions.append(e);existing.add(key)
   imp=Importer(src,doc);imp.import_entities(additions);imp.finalize();doc.saveas(folder/'ban_ve.dxf')
  dimensions=list(doc.modelspace().query('DIMENSION'));keys={tuple(round(v,3) for v in e.dxf.defpoint) for e in dimensions};dimension_parts=[]
  for e in src.modelspace().query('DIMENSION'):
   if tuple(round(v,3) for v in e.dxf.defpoint) in keys:
    try:dimension_parts.extend(list(e.virtual_entities()))
    except Exception:pass
  if dimension_parts:
   for e in dimensions:doc.modelspace().delete_entity(e)
   imp=Importer(src,doc);imp.import_entities(dimension_parts);imp.finalize();doc.saveas(folder/'ban_ve.dxf')
  preview=ezdxf.readfile(folder/'ban_ve.dxf');frame=src.entitydb.get(r['source_handle']);parts=[]
  if 'FORM_TITLE' not in preview.styles:preview.styles.new('FORM_TITLE',dxfattribs={'font':'arial.ttf'})
  if frame:
   for e in frame.virtual_entities():
    if e.dxftype()=='LINE':parts.append(e)
    elif e.dxftype() in ('TEXT','MTEXT'):
     text=e.dxf.text if e.dxftype()=='TEXT' else e.plain_text()
     if text.strip().upper() in {'DRAWING NAME','PROJECT','CUSTOMER','STANDARD','DATE','SCALE','PAGE','TOTAL','DESIGNER','APPROVED','NAME','DRAWING NO','DRAWING NUMBER','REVISION','TÊN BẢN VẼ','KHÁCH HÀNG','THIẾT KẾ','KÍCH THƯỚC','LOẠI TÔN','SỐ LƯỢNG'} or re.fullmatch(r'[A-Z]|\d{1,2}',text.strip()):parts.append(e)
    elif e.dxftype()=='INSERT' and 'STANDARD' in e.dxf.name.upper():parts.append(e)
    elif e.dxftype()=='LWPOLYLINE':
     pts=list(e.get_points('xy'))
     if all(abs(a[0]-b[0])<.01 or abs(a[1]-b[1])<.01 for a,b in zip(pts,pts[1:])):parts.append(e)
   imp=Importer(src,preview);imp.import_entities(parts);imp.finalize()
   for a in frame.attribs:
    if a.dxf.tag.upper() in {'STANDARD','SCALE','PAGE','TOTAL','PAPER','SHEET','SHEET_NO'}:
     preview.modelspace().add_text(a.dxf.text,dxfattribs={'insert':a.dxf.insert,'height':a.dxf.height,'rotation':a.dxf.rotation,'color':a.dxf.color,'style':'FORM_TITLE'})
  sheet=json.loads((folder/'bo_tri_goc.json').read_text(encoding='utf-8'))['source_sheet_bounds']
  technical=[]
  for e in src.modelspace().query('INSERT'):
   if any(a.dxf.tag=='MATERIAL' for a in e.attribs) and sheet[0]<=e.dxf.insert.x<=sheet[2] and sheet[1]<=e.dxf.insert.y<=sheet[3]:technical.append(e)
  if technical:
   imp=Importer(src,preview);imp.import_entities(technical);imp.finalize()
  preview.saveas(folder/'ban_ve_co_khung_goc.dxf')
  try:render(preview,folder/'xem_truoc.svg')
  except ValueError:pass
  r['blank_source_frame']={'source_handle':r['source_handle'],'geometry_entities':len(parts),'content_removed':['text','attributes','logos','nested_blocks'],'preview_cad':f"Mau/{r['id']}/ban_ve_co_khung_goc.dxf"}
  r['ventilation_review']={'preserved_parallel_slot_entities':len(vent),'basis':'SIDE VIEW retains original source shell primitives, ventilation, mechanical fastener holes and lifting hooks; electrical holes removed on door/interior views','needs_visual_confirmation':True,'side_view_geometry_preserved':True}
  r['technical_annotation_policy']={'preserve':['STANDARD','SCALE','sheet_grid','FORM','SIZE','MATERIAL','PAINTING','ASSEMBLY'],'clear':['DRAWING_NAME','CUSTOMER','company','logo','dates'],'dimension_change_policy':'Update source geometry, dimension annotations, SIZE and dimensions_mm consistently; update SCALE when drawing scale changes. Do not alter unchanged source values.'}
  r['view_orientation']={'mirrored':False,'rotation_applied_deg':0,'translation_mm':[0,0,0],'coordinate_system':'original_source_modelspace','review_status':'source_views_preserved_no_mirror'}
  r['cleaning']['accessory_alignment_translation']=[0,0]
  for f in r.get('faces',[]):
   label=src.entitydb.get(f.get('source_label_handle'))
   if label is not None:f['label_position_clean']=[label.dxf.insert.x,label.dxf.insert.y]
   f['clean_bounds']=f.get('source_bounds')
  save(folder/'thong_tin.json',r)
 save(OUT/'catalog.json',d);print('Blank frames/vents',len(rows),flush=True)
print('Restored',len(d['shells']),'blank source frames')
