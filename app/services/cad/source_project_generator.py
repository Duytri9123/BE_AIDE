"""Select and save a complete, traceable cabinet form from the CAD library."""
from __future__ import annotations

from pathlib import Path

from app.services.cad import cabinet_templates


class SourceProjectGenerator:
    @staticmethod
    def generate(project_id: int, output_dir: str, dimensions, kind: str = "", product_name: str = "") -> dict:
        if not dimensions or len(dimensions) != 3:
            raise ValueError("Chưa có kích thước tủ H×W×D được xác định từ bản vẽ hoặc người dùng.")
        height, width, depth = (float(value) for value in dimensions)
        requested = {"height": height, "width": width, "depth": depth}
        if any(value <= 0 for value in requested.values()):
            raise ValueError("Kích thước tủ phải lớn hơn 0.")
        if height >= 1800 and width < height / 3:
            raise ValueError("Tủ đứng quá hẹp so với chiều cao; cần kiểm tra lại kích thước và bố trí thiết bị.")
        matches = cabinet_templates.candidates(requested, kind=kind)
        match = next((item for item in matches if item["can_generate"]), None)
        if not match:
            raise ValueError("Không có form CAD nguồn đủ mốc co giãn cho kích thước/loại tủ này; cần chọn form thủ công.")
        dxf = cabinet_templates.generate(match["id"], requested, product_name=product_name)
        folder = Path(output_dir) / str(project_id) / "cad" / "cabinet_forms"
        folder.mkdir(parents=True, exist_ok=True)
        filename = f"FormTu_{match['id']}_H{height:g}W{width:g}D{depth:g}.dxf"
        path = folder / filename
        path.write_text(dxf, encoding="utf-8")
        return {"path": str(path), "template_id": match["id"], "source": match["filename"]}
