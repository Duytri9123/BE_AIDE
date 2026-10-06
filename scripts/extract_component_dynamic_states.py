"""Read AutoCAD dynamic visibility names from the full converted source DXF.

The lookup follows visibility parameter -> evaluation graph -> extension
dictionary -> BLOCK_RECORD. It does not generate geometry for unseen states.
"""
import json
import mmap
import re
from pathlib import Path

base=Path(__file__).resolve().parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
source=base.parent/'bao_cao_thu_vien_phu_kien/thu_vien_phu_kien.dxf'
path=base/'THIET_BI_KHAC_2026/dynamic_visibility_states.json'

def value(blob,code):
    found=re.search(rb'(?:\A|\r\n)\s*'+str(code).encode()+rb'\r\n([^\r\n]*)',blob)
    return found.group(1).decode('utf8','replace').strip() if found else None

with source.open('rb') as file:
    mm=mmap.mmap(file.fileno(),0,access=mmap.ACCESS_READ)
    marker=b'\r\n  0\r\nBLOCKVISIBILITYPARAMETER\r\n'
    boundary=b'\r\n  0\r\n'
    blocks={}
    cursor=0
    while (start:=mm.find(marker,cursor))>=0:
        end=mm.find(boundary,start+len(marker))
        if end<0: break
        blob=mm[start:end]
        handle=value(blob,5)
        graph=value(blob,330)
        names=[x.decode('utf8','replace').strip() for x in re.findall(rb'(?:\A|\r\n)303\r\n([^\r\n]*)',blob)]
        if graph and names:
            def object_by_handle(key):
                needle=b'\r\n  5\r\n'+key.encode()+b'\r\n'
                pos=mm.find(needle)
                if pos<0: return b''
                begin=mm.rfind(boundary,0,pos)
                finish=mm.find(boundary,pos+len(needle))
                return mm[begin:finish if finish>=0 else len(mm)]
            graph_blob=object_by_handle(graph)
            dictionary=value(graph_blob,330)
            dict_blob=object_by_handle(dictionary) if dictionary else b''
            block_record=value(dict_blob,330)
            record_blob=object_by_handle(block_record) if block_record else b''
            block_name=value(record_blob,2)
            if block_name:
                key=block_name.casefold()
                entry=blocks.setdefault(key,{'block_name':block_name,'states':[],'parameters':[]})
                entry['states'].extend(x for x in names if x and x not in entry['states'])
                entry['parameters'].append({'handle':handle,'name':value(blob,300)})
        cursor=end
    mm.close()

path.write_text(json.dumps({'source_dxf':str(source),'blocks':blocks},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'dynamic_blocks':len(blocks),'states':sum(len(x['states']) for x in blocks.values()),
                  'sample':list(blocks.values())[:3]},ensure_ascii=False))
