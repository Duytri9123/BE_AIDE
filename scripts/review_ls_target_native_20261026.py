"""Inspect previously unconverted native LS source sheets for exact target models."""
import hashlib,json,subprocess,sys
from pathlib import Path
import ezdxf
from ezdxf.addons.drawing import matplotlib
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'data/CatalogTB/LS/NguonBenNgoai'

def main():
    for ident in sys.argv[1:] or ['RU-660d12651a0f0c18','RU-11452f570d63c3d7','50373']:
        folder=BASE/ident;dwg=folder/'source.dwg';dxf=folder/'source.dxf'
        assert dwg.read_bytes().startswith(b'AC10')
        if not dxf.exists():
            script=folder/'convert-review.scr'
            script.write_text('FILEDIA\n0\nSECURELOAD\n2\n_.DXFOUT\n'+dxf.as_posix()+'\n_Version\n2018\n16\n_.QUIT\n_Y\n',encoding='ascii')
            with (folder/'convert-review.log').open('wb') as log:
                subprocess.run(['C:/Program Files/Autodesk/AutoCAD 2022/accoreconsole.exe','/i',str(dwg),'/s',str(script),'/l','en-US'],stdout=log,stderr=log,timeout=150,creationflags=subprocess.CREATE_NO_WINDOW)
        assert dxf.is_file(),ident
        doc=ezdxf.readfile(dxf);audit=doc.audit()
        texts=[dict(type=e.dxftype(),position=list(e.dxf.insert),text=e.dxf.text if e.dxftype()=='TEXT' else e.plain_text()) for e in doc.modelspace() if e.dxftype() in ['TEXT','MTEXT']]
        report=dict(source_dwg_sha256=hashlib.sha256(dwg.read_bytes()).hexdigest(),source_dxf_sha256=hashlib.sha256(dxf.read_bytes()).hexdigest(),units=doc.units,audit_errors=len(audit.errors),texts=texts)
        (folder/'native-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
        matplotlib.qsave(doc.modelspace(),folder/'source-review.png',dpi=110)
        print(ident,'units',doc.units,'entities',len(doc.modelspace()),'labels',len(texts),flush=True)

if __name__=='__main__':main()
