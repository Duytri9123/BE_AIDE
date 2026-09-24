"""Whole source sheets and dimension-driven stretch (never synthetic cabinet faces)."""
import io
import json
import math
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import ezdxf
from ezdxf import bbox
from ezdxf.addons import Importer
from ezdxf.disassemble import recursive_decompose
from ezdxf.math import Vec3
from ezdxf.explode import attrib_to_text
from ezdxf.upright import upright

LIBRARY = Path(__file__).resolve().parents[3] / 'data/cabinet_templates/formtu'


def inventory():
    path = LIBRARY / 'manifest.json'
    if not path.exists():
        raise ValueError('Thư viện form FOMTU đang được lập chỉ mục.')
    return json.loads(path.read_text(encoding='utf8'))['items']


def resolve(template_id):
    item = next((i for i in inventory() if i['id'] == template_id), None)
    if not item:
        raise ValueError('Không tìm thấy form tủ nguồn.')
    return item


def source_path(item):
    path = (LIBRARY / item['filename']).resolve()
    if path.parent != LIBRARY.resolve() or not path.is_file():
        raise ValueError('Không tìm thấy DXF của form tủ.')
    return path


def candidates(dimensions, kind='', items=None):
    """Never silently cross indoor/outdoor/fire types to find a closer size."""
    rows = []
    for item in inventory() if items is None else items:
        if kind and item['kind'] != kind:
            continue
        nominal = item.get('dimensions')
        distance = sum(abs(math.log(dimensions[k] / nominal[k])) for k in dimensions) if nominal else None
        changed = [k for k in dimensions if nominal and abs(dimensions[k]-nominal[k]) > .01]
        can_generate = bool(nominal and item.get('status') == 'source' and (not changed or (
            all(k in item.get('stretch_dimensions', []) for k in changed)
            and all(.75 <= dimensions[k]/nominal[k] <= 1.25 for k in dimensions))))
        rows.append({**item, 'distance': distance, 'can_generate': can_generate,
                     'exact': bool(nominal and all(abs(dimensions[k] - nominal[k]) < .01 for k in dimensions))})
    return sorted(rows, key=lambda i: (i['distance'] is None, i['distance'] or 0, i['id']))


def stretch_axes(doc, dimensions):
    """Use actual extension points, not the title text's approximate location.

    Coincident dimensions across views describe the same sheet-wide stretch band.
    Ambiguous overlapping bands are not automatically resized.
    """
    axes = [[], []]
    for entity in doc.modelspace().query('DIMENSION'):
        p, q = entity.dxf.get('defpoint2'), entity.dxf.get('defpoint3')
        if p is None or q is None or entity.dimtype not in (0, 1):
            continue
        for axis in (0, 1):
            if abs(p[1-axis] - q[1-axis]) > .1:
                continue
            length = abs(p[axis] - q[axis])
            keys = [key for key, value in dimensions.items() if abs(value-length) < .1
                    and key in (('width', 'depth') if axis == 0 else ('height', 'depth'))]
            if len(keys) != 1:
                continue
            band = {'start': min(p[axis], q[axis]), 'end': max(p[axis], q[axis]), 'dimension': keys[0]}
            if not any(abs(b['start']-band['start']) < 1 and abs(b['end']-band['end']) < 1 for b in axes[axis]):
                axes[axis].append(band)
    for bands in axes:
        bands.sort(key=lambda b: b['start'])
        for left, right in zip(bands, bands[1:]):
            if left['end'] > right['start'] + 1:
                raise ValueError('Các vùng kích thước trong form chồng nhau; cần xác nhận mốc co giãn trước khi đổi kích thước.')
    return axes


def map_coordinate(value, bands, delta):
    # Stretch through the centre; offsets, holes and hardware away from the seam
    # keep their original dimensions. Border endpoints move with their own edge.
    return value + sum(delta[b['dimension']] * (0 if value < (b['start']+b['end'])/2-.001
                       else .5 if abs(value-(b['start']+b['end'])/2) <= .001 else 1) for b in bands)


def readable_unicode(doc):
    """Legacy txt SHX cannot display the source's Vietnamese Unicode labels."""
    if 'AIDE_UNICODE' not in doc.styles:
        doc.styles.new('AIDE_UNICODE', dxfattribs={'font': 'arial.ttf'})
    for entity in doc.entitydb.values():
        if entity.dxftype() not in ('TEXT', 'MTEXT', 'ATTRIB', 'ATTDEF'):
            continue
        text = entity.text if entity.dxftype() == 'MTEXT' else entity.dxf.text
        style = doc.styles.get(entity.dxf.style)
        if any(ord(c) > 127 for c in text) and style.dxf.font.lower() in ('txt', 'txt.shx', 'simplex.shx'):
            entity.dxf.style = 'AIDE_UNICODE'


def stretch_entity(entity, point):
    kind = entity.dxftype()
    if kind == 'LINE':
        entity.dxf.start, entity.dxf.end = point(entity.dxf.start), point(entity.dxf.end)
    elif kind == 'LWPOLYLINE':
        entity.set_points([(point((x,y,0)).x, point((x,y,0)).y, sw, ew, bulge)
                           for x,y,sw,ew,bulge in entity.get_points()])
    elif kind == 'POLYLINE':
        for vertex in entity.vertices:
            vertex.dxf.location = point(vertex.dxf.location)
    elif kind in ('SOLID', 'TRACE', '3DFACE'):
        for key in ('vtx0', 'vtx1', 'vtx2', 'vtx3'):
            if entity.dxf.hasattr(key):
                setattr(entity.dxf, key, point(getattr(entity.dxf, key)))
    elif kind == 'HATCH':
        for path in entity.paths:
            if hasattr(path, 'vertices'):
                path.vertices = [(point((x,y,0)).x, point((x,y,0)).y, bulge) for x,y,bulge in path.vertices]
            else:
                for edge in path.edges:
                    for key in ('start', 'end', 'center'):
                        if hasattr(edge, key):
                            setattr(edge, key, point(getattr(edge, key)).vec2)
    elif kind in ('TEXT', 'MTEXT', 'ATTRIB', 'ATTDEF'):
        old = entity.dxf.insert
        new = point(old)
        entity.translate(new.x-old.x, new.y-old.y, 0)
    elif kind in ('CIRCLE', 'ARC', 'ELLIPSE', 'POINT'):
        key = 'location' if kind == 'POINT' else 'center'
        setattr(entity.dxf, key, point(getattr(entity.dxf, key)))
    else:
        box = bbox.extents([entity], fast=True)
        if not box.has_data:
            raise ValueError(f'Không thể điều chỉnh hình học {kind} trong form này.')
        lo, hi = point(box.extmin), point(box.extmax)
        if abs((hi.x-lo.x)-box.size.x) > .01 or abs((hi.y-lo.y)-box.size.y) > .01:
            raise ValueError(f'Chi tiết {kind} đi qua vùng co giãn; cần bổ sung mốc cho form này.')
        entity.translate(lo.x-box.extmin.x, lo.y-box.extmin.y, 0)


def generate(template_id, dimensions, product_name=''):
    item = resolve(template_id)
    nominal = item.get('dimensions')
    if not nominal:
        raise ValueError('Form chưa có kích thước gốc; hãy chọn form đã xác định kích thước.')
    if item.get('status') != 'source':
        raise ValueError(item.get('resize_note') or 'Form nguồn cần kiểm tra trước khi tạo CAD.')
    source = ezdxf.readfile(source_path(item))
    delta = {key: dimensions[key]-nominal[key] for key in nominal}
    resizing = any(abs(v) > .01 for v in delta.values())
    axes = stretch_axes(source, nominal) if resizing else [[], []]
    if resizing:
        if any(not .75 <= dimensions[k]/nominal[k] <= 1.25 for k in nominal):
            raise ValueError('Kích thước vượt khoảng co giãn 75–125% của form nguồn; hãy chọn form gần hơn.')
        supported = {b['dimension'] for bands in axes for b in bands}
        if any(abs(delta[k]) > .01 and k not in supported for k in nominal):
            raise ValueError('Form chưa đủ mốc kích thước để co giãn theo yêu cầu.')
    def point(p):
        p = Vec3(p)
        return Vec3(map_coordinate(p.x, axes[0], delta), map_coordinate(p.y, axes[1], delta), p.z)
    title_size = 'x'.join(f'{dimensions[k]:g}' for k in ('height', 'width', 'depth'))
    for insert in source.modelspace().query('INSERT'):
        if 'khung' not in insert.dxf.name.lower():
            continue
        for attr in insert.attribs:
            value = attr.dxf.text
            product_tag = ('#05' if insert.dxf.name.lower() == 'khungtenasean2'
                           else '#03' if insert.dxf.name.upper() == 'KHUNG CHUẨN' else 'SANPHAM')
            if re.search(r'\d{3,4}\s*[xX×*]\s*\d{3,4}\s*[xX×*]\s*\d{3,4}', value):
                attr.dxf.text = title_size
            elif attr.dxf.tag.upper() == product_tag or re.search(r'v[ỏõo]\s*t[ủu]', value, re.I):
                attr.dxf.text = product_name
            elif any(token in ''.join(c for c in unicodedata.normalize('NFD', value.upper().replace('Đ', 'D')) if not unicodedata.combining(c))
                     for token in ('NGOAI TROI', 'TRONG NHA', 'CHUA CHAY')):
                # This describes the actual source cabinet type.
                pass
            else:
                # Customer, date, maker and quantity belonged to the library
                # drawing. The new cabinet must not inherit that metadata.
                attr.dxf.text = ''
    readable_unicode(source)
    flattened = []
    for entity in source.modelspace():
        parts = list(recursive_decompose([entity]))
        rigid_offset = None
        if resizing and entity.dxftype() == 'INSERT' and 'khung' not in entity.dxf.name.lower():
            box = bbox.extents([entity], fast=True)
            if box.has_data and max(box.size.x, box.size.y) < min(nominal.values()) * .8:
                center = (box.extmin + box.extmax) / 2
                rigid_offset = point(center) - center
        if resizing and entity.dxftype() == 'DIMENSION' and entity.dimtype in (0, 1):
            p, q = entity.dxf.get('defpoint2'), entity.dxf.get('defpoint3')
            if p is not None and q is not None:
                old = entity.get_measurement()
                angle = math.radians(entity.dxf.get('angle', 0))
                vector = point(q)-point(p)
                new = abs(vector.x*math.cos(angle)+vector.y*math.sin(angle)) if entity.dimtype == 0 else vector.magnitude
                if abs(new-old) > .01:
                    for part in parts:
                        if part.dxftype() in ('TEXT', 'MTEXT'):
                            text = part.dxf.text if part.dxftype() == 'TEXT' else part.text
                            replacement = re.sub(r'(?<![\d.])'+re.escape(f'{old:g}')+r'(?![\d.])', f'{new:g}', text)
                            if part.dxftype() == 'TEXT': part.dxf.text = replacement
                            else: part.text = replacement
        for part in parts:
            copy = part.copy()
            # Mirrored source blocks produce negative-Z OCS geometry. Normalize
            # before using WCS stretch coordinates or the browser's block clone.
            upright(copy)
            if copy.dxftype() == 'ATTRIB':
                copy = attrib_to_text(copy)
            if rigid_offset is not None:
                copy.translate(rigid_offset.x, rigid_offset.y, 0)
            elif resizing:
                stretch_entity(copy, point)
            flattened.append(copy)
    target = ezdxf.new('R2018')
    target.units = 4
    importer = Importer(source, target)
    importer.import_entities(flattened)
    importer.finalize()
    target.header['$USERI1'] = 1
    stream = io.StringIO()
    target.write(stream)
    return stream.getvalue()


@lru_cache(maxsize=64)
def preview(template_id, stamp):
    from ezdxf.addons.drawing import RenderContext, Frontend, svg, layout
    doc = ezdxf.readfile(source_path(resolve(template_id)))
    readable_unicode(doc)
    renderer = svg.SVGBackend()
    Frontend(RenderContext(doc), renderer).draw_layout(doc.modelspace(), finalize=True)
    return renderer.get_string(layout.Page(0, 0, layout.Units.mm))
