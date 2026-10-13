import json
from pathlib import Path
import ezdxf
from ezdxf import bbox
base=Path(__file__).resolve().parents[1]
doc=ezdxf.readfile(base/'tmp/accessory_source_review/source.dxf')
for e in doc.modelspace():
    text=e.dxf.text if e.dxftype()=='TEXT' else e.plain_text() if e.dxftype()=='MTEXT' else ''
    if text.strip() in ('400 AF','800 AF','1000 AF','1000 AF+ELCB'):
        center=e.dxf.insert;rows=[]
        for item in doc.modelspace():
            if item.dxftype()=='INSERT':
                at=item.dxf.insert
                if abs(at.x-center.x)<200 and abs(at.y-center.y)<450:
                    box=bbox.extents([item],fast=True)
                    rows.append({'handle':item.dxf.handle,'name':item.dxf.name,'at':list(at),'min':list(box.extmin) if box.has_data else None,'max':list(box.extmax) if box.has_data else None})
        print(json.dumps({'label':text,'at':list(center),'nearby_blocks':rows},ensure_ascii=False),flush=True)

