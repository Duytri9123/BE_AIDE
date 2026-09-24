"""Recover original DIM graphics in sheets exported before explicit post_bind_hook."""
import json
from pathlib import Path
import ezdxf
from ezdxf.addons import Importer
from ezdxf.disassemble import recursive_decompose

ROOT = Path(__file__).resolve().parents[1]


def repair():
    source = ezdxf.readfile(ROOT / 'tmp/formtu/formtu.dxf')
    index = {}
    for entity in source.entitydb.values():
        if entity.dxftype() == 'DIMENSION':
            p = entity.dxf.defpoint
            index.setdefault((round(p.x, 2), round(p.y, 2), entity.dxf.dimtype), []).append(entity)
    directory = ROOT / 'data/cabinet_templates/formtu'
    items = json.loads((directory / 'manifest.json').read_text(encoding='utf8'))['items']
    missing = []
    for item in items:
        doc = ezdxf.readfile(directory / item['filename'])
        importer = Importer(source, doc)
        count = 0
        for dimension in list(doc.entitydb.values()):
            if dimension.dxftype() != 'DIMENSION' or dimension.dxf.get('geometry'):
                continue
            p = dimension.dxf.defpoint
            original = None
            for dx, dy in ((item['bounds'][0], item['bounds'][1]), (0, 0)):
                matches = index.get((round(p.x+dx, 2), round(p.y+dy, 2), dimension.dxf.dimtype), [])
                if matches:
                    original = matches[0]
                    break
            if original is None:
                missing.append([item['id'], dimension.dxf.handle])
                continue
            block = doc.blocks.new_anonymous_block(type_char='D')
            importer.import_entities(list(recursive_decompose([original])), target_layout=block)
            for entity in block:
                entity.translate(-dx, -dy, 0)
            dimension.dxf.geometry = block.name
            count += 1
        importer.finalize()
        doc.saveas(directory / item['filename'])
        print(item['id'], count, flush=True)
    (directory / 'dimension_repair_report.json').write_text(json.dumps({'unresolved': missing}), encoding='utf8')
    print('Unresolved', len(missing), flush=True)


if __name__ == '__main__':
    repair()
