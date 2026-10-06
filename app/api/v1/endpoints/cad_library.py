import json
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
LIBRARY = Path(__file__).resolve().parents[4] / "data" / "device_layouts" / "ls"


def guess_view_label(width: float, height: float) -> str:
    # Kept for old callers; shape proportions cannot establish view orientation.
    return 'Hình nguồn'


def manifest():
    # The historical device_layouts folders are no longer an insertion source.
    # Only exact-model CAD from the 2026 catalog is exposed here.
    import sqlite3
    path = CATALOG_DIR / 'equipment_catalog.sqlite'
    if not path.is_file():
        return {'items': []}
    with sqlite3.connect(path) as db:
        rows = db.execute("SELECT record_json FROM equipment WHERE cad_status = 'exact_model_cad'").fetchall()
    items = []
    for row in rows:
        record = json.loads(row[0])
        dxf = record['cad'].get('dxf')
        if not dxf or not (SOURCE_ROOT / dxf['path']).is_file():
            continue
        items.append({'id': record['catalog_id'], 'catalog_id': record['catalog_id'],
                      'name': record['display_name'], 'brand': record['brand'],
                      'kind': 'device', 'group': record['category'],
                      'category': record['category'], 'library': 'equipment_library_2026',
                      'filename': dxf['path'], 'source_file': dxf['path'],
                      'source_block': record['model'], 'cad_status': 'exact_model_cad',
                      'recognition': {'face': 'unknown', 'name': record['display_name'],
                                      'brand': record['brand']}})
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
    path = LIBRARY.parent.parent / 'cad_categories/index.json'
    if path.is_file():
        return {'items': json.loads(path.read_text(encoding='utf8'))}
    counts = defaultdict(int)
    for item in manifest()['items']:
        counts[(item['kind'], item['group'])] += 1
    return {'items': [dict(kind=kind, group=group, count=count)
                      for (kind, group), count in sorted(counts.items())]}


@router.get("/{asset_id}/dxf")
def download_layout(asset_id: str):
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
    doc = ezdxf.readfile(response.path)
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
    source = ezdxf.readfile(download_layout(asset_id).path)
    target = ezdxf.new('R2018')
    target.units = source.units
    importer = Importer(source, target)
    importer.import_entities(list(recursive_decompose(source.modelspace())))
    importer.finalize()
    stream = io.StringIO()
    target.write(stream)
    return Response(stream.getvalue(), media_type='application/dxf')
