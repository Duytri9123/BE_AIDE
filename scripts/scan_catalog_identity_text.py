"""Read visible CAD text/attributes from every profile, including referenced blocks.

This is evidence extraction, not a manufacturer/model classifier. Unused block
definitions are excluded so unrelated models cannot contaminate recognition.
"""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import ezdxf

ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'data/CatalogTB'


def extract_drawing(path):
    doc=ezdxf.readfile(path)
    texts=[];blocks=[];visited=set()
    def visit(entities,depth=0):
        if depth>12:return
        for entity in entities:
            kind=entity.dxftype()
            if kind in {'TEXT','ATTRIB','ATTDEF'}:
                value=entity.dxf.get('text','')
                if value.strip():texts.append(value.strip())
            elif kind=='MTEXT':
                value=entity.plain_text()
                if value.strip():texts.append(value.strip())
            elif kind=='INSERT':
                name=entity.dxf.name
                blocks.append(name)
                visit(entity.attribs,depth+1)
                if name not in visited and name in doc.blocks:
                    visited.add(name);visit(doc.blocks[name],depth+1)
    visit(doc.modelspace())
    return {'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'texts':list(dict.fromkeys(texts)),
            'referenced_blocks':list(dict.fromkeys(blocks)),'units':doc.units}


def scan_profile(path):
    raw=json.loads(path.read_text(encoding='utf-8-sig'));views=[]
    for view in raw.get('cad_don') or []:
        drawing=(path.parent/view.get('duong_dan','')).resolve()
        if not drawing.is_file() or not drawing.is_relative_to(CAT.resolve()):continue
        try:result=extract_drawing(drawing)
        except Exception as error:result={'error':type(error).__name__+': '+str(error)[:180]}
        views.append({'id':view['id_hinh_goc'],'path':drawing.relative_to(CAT).as_posix(),**result})
    return {'profile':path.relative_to(CAT).as_posix(),'display':raw.get('ten_san_pham'),
            'source_model':raw.get('ma_dong_san_pham'),'brand':raw.get('hang_xac_nhan'),
            'views':views,'texts':list(dict.fromkeys(t for v in views for t in v.get('texts',[])))}


def main():
    paths=sorted(CAT.rglob('thong_tin_thiet_bi.json'));records=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(scan_profile,p) for p in paths]
        for future in as_completed(futures):
            records.append(future.result())
            if len(records)%100==0:print(f'Scanned {len(records)}/{len(paths)} source profiles',flush=True)
    records.sort(key=lambda r:r['profile'])
    result={'checked_at':'2026-10-17','profiles':len(records),
            'views':sum(len(r['views']) for r in records),
            'with_text':sum(bool(r['texts']) for r in records),
            'errors':sum(bool(v.get('error')) for r in records for v in r['views']),'items':records}
    (ROOT/'docs/catalog-source-text-evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='items'}),flush=True)


if __name__=='__main__':main()
