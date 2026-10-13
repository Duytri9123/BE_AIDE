"""Recover stretch bands from original dimension extension points, scoped per sheet."""
import json
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
import ezdxf
from ezdxf import bbox
from app.services.cad.cabinet_templates import inventory, source_path, stretch_axes, LIBRARY

groups = defaultdict(list)
for item in inventory():
    groups[item['original_dxf']].append(item)
profiles = {}
for filename, items in groups.items():
    path = Path(__file__).resolve().parents[2] / filename
    if not path.is_file():
        continue
    original = ezdxf.readfile(path)
    dimensions = list(original.modelspace().query('DIMENSION'))
    for item in items:
        if not item.get('dimensions'): continue
        clean = ezdxf.readfile(source_path(item))
        ext = bbox.extents(clean.modelspace(), fast=True)
        chosen = []
        for entity in dimensions:
            p, q = entity.dxf.get('defpoint2'), entity.dxf.get('defpoint3')
            if p is not None and q is not None and all(
                ext.extmin.x-1 <= v.x <= ext.extmax.x+1 and ext.extmin.y-1 <= v.y <= ext.extmax.y+1 for v in (p,q)):
                chosen.append(entity)
        try:
            proxy = SimpleNamespace(modelspace=lambda: SimpleNamespace(query=lambda _: chosen))
            axes = stretch_axes(proxy, item['dimensions'])
            supported = sorted({b['dimension'] for bands in axes for b in bands})
            if supported:
                profiles[item['id']] = dict(axes=axes, supported=supported,
                    nominal=item['dimensions'], source_file=item['original_dxf'],
                    basis='original_dimension_extension_points_within_selected_sheet',
                    min_ratio=.75, max_ratio=1.25)
        except ValueError:
            pass
    print('Indexed', len(items), 'sheets; supported', len(profiles), flush=True)
    del original
(LIBRARY/'resize_profiles.json').write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding='utf-8')
print('Saved', len(profiles), 'profiles', flush=True)
