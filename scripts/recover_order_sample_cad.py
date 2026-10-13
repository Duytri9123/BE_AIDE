"""Export supplied project DWGs on scratch copies; never modify originals."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs' / 'sample-cad-recovery'
SOURCE = ROOT / 'outputs/order-447-457-audit/source-manifest.json'


def recover():
    OUT.mkdir(parents=True, exist_ok=True)
    sources = json.loads(SOURCE.read_text(encoding='utf8'))
    result = []
    for order, files in sources.items():
        source = Path(files['dwg']['path'])
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != files['dwg']['sha256']:
            raise ValueError(f'Order {order}: source changed; existing handle evidence must be refreshed')
        work = OUT / order
        work.mkdir(exist_ok=True)
        scratch, target = work / 'input.dwg', work / 'source.dxf'
        if not target.exists():
            shutil.copy2(source, scratch)
            script = work / 'export.scr'
            script.write_text('FILEDIA\n0\n_.DXFOUT\n' + target.as_posix()
                              + '\n_Version\n2018\n16\n_.QUIT\n_Y\n', encoding='ascii')
            with (work / 'conversion.log').open('wb') as log:
                subprocess.run(['C:/Program Files/Autodesk/AutoCAD 2022/accoreconsole.exe',
                                '/i', str(scratch), '/s', str(script), '/l', 'en-US'],
                               stdout=log, stderr=log, timeout=180,
                               creationflags=subprocess.CREATE_NO_WINDOW, check=True)
        if not target.exists():
            raise ValueError(f'Order {order}: native DXF export failed')
        result.append({'order': order, 'source': str(source), 'source_sha256': digest,
                       'source_unchanged': hashlib.sha256(source.read_bytes()).hexdigest() == digest,
                       'export': str(target), 'dxf_sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
        print(f'Order {order}: native source exported, original unchanged', flush=True)
    (OUT / 'source-integrity.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')


if __name__ == '__main__':
    recover()
