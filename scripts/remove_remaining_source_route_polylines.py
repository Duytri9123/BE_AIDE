import json
import ezdxf
from extract_project_helpers import OUT,save,render
d=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'))
for row in d['shells']:
 folder=OUT/'Mau'/row['id'];ref=json.loads((folder/'tham_chieu_dong_goc.json').read_text(encoding='utf-8'));offset=row['cleaning'].get('accessory_alignment_translation')
 if not offset:continue
 dx,dy=offset;routes=[]
 for r in ref['route_candidates']:
  if r['type']=='LWPOLYLINE':routes.append([(p[0]+dx,p[1]+dy) for p in r['points_source']])
 doc=ezdxf.readfile(folder/'ban_ve.dxf');removed=0
 for e in list(doc.modelspace().query('LWPOLYLINE')):
  pts=list(e.get_points('xy'))
  if any(len(pts)==len(r) and all(abs(a[0]-b[0])<.01 and abs(a[1]-b[1])<.01 for a,b in zip(pts,r)) for r in routes):doc.modelspace().delete_entity(e);removed+=1
 if removed:doc.saveas(folder/'ban_ve.dxf')
 row['cleaning']['source_route_polylines_removed']=removed;save(folder/'thong_tin.json',row)
 preview=ezdxf.readfile(folder/'ban_ve.dxf');preview.styles.new('SOURCE_FACE_LABEL',dxfattribs={'font':'arial.ttf'})
 for f in row.get('faces',[]):preview.modelspace().add_text(f['source_label'],dxfattribs={'height':32,'style':'SOURCE_FACE_LABEL','insert':tuple(f['label_position_clean'])})
 render(preview,folder/'xem_truoc.svg')
save(OUT/'catalog.json',d)
print('Checked source route polylines:',len(d['shells']))
