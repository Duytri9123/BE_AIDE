"""Recheck earlier generated candidates against source cancellation and keep source locks."""
import json,re
from collections import defaultdict
import ezdxf
from ezdxf import dynblkhelper,transform
from ezdxf.addons import Importer
from extract_project_helpers import OUT,ROOT,save,inside,bounds,render
from project_form_rejections import rejection,CACHE,norm
data=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'))
rejected=json.loads((OUT/'form_loai_bo.json').read_text(encoding='utf-8'))
groups=defaultdict(list)
for row in data['shells']:groups[row['original_dxf']].append(row)
kept=[]
for path,rows in groups.items():
 doc=ezdxf.readfile(ROOT/path);CACHE.clear();locks=[]
 for e in doc.modelspace().query('INSERT'):
  parent=dynblkhelper.get_dynamic_block_definition(e);name=parent.name if parent else e.dxf.name
  if re.search(r'KHOA|LOCK|LATCH|CAM LOCK',norm(name)):locks.append((e,bounds(e),name))
 for row in rows:
  r=row['source_rectangle'];reason=rejection(doc,r)
  if reason:
   rejected.append({'source_id':row['source_id'],'source_file':row['source_file'],'source_handle':row['source_handle'],'reason':reason});continue
  selected=[v for v in locks if inside(v[1],r)]
  folder=OUT/'Mau'/row['id'];clean=ezdxf.readfile(folder/'ban_ve.dxf')
  if not row.get('lock_handles_preserved') and selected:
   imp=Importer(doc,clean);imp.import_entities([v[0] for v in selected]);imp.finalize()
   # Imported entities alone must receive the same source-to-form translation.
   added=list(clean.modelspace())[-len(selected):]
   transform.translate(added,(-(r[0]+r[2])/2,-(r[1]+r[3])/2,0))
   for layout in [clean.modelspace(),*list(clean.blocks)]:
    for e in list(layout):
     if e.dxftype() in ('TEXT','MTEXT','ATTRIB','ATTDEF','DIMENSION','LEADER','MULTILEADER'):layout.delete_entity(e)
   clean.saveas(folder/'ban_ve.dxf');render(clean,folder/'xem_truoc.svg')
  row['lock_handles_preserved']=[v[0].dxf.handle for v in selected]
  row['lock_count']=len(selected);row['source_units_code']=doc.units
  row['lock_review_status']='source_lock_blocks_preserved' if selected else 'needs_visual_review_not_proof_of_no_lock'
  if not selected:row['notes'].append('Chưa nhận diện khóa bằng tên block; cần đối chiếu CAD nguồn, không hiểu là tủ không có khóa.')
  row['notes'][0]='Giữ đường bao mặt, đèn và khóa đã nhận diện từ CAD gốc; bỏ thiết bị điện còn lại và chữ.'
  row['cancellation_checked']=True;save(folder/'thong_tin.json',row);kept.append(row)
 print(path,'kept',len(kept),'locks',len(locks),flush=True)
data['shells']=kept;data['rules']=['Giữ vị trí đèn và khóa gốc. Loại mẫu gạch bỏ/hủy/lỗi. Mẫu chưa xác nhận mặt không tự chọn.']
save(OUT/'catalog.json',data);save(OUT/'form_loai_bo.json',list({(r['source_id'],r['source_handle']):r for r in rejected}.values()))
print('Kept',len(kept),'Rejected',len(rejected))
