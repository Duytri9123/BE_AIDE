"""Extract text and attributes from every exported CAD, including nested blocks."""
import json,sys
from pathlib import Path
import ezdxf
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.api.v1.endpoints.cad_library import manifest,LIBRARY

def extract(doc):
    texts=[]; seen=set()
    def walk(entities):
        for e in entities:
            if e.dxftype() in ('TEXT','ATTRIB','ATTDEF','MTEXT'):
                text=e.plain_text() if hasattr(e,'plain_text') else e.dxf.get('text','')
                if text.strip() and text not in texts: texts.append(text.strip())
            elif e.dxftype()=='INSERT':
                walk(e.attribs)
                name=e.dxf.name
                if name not in seen:
                    seen.add(name)
                    block=doc.blocks.get(name)
                    if block is not None: walk(block)
    walk(doc.modelspace())
    return texts

if __name__=='__main__':
    rows=[]
    for item in manifest()['items']:
        try:
            doc=ezdxf.readfile(LIBRARY.parent/item['library']/item['filename'])
            rows.append({**{k:item.get(k) for k in ('id','name','source_block','library','source_file','geometry_fingerprint')},'texts':extract(doc)})
        except Exception as e: rows.append({'id':item['id'],'error':str(e)})
    (ROOT/'data/cad_text_inventory.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
    print('Read',len(rows),'files;',sum(bool(r.get('texts')) for r in rows),'with text;',sum('error' in r for r in rows),'errors')
