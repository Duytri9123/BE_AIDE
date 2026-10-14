"""Manufacturer attribution is separate from SKU, ratings and CAD approval."""
import hashlib
import json
from pathlib import Path

EVIDENCE_PATH = Path(__file__).resolve().parents[1] / 'data/library_manufacturer_evidence.json'

SOURCE_MAKERS = {'@SCHNEIDER.DWG':'Schneider Electric', '@LS.DWG':'LS Electric',
                 '@CHINT.DWG':'CHINT', '@ABB.DWG':'ABB', '@MITSUBISHI.DWG':'Mitsubishi Electric'}
GENERIC_TYPES = ('bản lề','khóa cửa','khóa tay','khóa xoay','khóa cam','khóa bật','khóa móc',
                 'tay nắm','chốt trượt','chốt vặn','cửa sổ quan sát','túi đựng sơ đồ',
                 'máng dây','giá giữ nhãn','nhãn an toàn','điểm nâng','bản mã',
                 'chi tiết liên kết cơ khí','lưới lọc thông gió','lưới thông gió','tấm che bảo vệ quạt',
                 'giá đỡ cách điện','bộ đỡ cách điện','trụ đỡ cách điện','thanh đỡ cách điện',
                 'kẹp giữ thanh dẫn','mountingsupport','copperbusbar','đầu cốt cáp',
                 'thanh phân phối n và pe','thanh đấu nối')
PLACEHOLDERS = {'','asian','asia','oem','unknown','chưa xác định','chưa rõ'}


def manufacturer_identity(profile, current, profile_path=None):
    confirmed = current.get('hang_xac_nhan')
    if confirmed and str(confirmed).casefold() not in PLACEHOLDERS:
        return {'brand':confirmed,'brand_kind':'manufacturer','brand_identification_status':'verified',
                'brand_label':confirmed,'brand_identity_note':'Hãng được ghi trong hồ sơ thiết bị.'}
    if profile_path and EVIDENCE_PATH.is_file():
        evidence = json.loads(EVIDENCE_PATH.read_text(encoding='utf8')).get('evidence',{}).get(profile.get('id'))
        if evidence and evidence.get('status') in {'manufacturer_label_reviewed', 'manufacturer_candidate_reviewed', 'source_model_documented'}:
            if evidence['status'] == 'source_model_documented':
                source = current.get('nguon_cad') or {}
                expected = evidence.get('source') or {}
                if not expected.get('block') or not expected.get('sha256') or not evidence.get('manufacturer_document') or any(source.get(key) != expected.get(key) for key in ('block', 'sha256', 'file')):
                    evidence = None
            if not evidence:
                return manufacturer_identity(profile, current)
            view_paths = {v['id_hinh_goc']:v.get('duong_dan') for v in current.get('cad_don',[])}
            for view in evidence.get('views',[]):
                relative = view_paths.get(view['view_id'])
                if not relative:
                    continue
                drawing = (profile_path.parent / relative).resolve()
                if drawing.is_relative_to(profile_path.parent.resolve()) and drawing.is_file() and hashlib.sha256(drawing.read_bytes()).hexdigest() == view['sha256']:
                    maker = evidence['brand']
                    candidate = evidence['status'] == 'manufacturer_candidate_reviewed'
                    return {'brand':maker,'brand_kind':'manufacturer_candidate' if candidate else 'manufacturer',
                            'brand_identification_status':'candidate' if candidate else 'verified',
                            'brand_label':maker,'brand_identity_note':evidence.get('note') or 'Hãng được đọc từ nhãn CAD; cấu hình điện và mã đặt hàng được đối chiếu riêng.',
                            'reviewed_description':evidence.get('library_description') or {}}
    kind = str(profile.get('type') or current.get('ban_chat') or '').casefold()
    if any(term in kind for term in GENERIC_TYPES):
        return {'brand':None,'brand_kind':'generic','brand_identification_status':'not_applicable',
                'brand_label':'Phụ kiện phổ thông','brand_identity_note':'Hồ sơ không chỉ định hãng cho phụ kiện cơ khí này.'}
    source = current.get('nguon_cad') or {}
    source = source if isinstance(source,dict) else {}
    filename = str(source.get('file') or '').replace('\\','/').rsplit('/',1)[-1].upper()
    maker = SOURCE_MAKERS.get(filename)
    if maker and source.get('sha256') and source.get('block'):
        return {'brand':maker,'brand_kind':'manufacturer','brand_identification_status':'source_library',
                'brand_label':maker,'brand_identity_note':'Hãng theo thư viện CAD nguồn; mã đặt hàng và thông số được đối chiếu riêng.'}
    # Preserve identified candidate brands as candidates, without promoting them to approval.
    identification = current.get('nhan_dien_web') or {}
    candidate = identification.get('brand_candidate')
    if candidate and str(candidate).casefold() not in PLACEHOLDERS:
        return {'brand':candidate,'brand_kind':'manufacturer_candidate','brand_identification_status':'candidate',
                'brand_label':candidate,'brand_identity_note':'Hãng ứng viên trong hồ sơ; cần kiểm tra nhãn CAD.'}
    return {'brand':None,'brand_kind':'unidentified_equipment','brand_identification_status':'unknown',
            'brand_label':'Cần bổ sung hãng','brand_identity_note':'Thiết bị điện chưa có nhãn hãng trong hồ sơ nguồn; không dùng Asian làm tên hãng.'}


def identity_for_profile(current, path, root):
    profile_id = 'TB-' + hashlib.sha1(path.relative_to(root).as_posix().encode()).hexdigest()[:16]
    profile = {'id':profile_id,'type':current.get('ban_chat') or (current.get('nhan_dien_ai') or {}).get('loai_thiet_bi_code')}
    return manufacturer_identity(profile,current,path)
