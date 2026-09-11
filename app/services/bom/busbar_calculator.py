from dataclasses import dataclass
from typing import Optional, List, Any
from app.core.config import settings
from app.core.constants import (
    BUSBAR_REQUIRED_MIN_CURRENT_A,
    BUSBAR_MIN_INCOMER_CURRENT_A,
    BUSBAR_PHASE_MULTIPLIER,
    BUSBAR_DROPPER_LENGTH_PER_POLE_M,
    BUSBAR_MIN_DROPPER_LENGTH_M,
    BUSBAR_WASTE_FACTOR,
    COPPER_DENSITY_KG_PER_M_MM2,
    BUSBAR_CURRENT_DENSITY_TABLE,
    PRICE_ROUNDING_STEP_VND,
)

@dataclass
class BusbarResult:
    profile: str
    section_mm2: float
    L_main_m: float
    L_droppers_m: float
    L_total_m: float
    mass_Cu_kg: float
    unit_price: int
    spec_title: str
    phase_allocation: dict

class BusbarCalculatorService:
    @staticmethod
    def needs_busbar(in_a: float, devices: Optional[List[Any]] = None, has_busbar_mention: bool = False) -> bool:
        """
        Kiểm tra xem tủ điện có thực sự cần hệ thống đồng thanh cái (Busbar) hay không.
        - Tủ nhỏ (In < 100A, ví dụ tủ chiếu sáng LP, tủ căn hộ DB nhỏ chỉ dùng MCB/cầu lược) -> KHÔNG dùng đồng thanh cái.
        - Tủ In >= 100A hoặc dùng ACB/MCCB lớn hoặc có bản vẽ ghi rõ THANH CÁI -> BẮT BUỘC có đồng thanh cái.
        """
        if has_busbar_mention:
            return True
        if in_a >= BUSBAR_REQUIRED_MIN_CURRENT_A:
            return True
        if devices:
            for d in devices:
                cat = str(getattr(d, "category", "") or (d.get("category") if isinstance(d, dict) else "")).upper()
                d_in = float(getattr(d, "in_a", 0) or (d.get("in_a") if isinstance(d, dict) else 0) or 0)
                if "ACB" in cat:
                    return True
                if "MCCB" in cat and d_in >= BUSBAR_REQUIRED_MIN_CURRENT_A:
                    return True
        return False

    @staticmethod
    def calculate(in_a: float, enclosure_dims: dict, feeder_list: Optional[list] = None, force_calculation: bool = False) -> BusbarResult:
        """
        Tính toán quy cách và khối lượng đồng thanh cái kỹ thuật dựa trên dòng định mức In.

        Mật độ dòng điện J theo bảng BUSBAR_CURRENT_DENSITY_TABLE (A/mm²):
          In <= 400A  → J = 2.0
          In <= 1000A → J = 1.8
          In > 1000A  → J = 1.5

        Chiều dài thanh chính L_main = BUSBAR_PHASE_MULTIPLIER × W_tủ
        (3 pha L1/L2/L3 + N(100%) + PE(50%) = 4.5 × chiều rộng tủ)

        Khối lượng = L_total × S_mm² × COPPER_DENSITY_KG_PER_M_MM2 × BUSBAR_WASTE_FACTOR
        """
        in_curr = float(in_a or 0.0)
        # Nếu tủ nhỏ không cần thanh cái (dùng cầu lược/dây phân phối), không tự ý gán giá thanh cái giả
        if not force_calculation and not BusbarCalculatorService.needs_busbar(in_curr, feeder_list):
            return BusbarResult(
                profile="None",
                section_mm2=0.0,
                L_main_m=0.0,
                L_droppers_m=0.0,
                L_total_m=0.0,
                mass_Cu_kg=0.0,
                unit_price=0,
                spec_title="Không dùng thanh cái (Dùng cầu lược/dây phân phối)",
                phase_allocation={"L1": 0.0, "L2": 0.0, "L3": 0.0, "N": 0.0, "PE": 0.0}
            )

        in_a = max(BUSBAR_MIN_INCOMER_CURRENT_A, in_curr)

        # Xác định mật độ dòng điện từ bảng tra
        j = 1.5  # Mặc định cho dòng lớn
        for threshold_a, density in sorted(BUSBAR_CURRENT_DENSITY_TABLE.items(), key=lambda x: (x[0] == float("inf"), x[0])):
            if in_a <= threshold_a:
                j = density
                break

        s_cu_req = in_a / j

        # Bảng profile chuẩn công nghiệp cơ điện Việt Nam
        standard_profiles = [
            ("15x3", 45), ("20x3", 60), ("20x5", 100), ("25x5", 125), ("30x5", 150),
            ("40x5", 200), ("50x5", 250), ("60x6", 360), ("60x8", 480), ("60x10", 600),
            ("80x8", 640), ("80x10", 800), ("100x10", 1000),
            ("2x(60x10)", 1200), ("2x(80x8)", 1280), ("2x(80x10)", 1600),
            ("2x(100x10)", 2000), ("3x(100x10)", 3000)
        ]

        selected_profile = standard_profiles[0][0]
        actual_s_cu = standard_profiles[0][1]
        for name, area in standard_profiles:
            if area >= s_cu_req:
                selected_profile = name
                actual_s_cu = area
                break
        else:
            selected_profile = standard_profiles[-1][0]
            actual_s_cu = standard_profiles[-1][1]

        w_cab = float(enclosure_dims.get("W", enclosure_dims.get("width", 800))) / 1000.0
        # 3 pha L1, L2, L3 + N (100%) + PE (50%) = BUSBAR_PHASE_MULTIPLIER × chiều rộng tủ
        l_main = BUSBAR_PHASE_MULTIPLIER * w_cab

        feeders = feeder_list or []
        l_droppers = 0.0
        for f in feeders:
            poles = 3
            if isinstance(f, dict):
                poles = int(f.get("poles") or 3)
            elif hasattr(f, "poles"):
                poles = int(getattr(f, "poles", 3) or 3)
            l_droppers += poles * BUSBAR_DROPPER_LENGTH_PER_POLE_M

        l_total = l_main + max(BUSBAR_MIN_DROPPER_LENGTH_M, l_droppers)

        # Trọng lượng = L_total (m) × S_Cu (mm²) × tỷ trọng đồng × hệ số hao hụt
        mass = l_total * actual_s_cu * COPPER_DENSITY_KG_PER_M_MM2 * BUSBAR_WASTE_FACTOR
        mass_rounded = round(mass, 1)

        # Đơn giá gia công đồng đỏ mạ thiếc bọc co nhiệt (cấu hình trong settings)
        price_per_kg = settings.BUSBAR_PRICE_PER_KG
        min_price = settings.BUSBAR_MIN_PRICE
        price = int(round((mass_rounded * price_per_kg) / PRICE_ROUNDING_STEP_VND) * PRICE_ROUNDING_STEP_VND)
        # Giới hạn tối thiểu khi dùng thanh cái gia công
        price = max(min_price, price)

        spec_title = f"Đồng thanh cái mạ thiếc bọc co nhiệt (In={int(in_a)}A, Bản đồng {selected_profile}mm, KL ~{mass_rounded}kg)"

        return BusbarResult(
            profile=selected_profile,
            section_mm2=actual_s_cu,
            L_main_m=round(l_main, 2),
            L_droppers_m=round(l_droppers, 2),
            L_total_m=round(l_total, 2),
            mass_Cu_kg=mass_rounded,
            unit_price=price,
            spec_title=spec_title,
            phase_allocation={"L1": 1.0, "L2": 1.0, "L3": 1.0, "N": 1.0, "PE": 0.5}
        )
