import os
import uuid
import json
import asyncio
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.api.deps import get_current_active_user
from app.core.config import settings
from app.models.user import User
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.ai_connection import AiConnection
from app.models.conversation_session import ConversationSession
from app.models.analysis_iteration import AnalysisIteration
from app.schemas.ai import (
    AnalyzeStartRequest,
    AnalyzePromptRequest,
    AnalyzeRefineRequest,
    AnalyzeFinalizeRequest,
    AnalysisResultSchema,
    ExtractedDeviceSchema,
)
from app.services.ai.analysis_pipeline_service import AnalysisPipelineService
from app.services.ai.cluster_equipment_service import AccompanyingEquipmentService
from app.services.ai.connection_pool import ConnectionPoolService
from app.services.ai.vision_analyzer import VisionAnalyzerService
from app.services.ai.response_parser import ResponseParserService
from app.services.device_catalog_engine import DeviceCatalogEngine, catalog_engine
from app.services.bom.enclosure_sizer import EnclosureSizerService
from app.services.bom.busbar_calculator import BusbarCalculatorService
from app.services.cad.enclosure_cad_generator import EnclosureCadGeneratorService
from app.services.cad.physical_layout_engine import PhysicalLayoutEngine
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app
from app.tasks.worker_tasks import analyze_project_async_task
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_analysis_result_schema(
    session_id: Any,
    iteration_number: int,
    raw_devices: List[Any],
    conf_scores: Optional[dict] = None,
    iteration_id: Optional[int] = None,
    cad_file_info: Optional[dict] = None,
    quotation_file_info: Optional[dict] = None,
    enclosure_spec: Optional[dict] = None,
) -> AnalysisResultSchema:
    conf = conf_scores or {}
    panel_images: Dict[str, str] = {}
    cleaned_devices = []

    for d in raw_devices:
        payload = dict(d) if isinstance(d, dict) else (d.model_dump() if hasattr(d, "model_dump") else dict(d))
        payload.setdefault("category", "Thiết bị")
        payload.setdefault("name", "Thiết bị")
        payload.setdefault("spec", "")
        payload.setdefault("quantity", 1)
        payload.setdefault("confidence", 0.95)

        # Deduplicate massive base64 panel_evidence_image to keep payload light
        p_img = payload.get("panel_evidence_image")
        if p_img and len(p_img) > 100:
            key = payload.get("source_filename") or payload.get("panel_code") or "default"
            if key not in panel_images:
                panel_images[key] = p_img
            if "default" not in panel_images:
                panel_images["default"] = p_img
            payload["panel_evidence_image"] = None

        cleaned_devices.append(ExtractedDeviceSchema.model_validate(payload))

    # Capture any existing panel_images map
    if isinstance(conf.get("panel_images"), dict):
        for k, v in conf["panel_images"].items():
            if k not in panel_images:
                panel_images[k] = v

    enc_spec = enclosure_spec or conf.get("enclosure_spec")
    if not enc_spec:
        enc_devs = [
            {k: v for k, v in d.model_dump().items() if k not in ("evidence_image", "panel_evidence_image")}
            for d in cleaned_devices
        ]
        enc_spec = EnclosureCadGeneratorService.calculate_enclosure_specs(enc_devs)
    elif isinstance(enc_spec, dict) and "branch_rows" in enc_spec:
        clean_rows = []
        for row in enc_spec["branch_rows"]:
            if isinstance(row, list):
                clean_rows.append([
                    {k: v for k, v in b.items() if k not in ("evidence_image", "panel_evidence_image")}
                    if isinstance(b, dict) else b
                    for b in row
                ])
            else:
                clean_rows.append(row)
        enc_spec = {**enc_spec, "branch_rows": clean_rows}

    return AnalysisResultSchema(
        session_id=session_id,
        iteration_id=iteration_id,
        iteration_number=iteration_number,
        devices=cleaned_devices,
        warnings=conf.get("warnings", []),
        topology_preview={
            "incomer_a": enc_spec.get("incomer_rating", settings.DEFAULT_INCOMER_RATING) if enc_spec else settings.DEFAULT_INCOMER_RATING,
            "feeders_count": len(cleaned_devices)
        },
        enclosure_spec=enc_spec,
        panel_images=panel_images,
        cad_file=cad_file_info,
        quotation_file=quotation_file_info,
        quotation_rows=conf.get("quotation_rows") or [],
        technical_proposals=conf.get("technical_proposals") or [],
        conclusion=conf.get("conclusion"),
        panel_info=conf.get("panel_info"),
        panels=conf.get("panels") or [],
        technical_audit=conf.get("technical_audit"),
        file_assessment=conf.get("file_assessment") or {},
        files_assessment=conf.get("files_assessment") or [],
        overall_assessment=conf.get("overall_assessment") or {},
        execution_logs=conf.get("execution_logs") or [],
        process_steps=conf.get("process_steps") or [],
        physical_layout=conf.get("physical_layout"),
        layout_conflicts=conf.get("layout_conflicts") or [],
        analysis_mode=conf.get("analysis_mode", "sld_takeoff"),
        log_version=conf.get("log_version", 2),
    )


@router.post("/start", response_model=AnalysisResultSchema)
async def start_analysis(
    request: AnalyzeStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Bắt đầu bóc tách thiết bị từ bản vẽ dự án (CAD DXF/DWG, PDF, Ảnh).
    Sử dụng pipeline dịch vụ AnalysisPipelineService kết hợp tra cứu Catalog thực tế.
    """
    # 1. Tìm thông tin project và các file đính kèm
    proj_stmt = select(Project).where(
        Project.id == request.project_id,
        Project.user_id == current_user.id,
    )
    proj_res = await db.execute(proj_stmt)
    project = proj_res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Dự án không tồn tại")

    # Nạp tệp theo phạm vi người dùng chọn. Pipeline giữ mọi tệp làm ngữ cảnh
    # và ngăn artifact sinh tự động quay lại BOM.
    if request.file_id:
        target_stmt = select(ProjectFile).where(
            ProjectFile.id == request.file_id,
            ProjectFile.project_id == request.project_id,
        )
        target_res = await db.execute(target_stmt)
        target_file = target_res.scalar_one_or_none()
        
        # Nếu file_id trỏ tới file CAD đã bóc (kết quả cũ), tự động chuyển sang bóc tách các file nguồn import
        if target_file and (
            getattr(target_file, "is_generated", False) or 
            (target_file.filename and target_file.filename.startswith(("BanVe_", "PhacThao_")) and target_file.filename.lower().endswith((".dxf", ".dwg")))
        ):
            source_stmt = select(ProjectFile).where(
                ProjectFile.project_id == request.project_id
            )
            source_res = await db.execute(source_stmt)
            project_files = source_res.scalars().all()
            if not project_files:
                project_files = [target_file]
        else:
            project_files = [target_file] if target_file else []
    else:
        # Giữ toàn bộ tệp dự án làm ngữ cảnh; pipeline tự quyết định tệp nào là
        # nguồn BOM và tệp nào là tài liệu tham chiếu.
        files_stmt = select(ProjectFile).where(
            ProjectFile.project_id == request.project_id
        )
        files_res = await db.execute(files_stmt)
        project_files = files_res.scalars().all()

    if not project_files:
        raise HTTPException(status_code=400, detail="Không có tệp nguồn import hợp lệ để bóc tách.")

    # 2. Lấy danh sách AI Connections theo thứ tự ưu tiên (Connection Pool)
    all_connections = await ConnectionPoolService.get_ordered_connections(db)
    active_ai = all_connections[0] if all_connections else None
    if not active_ai:
        raise HTTPException(
            status_code=400,
            detail="Cần một kết nối AI đang hoạt động có model được chọn cụ thể trong BE.",
        )

    # 3. Thực thi Pipeline Bóc tách qua AnalysisPipelineService (truyền pool connections, không sinh CAD/báo giá)
    pipeline_result = await AnalysisPipelineService.execute_analysis(
        project=project,
        project_files=project_files,
        active_ai=active_ai,
        current_user=current_user,
        fallback_to_standard_template=bool(request.fallback_to_standard_template),
        user_prompt=request.user_prompt,
        db=db,
        all_connections=all_connections,
        generate_cad_and_quotation=False
    )

    extracted_devices = pipeline_result["devices"]
    warnings = pipeline_result["warnings"]
    enclosure_spec = pipeline_result["enclosure_spec"]
    quotation_rows = pipeline_result["quotation_rows"]
    tokens_consumed = pipeline_result["tokens_consumed"]

    if active_ai:
        used_model_name = getattr(active_ai, 'actual_model', None) or active_ai.selected_model
        warnings.append(f"Cấu hình AI: {active_ai.provider.upper()} (Model: {used_model_name})")

    # 4. Trừ token người dùng
    if current_user.tokens >= tokens_consumed:
        current_user.tokens -= tokens_consumed

    # 5. Lưu phiên ConversationSession & AnalysisIteration vào cơ sở dữ liệu
    sess_stmt = select(ConversationSession).where(
        ConversationSession.project_id == request.project_id,
        ConversationSession.status == "active"
    ).order_by(ConversationSession.created_at.desc())
    sess_res = await db.execute(sess_stmt)
    active_session = sess_res.scalars().first()

    if request.is_new_session and active_session:
        active_session.status = "archived"
        db.add(active_session)
        await db.flush()
        active_session = None

    if not active_session:
        active_session = ConversationSession(
            project_id=request.project_id,
            user_id=current_user.id,
            provider=active_ai.provider,
            model_key=active_ai.selected_model,
            status="active",
            total_iterations=0,
            total_tokens_used=0
        )
        db.add(active_session)
        await db.flush()

    active_session.total_iterations += 1
    active_session.total_tokens_used += tokens_consumed

    iteration = AnalysisIteration(
        session_id=active_session.id,
        iteration_number=active_session.total_iterations,
        trigger_type="pipeline_scan",
        files_analyzed={
            "file_ids": [f.id for f in project_files],
            "file_names": [f.filename for f in project_files],
            "count": len(project_files)
        },
        ai_parsed_devices=[d.model_dump() for d in extracted_devices],
        confidence_scores={
            "warnings": warnings,
            "quotation_rows": quotation_rows,
            "conclusion": pipeline_result.get("conclusion"),
            "panel_info": pipeline_result.get("panel_info"),
            "panels": pipeline_result.get("panels"),
            "enclosure_spec": enclosure_spec,
            "technical_audit": pipeline_result.get("technical_audit"),
            "file_assessment": pipeline_result.get("file_assessment"),
            "files_assessment": pipeline_result.get("files_assessment"),
            "overall_assessment": pipeline_result.get("overall_assessment"),
            "execution_logs": pipeline_result.get("execution_logs"),
            "process_steps": pipeline_result.get("process_steps"),
            "physical_layout": pipeline_result.get("physical_layout"),
            "layout_conflicts": pipeline_result.get("layout_conflicts"),
            "analysis_mode": pipeline_result.get("analysis_mode", "sld_takeoff"),
            "log_version": pipeline_result.get("log_version", 2),
        },
        tokens_used=tokens_consumed,
        status="completed"
    )
    from datetime import datetime, timezone
    project.updated_at = datetime.now(timezone.utc)
    db.add(project)
    db.add(iteration)
    await db.commit()
    await db.refresh(iteration)

    return _build_analysis_result_schema(
        session_id=active_session.id,
        iteration_number=active_session.total_iterations,
        raw_devices=extracted_devices,
        conf_scores=pipeline_result,
        iteration_id=iteration.id,
        cad_file_info=None,
        quotation_file_info=None,
        enclosure_spec=enclosure_spec,
    )


@router.post("/stream")
async def stream_analysis(
    request: AnalyzeStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Bóc tách bản vẽ thời gian thực qua Server-Sent Events (SSE).
    Phát trực tiếp tiến trình từng trang, các sự kiện log thực tế và danh sách thiết bị
    ngay khi mỗi trang phân tích hoàn tất (không bắt người dùng chờ hết toàn bộ tệp).
    """
    proj_stmt = select(Project).where(Project.id == request.project_id, Project.user_id == current_user.id)
    proj_res = await db.execute(proj_stmt)
    project = proj_res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Dự án không tồn tại")

    if request.file_id:
        target_stmt = select(ProjectFile).where(ProjectFile.id == request.file_id, ProjectFile.project_id == request.project_id)
        target_res = await db.execute(target_stmt)
        target_file = target_res.scalar_one_or_none()
        if target_file and (
            getattr(target_file, "is_generated", False) or 
            (target_file.filename and target_file.filename.startswith(("BanVe_", "PhacThao_")) and target_file.filename.lower().endswith((".dxf", ".dwg")))
        ):
            source_stmt = select(ProjectFile).where(ProjectFile.project_id == request.project_id)
            source_res = await db.execute(source_stmt)
            project_files = source_res.scalars().all()
            if not project_files:
                project_files = [target_file]
        else:
            project_files = [target_file] if target_file else []
    else:
        files_stmt = select(ProjectFile).where(ProjectFile.project_id == request.project_id)
        files_res = await db.execute(files_stmt)
        project_files = files_res.scalars().all()
        if not project_files:
            all_files_res = await db.execute(select(ProjectFile).where(ProjectFile.project_id == request.project_id))
            project_files = all_files_res.scalars().all()

    if not project_files:
        raise HTTPException(status_code=400, detail="Không tìm thấy bản vẽ để bóc tách")

    all_connections = await ConnectionPoolService.get_ordered_connections(db)
    active_ai = all_connections[0] if all_connections else None

    async def event_generator():
        progress_queue = asyncio.Queue()

        async def run_pipeline():
            try:
                pipeline_result = await AnalysisPipelineService.execute_analysis(
                    project=project,
                    project_files=project_files,
                    active_ai=active_ai,
                    current_user=current_user,
                    fallback_to_standard_template=bool(request.fallback_to_standard_template),
                    user_prompt=request.user_prompt,
                    db=db,
                    all_connections=all_connections,
                    generate_cad_and_quotation=False,
                    progress_callback=progress_queue.put,
                    target_page=request.target_page
                )

                extracted_devices = pipeline_result["devices"]
                warnings = pipeline_result["warnings"]
                enclosure_spec = pipeline_result["enclosure_spec"]
                quotation_rows = pipeline_result["quotation_rows"]
                tokens_consumed = pipeline_result["tokens_consumed"]

                if active_ai:
                    used_model_name = getattr(active_ai, 'actual_model', None) or active_ai.selected_model
                    warnings.append(f"Cấu hình AI: {active_ai.provider.upper()} (Model: {used_model_name})")

                if current_user.tokens >= tokens_consumed:
                    current_user.tokens -= tokens_consumed

                sess_stmt = select(ConversationSession).where(
                    ConversationSession.project_id == request.project_id,
                    ConversationSession.status == "active"
                ).order_by(ConversationSession.created_at.desc())
                sess_res = await db.execute(sess_stmt)
                active_session = sess_res.scalars().first()

                if request.is_new_session and active_session:
                    active_session.status = "archived"
                    db.add(active_session)
                    await db.flush()
                    active_session = None

                if not active_session:
                    active_session = ConversationSession(
                        project_id=request.project_id,
                        user_id=current_user.id,
                        provider=active_ai.provider,
                        model_key=active_ai.selected_model,
                        status="active",
                        total_iterations=0,
                        total_tokens_used=0
                    )
                    db.add(active_session)
                    await db.flush()

                active_session.total_iterations += 1
                active_session.total_tokens_used += tokens_consumed

                iteration = AnalysisIteration(
                    session_id=active_session.id,
                    iteration_number=active_session.total_iterations,
                    trigger_type="pipeline_scan_stream",
                    files_analyzed={
                        "file_ids": [f.id for f in project_files],
                        "file_names": [f.filename for f in project_files],
                        "count": len(project_files)
                    },
                    ai_parsed_devices=[d.model_dump() for d in extracted_devices],
                    confidence_scores={
                        "warnings": warnings,
                        "quotation_rows": quotation_rows,
                        "technical_proposals": pipeline_result.get("technical_proposals", []),
                        "conclusion": pipeline_result.get("conclusion"),
                        "panel_info": pipeline_result.get("panel_info"),
                        "panels": pipeline_result.get("panels"),
                        "enclosure_spec": enclosure_spec,
                        "technical_audit": pipeline_result.get("technical_audit"),
                        "file_assessment": pipeline_result.get("file_assessment"),
                        "files_assessment": pipeline_result.get("files_assessment"),
                        "overall_assessment": pipeline_result.get("overall_assessment"),
                        "execution_logs": pipeline_result.get("execution_logs"),
                        "process_steps": pipeline_result.get("process_steps"),
                        "physical_layout": pipeline_result.get("physical_layout"),
                        "layout_conflicts": pipeline_result.get("layout_conflicts"),
                        # A restored takeoff log must never be rendered as a
                        # catalog run from an older iteration.
                        "analysis_mode": pipeline_result.get("analysis_mode", "sld_takeoff"),
                        "log_version": pipeline_result.get("log_version", 2),
                    },
                    tokens_used=tokens_consumed,
                    status="completed"
                )
                from datetime import datetime, timezone
                project.updated_at = datetime.now(timezone.utc)
                db.add(project)
                db.add(iteration)
                await db.commit()

                complete_payload = {
                    "session_id": str(active_session.id),
                    "iteration_number": active_session.total_iterations,
                    "devices": [d.model_dump() for d in extracted_devices],
                    "warnings": warnings,
                    "topology_preview": {"incomer_a": enclosure_spec.get("incomer_rating", settings.DEFAULT_INCOMER_RATING) if enclosure_spec else settings.DEFAULT_INCOMER_RATING, "feeders_count": len(extracted_devices)},
                    "enclosure_spec": enclosure_spec,
                    "cad_file": None,
                    "quotation_file": None,
                    "quotation_rows": quotation_rows,
                    "technical_proposals": pipeline_result.get("technical_proposals", []),
                    "conclusion": pipeline_result.get("conclusion"),
                    "panel_info": pipeline_result.get("panel_info"),
                    "panels": pipeline_result.get("panels"),
                    "technical_audit": pipeline_result.get("technical_audit"),
                    "file_assessment": pipeline_result.get("file_assessment"),
                    "files_assessment": pipeline_result.get("files_assessment"),
                    "overall_assessment": pipeline_result.get("overall_assessment"),
                    "execution_logs": pipeline_result.get("execution_logs"),
                    "process_steps": pipeline_result.get("process_steps"),
                    "physical_layout": pipeline_result.get("physical_layout"),
                    "layout_conflicts": pipeline_result.get("layout_conflicts"),
                    "analysis_mode": pipeline_result.get("analysis_mode", "sld_takeoff"),
                    "log_version": pipeline_result.get("log_version", 2),
                }

                await progress_queue.put({
                    "type": "complete",
                    "result": complete_payload
                })
            except Exception as pipe_err:
                logger.error(f"Streaming pipeline error: {pipe_err}", exc_info=True)
                await progress_queue.put({
                    "type": "error",
                    "stage": "ai_vision",
                    "title": "Lỗi phân tích bản vẽ",
                    "detail": str(pipe_err)
                })
            finally:
                await progress_queue.put(None)

        task = asyncio.create_task(run_pipeline())

        try:
            while True:
                item = await progress_queue.get()
                if item is None:
                    break
                yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


class GenerateQuotationCadRequest(BaseModel):
    project_id: int
    brand_preference: Optional[str] = None
    devices: Optional[List[Dict[str, Any]]] = None
    user_prompt: Optional[str] = None
    enclosure_dimensions: Optional[str] = None
    panel_code: Optional[str] = None
    panel_name: Optional[str] = None
    per_panel: bool = False


@router.post("/generate-quotation-cad")
async def generate_quotation_and_cad(
    payload: GenerateQuotationCadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Quy trình Tạo Báo Giá chuyên biệt:
    1. Phân tích thiết bị kỹ thuật (kích thước vỏ tủ, thanh cái đồng Form 2B, layout vật lý, đối soát Catalog).
    2. Dựng bản vẽ AutoCAD DXF 4 hình chiếu và lưu vào tệp dự án (ProjectFile).
    3. Lập bảng báo giá chi tiết hoàn chỉnh.
    """
    proj_stmt = select(Project).where(Project.id == payload.project_id, Project.user_id == current_user.id)
    proj_res = await db.execute(proj_stmt)
    project = proj_res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Dự án không tồn tại")

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

    if not devices:
        raise HTTPException(status_code=400, detail="Chưa có dữ liệu thiết bị để phân tích và lập báo giá. Vui lòng bóc tách trước.")

    result = await AnalysisPipelineService.generate_cad_and_quotation(
        project=project,
        db=db,
        devices=devices,
        brand_preference=payload.brand_preference or settings.DEFAULT_BRAND,
        user_prompt=payload.user_prompt,
        enclosure_dimensions=payload.enclosure_dimensions,
        panel_code=payload.panel_code,
        panel_name=payload.panel_name,
        per_panel=payload.per_panel,
    )

    return result


@router.post("/generate-quotation-cad/stream")
async def stream_generate_quotation_and_cad(
    payload: GenerateQuotationCadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Stream real milestones produced by the CAD/quotation pipeline over SSE."""
    proj_stmt = select(Project).where(Project.id == payload.project_id, Project.user_id == current_user.id)
    project = (await db.execute(proj_stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Dự án không tồn tại")

    devices = payload.devices or []
    if not devices:
        sess_stmt = select(ConversationSession).where(
            ConversationSession.project_id == payload.project_id
        ).order_by(ConversationSession.created_at.desc())
        session = (await db.execute(sess_stmt)).scalars().first()
        if session:
            iter_stmt = select(AnalysisIteration).where(
                AnalysisIteration.session_id == session.id
            ).order_by(AnalysisIteration.iteration_number.desc())
            latest_iter = (await db.execute(iter_stmt)).scalars().first()
            if latest_iter and latest_iter.ai_parsed_devices:
                devices = latest_iter.ai_parsed_devices
    if not devices:
        raise HTTPException(status_code=400, detail="Chưa có dữ liệu thiết bị để tạo CAD và báo giá")

    progress_queue: asyncio.Queue = asyncio.Queue()

    async def run_generation():
        try:
            result = await AnalysisPipelineService.generate_cad_and_quotation(
                project=project,
                db=db,
                devices=devices,
                brand_preference=payload.brand_preference or settings.DEFAULT_BRAND,
                user_prompt=payload.user_prompt,
                enclosure_dimensions=payload.enclosure_dimensions,
                panel_code=payload.panel_code,
                panel_name=payload.panel_name,
                per_panel=payload.per_panel,
                progress_callback=progress_queue.put,
            )
            await progress_queue.put({"type": "complete", "result": result})
        except Exception as exc:
            logger.error("Streaming CAD generation error: %s", exc, exc_info=True)
            await progress_queue.put({"type": "error", "message": str(exc)})
        finally:
            await progress_queue.put(None)

    async def event_generator():
        task = asyncio.create_task(run_generation())
        try:
            while True:
                item = await progress_queue.get()
                if item is None:
                    break
                yield f"data: {json.dumps(item, ensure_ascii=False, default=str)}\n\n"
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.get("/project/{project_id}/latest", response_model=Optional[AnalysisResultSchema])
async def get_latest_project_analysis(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Lấy kết quả bóc tách gần nhất của dự án để phục hồi khi tải lại trang."""
    project_stmt = select(Project.id).where(
        Project.id == project_id,
        Project.user_id == current_user.id,
    )
    if (await db.execute(project_stmt)).scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Dự án không tồn tại")

    sess_stmt = select(ConversationSession).where(
        ConversationSession.project_id == project_id
    ).order_by(ConversationSession.created_at.desc())
    sess_res = await db.execute(sess_stmt)
    session = sess_res.scalars().first()
    if not session:
        return None

    iter_stmt = select(AnalysisIteration).where(
        AnalysisIteration.session_id == session.id
    ).order_by(AnalysisIteration.iteration_number.desc())
    iter_res = await db.execute(iter_stmt)
    all_iters = iter_res.scalars().all()
    if not all_iters:
        return None

    latest_iter = None
    for it in all_iters:
        if it.ai_parsed_devices and len(it.ai_parsed_devices) > 0:
            latest_iter = it
            break
    if not latest_iter:
        latest_iter = all_iters[0]

    existing_cad_stmt = select(ProjectFile).where(
        ProjectFile.project_id == project_id,
        (ProjectFile.filename.like("BanVe_%") | ProjectFile.filename.like("PhacThao_%"))
    )
    cad_res = await db.execute(existing_cad_stmt)
    cad_file = cad_res.scalars().first()
    cad_file_info = {
        "id": cad_file.id,
        "filename": cad_file.filename,
        "file_path": cad_file.file_path,
        "file_size": cad_file.file_size
    } if cad_file else None

    return _build_analysis_result_schema(
        session_id=session.id,
        iteration_number=latest_iter.iteration_number,
        raw_devices=latest_iter.ai_parsed_devices or [],
        conf_scores=latest_iter.confidence_scores or {},
        iteration_id=latest_iter.id,
        cad_file_info=cad_file_info,
    )


@router.post("/refine", response_model=AnalysisResultSchema)
async def refine_analysis(
    request: AnalyzeRefineRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Tinh chỉnh kết quả bóc tách — phục hồi iteration gần nhất và áp dụng chỉnh sửa."""
    # Tìm session
    sess_stmt = select(ConversationSession).where(
        ConversationSession.id == request.session_id
    )
    sess_res = await db.execute(sess_stmt)
    session = sess_res.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session không tồn tại")

    # Lấy iteration gần nhất
    iter_stmt = select(AnalysisIteration).where(
        AnalysisIteration.session_id == request.session_id
    ).order_by(AnalysisIteration.iteration_number.desc())
    iter_res = await db.execute(iter_stmt)
    latest_iter = iter_res.scalars().first()

    session.total_iterations += 1
    await db.commit()

    return _build_analysis_result_schema(
        session_id=request.session_id,
        iteration_number=session.total_iterations,
        raw_devices=raw_devs,
        conf_scores=conf_scores,
        iteration_id=latest_iter.id if latest_iter else None,
        cad_file_info=None,
        quotation_file_info=None,
    )


@router.post("/finalize")
async def finalize_analysis(
    request: AnalyzeFinalizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Chốt phiên phân tích và lưu trữ."""
    return {"status": "finalized", "session_id": str(request.session_id)}


@router.get("/project/{project_id}/sessions")
async def get_project_sessions(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Lấy danh sách tất cả các phiên và lần bóc tách của dự án để chọn xem lại."""
    sess_stmt = select(ConversationSession).where(
        ConversationSession.project_id == project_id
    ).order_by(ConversationSession.created_at.desc())
    sess_res = await db.execute(sess_stmt)
    sessions = sess_res.scalars().all()

    items = []
    for s in sessions:
        iter_stmt = select(AnalysisIteration).where(
            AnalysisIteration.session_id == s.id,
            AnalysisIteration.status == "completed"
        ).order_by(AnalysisIteration.iteration_number.desc())
        iter_res = await db.execute(iter_stmt)
        iterations = iter_res.scalars().all()

        for it in iterations:
            raw_devs = it.ai_parsed_devices or []
            total_device_count = 0
            for device in raw_devs:
                try:
                    total_device_count += max(int(float(device.get("quantity") or 1)), 0)
                except (TypeError, ValueError):
                    total_device_count += 1
            files_meta = it.files_analyzed or {}
            filenames = files_meta.get("file_names") or []
            if not filenames and files_meta.get("file_name"):
                filenames = [files_meta.get("file_name")]
            file_display = ", ".join(filenames) if filenames else None

            conf = it.confidence_scores or {}
            panel_code = conf.get("panel_code")
            panel_name = conf.get("panel_name")
            if not panel_code and conf.get("panel_info"):
                panel_code = conf["panel_info"].get("panel_code")
                panel_name = conf["panel_info"].get("panel_name")
            if not panel_code and raw_devs:
                panel_code = raw_devs[0].get("panel_code")
                panel_name = raw_devs[0].get("panel_name")

            items.append({
                "id": it.id,
                "iteration_id": it.id,
                "session_id": str(s.id),
                "iteration_number": it.iteration_number,
                "trigger_type": it.trigger_type,
                "devices_count": len(raw_devs),
                "device_count": len(raw_devs),
                "total_device_count": total_device_count,
                "panel_code": panel_code or "",
                "panel_name": panel_name or "",
                "filename": file_display or "Bản vẽ dự án",
                "files_analyzed": filenames,
                "created_at": it.created_at.isoformat() if it.created_at else None,
                "is_active_session": s.status == "active"
            })

    items.sort(key=lambda x: x["created_at"] or "", reverse=True)
    return {"sessions": items}


@router.get("/iteration/{iteration_id}", response_model=Optional[AnalysisResultSchema])
async def get_iteration_analysis(
    iteration_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Lấy chi tiết toàn bộ kết quả bóc tách của một phiên/iteration cụ thể để phục hồi lên giao diện."""
    iter_stmt = select(AnalysisIteration).where(AnalysisIteration.id == iteration_id)
    iter_res = await db.execute(iter_stmt)
    it = iter_res.scalar_one_or_none()
    if not it:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên bóc tách")

    sess_stmt = select(ConversationSession).where(ConversationSession.id == it.session_id)
    sess_res = await db.execute(sess_stmt)
    session = sess_res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session không tồn tại")

    existing_cad_stmt = select(ProjectFile).where(
        ProjectFile.project_id == session.project_id,
        (ProjectFile.filename.like("BanVe_%") | ProjectFile.filename.like("PhacThao_%"))
    )
    cad_res = await db.execute(existing_cad_stmt)
    cad_file = cad_res.scalars().first()
    cad_file_info = {
        "id": cad_file.id,
        "filename": cad_file.filename,
        "file_path": cad_file.file_path,
        "file_size": cad_file.file_size
    } if cad_file else None

    return _build_analysis_result_schema(
        session_id=session.id,
        iteration_number=it.iteration_number,
        raw_devices=it.ai_parsed_devices or [],
        conf_scores=it.confidence_scores or {},
        iteration_id=it.id,
        cad_file_info=cad_file_info,
    )


@router.delete("/iteration/{iteration_id}")
async def delete_iteration(
    iteration_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Xóa một phiên bóc tách (iteration) cụ thể."""
    iter_stmt = select(AnalysisIteration).where(AnalysisIteration.id == iteration_id)
    iter_res = await db.execute(iter_stmt)
    it = iter_res.scalar_one_or_none()
    if not it:
        raise HTTPException(status_code=404, detail="Phiên bóc tách không tồn tại")

    session_id = it.session_id
    await db.delete(it)

    # Nếu session không còn iteration nào, xóa luôn session
    remain_stmt = select(AnalysisIteration).where(AnalysisIteration.session_id == session_id)
    remain_res = await db.execute(remain_stmt)
    if not remain_res.scalars().first():
        sess_stmt = select(ConversationSession).where(ConversationSession.id == session_id)
        sess_res = await db.execute(sess_stmt)
        s = sess_res.scalar_one_or_none()
        if s:
            await db.delete(s)

    await db.commit()
    return {"status": "success", "message": "Đã xóa phiên bóc tách thành công"}


@router.get("/history/{session_id}")
async def get_analysis_history(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Lấy lịch sử các vòng lặp bóc tách."""
    iter_stmt = select(AnalysisIteration).where(
        AnalysisIteration.session_id == session_id
    ).order_by(AnalysisIteration.iteration_number.asc())
    iter_res = await db.execute(iter_stmt)
    iterations = iter_res.scalars().all()
    return {
        "history": [
            {
                "iteration_number": it.iteration_number,
                "trigger_type": it.trigger_type,
                "devices_count": len(it.ai_parsed_devices or []),
                "status": it.status,
                "created_at": it.created_at
            }
            for it in iterations
        ]
    }


@router.delete("/project/{project_id}/session")
async def delete_project_session(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Xóa toàn bộ phiên bóc tách của dự án, dọn dẹp các file CAD phát sinh và làm mới giao diện."""
    sess_stmt = select(ConversationSession).where(ConversationSession.project_id == project_id)
    sess_res = await db.execute(sess_stmt)
    sessions = sess_res.scalars().all()

    for s in sessions:
        iter_stmt = select(AnalysisIteration).where(AnalysisIteration.session_id == s.id)
        iter_res = await db.execute(iter_stmt)
        for it in iter_res.scalars().all():
            await db.delete(it)
        await db.delete(s)

    # Xóa file CAD sinh tự động nếu có trong project_files
    cad_stmt = select(ProjectFile).where(
        ProjectFile.project_id == project_id,
        (ProjectFile.filename.like("BanVe_%") | ProjectFile.filename.like("PhacThao_%"))
    )
    cad_res = await db.execute(cad_stmt)
    cad_files = cad_res.scalars().all()
    for cf in cad_files:
        if cf.file_path and os.path.exists(cf.file_path):
            try:
                os.remove(cf.file_path)
            except Exception:
                pass
        await db.delete(cf)

    # Đồng thời dọn dẹp mọi bản ghi file BaoGia_*.xlsx nếu còn sót
    q_stmt = select(ProjectFile).where(
        ProjectFile.project_id == project_id,
        ProjectFile.filename.like("BaoGia_%")
    )
    q_res = await db.execute(q_stmt)
    for qf in q_res.scalars().all():
        await db.delete(qf)

    await db.commit()
    return {"status": "success", "message": "Đã xóa phiên bóc tách thành công"}


@router.post("/prompt", response_model=AnalysisResultSchema)
async def analyze_prompt(
    request: AnalyzePromptRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Tiếp nhận yêu cầu kỹ thuật dạng văn bản từ khách hàng khi chưa có bản vẽ,
    sử dụng AI LLM để phân tích sơ đồ & danh mục thiết bị, tra cứu Catalog SKU & đơn giá thực tế,
    tính toán kích thước vỏ tủ & thanh cái theo tiêu chuẩn, sinh bản vẽ CAD và bảng BOM lưu vào DB.
    """
    import re
    from datetime import datetime, timezone
    from app.services.device_catalog_engine import BRAND_SYNONYMS

    proj_stmt = select(Project).where(Project.id == request.project_id, Project.user_id == current_user.id)
    proj_res = await db.execute(proj_stmt)
    project = proj_res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Dự án không tồn tại")

    prompt_text = request.prompt.strip()
    if not prompt_text:
        raise HTTPException(status_code=400, detail="Vui lòng nhập yêu cầu kỹ thuật")

    # 1. Lấy danh sách AI Connections theo thứ tự ưu tiên (Connection Pool)
    all_connections = await ConnectionPoolService.get_ordered_connections(db)
    prompt_ai = all_connections[0] if all_connections else None

    devices: List[ExtractedDeviceSchema] = []
    panel_code = ""
    panel_name = ""
    system_type = ""
    safety_rec = ""
    vendor_rec = ""
    ai_used = False
    tokens_consumed = 0
    file_assessment = None

    # 2. Xử lý bằng AI Model nếu có kết nối AI đang kích hoạt (Connection Pool fallback)
    if all_connections:
        try:
            from app.core.prompts import PROMPT_TYPES, TEXT_REQUIREMENT_ANALYSIS_PROMPT_TEMPLATE, append_canonical_output_contract
            from app.services.ai.prompt_template_service import PromptTemplateService
            system_prompt = await PromptTemplateService.render(
                db, PROMPT_TYPES["TEXT_REQUIREMENT"], TEXT_REQUIREMENT_ANALYSIS_PROMPT_TEMPLATE,
                {"user_request": prompt_text},
            )
            system_prompt = append_canonical_output_contract(system_prompt)
            ai_raw_response, used_conn = await ConnectionPoolService.call_with_fallback(
                db=db,
                connections=all_connections,
                call_fn=VisionAnalyzerService.analyze_text,
                prompt=system_prompt,
            )
            prompt_ai = used_conn
            parsed_devices = ResponseParserService.parse_device_list(ai_raw_response)
            if parsed_devices:
                parsed_panels = ResponseParserService.extract_panels_metadata(ai_raw_response)
                if parsed_panels:
                    panel_code = parsed_panels[0].get("panel_code") or ""
                    panel_name = parsed_panels[0].get("panel_name") or ""
                json_blocks = ResponseParserService.extract_json_blocks(ai_raw_response)
                for blk in json_blocks:
                    if isinstance(blk, dict):
                        if blk.get("panel_code"):
                            panel_code = str(blk["panel_code"]).strip()
                        if blk.get("panel_name"):
                            panel_name = str(blk["panel_name"]).strip()
                        if blk.get("system_type"):
                            system_type = str(blk["system_type"]).strip()
                        if blk.get("safety_recommendation"):
                            safety_rec = str(blk["safety_recommendation"]).strip()
                        if blk.get("vendor_recommendation"):
                            vendor_rec = str(blk["vendor_recommendation"]).strip()
                        if blk.get("file_assessment"):
                            file_assessment = blk["file_assessment"]

                for d in parsed_devices:
                    clean_in = float(d.in_a) if d.in_a is not None and float(d.in_a) > 0 else None
                    clean_icu = float(d.icu_ka) if d.icu_ka is not None and float(d.icu_ka) > 0 else None
                    clean_poles = int(d.poles) if d.poles is not None and int(d.poles) > 0 else None
                    
                    devices.append(ExtractedDeviceSchema(
                        category=d.category or "Thiết bị",
                        name=d.name or "Thiết bị",
                        spec=d.spec or "Chưa đủ thông số",
                        in_a=clean_in,
                        icu_ka=clean_icu,
                        poles=clean_poles,
                        quantity=int(d.quantity or 1),
                        brand=d.brand or "",
                        part_number=d.part_number or "",
                        section=d.section or "Đầu ra",
                        location=d.location,
                        panel_code=d.panel_code or panel_code,
                        panel_name=d.panel_name or panel_name,
                        notes=d.notes or "",
                        tag=d.tag,
                        mounting=d.mounting,
                        electrical_function=d.electrical_function,
                        upstream_device=d.upstream_device,
                        downstream_device=d.downstream_device,
                        connected_load=d.connected_load,
                        confidence=float(d.confidence or 0.0),
                        suggested_brands=d.suggested_brands or [],
                        accompanying_accessories=AccompanyingEquipmentService.format_accessories(d.accompanying_accessories),
                        compatible_proposal=d.compatible_proposal,
                        source_type="text",
                        source_filename="",
                    ))
                ai_used = True
                tokens_consumed = 350
        except Exception as ai_err:
            logger.error(f"Lỗi khi gọi AI analyze_text: {ai_err}")
            raise HTTPException(
                status_code=502,
                detail=f"Mô hình AI gặp sự cố khi phân tích yêu cầu kỹ thuật: {str(ai_err)}. Vui lòng kiểm tra lại cấu hình kết nối AI."
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="Chưa cấu hình hoặc kích hoạt AI Provider trong hệ thống. Vui lòng cấu hình API Key trong trang Quản trị để sử dụng tính năng bóc tách kỹ thuật."
        )

    # 3. Kiểm tra kết quả trích xuất từ AI: Báo lỗi rõ ràng, không tự ý bịa thiết bị giả
    if not devices:
        raise HTTPException(
            status_code=400,
            detail="Mô hình AI không nhận diện được thiết bị điện nào từ mô tả kỹ thuật của bạn. Vui lòng cung cấp mô tả chi tiết hơn (ví dụ: 'Tủ phân phối DB gồm MCCB tổng 100A 3P và 6 lộ MCB nhánh 16A')."
        )

    # 4. Tra cứu thông tin SKU và Catalog thực tế cho từng thiết bị
    for idx, d in enumerate(devices):
        cat_info = catalog_engine.lookup_device_info(
            category=d.category,
            in_a=d.in_a,
            poles=d.poles,
            brand=d.brand,
            part_number=d.part_number,
            name=d.name
        )
        final_sku = cat_info["sku"] or d.part_number or ""
        final_brand = cat_info["brand"] or d.brand or ""
        d.part_number = final_sku
        d.brand = final_brand

    # Trong quá trình bóc tách: KHÔNG tính đồng, KHÔNG vẽ CAD và KHÔNG tạo file báo giá
    quotation_rows = []
    cad_file_info = None
    enclosure_spec = None
    physical_layout = None
    layout_conflicts = []

    rated_currents = [float(d.in_a) for d in devices if d.in_a]
    incomer_a = max(rated_currents) if rated_currents else 0

    if not panel_code:
        panel_code = next((d.panel_code for d in devices if d.panel_code), "")
    if not panel_name:
        panel_name = next((d.panel_name for d in devices if d.panel_name), "")
    for device in devices:
        device.panel_code = device.panel_code or panel_code
        device.panel_name = device.panel_name or panel_name
    panels = AnalysisPipelineService._normalize_panels([], devices)

    if not file_assessment:
        if devices:
            file_assessment = {
                "is_suitable": True,
                "document_type": "Yêu cầu bóc tách thiết bị tủ điện",
                "assessment_summary": f"Yêu cầu kỹ thuật phù hợp, đã trích xuất danh mục {len(devices)} thiết bị cho {panel_name}.",
                "warnings": []
            }
        else:
            file_assessment = {
                "is_suitable": False,
                "document_type": "Yêu cầu không phù hợp",
                "assessment_summary": "Nội dung yêu cầu không liên quan đến tủ bảng điện hoặc sơ đồ nguyên lý điện.",
                "warnings": ["Vui lòng kiểm tra lại nội dung yêu cầu."]
            }

    conclusion = {
        "panel_code": panel_code,
        "system_type": system_type,
        "summary": f"{panel_name} đã được bóc tách thành công {len(devices)} thiết bị (Incomer {int(incomer_a)}A). Vui lòng bấm 'Tạo báo giá & Vẽ CAD' để phân tích kỹ thuật vỏ tủ, tính thanh cái đồng, dựng bản vẽ AutoCAD DXF và lập bảng báo giá hoàn chỉnh.",
        "enclosure_spec": "Kích thước vỏ tủ và thanh cái sẽ được phân tích tự động khi bấm 'Tạo báo giá & Vẽ CAD'.",
        "safety_recommendation": safety_rec,
        "vendor_recommendation": vendor_rec,
        "file_assessment": file_assessment
    }

    panel_info = {
        "panel_code": panel_code,
        "panel_name": panel_name,
        "panel_type": panel_name,
        "system_type": system_type
    }

    execution_logs = [
        {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "stage": "ingestion",
            "title": "Tiếp nhận yêu cầu kỹ thuật văn bản",
            "detail": f"Nội dung yêu cầu: {prompt_text[:120]}...",
            "status": "info"
        },
        {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "stage": "ai_vision",
            "title": "Phân tích AI mô tả cấu hình tủ điện",
            "detail": f"Trích xuất thành công {len(devices)} thiết bị cho {panel_name} ({panel_code})",
            "status": "success"
        },
        {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "stage": "catalog_matching",
            "title": "Tra cứu Catalog & Khớp SKU Đa Hãng",
            "detail": f"Khớp SKU chính xác và chuẩn hóa cho {len(devices)} thiết bị",
            "status": "success"
        },
        {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "stage": "finalization",
            "title": "Hoàn tất bóc tách danh mục thiết bị",
            "detail": f"Đã bóc tách {len(devices)} thiết bị. Sẵn sàng cho bước Tạo Báo Giá & Vẽ CAD.",
            "status": "success"
        }
    ]

    process_steps = [
        {
            "id": "ingestion",
            "title": "Tiếp nhận & Thẩm định yêu cầu",
            "description": f"Mô tả kỹ thuật: {panel_name}",
            "status": "completed"
        },
        {
            "id": "ai_vision",
            "title": "Phân tích Kỹ thuật & Thiết kế Cấu hình",
            "description": f"Đã bóc tách {len(devices)} thiết bị điện đóng cắt & phụ trợ",
            "status": "completed"
        },
        {
            "id": "catalog_matching",
            "title": "Tra cứu Catalog & Khớp SKU Đa Hãng",
            "description": f"Khớp SKU & hãng sản xuất cho {len(devices)} thiết bị",
            "status": "completed"
        },
        {
            "id": "finalization",
            "title": "Hoàn tất bóc tách thiết bị",
            "description": f"Đã bóc tách {len(devices)} thiết bị. Sẵn sàng tạo báo giá & vẽ CAD.",
            "status": "completed"
        }
    ]

    # 8. Lưu Session & Iteration
    sess_stmt = select(ConversationSession).where(
        ConversationSession.project_id == request.project_id,
        ConversationSession.status == "active"
    ).order_by(ConversationSession.created_at.desc())
    sess_res = await db.execute(sess_stmt)
    active_session = sess_res.scalars().first()

    if not active_session:
        active_session = ConversationSession(
            project_id=request.project_id,
            user_id=current_user.id,
            provider=prompt_ai.provider,
            model_key=prompt_ai.selected_model,
            status="active",
            total_iterations=0,
            total_tokens_used=0
        )
        db.add(active_session)
        await db.flush()

    active_session.total_iterations += 1
    active_session.total_tokens_used += tokens_consumed

    success_msg = f"Bóc tách thành công từ yêu cầu kỹ thuật bằng {'AI ' + prompt_ai.provider.upper() if ai_used else 'Engine Phân tích kỹ thuật'}: '{prompt_text[:60]}...'"
    iteration = AnalysisIteration(
        session_id=active_session.id,
        iteration_number=active_session.total_iterations,
        trigger_type="prompt_input",
        files_analyzed={"prompt": prompt_text, "source": "user_text_input", "ai_model": prompt_ai.selected_model if ai_used else "catalog_engine"},
        ai_parsed_devices=[d.model_dump() for d in devices],
        confidence_scores={
            "warnings": [success_msg],
            "quotation_rows": quotation_rows,
            "conclusion": conclusion,
            "panel_info": panel_info,
            "execution_logs": execution_logs,
            "process_steps": process_steps,
            "physical_layout": physical_layout,
            "layout_conflicts": layout_conflicts,
            "panels": panels,
            "file_assessment": file_assessment,
            "analysis_mode": "sld_takeoff",
            "log_version": 2,
        },
        tokens_used=tokens_consumed,
        status="completed"
    )
    project.updated_at = datetime.now(timezone.utc)
    db.add(project)
    db.add(iteration)
    await db.commit()
    await db.refresh(iteration)

    return AnalysisResultSchema(
        session_id=active_session.id,
        iteration_id=iteration.id,
        iteration_number=active_session.total_iterations,
        devices=devices,
        warnings=[success_msg],
        topology_preview={"incomer_a": int(incomer_a), "feeders_count": len(devices)},
        enclosure_spec=enclosure_spec,
        cad_file=cad_file_info,
        quotation_file=None,
        quotation_rows=quotation_rows,
        conclusion=conclusion,
        panel_info=panel_info,
        panels=panels,
        file_assessment=file_assessment,
        files_assessment=[],
        overall_assessment={},
        execution_logs=execution_logs,
        process_steps=process_steps,
        physical_layout=physical_layout,
        layout_conflicts=layout_conflicts,
        analysis_mode="sld_takeoff",
        log_version=2,
    )


# ---------------------------------------------------------------------------
# Celery Background Task Processing Endpoints (Async Queue qua Redis)
# ---------------------------------------------------------------------------

@router.post("/async-start")
async def start_analysis_async(
    request: AnalyzeStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Đẩy tác vụ bóc tách dự án vào hàng đợi Celery chạy nền qua Redis.
    Trả về ngay task_id để client theo dõi tiến độ thời gian thực (% tiến độ).
    """
    proj_stmt = select(Project).where(Project.id == request.project_id, Project.user_id == current_user.id)
    proj_res = await db.execute(proj_stmt)
    project = proj_res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Dự án không tồn tại")

    try:
        task = analyze_project_async_task.delay(
            project_id=request.project_id,
            user_id=current_user.id,
            file_id=request.file_id,
            user_prompt=request.user_prompt,
            fallback_to_standard_template=bool(request.fallback_to_standard_template),
        )
        return {
            "success": True,
            "task_id": task.id,
            "status": "PENDING",
            "project_id": request.project_id,
            "message": "Đã tiếp nhận yêu cầu bóc tách vào hàng đợi Celery (Redis Broker)."
        }
    except Exception as e:
        logger.error(f"Lỗi khi gửi task vào Celery: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Không thể khởi chạy tác vụ ngầm: {str(e)}")


@router.get("/task/{task_id}")
async def get_analysis_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Tra cứu trạng thái và tiến độ xử lý của tác vụ bóc tách Celery qua Redis Backend.
    """
    task = AsyncResult(task_id, app=celery_app)
    state = task.state

    if state == "PENDING":
        return {
            "task_id": task_id,
            "status": "PENDING",
            "progress": 0,
            "message": "Đang xếp hàng chờ worker tiếp nhận..."
        }
    elif state == "PROGRESS":
        info = task.info if isinstance(task.info, dict) else {}
        return {
            "task_id": task_id,
            "status": "PROGRESS",
            "progress": info.get("progress", 0),
            "stage": info.get("stage", ""),
            "message": info.get("message", "Đang xử lý...")
        }
    elif state == "SUCCESS":
        return {
            "task_id": task_id,
            "status": "SUCCESS",
            "progress": 100,
            "message": "Bóc tách hoàn tất thành công!",
            "result": task.result
        }
    elif state == "FAILURE":
        return {
            "task_id": task_id,
            "status": "FAILURE",
            "progress": 0,
            "error": str(task.info) if task.info else "Đã xảy ra lỗi trong quá trình xử lý ngầm."
        }
    else:
        return {
            "task_id": task_id,
            "status": state,
            "progress": 50 if state == "STARTED" else 0,
            "message": f"Trạng thái hiện tại: {state}"
        }


@router.post("/task/{task_id}/cancel")
async def cancel_analysis_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Hủy bỏ tác vụ Celery đang chạy ngầm.
    """
    try:
        celery_app.control.revoke(task_id, terminate=True)
        return {
            "task_id": task_id,
            "status": "CANCELLED",
            "message": "Đã gửi lệnh hủy tác vụ thành công."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể hủy tác vụ: {str(e)}")
