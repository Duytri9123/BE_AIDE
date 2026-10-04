"""Bundle CAD previews/DXFs referenced by the active 2026 equipment catalog."""
import json
import sqlite3
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'Tudien' / 'CATALOG_PHU_KIEN_DOC_LAP'
DATA = ROOT / 'BE_AIDE' / 'data' / 'equipment_library_2026'

with sqlite3.connect(DATA / 'equipment_catalog.sqlite') as db:
    records = [json.loads(row[0]) for row in db.execute('SELECT record_json FROM equipment')]
paths = sorted({ref['path'] for record in records
                for ref in (record['cad'].get('preview'), record['cad'].get('dxf')) if ref})
archive = DATA / 'source_cad_assets.zip'
with ZipFile(archive, 'w', compression=ZIP_DEFLATED, compresslevel=8) as output:
    for relative in paths:
        path = (SOURCE / relative).resolve()
        if not path.is_relative_to(SOURCE.resolve()) or not path.is_file():
            raise FileNotFoundError(relative)
        output.write(path, relative)
print(f'{len(paths)} CAD files copied to {archive} ({archive.stat().st_size:,} bytes)')
