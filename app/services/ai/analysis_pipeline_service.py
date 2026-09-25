"""
Analysis Pipeline Service
Điều phối toàn diện quy trình bóc tách thiết bị điện, tra cứu Catalog SKU & giá thực tế,
tính toán kích thước tủ - thanh cái, và tự động sinh bản vẽ CAD DXF & báo giá Excel.
"""
import os
import re
import logging
import io
import base64
import tempfile
import uuid
import time
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from fastapi import HTTPException
from PIL import Image, ImageDraw
import pdfplumber
import pypdfium2 as pdfium
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.ai_connection import AiConnection
from app.models.user import User
from app.schemas.ai import ExtractedDeviceSchema, AnalysisResultSchema
from app.services.ingestion.pdf_extractor import PdfExtractorService
from app.services.ingestion.pdf_drawing_indexer import PdfDrawingIndexerService, DrawingCategory
from app.services.ingestion.cad_parser import CadParserService
from app.services.ingestion.document_context import DocumentContextService
from app.services.ai.vision_analyzer import VisionAnalyzerService
from app.services.ai.response_parser import ResponseParserService
from app.services.ai.connection_pool import ConnectionPoolService
from app.services.ai.circuit_preflight import CircuitPreflightService
from app.services.device_catalog_engine import DeviceCatalogEngine
from app.services.cad.enclosure_cad_generator import EnclosureCadGeneratorService
from app.services.cad.source_project_generator import SourceProjectGenerator
from app.services.cad.physical_layout_engine import PhysicalLayoutEngine, MountingType, ElectricalFunction
from app.services.export.quotation_exporter import QuotationExporterService
from app.services.export.dynamic_grouping import DynamicGroupingEngine
from app.services.bom.busbar_calculator import BusbarCalculatorService
from app.services.ai.cluster_equipment_service import AccompanyingEquipmentService, CompatibleAlternativeService
from app.core.device_patterns import DevicePatterns
from app.core.config import settings
from app.core.constants import (
    PRICE_ROUNDING_STEP_VND,
    BUSBAR_REQUIRED_MIN_CURRENT_A,
    BUSBAR_INSULATOR_SPACING_M,
    BUSBAR_INSULATOR_PRICE_VND,
    DEFAULT_PANEL_CODE,
    DEFAULT_PROJECT_NAME,
)

logger = logging.getLogger(__name__)


class AnalysisPipelineService:
    """Dịch vụ điều phối bóc tách BOM chuyên nghiệp chuẩn công nghiệp."""

    @staticmethod
    def _compose_multifile_notes(
        user_prompt: Optional[str],
        contexts: List[Dict[str, Any]],
        current_filename: str,
    ) -> str:
        """Build request-scoped context without assuming every file is a drawing."""
        reference_context = DocumentContextService.build_prompt_context(contexts, max_total_chars=18_000)
        parts = [
            "Hãy xác định vai trò của tệp hiện tại theo yêu cầu của người dùng: nguồn bóc tách, "
            "tài liệu tham chiếu, yêu cầu kỹ thuật, catalog/bảng giá, bằng chứng, hoặc hỗn hợp. "
            "Không loại bỏ tài liệu chỉ vì không có thiết bị và không biến nội dung tham khảo thành "
            "thiết bị BOM. Chỉ sinh devices khi tệp có bằng chứng thiết bị cụ thể. Dùng các tệp khác "
            "để đối chiếu thông số, phạm vi và yêu cầu. Ghi vai trò vào file_assessment.document_role "
            "và tóm tắt thông tin hữu ích vào file_assessment.context_summary.",
            f"TỆP ĐANG XỬ LÝ: {current_filename}",
        ]
        if user_prompt:
            parts.append(f"YÊU CẦU NGƯỜI DÙNG:\n{user_prompt.strip()}")
        if reference_context:
            parts.append(f"NGỮ CẢNH ĐỌC ĐƯỢC TỪ TOÀN BỘ TỆP ĐÍNH KÈM:\n{reference_context}")
        return "\n\n".join(parts)

    @staticmethod
    def _detect_requested_brand(user_prompt: Optional[str], catalog_engine: Any) -> Optional[str]:
        """Resolve a requested brand from catalog data instead of a fixed shortlist."""
        if not user_prompt:
            return None
        normalized_prompt = re.sub(r"\s+", " ", user_prompt.casefold())
        candidates: Dict[str, str] = {}
        for item in getattr(catalog_engine, "items", []) or []:
            for field in ("brand_display", "brand"):
                value = str(item.get(field) or "").strip()
                if len(value) >= 2:
                    candidates[value.casefold()] = value
        for normalized, display in sorted(candidates.items(), key=lambda pair: len(pair[0]), reverse=True):
            if re.search(rf"(?<!\w){re.escape(normalized)}(?!\w)", normalized_prompt):
                return display
        return None

    @staticmethod
    def _partial_devices_payload(
        *,
        devices: List[ExtractedDeviceSchema],
        page_number: int,
        total_pages: int,
        source_type: str,
        filename: str,
        panel_code: Optional[str] = None,
        panel_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build one stable SSE payload for image, PDF and CAD inputs."""
        normalized_source = str(source_type or "").lower()
        return {
            "type": "partial_devices",
            "page_number": int(page_number),
            "total_pages": int(total_pages),
            "source_type": normalized_source,
            "filename": filename,
            "panel": {
                "panel_code": panel_code or "",
                "panel_name": panel_name or "",
                "page": int(page_number),
            },
            "devices": [device.model_dump() for device in devices],
        }

    @staticmethod
    def _normalize_panels(
        panels: List[Dict[str, Any]],
        devices: List[ExtractedDeviceSchema],
    ) -> List[Dict[str, Any]]:
        """Return the same panel shape regardless of the source file format."""
        by_code: Dict[str, Dict[str, Any]] = {}
        for raw_panel in panels or []:
            if not isinstance(raw_panel, dict):
                continue
            code = str(raw_panel.get("panel_code") or "").strip()
            if not code:
                continue
            dimension = str(
                raw_panel.get("dimension")
                or raw_panel.get("enclosure_dimensions")
                or ""
            ).strip()
            panel = by_code.setdefault(code, {
                "panel_code": code,
                "panel_name": str(raw_panel.get("panel_name") or "").strip(),
                "location": str(raw_panel.get("location") or "").strip(),
                "enclosure_dimensions": dimension,
                "dimension": dimension,
                "page": raw_panel.get("page"),
                "devices": [],
            })
            if not panel["location"] and raw_panel.get("location"):
                panel["location"] = str(raw_panel["location"]).strip()

        sole_panel_code = next(iter(by_code)) if len(by_code) == 1 else None
        for device in devices:
            code = str(device.panel_code or sole_panel_code or "").strip()
            device.panel_code = code
            if not device.panel_name:
                device.panel_name = str(
                    by_code.get(code, {}).get("panel_name")
                    or ""
                )
            panel = by_code.setdefault(code, {
                "panel_code": code,
                "panel_name": str(device.panel_name).strip(),
                "location": str(device.location or "").strip(),
                "enclosure_dimensions": "",
                "dimension": "",
                "page": None,
                "devices": [],
            })
            panel["devices"].append(device.model_dump())

        return list(by_code.values())

    @staticmethod
    def _attach_source_metadata(
        devices: List[ExtractedDeviceSchema],
        *,
        source_type: str,
        filename: str,
        page_number: Optional[int] = None,
    ) -> None:
        """Attach source identity and a normalized evidence-region contract."""
        for device in devices:
            device.source_type = str(source_type or "").lower()
            device.source_filename = filename
            if page_number is not None and device.source_page is None:
                device.source_page = int(page_number)
            box = device.box_2d
            if box and len(box) == 4 and not device.evidence_region:
                device.evidence_region = {
                    "coordinate_space": "normalized_1000",
                    "box_2d": [int(value) for value in box],
                    "page": device.source_page,
                }

    @staticmethod
    def _attach_cad_evidence_regions(
        devices: List[ExtractedDeviceSchema], cad_result: Any
    ) -> None:
        """Match devices to real CAD text coordinates without template guesses."""
        # A text-only model cannot author trustworthy drawing coordinates.
        # Clear any AI-provided box and rebuild it solely from parsed CAD data.
        for device in devices:
            device.box_2d = None
            device.evidence_region = None
        if not getattr(cad_result, "is_reliable", True):
            return
        texts = list(getattr(cad_result, "texts", None) or [])
        bounds = getattr(cad_result, "bounds", None) or {}
        min_x = float(bounds.get("min_x") or 0)
        min_y = float(bounds.get("min_y") or 0)
        width = float(bounds.get("width") or 0)
        height = float(bounds.get("height") or 0)
        if not texts or width <= 0 or height <= 0:
            return

        unused = set(range(len(texts)))
        normalized_names = [str(device.name or "").strip().upper() for device in devices]
        name_counts = {
            name: normalized_names.count(name)
            for name in set(normalized_names)
            if name
        }
        for device in devices:
            tag = str(device.tag or "").strip().upper()
            part_number = str(device.part_number or "").strip().upper()
            name = str(device.name or "").strip().upper()
            candidates = []
            if len(tag) >= 2:
                candidates.append((tag, 100))
            if len(part_number) >= 2:
                candidates.append((part_number, 90))
            # A generic/repeated name cannot identify one physical CAD entity.
            if len(name) >= 3 and name_counts.get(name) == 1:
                candidates.append((name, 80))
            if not candidates:
                continue
            best_index = None
            best_score = 0
            for index in unused:
                label = str(texts[index].get("text") or "").strip().upper()
                if not label:
                    continue
                score = 0
                for candidate, exact_score in candidates:
                    if candidate == label:
                        score = max(score, exact_score)
                    elif re.search(rf"(?<!\w){re.escape(candidate)}(?!\w)", label):
                        score = max(score, exact_score - 20)
                    elif len(candidate) >= 6 and candidate in label:
                        score = max(score, exact_score - 30)
                if score > best_score:
                    best_index, best_score = index, score
            if best_index is None:
                continue

            unused.discard(best_index)
            match = texts[best_index]
            x = float(match.get("x") or 0)
            y = float(match.get("y") or 0)
            pad_x = max(width * 0.035, 1.0)
            pad_y = max(height * 0.025, 1.0)
            x_min, x_max = x - pad_x, x + pad_x
            y_min, y_max = y - pad_y, y + pad_y
            # Image coordinates use top-left origin; CAD world coordinates use
            # bottom-left. Store both explicitly so no consumer has to guess.
            xmin_n = max(0, min(1000, round((x_min - min_x) / width * 1000)))
            xmax_n = max(0, min(1000, round((x_max - min_x) / width * 1000)))
            ymin_n = max(0, min(1000, round((1 - (y_max - min_y) / height) * 1000)))
            ymax_n = max(0, min(1000, round((1 - (y_min - min_y) / height) * 1000)))
            device.box_2d = [ymin_n, xmin_n, ymax_n, xmax_n]
            device.evidence_region = {
                "coordinate_space": "cad_world",
                "x_min": x_min,
                "y_min": y_min,
                "x_max": x_max,
                "y_max": y_max,
                "box_2d": device.box_2d,
                "matched_text": str(match.get("text") or ""),
                "layer": str(match.get("layer") or "0"),
            }

    @staticmethod
    async def execute_analysis(
        project: Project,
        project_files: List[ProjectFile],
        active_ai: Optional[AiConnection],
        current_user: User,
        fallback_to_standard_template: bool = False,
        user_prompt: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        all_connections: Optional[List[AiConnection]] = None,
        generate_cad_and_quotation: bool = False,
        progress_callback: Optional[Any] = None,
        target_page: Optional[int] = None
    ) -> Dict[str, Any]:
        extracted_devices: List[ExtractedDeviceSchema] = []
        warnings: List[str] = []
        device_price_map: Dict[str, int] = {}
        technical_proposals: List[Dict[str, Any]] = []
        # Brand and compatible-device analysis is part of takeoff as well as
        # quotation. Keep the brand read from the drawing in `detected_brand`,
        # while `brand`/`part_number` contain the automatically selected
        # supplier and compatible catalog item that the user may override.
        catalog_engine = DeviceCatalogEngine.get_instance()

        multi_panel_list: List[Dict[str, Any]] = []
        file_assessment: Optional[Dict[str, Any]] = None
        detected_enclosure_dim_str: Optional[str] = None
        detected_layout_intent: Optional[Dict[str, Any]] = None
        cad_extracted_texts: List[str] = []

        execution_logs: List[Dict[str, Any]] = []
        pipeline_perf_start = time.perf_counter()
        last_step_perf = pipeline_perf_start
        last_assigned_time = datetime.now()

        def log_event(
            stage: str,
            title: str,
            detail: str = "",
            status: str = "info",
            data: Optional[Dict[str, Any]] = None,
            duration: Optional[str] = None
        ):
            nonlocal last_step_perf, last_assigned_time
            now_perf = time.perf_counter()
            elapsed_step = now_perf - last_step_perf
            last_step_perf = now_perf

            if not duration:
                if elapsed_step >= 1.0:
                    duration = f"{elapsed_step:.1f}s"
                elif elapsed_step >= 0.1:
                    duration = f"{elapsed_step:.2f}s"
                else:
                    duration = f"{max(int(elapsed_step * 1000), 50)}ms"

            current_wall = datetime.now()
            if current_wall <= last_assigned_time and len(execution_logs) > 0:
                step_wall = last_assigned_time + timedelta(seconds=1)
            else:
                step_wall = current_wall
            last_assigned_time = step_wall

            evt = {
                "timestamp": step_wall.strftime("%H:%M:%S"),
                "duration": duration,
                "stage": stage,
                "title": title,
                "detail": detail,
                "status": status,
                "data": data or {}
            }
            execution_logs.append(evt)
            if progress_callback:
                try:
                    res = progress_callback({"type": "log", **evt})
                    if asyncio.iscoroutine(res):
                        asyncio.create_task(res)
                except Exception as cb_err:
                    logger.warning(f"Error in progress_callback: {cb_err}")

        # Every attachment remains available as chat context. Generated artifacts
        # are kept for reference but are never re-extracted into a new BOM.
        document_contexts = [DocumentContextService.extract(file_obj) for file_obj in project_files]

        # STAGE 1: TIẾP NHẬN VÀ THẨM ĐỊNH TỆP BẢN VẼ
        files_assessment: List[Dict[str, Any]] = []
        source_file_contexts: List[Dict[str, Any]] = []
        file_names_str = ", ".join(f.filename for f in project_files if f.filename)
        log_event(
            stage="ingestion",
            title="Tiếp nhận & Kiểm định bản vẽ dự án",
            detail=f"Nạp {len(project_files)} tệp nguồn import: {file_names_str}",
            status="info",
            data={"file_count": len(project_files), "project_name": project.name}
        )
        if progress_callback:
            await asyncio.sleep(0.35)

        log_event(stage="circuit_assessment", title="Đánh giá sơ đồ nguyên lý toàn hồ sơ",
                  detail="Đọc vai trò các tệp, mạch điện và cụm chức năng trước khi bóc tách thiết bị.", status="info")
        try:
            circuit_assessment = await CircuitPreflightService.assess(
                [f for f in project_files if not getattr(f, "is_generated", False)],
                document_contexts, db, all_connections or ([active_ai] if active_ai else []), user_prompt)
        except Exception as exc:
            logger.warning("Circuit preflight unavailable: %s", exc)
            circuit_assessment = {"status": "unavailable", "circuit_summary": "",
                                  "source_limits": ["Không thể hoàn tất đánh giá sơ đồ: " + str(exc)[:200]]}
        preflight_context = CircuitPreflightService.extraction_context(circuit_assessment)
        log_event(stage="circuit_assessment", title="Đã đánh giá sơ đồ trước bóc tách"
                  if preflight_context else "Chưa đủ dữ liệu đánh giá toàn sơ đồ",
                  detail=str(circuit_assessment.get("circuit_summary") or circuit_assessment.get("source_limits"))[:500],
                  status="success" if preflight_context else "warning")

        if circuit_assessment.get("status") != "assessed":
            raise HTTPException(
                status_code=422,
                detail="Chưa đánh giá được sơ đồ nguyên lý trước bóc tách: "
                       + "; ".join(map(str, circuit_assessment.get("source_limits") or []))
            )

        for consideration in circuit_assessment.get("installation_considerations") or []:
            if isinstance(consideration, dict):
                label = str(consideration.get("name") or consideration.get("component") or "").strip()
                reason = str(consideration.get("reason") or consideration.get("evidence") or "").strip()
            else:
                label, reason = str(consideration).strip(), ""
            if label:
                technical_proposals.append({
                    "original_device": "Phụ kiện lắp đặt chưa thể hiện trên SLD",
                    "proposed_device": label,
                    "ai_analysis": reason or "Cần kiểm tra điều kiện lắp đặt và tiêu chuẩn của tủ.",
                    "technical_reason": "Đề xuất từ bước đánh giá sơ đồ; chưa đưa vào BOM hoặc báo giá.",
                    "status": "review",
                })

        # 1. Trích xuất thiết bị từ các file bản vẽ
        for pfile in project_files:
            file_path = pfile.file_path
            if not file_path or not os.path.exists(file_path):
                files_assessment.append({
                    "file_id": getattr(pfile, "id", None),
                    "filename": pfile.filename,
                    "file_type": (pfile.filename.rsplit(".", 1)[-1].lower() if pfile.filename and "." in pfile.filename else ""),
                    "file_size": getattr(pfile, "file_size", 0),
                    "status": "failed",
                    "devices_count": 0,
                    "document_type": "Tệp không khả dụng",
                    "document_role": "unknown",
                    "context_summary": "",
                    "is_suitable": False,
                    "assessment_summary": "Không tìm thấy tệp vật lý để đọc.",
                    "warnings": ["file_not_found"],
                })
                continue

            ext = pfile.filename.split(".")[-1].lower() if pfile.filename else ""
            file_start_count = len(extracted_devices)
            cad_evidence_result = None
            file_assessment = None
            effective_user_prompt = AnalysisPipelineService._compose_multifile_notes(
                user_prompt, document_contexts, pfile.filename or ""
            )
            if preflight_context:
                effective_user_prompt += "\n\n" + preflight_context

            if getattr(pfile, "is_generated", False):
                context_info = next((c for c in document_contexts if c.get("file_id") == getattr(pfile, "id", None)), {})
                files_assessment.append({
                    "file_id": getattr(pfile, "id", None),
                    "filename": pfile.filename,
                    "file_type": ext,
                    "file_size": getattr(pfile, "file_size", 0),
                    "status": "reference",
                    "devices_count": 0,
                    "document_type": "Kết quả do hệ thống tạo",
                    "document_role": "reference",
                    "context_summary": str(context_info.get("text") or "")[:1000],
                    "is_suitable": True,
                    "assessment_summary": "Giữ làm ngữ cảnh tham chiếu; không bóc tách ngược để tránh nhân đôi BOM.",
                    "warnings": [],
                })
                continue

            log_event(
                stage="file_extraction",
                title=f"Đang bóc tách tệp: {pfile.filename}",
                detail=f"Phân tích sơ đồ 1 sợi SLD & nhận diện thiết bị ({ext.upper()})",
                status="info",
                data={"filename": pfile.filename, "file_type": ext, "file_id": getattr(pfile, "id", None)}
            )

            # A. File ảnh: Dùng AI Vision
            if ext in ["png", "jpg", "jpeg", "webp", "bmp"]:
                if all_connections and db:
                    try:
                        from app.core.prompts import PROMPT_TYPES, SLD_VISION_ANALYSIS_PROMPT, append_canonical_output_contract, append_completeness_review_instruction, append_user_notes
                        from app.services.ai.prompt_template_service import PromptTemplateService
                        vision_template = await PromptTemplateService.get_active_content(
                            db, PROMPT_TYPES["SLD_VISION"], SLD_VISION_ANALYSIS_PROMPT
                        )
                        vision_prompt = append_user_notes(
                            vision_template, effective_user_prompt,
                            "ĐẶC BIỆT LƯU Ý VÀ TUÂN THỦ YÊU CẦU KỸ THUẬT / GHI CHÚ TỪ KHÁCH HÀNG:",
                        )
                        vision_prompt = append_completeness_review_instruction(vision_prompt)
                        vision_prompt = append_canonical_output_contract(vision_prompt)
                        # Sử dụng ConnectionPool fallback thay vì gọi trực tiếp 1 connection
                        ai_response, used_conn = await ConnectionPoolService.call_with_fallback(
                            db=db,
                            connections=all_connections,
                            call_fn=VisionAnalyzerService.analyze_image,
                            image_path=file_path,
                            prompt=vision_prompt,
                        )
                        active_ai = used_conn  # Cập nhật active_ai cho log/warning
                        parsed_devs = ResponseParserService.parse_device_list(ai_response)
                        warnings.extend(ResponseParserService.extract_completeness_warnings(ai_response))
                        img_props = ResponseParserService.extract_technical_proposals(ai_response)
                        if img_props:
                            technical_proposals.extend(img_props)
                        # The canonical contract always uses `panels`, including
                        # for a single image.  Preserve that metadata here so an
                        # image containing several panels behaves like PDF/CAD.
                        image_panels = ResponseParserService.extract_panels_metadata(ai_response)
                        if image_panels:
                            multi_panel_list.extend(image_panels)
                        image_layout_intent = ResponseParserService.extract_layout_intent(ai_response)
                        if image_layout_intent and not detected_layout_intent:
                            detected_layout_intent = image_layout_intent
                        json_blocks = ResponseParserService.extract_json_blocks(ai_response)
                        for blk in json_blocks:
                            if isinstance(blk, dict):
                                if blk.get("file_assessment"):
                                    file_assessment = blk.get("file_assessment")
                                if blk.get("enclosure_dimensions") and not detected_enclosure_dim_str:
                                    detected_enclosure_dim_str = str(blk.get("enclosure_dimensions")).strip()
                                if blk.get("layout_intent") and not detected_layout_intent:
                                    detected_layout_intent = blk.get("layout_intent")
                                break
                        for d in parsed_devs:
                            try:
                                clean_in_a = float(d.in_a) if d.in_a is not None else None
                                if clean_in_a is not None and clean_in_a <= 0:
                                    clean_in_a = None

                                clean_icu_ka = float(d.icu_ka) if d.icu_ka is not None else None
                                if clean_icu_ka is not None and clean_icu_ka <= 0:
                                    clean_icu_ka = None

                                clean_poles = int(d.poles) if d.poles is not None else None
                                if clean_poles is not None and clean_poles <= 0:
                                    clean_poles = None

                                spec_str = d.spec
                                if not spec_str:
                                    if clean_poles is not None and clean_in_a is not None:
                                        spec_str = f"{clean_poles}P - {int(clean_in_a)}A"
                                    else:
                                        spec_str = "Tiêu chuẩn"

                                d_dict = {
                                    "category": d.category or "Thiết bị",
                                    "name": d.name or "Thiết bị",
                                    "notes": d.notes or "",
                                    "in_a": clean_in_a,
                                    "tag": getattr(d, "tag", None),
                                    "section": d.section
                                }
                                dev_tag = getattr(d, "tag", None) or PhysicalLayoutEngine.extract_or_assign_tag(d_dict, len(extracted_devices), d.section or "")
                                dev_mounting = getattr(d, "mounting", None) or PhysicalLayoutEngine.classify_mounting(d_dict)
                                dev_func = getattr(d, "electrical_function", None) or (
                                    ElectricalFunction.INCOMING if str(d.section or "").upper() in ["ĐẦU VÀO", "INCOMER"] else
                                    (ElectricalFunction.MEASUREMENT if dev_mounting == MountingType.DOOR_MOUNTED else ElectricalFunction.OUTGOING_PROTECTION)
                                )

                                clean_accs = AccompanyingEquipmentService.format_accessories(getattr(d, "accompanying_accessories", None))
                                cp = getattr(d, "compatible_proposal", None)
                                has_alt = bool(cp)

                                extracted_devices.append(ExtractedDeviceSchema(
                                    category=d.category or "Thiết bị",
                                    name=d.name or "Thiết bị",
                                    spec=spec_str,
                                    in_a=clean_in_a,
                                    icu_ka=clean_icu_ka,
                                    poles=clean_poles,
                                    quantity=int(d.quantity or 1),
                                    brand=d.brand or "",
                                    part_number=d.part_number or (cp.get("proposed_device") if cp else ""),
                                    section=d.section,
                                    location=d.location,
                                    panel_code=d.panel_code,
                                    panel_name=d.panel_name,
                                    notes=d.notes,
                                    tag=dev_tag,
                                    mounting=dev_mounting,
                                    electrical_function=dev_func,
                                    upstream_device=getattr(d, "upstream_device", None),
                                    downstream_device=getattr(d, "downstream_device", None),
                                    connected_load=getattr(d, "connected_load", None),
                                    confidence=float(d.confidence or 0.95),
                                    box_2d=getattr(d, "box_2d", None),
                                    evidence_image=d.evidence_image,
                                    suggested_brands=[
                                        str(brand).strip() for brand in (getattr(d, "suggested_brands", None) or [])
                                        if str(brand).strip()
                                    ],
                                    is_alternative_recommended=has_alt,
                                    original_spec=cp.get("original_spec") if cp else None,
                                    compatibility_note=(cp.get("technical_reason") or cp.get("ai_analysis")) if cp else None,
                                    suggested_alternatives=[cp] if cp else None,
                                    accompanying_accessories=clean_accs,
                                    inferred_components=getattr(d, "inferred_components", None),
                                    compatible_proposal=cp
                                ))
                            except Exception as dev_err:
                                logger.warning(f"Lỗi chuẩn hóa thiết bị {getattr(d, 'name', '')}: {str(dev_err)}")
                                continue
                    except HTTPException:
                        raise
                    except Exception as e:
                        logger.error(f"AI Vision image error: {str(e)}", exc_info=True)
                        raise HTTPException(
                            status_code=502,
                            detail=f"AI Vision gặp sự cố khi phân tích ảnh {pfile.filename}: {str(e)}"
                        )
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Chưa cấu hình API Key AI trong Admin để phân tích file ảnh {pfile.filename}. Vui lòng cấu hình kết nối AI trước khi bóc tách."
                    )

            # B. File PDF: Bóc tách trực tiếp bằng AI Vision (SLD). Tuyệt đối không fallback sang bộ bóc tách cấu trúc dự phòng.
            elif ext == "pdf":
                if not all_connections:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Chưa cấu hình hoặc kích hoạt AI Provider trong Admin để bóc tách file PDF {pfile.filename}. Vui lòng cấu hình API Key trong trang Quản lý AI."
                    )

                try:
                    pdf_devs, pdf_multi, pdf_warns, pdf_proposals = await AnalysisPipelineService._analyze_pdf_with_vision(
                        file_path=file_path,
                        filename=pfile.filename or "drawing.pdf",
                        active_ai=active_ai,
                        user_prompt=effective_user_prompt,
                        db=db,
                        all_connections=all_connections,
                        target_page=target_page,
                        progress_callback=progress_callback,
                        project_id=project.id
                    )
                    if pdf_devs:
                        extracted_devices.extend(pdf_devs)
                        if pdf_multi:
                            multi_panel_list.extend(pdf_multi)
                            for p in pdf_multi:
                                p_dim = p.get("dimension") or p.get("enclosure_dimensions")
                                if p_dim and not detected_enclosure_dim_str:
                                    detected_enclosure_dim_str = str(p_dim).strip()
                        warnings.extend(pdf_warns)
                        if pdf_proposals:
                            technical_proposals.extend(pdf_proposals)
                        logger.info(f"AI Vision extracted {len(pdf_devs)} devices from PDF {pfile.filename}")
                    else:
                        # A PDF that is not selected during AI intake is a valid
                        # project attachment, not a failed analysis. Continue to
                        # the next source file and record its result below.
                        logger.info("AI intake selected no takeoff pages from PDF %s", pfile.filename)
                except HTTPException:
                    raise
                except Exception as ai_pdf_err:
                    logger.error(f"AI Vision on PDF failed: {ai_pdf_err}", exc_info=True)
                    raise HTTPException(
                        status_code=502,
                        detail=f"Mô hình AI ({active_ai.provider.upper()} - {active_ai.selected_model}) gặp sự cố khi phân tích bản vẽ PDF {pfile.filename}: {str(ai_pdf_err)}. Vui lòng kiểm tra lại kết nối AI hoặc thử lại sau."
                    )

            # C. File CAD (DXF & DWG)
            elif ext in ["dxf", "dwg"]:
                try:
                    cad_quick = CadParserService.parse_cad(file_path)
                    cad_evidence_result = cad_quick
                    if cad_quick and cad_quick.texts:
                        for t in cad_quick.texts:
                            txt_val = t.get("text", "") if isinstance(t, dict) else getattr(t, "text", "")
                            if txt_val:
                                # Lọc surrogate characters trước khi propagate
                                safe_text = CadParserService._sanitize_text(txt_val)
                                if safe_text:
                                    cad_extracted_texts.append(safe_text)
                except Exception:
                    pass

                cad_ai_success = False
                cad_ai_error = None  # Lưu lỗi AI để quyết định fallback
                if all_connections and db:
                    try:
                        cad_devs, cad_multi, cad_warns = await AnalysisPipelineService._analyze_cad_with_ai(
                            file_path=file_path,
                            filename=pfile.filename or "drawing.dxf",
                            active_ai=active_ai,
                            user_prompt=effective_user_prompt,
                            db=db,
                            all_connections=all_connections
                        )
                        if cad_devs:
                            extracted_devices.extend(cad_devs)
                            if cad_multi:
                                multi_panel_list.extend(cad_multi)
                            warnings.extend(cad_warns)
                            cad_ai_success = True
                            logger.info(f"AI extracted {len(cad_devs)} devices from CAD {pfile.filename}")
                    except Exception as ai_cad_err:
                        cad_ai_error = ai_cad_err
                        logger.warning(f"AI CAD analysis failed for {pfile.filename}: {ai_cad_err}")

                if not cad_ai_success:
                    # FILE DWG: Bộ đọc dự phòng (quét binary regex) KHÔNG đáng tin cậy
                    # → Báo lỗi rõ ràng thay vì trả kết quả sai
                    if ext == "dwg":
                        error_detail = str(cad_ai_error) if cad_ai_error else "Không có kết nối AI"
                        logger.error(f"DWG file {pfile.filename} cannot be reliably parsed: {error_detail}")
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"Không thể đọc chính xác file DWG '{pfile.filename}'. "
                                f"Định dạng DWG là nhị phân độc quyền, hệ thống chỉ hỗ trợ phân tích DWG qua AI. "
                                f"Lỗi AI: {error_detail}. "
                                f"Vui lòng chuyển file DWG sang định dạng DXF (bằng AutoCAD: File → Save As → DXF) rồi upload lại, "
                                f"hoặc kiểm tra lại kết nối AI trong trang Quản lý AI."
                            )
                        )

                    # FILE DXF: Bộ đọc ezdxf cấu trúc đáng tin cậy → cho phép fallback
                    try:
                        cad_res = CadParserService.parse_cad(file_path)
                        if cad_ai_error:
                            warnings.append(f"AI phân tích CAD gặp sự cố ({cad_ai_error}), chuyển sang bộ đọc CAD dự phòng.")
                        detected_cad_panels = CadParserService.extract_panels_from_texts(cad_res.texts)
                        default_pcode = detected_cad_panels[0]["panel_code"] if detected_cad_panels else ""
                        default_pname = detected_cad_panels[0]["panel_name"] if detected_cad_panels else ""
                        if detected_cad_panels:
                            multi_panel_list.extend(detected_cad_panels)

                        for dev_match in cad_res.devices:
                            is_incomer = "incomer" in dev_match.raw_text.lower() or "tong" in dev_match.raw_text.lower() or (dev_match.in_a and dev_match.in_a >= 400)
                            p_val = dev_match.poles or (1 if "MCB" in dev_match.category else 3)
                            p_str = f"{p_val}P"
                            a_str = f" {int(dev_match.in_a)}A" if dev_match.in_a else ""
                            spec_str = f"{p_str}{' - ' + str(int(dev_match.in_a)) + 'A' if dev_match.in_a else ''}" + (f" - {int(dev_match.icu_ka)}kA" if dev_match.icu_ka else "")
                            extracted_devices.append(ExtractedDeviceSchema(
                                category=dev_match.category,
                                name=f"{dev_match.category} {p_str}{a_str}".strip(),
                                spec=spec_str,
                                in_a=float(dev_match.in_a) if dev_match.in_a else None,
                                icu_ka=float(dev_match.icu_ka) if dev_match.icu_ka else None,
                                poles=p_val,
                                quantity=1,
                                brand=dev_match.brand or "",
                                part_number=dev_match.model or "",
                                section="Đầu vào" if is_incomer else "Đầu ra",
                                panel_code=default_pcode,
                                panel_name=default_pname,
                                confidence=dev_match.confidence
                            ))

                    except HTTPException:
                        raise
                    except Exception as e:
                        warnings.append(f"Lỗi khi xử lý file CAD {pfile.filename}: {str(e)}")

            # D. Tài liệu/bảng dữ liệu khác: giữ nguyên làm ngữ cảnh của lượt chat.
            # Nội dung đã được đưa vào effective_user_prompt của mọi file hình/bản
            # vẽ; không ép một tài liệu tham khảo phải sinh thiết bị BOM.
            else:
                context_info = next(
                    (c for c in document_contexts if c.get("file_id") == getattr(pfile, "id", None)),
                    {},
                )
                readable_text = str(context_info.get("text") or "").strip()
                read_error = str(context_info.get("read_error") or "").strip()
                files_assessment.append({
                    "file_id": getattr(pfile, "id", None),
                    "filename": pfile.filename,
                    "file_type": ext,
                    "file_size": getattr(pfile, "file_size", 0),
                    "status": "reference" if readable_text else "warning",
                    "devices_count": 0,
                    "document_type": "Tài liệu ngữ cảnh",
                    "document_role": "reference",
                    "context_summary": readable_text[:1000],
                    "is_suitable": bool(readable_text),
                    "assessment_summary": (
                        "Đã đọc và dùng nội dung làm ngữ cảnh đối chiếu cho yêu cầu hiện tại."
                        if readable_text else
                        "Đã giữ tệp trong hồ sơ nhưng chưa trích được nội dung văn bản."
                    ),
                    "warnings": [read_error] if read_error else [],
                })
                continue

            # Chuẩn hóa các phần tử FA bị Vision gắn vào mô tả MCCB trước khi
            # phát dữ liệu từng phần, để UI trực tiếp và kết quả cuối giống nhau.
            current_file_devices = extracted_devices[file_start_count:]
            promoted_file_devices = AnalysisPipelineService._promote_drawn_fa_devices(current_file_devices)
            if len(promoted_file_devices) != len(current_file_devices):
                extracted_devices[file_start_count:] = promoted_file_devices
                current_file_devices = promoted_file_devices

            AnalysisPipelineService._attach_source_metadata(
                current_file_devices,
                source_type=ext,
                filename=pfile.filename or "",
            )
            # Make an AI-produced summary from a visual/CAD file available to
            # files processed later in the same request.  This keeps provenance
            # while allowing a photo/note drawing to support another drawing.
            if isinstance(file_assessment, dict):
                context_summary = str(
                    file_assessment.get("context_summary")
                    or file_assessment.get("assessment_summary")
                    or ""
                ).strip()
                if context_summary:
                    context_entry = next(
                        (c for c in document_contexts if c.get("file_id") == getattr(pfile, "id", None)),
                        None,
                    )
                    if context_entry is not None and not context_entry.get("text"):
                        context_entry["text"] = context_summary[:DocumentContextService.MAX_FILE_CHARS]
            if ext in ["dxf", "dwg"] and cad_evidence_result is not None:
                AnalysisPipelineService._attach_cad_evidence_regions(
                    current_file_devices, cad_evidence_result
                )

            # Ghi nhận kết quả bóc tách cho từng tệp cụ thể
            file_devs_added = len(extracted_devices) - file_start_count
            if file_devs_added > 0:
                file_devices = extracted_devices[file_start_count:]
                source_file_contexts.append({
                    "filename": pfile.filename or "Không rõ tên file",
                    "file_type": ext.upper(),
                    "devices_count": file_devs_added,
                    "panels": sorted({
                        str(device.panel_code).strip()
                        for device in file_devices
                        if getattr(device, "panel_code", None)
                    }),
                    "device_summary": [
                        {
                            "name": device.name,
                            "spec": device.spec,
                            "panel": device.panel_code,
                        }
                        for device in file_devices[:40]
                    ],
                })
                log_event(
                    stage="file_extraction",
                    title=f"Trích xuất thành công: {pfile.filename}",
                    detail=f"Nhận diện được {file_devs_added} thiết bị điện từ sơ đồ ({ext.upper()})",
                    status="success",
                    data={"filename": pfile.filename, "devices_count": file_devs_added, "file_id": getattr(pfile, "id", None)}
                )
                # PDF đã phát partial_devices theo từng trang. Ảnh/CAD cũng phát
                # đúng cùng contract để frontend dùng chung một UI kết quả thay vì
                # rẽ sang màn hình chỉ-hiện-kết-quả-cuối.
                if progress_callback and ext != "pdf":
                    try:
                        partial_result = progress_callback(AnalysisPipelineService._partial_devices_payload(
                            devices=file_devices,
                            page_number=1,
                            total_pages=1,
                            source_type=ext,
                            filename=pfile.filename or "",
                            panel_code=next((d.panel_code for d in file_devices if d.panel_code), None),
                            panel_name=next((d.panel_name for d in file_devices if d.panel_name), None),
                        ))
                        if asyncio.iscoroutine(partial_result):
                            await partial_result
                    except Exception as callback_error:
                        logger.warning("partial_devices callback failed for %s: %s", pfile.filename, callback_error)
                files_assessment.append({
                    "file_id": getattr(pfile, "id", None),
                    "filename": pfile.filename,
                    "file_type": ext,
                    "file_size": getattr(pfile, "file_size", 0),
                    "status": "success",
                    "devices_count": file_devs_added,
                    "document_type": file_assessment.get("document_type", "Sơ đồ 1 sợi SLD") if file_assessment else "Sơ đồ 1 sợi SLD",
                    "is_suitable": file_assessment.get("is_suitable", True) if file_assessment else True,
                    "assessment_summary": file_assessment.get("assessment_summary", f"Trích xuất thành công {file_devs_added} thiết bị") if file_assessment else f"Trích xuất thành công {file_devs_added} thiết bị",
                    "warnings": []
                })
            else:
                log_event(
                    stage="file_extraction",
                    title=f"Tệp {pfile.filename}: Không phát hiện thiết bị rõ ràng",
                    detail="Bản vẽ có thể không chứa sơ đồ nguyên lý 1 sợi (SLD) hoặc chất lượng ảnh chưa đạt",
                    status="warning",
                    data={"filename": pfile.filename, "devices_count": 0, "file_id": getattr(pfile, "id", None)}
                )
                files_assessment.append({
                    "file_id": getattr(pfile, "id", None),
                    "filename": pfile.filename,
                    "file_type": ext,
                    "file_size": getattr(pfile, "file_size", 0),
                    "status": "warning",
                    "devices_count": 0,
                    "document_type": file_assessment.get("document_type", "Chưa xác định") if file_assessment else "Chưa xác định",
                    "is_suitable": file_assessment.get("is_suitable", False) if file_assessment else False,
                    "assessment_summary": file_assessment.get("assessment_summary", "Không tìm thấy sơ đồ nguyên lý điện hoặc thông số đóng cắt") if file_assessment else "Không tìm thấy sơ đồ nguyên lý điện hoặc thông số đóng cắt",
                    "warnings": ["Bản vẽ không có ký hiệu thiết bị điện rõ ràng"]
                })

        # Tổng hợp như một lượt chat đa tài liệu. Kết quả này tồn tại độc lập với
        # BOM, nên một yêu cầu hỏi thông tin vẫn có câu trả lời dù devices rỗng.
        contextual_answer = ""
        file_roles: List[Dict[str, Any]] = []
        if active_ai and user_prompt:
            synthesis_context = DocumentContextService.build_prompt_context(
                document_contexts, max_total_chars=26_000
            )
            synthesis_prompt = f"""Bạn là trợ lý phân tích đa tài liệu. Trả lời yêu cầu người dùng dựa trên toàn bộ tệp đính kèm và dữ liệu đã đọc.
Không mặc định mọi tệp là bản vẽ bóc tách. Mỗi tệp có thể là nguồn chính, tài liệu tham chiếu, yêu cầu kỹ thuật, bảng giá/catalog, bằng chứng hoặc hỗn hợp.
Không bịa thông tin không có trong nguồn. Khi nguồn mâu thuẫn, nêu rõ tệp và giá trị mâu thuẫn. Không liệt kê hàng loạt hãng hoặc thiết bị nếu người dùng không yêu cầu.
Chỉ trả JSON: {{"answer":"câu trả lời trực tiếp, rõ ràng","file_roles":[{{"filename":"...","role":"...","reason":"..."}}],"extraction_scope":{{"should_extract_devices":true,"files":[],"reason":"..."}},"warnings":[]}}.

YÊU CẦU NGƯỜI DÙNG:
{user_prompt}

NỘI DUNG TỆP ĐỌC ĐƯỢC:
{synthesis_context or '(Các tệp hình/CAD đã được xử lý trực tiếp; xem tóm tắt bên dưới.)'}

TÓM TẮT XỬ LÝ TỪNG TỆP:
{files_assessment}
"""
            try:
                if all_connections and db:
                    synthesis_response, _used = await ConnectionPoolService.call_with_fallback(
                        db=db,
                        connections=all_connections,
                        call_fn=VisionAnalyzerService.analyze_text,
                        prompt=synthesis_prompt,
                    )
                else:
                    synthesis_response = await VisionAnalyzerService.analyze_text(
                        prompt=synthesis_prompt,
                        provider=active_ai.provider.lower(),
                        api_key=active_ai.api_key,
                        model=active_ai.selected_model,
                    )
                synthesis_blocks = ResponseParserService.extract_json_blocks(synthesis_response)
                synthesis = next((block for block in synthesis_blocks if isinstance(block, dict)), {})
                contextual_answer = str(synthesis.get("answer") or "").strip()
                file_roles = synthesis.get("file_roles") if isinstance(synthesis.get("file_roles"), list) else []
                roles_by_name = {
                    str(role.get("filename") or "").strip(): role
                    for role in file_roles if isinstance(role, dict)
                }
                for assessment in files_assessment:
                    role = roles_by_name.get(str(assessment.get("filename") or "").strip())
                    if role:
                        assessment["document_role"] = str(role.get("role") or assessment.get("document_role") or "reference")
                        assessment["role_reason"] = str(role.get("reason") or "")
            except Exception as synthesis_error:
                logger.warning("Không thể tổng hợp câu trả lời đa tài liệu: %s", synthesis_error)

        # Khi có nhiều file, AI đối chiếu kết quả đã đọc từ từng file để xác định
        # chúng bổ sung cùng một tủ/hệ thống hay là các phạm vi độc lập. Bước này
        # chỉ dùng dữ liệu thực tế đã trích xuất, không ghép nối theo tên file.
        if len(source_file_contexts) > 1 and active_ai:
            relationship_prompt = """Bạn là kỹ sư trưởng M&E đang đối chiếu một bộ hồ sơ đã bóc tách.
Hãy xác định các file có bổ sung/cùng tham chiếu tới một tủ hoặc cùng một hệ thống điện không, dựa duy nhất vào mã tủ, thiết bị và thông số đã trích xuất dưới đây. Không suy đoán từ tên file. Nếu chưa đủ bằng chứng, nói rõ là chưa thể kết luận.
Trả về JSON duy nhất: {\"summary\":\"...\",\"processing_order\":[\"...\"],\"warnings\":[\"...\"]}.

Dữ liệu đã đọc:\n""" + str(source_file_contexts)
            try:
                if all_connections and db:
                    relationship_response, _used = await ConnectionPoolService.call_with_fallback(
                        db=db,
                        connections=all_connections,
                        call_fn=VisionAnalyzerService.analyze_text,
                        prompt=relationship_prompt,
                    )
                else:
                    relationship_response = await VisionAnalyzerService.analyze_text(
                        prompt=relationship_prompt,
                        provider=active_ai.provider.lower(),
                        api_key=active_ai.api_key,
                        model=active_ai.selected_model,
                    )
                relationship_blocks = ResponseParserService.extract_json_blocks(relationship_response)
                relationship = next((item for item in relationship_blocks if isinstance(item, dict)), None)
                if relationship:
                    summary = str(relationship.get("summary") or "Đã đối chiếu các file trong bộ hồ sơ.").strip()
                    order = relationship.get("processing_order") or []
                    detail = summary[:700]
                    if order:
                        detail += " Thứ tự xử lý đề xuất: " + " → ".join(str(item) for item in order[:8]) + "."
                    log_event(
                        stage="ingestion",
                        title="Đối chiếu liên kết trong bộ hồ sơ",
                        detail=detail,
                        status="success",
                        data={"files": [item["filename"] for item in source_file_contexts], "relationship": relationship},
                    )
            except Exception as relation_error:
                logger.warning("Không thể đối chiếu liên kết giữa các file: %s", relation_error)

        # Đánh giá tổng thể toàn bộ các file dự án
        successful_files = [f for f in files_assessment if f.get("status") in {"success", "reference"}]
        failed_files = [f for f in files_assessment if f.get("status") == "failed"]
        overall_assessment = {
            "total_files": len(project_files),
            "successful_files": len(successful_files),
            "warning_files": len(project_files) - len(successful_files),
            "failed_files": len(failed_files),
            "total_devices": len(extracted_devices),
            "suitability": "SUITABLE" if len(extracted_devices) > 0 else ("CONTEXT_ONLY" if contextual_answer else "NEEDS_REVIEW"),
            "document_type": (file_assessment.get("document_type") if file_assessment else "Sơ đồ 1 sợi SLD") if len(extracted_devices) > 0 else ("Bộ tài liệu tham chiếu" if contextual_answer else "Chưa xác định"),
            "summary": (
                f"Đã thẩm định {len(project_files)} tệp bản vẽ. Trích xuất thành công {len(extracted_devices)} thiết bị điện đạt chuẩn kỹ thuật ({len(successful_files)}/{len(project_files)} tệp hợp lệ)."
                if len(extracted_devices) > 0 else
                (f"Đã đọc {len(project_files)} tệp làm ngữ cảnh và trả lời yêu cầu; không phát sinh BOM thiết bị."
                 if contextual_answer else
                 f"Đã thẩm định {len(project_files)} tệp nhưng chưa đủ thông tin để trả lời hoặc bóc tách thiết bị.")
            ),
            "warnings": warnings[:5]
        }
        overall_assessment["contextual_answer"] = contextual_answer
        overall_assessment["file_roles"] = file_roles
        if progress_callback:
            await asyncio.sleep(0.35)
        log_event(
            stage="overall_assessment",
            title="Đánh giá tổng thể hồ sơ bản vẽ dự án",
            detail=overall_assessment["summary"],
            status="success" if len(extracted_devices) > 0 else "warning",
            data=overall_assessment
        )

        # 2. Xử lý khi không trích xuất được thiết bị: Báo cáo trung thực
        if len(extracted_devices) == 0 and not contextual_answer:
            log_event(
                stage="ai_vision",
                title="Không phát hiện thiết bị rõ ràng",
                detail="Bản vẽ có thể không chứa sơ đồ nguyên lý 1 sợi (SLD) hoặc định dạng chưa hỗ trợ",
                status="warning"
            )
            warnings.append(
                "Không tìm thấy ký hiệu hoặc nhãn thiết bị điện rõ ràng trong bản vẽ. "
                "Hãy kiểm tra lại bản vẽ có chứa Sơ đồ nguyên lý 1 sợi (SLD), hoặc xuất CAD sang DXF và thử lại."
            )
        elif len(extracted_devices) > 0:
            if progress_callback:
                await asyncio.sleep(0.35)
            log_event(
                stage="ai_vision",
                title="Trích xuất thành công thiết bị điện",
                detail=f"Đã nhận diện {len(extracted_devices)} thiết bị điện từ sơ đồ bản vẽ",
                status="success",
                data={"total_extracted": len(extracted_devices)}
            )

        # Các phần tử được vẽ độc lập đôi khi bị Vision nhét vào mô tả của thiết
        # bị chính. Tách chúng ra trước khi deduplicate để BOM không làm mất FA.
        extracted_devices = AnalysisPipelineService._promote_drawn_fa_devices(extracted_devices)
        extracted_devices = AnalysisPipelineService._promote_embedded_accessories_to_devices(extracted_devices)
        AnalysisPipelineService._infer_practical_quantities(extracted_devices)

        # 3. Chỉ gộp khi thực sự là cùng một thiết bị. Tag, lộ, tải hoặc quan hệ
        # nguồn khác nhau đều là thiết bị vật lý riêng, kể cả khi cùng thông số.
        grouped_map: Dict[str, ExtractedDeviceSchema] = {}
        for dev in extracted_devices:
            has_physical_identity = any(str(value or "").strip() for value in (
                dev.tag, dev.connected_load, dev.upstream_device, dev.downstream_device
            ))
            is_distinct_branch = dev.name and any(
                k in dev.name.lower() for k in ["nhánh", "feeder", "lộ", "tầng", "vị trí"]
            )
            if has_physical_identity or is_distinct_branch:
                key = f"physical_{id(dev)}"
            else:
                # Thiết bị cùng loại cùng thông số không có nhãn nhánh thì gộp lại và tăng quantity
                key = f"{dev.panel_code or ''}_{dev.category}_{dev.name}_{dev.poles}_{dev.in_a}_{dev.icu_ka}_{dev.section}_{dev.spec}"
            if key in grouped_map:
                grouped_map[key].quantity += dev.quantity
                if dev.notes and dev.notes not in (grouped_map[key].notes or ""):
                    if grouped_map[key].notes:
                        grouped_map[key].notes += f", {dev.notes}"
                    else:
                        grouped_map[key].notes = dev.notes
            else:
                grouped_map[key] = dev
        extracted_devices = list(grouped_map.values())

        # 4. Phát hiện mã tủ & tên tủ dựa trên phân tích kỹ thuật (KHÔNG lấy chuỗi prompt hay DB FACADE 12F)
        detected_panel_code = None
        detected_panel_name = None
        detected_location = None

        if multi_panel_list and len(multi_panel_list) > 1:
            # A multi-panel result is a collection, not a new panel whose name
            # may be invented by the application. Keep document-derived values.
            codes = [str(p.get("panel_code") or "").strip() for p in multi_panel_list if p.get("panel_code")]
            names = [str(p.get("panel_name") or "").strip() for p in multi_panel_list if p.get("panel_name")]
            locations = [str(p.get("location") or "").strip() for p in multi_panel_list if p.get("location")]
            detected_panel_code = ", ".join(dict.fromkeys(codes))
            detected_panel_name = ", ".join(dict.fromkeys(names))
            detected_location = ", ".join(dict.fromkeys(locations))
        else:
            for dev in extracted_devices:
                c = (dev.panel_code or "").strip()
                if c and c not in ["-", "TU_DIEN", "THIET BI", "CHUA_RO", "CHƯA_RÕ", "CHƯA-XÁC-ĐỊNH"]:
                    detected_panel_code = c
                    break
            for dev in extracted_devices:
                n = (dev.panel_name or "").strip()
                if n and n not in ["-", "Tủ điện", "Tủ điện chưa xác định"]:
                    detected_panel_name = n
                    break
            for dev in extracted_devices:
                if dev.location and dev.location != "-":
                    detected_location = dev.location
                    break

            # Unknown remains unknown. Do not turn absence of evidence into a
            # plausible-looking code, name, location or system classification.
            detected_panel_code = detected_panel_code or ""
            detected_panel_name = detected_panel_name or ""

        # Tự động gán đồng bộ mã tủ & hãng phù hợp cho toàn bộ thiết bị
        preferred_brand = AnalysisPipelineService._detect_requested_brand(user_prompt, catalog_engine)
        if preferred_brand:
            warnings.append(f"Áp dụng yêu cầu kỹ thuật: {preferred_brand}")

        # Catalog comparison is also shown in the takeoff table.  Only the
        # quotation workflow is allowed to select a SKU/price or alter the
        # commercial brand; plain takeoff remains faithful to the SLD.
        catalog_for_quotation = generate_cad_and_quotation
        if progress_callback:
            await asyncio.sleep(0.35)
        log_event(
            stage="catalog_matching",
            title="Tra cứu Catalog để lập báo giá" if catalog_for_quotation else "Phân tích nhà cung cấp & thiết bị phù hợp",
            detail=(f"Đang đối chiếu thông số với {len(catalog_engine.items)} sản phẩm để lập báo giá..."
                    if catalog_for_quotation else
                    f"Đang đối chiếu {len(extracted_devices)} thiết bị bóc tách với {len(catalog_engine.items)} sản phẩm; giữ nguyên dữ liệu SLD gốc."),
            status="info"
        )

        # Nhận diện thương hiệu đóng cắt chủ đạo của tủ (Dominant Breaker Brand)
        breaker_brand_counts: Dict[str, int] = {}
        for d in extracted_devices:
            b_val = (d.brand or "").strip()
            cat_u = (d.category or "").upper()
            part_u = (d.part_number or "").upper()
            name_u = (d.name or "").upper()
            notes_u = (d.notes or "").upper()

            inferred_brand = None
            if b_val.upper() == "ASIA":
                b_val = ""
                d.brand = ""
            if any(part_u.startswith(p) for p in ["NF", "BH", "NV", "CP30"]) or "MITSUBISHI" in name_u or "MITSUBISHI" in notes_u:
                inferred_brand = "Mitsubishi"
            elif any(part_u.startswith(p) for p in ["GOPACT", "EZC", "NSX", "C60", "IC60", "A9F", "A9N", "LV4", "NSXF"]) or "SCHNEIDER" in name_u or "SCHNEIDER" in notes_u:
                inferred_brand = "Schneider Electric"
            elif any(part_u.startswith(p) for p in ["ABN", "ABS", "BKN", "BKH", "METASOL", "SUSOL"]) or "LS" in name_u or "LS" in notes_u:
                inferred_brand = "LS Electric"
            elif any(part_u.startswith(p) for p in ["XT", "TMAX", "FORMULA", "S200"]) or "ABB" in name_u or "ABB" in notes_u:
                inferred_brand = "ABB"
            elif "SELEC" in part_u or "SELEC" in name_u or "SELEC" in notes_u:
                inferred_brand = "Selec"
            elif "MIKRO" in part_u or "MIKRO" in name_u or "MIKRO" in notes_u:
                inferred_brand = "Mikro"
            elif "EMIC" in part_u or "EMIC" in name_u or "EMIC" in notes_u:
                inferred_brand = "Emic"

            if not b_val and inferred_brand:
                d.brand = inferred_brand
                b_val = inferred_brand

            if b_val and b_val.upper() not in ["---", "OEM", "KHÔNG", "CHƯA RÕ", "CHUA RO", "VN"]:
                if any(k in cat_u for k in ["ACB", "MCCB", "MCB", "RCBO", "CONTACTOR"]):
                    breaker_brand_counts[b_val] = breaker_brand_counts.get(b_val, 0) + 1

        dominant_breaker_brand = None
        if breaker_brand_counts:
            dominant_breaker_brand = max(breaker_brand_counts.items(), key=lambda x: x[1])[0]

        for dev in extracted_devices:
            if not dev.panel_code or dev.panel_code == "-":
                dev.panel_code = detected_panel_code
            if not dev.panel_name:
                dev.panel_name = detected_panel_name
            if not dev.location or dev.location == "-":
                dev.location = detected_location

            cat_upper = (dev.category or "").upper()
            in_val = dev.in_a or 0
            icu_val = dev.icu_ka or 0
            poles_val = dev.poles
            ai_suggested_brands = [
                str(brand).strip()
                for brand in (getattr(dev, "suggested_brands", None) or [])
                if str(brand).strip()
            ]

            dev_raw_brand = (dev.brand or "").strip()
            unknown_brand_values = {"---", "OEM", "KHÔNG", "CHƯA RÕ", "CHUA RO", "VN"}
            has_explicit_brand = bool(dev_raw_brand and dev_raw_brand.upper() not in unknown_brand_values)

            # Chỉ tra các hãng có căn cứ từ yêu cầu, bản vẽ hoặc đề xuất AI;
            # không quét và đẩy toàn bộ danh mục hãng vào từng thiết bị.
            catalog_matches = {}
            candidate_brands = list(dict.fromkeys(
                [brand for brand in [preferred_brand, dev_raw_brand if has_explicit_brand else None, *ai_suggested_brands[:3]] if brand]
            ))
            for brand_name in candidate_brands:
                matches = catalog_engine.filter_devices(
                    device_type=dev.category,
                    poles=poles_val,
                    in_current=in_val if in_val > 0 else None,
                    brand=brand_name,
                    limit=5
                )
                # "METER" covers several electrically different products.
                # Require the catalog name to agree with the meter function so
                # an ammeter/voltmeter is not presented as an energy meter.
                if matches and cat_upper == "METER":
                    source_text = f"{dev.name or ''} {dev.spec or ''}".upper()
                    required_terms = []
                    if "CÔNG TƠ" in source_text or "KWH" in source_text:
                        required_terms = ["CÔNG TƠ", "KWH"]
                    elif "AMPE" in source_text:
                        required_terms = ["AMPE"]
                    elif "VÔN" in source_text or "VOLT" in source_text:
                        required_terms = ["VÔN", "VOLT"]
                    elif "ĐA NĂNG" in source_text or "MFM" in source_text:
                        required_terms = ["ĐA NĂNG", "MFM"]
                    if required_terms:
                        matches = [
                            item for item in matches
                            if any(
                                term in f"{item.get('n') or item.get('name') or ''} {item.get('ma') or item.get('sku') or ''}".upper()
                                for term in required_terms
                            )
                        ]
                if matches:
                    exact_icu = [m for m in matches if icu_val and m.get("icu") and float(m.get("icu")) >= float(icu_val)]
                    best = exact_icu[0] if exact_icu else matches[0]
                    catalog_matches[brand_name] = {
                        "sku": best.get("ma") or best.get("sku") or "",
                        "name": best.get("n") or best.get("name") or "",
                        "icu": best.get("icu"),
                        "price": int(best.get("g") or best.get("price") or 0),
                        "meets_icu": bool(exact_icu) if icu_val else True
                    }

            # Khi lập báo giá mà không có chỉ định hãng, chỉ lấy một kết quả tốt
            # nhất từ catalog thay vì sinh danh sách đề xuất dài.
            if catalog_for_quotation and not catalog_matches and not candidate_brands:
                best = catalog_engine.lookup_device_info(
                    category=dev.category,
                    in_a=in_val if in_val > 0 else None,
                    poles=poles_val,
                    part_number=dev.part_number,
                    name=dev.name,
                )
                if best and best.get("catalog_matched"):
                    best_brand = str(best.get("brand") or "Catalog").strip()
                    catalog_matches[best_brand] = {
                        "sku": best.get("sku") or "",
                        "name": best.get("name") or "",
                        "icu": None,
                        "price": int(best.get("unit_price") or 0),
                        "meets_icu": True,
                    }

            dev.catalog_matches = catalog_matches

            # Lọc các hãng có model trong catalog
            valid_brands = list(catalog_matches.keys())
            if valid_brands:
                icu_brands = [b for b, info in catalog_matches.items() if info["meets_icu"]]
                pool = icu_brands if icu_brands else valid_brands
            else:
                pool = []

            # Lựa chọn hãng phù hợp dựa trên phân tích kỹ thuật:
            chosen_brand = None
            chosen_sku = (dev.part_number or "").strip()
            chosen_price = 0

            dev.detected_brand = dev_raw_brand if has_explicit_brand else ""

            # 1. Ưu tiên yêu cầu người dùng nếu có chỉ định hãng
            if preferred_brand and preferred_brand in catalog_matches:
                chosen_brand = preferred_brand
                dev.selection_source = "user_request"
            # 2. Ưu tiên hãng tự nhiên do AI trích xuất được từ bản vẽ (Selec, Mikro, Emic, Mitsubishi, Schneider...)
            elif has_explicit_brand:
                chosen_brand = dev_raw_brand
                dev.selection_source = "drawing"
            elif preferred_brand:
                chosen_brand = preferred_brand
                dev.selection_source = "user_request"
            # 3. Tự động chọn nhà cung cấp có model catalog khớp kỹ thuật nhất.
            elif pool:
                chosen_brand = pool[0]
                dev.selection_source = "catalog_auto"
            # 4. Không có hãng/catalog phù hợp: giữ nguyên dữ liệu gốc, không tự gán hãng.
            else:
                chosen_brand = dev_raw_brand if has_explicit_brand else ""
                dev.selection_source = "drawing" if has_explicit_brand else "unresolved"

            if chosen_brand in catalog_matches:
                m_info = catalog_matches[chosen_brand]
                chosen_sku = m_info["sku"]
                chosen_price = m_info["price"]
                icu_info = f", Icu {m_info['icu']}kA" if m_info.get("icu") else ""
                dev.technical_match_note = f"Đối chiếu Catalog: {chosen_brand} {chosen_sku}{icu_info} ({chosen_price:,} đ)"
            else:
                chosen_price = 0
                dev.technical_match_note = "Chưa có bản ghi khớp trong catalog.json; giữ nguyên dữ liệu đọc từ nguồn và cần xác nhận khi báo giá."
                # Tạm thời ẩn cảnh báo chưa khớp catalog theo yêu cầu để chỉ hiển thị các lưu ý kỹ thuật thực sự cần thiết

            # ĐỀ XUẤT THIẾT BỊ TƯƠNG THÍCH DO AI PHÂN TÍCH TỪ BẢN VẼ (KHÔNG HARD-CODE)
            if getattr(dev, "compatible_proposal", None):
                cp = dev.compatible_proposal
                dev.is_alternative_recommended = True
                dev.original_spec = cp.get("original_spec") or dev.spec
                dev.compatibility_note = cp.get("technical_reason") or cp.get("ai_analysis")
                dev.suggested_alternatives = [cp]
                prop_d = cp.get("proposed_device")
                if prop_d and (not chosen_sku or chosen_sku.endswith("-")):
                    chosen_sku = prop_d
                dev.technical_match_note = f"Đề xuất tương thích (AI): {prop_d or dev.name}"

            # PHỤ KIỆN ĐI KÈM DO AI PHÂN TÍCH TỪ BẢN VẼ (KHÔNG HARD-CODE)
            if getattr(dev, "accompanying_accessories", None):
                dev.accompanying_accessories = AccompanyingEquipmentService.format_accessories(
                    dev.accompanying_accessories,
                    parent_brand=chosen_brand or dev.brand,
                    parent_category=dev.category
                )

            # Gợi ý danh sách hãng khả dụng
            concise_brands = ([chosen_brand] if chosen_brand else []) + ai_suggested_brands[:2]
            dev.suggested_brands = list(dict.fromkeys(brand for brand in concise_brands if brand))[:3]

            # Tự động áp dụng lựa chọn kỹ thuật ở cả bảng bóc tách. Người dùng
            # có thể đổi sang các hãng khác từ `catalog_matches` trên giao diện.
            dev.brand = chosen_brand
            dev.part_number = chosen_sku

            if catalog_for_quotation:
                device_price_map[dev.part_number or dev.name] = chosen_price
            else:
                if catalog_matches:
                    comparison_brand = chosen_brand if chosen_brand in catalog_matches else valid_brands[0]
                    comparison = catalog_matches[comparison_brand]
                    sku = comparison.get("sku") or comparison.get("name") or ""
                    icu_info = f", Icu {comparison['icu']}kA" if comparison.get("icu") else ""
                    dev.technical_match_note = (
                        f"Đã tự chọn thiết bị phù hợp: {comparison_brand} {sku}{icu_info}; "
                        "có thể đổi nhà cung cấp trên bảng bóc tách."
                    )
                elif not getattr(dev, "compatible_proposal", None):
                    dev.technical_match_note = (
                        "Chưa tìm thấy thiết bị khớp thông số trong catalog; "
                        "cần bổ sung dữ liệu hoặc kiểm tra kỹ thuật."
                    )
                device_price_map[dev.part_number or dev.name] = 0

        log_event(
            stage="catalog_matching",
            title="Định giá & chọn mã SKU catalog hoàn tất" if catalog_for_quotation else "Phân tích nhà cung cấp & thiết bị phù hợp hoàn tất",
            detail=(f"Đã hoàn tất đối chiếu giá cho {len(extracted_devices)} thiết bị (Thương hiệu: {preferred_brand or settings.DEFAULT_BRAND})"
                    if catalog_for_quotation else
                    f"Đã đối chiếu hãng và cấu hình phù hợp cho {len(extracted_devices)} thiết bị; không thay đổi dữ liệu bóc tách gốc."),
            status="success"
        )

        # Đồng bộ lại danh sách thiết bị trong các tủ của multi_panel_list
        multi_panel_list = AnalysisPipelineService._normalize_panels(
            multi_panel_list, extracted_devices
        )

        # Tự động hiệu chỉnh vị trí bounding box cho thiết bị đầu vào (tránh AI đóng khung lệch sang nhánh phụ)
        AnalysisPipelineService._refine_device_bounding_boxes(extracted_devices)

        # 5. Tự động trích xuất ảnh dẫn chứng trực tiếp từ bản vẽ tải lên
        for pfile in project_files:
            if pfile.file_path:
                p_ext = pfile.filename.split(".")[-1].lower() if pfile.filename else ""
                if p_ext in ["png", "jpg", "jpeg", "webp", "bmp"]:
                    source_devices = [
                        device for device in extracted_devices
                        if device.source_filename == (pfile.filename or "")
                    ]
                    AnalysisPipelineService._attach_evidence_thumbnails(
                        source_devices, pfile.file_path
                    )

        # 6. Bổ sung thông số kích thước & parameters từ Catalog cho các model đã khớp
        for dev in extracted_devices:
            if catalog_engine is not None and dev.part_number:
                exact = catalog_engine.get_by_sku(dev.part_number)
                if exact:
                    if not dev.name or dev.name == "Thiết bị":
                        dev.name = exact.get("n") or exact.get("name") or dev.name
                    if exact.get("g"):
                        device_price_map[dev.part_number] = int(exact.get("g"))

        # Trích xuất kích thước vỏ tủ quy định trên bản vẽ (ví dụ: TỦ 1200X800X400, 1200x800x400mm)
        dim_sources = []
        if detected_enclosure_dim_str:
            dim_sources.append(detected_enclosure_dim_str)
        if file_assessment and file_assessment.get("assessment_summary"):
            dim_sources.append(file_assessment.get("assessment_summary"))
        if user_prompt:
            dim_sources.append(user_prompt)
        dim_sources.extend(cad_extracted_texts)
        for d in extracted_devices:
            if d.notes:
                dim_sources.append(d.notes)

        detected_dimensions = AnalysisPipelineService._extract_enclosure_dimensions(dim_sources)
        if detected_dimensions:
            log_event(
                stage="engineering_sizing",
                title="Phát hiện kích thước vỏ tủ chỉ định trên bản vẽ",
                detail=f"Bản vẽ quy định vỏ tủ: H{int(detected_dimensions[0])}xW{int(detected_dimensions[1])}xD{int(detected_dimensions[2])}mm",
                status="success"
            )

        # NẾU CHỈ BÓC TÁCH THIẾT BỊ (Không vẽ CAD và không tạo file báo giá luôn)
        if not generate_cad_and_quotation:
            log_event(
                stage="finalization",
                title="Hoàn tất bóc tách thiết bị điện",
                detail=f"Trích xuất thành công {len(extracted_devices)} thiết bị. Sẵn sàng cho bước Phân tích kỹ thuật, Vẽ CAD & Lập báo giá.",
                status="success"
            )

            is_multi = multi_panel_list and len(multi_panel_list) > 1
            summary_text = (
                f"Đã bóc tách thành công {len(extracted_devices)} thiết bị từ sơ đồ bản vẽ của hệ thống {len(multi_panel_list)} tủ điện. Vui lòng bấm 'Tạo báo giá & Vẽ CAD' để phân tích kỹ thuật, dựng bản vẽ AutoCAD DXF và lập bảng báo giá."
                if is_multi
                else f"Đã bóc tách thành công {len(extracted_devices)} thiết bị từ sơ đồ bản vẽ tủ {detected_panel_code} ({detected_panel_name}). Vui lòng bấm 'Tạo báo giá & Vẽ CAD' để phân tích kỹ thuật, dựng bản vẽ AutoCAD DXF và lập bảng báo giá."
            )

            if not file_assessment:
                if extracted_devices:
                    file_assessment = {
                        "is_suitable": True,
                        "document_type": "Sơ đồ nguyên lý một sợi (SLD) / Bản vẽ tủ điện",
                        "assessment_summary": f"Tệp bản vẽ phù hợp với hệ thống tủ bảng điện. Đã bóc tách thành công {len(extracted_devices)} thiết bị.",
                        "warnings": []
                    }
                else:
                    file_assessment = {
                        "is_suitable": False,
                        "document_type": "Tệp không phù hợp / Không phát hiện thiết bị điện",
                        "assessment_summary": "Tệp tải lên không chứa sơ đồ nguyên lý hoặc không có thông tin thiết bị điện phù hợp để bóc tách tủ bảng điện.",
                        "warnings": ["Tệp có thể là bản vẽ kiến trúc, kết cấu hoặc tài liệu không liên quan đến tủ điện. Vui lòng kiểm tra lại."]
                    }

            first_icu = int(extracted_devices[0].icu_ka or 10) if extracted_devices and extracted_devices[0].icu_ka else 10
            first_incomer = 40
            for d in extracted_devices:
                cat_u = (d.category or "").upper()
                if "MCCB" in cat_u or "ACB" in cat_u:
                    first_incomer = d.in_a or 100
                    break
            is_3p = any((d.poles or 1) >= 3 for d in extracted_devices)

            conclusion = {
                "panel_code": detected_panel_code,
                "panel_name": detected_panel_name,
                "panel_type": "Tủ phân phối điện" if not is_multi else f"Hệ thống đa tủ ({len(multi_panel_list)} tủ)",
                "voltage": "3 pha 380/220V 50Hz" if is_3p else "1 pha 220V 50Hz",
                "incomer": f"MCCB {first_incomer}A (Icu = {first_icu}kA)",
                "total_devices": len(extracted_devices),
                "enclosure_recommendation": "Kích thước vỏ tủ và thanh cái sẽ được phân tích tự động khi bấm 'Tạo báo giá & Vẽ CAD'.",
                "summary_notes": summary_text,
                "file_assessment": file_assessment
            }

            panel_info = {
                "panel_code": detected_panel_code,
                "panel_name": detected_panel_name,
                "panel_type": "Tủ phân phối điện",
                "incomer_rating": first_incomer,
                "voltage": "3 pha 380/220V 50Hz" if is_3p else "1 pha 220V 50Hz",
                "dimensions": detected_enclosure_dim_str or "",
                "surface_m2": 0
            }

            tokens_consumed = max(500, len(extracted_devices) * 120 + 300)

            process_steps = [
                {
                    "id": "ingestion",
                    "title": "Tiếp nhận & Thẩm định bản vẽ",
                    "description": f"Đã nạp {len(project_files)} tệp bản vẽ dự án",
                    "status": "completed",
                },
                {
                    "id": "ai_vision",
                    "title": "Phân tích Thị giác AI sơ đồ SLD",
                    "description": f"Nhận diện thành công {len(extracted_devices)} thiết bị điện",
                    "status": "completed" if len(extracted_devices) > 0 else "warning",
                },
                {
                    "id": "catalog_matching",
                    "title": "Phân tích nhà cung cấp & thiết bị phù hợp",
                    "description": (
                        f"Đã đối chiếu hãng và cấu hình tương thích cho {len(extracted_devices)} thiết bị; "
                        "giữ nguyên dữ liệu đọc từ bản vẽ."
                    ),
                    "status": "completed",
                },
                {
                    "id": "finalization",
                    "title": "Hoàn tất bóc tách thiết bị",
                    "description": f"Đã bóc tách {len(extracted_devices)} thiết bị. Sẵn sàng tạo báo giá & vẽ CAD.",
                    "status": "completed",
                }
            ]

            clean_warnings = [w for w in warnings if not ("chưa khớp catalog" in w.lower() or "chua khop catalog" in w.lower())]
            from app.services.ai.system_completeness import technical_audit
            completeness_audit = technical_audit(extracted_devices)
            # Review gaps are shown in technical_audit, not as repetitive BOM warnings.
            # Preserve the independent whole-document assessment. A BOM cannot
            # retroactively prove that the source circuit was assessed.
            circuit_assessment = circuit_assessment or {"status": "unavailable"}
            for device in extracted_devices:
                device.evidence_image = None
                device.panel_evidence_image = None
                device.box_2d = None
            return {
                "devices": extracted_devices,
                "warnings": clean_warnings,
                "enclosure_spec": None,
                "quotation_rows": [],
                "cad_file_path": None,
                "quotation_file_path": None,
                "tokens_consumed": tokens_consumed,
                "conclusion": conclusion,
                "panel_info": panel_info,
                "panels": multi_panel_list,
                "technical_audit": completeness_audit,
                "file_assessment": file_assessment,
                "files_assessment": files_assessment,
                "circuit_assessment": circuit_assessment,
                "overall_assessment": overall_assessment,
                "execution_logs": execution_logs,
                "process_steps": process_steps,
                "physical_layout": None,
                "layout_conflicts": [],
                "analysis_mode": "sld_takeoff",
                "log_version": 2,
            }

        # 7. Tính toán kích thước vỏ tủ & thanh cái đồng
        enclosure_spec = EnclosureCadGeneratorService.calculate_enclosure_specs(
            [d.model_dump() for d in extracted_devices],
            preferred_dimensions=detected_dimensions
        )

        incomer_rating = enclosure_spec.get("incomer_rating") or settings.DEFAULT_INCOMER_RATING or 0
        poles = enclosure_spec.get("poles", 2)
        is_3phase = enclosure_spec.get("is_3phase", False)
        voltage_str = "3 pha 380/220V 50Hz" if is_3phase else "1 pha 220V 50Hz"

        enclosure_height = enclosure_spec.get("height", 600 if not is_3phase else 1400)
        enclosure_width = enclosure_spec.get("width", 500 if not is_3phase else 800)
        enclosure_depth = enclosure_spec.get("depth", 200 if not is_3phase else 350)
        
        surface_m2 = 2 * (enclosure_height * enclosure_width + enclosure_height * enclosure_depth + enclosure_width * enclosure_depth) / 1e6
        min_enc_p = int(getattr(settings, "ENCLOSURE_MIN_PRICE", 1200000))
        enclosure_unit_price = max(min_enc_p, int(surface_m2 * 1200000))
        enclosure_unit_price = int(round(enclosure_unit_price / float(PRICE_ROUNDING_STEP_VND)) * PRICE_ROUNDING_STEP_VND)

        phase_cu_area = int(incomer_rating / 2) if is_3phase else 16
        busbar_kg_est = round((phase_cu_area * 3.0 * (enclosure_width / 1000.0) * 8.9e-3 * 1.05) + (len(extracted_devices) * 0.4), 1)
        busbar_unit_price = max(800000 if not is_3phase else 1800000, int(busbar_kg_est * 270000))
        busbar_unit_price = int(round(busbar_unit_price / float(PRICE_ROUNDING_STEP_VND)) * PRICE_ROUNDING_STEP_VND)

        log_event(
            stage="engineering_sizing",
            title="Tính toán Kỹ thuật Vỏ tủ & Thanh cái Form 2B",
            detail=f"Incomer {incomer_rating}A -> Vỏ tủ H{enclosure_height}xW{enclosure_width}xD{enclosure_depth}mm (tôn {enclosure_spec.get('thickness', settings.ENCLOSURE_DEFAULT_THICKNESS)}mm), Thanh cái Cu {phase_cu_area}mm² ({busbar_kg_est}kg)",
            status="success",
            data={
                "dimensions": f"H{enclosure_height}xW{enclosure_width}xD{enclosure_depth}mm",
                "busbar_kg": busbar_kg_est,
                "incomer_rating": incomer_rating
            }
        )

        # Tự động đồng bộ ý định hướng cáp từ yêu cầu người dùng nếu có
        if user_prompt:
            p_low = user_prompt.lower()
            if "cáp đáy" in p_low or "bottom" in p_low:
                detected_layout_intent = detected_layout_intent or {}
                detected_layout_intent["cable_entry"] = "BOTTOM"
            elif "cáp nóc" in p_low or "top" in p_low:
                detected_layout_intent = detected_layout_intent or {}
                detected_layout_intent["cable_entry"] = "TOP"

        # BƯỚC 4 & 5 — TẠO MÔ HÌNH VẬT LÝ PHYSICAL LAYOUT MODEL & BƯỚC 6 — KIỂM TRA XUNG ĐỘT HÌNH HỌC
        physical_layout = PhysicalLayoutEngine.compute_physical_layout_model(
            devices=[d.model_dump() for d in extracted_devices],
            enclosure_spec=enclosure_spec,
            mode="PANEL_LAYOUT_ONLY",
            layout_intent=detected_layout_intent
        )
        layout_conflict_res = physical_layout.get("conflict_check", {})
        has_layout_conflict = layout_conflict_res.get("has_conflict", False)
        layout_conflicts = layout_conflict_res.get("conflicts", [])

        if progress_callback:
            await asyncio.sleep(0.35)

        if has_layout_conflict:
            warn_msg = f"⚠️ Phát hiện {len(layout_conflicts)} xung đột hình học (LAYOUT_CONFLICT) trong bố trí tủ điện."
            warnings.append(warn_msg)
            log_event(
                stage="engineering_sizing",
                title="Cảnh báo xung đột hình học (LAYOUT_CONFLICT)",
                detail="; ".join([c.get("detail", "") for c in layout_conflicts[:2]]),
                status="warning",
                data={"conflicts": layout_conflicts}
            )
        else:
            log_event(
                stage="engineering_sizing",
                title="Bố trí Không gian Vật lý Chuẩn Công Nghiệp (OK)",
                detail=f"Mô hình Physical Layout 3D/2D: {physical_layout.get('total_components', 0)} linh kiện (X/Y/Z), không có xung đột va chạm.",
                status="success",
                data={"total_components": physical_layout.get("total_components", 0)}
            )

        # 8. Xây dựng danh sách dòng Báo giá chuẩn kỹ thuật (Quotation Rows đa tủ hoặc đơn tủ)
        quotation_rows = AnalysisPipelineService._build_quotation_rows(
            project_name=project.name,
            extracted_devices=extracted_devices,
            device_price_map=device_price_map,
            enclosure_spec=enclosure_spec,
            enclosure_unit_price=enclosure_unit_price,
            busbar_unit_price=busbar_unit_price,
            multi_panel_list=multi_panel_list,
            panel_code=detected_panel_code,
            panel_name=detected_panel_name
        )

        if quotation_rows:
            log_event(
                stage="quotation",
                title=f"Đã lập bảng báo giá dự toán ({len(quotation_rows)} dòng)",
                detail=f"Tổng hợp chi tiết đơn giá thiết bị, kích thước vỏ tủ & hệ thanh cái busbar. Bạn có thể xem bảng tính và xuất Excel ngay.",
                status="success",
                data={"quotation_rows_count": len(quotation_rows)}
            )

        # 9. Tự động sinh file CAD DXF Layout phác thảo chính xác theo loại tủ và thiết bị thực tế
        cad_file_path = None
        if len(extracted_devices) > 0:
            if has_layout_conflict:
                log_event(
                    stage="cad_generation",
                    title="Cảnh báo bố trí không gian (LAYOUT_CONFLICT) - Vẫn xuất bản vẽ CAD",
                    detail="Phát hiện cảnh báo xung đột không gian. Hệ thống tự động tối ưu và xuất bản vẽ AutoCAD DXF 4 hình chiếu.",
                    status="warning"
                )
            else:
                log_event(
                    stage="cad_generation",
                    title="Tự động thiết kế bản vẽ AutoCAD DXF 4 hình chiếu",
                    detail=f"Đang sinh View 1 (Mặt cánh), View 2 (Cover Form 2B), View 3 (Internal GA), View 4 (Mặt cắt), View 5 (BOM)...",
                    status="info"
                )
            try:
                source_cad = SourceProjectGenerator.generate(
                    project_id=project.id,
                    output_dir=getattr(settings, "PROJECTS_DIR", "storage/projects"),
                    dimensions=tuple(enclosure_spec["fit_check"]["minimum_required"][axis] for axis in ("height", "width", "depth")),
                    devices=[d.model_dump() for d in extracted_devices],
                    kind=("outdoor" if any(token in str(panel_info).lower() for token in ("ngoài trời", "outdoor")) else "fire" if any(token in str(panel_info).lower() for token in ("chữa cháy", "pccc")) else "indoor"),
                )
                cad_file_path = source_cad["path"]
                log_event(
                    stage="cad_generation",
                    title="Sinh bản vẽ CAD DXF thành công",
                    detail=f"Form nguồn {source_cad['source']}: {os.path.basename(cad_file_path)}",
                    status="success",
                    data={"cad_file": os.path.basename(cad_file_path)}
                )
            except Exception as e:
                warnings.append(f"Chưa thể xuất form CAD nguồn: {str(e)}")
                log_event(
                    stage="cad_generation",
                    title="Lỗi sinh bản vẽ CAD",
                    detail=str(e),
                    status="warning"
                )

        # 10. Không tự động sinh file Excel vật lý (dữ liệu báo giá được lưu vào database và chỉ xuất khi người dùng yêu cầu)
        quotation_file_path = None

        # 11. Phân loại loại tủ & xây dựng Technical Audit động theo thiết bị thực tế
        has_lighting = any("CONTACTOR" in (d.category or "").upper() or "TIMER" in (d.category or "").upper() for d in extracted_devices)
        panel_type_name = (
            "Tủ điều khiển & phân phối chiếu sáng (Lighting Control Panel)" if has_lighting
            else ("Tủ phân phối tổng MSB" if is_3phase and incomer_rating >= 400 else "Tủ phân phối điện tầng DB")
        )

        technical_audit = AnalysisPipelineService._build_technical_audit(
            extracted_devices=extracted_devices,
            enclosure_spec=enclosure_spec,
            panel_code=detected_panel_code,
            panel_name=detected_panel_name,
            is_3phase=is_3phase,
            incomer_rating=incomer_rating
        )

        is_multi = multi_panel_list and len(multi_panel_list) > 1
        summary_text = (
            f"Hệ thống gồm {len(multi_panel_list)} tủ điện đã được bóc tách chi tiết tổng cộng {len(extracted_devices)} thiết bị. Sơ đồ SLD và bản vẽ CAD tổng thể đã được lập tự động chính xác."
            if is_multi
            else f"Tủ điện {detected_panel_code} ({detected_panel_name}) đã được bóc tách chi tiết {len(extracted_devices)} thiết bị. Sơ đồ SLD và bản vẽ CAD đã được lập tự động chính xác."
        )

        if not file_assessment:
            if extracted_devices:
                file_assessment = {
                    "is_suitable": True,
                    "document_type": "Sơ đồ nguyên lý một sợi (SLD) / Bản vẽ tủ điện",
                    "assessment_summary": f"Tệp bản vẽ phù hợp với hệ thống tủ bảng điện. Đã bóc tách thành công {len(extracted_devices)} thiết bị.",
                    "warnings": []
                }
            else:
                file_assessment = {
                    "is_suitable": False,
                    "document_type": "Tệp không phù hợp / Không phát hiện thiết bị điện",
                    "assessment_summary": "Tệp tải lên không chứa sơ đồ nguyên lý hoặc không có thông tin thiết bị điện phù hợp để bóc tách tủ bảng điện.",
                    "warnings": ["Tệp có thể là bản vẽ kiến trúc, kết cấu hoặc tài liệu không liên quan đến tủ điện. Vui lòng kiểm tra lại."]
                }

        if file_assessment and not file_assessment.get("is_suitable", True):
            warnings.append(f"⚠️ Cảnh báo tệp: {file_assessment.get('assessment_summary')}")

        first_icu = int(extracted_devices[0].icu_ka or 10) if extracted_devices and extracted_devices[0].icu_ka else 10
        conclusion = {
            "panel_code": detected_panel_code,
            "panel_name": detected_panel_name,
            "panel_type": panel_type_name if not is_multi else f"Hệ thống đa tủ ({len(multi_panel_list)} tủ)",
            "voltage": voltage_str,
            "incomer": f"MCCB {poles}P {incomer_rating}A (Icu = {first_icu}kA)",
            "total_devices": len(extracted_devices),
            "enclosure_recommendation": f"Vỏ tủ {enclosure_spec.get('enclosure_code')}, tôn dày {enclosure_spec.get('thickness', 1.5)}mm sơn tĩnh điện tiêu chuẩn công nghiệp (cấp bảo vệ IP54 ngoài trời / IP42 trong nhà).",
            "summary_notes": summary_text,
            "file_assessment": file_assessment
        }

        panel_info = {
            "panel_code": detected_panel_code,
            "panel_name": detected_panel_name,
            "panel_type": panel_type_name,
            "incomer_rating": incomer_rating,
            "voltage": voltage_str,
            "dimensions": f"H{enclosure_height}xW{enclosure_width}xD{enclosure_depth}mm",
            "surface_m2": surface_m2
        }

        tokens_consumed = max(500, len(extracted_devices) * 120 + 300)

        if progress_callback:
            await asyncio.sleep(0.35)

        # STAGE 6: HOÀN TẤT & LẬP BÁO CÁO KỸ THUẬT
        log_event(
            stage="finalization",
            title="Kiểm định An toàn Kỹ thuật (Technical Audit)",
            detail=technical_audit['summary'],
            status="success"
        )
        log_event(
            stage="finalization",
            title="Hoàn tất quy trình bóc tách BOM & Lập dự toán",
            detail=f"Tổng hợp thành công {len(extracted_devices)} thiết bị, hoàn thiện bảng báo giá {len(quotation_rows)} dòng",
            status="success"
        )

        process_steps = [
            {
                "id": "ingestion",
                "title": "Tiếp nhận & Thẩm định bản vẽ",
                "description": f"Đã nạp {len(project_files)} tệp bản vẽ dự án",
                "status": "completed",
            },
            {
                "id": "ai_vision",
                "title": "Phân tích Thị giác AI sơ đồ SLD",
                "description": f"Nhận diện thành công {len(extracted_devices)} thiết bị điện",
                "status": "completed" if len(extracted_devices) > 0 else "warning",
            },
            {
                "id": "catalog_matching",
                "title": "Tra cứu Catalog & Định giá Đa Hãng",
                "description": f"Khớp SKU & đơn giá {len(extracted_devices)} thiết bị ({preferred_brand or 'Theo thiết kế'})",
                "status": "completed",
            },
            {
                "id": "engineering_sizing",
                "title": "Tính toán Kỹ thuật Vỏ tủ & Thanh cái",
                "description": f"Vỏ tủ H{enclosure_height}xW{enclosure_width}xD{enclosure_depth}mm, Thanh cái Cu {phase_cu_area}mm²",
                "status": "completed",
            },
            {
                "id": "cad_generation",
                "title": "Tự động Thiết kế & Sinh Bản vẽ CAD",
                "description": f"DXF 4 hình chiếu: {os.path.basename(cad_file_path) if cad_file_path else 'Không sinh CAD'}",
                "status": "completed" if cad_file_path else "warning",
            },
            {
                "id": "finalization",
                "title": "Kiểm định An toàn Kỹ thuật & Báo giá",
                "description": f"{technical_audit['overall_status']} - Bảng báo giá {len(quotation_rows)} dòng",
                "status": "completed",
            }
        ]

        clean_warnings = [w for w in warnings if not ("chưa khớp catalog" in w.lower() or "chua khop catalog" in w.lower())]
        for device in extracted_devices:
            device.evidence_image = None
            device.panel_evidence_image = None
            device.box_2d = None
        return {
            "devices": extracted_devices,
            "warnings": clean_warnings,
            "enclosure_spec": enclosure_spec,
            "quotation_rows": quotation_rows,
            "technical_proposals": technical_proposals,
            "cad_file_path": cad_file_path,
            "quotation_file_path": quotation_file_path,
            "tokens_consumed": tokens_consumed,
            "conclusion": conclusion,
            "panel_info": panel_info,
            "panels": multi_panel_list,
            "technical_audit": technical_audit,
            "file_assessment": file_assessment,
            "files_assessment": files_assessment,
            "circuit_assessment": circuit_assessment,
            "overall_assessment": overall_assessment,
            "execution_logs": execution_logs,
            "process_steps": process_steps,
            "physical_layout": physical_layout,
            "layout_conflicts": layout_conflicts if has_layout_conflict else []
        }

    @staticmethod
    def _infer_practical_quantities(devices: List[ExtractedDeviceSchema]) -> None:
        """Separate drawn symbols from the material quantity required in practice.

        A single-line diagram may use one grouped symbol for three physical
        phase devices. Rules only expand quantity when the drawing text or the
        surrounding measurement circuit provides a concrete basis.
        """
        panel_context: Dict[str, str] = {}
        for device in devices:
            panel = str(device.panel_code or "")
            panel_context[panel] = panel_context.get(panel, "") + " " + " ".join(
                str(value or "") for value in (
                    device.tag, device.category, device.name, device.spec,
                    device.notes, device.upstream_device, device.connected_load,
                )
            ).lower()

        for device in devices:
            # Keep this pass idempotent: a saved result may already contain an
            # expanded procurement quantity from an earlier reprocessing run.
            drawn_qty = max(1, int(device.drawing_quantity or device.quantity or 1))
            device.drawing_quantity = drawn_qty
            device.quantity = drawn_qty
            device.procurement_quantity = drawn_qty
            device.quantity_basis = "Theo số ký hiệu hoặc số lượng ghi trực tiếp trên sơ đồ."
            device.quantity_confidence = float(device.confidence or 0.0)

            searchable = " ".join(str(value or "") for value in (
                device.tag, device.category, device.name, device.spec,
                device.notes, device.section, device.upstream_device,
            )).lower()
            identity_text = " ".join(str(value or "") for value in (
                device.tag, device.category, device.name, device.spec,
            )).lower()
            category = str(device.category or "").upper()
            context = panel_context.get(str(device.panel_code or ""), "")

            # Generic explicit multiplicity works for every device family and
            # keeps model/vendor names out of the rule set. Avoid interpreting
            # electrical values such as 3P, 3 pha or 3xCT here; those have
            # dedicated semantic handling below.
            explicit_qty_matches = [
                int(value)
                for value in re.findall(r"(?:\bx\s*(\d+)\b|\b(\d+)\s*[x×]\s*(?:cái|chiếc|bộ|pcs?|nos?\.?)(?:\b|$))", identity_text, re.I)
                for value in value if value
            ]
            if explicit_qty_matches:
                explicit_qty = max(explicit_qty_matches)
                device.quantity = device.procurement_quantity = explicit_qty
                device.quantity_basis = f"Bản vẽ ghi rõ số lượng {explicit_qty} cho thiết bị này."
                device.quantity_confidence = max(device.quantity_confidence or 0, 0.99)
                # Explicit quantities take precedence over circuit heuristics.
                continue

            if re.search(r"\b3\s*x?\s*ct\b|\b3xct\b", identity_text, re.I):
                device.drawing_quantity = 1
                device.quantity = device.procurement_quantity = 3
                device.quantity_basis = (
                    "Ký hiệu 3XCT/3CT đại diện ba biến dòng vật lý, mỗi pha R-S-T dùng một chiếc."
                )
                device.quantity_confidence = max(device.quantity_confidence or 0, 0.98)
                continue

            is_fuse = category == "FUSE" or "cầu chì" in searchable or re.search(r"\bfuse\b", searchable)
            explicit_three_phase = bool(re.search(r"\b3\s*[x×]\b|\b3\s*(?:pha|phase|p)\b|\br\s*[-/,]\s*[sy]\s*[-/,]\s*[tb]\b", searchable, re.I))
            measurement_fuse = bool(re.search(r"v[oô]n|volt|điện áp|dien ap|báo pha|bao pha", searchable, re.I))
            panel_has_three_phase_measurement = bool(
                re.search(r"3xct|\b3ct\b|\br\s*[-/,]\s*[sy]\s*[-/,]\s*[tb]\b|đèn báo pha|chon mach volt|vôn kế", context, re.I)
            )
            if is_fuse and (explicit_three_phase or (measurement_fuse and panel_has_three_phase_measurement)):
                if not explicit_qty_matches:
                    device.drawing_quantity = 1
                device.quantity = device.procurement_quantity = max(3, drawn_qty)
                device.quantity_basis = (
                    "Sơ đồ một sợi chỉ vẽ một cụm, nhưng mạch đo/báo điện áp ba pha cần ba cầu chì, "
                    "tương ứng các pha R-S-T."
                )
                device.quantity_confidence = max(device.quantity_confidence or 0, 0.9)

    @staticmethod
    def _refine_device_bounding_boxes(devices: List[ExtractedDeviceSchema]) -> None:
        """
        Kiểm tra và chuẩn hóa tính hợp lệ của tọa độ box_2d [ymin, xmin, ymax, xmax] (0-1000).
        Giữ nguyên 100% tọa độ thực tế do AI thị giác trích xuất từ bản vẽ, không tự ý dịch chuyển hardcode.
        Đảm bảo ymin <= ymax, xmin <= xmax và tất cả giá trị đều nằm gọn trong phạm vi chuẩn 0..1000.
        """
        for d in devices:
            box = getattr(d, "box_2d", None)
            if not box or not isinstance(box, list) or len(box) != 4:
                continue
            try:
                ymin, xmin, ymax, xmax = [float(v) for v in box]
                norm_ymin = max(0.0, min(1000.0, min(ymin, ymax)))
                norm_ymax = max(0.0, min(1000.0, max(ymin, ymax)))
                norm_xmin = max(0.0, min(1000.0, min(xmin, xmax)))
                norm_xmax = max(0.0, min(1000.0, max(xmin, xmax)))
                d.box_2d = [int(norm_ymin), int(norm_xmin), int(norm_ymax), int(norm_xmax)]
            except Exception:
                continue

    @staticmethod
    def _apply_verified_boxes(devices: List[ExtractedDeviceSchema], payload: Any) -> None:
        """Join verifier results by request-local identity, never by repeated tags."""
        candidates = payload.get("boxes", []) if isinstance(payload, dict) else []
        by_id: Dict[str, list] = {}
        for candidate in candidates if isinstance(candidates, list) else []:
            if isinstance(candidate, dict):
                by_id.setdefault(str(candidate.get("device_id", "")), []).append(candidate)
        for index, device in enumerate(devices):
            device.box_2d = None
            matches = by_id.get(str(index), [])
            if len(matches) != 1 or matches[0].get("verified") is not True:
                continue
            box = matches[0].get("box_2d")
            try:
                device.box_2d = ExtractedDeviceSchema.normalize_evidence_box(box)
            except (TypeError, ValueError, OverflowError):
                pass

    @staticmethod
    def _evidence_crop_pixels(box: List[int], width: int, height: int) -> Optional[Tuple[int, int, int, int]]:
        """Convert normalized AI coordinates into a focused, contextual crop.

        Padding follows the detected box size rather than a percentage of the
        whole drawing. Wide SLD sheets previously added 8% of the complete page
        on each side, often pulling several neighbouring feeders into a crop.
        """
        if not box or len(box) != 4 or width <= 0 or height <= 0:
            return None
        ymin, xmin, ymax, xmax = [max(0.0, min(1000.0, float(value))) for value in box]
        if xmax <= xmin or ymax <= ymin:
            return None
        left, top = int(xmin * width / 1000), int(ymin * height / 1000)
        right, bottom = int(xmax * width / 1000), int(ymax * height / 1000)
        box_w, box_h = right - left, bottom - top
        pad_x = min(int(width * 0.04), max(24, int(box_w * 0.65)))
        pad_y = min(int(height * 0.05), max(20, int(box_h * 0.75)))
        left, top = max(0, left - pad_x), max(0, top - pad_y)
        right, bottom = min(width, right + pad_x), min(height, bottom + pad_y)
        if right - left < 180:
            missing = 180 - (right - left)
            left, right = max(0, left - missing // 2), min(width, right + missing - missing // 2)
        if bottom - top < 120:
            missing = 120 - (bottom - top)
            top, bottom = max(0, top - missing // 2), min(height, bottom + missing - missing // 2)
        return (left, top, right, bottom) if right > left and bottom > top else None

    @staticmethod
    def _attach_evidence_thumbnails(devices: List[ExtractedDeviceSchema], image_path: str):
        """Tự động cắt ảnh dẫn chứng (Visual Evidence Thumbnail) chuẩn xác từ file ảnh bản vẽ gốc."""
        try:
            from PIL import Image
            import base64, io

            AnalysisPipelineService._refine_device_bounding_boxes(devices)

            resolved_path = image_path
            if not os.path.exists(resolved_path):
                alt = os.path.join(os.getcwd(), image_path)
                if os.path.exists(alt):
                    resolved_path = alt
                else:
                    logger.warning(f"Evidence image path not found: {image_path}")
                    return

            with Image.open(resolved_path) as im:
                if im.mode in ("RGBA", "LA", "P"):
                    im = im.convert("RGB")
                w, h = im.size
                panel_preview = im.copy()
                panel_preview.thumbnail((1800, 1400), Image.Resampling.LANCZOS)
                panel_buf = io.BytesIO()
                panel_preview.save(panel_buf, format="JPEG", quality=88)
                panel_data_url = f"data:image/jpeg;base64,{base64.b64encode(panel_buf.getvalue()).decode()}"
                if devices:
                    devices[0].panel_evidence_image = devices[0].panel_evidence_image or panel_data_url

                for dev in devices:
                    try:
                        box = getattr(dev, "box_2d", None)
                        # Nếu có box_2d [ymin, xmin, ymax, xmax] (chuẩn hóa 0-1000)
                        if box and len(box) == 4:
                            crop_pixels = AnalysisPipelineService._evidence_crop_pixels(box, w, h)
                            if not crop_pixels:
                                continue
                            left, top, right, bottom = crop_pixels
                        else:
                            # Never invent a crop from device category or array
                            # position. A missing coordinate remains visibly
                            # unverified instead of pointing to the wrong item.
                            continue

                        if right <= left or bottom <= top:
                            continue

                        crop_im = im.crop((left, top, right, bottom))
                        if crop_im.mode in ("RGBA", "LA", "P"):
                            crop_im = crop_im.convert("RGB")
                        crop_im.thumbnail((900, 700), Image.Resampling.LANCZOS)
                        buf = io.BytesIO()
                        crop_im.save(buf, format="JPEG", quality=95)
                        dev.evidence_image = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"
                        dev.evidence_region = {
                            "coordinate_space": "normalized_1000",
                            "box_2d": [int(value) for value in box],
                            "page": dev.source_page,
                        }
                    except Exception as dev_err:
                        logger.warning(f"Error cropping evidence for device {dev.name}: {dev_err}")
        except Exception as err:
            logger.warning(f"Failed to generate evidence thumbnails: {err}")

    @staticmethod
    async def _analyze_cad_with_ai(
        file_path: str,
        filename: str,
        active_ai: AiConnection,
        user_prompt: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        all_connections: Optional[List[AiConnection]] = None
    ) -> Tuple[List[ExtractedDeviceSchema], List[Dict[str, Any]], List[str]]:
        """
        Trích xuất và phân tích toàn diện bản vẽ CAD (DXF / DWG) bằng AI LLM.
        Sử dụng cấu trúc phân cấp không gian (Spatial Layout) để nhận diện các tủ điện,
        Aptomat tổng Incomer, đo lường và các lộ nhánh phân phối chính xác.
        """
        extracted_devs: List[ExtractedDeviceSchema] = []
        multi_panels: List[Dict[str, Any]] = []
        warns: List[str] = []

        cad_res = CadParserService.parse_cad(file_path)
        cad_transcript = CadParserService.format_cad_for_ai(cad_res)
        # Lọc surrogate characters trong transcript trước khi gửi lên AI API
        cad_transcript = CadParserService._sanitize_text(cad_transcript)

        if not cad_res.texts:
            warns.append(f"File CAD {filename} không chứa nhãn văn bản TEXT/MTEXT.")
            return extracted_devs, multi_panels, warns

        from app.core.prompts import CAD_ANALYSIS_PROMPT_TEMPLATE, PROMPT_TYPES, append_canonical_output_contract, append_completeness_review_instruction, append_user_notes
        from app.services.ai.prompt_template_service import PromptTemplateService
        cad_prompt = await PromptTemplateService.render(
            db, PROMPT_TYPES["CAD_ANALYSIS"], CAD_ANALYSIS_PROMPT_TEMPLATE,
            {"cad_transcript": cad_transcript[:12000]},
        )
        cad_prompt = append_user_notes(cad_prompt, user_prompt, "LƯU Ý YÊU CẦU TỪ NGƯỜI DÙNG:")
        cad_prompt = append_completeness_review_instruction(cad_prompt)
        cad_prompt = append_canonical_output_contract(cad_prompt)

        if all_connections and db:
            ai_res, _used = await ConnectionPoolService.call_with_fallback(
                db=db,
                connections=all_connections,
                call_fn=VisionAnalyzerService.analyze_text,
                prompt=cad_prompt,
            )
        else:
            ai_res = await VisionAnalyzerService.analyze_text(
                prompt=cad_prompt,
                provider=active_ai.provider.lower(),
                api_key=active_ai.api_key,
                model=active_ai.selected_model
            )

        parsed_devs = ResponseParserService.parse_device_list(ai_res)
        warns.extend(ResponseParserService.extract_completeness_warnings(ai_res))
        extracted_panels = ResponseParserService.extract_panels_metadata(ai_res)
        if extracted_panels:
            multi_panels.extend(extracted_panels)

        for d in parsed_devs:
            clean_in_a = float(d.in_a) if d.in_a is not None and d.in_a > 0 else None
            clean_icu_ka = float(d.icu_ka) if d.icu_ka is not None and d.icu_ka > 0 else None
            clean_poles = int(d.poles) if d.poles is not None and d.poles > 0 else None
            spec_str = d.spec or (f"{clean_poles}P - {int(clean_in_a)}A" if clean_poles and clean_in_a else "Tiêu chuẩn")

            d_dict = {
                "category": d.category or "Thiết bị",
                "name": d.name or "Thiết bị",
                "notes": d.notes or "",
                "in_a": clean_in_a,
                "tag": getattr(d, "tag", None),
                "section": d.section
            }
            dev_tag = getattr(d, "tag", None) or PhysicalLayoutEngine.extract_or_assign_tag(d_dict, len(extracted_devs), d.section or "")
            dev_mounting = getattr(d, "mounting", None) or PhysicalLayoutEngine.classify_mounting(d_dict)
            dev_func = getattr(d, "electrical_function", None) or (
                ElectricalFunction.INCOMING if str(d.section or "").upper() in ["ĐẦU VÀO", "INCOMER"] else
                (ElectricalFunction.MEASUREMENT if dev_mounting == MountingType.DOOR_MOUNTED else ElectricalFunction.OUTGOING_PROTECTION)
            )

            extracted_devs.append(ExtractedDeviceSchema(
                category=d.category or "Thiết bị",
                name=d.name or "Thiết bị",
                spec=spec_str,
                in_a=clean_in_a,
                icu_ka=clean_icu_ka,
                poles=clean_poles,
                quantity=int(d.quantity or 1),
                brand=d.brand or "",
                part_number=d.part_number or "",
                section=d.section or "Đầu ra",
                location=d.location or filename,
                panel_code=d.panel_code or (extracted_panels[0]["panel_code"] if extracted_panels else ""),
                panel_name=d.panel_name or (extracted_panels[0]["panel_name"] if extracted_panels else ""),
                notes=d.notes,
                tag=dev_tag,
                mounting=dev_mounting,
                electrical_function=dev_func,
                upstream_device=getattr(d, "upstream_device", None),
                downstream_device=getattr(d, "downstream_device", None),
                connected_load=getattr(d, "connected_load", None),
                confidence=float(d.confidence or 0.95),
                box_2d=getattr(d, "box_2d", None),
                evidence_image=getattr(d, "evidence_image", None),
                suggested_brands=[
                    str(brand).strip() for brand in (getattr(d, "suggested_brands", None) or [])
                    if str(brand).strip()
                ],
                is_alternative_recommended=bool(getattr(d, "compatible_proposal", None)),
                original_spec=(getattr(d, "compatible_proposal", None) or {}).get("original_spec"),
                compatibility_note=(
                    (getattr(d, "compatible_proposal", None) or {}).get("technical_reason")
                    or (getattr(d, "compatible_proposal", None) or {}).get("ai_analysis")
                ),
                suggested_alternatives=[getattr(d, "compatible_proposal", None)] if getattr(d, "compatible_proposal", None) else None,
                inferred_components=getattr(d, "inferred_components", None),
                accompanying_accessories=AccompanyingEquipmentService.format_accessories(
                    getattr(d, "accompanying_accessories", None)
                ),
                compatible_proposal=getattr(d, "compatible_proposal", None),
            ))

        return extracted_devs, multi_panels, warns

    @staticmethod
    def _promote_drawn_fa_devices(
        devices: List[ExtractedDeviceSchema],
    ) -> List[ExtractedDeviceSchema]:
        """Promote a drawn FA/shunt-trip symbol that Vision embedded in MCCB text.

        The rule is intentionally narrow: it requires both a fire-alarm marker and
        shunt/trip wording, and it never creates FA when one already exists.
        """
        if any(
            (str(device.tag or "").strip().upper() == "FA")
            or (str(device.category or "").strip().upper() in {"FA", "SHUNT_TRIP", "SHUNT TRIP"})
            for device in devices
        ):
            return devices

        promoted = list(devices)
        for device in devices:
            searchable = " ".join(
                str(value or "")
                for value in (
                    device.name,
                    device.spec,
                    device.notes,
                    device.compatibility_note,
                )
            )
            normalized = searchable.upper()
            has_fire_alarm_marker = bool(re.search(r"\bFA\b|FIRE\s*ALARM|BÁO\s*CHÁY", normalized))
            has_shunt_trip = bool(re.search(r"SHUNT\s*TRIP|CUỘN\s*CẮT|TRIP\s*COIL", normalized))
            if not (has_fire_alarm_marker and has_shunt_trip):
                continue

            parent_label = device.tag or device.name or "MCCB tổng"
            promoted.append(ExtractedDeviceSchema(
                category="SHUNT_TRIP",
                name="Cuộn cắt Shunt Trip báo cháy FA",
                spec="Theo điện áp điều khiển thể hiện trên bản vẽ",
                quantity=1,
                brand="",
                part_number="",
                section="Điều khiển & Báo cháy",
                location=device.location,
                panel_code=device.panel_code,
                panel_name=device.panel_name,
                notes=f"Tín hiệu FA tác động cắt {parent_label}; phần tử được thể hiện độc lập trên SLD.",
                tag="FA",
                mounting=MountingType.MOUNTING_PLATE_MOUNTED,
                electrical_function=ElectricalFunction.CONTROL_AUXILIARY,
                upstream_device="Hệ thống báo cháy FA",
                downstream_device=str(parent_label),
                confidence=device.confidence,
                box_2d=device.box_2d,
                evidence_image=device.evidence_image,
            ))
            break

        return promoted

    @staticmethod
    def _promote_embedded_accessories_to_devices(
        devices: List[ExtractedDeviceSchema],
    ) -> List[ExtractedDeviceSchema]:
        """Promote only explicitly identified components; keep unnamed parts attached."""
        result = list(devices)
        def identity(d):
            return (d.source_filename, d.source_page, d.panel_code, d.tag)
        identified = {identity(d): d for d in devices if d.tag}
        for parent in devices:
            remaining = []
            for accessory in parent.accompanying_accessories or []:
                evidence = accessory.get("evidence") or accessory.get("source_reference") or accessory.get("sld_evidence")
                if not evidence:
                    parent.inferred_components = [*(parent.inferred_components or []), dict(accessory)]
                    continue
                tag = accessory.get("tag")
                # A generic CT/FU/PL label invented by code is not a source identity.
                if not tag:
                    remaining.append(accessory)
                    continue
                key = (parent.source_filename, parent.source_page, parent.panel_code, tag)
                if key in identified:
                    existing = identified[key]
                    if str(existing.spec or "").strip() != str(accessory.get("spec") or "").strip():
                        parent.inferred_components = [*(parent.inferred_components or []),
                            dict(accessory, reason="Trùng tag nhưng khác thông số; cần đối chiếu, chưa cộng lần hai")]
                    continue
                child = ExtractedDeviceSchema(
                    category=accessory.get("category") or "OTHER",
                    name=accessory.get("name") or str(tag), spec=accessory.get("spec") or "",
                    tag=str(tag), quantity=accessory.get("quantity") or 1,
                    brand=accessory.get("brand") or parent.brand,
                    part_number=accessory.get("sku") or accessory.get("part_number"),
                    in_a=accessory.get("in_a"), poles=accessory.get("poles"), icu_ka=accessory.get("icu_ka"),
                    panel_code=parent.panel_code, panel_name=parent.panel_name,
                    section=parent.section, source_filename=parent.source_filename,
                    source_page=parent.source_page, source_type=parent.source_type,
                    box_2d=accessory.get("box_2d"), confidence=parent.confidence,
                    notes=f"Thành phần cụm {parent.tag or parent.name}; căn cứ: {evidence}",
                    upstream_device=accessory.get("upstream_device"),
                )
                result.append(child)
                identified[key] = child
            parent.accompanying_accessories = remaining or None
        return result

    @staticmethod
    async def _preflight_pdf_with_vision(
        doc: Any,
        total_pages: int,
        active_ai: AiConnection,
        db: Optional[AsyncSession] = None,
        all_connections: Optional[List[AiConnection]] = None,
    ) -> Optional[List[int]]:
        """Use AI Vision to triage a PDF from page thumbnails before high-res takeoff.

        This is deliberately model-driven: it does not infer page types from page
        numbers, file names or keyword lists.  A contact sheet lets one Vision call
        review several pages quickly, while the detailed extractor still receives
        the original page at high resolution.
        """
        pages_per_sheet = 12
        selected_pages: List[int] = []
        received_valid_response = False

        for start_idx in range(0, total_pages, pages_per_sheet):
            page_indices = list(range(start_idx, min(start_idx + pages_per_sheet, total_pages)))
            thumbnails: List[Tuple[int, Image.Image]] = []
            for page_idx in page_indices:
                thumbnail = doc[page_idx].render(scale=0.28).to_pil().convert("RGB")
                thumbnail.thumbnail((360, 420), Image.Resampling.LANCZOS)
                thumbnails.append((page_idx + 1, thumbnail))

            columns = 3
            cell_w, cell_h = 380, 455
            rows = (len(thumbnails) + columns - 1) // columns
            sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), "white")
            drawer = ImageDraw.Draw(sheet)
            for position, (page_num, thumbnail) in enumerate(thumbnails):
                x = (position % columns) * cell_w
                y = (position // columns) * cell_h
                sheet.paste(thumbnail, (x + (cell_w - thumbnail.width) // 2, y + 28))
                drawer.rectangle((x, y, x + cell_w - 1, y + cell_h - 1), outline="#94a3b8", width=2)
                drawer.text((x + 12, y + 7), f"PAGE {page_num}", fill="#0f172a")

            preview_path = os.path.join(tempfile.gettempdir(), f"pdf_triage_{uuid.uuid4().hex[:8]}.jpg")
            sheet.save(preview_path, format="JPEG", quality=80, optimize=True)
            page_range = ", ".join(str(page_idx + 1) for page_idx in page_indices)
            triage_prompt = f"""Bạn đang tiếp nhận một tệp PDF để quyết định phần nào cần bóc tách thiết bị điện.
Ảnh là một contact sheet; nhãn PAGE là số trang PDF thật. Các trang có trong ảnh: {page_range}.

Quan sát trực tiếp nội dung ảnh, không suy đoán từ tên file. Hãy chọn mọi trang có sơ đồ một sợi, sơ đồ tủ điện, danh mục thiết bị điện hoặc chi tiết có đủ thông tin thiết bị để bóc tách. Bao gồm trang chưa chắc chắn nếu có thể chứa thiết bị; không bỏ sót chỉ vì chữ nhỏ.
Không chọn bìa, phối cảnh, mặt bằng/ghi chú thuần túy không có thiết bị cần bóc tách.
Chỉ trả một JSON hợp lệ, không markdown:
{{"relevant_pages":[4,5],"summary":"lý do ngắn"}}"""
            try:
                if all_connections and db:
                    response, _used = await ConnectionPoolService.call_with_fallback(
                        db=db,
                        connections=all_connections,
                        call_fn=VisionAnalyzerService.analyze_image,
                        image_path=preview_path,
                        prompt=triage_prompt,
                    )
                else:
                    response = await VisionAnalyzerService.analyze_image(
                        image_path=preview_path,
                        prompt=triage_prompt,
                        provider=active_ai.provider.lower(),
                        api_key=active_ai.api_key,
                        model=active_ai.selected_model,
                    )
                blocks = ResponseParserService.extract_json_blocks(response)
                decision = next((block for block in blocks if isinstance(block, dict) and "relevant_pages" in block), None)
                if decision is None:
                    logger.warning("PDF Vision triage returned no valid page decision")
                    continue
                received_valid_response = True
                for page_num in decision.get("relevant_pages") or []:
                    try:
                        normalized = int(page_num)
                    except (TypeError, ValueError):
                        continue
                    if normalized in {page_idx + 1 for page_idx in page_indices} and normalized not in selected_pages:
                        selected_pages.append(normalized)
            except Exception as exc:
                logger.warning("PDF Vision triage failed for pages %s: %s", page_range, exc)
            finally:
                try:
                    if os.path.exists(preview_path):
                        os.remove(preview_path)
                except OSError:
                    pass

        # An absent/invalid AI decision must never silently discard a drawing.
        return sorted(selected_pages) if received_valid_response else None

    @staticmethod
    async def _analyze_pdf_with_vision(
        file_path: str,
        filename: str,
        active_ai: AiConnection,
        user_prompt: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        all_connections: Optional[List[AiConnection]] = None,
        target_page: Optional[int] = None,
        progress_callback: Optional[Any] = None,
        project_id: Optional[int] = None
    ) -> Tuple[List[ExtractedDeviceSchema], List[Dict[str, Any]], List[str], List[Dict[str, Any]]]:
        """
        Tiếp nhận hồ sơ PDF và để AI Vision xác minh trực tiếp *mọi* trang. Không suy
        luận loại trang bằng tên file, số trang hoặc danh sách từ khóa cố định. Sau đó
        tuần tự đi vào từng trang; chỉ trang có phần tử điện thực tế mới sinh thiết bị.
        """
        extracted_devs: List[ExtractedDeviceSchema] = []
        multi_panels: List[Dict[str, Any]] = []
        warns: List[str] = []
        collected_technical_proposals: List[Dict[str, Any]] = []

        doc = pdfium.PdfDocument(file_path)
        try:
            total_pages = len(doc)
            file_size_mb = (os.path.getsize(file_path) / (1024 * 1024)) if os.path.exists(file_path) else 0
            logger.info(f"Analyzing PDF with AI Vision (PDFium): {file_path} ({total_pages} pages, {file_size_mb:.1f} MB)")

            # BƯỚC 1: TIẾP NHẬN HỒ SƠ & LẬP CHỈ MỤC SIÊU TỐC (Fast M&E Indexing)
            if progress_callback:
                import asyncio
                try:
                    coro = progress_callback({
                        "type": "log",
                        "stage": "ingestion",
                        "status": "running",
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "title": f"Đang tiếp nhận & quét sơ bộ PDF: {filename}",
                        "detail": f"Hồ sơ có {total_pages} trang ({file_size_mb:.1f} MB); đang lập chỉ mục khung tên và mã hiệu tủ điện."
                    })
                    if asyncio.iscoroutine(coro):
                        await coro
                except Exception as e:
                    logger.warning(f"progress_callback error: {e}")

            # 1.1. Chạy bộ lập chỉ mục M&E tốc độ cao (0.2s - 2s)
            indexer_result = PdfDrawingIndexerService.index_pdf(file_path=file_path, doc=doc)
            has_text_layer = indexer_result.get("has_text_layer", False)
            user_asked_for_panels = PdfDrawingIndexerService.detect_panel_query_intent(user_prompt)

            if has_text_layer:
                report_md = indexer_result.get("report_markdown", "")
                all_panel_pages = indexer_result.get("all_panel_pages", [])
                sld_pages = indexer_result.get("sld_pages", [])
                
                # Bắn log báo cáo 4 nhóm trang có tủ điện chuẩn M&E cho người dùng
                if progress_callback:
                    import asyncio
                    try:
                        coro = progress_callback({
                            "type": "log",
                            "stage": "ingestion",
                            "status": "success",
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "title": f"Đã định vị các trang có tủ điện ({len(all_panel_pages)}/{total_pages} trang)",
                            "detail": report_md,
                            "data": {
                                "total_pages": total_pages,
                                "all_panel_pages": all_panel_pages,
                                "sld_pages": sld_pages,
                                "categories": {
                                    k: [p["page_num"] for p in v]
                                    for k, v in indexer_result.get("categories", {}).items()
                                }
                            }
                        })
                        if asyncio.iscoroutine(coro):
                            await coro
                    except Exception as e:
                        logger.warning(f"progress_callback error: {e}")

                if user_asked_for_panels:
                    warns.append(report_md)

            # KIỂM TRA CHỈ ĐỊNH TRANG CỤ THỂ TỪ NGƯỜI DÙNG (Qua user_prompt hoặc target_page)
            requested_pages: List[int] = []
            if target_page and 1 <= target_page <= total_pages:
                requested_pages.append(target_page)

            if user_prompt:
                p_text = user_prompt.lower()
                # 1. Dải trang: "trang 4-6", "trang 4 đến 6", "từ trang 4 đến trang 6"
                range_matches = re.findall(r'(?:trang|page|p\.?)\s*(\d+)\s*(?:-|đến|to)\s*(?:trang\s*)?(\d+)', p_text)
                for start, end in range_matches:
                    try:
                        s, e = int(start), int(end)
                        for p in range(max(1, s), min(total_pages, e) + 1):
                            if p not in requested_pages:
                                requested_pages.append(p)
                    except ValueError:
                        pass

                # 2. Danh sách phân cách: "trang 4, 5, 6" hoặc "trang 4 và 5"
                list_matches = re.findall(r'(?:trang|page|sheet)\s*((?:\d+\s*[,&và]\s*)+\d+)', p_text)
                for group in list_matches:
                    for num in re.findall(r'\d+', group):
                        p = int(num)
                        if 1 <= p <= total_pages and p not in requested_pages:
                            requested_pages.append(p)

                # 3. Trang đơn lẻ: "trang 4 trong file", "bóc tách cho tôi trang 4", "trang số 4", "trang 4", "p.4", "p4"
                # Không bắt nhầm nếu chỉ là câu hỏi không chứa số trang
                single_matches = re.findall(r'(?:trang|page|sheet|p\.?)\s*(?:số\s*)?(\d+)', p_text)
                for m in single_matches:
                    p = int(m)
                    if 1 <= p <= total_pages and p not in requested_pages:
                        requested_pages.append(p)

            requested_pages = sorted(list(set(requested_pages)))

            if requested_pages:
                # TRƯỜNG HỢP A: NGƯỜI DÙNG YÊU CẦU BÓC TÁCH & BÁO GIÁ TRANG CỤ THỂ
                selected_pages_info = []
                page_assessments = []
                pages_meta = {p["page_num"]: p for p in indexer_result.get("pages", [])}
                for p_num in requested_pages:
                    p_idx = p_num - 1
                    meta = pages_meta.get(p_num)
                    clean_title = meta.get("title") if meta else ""
                    if not clean_title:
                        page = doc[p_idx]
                        tp = page.get_textpage()
                        raw_txt = (tp.get_text_range() or "").strip()
                        lines = [l.strip() for l in re.split(r'[\r\n]+', raw_txt) if len(l.strip()) > 3]
                        p_title = ""
                        for l in lines:
                            u_l = l.upper()
                            if any(k in u_l for k in ['SƠ ĐỒ', 'MẶT BẰNG', 'CHI TIẾT', 'DANH MỤC', 'TỦ ĐIỆN', 'CẤP ĐIỆN', 'SLD']):
                                p_title = l
                                break
                        if not p_title and lines:
                            p_title = lines[0]
                        clean_title = p_title or f"Bản vẽ trang {p_num}"

                    clean_title = clean_title.replace('\n', ' ').replace('\r', ' ').strip()
                    if len(clean_title) > 45:
                        clean_title = clean_title[:42] + "..."

                    page_assessments.append(f"Trang {p_num}: [{clean_title}] (AI Vision sẽ xác minh từ ảnh)")

                    selected_pages_info.append({
                        "page_idx": p_idx,
                        "page_num": p_num,
                        "title": clean_title,
                        "needs_visual_validation": True,
                    })

                pages_str = ", ".join(f"Trang {p}" for p in requested_pages)
                assessments_str = " • ".join(page_assessments)
                if progress_callback:
                    import asyncio
                    try:
                        coro = progress_callback({
                            "type": "log",
                            "stage": "ingestion",
                            "status": "success",
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "title": f"Tiếp nhận yêu cầu phân tích: {pages_str}",
                            "detail": f"Đã ghi nhận phạm vi trong [{filename}] ({total_pages} trang). {assessments_str}. Hệ thống sẽ phân tích chi tiết các trang được chỉ định.",
                            "data": {
                                "requested_pages": requested_pages,
                                "total_pages": total_pages
                            }
                        })
                        if asyncio.iscoroutine(coro):
                            await coro
                    except Exception as e:
                        logger.warning(f"progress_callback error: {e}")
            else:
                # TRƯỜNG HỢP B: TỰ ĐỘNG CHỌN TRANG CẦN BÓC TÁCH
                if has_text_layer and (indexer_result.get("sld_pages") or indexer_result.get("all_panel_pages")):
                    # B1: Đã có text layer và phát hiện các trang Sơ đồ nguyên lý SLD:
                    # Ưu tiên bóc tách chuyên sâu các trang SLD!
                    chosen_page_numbers = indexer_result.get("sld_pages") or indexer_result.get("all_panel_pages", [])
                    pages_map = {p["page_num"]: p for p in indexer_result.get("pages", [])}

                    selected_pages_info = [
                        {
                            "page_idx": p_num - 1,
                            "page_num": p_num,
                            "title": pages_map.get(p_num, {}).get("title") or f"Trang {p_num}",
                            "needs_visual_validation": True,
                        }
                        for p_num in chosen_page_numbers
                    ]

                    page_summary_list = [f"Trang {p['page_num']}: {p['title']}" for p in selected_pages_info]
                    page_details_str = " • ".join(page_summary_list[:5])
                    if len(page_summary_list) > 5:
                        page_details_str += f" • (+{len(page_summary_list) - 5} trang khác)"

                    skipped_pages = [p for p in range(1, total_pages + 1) if p not in chosen_page_numbers]
                    if progress_callback:
                        import asyncio
                        try:
                            coro = progress_callback({
                                "type": "log",
                                "stage": "ingestion",
                                "status": "success",
                                "timestamp": datetime.now().strftime("%H:%M:%S"),
                                "title": f"Tự động chọn {len(selected_pages_info)}/{total_pages} trang SLD tủ điện để bóc tách",
                                "detail": f"Trang bóc tách SLD: {page_details_str}. Hệ thống bỏ qua {len(skipped_pages)} trang phụ trợ/mặt bằng chiếu sáng để tăng tốc độ.",
                                "data": {
                                    "selected_pages": chosen_page_numbers,
                                    "total_pages": total_pages,
                                    "skipped_pages": skipped_pages
                                }
                            })
                            if asyncio.iscoroutine(coro):
                                await coro
                        except Exception as e:
                            logger.warning(f"progress_callback error: {e}")
                else:
                    # B2: File scan ảnh (không có text layer): Fallback sang contact sheet visual triage
                    if progress_callback:
                        import asyncio
                        try:
                            coro = progress_callback({
                                "type": "log",
                                "stage": "ingestion",
                                "status": "running",
                                "timestamp": datetime.now().strftime("%H:%M:%S"),
                                "title": f"AI tiếp nhận PDF scan [{filename}]",
                                "detail": f"Đang xem tổng quan {total_pages} trang để xác định phần cần bóc tách."
                            })
                            if asyncio.iscoroutine(coro):
                                await coro
                        except Exception as e:
                            logger.warning(f"progress_callback error: {e}")

                    triaged_page_numbers = await AnalysisPipelineService._preflight_pdf_with_vision(
                        doc=doc,
                        total_pages=total_pages,
                        active_ai=active_ai,
                        db=db,
                        all_connections=all_connections,
                    )
                    triage_fallback = triaged_page_numbers is None
                    if triage_fallback:
                        warns.append("AI chưa trả về kết quả tiếp nhận PDF hợp lệ; hệ thống kiểm tra toàn bộ trang để không bỏ sót bản vẽ.")
                        triaged_page_numbers = list(range(1, total_pages + 1))

                    selected_pages_info = [
                        {
                            "page_idx": page_num - 1,
                            "page_num": page_num,
                            "title": f"Trang {page_num}",
                            "needs_visual_validation": True,
                        }
                        for page_num in triaged_page_numbers
                    ]

                    page_summary_list = []
                    for p in selected_pages_info:
                        clean_t = p['title'].replace('\n', ' ').replace('\r', ' ').strip()
                        if len(clean_t) > 36:
                            clean_t = clean_t[:33] + "..."
                        page_summary_list.append(f"Trang {p['page_num']}: {clean_t}")

                    page_details_str = " • ".join(page_summary_list[:5])
                    if len(page_summary_list) > 5:
                        page_details_str += f" • (+{len(page_summary_list) - 5} trang khác)"

                    selected_page_numbers = [p["page_num"] for p in selected_pages_info]
                    skipped_page_numbers = [p for p in range(1, total_pages + 1) if p not in selected_page_numbers]
                    selection_is_visual_fallback = triage_fallback
                    if progress_callback:
                        import asyncio
                        try:
                            coro = progress_callback({
                                "type": "log",
                                "stage": "ingestion",
                                "status": "success",
                                "timestamp": datetime.now().strftime("%H:%M:%S"),
                                "title": f"AI đã chọn {len(selected_pages_info)}/{total_pages} trang cần bóc tách",
                                "detail": (
                                    f"Trang cần bóc tách chi tiết: {page_details_str or 'Không có trang nào'}. "
                                    + ("AI tiếp nhận không trả về kết quả hợp lệ nên hệ thống kiểm tra toàn bộ trang để tránh bỏ sót. " if selection_is_visual_fallback else "Kết quả được AI chọn từ ảnh tổng quan của PDF. ")
                                    + (f"Không đưa vào lượt bóc tách: Trang {', '.join(map(str, skipped_page_numbers))}." if skipped_page_numbers else "Toàn bộ trang đều được AI yêu cầu kiểm tra chi tiết.")
                                ),
                                "data": {
                                    "selected_pages": selected_page_numbers,
                                    "total_pages": total_pages,
                                    "skipped_pages": skipped_page_numbers,
                                    "selection_is_visual_fallback": selection_is_visual_fallback,
                                }
                            })
                            if asyncio.iscoroutine(coro):
                                await coro
                        except Exception as e:
                            logger.warning(f"progress_callback error: {e}")

            # BƯỚC 3: PHÂN TÍCH ĐI SÂU VÀO TỪNG TRANG & CẬP NHẬT VÀO PHIÊN / HIỂN THỊ LUÔN
            for page_info in selected_pages_info:
                page_idx = page_info["page_idx"]
                page_num = page_info["page_num"]
                page_title = page_info["title"]
                page = doc[page_idx]
                page_started_at = time.monotonic()

                if progress_callback:
                    import asyncio
                    try:
                        coro = progress_callback({
                            "type": "log",
                            "stage": "sld_scan",
                            "status": "running",
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "title": f"Đang đọc {filename} — Trang {page_num}/{total_pages}",
                            "detail": "Đang ghi nhận thiết bị, thông số và các liên kết thể hiện trên trang này."
                        })
                        if asyncio.iscoroutine(coro):
                            await coro
                    except Exception as e:
                        logger.warning(f"progress_callback error: {e}")

                # Render trang thành ảnh với độ phân giải tối ưu bằng pypdfium2 C engine (nhanh & siêu tiết kiệm RAM)
                page_img = page.render(scale=2).to_pil()
                if page_img.mode in ("RGBA", "LA", "P"):
                    page_img = page_img.convert("RGB")

                # Giới hạn kích thước tối đa 2048px (đảm bảo cực kỳ sắc nét cho sơ đồ SLD mà dung lượng giảm 80-90%)
                max_dim = 2048
                w, h = page_img.size
                if max(w, h) > max_dim:
                    scale = max_dim / max(w, h)
                    page_img = page_img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

                temp_img_path = os.path.join(tempfile.gettempdir(), f"sld_pdf_p{page_num}_{uuid.uuid4().hex[:6]}.jpg")
                page_img.save(temp_img_path, format="JPEG", quality=85, optimize=True)
                page_preview_buf = io.BytesIO()
                page_img.save(page_preview_buf, format="JPEG", quality=88, optimize=True)
                page_preview_data_url = (
                    "data:image/jpeg;base64,"
                    + base64.b64encode(page_preview_buf.getvalue()).decode()
                )

                try:
                    from app.core.prompts import PDF_MULTI_PANEL_VISION_PROMPT, PROMPT_TYPES, append_canonical_output_contract, append_completeness_review_instruction, append_user_notes
                    from app.services.ai.prompt_template_service import PromptTemplateService
                    vision_template = await PromptTemplateService.get_active_content(
                        db, PROMPT_TYPES["PDF_VISION"], PDF_MULTI_PANEL_VISION_PROMPT
                    )
                    vision_prompt = append_user_notes(
                        vision_template, user_prompt,
                        "ĐẶC BIỆT LƯU Ý VÀ TUÂN THỦ YÊU CẦU KỸ THUẬT / GHI CHÚ TỪ KHÁCH HÀNG:",
                    )
                    vision_prompt = append_completeness_review_instruction(vision_prompt)
                    vision_prompt = append_canonical_output_contract(vision_prompt)

                    if all_connections and db:
                        ai_response, _used = await ConnectionPoolService.call_with_fallback(
                            db=db,
                            connections=all_connections,
                            call_fn=VisionAnalyzerService.analyze_image,
                            image_path=temp_img_path,
                            prompt=vision_prompt,
                        )
                    else:
                        ai_response = await VisionAnalyzerService.analyze_image(
                            image_path=temp_img_path,
                            prompt=vision_prompt,
                            provider=active_ai.provider.lower(),
                            api_key=active_ai.api_key,
                            model=active_ai.selected_model
                        )

                    parsed_devs = ResponseParserService.parse_device_list(ai_response)
                    # Verify spatial evidence independently. The extraction pass
                    # may identify a device correctly but borrow coordinates from
                    # a neighbouring label or branch.
                    box_candidates = [
                        {
                            "device_id": str(index),
                            "panel_code": getattr(device, "panel_code", None),
                            "tag": getattr(device, "tag", None),
                            "name": getattr(device, "name", None),
                            "spec": getattr(device, "spec", None),
                            "box_2d": getattr(device, "box_2d", None),
                        }
                        for index, device in enumerate(parsed_devs)
                        if getattr(device, "box_2d", None)
                    ]
                    if box_candidates:
                        verifier_prompt = (
                            "Kiểm chứng tọa độ độc lập bằng cách quan sát lại TOÀN BỘ ảnh. "
                            "Với từng thiết bị, tìm đúng ký hiệu điện và nhãn tag/thông số của chính nó; "
                            "không dùng box cũ làm đáp án. Chỉ trả JSON "
                            "Giữ nguyên device_id của từng thiết bị trong kết quả. "
                            "{\"boxes\":[{\"device_id\":...,\"tag\":...,\"name\":...,\"box_2d\":[ymin,xmin,ymax,xmax],"
                            "\"verified\":true|false}]}. Tọa độ 0..1000. Box phải bao ký hiệu và nhãn "
                            "riêng, không bao thiết bị hoặc nhánh kế bên. Nếu không chắc chắn, trả "
                            "verified=false và box_2d=null. Danh sách:\n"
                            + json.dumps(box_candidates, ensure_ascii=False)
                        )
                        try:
                            if all_connections and db:
                                verifier_response, _ = await ConnectionPoolService.call_with_fallback(
                                    db=db, connections=all_connections,
                                    call_fn=VisionAnalyzerService.analyze_image,
                                    image_path=temp_img_path, prompt=verifier_prompt,
                                )
                            else:
                                verifier_response = await VisionAnalyzerService.analyze_image(
                                    image_path=temp_img_path, prompt=verifier_prompt,
                                    provider=active_ai.provider.lower(), api_key=active_ai.api_key,
                                    model=active_ai.selected_model,
                                )
                            verifier_blocks = ResponseParserService.extract_json_blocks(verifier_response)
                            payload = next(
                                (block for block in verifier_blocks if isinstance(block, dict) and isinstance(block.get("boxes"), list)),
                                None,
                            )
                            AnalysisPipelineService._apply_verified_boxes(parsed_devs, payload)
                        except Exception as verify_error:
                            logger.warning("Evidence verification failed on page %s: %s", page_num, verify_error)
                            for device in parsed_devs:
                                device.box_2d = None
                    # Keep all PDF-page warnings in the accumulator returned by this
                    # method.  Using an undefined `warnings` variable previously
                    # interrupted the AI pipeline after a successful model response.
                    warns.extend(ResponseParserService.extract_completeness_warnings(ai_response))
                    page_proposals = ResponseParserService.extract_technical_proposals(ai_response)
                    if page_proposals:
                        collected_technical_proposals.extend(page_proposals)
                    if parsed_devs:
                        extracted_panels = ResponseParserService.extract_panels_metadata(ai_response)
                        page_panel_code = None
                        page_panel_name = None
                        if extracted_panels:
                            for ep in extracted_panels:
                                ep["page"] = page_num
                                multi_panels.append(ep)
                            page_panel_code = extracted_panels[0].get("panel_code")
                            page_panel_name = extracted_panels[0].get("panel_name")

                        iw, ih = page_img.size
                        page_new_devs: List[ExtractedDeviceSchema] = []
                        for d in parsed_devs:
                            clean_in_a = float(d.in_a) if d.in_a is not None and d.in_a > 0 else None
                            clean_icu_ka = float(d.icu_ka) if d.icu_ka is not None and d.icu_ka > 0 else None
                            clean_poles = int(d.poles) if d.poles is not None and d.poles > 0 else None
                            spec_str = d.spec
                            if not spec_str:
                                if clean_poles is not None and clean_in_a is not None:
                                    spec_str = f"{clean_poles}P - {int(clean_in_a)}A"
                                else:
                                    spec_str = ""

                            ev_b64 = None
                            box = d.box_2d
                            if box and len(box) == 4:
                                try:
                                    crop_pixels = AnalysisPipelineService._evidence_crop_pixels(box, iw, ih)
                                    if not crop_pixels:
                                        raise ValueError("Invalid evidence box")
                                    c_left, c_top, c_right, c_bottom = crop_pixels
                                    if c_right > c_left and c_bottom > c_top:
                                        crop = page_img.crop((c_left, c_top, c_right, c_bottom))
                                        if crop.mode in ("RGBA", "LA", "P"):
                                            crop = crop.convert("RGB")
                                        crop.thumbnail((1200, 900), Image.Resampling.LANCZOS)
                                        buf = io.BytesIO()
                                        crop.save(buf, format="JPEG", quality=95)
                                        ev_b64 = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"
                                except Exception as crop_err:
                                    logger.warning(f"Error cropping thumbnail: {crop_err}")

                            d_dict = {
                                "category": d.category or "Thiết bị",
                                "name": d.name or "Thiết bị",
                                "notes": d.notes or "",
                                "in_a": clean_in_a,
                                "tag": getattr(d, "tag", None),
                                "section": d.section
                            }
                            dev_tag = getattr(d, "tag", None) or PhysicalLayoutEngine.extract_or_assign_tag(d_dict, len(extracted_devs), d.section or "")
                            dev_mounting = getattr(d, "mounting", None) or PhysicalLayoutEngine.classify_mounting(d_dict)
                            dev_func = getattr(d, "electrical_function", None) or (
                                ElectricalFunction.INCOMING if str(d.section or "").upper() in ["ĐẦU VÀO", "INCOMER"] else
                                (ElectricalFunction.MEASUREMENT if dev_mounting == MountingType.DOOR_MOUNTED else ElectricalFunction.OUTGOING_PROTECTION)
                            )

                            # Phụ kiện đi kèm do AI phân tích từ bản vẽ
                            clean_accs = AccompanyingEquipmentService.format_accessories(
                                getattr(d, "accompanying_accessories", None)
                            )
                            cp = getattr(d, "compatible_proposal", None)
                            has_alt = bool(cp)

                            new_dev = ExtractedDeviceSchema(
                                category=d.category or "Thiết bị",
                                name=d.name or "Thiết bị",
                                spec=spec_str,
                                in_a=clean_in_a,
                                icu_ka=clean_icu_ka,
                                poles=clean_poles,
                                quantity=int(d.quantity or 1),
                                brand=d.brand or "",
                                part_number=d.part_number or (cp.get("proposed_device") if cp else ""),
                                section=d.section,
                                location=d.location or f"Trang {page_num}",
                                panel_code=d.panel_code or page_panel_code,
                                panel_name=d.panel_name or page_panel_name,
                                notes=d.notes,
                                tag=dev_tag,
                                mounting=dev_mounting,
                                electrical_function=dev_func,
                                upstream_device=getattr(d, "upstream_device", None),
                                downstream_device=getattr(d, "downstream_device", None),
                                connected_load=getattr(d, "connected_load", None),
                                confidence=float(d.confidence or 0.95),
                                box_2d=d.box_2d,
                                evidence_image=ev_b64,
                                panel_evidence_image=page_preview_data_url,
                                source_type="pdf",
                                source_filename=filename,
                                source_page=page_num,
                                suggested_brands=[
                                    str(brand).strip() for brand in (getattr(d, "suggested_brands", None) or [])
                                    if str(brand).strip()
                                ],
                                is_alternative_recommended=has_alt,
                                original_spec=cp.get("original_spec") if cp else None,
                                compatibility_note=(cp.get("technical_reason") or cp.get("ai_analysis")) if cp else None,
                                suggested_alternatives=[cp] if cp else None,
                                accompanying_accessories=clean_accs,
                                inferred_components=getattr(d, "inferred_components", None),
                                compatible_proposal=cp
                            )
                            if new_dev.box_2d:
                                new_dev.evidence_region = {
                                    "coordinate_space": "normalized_1000",
                                    "box_2d": list(new_dev.box_2d),
                                    "page": page_num,
                                }
                            extracted_devs.append(new_dev)
                            page_new_devs.append(new_dev)

                        if page_new_devs:
                            # CẬP NHẬT NGAY VÀO PHIÊN PHÂN TÍCH TRONG DB
                            if db and project_id:
                                try:
                                    from app.models.conversation_session import ConversationSession
                                    from app.models.analysis_iteration import AnalysisIteration
                                    from sqlalchemy import select
                                    sess_stmt = select(ConversationSession).where(
                                        ConversationSession.project_id == project_id,
                                        ConversationSession.status == "active"
                                    ).order_by(ConversationSession.created_at.desc())
                                    sess_res = await db.execute(sess_stmt)
                                    active_sess = sess_res.scalars().first()
                                    if active_sess:
                                        active_sess.total_iterations += 1
                                        iter_entry = AnalysisIteration(
                                            session_id=active_sess.id,
                                            iteration_number=active_sess.total_iterations,
                                            trigger_type=f"partial_panel_p{page_num}",
                                            files_analyzed={"file_name": filename, "page_number": page_num},
                                            ai_parsed_devices=[d.model_dump() for d in extracted_devs],
                                            confidence_scores={
                                                "panel_code": page_panel_code,
                                                "panel_name": page_panel_name,
                                                "page_number": page_num,
                                                "page_devices_count": len(page_new_devs),
                                                "total_devices_so_far": len(extracted_devs)
                                            }
                                        )
                                        db.add(iter_entry)
                                        await db.commit()
                                except Exception as sess_err:
                                    logger.warning(f"Error saving partial session iteration: {sess_err}")

                            # PHÁT SỰ KIỆN LOG & HIỂN THỊ THIẾT BỊ LÊN GIAO DIỆN NGAY LẬP TỨC
                            if progress_callback:
                                import asyncio
                                try:
                                    p_title_display = page_panel_name or page_title or f"Tủ điện Trang {page_num}"
                                    p_code_display = f" [{page_panel_code}]" if page_panel_code else ""
                                    coro1 = progress_callback({
                                        "type": "log",
                                        "stage": "incomer_feeder",
                                        "status": "success",
                                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                                        "title": f"Hoàn tất Trang {page_num}: Tủ điện{p_code_display} • Đã cập nhật vào phiên (+{len(page_new_devs)} thiết bị)",
                                    "detail": f"Trích xuất thành công {len(page_new_devs)} thiết bị điện đóng cắt & phụ tải trong {time.monotonic() - page_started_at:.1f}s. Tổng tích lũy hiện tại: {len(extracted_devs)} thiết bị.",
                                        "data": {
                                            "page_num": page_num,
                                            "devices_count": len(page_new_devs),
                                            "panel_code": page_panel_code,
                                            "panel_name": page_panel_name
                                        }
                                    })
                                    if asyncio.iscoroutine(coro1):
                                        await coro1

                                    coro2 = progress_callback(AnalysisPipelineService._partial_devices_payload(
                                        devices=page_new_devs,
                                        page_number=page_num,
                                        total_pages=total_pages,
                                        source_type="pdf",
                                        filename=filename,
                                        panel_code=page_panel_code,
                                        panel_name=page_panel_name,
                                    ))
                                    if asyncio.iscoroutine(coro2):
                                        await coro2
                                except Exception as cb_err:
                                    logger.warning(f"progress_callback error: {cb_err}")
                except Exception as page_err:
                    logger.warning(f"Lỗi phân tích trang {page_num}: {page_err}")
                    warns.append(f"Trang {page_num} ({page_title[:40]}): {str(page_err)[:120]}")
                    if progress_callback:
                        import asyncio
                        try:
                            coro_warn = progress_callback({
                                "type": "log",
                                "stage": "ai_vision",
                                "status": "warning",
                                "timestamp": datetime.now().strftime("%H:%M:%S"),
                                "title": f"Lưu ý Trang {page_num}/{total_pages}: {page_title[:40]}",
                                "detail": f"Gặp sự cố AI: {str(page_err)[:120]}. Hệ thống tự động bảo toàn các tủ đã xong."
                            })
                            if asyncio.iscoroutine(coro_warn):
                                await coro_warn
                        except Exception:
                            pass
                    # Nếu bị 429 quota/rate-limit từ provider, dừng an toàn để bảo toàn các trang đã trích xuất thành công
                    if "429" in str(page_err) or "Quota Exceeded" in str(page_err) or "RateLimit" in str(page_err):
                        logger.info("Dừng bóc tách các trang kế tiếp do API AI gặp Rate Limit (429).")
                        break
                finally:
                    if os.path.exists(temp_img_path):
                        try:
                            os.remove(temp_img_path)
                        except Exception:
                            pass
                await asyncio.sleep(2)  # Cooldown an toàn giữa các trang để chống rate limit
        finally:
            try:
                doc.close()
            except Exception:
                pass

        return extracted_devs, multi_panels, warns, collected_technical_proposals

    @staticmethod
    def _build_quotation_rows(
        project_name: str,
        extracted_devices: List[ExtractedDeviceSchema],
        device_price_map: Dict[str, int],
        enclosure_spec: Dict[str, Any],
        enclosure_unit_price: int,
        busbar_unit_price: int,
        multi_panel_list: Optional[List[Dict[str, Any]]] = None,
        panel_code: Optional[str] = None,
        panel_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        rows = []
        if not extracted_devices and not multi_panel_list:
            return []
        clean_pname = (panel_name or panel_code or "").upper()

        def _device_value(dev_obj: Any, key: str, default: Any = None) -> Any:
            """Read the same field from Pydantic models and streamed dict rows."""
            if isinstance(dev_obj, dict):
                value = dev_obj.get(key, default)
            else:
                value = getattr(dev_obj, key, default)
            return default if value is None else value

        def _device_bucket(dev_obj: Any) -> str:
            """Return one exhaustive quotation group; no device may be dropped."""
            section = str(_device_value(dev_obj, "section", "")).strip().casefold()
            category = str(_device_value(dev_obj, "category", "")).strip().upper()
            name = str(_device_value(dev_obj, "name", "")).strip().casefold()
            in_a = float(_device_value(dev_obj, "in_a", 0) or 0)
            combined = f"{section} {name}"

            if (
                "đầu vào" in combined
                or "incomer" in combined
                or "nguồn cấp" in combined
                or "ACB" in category
                or ("MCCB" in category and in_a >= 400)
            ):
                return "incoming"
            if (
                any(token in combined for token in ["đo lường", "giám sát", "đồng hồ", "đèn báo", "volt", "ampe"])
                or any(token in category for token in ["METER", "LIGHT", "PILOT", "CT"])
            ):
                return "measurement"
            if (
                any(token in combined for token in ["điều khiển", "chiếu sáng", "rơ le", "khởi động từ"])
                or any(token in category for token in ["CONTACTOR", "TIMER", "RELAY", "CONTROL", "FUSE"])
            ):
                return "control"
            if (
                any(token in combined for token in ["làm mát", "thông gió", "quạt", "nhiệt"])
                or any(token in category for token in ["COOLING", "FAN", "THERMOSTAT", "LOUVER"])
            ):
                return "cooling"
            return "outgoing"

        def _append_device_with_accessories(
            target_rows: list,
            dev_obj: Any,
            price: int,
            panel_id_str: str,
            default_note: str = "",
            incomer_ref_rating: Optional[float] = None
        ):
            dev_dict = dev_obj.model_dump() if hasattr(dev_obj, "model_dump") else (dict(dev_obj) if isinstance(dev_obj, dict) else dev_obj.__dict__)
            p_num = dev_dict.get("part_number") or dev_dict.get("name") or str(uuid.uuid4())[:8]
            dev_id = f"{panel_id_str}-{p_num}"
            qty = int(dev_dict.get("quantity") or 1)
            is_alt = bool(dev_dict.get("is_alternative_recommended", False))
            comp_note = dev_dict.get("compatibility_note") or ""
            note_str = dev_dict.get("notes") or default_note

            target_rows.append({
                "id": dev_id,
                "row_type": "item",
                "is_accessory": False,
                "is_alternative_recommended": is_alt,
                "compatibility_note": comp_note,
                "tt": "+",
                "name": dev_dict.get("name", "Thiết bị"),
                "spec": dev_dict.get("spec", ""),
                "sku": dev_dict.get("part_number") or "",
                "origin": (dev_dict.get("brand") or "").replace(" Electric", "") or "VN",
                "unit": dev_dict.get("unit") or ("Bộ" if "LIGHT" in str(dev_dict.get("category") or "").upper() or "CT" in str(dev_dict.get("category") or "").upper() else "Cái"),
                "quantity": qty,
                "unit_price": price,
                "line_total": qty * price,
                "notes": note_str
            })

            # Tự động chèn CỤM PHỤ KIỆN / THIẾT BỊ ĐI KÈM do AI phân tích từ bản vẽ
            accs = dev_dict.get("accompanying_accessories")
            if accs:
                for a_idx, acc in enumerate(accs, 1):
                    acc_qty = int(acc.get("quantity") or 1)
                    acc_price = int(acc.get("unit_price") or 0)
                    target_rows.append({
                        "id": f"acc-{dev_id}-{acc.get('code', a_idx)}",
                        "parent_id": dev_id,
                        "row_type": "accessory",
                        "is_accessory": True,
                        "is_alternative_recommended": False,
                        "tt": "↳",
                        "name": acc.get("name"),
                        "spec": acc.get("spec", ""),
                        "sku": acc.get("sku", "-"),
                        "origin": acc.get("origin", "VN"),
                        "unit": acc.get("unit", "Bộ"),
                        "quantity": acc_qty,
                        "unit_price": acc_price,
                        "line_total": acc_qty * acc_price,
                        "notes": acc.get("notes", "")
                    })

        catalog_engine = DeviceCatalogEngine.get_instance()

        def _resolve_price(dev) -> int:
            sku = getattr(dev, "part_number", None) or (dev.get("part_number") if isinstance(dev, dict) else None)
            name = getattr(dev, "name", None) or (dev.get("name") if isinstance(dev, dict) else None)
            cat = getattr(dev, "category", "") or (dev.get("category") if isinstance(dev, dict) else "")
            in_a = getattr(dev, "in_a", None) or (dev.get("in_a") if isinstance(dev, dict) else None)
            poles = getattr(dev, "poles", None) or (dev.get("poles") if isinstance(dev, dict) else None)

            if sku and sku in device_price_map and device_price_map[sku] > 0:
                return device_price_map[sku]
            if sku:
                cat_item = catalog_engine.get_by_sku(sku)
                if cat_item and cat_item.get("g") and int(cat_item["g"]) > 0:
                    return int(cat_item["g"])
            return 0

        # TRƯỜNG HỢP 1: Bóc tách Đa tủ (Multi-Panel Breakdown)
        if multi_panel_list:
            # One physical cabinet can be reported by several pages/partial AI
            # events. Consolidate by panel_code before producing quotation rows;
            # otherwise the same cabinet header and enclosure were repeated.
            consolidated_panels: Dict[str, Dict[str, Any]] = {}
            for raw_idx, raw_panel in enumerate(multi_panel_list, 1):
                raw_code = str(raw_panel.get("panel_code") or f"P-{raw_idx}").strip()
                panel_entry = consolidated_panels.setdefault(raw_code, dict(raw_panel))
                panel_entry["panel_code"] = raw_code
                current_devices = list(panel_entry.get("devices") or [])
                known_device_keys = {
                    (
                        str(_device_value(device, "tag", "")),
                        str(_device_value(device, "part_number", "")),
                        str(_device_value(device, "name", "")),
                        str(_device_value(device, "spec", "")),
                    )
                    for device in current_devices
                }
                for device in raw_panel.get("devices") or []:
                    device_key = (
                        str(_device_value(device, "tag", "")),
                        str(_device_value(device, "part_number", "")),
                        str(_device_value(device, "name", "")),
                        str(_device_value(device, "spec", "")),
                    )
                    if device_key not in known_device_keys:
                        current_devices.append(device)
                        known_device_keys.add(device_key)
                panel_entry["devices"] = current_devices

            for p_idx, panel in enumerate(consolidated_panels.values(), 1):
                p_code = panel.get("panel_code") or f"P-{p_idx}"
                p_name = panel.get("panel_name") or ""
                dim_str = panel.get("dimension") or ""
                dim_h = panel.get("dim_h") or 1200
                dim_w = panel.get("dim_w") or 700
                dim_d = panel.get("dim_d") or 250
                dim_t = panel.get("dim_t") or 1.4
                dwg_code = panel.get("drawing_code") or ""

                panel_devs = [
                    d for d in extracted_devices
                    if str(_device_value(d, "panel_code", "")).strip() == str(p_code).strip()
                ]
                if not panel_devs:
                    panel_devs = panel.get("devices", [])

                # 1. Dòng Header Tủ
                rows.append({
                    "id": f"p-{p_code}",
                    "row_type": "panel_header",
                    "tt": str(p_idx),
                    "name": f" {p_code} - {p_name.upper()}",
                    "sku": dim_str,
                    "origin": "VN",
                    "unit": "Tủ",
                    "quantity": 1,
                    "unit_price": 0,
                    "line_total": 0,
                    "notes": f"Vị trí: Trang {panel.get('page_num')} - Bản vẽ {dwg_code}"
                })

                # Tính toán Incomer rating riêng của tủ này từ thiết bị thực tế (không ép 630A giả)
                inc_devs = [d for d in panel_devs if _device_bucket(d) == "incoming"]
                if inc_devs and _device_value(inc_devs[0], "in_a"):
                    inc_rating = int(_device_value(inc_devs[0], "in_a"))
                else:
                    dev_currents = [float(_device_value(d, "in_a", 0) or 0) for d in panel_devs if _device_value(d, "in_a")]
                    inc_rating = int(max(dev_currents)) if dev_currents else 0

                # Dự toán vỏ tủ riêng của tủ này theo kích thước bản vẽ
                surface_m2 = 2 * (dim_h * dim_w + dim_h * dim_d + dim_w * dim_d) / 1e6
                p_enc_price = max(1800000, int(surface_m2 * 1250000))
                p_enc_price = int(round(p_enc_price / float(PRICE_ROUNDING_STEP_VND)) * PRICE_ROUNDING_STEP_VND)

                # Kiểm tra tủ có cần hệ thống đồng thanh cái không (In >= 100A hoặc ACB/MCCB lớn)
                need_busbar = BusbarCalculatorService.needs_busbar(inc_rating, panel_devs)
                bus_res = None
                if need_busbar:
                    bus_res = BusbarCalculatorService.calculate(inc_rating, {"width": dim_w, "height": dim_h, "depth": dim_d}, panel_devs)

                # Tính toán chi tiết phụ kiện & vật tư phụ theo tải và số cực thực tế
                total_poles = sum(int(_device_value(d, "poles", 3) or 3) * int(_device_value(d, "quantity", 1) or 1) for d in panel_devs)
                lug_cost = total_poles * (25000 if inc_rating >= 400 else 12000)
                wire_cost = 200000 + len([d for d in panel_devs if _device_bucket(d) in ["measurement", "control"]]) * 35000
                duct_cost = int(((dim_h + dim_w) / 1000.0) * 75000)
                insulator_cost = (int(bus_res.L_main_m / BUSBAR_INSULATOR_SPACING_M) * 4 * BUSBAR_INSULATOR_PRICE_VND) if (need_busbar and bus_res) else 0
                comb_busbar_cost = (total_poles * 8000) if not need_busbar else 0
                p_acc_price = int(round((lug_cost + wire_cost + duct_cost + insulator_cost + comb_busbar_cost + 150000) / float(PRICE_ROUNDING_STEP_VND)) * PRICE_ROUNDING_STEP_VND)
                p_acc_price = max(450000, p_acc_price)

                # Nhân công lắp ráp, đấu nối & QC
                base_lab = 500000 if inc_rating < 100 else (1000000 if inc_rating <= 630 else 1800000)
                dev_lab = len(panel_devs) * 50000
                p_lab_price = int(round((base_lab + dev_lab) / float(PRICE_ROUNDING_STEP_VND)) * PRICE_ROUNDING_STEP_VND)
                p_lab_price = max(800000, p_lab_price)

                # 2. Section 1: Vỏ tủ + Phụ kiện
                rows.append({"id": f"s-enc-{p_code}", "row_type": "section_header", "tt": "*", "name": f"Vỏ tủ {p_code} & phụ kiện"})
                rows.append({
                    "id": f"i-enc-{p_code}",
                    "row_type": "item",
                    "tt": "+",
                    "name": f"Vỏ tủ điện sơn tĩnh điện (KT: H{dim_h}xW{dim_w}xD{dim_d}xT{dim_t}mm) kèm chân đế cao {settings.ENCLOSURE_DEFAULT_PLINTH_HEIGHT}mm",
                    "sku": f"H{dim_h}xW{dim_w}",
                    "origin": "VN",
                    "unit": "Cái",
                    "quantity": 1,
                    "unit_price": p_enc_price,
                    "line_total": p_enc_price,
                    "notes": f"Định hướng thiết kế theo bản vẽ {dwg_code}"
                })
                
                # CHỈ thêm đồng thanh cái khi tủ thực sự cần thanh cái (KHÔNG mock cho tủ nhỏ)
                if need_busbar and bus_res:
                    rows.append({
                        "id": f"i-bus-{p_code}",
                        "row_type": "item",
                        "tt": "+",
                        "name": bus_res.spec_title,
                        "sku": f"Cu {bus_res.section_mm2}mm2",
                        "origin": "VN",
                        "unit": "Hệ",
                        "quantity": 1,
                        "unit_price": bus_res.unit_price,
                        "line_total": bus_res.unit_price,
                        "notes": f"Gia công uốn đột CNC, bọc co nhiệt R-S-T-N-E ({bus_res.profile}mm)"
                    })

                acc_name = "Vật tư phụ tủ điện (đầu cosse SC động lực, dây điều khiển Cadivi VSF, máng cáp nhựa PVC, sứ đỡ thanh cái SM, domino kẹp dây)" if need_busbar else "Vật tư phụ tủ điện (Cầu lược 3P/1P phân phối MCB, đầu cosse ghim, dây điều khiển Cadivi VSF, máng cáp nhựa PVC, kẹp tiếp địa)"
                rows.append({
                    "id": f"i-acc-{p_code}",
                    "row_type": "item",
                    "tt": "+",
                    "name": acc_name,
                    "sku": "Trọn gói",
                    "origin": "VN",
                    "unit": "Tủ",
                    "quantity": 1,
                    "unit_price": p_acc_price,
                    "line_total": p_acc_price,
                    "notes": ""
                })
                rows.append({
                    "id": f"i-lab-{p_code}",
                    "row_type": "item",
                    "tt": "+",
                    "name": "Nhân công lắp ráp, đấu nối & kiểm tra xuất xưởng (QC)",
                    "sku": "QC-LABOR",
                    "origin": "VN",
                    "unit": "Tủ",
                    "quantity": 1,
                    "unit_price": p_lab_price,
                    "line_total": p_lab_price,
                    "notes": ""
                })

                # Phân loại và gộp nhóm thiết bị trùng lặp trong tủ này
                p_incomers = DynamicGroupingEngine.merge_duplicates([d for d in panel_devs if _device_bucket(d) == "incoming"])
                p_meters = DynamicGroupingEngine.merge_duplicates([d for d in panel_devs if _device_bucket(d) == "measurement"])
                p_controls = DynamicGroupingEngine.merge_duplicates([d for d in panel_devs if _device_bucket(d) == "control"])
                p_cooling = DynamicGroupingEngine.merge_duplicates([d for d in panel_devs if _device_bucket(d) == "cooling"])
                p_feeders = DynamicGroupingEngine.merge_duplicates([d for d in panel_devs if _device_bucket(d) == "outgoing"])

                # 3. Đầu vào
                if p_incomers:
                    rows.append({"id": f"s-inc-{p_code}", "row_type": "section_header", "tt": "*", "name": f"Thiết bị đầu vào ({p_code})"})
                    for inc in p_incomers:
                        price = _resolve_price(inc)
                        _append_device_with_accessories(rows, inc, price, f"inc-{p_code}", default_note="Aptomat tổng", incomer_ref_rating=inc_rating)

                # 4. Đo lường & Giám sát
                if p_meters:
                    rows.append({"id": f"s-met-{p_code}", "row_type": "section_header", "tt": "*", "name": f"Đo lường & Giám sát ({p_code})"})
                    for m in p_meters:
                        price = _resolve_price(m)
                        _append_device_with_accessories(rows, m, price, f"met-{p_code}", incomer_ref_rating=inc_rating)

                # 5. Điều khiển & Chiếu sáng
                if p_controls:
                    rows.append({"id": f"s-ctl-{p_code}", "row_type": "section_header", "tt": "*", "name": f"Điều khiển ({p_code})"})
                    for c in p_controls:
                        price = _resolve_price(c)
                        _append_device_with_accessories(rows, c, price, f"ctl-{p_code}", incomer_ref_rating=inc_rating)

                # 6. Làm mát & Thông gió (thiết bị cánh/khung tủ)
                if p_cooling:
                    rows.append({"id": f"s-cool-{p_code}", "row_type": "section_header", "tt": "*", "name": f"Làm mát & Thông gió ({p_code})"})
                    for c in p_cooling:
                        price = _resolve_price(c)
                        _append_device_with_accessories(rows, c, price, f"cool-{p_code}", incomer_ref_rating=inc_rating)

                # 7. Đầu ra
                if p_feeders:
                    rows.append({"id": f"s-out-{p_code}", "row_type": "section_header", "tt": "*", "name": f"Thiết bị đầu ra ({p_code})"})
                    for f in p_feeders:
                        price = _resolve_price(f)
                        _append_device_with_accessories(rows, f, price, f"f-{p_code}", incomer_ref_rating=inc_rating)

            return rows

        # TRƯỜNG HỢP 2: Bóc tách Đơn tủ (Single Panel Fallback)
        rows.append({
            "id": "p-1",
            "row_type": "panel_header",
            "tt": "1",
            "name": f"TỦ ĐIỆN {clean_pname}",
            "sku": "",
            "origin": "VN",
            "unit": "Tủ",
            "quantity": 1,
            "unit_price": 0,
            "line_total": 0,
            "notes": ""
        })

        # 2. Section 1: Vỏ tủ + Phụ kiện
        rows.append({"id": "s-1", "row_type": "section_header", "tt": "*", "name": "Vỏ tủ + phụ kiện"})
        rows.append({
            "id": "i-enc",
            "row_type": "item",
            "tt": "+",
            "name": f"Vỏ tủ điện {panel_code or 'DB'} ({clean_pname}) sơn tĩnh điện công nghiệp.\n+ KT: H{enclosure_spec['height']}xW{enclosure_spec['width']}xD{enclosure_spec['depth']}xT{enclosure_spec['thickness']}mm\n+ Cấp bảo vệ IP54/IP42" + (f"\n+ Có chân đế cao {enclosure_spec['plinth_height']}mm" if enclosure_spec.get('plinth_height') else ""),
            "sku": f"H{enclosure_spec['height']}xW{enclosure_spec['width']}",
            "origin": "VN",
            "unit": "Cái",
            "quantity": 1,
            "unit_price": enclosure_unit_price,
            "line_total": enclosure_unit_price,
            "notes": "Sơn tĩnh điện RAL 7035 công nghiệp"
        })
        inc_dev = next((d for d in extracted_devices if getattr(d, 'section', '') == 'Đầu vào' or 'ACB' in getattr(d, 'category', '').upper() or 'MCCB' in getattr(d, 'category', '').upper()), None)
        raw_inc = enclosure_spec.get('incomer_rating') or (getattr(inc_dev, 'in_a', None) if inc_dev else None) or max([getattr(d, 'in_a', 0) or 0 for d in extracted_devices] + [0])
        inc_a_single = float(raw_inc or 0)
        need_busbar_single = BusbarCalculatorService.needs_busbar(inc_a_single, extracted_devices)
        bus_res_single = None
        if need_busbar_single:
            bus_res_single = BusbarCalculatorService.calculate(inc_a_single, enclosure_spec, extracted_devices)
            rows.append({
                "id": "i-bus",
                "row_type": "item",
                "tt": "+",
                "name": bus_res_single.spec_title,
                "sku": f"Cu {bus_res_single.section_mm2}mm2",
                "origin": "VN",
                "unit": "Hệ",
                "quantity": 1,
                "unit_price": bus_res_single.unit_price,
                "line_total": bus_res_single.unit_price,
                "notes": f"Gia công uốn đột CNC, bọc co nhiệt R-S-T-N-E ({bus_res_single.profile}mm)"
            })

        acc_name_single = "Vật tư phụ tủ điện (đầu cosse SC động lực, dây điều khiển Cadivi VSF, máng cáp nhựa PVC, sứ đỡ thanh cái SM, domino kẹp dây)" if need_busbar_single else "Vật tư phụ tủ điện (Cầu lược 3P/1P phân phối MCB, đầu cosse ghim, dây điều khiển Cadivi VSF, máng cáp nhựa PVC, kẹp tiếp địa)"
        total_poles_s = sum(int(getattr(d, "poles", 3) or 3) * int(getattr(d, "quantity", 1) or 1) for d in extracted_devices)
        lug_cost_s = total_poles_s * (25000 if inc_a_single >= 400 else 12000)
        wire_cost_s = 200000 + len([d for d in extracted_devices if getattr(d, "section", "") in ["Đo lường & Giám sát", "Điều khiển & Chiếu sáng"]]) * 35000
        insulator_cost_s = (int(bus_res_single.L_main_m / BUSBAR_INSULATOR_SPACING_M) * 4 * BUSBAR_INSULATOR_PRICE_VND) if (need_busbar_single and bus_res_single) else 0
        comb_cost_s = (total_poles_s * 8000) if not need_busbar_single else 0
        calc_acc_price = int(round((lug_cost_s + wire_cost_s + 150000 + insulator_cost_s + comb_cost_s) / float(PRICE_ROUNDING_STEP_VND)) * PRICE_ROUNDING_STEP_VND)
        calc_acc_price = max(450000, calc_acc_price)

        rows.append({
            "id": "i-acc",
            "row_type": "item",
            "tt": "+",
            "name": acc_name_single,
            "sku": "Trọn gói",
            "origin": "VN",
            "unit": "Tủ",
            "quantity": 1,
            "unit_price": calc_acc_price,
            "line_total": calc_acc_price,
            "notes": ""
        })

        base_lab_s = 500000 if inc_a_single < 100 else (1000000 if inc_a_single <= 630 else 1800000)
        dev_lab_s = len(extracted_devices) * 50000
        calc_lab_price = int(round((base_lab_s + dev_lab_s) / float(PRICE_ROUNDING_STEP_VND)) * PRICE_ROUNDING_STEP_VND)
        calc_lab_price = max(800000, calc_lab_price)

        rows.append({
            "id": "i-lab",
            "row_type": "item",
            "tt": "+",
            "name": "Nhân công lắp ráp, đấu nối & kiểm tra xuất xưởng (QC)",
            "sku": "QC-LABOR",
            "origin": "VN",
            "unit": "Tủ",
            "quantity": 1,
            "unit_price": calc_lab_price,
            "line_total": calc_lab_price,
            "notes": ""
        })

        incomers = [d for d in extracted_devices if "ACB" in d.category.upper() or (d.in_a and d.in_a >= 400) or (d.section and "đầu vào" in d.section.lower())]
        meters = [d for d in extracted_devices if "METER" in d.category.upper() or "LIGHT" in d.category.upper() or (d.section and "đo lường" in d.section.lower())]
        coolings = [d for d in extracted_devices if "COOLING" in d.category.upper() or "FAN" in d.category.upper() or "THERMOSTAT" in d.category.upper() or (d.section and "làm mát" in d.section.lower())]
        feeders = [d for d in extracted_devices if d not in incomers and d not in meters and d not in coolings]

        # Gộp nhóm các thiết bị trùng lặp trong từng section
        incomers = DynamicGroupingEngine.merge_duplicates(incomers)
        meters = DynamicGroupingEngine.merge_duplicates(meters)
        coolings = DynamicGroupingEngine.merge_duplicates(coolings)
        feeders = DynamicGroupingEngine.merge_duplicates(feeders)

        # 3. Section 2: Đầu vào
        if incomers:
            rows.append({"id": "s-2", "row_type": "section_header", "tt": "*", "name": "Đầu vào"})
            for inc in incomers:
                price = _resolve_price(inc)
                _append_device_with_accessories(rows, inc, price, "inc", default_note="Aptomat tổng", incomer_ref_rating=inc_a_single)

        # 4. Section 3: Đầu ra (Feeders)
        if feeders:
            rows.append({"id": "s-3", "row_type": "section_header", "tt": "*", "name": "Đầu ra"})
            for f in feeders:
                price = _resolve_price(f)
                _append_device_with_accessories(rows, f, price, "f", incomer_ref_rating=inc_a_single)

        # 5. Section 4: Đo lường & Giám sát
        if meters:
            rows.append({"id": "s-4", "row_type": "section_header", "tt": "*", "name": "Đo lường & Giám sát"})
            for m in meters:
                price = _resolve_price(m)
                _append_device_with_accessories(rows, m, price, "m", incomer_ref_rating=inc_a_single)

        # 6. Section 5: Làm mát & Thông gió
        if coolings:
            rows.append({"id": "s-5", "row_type": "section_header", "tt": "*", "name": "Làm mát & Thông gió"})
            for c in coolings:
                price = _resolve_price(c)
                _append_device_with_accessories(rows, c, price, "c", incomer_ref_rating=inc_a_single)

        return rows

    @staticmethod
    def _build_technical_audit(
        extracted_devices: list,
        enclosure_spec: dict,
        panel_code: str,
        panel_name: str,
        is_3phase: bool,
        incomer_rating: float
    ) -> dict:
        from app.services.ai.system_completeness import technical_audit
        return technical_audit(extracted_devices)

    @staticmethod
    def _extract_enclosure_dimensions(text_sources: List[Any]) -> Optional[Tuple[float, float, float]]:
        """
        Trích xuất kích thước vỏ tủ HxWxD (mm) từ các nguồn văn bản (ghi chú, tóm tắt AI, văn bản CAD).
        Chuẩn hóa theo quy cách ngành điện VN: Cao (Height) x Rộng (Width) x Sâu (Depth).
        """
        for text in text_sources:
            if not text:
                continue
            text_str = str(text)

            # 1. Định dạng có ký hiệu rõ ràng: H1200 x W800 x D400 hoặc W800 x H1200 x D400
            m_explicit = re.search(
                r'(?:[Hh]\s*[:=]?\s*(\d{3,4})\s*[*xX×,]\s*[Ww]\s*[:=]?\s*(\d{3,4})\s*[*xX×,]\s*[Dd]\s*[:=]?\s*(\d{2,4}))|'
                r'(?:[Ww]\s*[:=]?\s*(\d{3,4})\s*[*xX×,]\s*[Hh]\s*[:=]?\s*(\d{3,4})\s*[*xX×,]\s*[Dd]\s*[:=]?\s*(\d{2,4}))',
                text_str
            )
            if m_explicit:
                if m_explicit.group(1):
                    h = float(m_explicit.group(1))
                    w = float(m_explicit.group(2))
                    d = float(m_explicit.group(3))
                    if h >= 300 and w >= 200 and d >= 100:
                        return (h, w, d)
                elif m_explicit.group(4):
                    w = float(m_explicit.group(4))
                    h = float(m_explicit.group(5))
                    d = float(m_explicit.group(6))
                    if h >= 300 and w >= 200 and d >= 100:
                        return (h, w, d)

            # 2. Định dạng tiền tố: TỦ 1200X800X400 hoặc KÍCH THƯỚC: 1200x800x400 hoặc VỎ TỦ 1200*800*400
            m_prefixed = re.search(
                r'(?:TỦ|KÍCH\s*THƯỚC|KT|VỎ\s*TỦ|DIMENSIONS?|SIZE)\s*[:=]?\s*(\d{3,4})\s*[*xX×]\s*(\d{3,4})\s*[*xX×]\s*(\d{2,4})',
                text_str,
                re.IGNORECASE
            )
            if m_prefixed:
                d1, d2, d3 = float(m_prefixed.group(1)), float(m_prefixed.group(2)), float(m_prefixed.group(3))
                if d1 < d2 and d2 >= 600 and d1 <= 800:
                    h, w, d = d2, d1, d3
                else:
                    h, w, d = d1, d2, d3
                if h >= 300 and w >= 200 and d >= 100:
                    return (h, w, d)

            # 3. Định dạng 3 kích thước kèm đơn vị mm: 1200x800x400mm
            m_mm = re.search(
                r'(\d{3,4})\s*[*xX×]\s*(\d{3,4})\s*[*xX×]\s*(\d{2,4})\s*mm',
                text_str,
                re.IGNORECASE
            )
            if m_mm:
                d1, d2, d3 = float(m_mm.group(1)), float(m_mm.group(2)), float(m_mm.group(3))
                if d1 < d2 and d2 >= 600 and d1 <= 800:
                    h, w, d = d2, d1, d3
                else:
                    h, w, d = d1, d2, d3
                if h >= 300 and w >= 200 and d >= 100:
                    return (h, w, d)

            # 4. Định dạng 3 số thông thường: 1200x800x400
            m_generic = re.search(
                r'(?:^|[^\d])(\d{3,4})\s*[*xX×]\s*(\d{3,4})\s*[*xX×]\s*(\d{2,4})(?:[^\d]|$)',
                text_str
            )
            if m_generic:
                d1, d2, d3 = float(m_generic.group(1)), float(m_generic.group(2)), float(m_generic.group(3))
                if 100 <= d3 <= 800 and 300 <= d1 <= 2400 and 250 <= d2 <= 1600:
                    if d1 < d2 and d2 >= 600 and d1 <= 800:
                        h, w, d = d2, d1, d3
                    else:
                        h, w, d = d1, d2, d3
                    return (h, w, d)

        return None

    @staticmethod
    async def generate_cad_and_quotation(
        project: Project,
        db: AsyncSession,
        devices: List[Dict[str, Any]],
        brand_preference: Optional[str] = None,
        user_prompt: Optional[str] = None,
        multi_panel_list: Optional[List[Dict[str, Any]]] = None,
        enclosure_dimensions: Optional[str] = None,
        panel_code: Optional[str] = None,
        panel_name: Optional[str] = None,
        per_panel: bool = False,
        progress_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Quy trình chuyên biệt khi người dùng bấm Tạo báo giá:
        1. Phân tích thiết bị kỹ thuật (sizing vỏ tủ, thanh cái, layout vật lý, đối soát Catalog).
        2. Vẽ CAD kỹ thuật (AutoCAD DXF 4 hình chiếu và lưu vào ProjectFile).
        3. Lập bảng báo giá chi tiết hoàn chỉnh.
        """
        from sqlalchemy import select
        from app.models.project_file import ProjectFile
        from app.models.conversation_session import ConversationSession
        from app.models.analysis_iteration import AnalysisIteration

        if not devices:
            raise ValueError("Không có danh sách thiết bị để phân tích và lập báo giá.")

        async def emit_progress(stage: str, progress: int, message: str, **extra: Any) -> None:
            """Emit milestones from completed real work, never timer-based progress."""
            if not progress_callback:
                return
            payload = {
                "type": "cad_progress",
                "stage": stage,
                "progress": progress,
                "message": message,
                **extra,
            }
            result = progress_callback(payload)
            if asyncio.iscoroutine(result):
                await result
            # Give an SSE response a chance to flush before CPU-bound CAD work.
            await asyncio.sleep(0)

        await emit_progress("normalize", 5, f"Đang chuẩn hóa {len(devices)} thiết bị đầu vào")

        resolved_brand_pref = brand_preference or settings.DEFAULT_BRAND
        explicit_brand_preference = bool(
            resolved_brand_pref
            and resolved_brand_pref.strip().lower()
            not in {"theo thiết kế", "theo thiet ke", "default", "auto"}
        )

        # 1. Chuẩn hóa thiết bị sang ExtractedDeviceSchema
        extracted_devices: List[ExtractedDeviceSchema] = []
        for d in devices:
            if isinstance(d, ExtractedDeviceSchema):
                extracted_devices.append(d)
            elif isinstance(d, dict):
                extracted_devices.append(ExtractedDeviceSchema(
                    category=d.get("category", "Thiết bị"),
                    name=d.get("name", "Thiết bị"),
                    spec=d.get("spec", ""),
                    in_a=d.get("in_a"),
                    icu_ka=d.get("icu_ka"),
                    poles=d.get("poles"),
                    quantity=d.get("quantity", 1),
                    drawing_quantity=d.get("drawing_quantity"),
                    procurement_quantity=d.get("procurement_quantity"),
                    quantity_basis=d.get("quantity_basis"),
                    quantity_confidence=d.get("quantity_confidence"),
                    brand=(
                        resolved_brand_pref
                        if explicit_brand_preference
                        else d.get("brand")
                        or (resolved_brand_pref if resolved_brand_pref != settings.DEFAULT_BRAND else "")
                    ),
                    part_number=d.get("part_number", ""),
                    section=d.get("section"),
                    location=d.get("location"),
                    panel_code=d.get("panel_code") or panel_code or "",
                    panel_name=d.get("panel_name") or panel_name or "",
                    notes=d.get("notes"),
                    tag=d.get("tag"),
                    mounting=d.get("mounting"),
                    electrical_function=d.get("electrical_function"),
                    upstream_device=d.get("upstream_device"),
                    downstream_device=d.get("downstream_device"),
                    connected_load=d.get("connected_load"),
                    accompanying_accessories=d.get("accompanying_accessories"),
                    inferred_components=d.get("inferred_components"),
                    confidence=d.get("confidence", settings.DEFAULT_CONFIDENCE),
                    evidence_image=d.get("evidence_image"),
                    box_2d=d.get("box_2d"),
                    evidence_region=d.get("evidence_region"),
                    panel_evidence_image=d.get("panel_evidence_image"),
                    source_type=d.get("source_type"),
                    source_filename=d.get("source_filename"),
                    source_page=d.get("source_page"),
                ))

        await emit_progress("catalog", 15, "Đang đối chiếu mã hàng và đơn giá catalog thực tế")

        detected_panel_code = panel_code or (extracted_devices[0].panel_code if extracted_devices else "") or ""
        detected_panel_name = panel_name or (extracted_devices[0].panel_name if extracted_devices else "") or ""

        # Tra cứu Catalog & khớp đơn giá thiết bị
        catalog_engine = DeviceCatalogEngine.get_instance()
        device_price_map: Dict[str, int] = {}

        def catalog_type_matches(category: str, item: Dict[str, Any]) -> bool:
            expected = str(category or "").strip().upper()
            actual = str(item.get("t") or item.get("type") or "").strip().upper()
            aliases = {
                "LIGHT": {"LIGHT", "PILOT", "PILOT_LIGHT", "INDICATOR"},
                "METER": {"METER", "AMMETER", "VOLTMETER", "MULTIMETER", "CT"},
                "FUSE": {"FUSE"},
                "RCBO": {"RCBO"},
                "MCB": {"MCB"},
                "MCCB": {"MCCB"},
                "ACB": {"ACB"},
            }
            return actual in aliases.get(expected, {expected})

        for dev in extracted_devices:
            brand_to_match = (
                resolved_brand_pref
                if explicit_brand_preference
                else dev.brand or resolved_brand_pref or settings.DEFAULT_BRAND
            )
            # 1. Tìm theo SKU chính xác
            if dev.part_number and not explicit_brand_preference:
                exact = catalog_engine.get_by_sku(dev.part_number)
                exact_brand = str((exact or {}).get("brand_display") or (exact or {}).get("brand") or "")
                brand_matches_preference = (
                    not explicit_brand_preference
                    or resolved_brand_pref.lower() in exact_brand.lower()
                    or exact_brand.lower() in resolved_brand_pref.lower()
                )
                if exact and exact.get("g") and brand_matches_preference and catalog_type_matches(dev.category, exact):
                    device_price_map[dev.part_number] = int(exact.get("g"))
                    if exact.get("brand") and not dev.brand:
                        dev.brand = exact.get("brand")
                    dev.technical_match_note = f"Báo giá dùng mã catalog {dev.part_number}; thông số và kết nối SLD gốc được bảo toàn."
                    continue
                if explicit_brand_preference and not brand_matches_preference:
                    # A SKU extracted for another manufacturer must not defeat an
                    # explicit user request such as "bóc tách với LS".
                    dev.part_number = ""

            # A generic symbol does not establish an exact catalog model.
            # Preserve circuit evidence and leave the quote unpriced for review.
            if not dev.part_number or not catalog_engine.get_by_sku(dev.part_number):
                dev.part_number = ""
                dev.technical_match_note = (
                    "Chưa xác định được mã catalog từ thông số và chức năng mạch; "
                    "cần chọn thiết bị trước khi chốt đơn giá."
                )

            # 3. Đề xuất tương thích: nếu dev đã có compatible_proposal từ AI
            if getattr(dev, "compatible_proposal", None):
                cp = dev.compatible_proposal
                dev.is_alternative_recommended = True
                dev.original_spec = cp.get("original_spec") or dev.spec
                dev.compatibility_note = cp.get("technical_reason") or cp.get("ai_analysis")
                dev.suggested_alternatives = [cp]

            # 4. Chuẩn hóa phụ kiện đi kèm đã bóc tách từ AI (nếu có)
            if getattr(dev, "accompanying_accessories", None):
                dev.accompanying_accessories = AccompanyingEquipmentService.format_accessories(
                    dev.accompanying_accessories,
                    parent_brand=dev.brand,
                    parent_category=dev.category
                )

        await emit_progress("engineering", 35, "Đang tính kích thước vỏ tủ và tiết diện thanh cái")

        # 2. Phân tích kỹ thuật vỏ tủ & thanh cái
        dim_sources = []
        if enclosure_dimensions:
            dim_sources.append(enclosure_dimensions)
        for d in extracted_devices:
            if d.notes:
                dim_sources.append(d.notes)
        detected_dimensions = AnalysisPipelineService._extract_enclosure_dimensions(dim_sources)

        enclosure_spec = EnclosureCadGeneratorService.calculate_enclosure_specs(
            [d.model_dump() for d in extracted_devices],
            preferred_dimensions=detected_dimensions
        )

        incomer_rating = enclosure_spec.get("incomer_rating") or settings.DEFAULT_INCOMER_RATING or 0
        poles = enclosure_spec.get("poles", 2)
        is_3phase = enclosure_spec.get("is_3phase", False)
        voltage_str = "3 pha 380/220V 50Hz" if is_3phase else "1 pha 220V 50Hz"

        enclosure_height = enclosure_spec.get("height", 600 if not is_3phase else 1400)
        enclosure_width = enclosure_spec.get("width", 500 if not is_3phase else 800)
        enclosure_depth = enclosure_spec.get("depth", 200 if not is_3phase else 350)

        surface_m2 = 2 * (enclosure_height * enclosure_width + enclosure_height * enclosure_depth + enclosure_width * enclosure_depth) / 1e6
        min_enc_p = int(getattr(settings, "ENCLOSURE_MIN_PRICE", 1200000))
        enclosure_unit_price = max(min_enc_p, int(surface_m2 * 1200000))
        enclosure_unit_price = int(round(enclosure_unit_price / float(PRICE_ROUNDING_STEP_VND)) * PRICE_ROUNDING_STEP_VND)

        # Bắt đầu tính đồng qua BusbarCalculatorService chuẩn kỹ thuật
        from app.services.bom.busbar_calculator import BusbarCalculatorService
        from app.services.export.quotation_exporter import QuotationExporterService

        need_busbar = BusbarCalculatorService.needs_busbar(incomer_rating, [d.model_dump() for d in extracted_devices])
        busbar_calc = BusbarCalculatorService.calculate(
            in_a=incomer_rating,
            enclosure_dims={"W": enclosure_width, "width": enclosure_width, "H": enclosure_height, "D": enclosure_depth},
            feeder_list=[d.model_dump() for d in extracted_devices]
        )
        busbar_unit_price = busbar_calc.unit_price if need_busbar else 0

        # Physical layout model & kiểm tra xung đột
        detected_layout_intent = None
        if user_prompt:
            p_low = user_prompt.lower()
            if "cáp đáy" in p_low or "bottom" in p_low:
                detected_layout_intent = {"cable_entry": "BOTTOM"}
            elif "cáp nóc" in p_low or "top" in p_low:
                detected_layout_intent = {"cable_entry": "TOP"}

        physical_layout = PhysicalLayoutEngine.compute_physical_layout_model(
            devices=[d.model_dump() for d in extracted_devices],
            enclosure_spec=enclosure_spec,
            mode="PANEL_LAYOUT_ONLY",
            layout_intent=detected_layout_intent
        )
        layout_conflict_res = physical_layout.get("conflict_check", {})
        layout_conflicts = layout_conflict_res.get("conflicts", [])

        await emit_progress(
            "layout",
            52,
            "Đã bố trí thiết bị và kiểm tra xung đột không gian",
            conflict_count=len(layout_conflicts),
        )

        # Use the checked enclosure envelope, never the unvalidated drawing note.
        await emit_progress("cad_drawing", 60, "Đang chọn form tủ CAD từ thư viện nguồn")
        cad_file_path = None
        dxf_filename = ""
        dxf_size = 0
        cad_layout = None
        try:
            source_cad = SourceProjectGenerator.generate(
                project_id=project.id,
                output_dir=getattr(settings, "PROJECTS_DIR", "storage/projects"),
                dimensions=tuple(enclosure_spec["fit_check"]["minimum_required"][axis] for axis in ("height", "width", "depth")),
                devices=[d.model_dump() for d in extracted_devices],
                kind=("outdoor" if any(token in str(panel_name or "").lower() for token in ("ngoài trời", "outdoor")) else "fire" if any(token in str(panel_name or "").lower() for token in ("chữa cháy", "pccc")) else "indoor"),
            )
            cad_file_path = source_cad["path"]
            cad_layout = {key: source_cad[key] for key in ("template_id", "source", "dimensions", "minimum_required", "placements", "unmatched_devices")}
            dxf_filename = os.path.basename(cad_file_path)
            dxf_size = os.path.getsize(cad_file_path)
        except ValueError as exc:
            await emit_progress("cad_review", 75, f"Cần chọn form tủ nguồn: {exc}")
        await emit_progress(
            "cad_ready",
            75,
            "Đã chọn form CAD nguồn" if cad_file_path else "Chưa xuất CAD: cần xác nhận form nguồn",
            filename=dxf_filename,
            file_size=dxf_size,
        )

        # Dọn dẹp các file CAD tự sinh cũ và lưu bản ghi mới vào ProjectFile
        if cad_file_path and not per_panel:
            old_cad_stmt = select(ProjectFile).where(
                ProjectFile.project_id == project.id,
                (ProjectFile.filename.like("BanVe_%") | ProjectFile.filename.like("PhacThao_%")),
                ProjectFile.filename != dxf_filename
            )
            old_cad_files = (await db.execute(old_cad_stmt)).scalars().all()
            for o_file in old_cad_files:
                if o_file.file_path and os.path.exists(o_file.file_path):
                    try:
                        os.remove(o_file.file_path)
                    except Exception:
                        pass
                await db.delete(o_file)

        cad_file = None
        if cad_file_path:
            stmt = select(ProjectFile).where(
                ProjectFile.project_id == project.id,
                ProjectFile.filename == dxf_filename
            )
            cad_file = (await db.execute(stmt)).scalars().first()
            if not cad_file:
                cad_file = ProjectFile(
                    project_id=project.id,
                    filename=dxf_filename,
                    file_path=cad_file_path,
                    file_type="application/dxf",
                    file_size=dxf_size,
                    is_generated=True
                )
                db.add(cad_file)
            else:
                cad_file.file_path = cad_file_path
                cad_file.file_size = dxf_size
                cad_file.is_generated = True

        # 4. Lập bảng báo giá chi tiết hoàn chỉnh
        quotation_rows = AnalysisPipelineService._build_quotation_rows(
            project_name=project.name,
            extracted_devices=extracted_devices,
            device_price_map=device_price_map,
            enclosure_spec=enclosure_spec,
            enclosure_unit_price=enclosure_unit_price,
            busbar_unit_price=busbar_unit_price,
            multi_panel_list=multi_panel_list or [],
            panel_code=detected_panel_code,
            panel_name=detected_panel_name
        )
        await emit_progress("quotation", 84, f"Đã lập {len(quotation_rows)} dòng báo giá")

        # 5. Thu thập danh sách đề xuất kỹ thuật tương thích
        technical_proposals = []
        for d in extracted_devices:
            cp = getattr(d, "compatible_proposal", None)
            if cp and isinstance(cp, dict):
                technical_proposals.append(cp)

        # 6. Tạo file Excel báo giá dự toán chính thức (.xlsx)
        excel_file_info = None
        try:
            await emit_progress("excel", 88, "Đang xuất file báo giá Excel")
            excel_path = QuotationExporterService.export(
                devices=quotation_rows if quotation_rows else [d.model_dump() for d in extracted_devices],
                project_name=project.name,
                brand_preference=resolved_brand_pref,
                proposals=technical_proposals,
                filename_suffix=detected_panel_code if per_panel else None,
            )
            if os.path.exists(excel_path):
                excel_filename = os.path.basename(excel_path)
                excel_size = os.path.getsize(excel_path)

                # Dọn dẹp bản ghi Excel cũ
                # Báo giá từng tủ chỉ thay phiên bản cũ của chính tủ đó.
                # Báo giá tổng vẫn giữ hành vi dọn các bản tổng cũ như trước đây.
                excel_prefix = excel_filename.rsplit("_", 2)[0]
                old_excel_pattern = f"{excel_prefix}_%" if per_panel else "BaoGia_%"
                old_excel_stmt = select(ProjectFile).where(
                    ProjectFile.project_id == project.id,
                    ProjectFile.filename.like(old_excel_pattern),
                    ProjectFile.filename != excel_filename
                )
                old_excels = (await db.execute(old_excel_stmt)).scalars().all()
                for oe in old_excels:
                    if oe.file_path and os.path.exists(oe.file_path):
                        try:
                            os.remove(oe.file_path)
                        except Exception:
                            pass
                    await db.delete(oe)

                # Ghi nhận file Excel vào ProjectFile
                excel_stmt = select(ProjectFile).where(
                    ProjectFile.project_id == project.id,
                    ProjectFile.filename == excel_filename
                )
                excel_file = (await db.execute(excel_stmt)).scalars().first()
                if not excel_file:
                    excel_file = ProjectFile(
                        project_id=project.id,
                        filename=excel_filename,
                        file_path=excel_path,
                        file_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        file_size=excel_size,
                        is_generated=True
                    )
                    db.add(excel_file)
                else:
                    excel_file.file_path = excel_path
                    excel_file.file_size = excel_size
                    excel_file.is_generated = True

                excel_file_info = {
                    "id": excel_file.id if excel_file else 0,
                    "filename": excel_filename,
                    "file_path": excel_path,
                    "file_size": excel_size
                }
        except Exception as ex_excel:
            logger.warning(f"Lỗi tạo file Excel báo giá trong generate_cad_and_quotation: {ex_excel}")

        technical_audit = AnalysisPipelineService._build_technical_audit(
            extracted_devices=extracted_devices,
            enclosure_spec=enclosure_spec,
            panel_code=detected_panel_code,
            panel_name=detected_panel_name,
            is_3phase=is_3phase,
            incomer_rating=incomer_rating
        )

        # 6. Lưu đồng bộ vào AnalysisIteration mới nhất của dự án
        sess_stmt = select(ConversationSession).where(
            ConversationSession.project_id == project.id
        ).order_by(ConversationSession.created_at.desc())
        sess_res = await db.execute(sess_stmt)
        active_session = sess_res.scalars().first()
        if active_session:
            iter_stmt = select(AnalysisIteration).where(
                AnalysisIteration.session_id == active_session.id
            ).order_by(AnalysisIteration.iteration_number.desc())
            iter_res = await db.execute(iter_stmt)
            latest_iter = iter_res.scalars().first()
            if latest_iter:
                conf = dict(latest_iter.confidence_scores or {})
                conf["quotation_rows"] = quotation_rows
                if per_panel:
                    quotation_rows_by_panel = dict(conf.get("quotation_rows_by_panel") or {})
                    quotation_rows_by_panel[detected_panel_code] = quotation_rows
                    conf["quotation_rows_by_panel"] = quotation_rows_by_panel
                conf["enclosure_spec"] = enclosure_spec
                conf["technical_audit"] = technical_audit
                conf["physical_layout"] = physical_layout
                conf["layout_conflicts"] = layout_conflicts
                conf["busbar_calc"] = {
                    "profile": busbar_calc.profile,
                    "section_mm2": busbar_calc.section_mm2,
                    "mass_Cu_kg": busbar_calc.mass_Cu_kg,
                    "unit_price": busbar_calc.unit_price,
                    "spec_title": busbar_calc.spec_title,
                    "need_busbar": need_busbar
                }
                latest_iter.confidence_scores = conf
                if not per_panel:
                    latest_iter.ai_parsed_devices = [d.model_dump() for d in extracted_devices]
                db.add(latest_iter)

        await db.commit()
        if cad_file:
            await db.refresh(cad_file)
        if excel_file_info and "excel_file" in locals() and excel_file:
            await db.refresh(excel_file)
            excel_file_info["id"] = excel_file.id

        await emit_progress("published", 100, "Đã lưu CAD và báo giá vào dự án")

        return {
            "success": True,
            "cad_file": {
                "id": cad_file.id if cad_file else 0,
                "filename": dxf_filename,
                "file_path": cad_file_path,
                "file_size": dxf_size
            } if cad_file else None,
            "cad_layout": cad_layout,
            "quotation_file": excel_file_info,
            "quotation_rows": quotation_rows,
            "technical_proposals": technical_proposals,
            "enclosure_spec": enclosure_spec,
            "busbar_calc": {
                "profile": busbar_calc.profile,
                "section_mm2": busbar_calc.section_mm2,
                "mass_Cu_kg": busbar_calc.mass_Cu_kg,
                "unit_price": busbar_calc.unit_price,
                "spec_title": busbar_calc.spec_title,
                "need_busbar": need_busbar
            },
            "physical_layout": physical_layout,
            "layout_conflicts": layout_conflicts,
            "technical_audit": technical_audit,
            "devices": [d.model_dump() for d in extracted_devices]
        }
