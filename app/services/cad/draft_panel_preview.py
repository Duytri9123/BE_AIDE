"""Compatibility entry point: require actual selected CAD, never fake device boxes."""
from app.services.cad.reference_panel_layout import generate


def generate_tdt_preview(devices, output_dir):
    selected = [dict(d) for d in devices if d.get("panel_code") == "TĐT"]
    if not selected or any(not (d.get("cad") or {}).get("asset_id") for d in selected):
        raise ValueError("Cần chọn CAD thực tế cho thiết bị; không thay bằng ô ký hiệu giả")
    return generate(selected, (1000, 600, 300), output_dir)
