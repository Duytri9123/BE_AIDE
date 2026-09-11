from typing import Union
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.config import settings
from app.models.conversation_session import ConversationSession
from app.models.analysis_iteration import AnalysisIteration
from app.schemas.bom import (
    BomCalculateRequest,
    BomCalculationResponse,
    EnclosureResultSchema,
    BusbarResultSchema,
    AccessoryItemSchema,
    LaborResultSchema,
)
from app.services.bom.bom_orchestrator import BomOrchestratorService
from app.services.bom.enclosure_sizer import EnclosureSizerService
from app.services.topology.circuit_graph import CircuitGraphService

router = APIRouter()

@router.post("/calculate", response_model=BomCalculationResponse)
async def calculate_bom(request: BomCalculateRequest):
    """Tính toán toàn bộ BOM tủ điện (vỏ tủ, thanh cái đồng, phụ kiện và nhân công)."""
    raw_res = BomOrchestratorService.calculate_full_bom(
        project_id=str(request.project_id),
        devices=request.devices
    )

    enc = raw_res.enclosure
    enc_price = float(enc.get("estimated_price", 0))
    enclosure_obj = EnclosureResultSchema(
        H=float(enc.get("H", 0)),
        W=float(enc.get("W", 0)),
        D=float(enc.get("D", 0)),
        tole_thickness_mm=float(enc.get("tole_thickness_mm", settings.ENCLOSURE_DEFAULT_THICKNESS)),
        tole_mass_kg=float(enc.get("tole_mass_kg", 0)),
        din_rail_count=int(enc.get("din_rail_count", 1)),
        estimated_price=enc_price,
    )

    bus = raw_res.busbar
    busbar_cost = float(bus.get("unit_price", 0))
    busbar_obj = BusbarResultSchema(
        profile=str(bus.get("profile", "Standard")),
        section_mm2=float(bus.get("section_mm2", 0)),
        L_total_m=float(bus.get("L_total_m", 0)),
        mass_Cu_kg=float(bus.get("mass_Cu_kg", 0)),
        unit_price=busbar_cost,
        phase_allocation=bus.get("phase_allocation") or {},
    )

    accessories_list = []
    acc_cost = 0.0
    for a in raw_res.accessories:
        qty = float(a.get("quantity", 1))
        u_p = float(a.get("unit_price", 0))
        acc_cost += qty * u_p
        accessories_list.append(
            AccessoryItemSchema(
                category=str(a.get("category", "")),
                name=str(a.get("name", "")),
                spec=str(a.get("spec", "")),
                unit=str(a.get("unit", "Cái")),
                quantity=qty,
                unit_price=u_p,
            )
        )

    lab = raw_res.labor
    labor_breakdown = {
        "mechanical_hours": lab.get("T_mechanical", 0),
        "mounting_hours": lab.get("T_mounting", 0),
        "busbar_hours": lab.get("T_busbar", 0),
        "wiring_hours": lab.get("T_wiring", 0),
        "testing_hours": lab.get("T_testing", 0),
    }
    t_hours = float(lab.get("T_total_hours", 0))
    labor_obj = LaborResultSchema(
        T_total_hours=t_hours,
        estimated_days=float(lab.get("estimated_days", round(t_hours / settings.WORK_HOURS_PER_DAY, 1))),
        breakdown=labor_breakdown,
    )

    hourly_rate = settings.DEFAULT_LABOR_HOURLY_RATE
    total_labor = t_hours * hourly_rate

    return BomCalculationResponse(
        enclosure=enclosure_obj,
        busbar=busbar_obj,
        accessories=accessories_list,
        labor=labor_obj,
        total_material_cost=round(enc_price + busbar_cost + acc_cost, 2),
        total_labor_cost=round(total_labor, 2),
    )

async def _fetch_project_devices(project_id: Union[int, str, UUID], db: AsyncSession) -> list:
    devices = []
    try:
        proj_id_int = int(str(project_id))
        sess_stmt = select(ConversationSession).where(
            ConversationSession.project_id == proj_id_int
        ).order_by(ConversationSession.created_at.desc())
        sess_res = await db.execute(sess_stmt)
        session = sess_res.scalars().first()
        if session:
            iter_stmt = select(AnalysisIteration).where(
                AnalysisIteration.session_id == session.id
            ).order_by(AnalysisIteration.iteration_number.desc())
            iter_res = await db.execute(iter_stmt)
            latest_iter = iter_res.scalars().first()
            if latest_iter and latest_iter.ai_parsed_devices:
                devices = latest_iter.ai_parsed_devices
    except Exception:
        pass
    return devices

@router.get("/topology/{project_id}")
async def get_topology(project_id: Union[int, str, UUID], db: AsyncSession = Depends(get_db)):
    """Lấy sơ đồ phân cấp mạch điện (topology graph) dạng JSON từ thiết bị bóc tách."""
    devices = await _fetch_project_devices(project_id, db)
    graph = CircuitGraphService.build_graph(devices)
    return CircuitGraphService.to_json(graph)

@router.get("/enclosure-preview/{project_id}")
async def get_enclosure_preview(project_id: Union[int, str, UUID], db: AsyncSession = Depends(get_db)):
    """Lấy thông số kích thước vỏ tủ điện (H, W, D, tole) tính toán theo thiết bị dự án."""
    devices = await _fetch_project_devices(project_id, db)
    enc = EnclosureSizerService.calculate(devices)
    return {
        "H": enc.H,
        "W": enc.W,
        "D": enc.D,
        "tole_thickness_mm": enc.tole_thickness_mm,
        "tole_mass_kg": enc.tole_mass_kg,
        "din_rail_count": enc.din_rail_count,
        "mounting_type": enc.mounting_type,
        "estimated_price": enc.estimated_price,
    }
