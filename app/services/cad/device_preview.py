"""Orthographic envelopes from catalog dimensions, without invented geometry."""
import math
from html import escape


def device_views(sku, dimensions):
    dims = {}
    for key in ("w", "h", "d"):
        try:
            value = float((dimensions or {}).get(key))
            dims[key] = value if math.isfinite(value) and value > 0 else None
        except (ValueError, TypeError):
            dims[key] = None
    views = []
    for key, title, horizontal, vertical in (
        ("front", "Mặt trước", "w", "h"),
        ("side", "Mặt bên", "d", "h"),
        ("top", "Mặt trên", "w", "d"),
    ):
        w, h = dims[horizontal], dims[vertical]
        if w is None or h is None:
            views.append(dict(id=key, title=title, svg=None, status="missing_dimensions"))
            continue
        scale = min(260 / w, 190 / h)
        rw, rh = w * scale, h * scale
        x, y = (400 - rw) / 2, (280 - rh) / 2
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 320">
<rect width="400" height="320" fill="#17212e"/>
<defs><pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse"><path d="M20 0H0V20" fill="none" stroke="#263546" stroke-width=".5"/></pattern></defs>
<rect width="400" height="320" fill="url(#grid)"/>
<rect x="{x}" y="{y}" width="{rw}" height="{rh}" fill="#20394a" stroke="#6bd5ff" stroke-width="1.5"/>
<path d="M{x} {y+rh+8}v20m{rw} 0v-20M{x} {y+rh+22}h{rw}" stroke="#a7bacb" fill="none"/>
<path d="M{x+rw+8} {y}h22m0 {rh}h-22M{x+rw+24} {y}v{rh}" stroke="#a7bacb" fill="none"/>
<g fill="#dceaf5" font-family="sans-serif" font-size="12" text-anchor="middle">
<text x="200" y="{y+rh+40}">{horizontal.upper()} = {w:g} mm</text>
<text transform="translate({x+rw+42},{y+rh/2}) rotate(-90)">{vertical.upper()} = {h:g} mm</text>
<text x="200" y="22">{escape(title)}</text>
<text x="200" y="305" font-size="10">{escape(str(sku))}</text></g></svg>'''
        views.append(dict(id=key, title=title, svg=svg, status="dimension_envelope",
                          width_mm=w, height_mm=h))
    return dict(sku=sku, source="catalog_dimensions", manufacturer_drawing=False,
                note="Hình bao theo kích thước catalog; chưa có chi tiết đầu cực, lỗ gá hoặc bản vẽ nhà sản xuất khớp model.", views=views)
