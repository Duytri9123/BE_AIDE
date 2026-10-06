"""Reproducible, source-preserving import of production cabinet drawings."""
import hashlib, json, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'Tudien'
OUT = ROOT / 'data/tudien'
WORK = ROOT / 'tmp/tudien'
CORE = Path('C:/Program Files/Autodesk/AutoCAD 2022/accoreconsole.exe')

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

def convert():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    rows=[]
    for source in sorted(SOURCE.rglob('*')):
        if not source.is_file(): continue
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        sid=digest[:16]
        folder=WORK/sid
        folder.mkdir(parents=True, exist_ok=True)
        row=dict(id=sid, source_file=str(source.relative_to(SOURCE)), sha256=digest, bytes=source.stat().st_size)
        rows.append(row)
        dxf=OUT/'nguon'/sid/'drawing.dxf'
        dxf.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix.lower()=='.dwg':
            if not dxf.exists():
                local=folder/'input.dwg'
                shutil.copy2(source,local)
                script=folder/'export.scr'
                script.write_text('FILEDIA\n0\n_.DXFOUT\n'+dxf.as_posix()+'\n_Version\n2018\n16\n_.QUIT\n_Y\n',encoding='ascii')
                with (folder/'conversion.log').open('wb') as log:
                    try:
                        p=subprocess.run([str(CORE),'/i',str(local),'/s',str(script),'/l','en-US'],stdout=log,stderr=log,timeout=240)
                        row['converter_exit_code']=p.returncode
                    except Exception as exc: row['error']=str(exc)
            row['converted']=dxf.exists() and dxf.stat().st_size>0
            row['dxf']=str(dxf.relative_to(OUT)).replace('\\','/')
        else: row['conversion_status']='Not a DWG; handled by build_tudien_library.py'
        write(OUT/'nguon/manifest.json',rows)
        print(len(rows),source.name,row.get('converted'),flush=True)
    return rows

if __name__=='__main__':
    convert()
