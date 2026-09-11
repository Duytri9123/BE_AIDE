import os
import re
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.ai_connection import AiConnection
from app.schemas.ai import (
    ChatRequest,
    ChatResponse,
    CadMacroBlockSchema,
    ExtractedDeviceSchema
)
from app.services.device_catalog_engine import DeviceCatalogEngine
from app.services.cad.enclosure_cad_generator import EnclosureCadGeneratorService
from app.services.export.quotation_exporter import QuotationExporterService
from app.services.ingestion.pdf_drawing_indexer import PdfDrawingIndexerService
from app.core.config import settings

router = APIRouter()

def parse_electrical_intent(message: str, current_devices: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Phân tích câu lệnh kỹ thuật điện của người dùng để sinh hoặc cập nhật danh sách thiết bị.
    Hỗ trợ cả thiết kế mới toàn diện và thêm/bớt/sửa thiết bị.
    """
    msg = message.lower()
    updated_devices = list(current_devices) if current_devices else []
    action_type = "macro_draft"
    explanation = []

    # 1. Phát hiện thiết kế tủ mới từ đầu (MSB, DB, ATS, Tủ bơm...)
    is_new_design = any(k in msg for k in ["thiết kế tủ", "tạo tủ", "vẽ tủ", "tủ mới", "tủ msb", "tủ db", "tủ ats", "tủ điện"])
    
    if is_new_design or not updated_devices:
        updated_devices = []
        # Incomer Rating
        incomer_rating = int(settings.DEFAULT_INCOMER_RATING or 630)
        inc_match = re.search(r'(\d+)\s*a', msg)
        if inc_match:
            incomer_rating = int(inc_match.group(1))
        elif "1000" in msg:
            incomer_rating = 1000
        elif "800" in msg:
            incomer_rating = 800
        elif "400" in msg:
            incomer_rating = 400
        elif "250" in msg:
            incomer_rating = 250
        elif "100" in msg:
            incomer_rating = 100

        # Incomer Breaker
        inc_cat = "ACB" if incomer_rating >= 1000 else "MCCB"
        updated_devices.append({
            "category": inc_cat,
            "name": f"{inc_cat} Tổng {incomer_rating}A 3P",
            "spec": f"3P - {incomer_rating}A - 45kA",
            "in_a": float(incomer_rating),
            "icu_ka": 45.0 if incomer_rating >= 400 else 30.0,
            "poles": 3,
            "quantity": 1,
            "brand": "",
            "part_number": "",
            "section": "Đầu vào",
            "confidence": settings.DEFAULT_CONFIDENCE
        })

        # Đo lường & đèn báo
        updated_devices.append({
            "category": "METER",
            "name": "Đồng hồ đa năng MFM hiển thị số (V, A, Hz, CosPhi, kWh)",
            "spec": "Màn hình LCD 3 pha - Class 0.5",
            "quantity": 1,
            "brand": "",
            "part_number": "",
            "section": "Đo lường & Giám sát",
            "confidence": settings.DEFAULT_CONFIDENCE
        })
        updated_devices.append({
            "category": "LIGHT",
            "name": "Bộ 3 đèn báo pha LED R-S-T (Đỏ, Vàng, Xanh)",
            "spec": "Phi 22 - 220VAC",
            "quantity": 3,
            "brand": "",
            "part_number": "",
            "section": "Đo lường & Giám sát",
            "confidence": settings.DEFAULT_CONFIDENCE
        })

        # Lộ nhánh mặc định theo công suất tủ
        if incomer_rating >= 630:
            updated_devices.append({
                "category": "MCCB",
                "name": "MCCB 3P 250A 30kA Phân phối",
                "spec": "3P - 250A - 30kA",
                "in_a": 250.0,
                "icu_ka": 30.0,
                "poles": 3,
                "quantity": 3,
                "brand": "",
                "part_number": "",
                "section": "Đầu ra",
                "confidence": 0.94
            })
            updated_devices.append({
                "category": "MCCB",
                "name": "MCCB 3P 100A 18kA Phân phối",
                "spec": "3P - 100A - 18kA",
                "in_a": 100.0,
                "icu_ka": 18.0,
                "poles": 3,
                "quantity": 4,
                "brand": "",
                "part_number": "",
                "section": "Đầu ra",
                "confidence": 0.94
            })
            updated_devices.append({
                "category": "MCB",
                "name": "MCB 1P 20A 6kA Chiếu sáng & Ổ cắm",
                "spec": "1P - 20A - 6kA",
                "in_a": 20.0,
                "icu_ka": 6.0,
                "poles": 1,
                "quantity": 6,
                "brand": "",
                "part_number": "",
                "section": "Đầu ra",
                "confidence": 0.92
            })
        else:
            updated_devices.append({
                "category": "MCCB",
                "name": "MCCB 3P 100A 18kA Phân phối",
                "spec": "3P - 100A - 18kA",
                "in_a": 100.0,
                "icu_ka": 18.0,
                "poles": 3,
                "quantity": 3,
                "brand": "",
                "part_number": "",
                "section": "Đầu ra",
                "confidence": 0.94
            })
            updated_devices.append({
                "category": "MCB",
                "name": "MCB 3P 32A 6kA Phụ tải",
                "spec": "3P - 32A - 6kA",
                "in_a": 32.0,
                "icu_ka": 6.0,
                "poles": 3,
                "quantity": 4,
                "brand": "",
                "part_number": "",
                "section": "Đầu ra",
                "confidence": 0.92
            })

        # Quạt hút & cảm biến nhiệt độ
        updated_devices.append({
            "category": "COOLING",
            "name": "Quạt hút thông gió tủ điện gắn nóc/hông",
            "spec": "220VAC - Kèm lưới lọc bụi",
            "quantity": 2,
            "brand": "",
            "part_number": "",
            "section": "Làm mát cho ngăn tủ",
            "confidence": 0.95
        })
        updated_devices.append({
            "category": "COOLING",
            "name": "Bộ điều khiển nhiệt độ tủ điện (Thermostat)",
            "spec": "0-60°C - Tiếp điểm 10A",
            "quantity": 1,
            "brand": "",
            "part_number": "",
            "section": "Làm mát cho ngăn tủ",
            "confidence": 0.95
        })

        explanation.append(f"⚡ Đã thiết kế hoàn chỉnh hệ thống **Tủ Điện {incomer_rating}A**.")
        explanation.append(f"🔹 Aptomat tổng Incomer: **{inc_cat} 3P {incomer_rating}A**.")
        explanation.append(f"🔹 Hệ thống đo lường & bảo vệ: Đồng hồ đa năng MFM, 3 đèn báo pha LED R-S-T.")
        explanation.append(f"🔹 Xuất tuyến phân phối: Gồm các lộ MCCB và MCB phân tầng tối ưu không gian lắp ráp.")
    else:
        # 2. Xử lý câu lệnh thêm thiết bị cụ thể (Increment)
        mccb_add = re.search(r'thêm\s*(\d+)?\s*(mccb|aptomat|cb)\s*(\d+)?a?', msg)
        mcb_add = re.search(r'thêm\s*(\d+)?\s*(mcb)\s*(\d+)?a?', msg)
        
        qty = 2
        rating = 100
        if mccb_add:
            qty_str = mccb_add.group(1)
            rating_str = mccb_add.group(3)
            qty = int(qty_str) if qty_str else 2
            rating = int(rating_str) if rating_str else 100
            
            updated_devices.append({
                "category": "MCCB",
                "name": f"MCCB 3P {rating}A Phân phối nhánh",
                "spec": f"3P - {rating}A - 30kA",
                "in_a": float(rating),
                "icu_ka": 30.0,
                "poles": 3,
                "quantity": qty,
                "brand": "",
                "part_number": "",
                "section": "Đầu ra",
                "confidence": 0.96
            })
            explanation.append(f"➕ Đã thêm **{qty}x MCCB 3P {rating}A** vào ngăn phân phối nhánh.")
            action_type = "update_devices"
        elif mcb_add:
            qty_str = mcb_add.group(1)
            rating_str = mcb_add.group(3)
            qty = int(qty_str) if qty_str else 4
            rating = int(rating_str) if rating_str else 20
            
            updated_devices.append({
                "category": "MCB",
                "name": f"MCB 1P {rating}A 6kA Chiếu sáng",
                "spec": f"1P - {rating}A - 6kA",
                "in_a": float(rating),
                "icu_ka": 6.0,
                "poles": 1,
                "quantity": qty,
                "brand": "",
                "part_number": "",
                "section": "Đầu ra",
                "confidence": 0.95
            })
            explanation.append(f"➕ Đã thêm **{qty}x MCB 1P {rating}A** trên thanh DIN-Rail.")
            action_type = "update_devices"
        else:
            explanation.append(f"💡 Đã ghi nhận yêu cầu và tối ưu lại sơ đồ bố trí không gian tủ điện.")

    return {
        "devices": updated_devices,
        "action_type": action_type,
        "explanation": "\n\n".join(explanation)
    }

def generate_macro_blocks(enclosure_spec: Dict[str, Any], devices: List[Dict[str, Any]]) -> List[CadMacroBlockSchema]:
    """
    Sinh danh sách các Macro Blocks đồ họa cấp cao cho CAD Canvas và AutoCAD Commands.
    """
    H = enclosure_spec.get("height", 1700)
    W = enclosure_spec.get("width", 700)
    plinth = enclosure_spec.get("plinth_height", settings.ENCLOSURE_DEFAULT_PLINTH_HEIGHT)
    incomer_a = enclosure_spec.get("incomer_rating", settings.DEFAULT_INCOMER_RATING or 630)

    blocks: List[CadMacroBlockSchema] = []

    # 1. Macro Block: Khung vỏ tủ & Đế tủ
    blocks.append(CadMacroBlockSchema(
        id="mb-enclosure",
        type="ENCLOSURE_BODY",
        name=f"Vỏ tủ & Đế đỡ {plinth}mm",
        layer="0_ENCLOSURE",
        command_line=f"_RECTANGLE 0,0 {W},{H} -> Khung tủ điện 2 lớp cánh H{H}xW{W}xD600 kèm đế {plinth}mm",
        bounds={"x": 0, "y": 0, "w": W, "h": H},
        metadata={"thickness": settings.ENCLOSURE_DEFAULT_THICKNESS, "plinth": plinth, "ip_rating": "IP54"}
    ))

    # 2. Macro Block: Ngăn thanh cái đồng chính (Cu Busbar)
    busbar_cu = int(incomer_a / 2)
    blocks.append(CadMacroBlockSchema(
        id="mb-busbar",
        type="BUSBAR_SYSTEM",
        name=f"Hệ thanh cái đồng {incomer_a}A (R-S-T-N)",
        layer="0_BUSBAR",
        command_line=f"_BUSBAR 4P {incomer_a}A Cu {busbar_cu}mm² N=50% -> Kéo 4 thanh cái đồng đỏ",
        bounds={"x": 35, "y": 140, "w": W - 70, "h": 220},
        metadata={"rating": incomer_a, "cu_area": busbar_cu, "phases": ["R", "S", "T", "N"]}
    ))

    # 3. Macro Block: Ngăn Incomer đầu vào
    blocks.append(CadMacroBlockSchema(
        id="mb-incomer",
        type="INCOMER_UNIT",
        name=f"Khối Incomer {incomer_a}A & 3 Đèn pha",
        layer="0_DEVICES",
        command_line=f"_INSERT INCOMER_{incomer_a}A_3P -> Bố trí MCCB tổng và 3 đèn báo pha R-S-T",
        bounds={"x": (W - 240) / 2, "y": 380, "w": 240, "h": 210},
        metadata={"rating": incomer_a, "icu_ka": 45, "part_number": f"ABN {incomer_a}C"}
    ))

    # 4. Macro Block: Dãy phân phối nhánh Feeder Rails
    feeder_devs = [d for d in devices if d.get("category") in ["MCCB", "MCB", "CONTACTOR"] and float(d.get("in_a") or 0) < incomer_a]
    blocks.append(CadMacroBlockSchema(
        id="mb-feeders",
        type="FEEDER_ROW",
        name=f"Dãy xuất tuyến phân phối ({len(feeder_devs)} lộ)",
        layer="0_DEVICES",
        command_line=f"_ARRAY Feeder Breakers -> Gắn 3 dãy DIN-rail và bố trí các lộ nhánh MCCB/MCB",
        bounds={"x": 40, "y": 620, "w": W - 80, "h": 500},
        metadata={"feeder_count": len(feeder_devs)}
    ))

    # 5. Macro Block: Đo lường & Làm mát
    blocks.append(CadMacroBlockSchema(
        id="mb-accessories",
        type="ACCESSORY_PANEL",
        name="Đo lường MFM & Làm mát Rack",
        layer="0_DEVICES",
        command_line=f"_INSERT MFM383A + 2x FAN 220V -> Đồng hồ đa năng và cụm quạt hút giải nhiệt",
        bounds={"x": 50, "y": 1150, "w": W - 100, "h": 120},
        metadata={"cooling": "2x 220V", "meter": "MFM383A"}
    ))

    # 6. Macro Block: Kích thước & Khung tên
    blocks.append(CadMacroBlockSchema(
        id="mb-titleblock",
        type="TITLEBLOCK",
        name="Khung tên kỹ thuật & Dim kích thước",
        layer="0_TITLEBLOCK",
        command_line=f"_DIMLINEAR H{H}xW{W} & _TITLEBLOCK -> Đóng khung tên bản vẽ kỹ thuật",
        bounds={"x": W - 280, "y": H - 160, "w": 260, "h": 140},
        metadata={"dimensions": f"H{H}xW{W}xD600"}
    ))

    return blocks

@router.post("/", response_model=ChatResponse)
async def chat_with_cad_agent(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    CAD AI Agent Orchestrator (Kiến trúc Hybrid BE + Macro Blocks).
    Tự động suy luận thiết kế, tra cứu Catalog SKU, sinh Macro CAD Blocks và đồng bộ bảng Báo giá BOM.
    """
    # 1. Lấy thông tin dự án
    proj_stmt = select(Project).where(Project.id == request.project_id)
    proj_res = await db.execute(proj_stmt)
    project = proj_res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Dự án không tồn tại")

    # 2. Kiểm tra nếu người dùng hỏi về danh sách / các trang có tủ điện trong bản vẽ
    if PdfDrawingIndexerService.detect_panel_query_intent(request.message):
        pdf_file_stmt = select(ProjectFile).where(
            ProjectFile.project_id == request.project_id,
            ProjectFile.filename.ilike("%.pdf")
        ).order_by(ProjectFile.id.desc())
        pdf_file_res = await db.execute(pdf_file_stmt)
        pdf_file = pdf_file_res.scalars().first()
        if pdf_file and pdf_file.file_path and os.path.exists(pdf_file.file_path):
            idx_res = PdfDrawingIndexerService.index_pdf(pdf_file.file_path)
            if idx_res.get("has_text_layer"):
                return ChatResponse(
                    reply=idx_res["report_markdown"],
                    action_type="query_drawings",
                    devices=request.current_devices or [],
                    enclosure_specs={},
                    cad_macro_blocks=[]
                )

    # 3. Phân tích lệnh kỹ thuật của người dùng
    intent = parse_electrical_intent(request.message, request.current_devices or [])
    devices_raw = intent["devices"]
    action_type = intent["action_type"]
    reply_text = intent["explanation"]

    # 3. Khớp SKU và đơn giá từ DeviceCatalogEngine trên Backend
    eng = DeviceCatalogEngine.get_instance()
    extracted_devices: List[ExtractedDeviceSchema] = []
    
    for dev in devices_raw:
        cat = dev.get("category", "MCCB")
        poles = dev.get("poles", 3)
        in_a = dev.get("in_a", 100.0)
        p_num = dev.get("part_number")

        info = eng.lookup_device_info(
            category=cat,
            in_a=in_a,
            poles=poles,
            brand=dev.get("brand"),
            part_number=p_num,
            name=dev.get("name")
        )
        p_num = info["sku"]

        extracted_devices.append(ExtractedDeviceSchema(
            category=cat,
            name=dev.get("name", f"{cat} {in_a}A"),
            spec=dev.get("spec", f"{poles}P - {in_a}A"),
            in_a=float(in_a) if in_a else None,
            icu_ka=float(dev.get("icu_ka", 30.0)),
            poles=int(poles) if poles else None,
            quantity=int(dev.get("quantity", 1)),
            brand=info.get("brand") or dev.get("brand") or "",
            part_number=p_num,
            section=dev.get("section", "Đầu ra"),
            confidence=float(dev.get("confidence", settings.DEFAULT_CONFIDENCE))
        ))

    # 4. Tính toán quy cách vỏ tủ điện & thanh cái
    enclosure_specs = EnclosureCadGeneratorService.calculate_enclosure_specs([d.model_dump() for d in extracted_devices])

    # 5. Sinh tập Macro Blocks cấp cao
    macro_blocks = generate_macro_blocks(enclosure_specs, [d.model_dump() for d in extracted_devices])

    # 6. Tự động sinh file AutoCAD DXF cập nhật thực tế
    cad_file_info = None
    try:
        dxf_path = EnclosureCadGeneratorService.generate_dxf(
            project_id=request.project_id,
            project_name=project.name,
            devices=[d.model_dump() for d in extracted_devices],
            output_dir=settings.PROJECTS_DIR
        )
        dxf_filename = os.path.basename(dxf_path)
        dxf_size = os.path.getsize(dxf_path) if os.path.exists(dxf_path) else 0

        existing_cad_stmt = select(ProjectFile).where(
            ProjectFile.project_id == request.project_id,
            ProjectFile.filename.like("PhacThao_TuDien%")
        )
        cad_res = await db.execute(existing_cad_stmt)
        cad_file = cad_res.scalars().first()

        if not cad_file:
            cad_file = ProjectFile(
                project_id=request.project_id,
                filename=dxf_filename,
                file_path=dxf_path,
                file_type="application/dxf",
                file_size=dxf_size
            )
            db.add(cad_file)
        else:
            cad_file.file_path = dxf_path
            cad_file.file_size = dxf_size

        await db.commit()
        await db.refresh(cad_file)

        cad_file_info = {
            "id": cad_file.id,
            "filename": cad_file.filename,
            "file_path": cad_file.file_path,
            "file_size": cad_file.file_size
        }
    except Exception as e:
        reply_text += f"\n\n*(Lưu ý: Không thể xuất file CAD DXF: {str(e)})*"

    # 7. Trừ token hợp lý
    token_cost = 250
    if current_user.tokens >= token_cost:
        current_user.tokens -= token_cost
        await db.commit()

    cad_commands = [b.command_line for b in macro_blocks]

    return ChatResponse(
        reply=reply_text,
        action_type=action_type,
        macro_blocks=macro_blocks,
        enclosure_specs=enclosure_specs,
        devices=extracted_devices,
        cad_file=cad_file_info,
        cad_commands=cad_commands,
        suggested_corrections=[]
    )
