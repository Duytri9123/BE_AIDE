"""Render title-free D02 CAD, including copper terminals stored as ACIS REGIONs.

The source DXF is never changed. The added 2D outlines are preview-only copies of
rectangular regions and their circular holes read from the REGION SAT geometry.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext, config, layout, svg

ROOT = Path(__file__).resolve().parents[2]
CAT = ROOT / 'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
BASE = CAT / 'LS_D02_DU_LIEU_MOI'
records = json.loads((BASE / 'devices.json').read_text(encoding='utf8'))
OUT = BASE / 'cad_preview'
OUT.mkdir(exist_ok=True)
point_re = re.compile(r'^point \$-1 -1 \$-1 ([\d.eE+-]+) ([\d.eE+-]+) ([\d.eE+-]+)')
results = []

def sat_outlines(sat):
    records = sat[3:]
    segments = []
    for line in records:
        tokens = line.split()
        if not tokens or tokens[0] != 'edge' or len(tokens) < 10:
            continue
        try:
            curve = records[int(tokens[9][1:])].split()
            if curve[0] != 'straight-curve':
                continue
            x, y = float(curve[4]), float(curve[5])
            dx, dy = float(curve[7]), float(curve[8])
            t0, t1 = float(tokens[5]), float(tokens[7])
            segments.append(((x+dx*t0, y+dy*t0), (x+dx*t1, y+dy*t1)))
        except (ValueError, IndexError):
            return []
    if not segments:
        return []
    outlines = []
    # A REGION may contain more than one independent straight-edge loop.
    while segments:
        first = segments.pop(0)
        ordered = [first[0], first[1]]
        current = first[1]
        while math.dist(current, ordered[0]) >= 1e-4:
            found = None
            for index, (a, b) in enumerate(segments):
                if math.dist(current, a) < 1e-4:
                    found = (index, b)
                    break
                if math.dist(current, b) < 1e-4:
                    found = (index, a)
                    break
            if found is None:
                return []
            index, point = found
            ordered.append(point)
            current = point
            segments.pop(index)
        outlines.append(ordered[:-1])
    return outlines

for record in records:
    source = CAT / record['cad_dxf']
    doc = ezdxf.readfile(source)
    copper = []
    for block in doc.blocks:
        for region in list(block.query('REGION')):
            sat = region.sat
            # Trace the SAT edges and ellipse curves themselves. Unknown ACIS
            # topology is skipped; never substitute a bounding rectangle.
            topology = (sum(line.startswith('straight-curve ') for line in sat),
                        sum(line.startswith('ellipse-curve ') for line in sat),
                        sum(line.startswith('point ') for line in sat))
            if topology not in ((6, 1, 7), (4, 2, 6), (8, 6, 14), (0, 2, 2)):
                continue
            circles = []
            for line in sat:
                fields = line.split()
                if fields and fields[0] == 'ellipse-curve' and len(fields) > 10:
                    circles.append((float(fields[4]), float(fields[5]), abs(float(fields[10]))))
            if len(circles) != topology[1]:
                continue
            outlines = sat_outlines(sat)
            if topology[0] and sum(len(shape) for shape in outlines) != topology[0]:
                continue
            corners = [point for shape in outlines for point in shape]
            if outlines:
                xs = [round(min(x for x, _ in corners), 6), round(max(x for x, _ in corners), 6)]
                ys = [round(min(y for _, y in corners), 6), round(max(y for _, y in corners), 6)]
                for shape in outlines:
                    block.add_lwpolyline(shape, close=True,
                                         dxfattribs={'color': region.dxf.color, 'layer': region.dxf.layer})
            else:
                xs = [round(min(x-r for x, _, r in circles), 6), round(max(x+r for x, _, r in circles), 6)]
                ys = [round(min(y-r for _, y, r in circles), 6), round(max(y+r for _, y, r in circles), 6)]
            for x, y, radius in circles:
                block.add_circle((x, y), radius, dxfattribs={'color': region.dxf.color,
                                                              'layer': region.dxf.layer})
            copper.append({'source_region_handle': region.dxf.handle, 'sat_topology': topology,
                           'outlines_local_mm': [[[round(x, 6), round(y, 6)] for x, y in shape] for shape in outlines],
                           'rectangle_local_mm': [xs[0], ys[0], xs[1], ys[1]],
                           'holes_local_mm': circles})
    backend = svg.SVGBackend()
    cfg = config.Configuration(background_policy=config.BackgroundPolicy.CUSTOM,
                               custom_bg_color='#202830')
    Frontend(RenderContext(doc), backend, config=cfg).draw_layout(doc.modelspace(), finalize=True)
    target = OUT / f"{record['id']}.svg"
    target.write_text(backend.get_string(layout.Page(240, 240, layout.Units.mm,
                                                     margins=layout.Margins.all(4))), encoding='utf8')
    record['preview_svg'] = target.relative_to(CAT).as_posix()
    record['copper_terminals_from_region'] = copper
    # Physical copper port coordinates are promoted only for the large
    # two-hole bars, not for the smaller chamfered terminal details.
    contact_bars = [r for r in copper if r['sat_topology'] == (4, 2, 6)]
    record.pop('physical_copper_ports', None)
    if len(contact_bars) >= 4 and len(contact_bars) % 2 == 0:
        centers = sorted((r['rectangle_local_mm'][1] + r['rectangle_local_mm'][3]) / 2 for r in contact_bars)
        split = (centers[len(centers)//2 - 1] + centers[len(centers)//2]) / 2
        upper = sorted((r for r in contact_bars if (r['rectangle_local_mm'][1] + r['rectangle_local_mm'][3])/2 > split),
                       key=lambda r: r['rectangle_local_mm'][0])
        lower = sorted((r for r in contact_bars if (r['rectangle_local_mm'][1] + r['rectangle_local_mm'][3])/2 <= split),
                       key=lambda r: r['rectangle_local_mm'][0])
        if len(upper) == len(lower):
            record['physical_copper_ports'] = [
                {'side': side, 'position_left_to_right': index, 'phase': None,
                 'region_handle': region['source_region_handle'],
                 'rectangle_local_mm': region['rectangle_local_mm'],
                 'holes_local_mm': region['holes_local_mm']}
                for side, group in (('upper', upper), ('lower', lower))
                for index, region in enumerate(group, 1)]
    results.append({'id': record['id'], 'region_count': len(copper), 'preview': record['preview_svg']})

(BASE / 'devices.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
(BASE / 'cad_visual_audit.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps({'rendered': len(results), 'regions': sum(x['region_count'] for x in results)}))
