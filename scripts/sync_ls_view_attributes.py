"""Read final attribute text from AutoCAD-saved DXF into the view manifest."""
import json
from pathlib import Path
import ezdxf

base=Path(__file__).resolve().parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/LS_D02_DU_LIEU_MOI'
path=base/'native/views.json'
views=json.loads(path.read_text(encoding='utf8'))
changed=0
for view in views:
    entities=list(ezdxf.readfile(base/view['dxf']).modelspace())
    if len(entities)!=1 or entities[0].dxftype()!='INSERT':
        raise RuntimeError(f'{view["id"]}: expected one block INSERT')
    attrs={a.dxf.tag.upper():a.dxf.text for a in entities[0].attribs}
    if attrs!=view['attributes']:
        view['attributes']=attrs
        changed+=1
path.write_text(json.dumps(views,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(f'{len(views)} views, {changed} attribute records refreshed from DXF')
