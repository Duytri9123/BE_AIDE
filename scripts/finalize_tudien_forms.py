import json,re
import ezdxf
from ezdxf import bbox,transform
from ezdxf.disassemble import recursive_decompose
from extract_project_helpers import OUT,save,render
d=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'))
for row in d['shells']:
 folder=OUT/'Mau'/row['id'];doc=ezdxf.readfile(folder/'ban_ve.dxf');intervals=[]
 if list(doc.modelspace().query('INSERT')):
  entities=[e.copy() for e in recursive_decompose(doc.modelspace()) if e.dxftype() not in ('TEXT','MTEXT','ATTRIB','ATTDEF','DIMENSION','HATCH')]
  for e in list(doc.modelspace()):doc.modelspace().delete_entity(e)
  for e in entities:doc.modelspace().add_entity(e)
  doc.saveas(folder/'ban_ve.dxf');render(doc,folder/'xem_truoc.svg')
 for e in doc.modelspace():
  b=bbox.extents([e],fast=True)
  if b.has_data:intervals.append((b.extmin.y,b.extmax.y,e))
 groups=[]
 for lo,hi,e in sorted(intervals,key=lambda r:r[0]):
  if not groups or lo>groups[-1][1]+200:groups.append([lo,hi,[e]])
  else:groups[-1][1]=max(groups[-1][1],hi);groups[-1][2].append(e)
 removed=0
 if len(groups)>1:
  largest=max(len(g[2]) for g in groups)
  for g in groups:
   if len(g[2])<=8 and len(g[2])<largest*.05:
    for e in g[2]:doc.modelspace().delete_entity(e);removed+=1
 if removed:
  ext=bbox.extents(doc.modelspace(),fast=True);transform.translate(doc.modelspace(),(-(ext.extmin.x+ext.extmax.x)/2,-(ext.extmin.y+ext.extmax.y)/2,0));doc.saveas(folder/'ban_ve.dxf');render(doc,folder/'xem_truoc.svg')
 row['cleaning']['isolated_annotation_frames_removed']=removed
 size=row.get('size_from_source') or ''
 match=re.search(r'C\s*(\d+(?:[.,]\d+)?)\s*x\s*R\s*(\d+(?:[.,]\d+)?)\s*x\s*S\s*(\d+(?:[.,]\d+)?)',size,re.I)
 if match:row['dimensions_mm']=dict(zip(('height','width','depth'),(float(v.replace(',','.')) for v in match.groups())))
 row['review_status']='requires_visual_review_of_remaining_unknown_geometry'
 row['material_source_value']=row.get('material_from_source')
 thickness=re.search(r'(\d+(?:[.,]\d+)?)\s*mm',row.get('material_from_source') or '',re.I)
 row['sheet_thickness_mm']=float(thickness.group(1).replace(',','.')) if thickness else None
 save(folder/'thong_tin.json',row)
 saved=ezdxf.readfile(folder/'ban_ve.dxf')
 assert not list(saved.modelspace().query('TEXT MTEXT DIMENSION HATCH')),row['id']
 assert all(all(v.dxftype() in ('REGION','BODY','3DSOLID') for v in saved.blocks[e.dxf.name]) for e in saved.modelspace().query('INSERT')),row['id']
save(OUT/'catalog.json',d)
print('Verified cleaned geometry and metadata:',len(d['shells']))
