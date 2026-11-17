"""
Enclosure Fabrication Cost Engine (Khai triển và tính giá vỏ tủ điện theo chuẩn Cơ Điện Asean / Bao gia v6.0)
Calculates exact sheet metal unfolded parts, tole mass, and industrial powder-coated enclosure unit price.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
import math


@dataclass
class EnclosureFabricationResult:
    mass_kg: float
    unit_price: int
    price_per_kg: float
    surface_area_m2: float
    parts_breakdown: Dict[str, float]


class EnclosureFabricationService:
    STEEL_DENSITY_G_CM3: float = 7.85  # kg/m² per 1mm thickness
    DEFAULT_TOLE_PRICE_PER_KG: float = 40000.0  # VNĐ/kg sơn tĩnh điện công nghiệp

    @staticmethod
    def calculate(
        height_mm: float,
        width_mm: float,
        depth_mm: float,
        thickness_mm: float = 1.2,
        location: str = "Trong nhà",
        construction: str = "Tủ dựng, quây",
        door_layers: str = "1 lớp cánh",
        plinth_height_mm: float = 100.0,
        price_per_kg: Optional[float] = None,
        compartments: int = 1,
        side_panels: int = 2,
        accessories: str = "Panel",
    ) -> EnclosureFabricationResult:
        """
        Tính toán khai triển phôi tole và đơn giá vỏ tủ điện đồng bộ 1:1 với sheet 'Tính vỏ tủ (V6.0)'.
        """
        H = float(height_mm or 0)
        W = float(width_mm or 0)
        D = float(depth_mm or 0)
        t = float(thickness_mm or 1.2)
        price_kg = float(price_per_kg or EnclosureFabricationService.DEFAULT_TOLE_PRICE_PER_KG)
        plinth = float(plinth_height_mm if plinth_height_mm is not None else 100.0)
        num_comp = max(1, int(compartments or 1))

        if H <= 0 or W <= 0 or D <= 0:
            return EnclosureFabricationResult(
                mass_kg=0.0,
                unit_price=0,
                price_per_kg=price_kg,
                surface_area_m2=0.0,
                parts_breakdown={}
            )

        # Hèm tủ G11 theo chiều cao H
        if H >= 2000:
            g11 = 60
        elif H > 1500:
            g11 = 45
        elif H > 900:
            g11 = 40
        elif H > 500:
            g11 = 35
        else:
            g11 = 25

        # Mép nhỏ hèm G12
        if H >= 1000:
            g12 = 15
        elif H > 300:
            g12 = 12
        else:
            g12 = 10

        parts: Dict[str, float] = {}
        is_outdoor = "ngoài trời" in str(location).lower()
        is_frame = "khung" in str(construction).lower()
        two_doors = "2" in str(door_layers)

        if not is_frame:
            # TỦ DỰNG, QUÂY (Liền khối)
            # 1. Thành quây: 2 hông + lưng + mép gấp hèm
            d_side = max(0.0, D - 25 - 2 * t)
            w_back = max(0.0, W - 2 * t)
            x_quay = 2 * (g12 + g11 + d_side) + w_back
            y_quay = max(0.0, H - 2 * t)
            mass_quay = (x_quay / 1000.0) * (y_quay / 1000.0) * 1 * t * EnclosureFabricationService.STEEL_DENSITY_G_CM3
            parts["thanh_quay"] = mass_quay

            # 2. Tấm nóc/đáy tủ quây (2 tấm)
            x_noc_day = d_side + g11 + g12 + 1
            y_noc_day = W
            mass_noc_day = (x_noc_day / 1000.0) * (y_noc_day / 1000.0) * 2 * t * EnclosureFabricationService.STEEL_DENSITY_G_CM3
            parts["tam_noc_day"] = mass_noc_day

            if is_outdoor:
                # Mái dốc ngoài trời che nước (đua ra 50mm, mép ngược 16mm)
                x_mai = W + 60
                y_mai = D + 80
                parts["mai_doc_ngoai_troi"] = (x_mai / 1000.0) * (y_mai / 1000.0) * 1 * t * EnclosureFabricationService.STEEL_DENSITY_G_CM3

        else:
            # TỦ KHUNG MODULE GHÉP KHOANG
            # 4 cột đứng trước & sau
            x_cot = 150.0
            y_cot = max(0.0, H - 2 * t)
            parts["khung_cot_dung"] = (x_cot / 1000.0) * (y_cot / 1000.0) * (4 * num_comp) * t * EnclosureFabricationService.STEEL_DENSITY_G_CM3

            # Thanh giằng ngang nóc/đáy
            x_ngang = 120.0
            y_ngang = W / num_comp
            parts["thanh_giang_ngang"] = (x_ngang / 1000.0) * (y_ngang / 1000.0) * (4 * num_comp) * t * EnclosureFabricationService.STEEL_DENSITY_G_CM3

            # Tấm nóc + đáy
            x_nd = D
            y_nd = W / num_comp
            parts["tam_noc_day_khung"] = (x_nd / 1000.0) * (y_nd / 1000.0) * (2 * num_comp) * t * EnclosureFabricationService.STEEL_DENSITY_G_CM3

            # Ốp hông (2 bên)
            num_sides = int(side_panels if side_panels is not None else 2)
            if num_sides > 0:
                parts["op_hong"] = (D / 1000.0) * (max(0.0, H - 100) / 1000.0) * num_sides * t * EnclosureFabricationService.STEEL_DENSITY_G_CM3

            # Ốp lưng
            parts["op_lung"] = ((W / num_comp) / 1000.0) * (max(0.0, H - 100) / 1000.0) * num_comp * t * EnclosureFabricationService.STEEL_DENSITY_G_CM3

        # 3. Cánh ngoài tủ (mép bẻ 22+12 = 34mm mỗi cạnh)
        x_cngoai = (W / num_comp) - 2 * t - 2 + 34 * 2
        y_cngoai = H - 2 * t - 2 + 34 * 2
        parts["canh_ngoai"] = (x_cngoai / 1000.0) * (y_cngoai / 1000.0) * num_comp * t * EnclosureFabricationService.STEEL_DENSITY_G_CM3

        # 4. Cánh trong tủ (nếu 2 lớp cánh)
        if two_doors:
            x_ct = (W / num_comp) - 2 * (g11 + 2 * t) - 15 + 26 * 2
            y_ct = H - 2 * (g11 + 2 * t) - 15 + 26 * 2
            parts["canh_trong"] = (x_ct / 1000.0) * (y_ct / 1000.0) * num_comp * t * EnclosureFabricationService.STEEL_DENSITY_G_CM3

        # 5. Panel gá thiết bị hoặc Thanh gá
        if "thanh gá" in str(accessories).lower():
            parts["thanh_ga"] = (H / 1000.0) * 0.12 * 4 * num_comp * t * EnclosureFabricationService.STEEL_DENSITY_G_CM3
        else:
            # Panel phẳng gá thiết bị
            x_pan = (W / num_comp) - 2 * g11 - 10 + 40
            y_pan = H - 2 * g11 - 10
            parts["panel_chinh"] = (x_pan / 1000.0) * (y_pan / 1000.0) * num_comp * t * EnclosureFabricationService.STEEL_DENSITY_G_CM3

        # 6. Chân đế tủ (Plinth) nếu có
        if plinth > 0:
            x_de_w = plinth + 100
            y_de_w = W / num_comp
            x_de_d = plinth + 100
            y_de_d = max(0.0, D - 25)
            mass_de = ((x_de_w * y_de_w * 2 + x_de_d * y_de_d * 2) / 1e6) * num_comp * t * EnclosureFabricationService.STEEL_DENSITY_G_CM3
            parts["chan_de"] = mass_de

        # 7. Gá tài liệu (tủ cao >= 800mm)
        if H >= 800:
            parts["ga_tai_lieu"] = 0.0516 * num_comp * t * EnclosureFabricationService.STEEL_DENSITY_G_CM3

        total_mass = sum(parts.values())
        mass_rounded = round(total_mass, 2)

        # Tính đơn giá: Làm tròn lên 10.000 VNĐ theo đúng công thức =ROUNDUP(mass * price_kg, -4) của Excel
        raw_price = mass_rounded * price_kg
        unit_price = int(-(-raw_price // 10000) * 10000) if raw_price > 0 else 0

        # Tổng diện tích tole trải phôi (m²)
        surface_area = round(total_mass / (t * EnclosureFabricationService.STEEL_DENSITY_G_CM3), 2)

        return EnclosureFabricationResult(
            mass_kg=mass_rounded,
            unit_price=unit_price,
            price_per_kg=price_kg,
            surface_area_m2=surface_area,
            parts_breakdown={k: round(v, 3) for k, v in parts.items()}
        )
