"""Recover identifiable project block views with lossless visible-geometry checks."""
from pathlib import Path
import hashlib
import json
import re
import numpy as np
import ezdxf
from ezdxf.addons import Importer
from ezdxf.addons.drawing import Frontend, RenderContext, svg, layout
from ezdxf.addons.drawing.recorder import Recorder
from ezdxf.math import Matrix44

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / 'BE_AIDE/data/CatalogTB'
OUT = ROOT / 'outputs/sample-cad-recovery'


def recorded(doc, entities):
    recorder = Recorder()
    Frontend(RenderContext(doc), recorder).draw_entities(entities)
    return recorder.player()


def fingerprint(player):
    """Compare all drawn primitives, including text outlines and colours."""
    records = []
    for record, properties in player.recordings():
        shapes = [getattr(record, key) for key in ('path', 'points') if hasattr(record, key)]
        if hasattr(record, 'paths'):
            shapes.extend(record.paths)
        vertices = []
        for shape in shapes:
            method = getattr(shape, 'control_vertices', None) or getattr(shape, 'vertices', None)
            if method:
                vertices.append([[round(float(v), 5) for v in point] for point in method()])
        records.append([type(record).__name__, vertices, properties.color, properties.lineweight])
    return hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest(), len(records)


def compare_visible(before, after, tolerance=.01):
    """Arc subdivision can change after translation; compare drawn curves."""
    left, right = list(before.recordings()), list(after.recordings())
    if len(left) != len(right):
        raise ValueError('Visible primitive count changed')
    maximum = 0.
    def shapes(record):
        return [getattr(record, k) for k in ('path', 'points') if hasattr(record, k)] + list(getattr(record, 'paths', []))
    def points(shape):
        return np.array([tuple(v) for v in (shape.flattening(.001) if hasattr(shape, 'flattening') else shape.vertices())])
    def deviation(a, b):
        if len(b) == 1:
            return float(np.linalg.norm(a-b[0], axis=1).max())
        starts, vectors = b[:-1], b[1:]-b[:-1]
        denominator = (vectors*vectors).sum(axis=1)
        denominator[denominator == 0] = 1
        t = np.clip(((a[:, None, :]-starts)*vectors).sum(axis=2)/denominator, 0, 1)
        distance = np.linalg.norm(a[:, None, :]-starts-t[:, :, None]*vectors, axis=2)
        return float(distance.min(axis=1).max())
    for (a, pa), (b, pb) in zip(left, right):
        if type(a) != type(b) or pa.color != pb.color or pa.lineweight != pb.lineweight:
            raise ValueError('Visible primitive type, colour or stroke changed')
        aa, bb = shapes(a), shapes(b)
        if len(aa) != len(bb):
            raise ValueError('Visible compound path count changed')
        for sa, sb in zip(aa, bb):
            va, vb = points(sa), points(sb)
            if not len(va) or not len(vb):
                if len(va) != len(vb):
                    raise ValueError('Visible path became empty')
                continue
            maximum = max(maximum, deviation(va, vb), deviation(vb, va))
    if maximum > tolerance:
        raise ValueError(f'Visible geometry deviation {maximum:g} mm exceeds {tolerance:g} mm')
    return maximum


def export_face(doc, occurrence, destination):
    integrity = json.loads((OUT / 'source-integrity.json').read_text(encoding='utf8'))
    original = next(row for row in integrity if row['order'] == occurrence['order'])
    entity = doc.entitydb.get(occurrence['handle'])
    if entity is None or entity.dxftype() != 'INSERT':
        raise ValueError('Source occurrence no longer identifies a block insertion')
    before = recorded(doc, [entity])
    bounds = before.bbox()
    if not bounds.has_data:
        raise ValueError('Source view has no visible geometry')
    shift = Matrix44.translate(-bounds.extmin.x, -bounds.extmin.y, 0)
    before.transform(shift)
    target = ezdxf.new('R2018')
    target.units = doc.units
    importer = Importer(doc, target)
    # Existing Standard/0 defaults otherwise silently override supplier styles.
    importer.import_table('styles', replace=True)
    importer.import_table('linetypes', replace=True)
    importer.import_table('layers', replace=True)
    importer.import_entities([entity], target_layout=target.modelspace())
    importer.finalize()
    for imported in target.modelspace():
        imported.transform(shift)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / 'ban_ve.dxf'
    target.saveas(path)
    restored = ezdxf.readfile(path)
    after = recorded(restored, restored.modelspace())
    deviation = compare_visible(before, after)
    box = after.bbox()
    backend = svg.SVGBackend()
    after.replay(backend)
    (destination / 'xem_truoc.svg').write_text(backend.get_string(layout.Page(0, 0)), encoding='utf8')
    metadata = {'schema_version': '1.0', 'hinh_hoc_lap_dat': {
        'don_vi': 'mm', 'bao_hinh_mm': dict(min_x=box.extmin.x, min_y=box.extmin.y,
                                         max_x=box.extmax.x, max_y=box.extmax.y),
        'status': 'source_view_envelope_not_manufacturer_mounting_dimensions'},
        'provenance': {'order': occurrence['order'], 'handle': occurrence['handle'],
                       'source_dwg': original['source'], 'source_sha256': original['source_sha256'],
                       'effective_block': occurrence['effective_name'],
                       'dynamic_state': occurrence['properties'],
                       'owner_face_in_source': occurrence['owner_face']},
        'visible_linework': {'preserved': True, 'primitive_count': fingerprint(after)[1],
                             'maximum_curve_deviation_mm': deviation, 'tolerance_mm': .01,
                             'fingerprint': fingerprint(after)[0]}, 'fabrication_ready': False}
    (destination / 'thong_tin_cad_chen.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf8')
    return metadata


def run():
    rows = json.loads((ROOT / 'outputs/order-447-457-audit/cad-face-occurrences.json').read_text(encoding='utf8'))
    # Prefer a complete pair from the same project; source colour variants differ.
    rows.sort(key=lambda row: row['order'] != '457')
    documents = {order: ezdxf.readfile(OUT / order / 'source.dxf') for order in ('447', '457')}
    specifications = [
        ('Timer24h', 'TIMER 24H CHINT', 'TIMER', 'CHINT', None),
        ('Selector', 'CHUYEN MACH', 'SELECTOR', '', None),
        ('MC12AF', 'MC 12AF', 'CONTACTOR', 'LS Electric', None),
        ('SupplyS8FS', 'VTPK_S8FS-C05024J', 'POWER_SUPPLY', 'Omron', None),
        ('Relay125SRQ', '125SRQ', 'RELAY', '', None),
        ('FuseSingle', 'CẦU CHÌ', 'FUSE', '', None),
        *[(f'BKN_{p}P', 'BKN-LS', 'MCB', 'LS Electric', p) for p in (1, 2, 3)],
    ]
    report = []
    for key, name, category, brand, poles in specifications:
        selected = []
        for row in rows:
            if row['effective_name'] != name or not row['owner_face']:
                continue
            state = ' '.join(str(v) for v in row['properties'].values()).upper()
            if poles and re.search(r'\b[1-4]P', state) and not re.search(fr'\b{poles}P', state):
                continue
            if 'COVER' in state:
                face, label = 'cover', 'Nắp che mặt trước'
            elif row['owner_face'] == 'side_projection' or 'SIDE' in state:
                face, label = 'side', 'Mặt bên'
            else:
                face, label = 'front', 'Mặt trước'
            if any(x[0] == face for x in selected):
                continue
            selected.append((face, label, row))
        folder = LIB / 'ProjectSamples' / key
        profile = {'nhom': 'CAD từ bản vẽ mẫu', 'ten_san_pham': name + (f' · {poles}P' if poles else '') + ' · mẫu dự án',
                   'ten_kieu': name, 'hang_xac_nhan': brand,
                   'muc_do_xac_nhan': 'Hình CAD nguồn và các mặt; chưa xác nhận mã mua hàng/thông số điện',
                   'tu_khoa_tim_kiem': [name, key], 'thong_so': {},
                   'nhan_dien_ai': {'loai_thiet_bi_code': category, 'so_cuc': poles,
                                    'fabrication_ready': False, 'kich_thuoc_cad_la_kich_thuoc_hang': False},
                   'bo_tri_lap_dat': {'source_project_reference': True}, 'cad_don': [],
                   'nguon_cad': [], 'quy_tac_ghep_mat': {'basis': 'same_effective_source_block_current_state',
                                                       'exact_order_code_verified': False}}
        for face, label, row in selected:
            metadata = export_face(documents[row['order']], row, folder / 'CadDon' / face)
            entry = {'id_hinh_goc': face, 'huong_nhin': label, 'nhan_hien_thi': label,
                     'duong_dan': f'CadDon/{face}/ban_ve.dxf',
                     'bo_tri_trong_tu': {'cho_phep_chen': True, 'fabrication_ready': False},
                     'kiem_tra_net_cad': {'status': 'source_visible_primitives_preserved'}}
            profile['cad_don'].append(entry)
            profile['nguon_cad'].append(metadata['provenance'])
        if not profile['cad_don']:
            raise ValueError(f'No source views for {key}')
        primary = next((x for x in profile['cad_don'] if x['id_hinh_goc'] == 'front'), profile['cad_don'][0])
        profile['cad_chen_tu'] = {k: primary[k] for k in ('id_hinh_goc', 'huong_nhin', 'duong_dan')}
        (folder / 'thong_tin_thiet_bi.json').write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding='utf8')
        report.append({'profile': str(folder.relative_to(LIB)), 'views': [x[0] for x in selected],
                       'visible_linework_preserved': True, 'exact_model_verified': False})
    (OUT / 'imported-device-faces.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'profiles': len(report), 'views': sum(len(x['views']) for x in report),
                      'all_visible_primitives_preserved': True}))


if __name__ == '__main__':
    run()
