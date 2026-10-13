"""Restore the actual source drawing border/title block in previews, never synthesize it."""
import json,logging
raise SystemExit('Disabled: latest request removes customer, company, logo and project title contents from forms.')
from collections import defaultdict
import ezdxf
from ezdxf import transform
from ezdxf.addons import Importer
from extract_project_helpers import ROOT,OUT,save,render
logging.getLogger('ezdxf').setLevel(logging.ERROR)
d=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'));groups=defaultdict(list)
for row in d['shells']:groups[row['original_dxf']].append(row)
for path,rows in groups.items():
 src=ezdxf.readfile(ROOT/path)
 for row in rows:
  frame=src.entitydb.get(row['source_handle']);offset=row['cleaning'].get('accessory_alignment_translation');folder=OUT/'Mau'/row['id']
  if not frame or not offset:
   row['original_title_frame']={'status':'needs_coordinate_review','source_handle':row['source_handle']};continue
  preview=ezdxf.readfile(folder/'ban_ve.dxf');before={e.dxf.handle for e in preview.modelspace()};imp=Importer(src,preview);imp.import_entities([frame]);imp.finalize()
  added=[e for e in preview.modelspace() if e.dxf.handle not in before];transform.translate(added,(offset[0],offset[1],0))
  preview.styles.new('SOURCE_FACE_LABEL',dxfattribs={'font':'arial.ttf'})
  for f in row.get('faces',[]):preview.modelspace().add_text(f['source_label'],dxfattribs={'height':32,'style':'SOURCE_FACE_LABEL','insert':tuple(f['label_position_clean'])})
  # Vietnamese source title attributes require a Unicode font to remain legible.
  for e in preview.entitydb.values():
   if e.dxftype() in ('TEXT','ATTRIB','ATTDEF','MTEXT'):
    text=e.dxf.text if e.dxftype()!='MTEXT' else e.plain_text()
    if any(ord(c)>127 for c in text):e.dxf.style='SOURCE_FACE_LABEL'
  preview.saveas(folder/'ban_ve_co_khung_goc.dxf');render(preview,folder/'xem_truoc.svg')
  row['original_title_frame']={'status':'restored_from_source','source_handle':row['source_handle'],'preview_cad':f"Mau/{row['id']}/ban_ve_co_khung_goc.dxf",'source_title_attributes':row['source_title_attributes'],'transform':'translation_only_no_mirror'}
  row['view_orientation']={'mirrored':False,'rotation_applied_deg':0,'basis':'Source geometry translated only. Inner-door rear/front viewpoint requires source confirmation; do not mirror automatically.','review_status':'needs_front_rear_view_confirmation'}
  save(folder/'thong_tin.json',row)
 save(OUT/'catalog.json',d);print(path,'source title frames restored',flush=True)
print('Original title frame previews:',sum(r.get('original_title_frame',{}).get('status')=='restored_from_source' for r in d['shells']))
