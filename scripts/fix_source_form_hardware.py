import json,re,logging
from collections import defaultdict
import ezdxf
from ezdxf import bbox,dynblkhelper
from ezdxf.addons import Importer
from extract_project_helpers import ROOT,OUT,save,render,inside
from project_form_rejections import norm
logging.getLogger('ezdxf').setLevel(logging.ERROR)
d=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'));groups=defaultdict(list)
for row in d['shells']:groups[row['original_dxf']].append(row)
LOCK=re.compile(r'KHOA|LOCK|LATCH|\bMS(?:722|303|308|325|406)|\bAB301|\bME ?4[01]')
def box(e):
 try:
  b=bbox.extents([e],fast=True);return (b.extmin.x,b.extmin.y,b.extmax.x,b.extmax.y) if b.has_data else None
 except:return None
def flat(e):
 if e.dxftype() in ('TEXT','MTEXT','ATTRIB','ATTDEF','DIMENSION','HATCH'):return
 if e.dxftype()=='INSERT':
  try:
   for v in e.virtual_entities():yield from flat(v)
  except:return
 else:yield e.copy()
for path,rows in groups.items():
 src=ezdxf.readfile(ROOT/path);locks=[];supports=[]
 for e in src.modelspace().query('INSERT'):
  p=dynblkhelper.get_dynamic_block_definition(e);name=p.name if p else e.dxf.name;n=norm(name)
  if LOCK.search(n):locks.append(e)
  if re.search(r'SU KEP|THANH DONG|BUSBAR|ISOLATE BKD',n):supports.append(e)
 for row in rows:
  folder=OUT/'Mau'/row['id'];a=json.loads((folder/'bo_tri_goc.json').read_text(encoding='utf-8'));sheet=a['source_sheet_bounds'];offset=row['cleaning'].get('accessory_alignment_translation')
  if not offset:continue
  dx,dy=offset;shift=lambda b:(b[0]+dx,b[1]+dy,b[2]+dx,b[3]+dy);doc=ezdxf.readfile(folder/'ban_ve.dxf');restored=[];protected=[]
  for e in locks:
   eb=box(e)
   if not eb or not inside(eb,sheet):continue
   protected.append(shift(eb))
   for part in flat(e):part.translate(dx,dy,0);doc.modelspace().add_entity(part)
   restored.append(e.dxf.handle)
  areas=[]
  for e in supports:
   eb=box(e)
   if eb and inside(eb,sheet):areas.append(shift(eb))
  removed=0
  for face in row.get('faces',[]):
   if face['kind']!='mounting_plate':continue
   region=face['clean_bounds'];members=[r for r in areas if inside(r,region)]
   if not members:continue
   hull=(max(region[0]+35,min(r[0] for r in members)-120),max(region[1]+35,min(r[1] for r in members)-120),min(region[2]-35,max(r[2] for r in members)+120),min(region[3]-35,max(r[3] for r in members)+120))
   for e in list(doc.modelspace()):
    eb=box(e)
    if not eb and e.dxftype()=='INSERT':p=e.dxf.insert;eb=(p.x,p.y,p.x,p.y)
    if eb and inside(eb,hull) and not any(inside(eb,p) for p in protected):doc.modelspace().delete_entity(e);removed+=1
  doc.saveas(folder/'ban_ve.dxf');preview=ezdxf.readfile(folder/'ban_ve.dxf');preview.styles.new('SOURCE_FACE_LABEL',dxfattribs={'font':'arial.ttf'})
  # Keep source label wording and source position, rather than assigning a new label location.
  for face in row.get('faces',[]):
   face['display_label']=face['source_label'];p=face['label_position_clean'];preview.modelspace().add_text(face['source_label'],dxfattribs={'height':32,'style':'SOURCE_FACE_LABEL','insert':tuple(p)})
  render(preview,folder/'xem_truoc.svg');row['cleaning']['locks_restored_from_source']=restored;row['cleaning']['remaining_busbar_assembly_removed']=removed;save(folder/'thong_tin.json',row)
 save(OUT/'catalog.json',d);print(path,'locks/source labels checked',flush=True)
print('Corrected source locks and labels',len(d['shells']))
