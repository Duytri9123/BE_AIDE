"""Review capacitor candidates and retain only the active CAD geometry."""
import json
import math
import shutil
from pathlib import Path

import ezdxf
from ezdxf import bbox
from ezdxf.addons import Importer

ROOT = Path(__file__).resolve().parents[1] / 'data' / 'CatalogTB'
BASE = ROOT / 'Tụ bù'
NU = 'https://etinco.vn/wp-content/uploads/2025/03/catalogue-tu-bu-nuintek.pdf'
SA = 'https://rhona.cl/uploads/archivos/20141222130945_cat-360306-360320cataloguesamwhacapacitor-1.pdf'


def read(p):
    return json.loads(p.read_text(encoding='utf-8'))


def write(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def visible(doc, entities):
    for entity in entities:
        if entity.dxf.get('invisible', 0):
            continue
        layer = doc.layers.get(entity.dxf.layer)
        if layer.is_off() or layer.is_frozen():
            continue
        if entity.dxftype() == 'INSERT':
            yield from visible(doc, entity.virtual_entities())
        else:
            yield entity


# Candidate associations are approximate, never a confirmed product identity.
SAM_OIL = {
    1: [('SMS-4150ST', 9.1)],
    2: [('SMB-45030KT', 30)],
    3: [('SMB-45040KT', 40)],
    4: [('SMS-45010KST', 10), ('SMS-45015KST', 15)],
    5: [('SMS-4300ST', 18.2)],
    6: [('SMB-45020KT', 20), ('SMB-45025KT', 25)],
    7: [('SMB-45030KT', 30)],
}
SAM_DRY = {1: [('RMC-445075KT', 7.5), ('RMC-445100KT', 10),
               ('RMC-445125KT', 12.5), ('RMC-445150KT', 15)],
           2: [('RMC-445300KT', 30)]}
NU_DRY = {1: [('KNE-4438205S', 5), ('KNE-4431646S', 10)],
          2: [('KNE-4432066S', 12.5), ('KNE-4432476S', 15)],
          3: [('KNE-4433296S', 20)], 4: [('KNE-4434116S', 25)],
          5: [('KNE-4434936S', 30)], 6: [('KNE-4436586S', 40)]}

review_path = ROOT.parents[1] / 'scripts' / 'catalogtb_face_review.json'
review = read(review_path)
report = []
for path in sorted(BASE.rglob('thong_tin_thiet_bi.json')):
    profile = read(path)
    source_path = next(path.parent.glob('HinhChieu/*/thong_tin.json'))
    record = read(source_path)
    ident = record['id']
    cluster, variant = map(int, ident.replace('C10_cluster', '').split('-V'))
    original = source_path.parent / record['tep']['cad_dxf']
    backup = BASE / 'TuLieuBanVe' / 'CADGoc' / (ident+'.dxf')
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(original, backup)
    src = ezdxf.readfile(backup)
    clean = ezdxf.new('R2018')
    clean.header['$INSUNITS'] = 4
    importer = Importer(src, clean)
    importer.import_entities(list(visible(src, src.modelspace())))
    importer.finalize()
    ext = bbox.extents(clean.modelspace(), fast=True)
    assert ext.has_data
    clean.saveas(original)
    size = {'ngang': round(ext.size.x, 1), 'cao': round(ext.size.y, 1)}
    record['kich_thuoc_hinh_mm'] = size
    face = 'Mặt bên' if ident == 'C10_cluster5-V001' else 'Mặt trước'
    record['ten_hinh'] = face
    write(source_path, record)
    review[ident] = face
    brand = 'Samwha' if cluster in (2, 3) else 'Nuintek'
    construction = 'khô' if cluster in (3, 6) else 'dầu'
    voltage = 415 if cluster == 5 else 440
    source = SA if brand == 'Samwha' else NU
    if cluster == 2:
        candidates = SAM_OIL[variant]
    elif cluster == 3:
        candidates = SAM_DRY[variant]
    elif cluster == 6:
        candidates = NU_DRY[variant]
    else:
        powers = [10, 15, 20, 25, 30, 40, 50] if cluster == 4 else [10, 15, 20, 25, 30, 40, 50]
        q = powers[variant-1]
        series = 'ENU' if variant <= 3 else 'ANU'
        candidates = [(f'{series}-{44 if voltage == 440 else 41}2{q}KS', q)]
    qtext = '/'.join(f'{q:g}' for _, q in candidates)
    title = (f'Tụ bù {construction} {brand} {voltage} V · gợi ý {qtext} kvar'
             f" · cỡ {size['ngang']:g} × {size['cao']:g} mm")
    profile['ten_kieu'] = profile['ten_san_pham'] = title
    profile['hang_xac_nhan'] = brand
    profile['ma_dong_san_pham'] = None
    profile['thong_so'] = {
        'dien_ap_dinh_muc': f'{voltage} V', 'tan_so_Hz': 50, 'so_pha': 3,
        'kich_thuoc_hinh_chieu_mm': f"{size['ngang']:g} × {size['cao']:g}",
        'ma_ung_vien': ' / '.join(code for code, _ in candidates),
        'dung_luong_goi_y_kvar': qtext,
        'dong_dien_goi_y_A': ' / '.join(f'{q*1000/(math.sqrt(3)*voltage):.1f}' for _, q in candidates),
    }
    profile['doi_chieu_san_pham'] = {
        'trang_thai': 'Mã gợi ý theo kiểu vỏ và kích thước gần tương ứng; chưa xác nhận mã thiết bị.',
        'cac_ma_goi_y': [{'ma': code, 'dung_luong_kvar': q,
                         'dien_ap_V': voltage, 'tan_so_Hz': 50, 'so_pha': 3,
                         'dong_dien_tinh_A': round(q*1000/(math.sqrt(3)*voltage), 1)}
                        for code, q in candidates],
        'gioi_han': 'Các thông số điện thuộc mã gợi ý. Cùng kiểu vỏ không xác định duy nhất dung lượng; không coi các mã này là thay thế trực tiếp.',
    }
    profile['muc_do_xac_nhan'] = profile['doi_chieu_san_pham']['trang_thai']
    profile['nguon_tham_khao'] = [source]
    profile['tai_lieu_hang'] = source
    profile['dac_diem'] = [
        'Mã và dung lượng nêu trên là gợi ý; cùng kiểu vỏ có thể có nhiều cấu hình điện.',
        'Dung lượng bù dùng đơn vị kvar; điện áp sử dụng thấp hơn điện áp định mức sẽ làm giảm dung lượng bù.',
        'Kích thước mặt CAD bao gồm phần chân gá hoặc đầu nối đang hiển thị.',
        f'Hiện có {face.lower()} riêng; chọn theo hướng bố trí thiết bị trong tủ.',
    ]
    profile['cac_mat_con_thieu'] = [f for f in ('Mặt trước', 'Mặt bên', 'Mặt trên') if f != face]
    profile['trang_thai_cad'] = f'Một {face.lower()} riêng.'
    for entry in profile.get('cad_don', []) + [profile.get('cad_chen_tu', {})]:
        entry['huong_nhin'] = face
    for meta_path in list(path.parent.glob('CadDon/*/thong_tin_cad_chen.json')) + list(path.parent.glob('CadChenTu/thong_tin_cad_chen.json')):
        meta = read(meta_path)
        meta['huong_nhin'] = face
        write(meta_path, meta)
    write(path, profile)
    report.append({'thiet_bi': title, 'id': ident, 'mat': face, 'kich_thuoc_mm': size,
                   'ma_goi_y': candidates})
write(review_path, review)
write(BASE/'kiem_tra_tu_bu.json', {'so_thiet_bi': len(report), 'thiet_bi': report})
print(f'Reviewed {len(report)} capacitor profiles')
