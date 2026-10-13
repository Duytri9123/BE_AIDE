import json,shutil
from pathlib import Path
from extract_project_helpers import ROOT,OUT,save
staged=ROOT/'BE_AIDE/tmp/forms_mechanical_restored'
new=json.loads((staged/'catalog.json').read_text(encoding='utf-8'));old=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'));previous={r['id']:r for r in old['shells']}
assert len(new['shells'])==len(old['shells'])
assert {r['id'] for r in new['shells']}==set(previous)
for row in new['shells']:
 prior=previous[row['id']]
 for key in ('layout_analysis_json','separation_review','reuse_decision','dimensions_mm','sheet_thickness_mm','material_source_value','review_status'):row[key]=prior.get(key)
 row['cleaning_policy']={'remove':'thiết bị điện nhận diện được, nét đồng/dây nhận diện được, chữ/kích thước và nét gạch chéo đã yêu cầu','preserve':'tên tủ, loại tôn, đèn, khóa, bản lề và hình học cơ khí nhận diện được','unidentified_geometry':'cần đối chiếu nguồn; chưa chứng nhận hoàn chỉnh'}
 dest=OUT/'Mau'/row['id'];shutil.copyfile(staged/'Mau'/row['id']/'ban_ve.dxf',dest/'ban_ve.dxf');shutil.copyfile(staged/'Mau'/row['id']/'xem_truoc.svg',dest/'xem_truoc.svg');save(dest/'thong_tin.json',row)
save(OUT/'catalog.json',new)
print('Restored mechanical features; preserved baseline JSON:',len(new['shells']))
