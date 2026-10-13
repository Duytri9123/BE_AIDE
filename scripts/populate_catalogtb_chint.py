"""Import reviewed CHINT source geometry; retain unresolved candidates explicitly."""
import json
import logging
import shutil
from pathlib import Path

import ezdxf
from ezdxf import bbox, transform
from ezdxf.addons import Importer
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.config import Configuration, ColorPolicy
from ezdxf.addons.drawing.layout import Page
from ezdxf.addons.drawing.properties import LayoutProperties
from ezdxf.addons.drawing.svg import SVGBackend

logging.getLogger('ezdxf').setLevel(logging.ERROR)
ROOT = Path(__file__).resolve().parents[1] / 'data/CatalogTB'
SOURCE = ROOT.parents[2] / 'Tudien/CATALOG_PHU_KIEN_DOC_LAP/02_BLOCK_VA_THIET_BI'
TARGET = ROOT / 'Chint/ThietBi'
WEB = 'https://www.chintglobal.com/global/en/products/low-voltage/iec/'
NP2 = 'https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/industrial-control/push-button/np2/catalog/NP2-PUSH-BUTTON-Catalog.pdf'
RT36 = 'https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/secondary-power-distribution/fuse1/rt36/catalog/RT36-Fuse-Catalog.pdf'
TIME = 'https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/industrial-control/time-switch/kg316t/manual/2207-KG316T-Time%20Switch-Manual.pdf'

def save(p, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def visible(doc, entities):
    for e in entities:
        if e.dxf.get('invisible', 0): continue
        layer = doc.layers.get(e.dxf.layer)
        if layer.is_off() or layer.is_frozen(): continue
        if e.dxftype() == 'INSERT': yield from visible(doc, e.virtual_entities())
        elif e.dxftype() not in ('TEXT', 'MTEXT', 'ATTRIB', 'ATTDEF', 'DIMENSION', 'LEADER', 'VIEWPORT'): yield e

def drawing(folder, sid, face, label=None, roi=None, variant=None, *, source_path=None):
    source = source_path or next(SOURCE.glob(sid + '_*/cad.dxf'))
    src = ezdxf.readfile(source)
    if any(e.dxftype() in ('REGION','3DSOLID','BODY','SURFACE') and not e.dxf.get('invisible',0) for block in src.blocks for e in block):
        raise RuntimeError(f'{sid}: native supplier-state export required; legacy import would lose ACIS connections')
    entities = list(visible(src, src.modelspace()))
    if roi:
        # Keep complete entities wholly inside the selected single control head.
        x0, y0, x1, y1 = roi
        entities = [e for e in entities if (b := bbox.extents([e])).has_data
                    and b.extmin.x >= x0-0.01 and b.extmin.y >= y0-0.01
                    and b.extmax.x <= x1+0.01 and b.extmax.y <= y1+0.01]
    assert entities, (sid, roi)
    doc = ezdxf.new('R2018'); doc.units = 4
    imp = Importer(src, doc); imp.import_entities(entities); imp.finalize()
    bounds = bbox.extents(doc.modelspace(), fast=False)
    assert bounds.has_data
    transform.translate(doc.modelspace(), (-bounds.center.x, -bounds.center.y, 0))
    bounds = bbox.extents(doc.modelspace(), fast=False)
    assert abs(bounds.center.x) < 0.001 and abs(bounds.center.y) < 0.001
    view_id = sid + (('-' + variant) if variant else '')
    dest = folder / 'HinhChieu' / view_id
    dest.mkdir(parents=True, exist_ok=True)
    doc.saveas(dest / 'ban_ve.dxf')
    backend = SVGBackend()
    Frontend(RenderContext(doc), backend, config=Configuration(color_policy=ColorPolicy.BLACK)).draw_layout(
        doc.modelspace(), layout_properties=LayoutProperties('Model', '#ffffff', '#243b53', units=4, dark_background=False))
    (dest / 'xem_truoc.svg').write_text(backend.get_string(Page(max(35, bounds.size.x+8), max(35, bounds.size.y+8))), encoding='utf-8')
    record = {'id': view_id, 'ten_hinh': face, 'nhan_hien_thi': label or face, 'loai_hinh': 'view',
              'tep': {'cad_dxf': 'ban_ve.dxf', 'preview': 'xem_truoc.svg'},
              'kich_thuoc_hinh_mm': {'ngang': round(bounds.size.x, 3), 'cao': round(bounds.size.y, 3)},
              'nguon_cad': source.relative_to(ROOT.parents[2]).as_posix(), 'vung_tach_mm': roi,
              'bien_the_cad': variant, 'don_vi': 'mm'}
    save(dest / 'thong_tin.json', record)
    insert = folder / 'CadDon' / view_id
    insert.mkdir(parents=True, exist_ok=True)
    for filename in ('ban_ve.dxf', 'xem_truoc.svg'): shutil.copy2(dest / filename, insert / filename)
    placement = {'mat_form_mac_dinh': face, 'cho_phep_chen': True,
                 'huong_dan': 'Chọn đúng mặt và biến thể. Mặt bên thể hiện chiều sâu, không thay cho mặt trước cánh tủ. Xoay CAD không xác nhận tư thế lắp được hãng cho phép.'}
    meta = {'id_hinh_goc': view_id, 'huong_nhin': face, 'nhan_hien_thi': label or face,
            'tep': record['tep'], 'bo_tri_trong_tu': placement,
            'hinh_hoc_lap_dat': {'don_vi': 'mm', 'goc_chen_dxf_mm': {'x': 0, 'y': 0},
                'bao_hinh_mm': {'min_x': round(bounds.extmin.x, 3), 'min_y': round(bounds.extmin.y, 3),
                               'max_x': round(bounds.extmax.x, 3), 'max_y': round(bounds.extmax.y, 3)},
                'tam_bao_hinh_mm': {'x': 0, 'y': 0}}, 'nguon_cad': record['nguon_cad'],
            'bien_the_cad': variant, 'ghi_chu': 'CAD đơn từ trạng thái đang hiển thị; giữ kích thước gốc, chưa xác nhận kích thước sản phẩm thực tế.'}
    save(insert / 'thong_tin_cad_chen.json', meta)
    return {'id_hinh_goc': view_id, 'huong_nhin': face, 'nhan_hien_thi': label or face,
            'duong_dan': f'CadDon/{view_id}/ban_ve.dxf', 'bo_tri_trong_tu': placement, 'bien_the_cad': variant}

def profile(key, name, kind, code, use, views, specs, urls, *, door=False, status=None, aliases=()):
    folder = TARGET / key
    entries = [drawing(folder, *v) for v in views]
    primary = next((v for v in entries if v['huong_nhin'] == 'Mặt trước'), entries[0])
    src = folder / 'CadDon' / primary['id_hinh_goc']; dest = folder / 'CadChenTu'; dest.mkdir(exist_ok=True)
    for filename in ('ban_ve.dxf', 'xem_truoc.svg', 'thong_tin_cad_chen.json'): shutil.copy2(src / filename, dest / filename)
    mounting = {'vi_tri_uu_tien': 'canh_ngoai' if door else 'ben_trong',
                'vi_tri_phu_hop': ['canh_ngoai', 'canh_trong'] if door else ['ben_trong'],
                'huong_dan': 'Đầu thao tác/đèn trên cánh, thân và cọc phía sau; kiểm tra lỗ khoét theo mã đầy đủ.' if door else 'Gắn trên tấm lắp hoặc ray theo tài liệu đúng biến thể; chừa khoảng đấu dây và bảo trì.'}
    d = {'nhom': 'Chint', 'ten_kieu': name, 'ten_san_pham': name, 'ban_chat': kind,
         'hang_xac_nhan': 'CHINT', 'ma_dong_san_pham': code, 'cong_dung': use,
         'vi_tri_lap_dat': mounting['huong_dan'], 'bo_tri_lap_dat': mounting, 'thong_so': specs,
         'quy_cach_hien_thi': specs.get('tom_tat', 'Chọn cấu hình điện theo mã đầy đủ'),
         'cac_hinh_cad': [v['id_hinh_goc'] for v in entries], 'cad_don': entries,
         'cad_chen_tu': {'id_hinh_goc': primary['id_hinh_goc'], 'huong_nhin': primary['huong_nhin'], 'duong_dan': 'CadChenTu/ban_ve.dxf'},
         'nguon_tham_khao': urls, 'tai_lieu_hang': urls[0] if urls else None,
         'muc_do_xac_nhan': status or 'Mã/dòng có trên CAD nguồn; thông số hãng là tham khảo theo dòng, chưa xác nhận kích thước và mã đặt hàng của CAD.',
         'tu_khoa_tim_kiem': [name, code or '', kind, *aliases],
         'nhan_dien_ai': {'loai_thiet_bi_code': {'Rơ le giám sát pha': 'PhaseRelay', 'Công tắc hẹn giờ': 'Timer', 'Cầu chì kèm đế': 'FuseAssembly', 'Nút nhấn': 'Pushbutton', 'Công tắc chọn': 'Selector', 'Đèn báo': 'Indicator', 'Rơ le trung gian': 'Relay', 'Biến áp điều khiển': 'Transformer'}[kind], 'hang': 'CHINT', 'cac_ma_dong_san_pham': [code] if code else [],
                         'ma_dat_hang_da_chon': None, 'thong_so_da_chon': {},
                         'tu_dong_chon_theo_vai_tro': bool(code and urls), 'kich_thuoc_cad_la_kich_thuoc_hang': False},
         'cau_hinh_chon': {'can_chon': ['Mã đầy đủ', 'Thông số điện', 'Biến thể CAD', 'Mặt CAD', 'Kiểu gá'], 'ma_da_chon': None},
         'dac_diem': ['Mỗi CAD chỉ chứa một mặt của một thiết bị hoặc biến thể.', 'Giữ tỷ lệ CAD gốc; không suy dòng chịu tải, màu đặt hàng hoặc lỗ gá từ bao hình.'],
         'yeu_cau_lap_dat': {'schema': 'installation_contract.schema.json', 'status': 'Dự thảo bố trí; cần xác nhận mã và dữ liệu gá/cọc',
                            'unknown_value': None, 'cad_rotation_is_mounting_approval': False},
         'lua_chon_ky_thuat': ['Đối chiếu điện áp, tiếp điểm, tải, kiểu gá và kích thước thực tế trước lắp đặt.']}
    if code == 'NP2':
        d['nhan_dien_ai']['pham_vi_ma'] = 'product_family_not_order_code'
        d['nhan_dien_ai']['can_xac_nhan_ghep_mat_va_bien_the'] = True
        d['yeu_cau_lap_dat']['du_lieu_hang_tham_khao'] = {'pham_vi': 'Dòng NP2, kiểm tra đúng phiên bản',
            'luc_siet_Nm': [0.8, 1.2], 'tiet_dien_day_mm2': [0.5, 2.5], 'tuot_day_mm': 8, 'nguon': NP2}
    d['nhan_dien_ai']['fabrication_ready'] = False
    save(folder / 'thong_tin_thiet_bi.json', d)
    return {'profile': (folder / 'thong_tin_thiet_bi.json').relative_to(ROOT).as_posix(), 'name': name, 'views': len(entries)}

def main():
    rows = []
    rows.append(profile('XJ3_G', 'Phase Relay CHINT XJ3-G', 'Rơ le giám sát pha', 'XJ3-G', 'Giám sát mất pha, thứ tự pha và mất cân bằng; điều khiển mạch bảo vệ.',
        [('B_0bb80e139ae2', 'Mặt trước')], {'tom_tat': '380 VAC · 1NO+1NC', 'dien_ap_tham_khao': '380 VAC', 'tan_so_Hz': '50/60', 'tiep_diem_tham_khao': '1NO+1NC', 'luu_y': 'Không gán chức năng quá/thấp áp của XJ3-D cho XJ3-G.'}, [WEB+'industrial-control/xj3.html'], aliases=['bao ve pha', 'phase failure relay']))
    rows.append(profile('KG316T', 'Timer CHINT KG316T', 'Công tắc hẹn giờ', 'KG316T', 'Đóng cắt theo lịch; dùng contactor cho tải lớn hoặc ba pha.',
        [('B_ce1fd0282461', 'Mặt trước')], {'tom_tat': '1NO · chọn điện áp', 'dien_ap_da_chon': None, 'tiep_diem_tham_khao': '1NO', 'luu_y': 'Chọn điện áp và tải tiếp điểm theo phiên bản. Trang hãng có mô tả kiểu gá không thống nhất; ưu tiên bản vẽ/manual đúng phiên bản.'}, [TIME, WEB+'industrial-control/kg316t.html'], aliases=['hen gio', 'timer 24h']))
    rows.append(profile('RT36_00', 'Fuse Assembly CHINT RT36-00 · 160A', 'Cầu chì kèm đế', 'RT36-00', 'Bảo vệ quá tải/ngắn mạch; chọn riêng ruột cầu chì và đế phù hợp.',
        [('B_696b26c03c1d', 'Mặt trước'), ('B_737ec3dcbebb', 'Mặt bên')], {'tom_tat': '160 A · 690 VAC trên CAD', 'nhan_tren_cad': 'RT36-00(NT00) AC690V 160A', 'cap_su_dung_tham_khao': 'gG', 'kha_nang_cat_tham_khao': '50 kA tại 690 VAC theo catalog RT36-00', 'dong_da_chon': None, 'luu_y': 'CAD có đế và ruột. Dòng 160A là nhãn nguồn, chưa phải lựa chọn cho một hệ thống.'}, [RT36], aliases=['cau chi', 'NT00', 'NH00']))
    for contact, sid1, sid2, x in [('NO','B_7f76c8fb858b','B_dcae49a71397',0), ('NC','B_1bdf96abf968','B_1d686a825497',50)]:
        rows.append(profile('NP2_'+contact, 'Pushbutton CHINT NP2 · '+contact, 'Nút nhấn', 'NP2', 'Đưa tín hiệu điều khiển bằng tiếp điểm '+contact+'.',
            [('B_9cf64fc3bafd', 'Mặt trước', 'Mặt trước · đầu tròn tham khảo', (x,-50,x+30,-20), 'FRONT_'+contact),
             (sid1,'Mặt bên','Mặt bên · kiểu đầu 1',None,'SIDE_1'), (sid2,'Mặt bên','Mặt bên · kiểu đầu 2',None,'SIDE_2')],
            {'tom_tat': contact+' · chọn kiểu đầu, màu và điện áp đèn', 'tiep_diem_tren_cad': contact, 'dien_ap_den_tren_cad': '230 V AC/DC', 'dong_tiep_diem_tren_cad': 'AC-15 220V/4.5A; DC-13 110V/0.6A', 'luu_y': 'Hai mặt bên là hai biến thể đầu, không phải hai góc của một cấu hình. Mặt trước tách từ bảng NP2; chưa xác nhận ghép với biến thể bên nào.'}, [NP2], door=True, aliases=['nut nhan', 'push button', 'BE101']))
    rows.append(profile('NP2_Selector', 'Selector CHINT NP2', 'Công tắc chọn', 'NP2', 'Chọn chế độ điều khiển.',
        [('B_9cf64fc3bafd','Mặt trước',None,(150,-53,180,-18),'SELECTOR')], {'tom_tat': 'Chọn số vị trí và tiếp điểm', 'so_vi_tri_da_chon': None, 'luu_y': 'Mặt trước từ bảng NP2; chưa có mặt bên của cùng mã.'}, [NP2], door=True, aliases=['cong tac chon', 'auto off man']))
    rows.append(profile('NP2_Indicator', 'Indicator CHINT NP2 · FAULT', 'Đèn báo', 'NP2', 'Hiển thị trạng thái lỗi theo sơ đồ tín hiệu.',
        [('B_9cf64fc3bafd','Mặt trước',None,(100,-50,130,-20),'FAULT')], {'tom_tat': 'Chọn màu và điện áp', 'mau_da_chon': None, 'dien_ap_da_chon': None, 'luu_y': 'FAULT là nhãn vận hành, không phải mã sản phẩm. NP2 là dòng của bảng nguồn; chưa xác nhận mã đèn đầy đủ.'}, [NP2], door=True, aliases=['den bao', 'pilot light']))
    rows.append(profile('RJ25_CL', 'Relay CHINT RJ25-CL', 'Rơ le trung gian', 'RJ25-CL', 'Chuyển tiếp tín hiệu điều khiển.',
        [('B_738461931c43','Mặt trước')], {'tom_tat': 'Chưa xác nhận cuộn hút và tiếp điểm', 'dien_ap_cuon_hut': None, 'tiep_diem': None, 'luu_y': 'RJ25-CL là nhãn nguồn; chưa tìm được tài liệu hãng khớp mã. Không thay bằng NJX/NXJ chỉ vì cùng kiểu relay.'}, [], status='Có nhãn CHINT/RJ25-CL trên nguồn; chưa xác nhận mã sản phẩm bằng tài liệu hãng.', aliases=['relay trung gian']))
    rows.append(profile('Control_Transformer', 'Transformer CHINT · chưa rõ mã', 'Biến áp điều khiển', None, 'Cấp điện áp AC cho mạch điều khiển.',
        [('B_f1955bc652ff','Mặt trước')], {'tom_tat': 'Chọn VA và điện áp sơ/thứ cấp', 'cong_suat_VA': None, 'dien_ap_vao': None, 'dien_ap_ra': None, 'luu_y': 'Nguồn ghi MBA - Chint; NDK chỉ là dòng tham khảo, không xác nhận CAD này là NDK.'}, [WEB+'industrial-control/ndk.html'], aliases=['bien ap', 'MBA', 'control transformer']))
    used = {'B_0bb80e139ae2','B_ce1fd0282461','B_696b26c03c1d','B_737ec3dcbebb','B_7f76c8fb858b','B_dcae49a71397','B_1bdf96abf968','B_1d686a825497','B_9cf64fc3bafd','B_738461931c43','B_f1955bc652ff'}
    audit = []
    for p in sorted(SOURCE.glob('*/thong_tin.json')):
        d = json.loads(p.read_text(encoding='utf-8'))
        if 'chint' not in json.dumps(d).lower(): continue
        sid = d['id']
        if sid in used: status = 'imported_active_state'
        elif sid == 'B_9a04669d7753': status = 'duplicate_RT36_front_kept_in_source'
        elif sid == 'B_61f9f7632ef6': status = 'existing_profile_DenBaoNutNhanCauChiContactor/ThietBi/CHINT_DenBaoPha'
        else: status = 'unresolved_nearby_brand_label_not_confirmed_product'
        audit.append({'source': p.relative_to(ROOT.parents[2]).as_posix(), 'id': sid, 'status': status,
                      'text_evidence': d.get('text_evidence', []), 'auto_select': sid in used and sid not in ('B_f1955bc652ff','B_738461931c43')})
    save(ROOT / 'Chint/kiem_tra_chint.json', {'profiles': len(rows), 'views': sum(r['views'] for r in rows), 'items': rows,
         'source_audit': audit, 'unresolved_policy': 'Đọc danh sách chưa xác định; không tự gán hãng/model từ nhãn gần CAD. Không dựng mặt thiếu hoặc ghép mặt bên khác biến thể.',
         'source_review': '../../../tmp/chint_source_review.png'})
    print('CHINT:', len(rows), 'profiles,', sum(r['views'] for r in rows), 'views;', len(audit), 'source blocks reviewed')

if __name__ == '__main__': main()
