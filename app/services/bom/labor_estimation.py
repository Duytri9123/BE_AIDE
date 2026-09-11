from dataclasses import dataclass
from app.core.config import settings
from app.services.bom.enclosure_sizer import EnclosureResult


@dataclass
class LaborResult:
    T_mechanical: float
    T_mounting: float
    T_busbar: float
    T_wiring: float
    T_testing: float
    T_total_hours: float
    estimated_days: float


class LaborEstimationService:
    @staticmethod
    def estimate(enclosure: EnclosureResult, device_count: int, busbar_mass: float) -> LaborResult:
        """Ước tính nhân công gia công và lắp ráp tủ điện.

        Tất cả hệ số nhân công có thể cấu hình qua .env:
          LABOR_RATE_SHEET_METAL_H_PER_M2  — giờ/m² tole
          LABOR_RATE_MOUNTING_H_PER_DEVICE — giờ/thiết bị lắp đặt
          LABOR_RATE_BUSBAR_H_PER_KG       — giờ/kg đồng gia công
          LABOR_RATE_WIRING_H_PER_DEVICE   — giờ/thiết bị đấu nối
          LABOR_RATE_TESTING_H_PER_DEVICE  — giờ/thiết bị kiểm tra
          LABOR_TESTING_BASE_HOURS         — giờ base kiểm tra xuất xưởng
          WORK_HOURS_PER_DAY               — số giờ/ngày công
        """
        h, w, d = enclosure.H / 1000, enclosure.W / 1000, enclosure.D / 1000
        surface_area = 2 * (h * w + h * d + w * d)

        t_mechanical = surface_area * settings.LABOR_RATE_SHEET_METAL_H_PER_M2
        t_mounting   = device_count * settings.LABOR_RATE_MOUNTING_H_PER_DEVICE
        t_busbar     = busbar_mass  * settings.LABOR_RATE_BUSBAR_H_PER_KG
        t_wiring     = device_count * settings.LABOR_RATE_WIRING_H_PER_DEVICE
        t_testing    = device_count * settings.LABOR_RATE_TESTING_H_PER_DEVICE + settings.LABOR_TESTING_BASE_HOURS

        t_total = t_mechanical + t_mounting + t_busbar + t_wiring + t_testing
        days = round(t_total / settings.WORK_HOURS_PER_DAY, 1)

        return LaborResult(
            T_mechanical=round(t_mechanical, 1),
            T_mounting=round(t_mounting, 1),
            T_busbar=round(t_busbar, 1),
            T_wiring=round(t_wiring, 1),
            T_testing=round(t_testing, 1),
            T_total_hours=round(t_total, 1),
            estimated_days=days
        )
