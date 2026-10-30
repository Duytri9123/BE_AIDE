"""Read public LS America download metadata and preserve original source files."""
import json
import re
import sys
import urllib.request
import urllib.parse
import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = 'https://www.lselectricamerica.com'
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Referer': HOST + '/support/download-center'}


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60).read()


def acquire(entry):
    title, f = entry
    folder = ROOT / 'data/CatalogTB/LS/NguonBenNgoai' / ('AMERICA-' + str(f['fileId']))
    folder.mkdir(exist_ok=True)
    target = folder / ('source.pdf' if f['fileExt'].lower() == 'pdf' else 'source.step')
    resolver = HOST + '/api/v1/fo/ctpApi/fileDownUrl?' + urllib.parse.urlencode({'filePath': f['filePath']})
    if not target.exists():
        raw = fetch(resolver).decode('utf8').strip()
        response = raw if raw.startswith('https://') else json.loads(raw)
        if isinstance(response, str):
            url = response
        else:
            print('Resolver keys', f['fileId'], list(response), flush=True)
            url = response.get('url') or response.get('downloadUrl') or response.get('data')
            if isinstance(url, dict):
                url = url.get('url') or url.get('downloadUrl') or url.get('fileDownUrl')
        assert isinstance(url, str) and url.startswith('https://'), f['fileId']
        data = fetch(url)
        if target.suffix == '.pdf':
            assert data.startswith(b'%PDF')
        else:
            assert data.startswith(b'ISO-10303-21') and b'END-ISO-10303-21' in data[-500:]
        target.write_bytes(data)
    metadata = dict(f, content_title=title, source_url=resolver, resolver_url=resolver,
                    source_page=HOST + '/support/download-center', checked_at='2026-10-25',
                    sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    (folder / 'source.json').write_text(json.dumps(metadata, indent=2), encoding='utf8')
    print(f['fileId'], f['fileName'], target.stat().st_size, flush=True)


if __name__ == '__main__':
    selected = set(map(int, sys.argv[1:] or [22404, 23731, 33175, 33178]))
    entries = [(row['title'], f)
               for row in json.loads((ROOT / 'tmp/ls-america-api/Metasol.json').read_text(encoding='utf8'))['content']
               for version in row['versions'] for f in version['files'] if f['fileId'] in selected]
    assert len(entries) == len(selected)
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(acquire, entries))
