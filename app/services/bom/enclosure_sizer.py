import math
from app.core.config import settings
from app.core.constants import (
    STEEL_DENSITY_G_CM3,
    FLOOR_STANDING_HEIGHT_THRESHOLD_MM,
    PRICE_ROUNDING_STEP_VND,
)
from app.services.thermal_analysis import EnclosureResult
from app.services.cad.enclosure_cad_generator import EnclosureCadGeneratorService
from app.services.bom.enclosure_fabrication_service import EnclosureFabricationService


class EnclosureSizerService:
    @staticmethod
    def calculate(devices: list[dict]) -> EnclosureResult:
        """
        Tính toán kích thước vỏ tủ điện đồng bộ với sơ đồ CAD và bố trí thiết bị thực tế.
        Sử dụng thuật toán phân bổ Layout-Driven Sizing kết hợp công thức khai triển tole Cơ Điện Asean (Bao gia v6.0).
        """
        specs = EnclosureCadGeneratorService.calculate_enclosure_specs(devices)
        h_total = float(specs.get("height", 800))
        w_total = float(specs.get("width", 600))
        d_total = float(specs.get("depth", 250))
        tole_thickness = float(specs.get("thickness", settings.ENCLOSURE_DEFAULT_THICKNESS))

        branch_rows = specs.get("branch_rows") or [[]]
        din_rail_count = max(1, len(branch_rows))

        # Khai triển tole và tính giá vỏ tủ trực tiếp theo chuẩn kỹ thuật
        fab_res = EnclosureFabricationService.calculate(
            height_mm=h_total,
            width_mm=w_total,
            depth_mm=d_total,
            thickness_mm=tole_thickness,
            location=specs.get("location", "Trong nhà"),
            construction=specs.get("construction", "Tủ dựng, quây"),
            door_layers=f"{specs.get('door_layers', 1)} lớp cánh",
            plinth_height_mm=specs.get("plinth_height", 100),
            price_per_kg=settings.ENCLOSURE_TOLE_PRICE_PER_KG
        )

        min_enc_price = settings.ENCLOSURE_MIN_PRICE
        enc_price = max(min_enc_price, fab_res.unit_price)

        return EnclosureResult(
            H=h_total,
            W=w_total,
            D=d_total,
            tole_thickness_mm=tole_thickness,
            tole_mass_kg=fab_res.mass_kg,
            din_rail_count=din_rail_count,
            mounting_type="floor" if h_total >= FLOOR_STANDING_HEIGHT_THRESHOLD_MM else "wall",
            estimated_price=enc_price
        )
