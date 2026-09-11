from dataclasses import dataclass
from app.services.bom.enclosure_sizer import EnclosureSizerService
from app.services.bom.busbar_calculator import BusbarCalculatorService
from app.services.bom.accessory_inference import AccessoryInferenceService
from app.services.bom.labor_estimation import LaborEstimationService

from app.core.config import settings

@dataclass
class BomCalculationResponse:
    project_id: str
    enclosure: dict
    busbar: dict
    accessories: list
    labor: dict
    total_cost: float

class BomOrchestratorService:
    @staticmethod
    def calculate_full_bom(project_id: str, devices: list[dict]) -> BomCalculationResponse:
        """Điều phối toàn bộ quá trình tính toán BOM."""
        
        enclosure = EnclosureSizerService.calculate(devices)
        
        # In của incomer là thiết bị dòng lớn nhất hoặc có cờ is_incomer
        incomer_in = max([float(d.get("in_a") or 0) for d in devices if d.get("in_a")] + [0.0])
        
        busbar = BusbarCalculatorService.calculate(incomer_in, enclosure.__dict__, devices)
        
        accessories = AccessoryInferenceService.infer(devices, enclosure, busbar)
        
        labor = LaborEstimationService.estimate(enclosure, len(devices), busbar.mass_Cu_kg)
        
        # Tính toán chi phí thực tế từ kết quả của các engine kỹ thuật
        enc_price = float(enclosure.estimated_price)
        bus_price = float(busbar.unit_price)
        acc_price = sum(float(a.quantity * a.unit_price) for a in accessories)
        hourly_rate = settings.DEFAULT_LABOR_HOURLY_RATE
        labor_price = float(labor.T_total_hours) * hourly_rate
        total_cost = round(enc_price + bus_price + acc_price + labor_price, 2)
        
        return BomCalculationResponse(
            project_id=project_id,
            enclosure=enclosure.__dict__,
            busbar=busbar.__dict__,
            accessories=[a.__dict__ for a in accessories],
            labor=labor.__dict__,
            total_cost=total_cost
        )
