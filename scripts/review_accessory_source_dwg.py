"""Read the supplied DWG through AutoCAD Core Console on a private scratch copy."""
import hashlib,json,shutil,subprocess
from pathlib import Path
import ezdxf
from collections import Counter
base=Path(__file__).resolve().parents[1]
source=base/'data/CatalogTB/THƯ VIỆN PHỤ KIỆN( Mới nhất).dwg'
work=base/'tmp/accessory_source_review';work.mkdir(parents=True,exist_ok=True)
digest=hashlib.sha256(source.read_bytes()).hexdigest()
local=work/'input.dwg';dxf=work/'source.dxf'
if not dxf.exists() or not (work/'sha256.txt').exists() or (work/'sha256.txt').read_text()!=digest:
    shutil.copy2(source,local)
    script=work/'export.scr'
    script.write_text('FILEDIA\n0\n_.DXFOUT\n'+dxf.as_posix()+'\n_Version\n2018\n16\n_.QUIT\n_Y\n',encoding='ascii')
    with (work/'conversion.log').open('wb') as log:
        result=subprocess.run(['C:/Program Files/Autodesk/AutoCAD 2022/accoreconsole.exe','/i',str(local),'/s',str(script),'/l','en-US'],stdout=log,stderr=log,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
    if not dxf.exists():raise RuntimeError('Source DXF export failed; see conversion.log')
    (work/'sha256.txt').write_text(digest)
print('DWG exported; inspecting original geometry',flush=True)
doc=ezdxf.readfile(dxf)
colors=Counter();labels=[]
for block in doc.blocks:
    for e in block:
        colors[e.dxf.get('color',256)]+=1
        if e.dxftype() in ('TEXT','MTEXT'):
            text=e.dxf.text if e.dxftype()=='TEXT' else e.plain_text()
            if any(s in text.upper() for s in (' AF','AF+','METASOL','MITSUBISHI','SCHNEIDER')):
                labels.append({'block':block.name,'handle':e.dxf.handle,'text':text[:160]})
report={'source':source.name,'sha256':digest,'source_unchanged':hashlib.sha256(source.read_bytes()).hexdigest()==digest,'blocks':len(doc.blocks),'model_entities':len(doc.modelspace()),'entity_colors':dict(colors),'frame_labels':labels,'policy':'Giữ đồng và đầu nối có trong bản gốc của nhà cung cấp. Không dùng bộ lọc xóa đồng của form tủ cho thiết bị.'}
(base/'data/CatalogTB/kiem_tra_file_phu_kien_goc.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('entity_colors','frame_labels')},ensure_ascii=False),flush=True)
