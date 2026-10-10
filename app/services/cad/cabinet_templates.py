"""Whole source sheets and dimension-driven stretch (never synthetic cabinet faces)."""
import base64
import binascii
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

_DATA = Path(__file__).resolve().parents[3] / 'data'
LIBRARY = _DATA / 'CatalogTB/Form tủ'


def separation_forms():
    """IEC 61439-2 reference forms, distinct from physical enclosure templates."""
    path = LIBRARY / 'catalog.json'
    if not path.is_file():
        raise ValueError('Chưa tìm thấy danh mục form trong CatalogTB/Form tủ.')
    catalog = json.loads(path.read_text(encoding='utf-8'))
    forms = catalog.get('separation_forms', [])
    if not forms:
        raise ValueError('Danh mục CatalogTB chưa có form phân khoang.')
    return {'standard_scope': 'IEC 61439-2 internal separation', 'forms': forms}



@lru_cache(maxsize=2)
def _resize_profiles(stamp):
    path = LIBRARY / 'resize_profiles.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}


def resize_profile(item):
    path = LIBRARY / 'resize_profiles.json'
    profile = _resize_profiles(path.stat().st_mtime_ns if path.is_file() else 0).get(item['id'])
    return profile if profile and profile.get('nominal') == item.get('dimensions') else None


def inventory():
    path = LIBRARY / 'catalog.json'
    if not path.exists():
        raise ValueError('Thư viện vỏ tủ trống đã lọc chưa được lập chỉ mục.')
    rows = json.loads(path.read_text(encoding='utf8'))['shells']
    result = []
    for row in rows:
        dimensions = row.get('dimensions_mm') or {}
        description = row.get('source_specification', {}).get('FORM', '')
        kind = 'outdoor' if 'ngoài trời' in description.lower() else 'indoor' if 'trong nhà' in description.lower() else 'unknown'
        result.append({**row, 'kind': kind, 'filename': row['source_dxf'],
                       'dimensions': dimensions if dimensions and all(dimensions.get(k) for k in ('height', 'width', 'depth')) else None,
                       'status': 'needs_review', 'description': description,
                       'resize_note': 'CAD dự án đã làm sạch, cần xác nhận từng mặt và cơ khí trước đổi kích thước.'})
    for item in result:
        profile = resize_profile(item)
        item['stretch_dimensions'] = profile['supported'] if profile else []
        if profile:
            item['resize_note'] = 'Có thể điều chỉnh 75–125% kích thước gốc theo các mốc DIM nguồn.'
    return result


def resolve(template_id):
    item = next((i for i in inventory() if i['id'] == template_id), None)
    if not item:
        raise ValueError('Không tìm thấy form tủ nguồn.')
    return item


def source_path(item):
    # Keep the selected shell together with its original drawing frame.
    filename = (item.get('blank_source_frame') or {}).get('preview_cad') or item['filename']
    path = (LIBRARY / filename).resolve()
    if not path.is_relative_to(LIBRARY.resolve()) or not path.is_file():
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
        can_generate = bool(nominal and (not changed or (all(k in item.get('stretch_dimensions', []) for k in changed)
            and all(.75 <= dimensions[k]/nominal[k] <= 1.25 for k in dimensions))))
        note = item.get('resize_note', '')
        if nominal and changed and not can_generate:
            labels = {'height': 'H', 'width': 'W', 'depth': 'D'}
            supported = item.get('stretch_dimensions', [])
            if any(k not in supported for k in changed):
                note = 'Mẫu này chưa có mốc DIM nguồn cho chiều đang thay đổi. Chọn mẫu khác gần kích thước yêu cầu.'
            else:
                note = 'Khoảng điều chỉnh của mẫu: ' + ', '.join(
                    f'{labels[k]} {nominal[k]*.75:g}–{nominal[k]*1.25:g} mm' for k in ('height','width','depth')) + '.'
        rows.append({**item, 'resize_note': note, 'distance': distance, 'can_generate': can_generate,
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



def fill_title_block(doc, product_name, info):
    """Fill the cleaned source title cells; embed logos as portable CAD solids."""
    labels = {e.dxf.text.strip().upper(): e for e in doc.modelspace().query('TEXT')}
    required = ('DESIGNER', 'APPROVED', 'NAME', 'DATE', 'DRAWING NAME', 'CUSTOMER')
    if not all(key in labels for key in required):
        if any(info.values()):
            raise ValueError('Form này chưa có đủ ô khung tên để điền thông tin. Hãy chọn form có khung gốc.')
        return
    ext = bbox.extents(doc.modelspace(), fast=True)
    left, bottom, sheet_width = ext.extmin.x, ext.extmin.y, ext.size.x
    row = abs(labels['DESIGNER'].dxf.insert.y - labels['APPROVED'].dxf.insert.y)
    text_height = row * .38
    style_name = 'AIDE_TITLE'
    if style_name not in doc.styles:
        doc.styles.new(style_name, dxfattribs={'font': 'arial.ttf'})

    def text(value, x, y, width):
        if not value:
            return
        # Escape user text so it cannot introduce MTEXT formatting controls.
        value = str(value).replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}').replace('\n', ' ')
        doc.modelspace().add_mtext(value, dxfattribs={
            'insert': (x, y, 0), 'char_height': text_height,
            'width': width, 'attachment_point': 5, 'style': style_name, 'color': 7})

    designer_y = labels['DESIGNER'].dxf.insert.y + text_height * .4
    text(info.get('designer_name'), labels['NAME'].dxf.insert.x, designer_y, sheet_width * .09)
    text(info.get('drawing_date'), labels['DATE'].dxf.insert.x, designer_y, sheet_width * .055)
    customer = labels['CUSTOMER'].dxf.insert
    text(info.get('customer_name'), customer.x + sheet_width * .095, customer.y + text_height * .4, sheet_width * .10)
    drawing = labels['DRAWING NAME'].dxf.insert
    text(product_name, drawing.x, drawing.y - row * 1.3, sheet_width * .29)
    # Share the company cell horizontally: logo on the left, name on the right.
    company_y = bottom + row * 1.5
    text(info.get('company_name'), left + sheet_width * .355, company_y, sheet_width * .09)
    logo_data = info.get('logo_data')
    if not logo_data:
        return
    from PIL import Image, UnidentifiedImageError
    try:
        prefix, encoded = logo_data.split(',', 1)
        if prefix not in ('data:image/png;base64', 'data:image/jpeg;base64', 'data:image/webp;base64'):
            raise ValueError('Định dạng logo không hỗ trợ.')
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > 1024 * 1024:
            raise ValueError('Logo tối đa 1 MB.')
        with Image.open(io.BytesIO(raw)) as original:
            if original.width * original.height > 16000000:
                raise ValueError('Logo có kích thước quá lớn.')
            image = original.convert('RGBA')
            image.thumbnail((96, 64))
    except (ValueError, binascii.Error, UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError('Logo không hợp lệ. Dùng PNG, JPG hoặc WebP tối đa 1 MB.') from exc
    scale = min(sheet_width * .055 / image.width, row * 1.65 / image.height)
    x0 = left + sheet_width * .275 - image.width * scale / 2
    y0 = company_y - image.height * scale / 2
    pixels = image.load()
    for y in range(image.height):
        x = 0
        while x < image.width:
            rgba = pixels[x, y]
            end = x + 1
            while end < image.width and pixels[end, y] == rgba:
                end += 1
            if rgba[3] > 32:
                x1, x2 = x0 + x * scale, x0 + end * scale
                y1 = y0 + (image.height - y - 1) * scale
                doc.modelspace().add_solid([(x1, y1), (x2, y1), (x1, y1 + scale), (x2, y1 + scale)],
                    dxfattribs={'true_color': (rgba[0] << 16) | (rgba[1] << 8) | rgba[2]})
            x = end


def generate(template_id, dimensions, product_name='', title_info=None):
    item = resolve(template_id)
    nominal = item.get('dimensions')
    if not nominal:
        raise ValueError('Form chưa có kích thước gốc; hãy chọn form đã xác định kích thước.')
    delta = {key: dimensions[key]-nominal[key] for key in nominal}
    resizing = any(abs(v) > .01 for v in delta.values())
    source = ezdxf.readfile(source_path(item))
    profile = resize_profile(item)
    axes = profile['axes'] if resizing and profile else stretch_axes(source, nominal) if resizing else [[], []]
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
    for insert in source.modelspace().query('INSERT'):
        for attr in insert.attribs:
            if attr.dxf.tag.upper() == 'SIZE':
                attr.dxf.text = f"C{dimensions['height']:g}xR{dimensions['width']:g}xS{dimensions['depth']:g}"
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
            if resizing and copy.dxftype() in ('TEXT', 'MTEXT'):
                plain = copy.dxf.text if copy.dxftype() == 'TEXT' else copy.plain_text()
                matching = [key for key, value in nominal.items() if plain.strip() == f'{value:g}']
                if len(matching) == 1:
                    old = f'{nominal[matching[0]]:g}'
                    new = f'{dimensions[matching[0]]:g}'
                    if copy.dxftype() == 'TEXT': copy.dxf.text = new
                    else: copy.text = re.sub(r'(?<![\d.])'+re.escape(old)+r'(?![\d.])', new, copy.text)
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
    fill_title_block(target, product_name, title_info or {})
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
