"""Read CatalogTB projection evidence independently of the priced SKU database."""
import hashlib
import json
import time
from pathlib import Path
from functools import lru_cache

ROOT = Path(__file__).resolve().parents[3] / 'data' / 'CatalogTB'
FACES = {'Mặt trước':'front', 'Mặt bên':'side', 'Mặt trên':'top', 'Mặt sau':'rear', 'Mặt cắt':'section', 'Mặt có các lỗ đấu nối':'front', 'Mặt đứng':'front', 'Mặt hông':'side', 'Mặt bằng':'top', 'Mặt xuyên dây':'wire_passage', 'Mặt đấu dây':'wiring'}


def insertion_source(path):
    """Use native REGION outlines only while tied to the exact original DXF."""
    path=Path(path).resolve()
    marker=path.parent/'native_preview.json'
    if not marker.is_file():return path
    meta=json.loads(marker.read_text(encoding='utf8'))
    if not meta.get('insertion_outline'):return path
    derived=(path.parent/meta['insertion_outline']).resolve()
    if derived.parent!=path.parent or not derived.is_relative_to(ROOT.resolve()):
        raise ValueError('Bản chuyển nét CAD nằm ngoài thư viện')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=meta.get('source_sha256'):
        raise ValueError('CAD nguồn đã đổi; cần dựng lại nét REGION trước khi chèn')
    if hashlib.sha256(derived.read_bytes()).hexdigest()!=meta.get('outline_sha256'):
        raise ValueError('Bản chuyển nét CAD không khớp hồ sơ kiểm tra')
    return derived


def category_matches(requested, actual):
    """Search related roles without changing a holder into a complete fuse BOM."""
    requested=str(requested).upper().replace(' ','_')
    actual=str(actual).upper().replace(' ','_')
    aliases={'FUSE':{'FUSE','FUSE_HOLDER','FUSEASSEMBLY','FUSE_ASSEMBLY'},
             'LIGHT':{'LIGHT','INDICATOR','PILOT'},'INDICATOR':{'LIGHT','INDICATOR','PILOT'},
             'BUTTON':{'BUTTON','PUSHBUTTON'},'PUSHBUTTON':{'BUTTON','PUSHBUTTON'},
             'PHASE_RELAY':{'PHASE_RELAY','PHASERELAY'},
             'MOUNTING_SUPPORT':{'MOUNTING_SUPPORT','MOUNTINGSUPPORT'},
             'AUX_CONTACT':{'AUX_CONTACT'}}
    return actual in aliases.get(requested,{requested})


def assets(refresh=False):
    if refresh:
        _signature.cache_clear()
        _read.cache_clear()
    return _read(_signature(int(time.monotonic()/5)))


@lru_cache(maxsize=2)
def _signature(window):
    signature = tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size)
                      for p in sorted(ROOT.rglob('thong_tin_thiet_bi.json')))
    manifest=ROOT/'ai_library_manifest.json'
    if manifest.is_file():signature+=((str(manifest),manifest.stat().st_mtime_ns,manifest.stat().st_size),)
    variants = ROOT / 'electrical_selection_variants.json'
    if variants.is_file():signature+=((str(variants),variants.stat().st_mtime_ns,variants.stat().st_size),)
    return signature


@lru_cache(maxsize=2)
def _read(signature):
    result = []
    manifest=ROOT/'ai_library_manifest.json'
    discovery={r['profile']:r for r in json.loads(manifest.read_text(encoding='utf8')).get('items',[])} if manifest.is_file() else {}
    variants_path = ROOT / 'electrical_selection_variants.json'
    variants = json.loads(variants_path.read_text(encoding='utf8')).get('variants', []) if variants_path.is_file() else []
    for filename,_,_ in signature:
        p = Path(filename)
        if p.name!='thong_tin_thiet_bi.json':continue
        profile = json.loads(p.read_text(encoding='utf-8'))
        ai = profile.get('nhan_dien_ai') or {}
        mapped=discovery.get(p.relative_to(ROOT).as_posix()) or {}
        if mapped.get('sha256')!=hashlib.sha256(p.read_bytes()).hexdigest():mapped={}
        kind = str(ai.get('loai_thiet_bi_code') or mapped.get('category_code') or 'UNCLASSIFIED').upper()
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
                classification_source='profile' if ai.get('loai_thiet_bi_code') else 'ai_library_manifest' if mapped else 'unclassified_discovery',
                brand=profile.get('hang_xac_nhan') or '', category=kind,
                variant_id=entry.get('bien_the_cad') or entry.get('bien_the'),
                variant_pairing_rule=profile.get('quy_tac_ghep_mat') or {},
                poles=ai.get('so_cuc'), measurement_function=ai.get('measurement_function'), search_aliases=profile.get('tu_khoa_tim_kiem') or [], face=face, primary=entry['id_hinh_goc']==primary,
                path=str(path), profile_path=p.relative_to(ROOT).as_posix(),
                specifications=profile.get('thong_so') or {},
                electrical_variants=[v for v in variants if v['profile'] == p.relative_to(ROOT).as_posix()],
                placement=entry.get('bo_tri_trong_tu') or {},
                linework_review=entry.get('kiem_tra_net_cad') or {},
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
    if item['category']=='UNCLASSIFIED':
        raise ValueError('CAD có trong thư viện nhưng chưa xác định loại thiết bị; cần nhận diện trước chèn')
    if face and item['face'] != face:
        raise ValueError('Mặt CAD đã chọn không đúng hướng nhìn yêu cầu')
    if item['linework_review'].get('status')=='unresolved_visible_geometry_defect':
        raise ValueError('CAD còn thiếu chi tiết đã được báo lỗi; cần sửa hình học trước khi chèn layout')
    if item['placement'].get('cho_phep_chen') is False:
        raise ValueError('Hồ sơ không cho phép chèn mặt CAD này')
    return item


def candidates(category, brand=None, poles=None, measurement_function=None, face=None):
    import re,unicodedata
    def norm(s):
        text=''.join(c for c in unicodedata.normalize('NFD',str(s)) if not unicodedata.combining(c))
        return text.replace('đ','d').replace('Đ','D').lower().replace(' electric','').strip()
    category = {'INDICATOR':'LIGHT','PILOT':'LIGHT'}.get(str(category).upper(),str(category).upper())
    rows=[]
    for a in assets():
        if not category_matches(category,a['category']):continue
        if a['linework_review'].get('status')=='unresolved_visible_geometry_defect':continue
        allowed_faces={face} if face else ({'front','wire_passage','top'} if category=='CT' else {'front','wiring'} if category=='TERMINAL' else {'front'})
        if a['face'] not in allowed_faces:continue
        if measurement_function and a.get('measurement_function')!=measurement_function:continue
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


def inventory_diagnostics():
    """Distinguish unindexed CAD from genuinely absent equipment."""
    missing=[]
    for p in sorted(ROOT.rglob('thong_tin_thiet_bi.json')):
        profile=json.loads(p.read_text(encoding='utf8'))
        if not (profile.get('nhan_dien_ai') or {}).get('loai_thiet_bi_code'):
            missing.append({'profile':p.relative_to(ROOT).as_posix(),
                            'name':profile.get('ten_san_pham'),
                            'cad_views':len(profile.get('cad_don') or [])})
    return {'assets':len(assets(refresh=True)), 'unclassified_profiles':missing,
            'unclassified_is_not_missing_cad':True}


def instance_count(quantity, asset):
    count=int(asset.get('components_per_asset') or 1)
    quantity=int(quantity)
    if quantity<=0 or count<=0 or quantity%count:
        raise ValueError('Số lượng thiết bị không khớp số thành phần trong một CAD cụm; chọn CAD đơn hoặc cụm khác')
    return quantity//count
