"""Extract labelled drawing-table cells, including loose and anonymous geometry.

Keep the entire source cell: adjacent symbols can be different views of one
device, so splitting them without model evidence would invent duplicates.
"""
import hashlib
import json
from pathlib import Path

import ezdxf
from ezdxf import bbox
from ezdxf.addons import Importer
from ezdxf.addons.drawing import Frontend, RenderContext, svg, layout

ROOT = Path(__file__).resolve().parents[1]


def extract():
    output = ROOT / 'data/device_layouts/source_cells'
    output.mkdir(parents=True, exist_ok=True)
    items, seen = [], {}
    component_output = ROOT / 'data/device_layouts/source_components'
    component_output.mkdir(parents=True, exist_ok=True)
    components, component_seen = [], {}
    for stem, source in [('combined', 'TỔNG HỢP 1.dwg'), ('combined_backup', 'TỔNG HỢP 1.bak')]:
        doc = ezdxf.readfile(ROOT / f'tmp/multibrand/{stem}.dxf')
        space = doc.modelspace()
        cache = bbox.Cache()
        cells, texts, entities = [], [], []
        for entity in space:
            box = bbox.extents([entity], cache=cache, fast=True)
            if not box.has_data:
                continue
            entities.append((entity, box))
            if entity.dxftype() in ('TEXT', 'MTEXT'):
                text = entity.dxf.text if entity.dxftype() == 'TEXT' else entity.plain_text()
                texts.append((entity.dxf.insert.x, entity.dxf.insert.y, ' '.join(text.split())))
            if entity.dxftype() == 'LWPOLYLINE' and entity.closed and 500 < box.size.y < 540 and 550 < box.size.x < 2300:
                cells.append((entity, box))
        for border, cell in cells:
            # Label column immediately to the left, at the same vertical position.
            labels = [t for x, y, t in texts if cell.extmin.x - 650 < x < cell.extmin.x - 5 and cell.extmin.y < y < cell.extmax.y]
            if not labels:
                continue
            selected = [e for e, b in entities if e is not border
                        and b.extmin.x >= cell.extmin.x - .1 and b.extmax.x <= cell.extmax.x + .1
                        and b.extmin.y >= cell.extmin.y - .1 and b.extmax.y <= cell.extmax.y + .1]
            if not any(e.dxftype() not in ('TEXT', 'MTEXT') for e in selected):
                continue
            target = ezdxf.new('R2018')
            target.units = doc.units
            importer = Importer(doc, target)
            importer.import_entities(selected)
            importer.finalize()
            for entity in target.modelspace():
                entity.translate(-cell.extmin.x, -cell.extmin.y, 0)
            backend = svg.SVGBackend()
            Frontend(RenderContext(target), backend).draw_layout(target.modelspace(), finalize=True)
            drawing = backend.get_string(layout.Page(0, 0, layout.Units.mm))
            digest = hashlib.sha256(drawing.encode()).hexdigest()
            if digest in seen:
                seen[digest]['source_files'].append(source)
                continue
            asset_id = hashlib.sha256(('cell:' + stem + ':' + border.dxf.handle).encode()).hexdigest()[:20]
            name = ' / '.join(dict.fromkeys(labels))
            target.saveas(output / f'{asset_id}.dxf')
            item = dict(id=asset_id, name=name, category=name, brand='Chưa xác định hãng',
                        filename=f'{asset_id}.dxf', source_block=f'Ô {border.dxf.handle}',
                        source_file=source, source_files=[source], units='mm' if doc.units == 4 else 'đơn vị nguồn',
                        geometry_sha256=digest, view='Các hình trong ô nguồn', model_verified=False)
            items.append(item)
            seen[digest] = item
            # Every placed block is also independently reusable, including *U
            # anonymous blocks that the name-based index cannot discover.
            for entity in selected:
                if entity.dxftype() != 'INSERT':
                    continue
                part = ezdxf.new('R2018')
                part.units = doc.units
                part_importer = Importer(doc, part)
                part_importer.import_entities([entity])
                part_importer.finalize()
                bounds = bbox.extents(part.modelspace())
                if not bounds.has_data or bounds.size.x <= 0 or bounds.size.y <= 0:
                    continue
                for copied in part.modelspace():
                    copied.translate(-bounds.extmin.x, -bounds.extmin.y, -bounds.extmin.z)
                renderer = svg.SVGBackend()
                Frontend(RenderContext(part), renderer).draw_layout(part.modelspace(), finalize=True)
                drawing = renderer.get_string(layout.Page(0, 0, layout.Units.mm))
                fingerprint = hashlib.sha256(drawing.encode()).hexdigest()
                if fingerprint in component_seen:
                    existing = component_seen[fingerprint]
                    if source not in existing['source_files']: existing['source_files'].append(source)
                    continue
                part_id = hashlib.sha256(('part:' + stem + ':' + entity.dxf.handle).encode()).hexdigest()[:20]
                block = entity.dxf.name
                title = f'{name} · {block}' if not block.startswith(('*', 'A$')) else f'{name} · mẫu {len(components) + 1}'
                part.saveas(component_output / f'{part_id}.dxf')
                component = dict(id=part_id, name=title, category=name, brand='Chưa xác định hãng',
                                 filename=f'{part_id}.dxf', source_block=block, source_file=source,
                                 source_files=[source], units=item['units'], source_units=int(doc.units),
                                 width=round(bounds.size.x, 3), height=round(bounds.size.y, 3),
                                 geometry_sha256=fingerprint, view='Hình có trong nguồn',
                                 parent_asset_id=asset_id, model_verified=False)
                components.append(component)
                component_seen[fingerprint] = component
    (output / 'manifest.json').write_text(json.dumps(dict(items=items), ensure_ascii=False, indent=2), encoding='utf8')
    (component_output / 'manifest.json').write_text(json.dumps(dict(items=components), ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'cells': len(items), 'categories': [i['name'] for i in items]}, ensure_ascii=True))


if __name__ == '__main__':
    extract()
