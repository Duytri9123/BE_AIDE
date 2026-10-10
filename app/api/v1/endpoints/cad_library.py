import json
import hashlib
import re
import unicodedata
from pathlib import Path
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.responses import Response
from functools import lru_cache
from app.api.deps import get_current_active_user
from app.services.cad.library_taxonomy import classify, explicit_brands
from app.services.equipment_library import SOURCE_ROOT, CATALOG_DIR

router = APIRouter(dependencies=[Depends(get_current_active_user)])
LIBRARY = Path(__file__).resolve().parents[4] / "data" / "CatalogTB"
CATALOG_TB = Path(__file__).resolve().parents[4] / "data" / "CatalogTB"
EMIC_CT_CATALOG = "https://emic.com.vn/img/files/bien-dong/Catalog%20xuy%E1%BA%BFn%20CT0.6%20%28290623%29.pdf"


def catalog_tb_manifest():
    """Expose named devices and their separate, centered CAD projections."""
    items = []
    views = {}
    if not CATALOG_TB.is_dir():
        return items, views
    for profile_path in sorted(CATALOG_TB.rglob('thong_tin_thiet_bi.json')):
        profile = json.loads(profile_path.read_text(encoding='utf-8'))
        if not profile.get('cad_don'):
            continue
        profile_id = hashlib.sha1(profile_path.relative_to(CATALOG_TB).as_posix().encode()).hexdigest()[:16]
        primary_id = profile.get('cad_chen_tu', {}).get('id_hinh_goc')
        cad_views = []
        seen_geometry = {}
        for entry in profile['cad_don']:
            folder = profile_path.parent / 'CadDon' / entry['id_hinh_goc']
            dxf = (folder / 'ban_ve.dxf').resolve()
            preview = (folder / 'xem_truoc.svg').resolve()
            if not dxf.is_relative_to(CATALOG_TB.resolve()) or not dxf.is_file() or not preview.is_file():
                continue
            geometry_key = hashlib.sha256(preview.read_bytes()).hexdigest()
            view_id = hashlib.sha1(f"{profile_id}:{entry['id_hinh_goc']}".encode()).hexdigest()[:20]
            face = entry.get('huong_nhin') or 'Chưa xác định hướng nhìn'
            view = {'id': view_id, 'source_id': entry['id_hinh_goc'], 'face': face,
                    'label': entry.get('nhan_hien_thi') or (face if face != 'Chưa xác định hướng nhìn' else f'Mặt CAD {len(cad_views) + 1} · chưa xác định hướng'),
                    'is_primary': entry['id_hinh_goc'] == primary_id,
                    'placement': entry.get('bo_tri_trong_tu', {}),
                    'preview_url': f'/cad-library/catalog-tb/view/{view_id}/preview',
                    'insert_url': f'/cad-library/catalog-tb/view/{view_id}/insert-dxf'}
            cad_views.append(view)
            seen_geometry[geometry_key] = view
            views[view_id] = {'dxf': dxf, 'preview': preview,'linework_review':entry.get('kiem_tra_net_cad') or {}}
        if not cad_views:
            continue
        brand = profile.get('hang_xac_nhan') or ''
        code = profile.get('ma_dong_san_pham') or profile.get('ten_kieu') or ''
        items.append({'id': profile_id, 'name': profile.get('ten_san_pham') or profile.get('ten_kieu'),
                      'spec_hint': profile.get('quy_cach_hien_thi', ''),
                      'search_aliases': profile.get('tu_khoa_tim_kiem', []),
                        'ai_identification': profile.get('nhan_dien_ai', {}),
                      'conductor_requirements': profile.get('yeu_cau_chon_day', {}),
                      'installation_requirements': profile.get('yeu_cau_lap_dat', {}),
                      'parametric_cad': profile.get('cad_tham_so', {}),
                      'selection_configuration': profile.get('cau_hinh_chon', {}),
                      'code': code, 'brand': brand, 'category': profile.get('nhom') or profile_path.relative_to(CATALOG_TB).parts[0],
                      'device_type': profile.get('ban_chat') or profile.get('loai_thiet_bi') or '',
                      'use': profile.get('cong_dung') or '', 'placement': profile.get('vi_tri_lap_dat') or '',
                      'features': profile.get('dac_diem') or [], 'view_count': len(cad_views),
                      'views': cad_views, 'mounting': profile.get('bo_tri_lap_dat', {}),
                      'source_url': profile.get('tai_lieu_hang') or (EMIC_CT_CATALOG if brand == 'EMIC' and code.startswith('EM4H') else None)})
    return items, views


@router.get('/catalog-tb')
def list_catalog_tb(q: str = ''):
    items, _ = catalog_tb_manifest()
    if q:
        def search_key(value):
            value = unicodedata.normalize('NFD', str(value or '').casefold()).replace('đ', 'd')
            return re.sub(r'[^a-z0-9]', '', value)
        terms = [search_key(term) for term in q.split() if search_key(term)]
        items = [item for item in items if all(term in search_key(' '.join(
            [item['name'], item['code'], item['brand'] or '', item['category'], item['device_type'],
             *item.get('search_aliases', [])])) for term in terms)]
    rules_path = CATALOG_TB / 'ai_selection_rules.json'
    return {'total': len(items), 'items': items,
            'selection_rules': json.loads(rules_path.read_text(encoding='utf-8')) if rules_path.is_file() else {}}


@router.get('/catalog-tb/view/{view_id}/preview')
def catalog_tb_preview(view_id: str):
    asset = catalog_tb_manifest()[1].get(view_id)
    if not asset:
        raise HTTPException(404, 'Không tìm thấy mặt CAD')
    return FileResponse(asset['preview'], media_type='image/svg+xml')


@router.get('/catalog-tb/view/{view_id}/insert-dxf')
def catalog_tb_insert_dxf(view_id: str):
    asset = catalog_tb_manifest()[1].get(view_id)
    if not asset:
        raise HTTPException(404, 'Không tìm thấy mặt CAD')
    if asset.get('linework_review',{}).get('status')=='unresolved_visible_geometry_defect':
        raise HTTPException(422,'CAD còn thiếu chi tiết; cần sửa hình học trước khi chèn layout')
    import io
    import ezdxf
    from ezdxf.disassemble import recursive_decompose
    from ezdxf.addons import Importer
    from app.services.cad.catalogtb_assets import insertion_source
    source = ezdxf.readfile(insertion_source(asset['dxf']))
    target = ezdxf.new('R2018')
    target.units = source.units
    importer = Importer(source, target)
    importer.import_entities(list(recursive_decompose(source.modelspace())))
    importer.finalize()
    stream = io.StringIO()
    target.write(stream)
    return Response(stream.getvalue(), media_type='application/dxf')


def guess_view_label(width: float, height: float) -> str:
    # Kept for old callers; shape proportions cannot establish view orientation.
    return 'Hình nguồn'


def manifest():
    import time
    catalog = CATALOG_DIR / 'equipment_catalog.sqlite'
    stamp = catalog.stat().st_mtime_ns if catalog.is_file() else 0
    return _current_manifest(int(time.monotonic() / 5),stamp)


@lru_cache(maxsize=2)
def _current_manifest(window, catalog_stamp):
    items = []
    from app.services.cad.catalogtb_assets import assets
    for a in assets():
        items.append(dict(id=a['id'], catalog_id=None, name=a['name'], brand=a['brand'],
            kind='device', group=a['category'], category=a['category'], library='CatalogTB',
            filename=a['path'], source_file=a['profile_path'], source_block=a['name'],
            cad_status=a['status'], recognition=dict(face=a['face'],name=a['name'],
                family=a['family_id'],brand=a['brand'],status=a['status'])))
    return {'items': items}


@lru_cache(maxsize=2)
def _manifest_cached(signature, evidence_stamp=0):
    from app.services.cad.recognition import evidence
    items = []
    for filename, _, _ in signature:
        path = Path(filename)
        for entry in json.loads(path.read_text(encoding="utf-8"))["items"]:
            brands = explicit_brands(entry.get('category', '') + ' ' + entry['name'])
            items.append({**entry, "library": path.parent.name,
                          **classify(entry['name'], entry.get('category', '')),
                          "brand": brands[0] if len(brands) == 1 else entry.get('brand', 'Chưa xác định hãng'),
                          "brands_in_source": brands,
                          "is_collection": path.parent.name == 'source_cells'})
    for item in items:
        recognition = evidence(item)
        item['recognition'] = recognition
        item['brand'] = recognition['brand']
        for field in ('kind', 'group'):
            if field in recognition: item[field] = recognition[field]
    return {"items": items}


def resolve_model_asset(sku, parameters, items=None):
    """Insert only a 2026 catalog record with exact-model CAD."""
    items = items if items is not None else manifest()["items"]
    asset_id = ((parameters or {}).get('cad') or {}).get('catalog_id')
    if not asset_id:
        return None
    asset = next((item for item in items if item['catalog_id'] == asset_id), None)
    if asset and (SOURCE_ROOT / asset['filename']).is_file():
        return asset
    return None


@router.get("")
def list_layouts(q: str = "", brand: str = "", kind: str = "", group: str = ""):
    return {"items": [item for item in manifest()["items"]
                      if q.casefold() in (item["name"] + " " + item.get("brand", "")).casefold()
                      and (not brand or item.get("brand") == brand)
                      and (not kind or item['kind'] == kind)
                      and (not group or item['group'] == group)]}


@router.get('/categories')
def list_categories():
    """Source-backed folders by device/accessory function."""
    counts = defaultdict(int)
    for item in manifest()['items']:
        counts[(item['kind'], item['group'])] += 1
    return {'items': [dict(kind=kind, group=group, count=count)
                      for (kind, group), count in sorted(counts.items())]}


@router.get("/{asset_id}/dxf")
def download_layout(asset_id: str):
    if asset_id.startswith('tb:'):
        from app.services.cad.catalogtb_assets import resolve
        try:
            asset = resolve(asset_id)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        return FileResponse(asset['path'], filename=asset_id.replace(':','_')+'.dxf', media_type='application/dxf')
    item = next((item for item in manifest()["items"] if item["id"] == asset_id), None)
    if not item:
        raise HTTPException(404, "Không tìm thấy hình thiết bị")
    path = (SOURCE_ROOT / item['filename']).resolve()
    if not path.is_relative_to(SOURCE_ROOT.resolve()) or not path.is_file():
        raise HTTPException(404, "Không tìm thấy file DXF")
    return FileResponse(path, filename=f"{asset_id}.dxf", media_type="application/dxf")


@lru_cache(maxsize=512)
def render_layout_svg(asset_id: str):
    import ezdxf
    from ezdxf.addons.drawing import RenderContext, Frontend, svg, layout
    response = download_layout(asset_id)
    from app.services.cad.catalogtb_assets import insertion_source
    doc = ezdxf.readfile(insertion_source(response.path))
    backend = svg.SVGBackend()
    Frontend(RenderContext(doc), backend).draw_layout(doc.modelspace(), finalize=True)
    return backend.get_string(layout.Page(0, 0, layout.Units.mm, margins=layout.Margins.all(5)))


@router.get('/grouped')
def list_grouped_layouts(q: str = '', kind: str = '', group: str = '', library: str = '', skip: int = 0, limit: int = 24, face: str = ''):
    from app.services.cad.device_families import build_families
    families = build_families(manifest()['items'])
    rows = [f for f in families if (not q or q.casefold() in (f['name'] + ' ' + f['brand']).casefold())
            and (not kind or kind == f['kind']) and (not group or group == f['group'])
            and (not face or any(v['face'] == face for v in f['views']))
            and (not library or any(library in source for source in f['sources']))]
    return {'total': len(rows), 'items': rows[max(0, skip):max(0, skip) + min(100, max(1, limit))]}


@router.get("/{asset_id}/preview")
def preview_layout(asset_id: str):
    return Response(render_layout_svg(asset_id), media_type="image/svg+xml",
                    headers={"X-Content-Type-Options": "nosniff",
                              "Cache-Control": "public, max-age=86400"})


@router.get('/{asset_id}/insert-dxf')
def insertion_dxf(asset_id: str):
    """Explode nested inserts/dimensions for portable editable insertion."""
    import io
    import ezdxf
    from ezdxf.disassemble import recursive_decompose
    from ezdxf.addons import Importer
    from app.services.cad.catalogtb_assets import insertion_source
    source = ezdxf.readfile(insertion_source(download_layout(asset_id).path))
    target = ezdxf.new('R2018')
    target.units = source.units
    importer = Importer(source, target)
    importer.import_entities(list(recursive_decompose(source.modelspace())))
    importer.finalize()
    stream = io.StringIO()
    target.write(stream)
    return Response(stream.getvalue(), media_type='application/dxf')
