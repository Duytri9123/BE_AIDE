"""Read CatalogTB projection evidence independently of the priced SKU database."""
import hashlib
import json
from pathlib import Path
from functools import lru_cache

ROOT = Path(__file__).resolve().parents[3] / 'data' / 'CatalogTB'
FACES = {'Mặt trước':'front', 'Mặt bên':'side', 'Mặt trên':'top', 'Mặt sau':'rear', 'Mặt cắt':'section', 'Mặt có các lỗ đấu nối':'front'}


def assets():
    signature = tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size)
                      for p in sorted(ROOT.rglob('thong_tin_thiet_bi.json')))
    return _read(signature)


@lru_cache(maxsize=2)
def _read(signature):
    result = []
    for filename,_,_ in signature:
        p = Path(filename)
        profile = json.loads(p.read_text(encoding='utf-8'))
        ai = profile.get('nhan_dien_ai') or {}
        kind = str(ai.get('loai_thiet_bi_code') or '').upper()
        if not kind:
            continue
        family = hashlib.sha1(p.relative_to(ROOT).as_posix().encode()).hexdigest()[:16]
        primary = (profile.get('cad_chen_tu') or {}).get('id_hinh_goc')
        for entry in profile.get('cad_don') or []:
            face = FACES.get(entry.get('huong_nhin'), 'unknown')
            path = (p.parent / entry.get('duong_dan',f"CadDon/{entry['id_hinh_goc']}/ban_ve.dxf")).resolve()
            if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
                continue
            view = hashlib.sha1(f"{family}:{entry['id_hinh_goc']}".encode()).hexdigest()[:20]
            result.append(dict(id='tb:'+view, family_id='tb:'+family,
                name=profile.get('ten_san_pham') or profile.get('ten_kieu'),
                brand=profile.get('hang_xac_nhan') or '', category=kind,
                poles=ai.get('so_cuc'), face=face, primary=entry['id_hinh_goc']==primary,
                path=str(path), profile_path=p.relative_to(ROOT).as_posix(),
                specifications=profile.get('thong_so') or {},
                placement=entry.get('bo_tri_trong_tu') or {},
                mounting=profile.get('bo_tri_lap_dat') or {},
                confirmation=profile.get('muc_do_xac_nhan') or '',
                label_config=profile.get('nhan_bo_tri_cad') or {},
                replacement_options=profile.get('phuong_an_thay_the_agent') or {},
                components_per_asset=int((profile.get('cau_truc_cum') or {}).get('physical_units_per_cad',1)),
                status='reference_geometry', exact_model=False))
    return result


def resolve(asset_id, face=None):
    item = next((a for a in assets() if a['id']==asset_id),None)
    if not item:
        raise ValueError('Không tìm thấy CAD CatalogTB đã chọn')
    if face and item['face'] != face:
        raise ValueError('Mặt CAD đã chọn không đúng hướng nhìn yêu cầu')
    if item['placement'].get('cho_phep_chen') is False:
        raise ValueError('Hồ sơ không cho phép chèn mặt CAD này')
    return item


def candidates(category, brand=None, poles=None):
    from app.services.device_catalog_engine import strip_accents
    import re
    def norm(s):return strip_accents(str(s)).lower().replace(' electric','').strip()
    category = {'INDICATOR':'LIGHT','PILOT':'LIGHT'}.get(str(category).upper(),str(category).upper())
    rows=[]
    for a in assets():
        if a['category'] != category or a['face'] != 'front':continue
        if brand and norm(a['brand']) != norm(brand):continue
        if poles and category in ('MCB','MCCB','ACB','RCBO','RCCB','CONTACTOR','ISOLATOR'):
            match=re.fullmatch(r'(\d+)P?',str(a['poles'] or ''),re.I)
            if not match or int(match[1])!=int(poles):continue
        if a['placement'].get('cho_phep_chen') is False:continue
        rows.append(a)
    # Primary is a selected appearance; a cover is not another product.
    rows.sort(key=lambda a:(not a['primary'],a['name'],a['id']))
    seen=set();unique=[]
    for a in rows:
        if a['family_id'] in seen:continue
        seen.add(a['family_id']);unique.append(a)
    return unique


def instance_count(quantity, asset):
    count=int(asset.get('components_per_asset') or 1)
    quantity=int(quantity)
    if quantity<=0 or count<=0 or quantity%count:
        raise ValueError('Số lượng thiết bị không khớp số thành phần trong một CAD cụm; chọn CAD đơn hoặc cụm khác')
    return quantity//count
