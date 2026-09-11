from dataclasses import dataclass
from app.services.bom.enclosure_sizer import EnclosureResult
from app.services.bom.busbar_calculator import BusbarResult


@dataclass
class AccessoryItem:
    category: str
    name: str
    spec: str
    unit: str
    quantity: int
    unit_price: float
    note: str


class AccessoryInferenceService:
    @staticmethod
    def infer(devices: list[dict], enclosure: EnclosureResult, busbar: BusbarResult) -> list[AccessoryItem]:
        """Do not invent accessories or prices outside the catalog/source drawing."""
        return []
