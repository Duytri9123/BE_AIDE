"""Download traceable LS reference drawings; never auto-approve SKU or face matches."""
import hashlib
import html
import json
import re
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/thu_vien_tu_dien_v2/nguon/ls_external'
PAGE = 'https://lselectric-ru.com/equipment/oborudovanie-nizkogo-napryazheniya/'
CORE = Path('C:/Program Files/Autodesk/AutoCAD 2022/accoreconsole.exe')

def run():
    OUT.mkdir(parents=True, exist_ok=True)
    text = urllib.request.urlopen(PAGE, timeout=40).read().decode()
    (OUT/'source_page.html').write_text(text, encoding='utf8')
    matches = re.findall(r'files-list__item-name">([^<]+)</div>\s*<div class="files-list__item-link"><a[^>]+href="([^"]+)"', text)
    rows = []
    for name, link in matches:
        name = html.unescape(name)
        if not name.lower().endswith('.dwg') or not any(s in name for s in ('Metasol+MCCB', 'AB_bX', 'MC-185a', 'MT-12', 'MT_32_95', 'MT_150_800', '1_D_AN_AS_AH-06-16D-F', '2_D_AN_AS_AH-06-16D-D')):
            continue
        url = 'https://lselectric-ru.com' + link
        sid = Path(link).stem
        folder = OUT/sid
        folder.mkdir(exist_ok=True)
        dwg = folder/'source.dwg'
        if not dwg.exists():
            payload = urllib.request.urlopen(url, timeout=60).read(50*1024*1024+1)
            if len(payload)>50*1024*1024 or not payload.startswith(b'AC10'):
                raise ValueError('Invalid or oversized DWG: '+name)
            dwg.write_bytes(payload)
        row = dict(id=sid, name=name, source_url=url, source_page=PAGE,
                   source_type='external_reference_not_independently_authenticated',
                   sha256=hashlib.sha256(dwg.read_bytes()).hexdigest(), bytes=dwg.stat().st_size,
                   dwg=dwg.relative_to(OUT.parent.parent).as_posix(),
                   status='pending_model_and_face_review', approved_for_layout=False)
        dxf = folder/'source.dxf'
        if CORE.exists() and not dxf.exists():
            script=folder/'export.scr'
            script.write_text('FILEDIA\n0\n_.DXFOUT\n'+dxf.as_posix()+'\n_Version\n2018\n16\n_.QUIT\n_Y\n',encoding='ascii')
            with (folder/'conversion.log').open('wb') as log:
                try:
                    p=subprocess.run([str(CORE),'/i',str(dwg),'/s',str(script),'/l','en-US'],stdout=log,stderr=log,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
                    row['conversion_exit_code']=p.returncode
                except subprocess.TimeoutExpired:
                    row['conversion_error']='timeout'
        if dxf.exists():
            row['dxf']=dxf.relative_to(OUT.parent.parent).as_posix()
        rows.append(row)
        (OUT/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
        print(name, 'DXF' if dxf.exists() else 'DWG', flush=True)
    return rows

if __name__=='__main__': run()
