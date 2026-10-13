"""Consolidate reviewed device families while keeping each CAD view independent."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'data' / 'CatalogTB'
ARCHIVE = ROOT.parent / 'CatalogTB_Archive' / '20261007_merge'


def read(p):
    return json.loads(p.read_text(encoding='utf-8'))


def write(p, d):
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def merge(source, target):
    src, dst = ROOT/source, ROOT/target
    if not src.exists():
        return False
    a, b = read(src/'thong_tin_thiet_bi.json'), read(dst/'thong_tin_thiet_bi.json')
    for p in src.rglob('*'):
        rel = p.relative_to(src)
        if not p.is_file() or rel.parts[0] == 'CadChenTu' or p.name == 'thong_tin_thiet_bi.json':
            continue
        dest = dst/rel
        if dest.exists():
            assert dest.read_bytes() == p.read_bytes(), dest
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
    b['cac_hinh_cad'] = list(dict.fromkeys(b['cac_hinh_cad'] + a['cac_hinh_cad']))
    ids = {v['id_hinh_goc'] for v in b['cad_don']}
    b['cad_don'] += [v for v in a['cad_don'] if v['id_hinh_goc'] not in ids]
    b.setdefault('cac_ho_so_da_gop', []).append({'thu_muc': source, 'ten': a['ten_kieu']})
    write(dst/'thong_tin_thiet_bi.json', b)
    backup = ARCHIVE/source
    assert src.resolve().is_relative_to(ROOT.resolve())
    assert backup.resolve().is_relative_to(ROOT.parent.resolve())
    assert not backup.exists()
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(backup))
    return True


merged = []
for size, code in [('116,5', '6621'), ('148,5', '6622'), ('204', '6623')]:
    source = f'Quạt/ThietBi/LuoiGio_{code}'
    target = f'Quạt/ThietBi/Leipole_FKL{code}_300'
    if merge(source, target):
        merged.append([source, target])
    path = ROOT/target/'thong_tin_thiet_bi.json'
    d = read(path)
    d['ten_kieu'] = d['ten_san_pham'] = f'Lưới thông gió · loại có lọc bụi · {size} × {size} mm'
    d['ban_chat'] = 'Lưới lọc thông gió thụ động, không có động cơ'
    d['hang_xac_nhan'] = None
    d['ma_dong_san_pham'] = None
    d['thong_so']['kieu_nan'] = 'Nan thẳng / nan chữ V'
    d['thong_so']['ma_ung_vien'] = f'Leipole FKL{code}.300 · kiểu nan chữ V'
    d['muc_do_xac_nhan'] = 'Gộp theo chức năng và cỡ mặt; hai kiểu nan là hai biến thể, chưa xác nhận cùng mã sản phẩm.'
    d['dac_diem'] = ['Có hai kiểu mặt trước: nan thẳng và nan chữ V.',
                     'Các mặt bên hiện có thuộc kiểu nan chữ V; không suy ra chiều sâu hoặc ngàm của kiểu nan thẳng.',
                     'Không có động cơ; dùng làm cửa lấy hoặc thoát gió, phối hợp quạt lọc của tủ.']
    d['bien_the_cad'] = [{'id': 'nan_thang', 'ten': 'Nan thẳng', 'hang': None},
                        {'id': 'nan_chu_v', 'ten': 'Nan chữ V', 'hang': 'Leipole', 'ma_goi_y': f'FKL{code}.300'}]
    for view in d['cad_don']:
        variant = 'nan_thang' if view['id_hinh_goc'].startswith('C01_') else 'nan_chu_v'
        view['bien_the'] = variant
        view['nhan_hien_thi'] = view['huong_nhin'] + (' · nan thẳng' if variant == 'nan_thang' else ' · nan chữ V')
        meta_path = path.parent/'CadDon'/view['id_hinh_goc']/'thong_tin_cad_chen.json'
        meta = read(meta_path)
        meta['bien_the'] = variant
        meta['nhan_hien_thi'] = view['nhan_hien_thi']
        write(meta_path, meta)
    write(path, d)

for source, target, name in [
    ('Phụ kiện tủ điện/ThietBi/KhoaTu_21', 'Khóa/ThietBi/MS8712', 'Khóa cam đầu tam giác MS8712'),
    ('Phụ kiện tủ điện/ThietBi/KhoaTu_14', 'Khóa/ThietBi/KhoaBat', 'Khóa bật cửa tủ · ký hiệu MS603-3'),
]:
    if merge(source, target):
        merged.append([source, target])
    p = ROOT/target/'thong_tin_thiet_bi.json'
    d = read(p)
    d['ten_kieu'] = d['ten_san_pham'] = name
    write(p, d)

renamed = []
for p in ROOT.rglob('thong_tin_thiet_bi.json'):
    d = read(p)
    old = d['ten_kieu']
    name = (d.get('ten_san_pham') or old).replace(' · nhãn ', ' · ký hiệu ')
    name = name.replace('hai mặt hình', 'mặt trước và mặt bên')
    if '_' in name and ' · ' not in name:
        name = d['ban_chat'] + ' · ' + name.replace('_', ' ')
    d['ten_kieu'] = d['ten_san_pham'] = name
    if old != name:
        renamed.append({'cu': old, 'moi': name})
    write(p, d)

# A shared side or cover is insufficient proof of the same device.
fingerprints = {}
for p in ROOT.rglob('thong_tin_thiet_bi.json'):
    for v in read(p)['cad_don']:
        svg = p.parent/Path(v['duong_dan']).parent/'xem_truoc.svg'
        key = hashlib.sha256(svg.read_bytes()).hexdigest()
        fingerprints.setdefault(key, []).append({'ho_so': p.parent.relative_to(ROOT).as_posix(), 'mat': v['id_hinh_goc']})
shared = [rows for rows in fingerprints.values() if len({r['ho_so'] for r in rows}) > 1]
write(ROOT/'kiem_tra_gop_thiet_bi.json', {'da_gop': merged, 'ten_da_sua': renamed,
                                       'cac_mat_dung_chung_can_doi_chieu': shared})
print(json.dumps({'merged': len(merged), 'renamed': len(renamed), 'shared_view_groups': len(shared)}))
