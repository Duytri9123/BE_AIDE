"""Retain manufacturer catalog pages used for MT/GMP configuration checks."""
import hashlib
import json
import urllib.request
import subprocess
from pathlib import Path
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/ls-all-cad-2026-10-24/research-2026-10-25'
SOURCES = {
    'metasol': 'https://www.ls-electric.com/upload/customer/download/280b6197-f4bb-4f86-a60d-917b7b8bf890/Metasol_MC_E_170915.pdf',
    'gmp': 'https://www.ls-electric.com/upload/customer/download/1556/G_EMPR-DMPR.pdf',
}

if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    reports = []
    for name, url in SOURCES.items():
        target = OUT / (name + '.pdf')
        if not target.exists():
            try:
                data = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'}), timeout=60).read()
            except OSError:
                subprocess.run(['curl.exe','-sS','-f','-L','--max-time','60','-o',str(target),url],check=True)
                data=target.read_bytes()
            assert data.startswith(b'%PDF')
            target.write_bytes(data)
        doc = pymupdf.open(target)
        pages = []
        for i, page in enumerate(doc):
            text = page.get_text()
            relevant = (name == 'metasol' and i in [94,170,171]) or (name == 'gmp' and i in [9, 10, 32])
            if relevant:
                (OUT / f'{name}-{i+1}.txt').write_text(text, encoding='utf8')
                page.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5)).save(OUT / f'{name}-{i+1}.png')
                pages.append(i+1)
        reports.append(dict(file=target.name, source_url=url, sha256=hashlib.sha256(target.read_bytes()).hexdigest(), reviewed_pdf_pages=pages))
        print(name, len(doc), pages, flush=True)
    (OUT / 'catalog-sources.json').write_text(json.dumps(reports, indent=2), encoding='utf8')
