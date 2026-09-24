"""Index whole FOMTU sheets, including title attributes and every contained view.

Run from BE_AIDE: python scripts/extract_cabinet_templates.py
The original DWG/DXF is never modified. Unclassified sheets stay in the inventory.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

import ezdxf
from ezdxf import bbox
from ezdxf.addons import Importer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.cad.cabinet_templates import stretch_axes
OUTPUT = ROOT / 'data/cabinet_templates/formtu'


def plain(value):
    return ''.join(c for c in unicodedata.normalize('NFD', value.lower().replace('đ', 'd'))
                   if not unicodedata.combining(c))


def extract():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    doc = ezdxf.readfile(ROOT / 'tmp/formtu/formtu.dxf')
    print('Source loaded', flush=True)
    titles = [e for e in doc.modelspace() if e.dxftype() == 'INSERT' and 'khung' in plain(e.dxf.name)]
    sheets = []
    for title in titles:
        box = bbox.extents(title.virtual_entities(), fast=True)
        if not box.has_data:
            continue
        attrs = {a.dxf.tag: a.dxf.text for a in title.attribs}
        dims = next((re.search(r'(\d{3,4})\s*[xX×*]\s*(\d{3,4})\s*[xX×*]\s*(\d{3,4})', v)
                     for v in attrs.values() if re.search(r'\d{3,4}\s*[xX×*]\s*\d{3,4}\s*[xX×*]\s*\d{3,4}', v)), None)
        description = ' '.join(attrs.values())
        key = plain(description)
        kind = 'outdoor' if 'ngoai troi' in key or 'treo cot' in key else 'indoor' if 'trong nha' in key else 'fire' if 'chua chay' in key or 'cuu hoa' in key else 'unknown'
        item = dict(id='formtu-' + title.dxf.handle.lower(), source_handle=title.dxf.handle,
                    source_file='FOMTU.dwg', source_block=title.dxf.name, kind=kind,
                    kind_basis='title_attributes' if kind != 'unknown' else 'unclassified',
                    dimensions=dict(zip(('height', 'width', 'depth'), map(int, dims.groups()))) if dims else None,
                    attributes=attrs, description=description,
                    bounds=[box.extmin.x, box.extmin.y, box.extmax.x, box.extmax.y],
                    filename='formtu-' + title.dxf.handle.lower() + '.dxf')
        sheets.append((item, title, []))
    # A bounding box is evaluated once per model entity, not once per sheet.
    cache = bbox.Cache()
    failures = []
    for index, entity in enumerate(doc.modelspace()):
        try:
            box = bbox.extents([entity], fast=True, cache=cache)
            if not box.has_data:
                continue
            for item, title, entities in sheets:
                x0, y0, x1, y1 = item['bounds']
                if entity is title or (box.extmin.x >= x0 - .5 and box.extmax.x <= x1 + .5
                                      and box.extmin.y >= y0 - .5 and box.extmax.y <= y1 + .5):
                    entities.append(entity)
        except Exception as exc:
            failures.append({'handle': entity.dxf.handle, 'error': str(exc)})
        if index % 10000 == 0:
            print('Indexed entities', index, flush=True)
    inventory = []
    for item, title, entities in sheets:
        if title not in entities:
            entities.append(title)
        target = ezdxf.new('R2018')
        target.units = 4
        importer = Importer(doc, target)
        importer.import_entities(entities)
        importer.finalize()
        # Importer keeps copied dimension graphics as virtual content. Bind them
        # explicitly before saving; otherwise DIMENSION loses its display block.
        for dimension in list(target.entitydb.values()):
            if dimension.dxftype() == 'DIMENSION' and dimension.virtual_block_content:
                dimension.post_bind_hook()
        x0, y0, _, _ = item['bounds']
        for entity in target.modelspace():
            entity.translate(-x0, -y0, 0)
        target.saveas(OUTPUT / item['filename'])
        item['entity_count'] = len(entities)
        item['exported_entity_count'] = len(target.modelspace())
        item['stretch_dimensions'] = []
        if item['dimensions']:
            try:
                item['stretch_axes'] = stretch_axes(target, item['dimensions'])
                item['stretch_dimensions'] = sorted({b['dimension'] for bands in item['stretch_axes'] for b in bands})
                item['resize_note'] = ''
            except ValueError as exc:
                item['resize_note'] = str(exc)
        item['labels'] = [e.dxf.text if e.dxftype() == 'TEXT' else e.plain_text()
                          for e in entities if e.dxftype() in ('TEXT', 'MTEXT')]
        item['status'] = 'source' if item['dimensions'] and len(entities) > 10 else 'needs_review'
        if item['exported_entity_count'] != item['entity_count']:
            item['status'] = 'needs_review'
            item['resize_note'] = 'Cần kiểm tra đối tượng nguồn không được xuất đủ.'
            item['stretch_dimensions'] = []
        inventory.append(item)
        print(item['id'], len(entities), flush=True)
    (OUTPUT / 'manifest.json').write_text(json.dumps(dict(source_file='FOMTU.dwg', items=inventory,
                                                         extraction_errors=failures), ensure_ascii=False, indent=2), encoding='utf8')
    print('Exported', len(inventory), 'sheets; errors', len(failures), flush=True)


if __name__ == '__main__':
    extract()
