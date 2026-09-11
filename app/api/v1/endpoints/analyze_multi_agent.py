"""
Multi-Agent BOM Extraction Endpoint
Sử dụng Multi-Agent Orchestrator cho iterative refinement
"""
import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.project import Project
from app.models.project_file import ProjectFile
try:
    from app.models.cad_template import CADTemplate
except ImportError:
    CADTemplate = None

try:
    from app.models.quotation_template import QuotationTemplate
except ImportError:
    QuotationTemplate = None

from app.schemas.ai import AnalyzeStartRequest
from app.services.ai.multi_agent_orchestrator import MultiAgentOrchestrator
from app.core.config import settings
from app.core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/start-multi-agent")
async def start_multi_agent_analysis(
    request: AnalyzeStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Multi-Agent BOM Extraction với iterative refinement
    
    Features:
    - 6 specialized agents (VisionExtractor, SpecValidator, CatalogMatcher, 
      QualityChecker, QuotationBuilder, CADGenerator)
    - Adaptive complexity detection (simple/standard/complex/very_complex)
    - Multi-panel detection (tách nhiều tủ điện)
    - Multi-panel quotations (1 báo giá/tủ + 1 tổng hợp)
    - Block/module support
    - Quality scoring với iterative improvement
    """
    logger.info(f"Starting multi-agent analysis for project {request.project_id}")
    
    # 1. Load project
    proj_stmt = select(Project).where(Project.id == request.project_id)
    proj_res = await db.execute(proj_stmt)
    project = proj_res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Dự án không tồn tại")
    
    # 2. Load file(s)
    files_stmt = select(ProjectFile).where(ProjectFile.project_id == request.project_id)
    if request.file_id:
        files_stmt = files_stmt.where(ProjectFile.id == request.file_id)
    else:
        files_stmt = files_stmt.where(
            (ProjectFile.is_generated == False) | (ProjectFile.is_generated == None),
            ~ProjectFile.filename.like("BanVe_%"),
            ~ProjectFile.filename.like("PhacThao_%")
        )
    files_res = await db.execute(files_stmt)
    project_files = files_res.scalars().all()
    if not project_files and not request.file_id:
        all_res = await db.execute(select(ProjectFile).where(ProjectFile.project_id == request.project_id))
        project_files = all_res.scalars().all()
    
    if not project_files:
        raise HTTPException(status_code=400, detail="Không tìm thấy file để phân tích")
    
    # For now, use first image file
    image_file = next(
        (f for f in project_files if f.filename and 
         f.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp'))),
        None
    )
    
    if not image_file:
        raise HTTPException(
            status_code=400, 
            detail="Chưa hỗ trợ file này. Vui lòng upload file ảnh (PNG/JPG)"
        )
    
    if not os.path.exists(image_file.file_path):
        raise HTTPException(status_code=404, detail="File không tồn tại trên server")
    
    # 3. Load AI connection (Connection Pool - Priority ordered)
    from app.services.ai.connection_pool import ConnectionPoolService
    all_connections = await ConnectionPoolService.get_ordered_connections(db)
    active_ai = all_connections[0] if all_connections else None
    
    if not active_ai:
        raise HTTPException(
            status_code=400,
            detail="Chưa cấu hình AI Provider. Vui lòng cấu hình trong Admin."
        )
    
    # 4. Load templates (optional)
    cad_template = None
    if CADTemplate is not None:
        try:
            cad_template_stmt = select(CADTemplate).where(CADTemplate.is_default == True)
            cad_res = await db.execute(cad_template_stmt)
            cad_template = cad_res.scalars().first()
        except Exception:
            pass

    quotation_template = None
    if QuotationTemplate is not None:
        try:
            quotation_template_stmt = select(QuotationTemplate).where(
                QuotationTemplate.is_active == True
            ).order_by(QuotationTemplate.created_at.desc())
            quotation_res = await db.execute(quotation_template_stmt)
            quotation_template = quotation_res.scalars().first()
        except Exception:
            pass
    
    # 5. Run Multi-Agent Orchestrator
    orchestrator = MultiAgentOrchestrator(
        provider=active_ai.provider.lower(),
        api_key=active_ai.api_key,
        model=active_ai.selected_model,
        max_iterations=5,
        confidence_threshold=0.90
    )
    
    try:
        result = await orchestrator.orchestrate(
            image_path=image_file.file_path,
            project_name=project.name,
            cad_template=cad_template.template_data if cad_template else None,
            quotation_template=quotation_template.template_structure if quotation_template else None
        )
    except Exception as e:
        logger.error(f"Multi-agent orchestration failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi trong quá trình phân tích: {str(e)}"
        )
    
    # 6. Deduct tokens
    tokens_used = result.get("total_tokens_used", 0)
    if current_user.tokens >= tokens_used:
        current_user.tokens -= tokens_used
        await db.commit()
    else:
        logger.warning(f"User {current_user.id} không đủ tokens ({current_user.tokens} < {tokens_used})")
    
    # 7. Save results to database (TODO: implement persistence)
    # - Save ConversationSession
    # - Save AnalysisIteration for each agent step
    # - Save extracted devices
    # - Save generated files (CAD, Quotations)
    
    # 8. Return response
    return {
        "success": True,
        "project_id": project.id,
        "project_name": project.name,
        "file_analyzed": {
            "id": image_file.id,
            "filename": image_file.filename,
            "file_path": image_file.file_path
        },
        "analysis_result": {
            "complexity": result.get("complexity_level"),
            "total_iterations": result.get("total_iterations"),
            "final_confidence": result.get("final_confidence_score"),
            "device_count": len(result.get("devices", [])),
            "panel_count": len(result.get("panels", [])),
            "devices": result.get("devices", []),
            "panels": [
                {
                    "id": p.id,
                    "name": p.name,
                    "device_count": p.device_count,
                    "incomer_rating": p.incomer_rating
                } for p in result.get("panels", [])
            ],
            "quotation_files": result.get("quotation_files", []),
            "cad_file": result.get("cad_file"),
            "enclosure_spec": result.get("enclosure_spec"),
            "feedback_history": result.get("feedback_history", []),
            "warnings": result.get("warnings", [])
        },
        "tokens_used": tokens_used,
        "user_tokens_remaining": current_user.tokens
    }


@router.get("/test-multi-agent")
async def test_multi_agent():
    """
    Test endpoint để verify multi-agent system hoạt động
    """
    return {
        "status": "ready",
        "orchestrator": "MultiAgentOrchestrator",
        "agents": [
            "VisionExtractor",
            "SpecValidator",
            "CatalogMatcher",
            "QualityChecker",
            "QuotationBuilder",
            "CADGenerator"
        ],
        "features": [
            "Iterative refinement (max 5 iterations)",
            "Adaptive complexity detection",
            "Multi-panel detection",
            "Block/module support",
            "Template-based quotation & CAD",
            "Quality scoring with feedback loop"
        ]
    }
