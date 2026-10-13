"""Keep the complete source view set, including views without rectangular polylines."""
import json,re,logging
from collections import defaultdict
import ezdxf
from extract_project_helpers import ROOT,OUT,save,render
from project_form_rejections import norm
logging.getLogger('ezdxf').setLevel(logging.ERROR)
d=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'));groups=defaultdict(list)
for row in d['shells']:groups[row['original_dxf']].append(row)
LABEL=re.compile(r'^(?:1ST DOOR VIEW|2ND DOOR VIEW|EQUIPMENT VIEW|E-SIDE VIEW|SIDE VIEW|TOP VIEW|BOTTOM VIEW|FRONT VIEW|REAR VIEW|SECTION\b|MAT\b|CANH (NGOAI|TRONG)\b|BEN TRONG TU\b|HONG\b|NOC\b|DAY TU\b|KHUNG TU\b)')
for path,rows in groups.items():
 src=ezdxf.readfile(ROOT/path);labels=[]
 for e in src.modelspace().query('TEXT MTEXT'):
  text=e.dxf.text if e.dxftype()=='TEXT' else e.plain_text()
  if LABEL.search(norm(text)):labels.append((e,text))
 for row in rows:
  folder=OUT/'Mau'/row['id'];a=json.loads((folder/'bo_tri_goc.json').read_text(encoding='utf-8'));sheet=a['source_sheet_bounds'];offset=row['cleaning'].get('accessory_alignment_translation')
  if not offset:continue
  dx,dy=offset;faces=row.get('faces',[]);known={f['source_label_handle'] for f in faces}
  for e,text in labels:
   p=e.dxf.insert
   if e.dxf.handle in known or not (sheet[0]<=p.x<=sheet[2] and sheet[1]<=p.y<=sheet[3]):continue
   faces.append({'id':row['id']+'-'+e.dxf.handle,'kind':'source_view_requires_boundary_review','name':text,'source_label':text,'display_label':text,'source_label_handle':e.dxf.handle,'label_position_clean':[p.x+dx,p.y+dy],'source_bounds':None,'clean_bounds':None,'identification_basis':'source_label_preserved_no_boundary_inferred'})
  row['faces']=faces;row['drawing_labels']=[f['source_label'] for f in faces];row['view_preservation_policy']={'keep':'toàn bộ mặt và hình học vỏ trong tờ nguồn','remove':'thiết bị điện, đèn, đồng/dây và chú thích không cần thiết','reference_layout':'cabinet_templates/formtu','geometry_source':'Tudien','missing_view_policy':'không tự dựng mặt không có trong nguồn','verification':'nhãn nguồn đã giữ; cần đối chiếu hình học từng mặt, không chứng nhận đầy đủ cơ khí'}
  preview=ezdxf.readfile(folder/'ban_ve.dxf');preview.styles.new('SOURCE_FACE_LABEL',dxfattribs={'font':'arial.ttf'})
  for f in faces:preview.modelspace().add_text(f['source_label'],dxfattribs={'height':32,'style':'SOURCE_FACE_LABEL','insert':tuple(f['label_position_clean'])})
  render(preview,folder/'xem_truoc.svg');save(folder/'thong_tin.json',row);a['source_faces']=faces;save(folder/'bo_tri_goc.json',a)
 save(OUT/'catalog.json',d);print(path,'complete source view labels',flush=True)
print('Preserved source view sets:',len(d['shells']))
