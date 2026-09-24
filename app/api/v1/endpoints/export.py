import os
from pathlib import Path
from typing import List, Optional, Annotated
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.project import Project
from app.models.conversation_session import ConversationSession
import mimetypes
from app.core.config import settings
from app.core.constants import DEFAULT_PROJECT_NAME
from app.models.analysis_iteration import AnalysisIteration
from app.services.export.quotation_exporter import QuotationExporterService
from app.schemas.export import ExportRequest, ExportResponse

router = APIRouter()

class MatchQuotationRequest(BaseModel):
    project_id: int
    default_brand: Optional[str] = None
    devices: Optional[List[dict]] = None

@router.post("/match-quotation")
async def match_quotation(
    payload: MatchQuotationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Đối chiếu thiết bị bóc tách với dữ liệu Catalog các hãng."""
    devices = payload.devices or []
    if not devices:
        sess_stmt = select(ConversationSession).where(
            ConversationSession.project_id == payload.project_id
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

    items = QuotationExporterService.match_devices_multi_brand(
        devices=devices,
        default_brand=payload.default_brand or settings.DEFAULT_BRAND
    )

    return {"items": items}

class ExcelExportPayload(BaseModel):
    project_id: int
    brand_name: Optional[str] = None
    devices: Optional[List[dict]] = None
    proposals: Optional[List[dict]] = None
    vat_percent: Optional[float] = None
    manufacturer_discounts: dict[str, Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]] = Field(default_factory=dict)

@router.post("/excel")
async def export_excel_quotation(
    payload: ExcelExportPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Xuất file Excel bảng báo giá dự toán thiết bị tủ điện."""
    # 1. Tìm thông tin dự án
    proj_stmt = select(Project).where(Project.id == payload.project_id)
    proj_res = await db.execute(proj_stmt)
    project = proj_res.scalar_one_or_none()
    project_name = project.name if project else DEFAULT_PROJECT_NAME

    devices = payload.devices or []

    # 2. Nếu không truyền devices từ client, lấy từ phiên bóc tách mới nhất trong DB
    if not devices:
        sess_stmt = select(ConversationSession).where(
            ConversationSession.project_id == payload.project_id
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

    if not devices:
        raise HTTPException(status_code=400, detail="Không có dữ liệu thiết bị để tạo báo giá")

    # 3. Tạo file Excel
    file_path = QuotationExporterService.export(
        devices=devices,
        project_name=project_name,
        brand_preference=payload.brand_name or settings.DEFAULT_BRAND,
        proposals=payload.proposals,
        vat_percent=payload.vat_percent,
        manufacturer_discounts=payload.manufacturer_discounts,
    )

    if not os.path.exists(file_path):
        raise HTTPException(status_code=500, detail="Lỗi khi tạo file Excel báo giá")

    filename = Path(file_path).name
    abs_path = str(Path(file_path).resolve())
    return FileResponse(
        path=abs_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename
    )

class SaveQuotationFilePayload(BaseModel):
    project_id: int
    brand_name: Optional[str] = None
    devices: List[dict]
    proposals: Optional[List[dict]] = None
    vat_percent: Optional[float] = None
    manufacturer_discounts: dict[str, Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]] = Field(default_factory=dict)

@router.post("/save-to-project")
async def save_quotation_to_project(
    payload: SaveQuotationFilePayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Lưu bảng báo giá thành một file Excel chính thức trong danh sách file dự án."""
    from app.models.project_file import ProjectFile

    proj_stmt = select(Project).where(Project.id == payload.project_id)
    proj_res = await db.execute(proj_stmt)
    project = proj_res.scalar_one_or_none()
    project_name = project.name if project else DEFAULT_PROJECT_NAME

    # Export to Excel file on server (da bao gom tinh toan thanh cai dong qua BusbarCalculatorService)
    file_path = QuotationExporterService.export(
        devices=payload.devices,
        project_name=project_name,
        brand_preference=payload.brand_name or settings.DEFAULT_BRAND,
        proposals=payload.proposals,
        vat_percent=payload.vat_percent,
        manufacturer_discounts=payload.manufacturer_discounts,
    )

    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    # Save record to ProjectFile
    new_file = ProjectFile(
        project_id=payload.project_id,
        filename=filename,
        file_path=file_path,
        file_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size=file_size,
        is_generated=True
    )
    db.add(new_file)

    # Saving a quotation must not silently fabricate a CAD sheet. The user
    # chooses source-backed cabinet and device drawings in the CAD workspace.

    await db.commit()
    await db.refresh(new_file)

    return {
        "success": True,
        "message": "Đã tạo và lưu file báo giá vào dự án thành công",
        "file": {
            "id": new_file.id,
            "project_id": new_file.project_id,
            "filename": new_file.filename,
            "file_size": new_file.file_size,
            "file_type": new_file.file_type,
            "created_at": new_file.created_at.isoformat() if new_file.created_at else None
        }
    }

@router.post("/quotation", response_model=ExportResponse)
async def export_quotation(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Xuất file báo giá theo yêu cầu ExportRequest, lấy dữ liệu từ phiên phân tích mới nhất."""
    try:
        project_id_int = int(str(request.project_id))
    except (ValueError, TypeError):
        project_id_int = 0

    proj_stmt = select(Project).where(Project.id == project_id_int)
    proj_res = await db.execute(proj_stmt)
    project = proj_res.scalar_one_or_none()
    project_name = project.name if project else DEFAULT_PROJECT_NAME

    sess_stmt = select(ConversationSession).where(
        ConversationSession.project_id == project_id_int
    ).order_by(ConversationSession.created_at.desc())
    sess_res = await db.execute(sess_stmt)
    session = sess_res.scalars().first()
    devices = []
    if session:
        iter_stmt = select(AnalysisIteration).where(
            AnalysisIteration.session_id == session.id
        ).order_by(AnalysisIteration.iteration_number.desc())
        iter_res = await db.execute(iter_stmt)
        latest_iter = iter_res.scalars().first()
        if latest_iter and latest_iter.ai_parsed_devices:
            devices = latest_iter.ai_parsed_devices

    file_path = QuotationExporterService.export(
        devices=devices,
        project_name=project_name,
        brand_preference=request.brand_preference or settings.DEFAULT_BRAND
    )
    filename = Path(file_path).name
    file_size = os.path.getsize(file_path)

    return ExportResponse(
        download_url=f"{settings.API_V1_STR}/export/download/{filename}",
        filename=filename,
        file_size=file_size
    )

@router.get("/download/{filename}")
async def download_file(filename: str):
    file_path = Path(settings.EXPORT_DIR) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File không tồn tại")
    mime_type, _ = mimetypes.guess_type(filename)
    return FileResponse(
        path=str(file_path),
        media_type=mime_type or "application/octet-stream",
        filename=filename
    )
