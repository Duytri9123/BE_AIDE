"""Invalidate one D04 extraction whose prior source selection included external title."""
import json
from pathlib import Path

native=Path(__file__).resolve().parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/MITSUBISHI_D04_DU_LIEU_MOI/native'
device_id='MIT-D04-C6-I03'
path=native/'manifest.json'
manifest=json.loads(path.read_text(encoding='utf8'))
selected=[m for m in manifest if m['id']==device_id]
assert len(selected)==1 and selected[0]['source_handles']==['37ADEF','37B04B']
path.write_text(json.dumps([m for m in manifest if m['id']!=device_id],ensure_ascii=False,indent=2)+'\n',encoding='utf8')
for suffix in ('.dwg','.wmf','.png','-crop.png'):
    target=native/(device_id+suffix)
    if target.exists(): target.unlink()
print('Removed prior C6-I03 export that contained external title; source DWG untouched')
