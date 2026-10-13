"""Persist visually reviewed projections and their installation guidance."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'data' / 'CatalogTB'
review = json.loads(Path(__file__).with_name('catalogtb_face_review.json').read_text(encoding='utf-8'))

def guidance(face, category):
    if face == 'Nắp che mặt trước':
        return {'mat_form_mac_dinh': 'Mặt trước', 'cho_phep_chen': True,
                'huong_dan': 'Biểu diễn mặt trước khi dùng nắp che. Đây là trạng thái đóng nắp, không phải mặt bên hoặc mặt sau.'}
    if face.startswith('Mặt bên ·'):
        face = 'Mặt bên'
    if face.startswith('Mặt trước ·'):
        face = 'Mặt trước'
    if face == 'Mặt dưới':
        return {'mat_form_mac_dinh': 'Mặt dưới', 'cho_phep_chen': True,
                'huong_dan': 'Dùng khi nhìn từ phía dưới lên thiết bị, để bố trí đầu nối hoặc kiểm tra chiều sâu. Không dùng thay mặt trước khi thiết bị lắp đứng.'}
    if face in ('CAD thiếu đường nét', 'CAD còn nhiều mặt', 'CAD cần đối chiếu thiết bị'):
        return {'mat_form_mac_dinh': None, 'cho_phep_chen': False,
                'huong_dan': 'Cần hoàn thiện hoặc tách CAD trước khi bố trí vào tủ.'}
    if face == 'Mặt xuyên dây':
        return {'mat_form_mac_dinh': 'Mặt trước', 'cho_phep_chen': True,
                'huong_dan': 'Dùng khi nhìn dọc theo dây hoặc thanh cái xuyên lõi. Khi lắp đứng và nhìn vào lỗ, dùng cho mặt trước tủ; nếu đổi hướng xuyên dây, chọn lại mặt CAD.'}
    if category == 'DenBaoNutNhanCauChiContactor' and face == 'Mặt bên':
        text = 'Thể hiện chiều sâu thân phía sau cánh tủ. Không dùng cho mặt trước cánh tủ khi đầu đèn/nút hướng ra người nhìn.'
    elif face == 'Mặt đấu dây':
        return {'mat_form_mac_dinh': 'Mặt trước', 'cho_phep_chen': True,
                'huong_dan': 'Dùng cho bố trí nhìn vào các đầu đấu dây khi thiết bị gắn trên tấm lắp hoặc ray DIN hướng về người nhìn.'}
    elif face in ('Mặt đấu nối phía sau', 'Mặt sau'):
        return {'mat_form_mac_dinh': 'Mặt sau', 'cho_phep_chen': True,
                'huong_dan': 'Dùng khi nhìn từ phía sau thiết bị để bố trí đầu đấu nối; không phải mặt thao tác phía trước.'}
    elif face == 'Mặt có các lỗ đấu nối':
        return {'mat_form_mac_dinh': 'Mặt trước', 'cho_phep_chen': True,
                'huong_dan': 'Dùng khi nhìn vuông góc vào mặt có các lỗ đấu nối. Phù hợp bố trí trên tấm lắp nếu mặt này hướng ra người nhìn.'}
    elif face == 'Mặt trước':
        text = 'Dùng cho mặt trước form tủ khi mặt thao tác hoặc mặt chính của thiết bị hướng về người nhìn.'
    elif face == 'Mặt bên':
        text = 'Dùng cho mặt bên form tủ khi thiết bị giữ tư thế lắp đứng. Nếu xoay tư thế lắp, cần đối chiếu lại hướng nhìn.'
    elif face == 'Mặt trên':
        text = 'Dùng cho mặt trên form tủ khi nhìn từ trên xuống thiết bị lắp đứng. Thiết bị nằm ngang có thể cần mặt này cho hướng nhìn khác.'
    else:
        return {'mat_form_mac_dinh': None, 'cho_phep_chen': True,
                'huong_dan': 'Chưa đủ căn cứ xác nhận hướng nhìn. Đối chiếu các đầu nối, bề mặt lắp và tư thế đặt trước khi chọn.'}
    return {'mat_form_mac_dinh': face, 'cho_phep_chen': True, 'huong_dan': text}

changed = 0
for path in ROOT.rglob('thong_tin_thiet_bi.json'):
    p = json.loads(path.read_text(encoding='utf-8'))
    category = path.relative_to(ROOT).parts[0]
    for entry in p.get('cad_don', []):
        ident = entry['id_hinh_goc']
        meta_path = path.parent / 'CadDon' / ident / 'thong_tin_cad_chen.json'
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        if ident in review:
            meta['huong_nhin'] = entry['huong_nhin'] = review[ident]
            meta['nhan_dien_mat'] = 'Đã đối chiếu hình dạng; hướng sử dụng phụ thuộc tư thế lắp.'
            changed += 1
        use = guidance(meta['huong_nhin'], category)
        meta['bo_tri_trong_tu'] = entry['bo_tri_trong_tu'] = use
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        if p.get('cad_chen_tu', {}).get('id_hinh_goc') == ident:
            p['cad_chen_tu']['huong_nhin'] = meta['huong_nhin']
            (path.parent/'CadChenTu'/'thong_tin_cad_chen.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    path.write_text(json.dumps(p, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(f'Reviewed {changed} projections; installation guidance saved for all profiles.')
