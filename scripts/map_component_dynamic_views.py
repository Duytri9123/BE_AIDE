"""Associate source INSERT handles with dynamic block visibility choices."""
import json
import mmap
import re
from pathlib import Path

base=Path(__file__).resolve().parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
inventory=json.loads((base/'full_accessory_cad_inventory.json').read_text(encoding='utf8'))
analysis_path=base/'THIET_BI_KHAC_2026/cad_view_analysis.json'
analysis=json.loads(analysis_path.read_text(encoding='utf8'))
dynamic=json.loads((base/'THIET_BI_KHAC_2026/dynamic_visibility_states.json').read_text(encoding='utf8'))['blocks']
source=base.parent/'bao_cao_thu_vien_phu_kien/thu_vien_phu_kien.dxf'
views=[r for r in inventory['records'] if r['kind']=='view']
wanted={h.upper() for r in views for h in r.get('source_handles',[])}

def value(blob,code):
    match=re.search(rb'(?:\A|\r\n)\s*'+str(code).encode()+rb'\r\n([^\r\n]*)',blob)
    return match.group(1).decode('utf8','replace').strip() if match else None

found={}
with source.open('rb') as file:
    mm=mmap.mmap(file.fileno(),0,access=mmap.ACCESS_READ)
    marker=b'\r\n  0\r\nINSERT\r\n'
    boundary=b'\r\n  0\r\n'
    cursor=0
    while (start:=mm.find(marker,cursor))>=0:
        end=mm.find(boundary,start+len(marker))
        if end<0: break
        blob=mm[start:end]
        handle=value(blob,5)
        if handle and handle.upper() in wanted:
            found[handle.upper()]={'block':value(blob,2),
                                   'rotation':float(value(blob,50) or 0)}
        cursor=end
    mm.close()

matches=0
for row in views:
    entry=analysis['views'][row['id']]
    inserts=[found[h.upper()] for h in row.get('source_handles',[]) if h.upper() in found]
    entry['source_inserts']=inserts
    states=[]
    for insert in inserts:
        data=dynamic.get((insert.get('block') or '').casefold())
        if data:
            states.extend(s for s in data['states'] if s not in states)
    entry['dynamic_visibility_states']=states
    if states: matches+=1

analysis_path.write_text(json.dumps(analysis,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'source_inserts_found':len(found),'views_with_dynamic_state_names':matches,
                  'total_views':len(views)},ensure_ascii=False))
