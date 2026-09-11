import math
from app.core.config import settings
from app.core.constants import (
    STEEL_DENSITY_G_CM3,
    FLOOR_STANDING_HEIGHT_THRESHOLD_MM,
    PRICE_ROUNDING_STEP_VND,
)
from app.services.thermal_analysis import EnclosureResult
from app.services.cad.enclosure_cad_generator import EnclosureCadGeneratorService


class EnclosureSizerService:
    @staticmethod
    def calculate(devices: list[dict]) -> EnclosureResult:
        """
        Tính toán kích thước vỏ tủ điện đồng bộ với sơ đồ CAD và bố trí thiết bị thực tế.
        Sử dụng thuật toán phân bổ Layout-Driven Sizing (ngăn tổng, ngăn nhánh, máng cáp, dự phòng 20%).
        """
        specs = EnclosureCadGeneratorService.calculate_enclosure_specs(devices)
        h_total = float(specs.get("height", 800))
        w_total = float(specs.get("width", 600))
        d_total = float(specs.get("depth", 250))
        # Dùng ENCLOSURE_DEFAULT_THICKNESS từ settings làm fallback (nhất quán toàn hệ thống)
        tole_thickness = float(specs.get("thickness", settings.ENCLOSURE_DEFAULT_THICKNESS))

        branch_rows = specs.get("branch_rows") or [[]]
        din_rail_count = max(1, len(branch_rows))

        surface_area = 2 * (h_total * w_total + h_total * d_total + w_total * d_total) / 1e6
        # Khối lượng tole = diện tích (m²) × độ dày (mm) × tỷ trọng thép (g/cm³ → kg/m²·mm)
        tole_mass = surface_area * tole_thickness * STEEL_DENSITY_G_CM3

        # Đơn giá vỏ tủ điện sơn tĩnh điện (tole + chấn gấp CNC + sơn tĩnh điện + phụ kiện vỏ)
        min_enc_price = settings.ENCLOSURE_MIN_PRICE
        tole_price_per_kg = settings.ENCLOSURE_TOLE_PRICE_PER_KG
        base_fab_fee = settings.ENCLOSURE_BASE_FABRICATION_FEE
        enc_price = max(
            min_enc_price,
            int(round((tole_mass * tole_price_per_kg + base_fab_fee) / PRICE_ROUNDING_STEP_VND) * PRICE_ROUNDING_STEP_VND)
        )

        return EnclosureResult(
            H=h_total,
            W=w_total,
            D=d_total,
            tole_thickness_mm=tole_thickness,
            tole_mass_kg=round(tole_mass, 2),
            din_rail_count=din_rail_count,
            mounting_type="floor" if h_total >= FLOOR_STANDING_HEIGHT_THRESHOLD_MM else "wall",
            estimated_price=enc_price
        )
