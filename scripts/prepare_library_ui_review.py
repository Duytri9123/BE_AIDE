import json
from pathlib import Path
from app.services.catalogtb_browser import browser_data
from app.api.v1.endpoints.equipment_library import _cad_view_file,_raster_preview
from PIL import Image
import io
out=Path(__file__).resolve().parents[2]/'tmp/library-security';out.mkdir(parents=True,exist_ok=True)
data=browser_data();(out/'browser-fixture.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
item=next(p for p in data['items'] if p['display']=='MCCB LS ABN400AF · 3P')
view=next((v for v in item['views'] if v['id']==item['primary_view']),item['views'][0])
png=_raster_preview(_cad_view_file(item['id'],view['id'],'preview'))
(out/'ls-original-color.png').write_bytes(png)
im=Image.open(io.BytesIO(png)).convert('RGB')
red=sum(r>150 and r>g*1.5 and r>b*1.5 for r,g,b in im.getdata())
assert red>20, 'Original red terminal/copper outlines must remain visible'
for box in [(0,0,im.width,im.height//5),(0,im.height*4//5,im.width,im.height)]:
    assert sum(r>150 and r>g*1.5 and r>b*1.5 for r,g,b in im.crop(box).getdata())>100, 'Copper terminal outlines must remain visible at both ends'
print('LS source-color PNG verified; red pixels:',red)
