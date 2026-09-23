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
    """Đoán tên mặt nhìn dựa trên tỷ lệ kích thước."""
    if width <= 0 or height <= 0:
        return "Hình chiếu"
    ratio = height / width
    if ratio >= 2.5:
        return "Mặt đứng"
    if ratio >= 1.4:
        return "Mặt trước"
    if ratio <= 0.4:
        return "Mặt ngang"
    if 0.8 <= ratio <= 1.25:
        return "Mặt cắt ngang"
    return "Hình chiếu"


def manifest():
    items = []
    for path in sorted(LIBRARY.parent.glob("*/manifest.json")):
        for entry in json.loads(path.read_text(encoding="utf-8"))["items"]:
            brands = explicit_brands(entry.get('category', '') + ' ' + entry['name'])
            items.append({**entry, "library": path.parent.name,
                          **classify(entry['name'], entry.get('category', '')),
                          "brand": brands[0] if len(brands) == 1 else entry.get('brand', 'Chưa xác định hãng'),
                          "brands_in_source": brands,
                          "is_collection": path.parent.name == 'source_cells'})
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


@router.get("/grouped")
def list_grouped_layouts(q: str = "", kind: str = "", group: str = "", library: str = ""):
    """Trả về danh sách thiết bị CAD đã gom nhóm theo parent_asset_id.
    Mỗi nhóm thiết bị có thumbnail_id (mặt đầu tiên) để hiển thị preview trên card.
    """
    all_items = manifest()["items"]

    # Lọc theo query
    if q:
        q_lower = q.casefold()
        all_items = [i for i in all_items
                     if q_lower in (i["name"] + " " + i.get("brand", "") + " " + i.get("category", "")).casefold()]
    if kind:
        all_items = [i for i in all_items if i.get("kind") == kind]
    if group:
        all_items = [i for i in all_items if i.get("group") == group]
    if library:
        all_items = [i for i in all_items if i.get("library") == library]

    # Gom nhóm theo parent_asset_id; item không có parent_asset_id thì tự thành group riêng
    groups: dict = defaultdict(list)
    for item in all_items:
        gid = item.get("parent_asset_id") or item["id"]
        groups[gid].append(item)

    result = []
    for gid, members in groups.items():
        # Dùng category của member đầu làm tên nhóm; fallback = name của member đầu
        first = members[0]
        group_name = first.get("category") or first["name"]
        # Bỏ phần " · biến thể" trong tên nếu có (vd: "Đèn báo pha · mẫu 1" → "Đèn báo pha")
        if " · " in group_name:
            group_name = group_name.split(" · ")[0].strip()

        # Sắp xếp views: ưu tiên mặt đứng (ratio cao) lên trước
        def sort_key(m):
            w, h = m.get("width", 1) or 1, m.get("height", 1) or 1
            return -(h / w)  # ratio cao nhất lên đầu (mặt đứng)

        members_sorted = sorted(members, key=sort_key)

        views = []
        for m in members_sorted:
            w, h = m.get("width", 0) or 0, m.get("height", 0) or 0
            views.append({
                "id": m["id"],
                "name": m["name"],
                "view_label": guess_view_label(w, h),
                "source_block": m.get("source_block", ""),
                "source_file": m.get("source_file", ""),
                "width": w,
                "height": h,
                "units": m.get("units", "mm"),
                "library": m.get("library", ""),
            })

        result.append({
            "group_id": gid,
            "name": group_name,
            "category": first.get("category", ""),
            "brand": first.get("brand", "Chưa xác định hãng"),
            "kind": first.get("kind", "unclassified"),
            "group": first.get("group", "Chưa phân loại"),
            "library": first.get("library", ""),
            "thumbnail_id": members_sorted[0]["id"],  # mặt đứng nhất → thumbnail
            "view_count": len(members),
            "views": views,
        })

    # Sắp xếp theo kind rồi group rồi name
    result.sort(key=lambda x: (x["kind"], x["group"], x["name"]))
    return {"total": len(result), "items": result}


@router.get("/{asset_id}/preview")
def preview_layout(asset_id: str):
    return Response(render_layout_svg(asset_id), media_type="image/svg+xml",
                    headers={"X-Content-Type-Options": "nosniff",
                              "Cache-Control": "public, max-age=86400"})
