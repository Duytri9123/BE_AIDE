"""Extract actual drawing text for every public CAD, without inferring identity."""
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit,unquote
import ezdxf

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.services.catalogtb_browser import browser_data
from app.api.v1.endpoints.equipment_library import _cad_view_file
from app.services.equipment_library import _catalogtb_asset


def drawing_text(entities,doc,seen=None,depth=0):
    seen=set() if seen is None else seen
    if depth>12:return
    for entity in entities:
        kind=entity.dxftype()
        if kind in {'TEXT','MTEXT','ATTRIB','ATTDEF'}:
            text=entity.plain_text() if kind=='MTEXT' else entity.dxf.text
            if text.strip():yield text.strip()
        elif kind=='INSERT':
            yield from drawing_text(entity.attribs,doc,seen,depth+1)
            name=entity.dxf.name
            if name not in seen:
                seen.add(name)
                yield from drawing_text(doc.blocks[name],doc,seen,depth+1)


if __name__=='__main__':
    items=[]
    for index,device in enumerate(browser_data()['items'],1):
        record={k:device.get(k) for k in ('id','name','brand','brand_identification_status','type','product_code','spec')}
        record['views']=[]
        for view in device['views']:
            parts=urlsplit(view['download']).path.strip('/').split('/')
            path=_catalogtb_asset(_cad_view_file(unquote(parts[1]),unquote(parts[3]),'dxf'))
            result={'view_id':view['id'],'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
            try:
                doc=ezdxf.readfile(path)
                result['texts']=list(dict.fromkeys(drawing_text(doc.modelspace(),doc)))
            except Exception as exc:result['error']=type(exc).__name__
            record['views'].append(result)
        items.append(record)
        if index%100==0:print(index,flush=True)
    result={'checked_devices':len(items),'checked_views':sum(len(d['views']) for d in items),'items':items}
    (ROOT/'docs/library-dxf-identity-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Complete:',result['checked_devices'],result['checked_views'])
