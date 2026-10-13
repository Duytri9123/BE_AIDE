from pathlib import Path
import json,logging
import ezdxf
logging.disable(logging.CRITICAL)
root=Path(__file__).resolve().parents[1]
doc=ezdxf.readfile(root/'tmp/accessory_source_review/source.dxf')
result=[]
for handle in ('37AA98','37AAA3'):
    e=doc.entitydb[handle]
    result.append({'handle':handle,'block':e.dxf.name,'attributes':[(a.dxf.tag,a.dxf.text) for a in e.attribs],
                   'types':[(v.dxftype(),v.dxf.get('color',256),v.dxf.layer) for v in e.virtual_entities()][:80]})
(root/'tmp/accessory_source_review/frame_attributes.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False),flush=True)
