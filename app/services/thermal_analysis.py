from dataclasses import dataclass

@dataclass
class EnclosureResult:
    H: int
    W: int
    D: int
    tole_thickness_mm: float
    tole_mass_kg: float
    din_rail_count: int
    mounting_type: str
    estimated_price: float = 0.0

@dataclass
class ThermalResult:
    P_loss_W: float
    T_rise_K: float
    needs_forced_cooling: bool
    fan_flow_m3h: float

class ThermalAnalysisService:
    @staticmethod
    def analyze(devices: list, enclosure: EnclosureResult) -> ThermalResult:
        """Phân tích nhiệt độ và công suất tỏa nhiệt tủ điện."""
        p_loss_total = sum(d.get("heat_W", 0) * d.get("quantity", 1) for d in devices)
        
        # Diện tích bề mặt tủ (m2) - giả sử tủ đứng độc lập
        h, w, d = enclosure.H / 1000, enclosure.W / 1000, enclosure.D / 1000
        a_surface = 1.8 * h * (w + d) + 1.4 * w * d
        
        # Hệ số tản nhiệt k (W/m2.K)
        k = 5.5 
        
        t_rise = p_loss_total / (k * a_surface) if a_surface > 0 else 0
        needs_cooling = t_rise > 35
        
        # Tính lưu lượng quạt (m3/h) nếu cần: Q = P / (rho * Cp * dT) -> đơn giản hóa Q = 3.1 * P / dT
        fan_flow = (3.1 * p_loss_total / 15) if needs_cooling else 0.0
        
        return ThermalResult(
            P_loss_W=p_loss_total,
            T_rise_K=t_rise,
            needs_forced_cooling=needs_cooling,
            fan_flow_m3h=fan_flow
        )
