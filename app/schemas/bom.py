from pydantic import BaseModel
from typing import List, Optional, Union
from uuid import UUID

class BomCalculateRequest(BaseModel):
    project_id: Union[int, str, UUID]
    devices: List[dict]

class EnclosureResultSchema(BaseModel):
    H: float
    W: float
    D: float
    tole_thickness_mm: float
    tole_mass_kg: float
    din_rail_count: int
    estimated_price: float = 0.0

class BusbarResultSchema(BaseModel):
    profile: str
    section_mm2: float
    L_total_m: float
    mass_Cu_kg: float
    unit_price: float = 0.0
    phase_allocation: dict

class AccessoryItemSchema(BaseModel):
    category: str
    name: str
    spec: str
    unit: str
    quantity: float
    unit_price: float

class LaborResultSchema(BaseModel):
    T_total_hours: float
    estimated_days: float
    breakdown: dict

class BomCalculationResponse(BaseModel):
    enclosure: EnclosureResultSchema
    busbar: BusbarResultSchema
    accessories: List[AccessoryItemSchema]
    labor: LaborResultSchema
    total_material_cost: float
    total_labor_cost: float
