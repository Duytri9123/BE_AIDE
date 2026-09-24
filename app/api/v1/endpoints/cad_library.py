import json
from pathlib import Path
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.responses import Response
from functools import lru_cache
from app.api.deps import get_current_active_user
from app.services.cad.library_taxonomy import classify, explicit_brands

router = APIRouter(dependencies=[Depends(get_current_active_user)])
LIBRARY = Path(__file__).resolve().parents[4] / "data" / "device_layouts" / "ls"


def guess_view_label(width: float, height: float) -> str:
    # Kept for old callers; shape proportions cannot establish view orientation.
    return 'Hình nguồn'


def manifest():
    paths = sorted(LIBRARY.parent.glob('*/manifest.json'))
    signature = tuple((str(path), path.stat().st_mtime_ns, path.stat().st_size) for path in paths)
    from app.services.cad.recognition import DATA
    return _manifest_cached(signature, DATA.stat().st_mtime_ns if DATA.exists() else 0)


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
    """Resolve legacy CAD SKUs as well as explicit links; never infer from size."""
    items = items if items is not None else manifest()["items"]
    asset_id = ((parameters or {}).get("cad") or {}).get("asset_id")
    if not asset_id and (sku or "").startswith("CAD:"):
        asset_id = sku[4:]
    asset = next((item for item in items if item["id"] == asset_id), None)
    if asset and (LIBRARY.parent / asset["library"] / asset["filename"]).is_file():
        return asset
    return None


@router.get("")
def list_layouts(q: str = "", brand: str = "", kind: str = "", group: str = ""):
    return {"items": [item for item in manifest()["items"]
                      if q.casefold() in (item["name"] + " " + item.get("brand", "")).casefold()
                      and (not brand or item.get("brand") == brand)
                      and (not kind or item['kind'] == kind)
                      and (not group or item['group'] == group)]}


@router.get("/{asset_id}/dxf")
def download_layout(asset_id: str):
    item = next((item for item in manifest()["items"] if item["id"] == asset_id), None)
    if not item:
        raise HTTPException(404, "Không tìm thấy hình thiết bị")
    directory = (LIBRARY.parent / item["library"]).resolve()
    path = (directory / item["filename"]).resolve()
    if directory.parent != LIBRARY.parent.resolve() or path.parent != directory or not path.is_file():
        raise HTTPException(404, "Không tìm thấy file DXF")
    return FileResponse(path, filename=f"{item['library']}_{asset_id}.dxf", media_type="application/dxf")


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
