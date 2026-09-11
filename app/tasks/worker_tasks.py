import asyncio
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy import select

from app.tasks.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.conversation_session import ConversationSession
from app.models.analysis_iteration import AnalysisIteration
from app.services.ai.analysis_pipeline_service import AnalysisPipelineService
from app.services.ai.connection_pool import ConnectionPoolService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.worker_tasks.analyze_project_async_task")
def analyze_project_async_task(
    self,
    project_id: int,
    user_id: int,
    file_id: Optional[int] = None,
    user_prompt: Optional[str] = None,
    fallback_to_standard_template: bool = False
) -> Dict[str, Any]:
    """
    Celery Background Task để bóc tách dự án CAD/PDF/Ảnh bất đồng bộ.
    Cập nhật trạng thái tiến độ thời gian thực (% tiến độ) và lưu kết quả vào DB.
    """
    self.update_state(
        state="PROGRESS",
        meta={"progress": 10, "stage": "init", "message": "Đang chuẩn bị file và dữ liệu dự án..."}
    )

    async def _run():
        async with AsyncSessionLocal() as db:
            # 1. Tìm thông tin project
            proj_stmt = select(Project).where(Project.id == project_id)
            proj_res = await db.execute(proj_stmt)
            project = proj_res.scalar_one_or_none()
            if not project:
                raise ValueError(f"Dự án ID {project_id} không tồn tại.")

            # 2. Tìm User
            user_stmt = select(User).where(User.id == user_id)
            user_res = await db.execute(user_stmt)
            current_user = user_res.scalar_one_or_none()
            if not current_user:
                raise ValueError(f"Người dùng ID {user_id} không tồn tại.")

            # 3. Tìm files nguồn bóc tách
            if file_id:
                target_stmt = select(ProjectFile).where(ProjectFile.id == file_id)
                target_res = await db.execute(target_stmt)
                target_file = target_res.scalar_one_or_none()
                project_files = [target_file] if target_file else []
            else:
                files_stmt = select(ProjectFile).where(
                    ProjectFile.project_id == project_id,
                    (ProjectFile.is_generated == False) | (ProjectFile.is_generated == None),
                    ~ProjectFile.filename.like("BanVe_%"),
                    ~ProjectFile.filename.like("PhacThao_%")
                )
                files_res = await db.execute(files_stmt)
                project_files = files_res.scalars().all()

            if not project_files:
                raise ValueError("Không tìm thấy file nguồn hợp lệ để bóc tách.")

            self.update_state(
                state="PROGRESS",
                meta={"progress": 25, "stage": "ai_connection", "message": "Đang kết nối AI Provider..."}
            )

            # 4. Lấy danh sách AI Connections
            all_connections = await ConnectionPoolService.get_ordered_connections(db)
            active_ai = all_connections[0] if all_connections else None
            if not active_ai:
                raise ValueError("Cần ít nhất một kết nối AI đang hoạt động trong hệ thống.")

            self.update_state(
                state="PROGRESS",
                meta={"progress": 45, "stage": "ai_vision", "message": "Đang phân tích hình ảnh và bóc tách thiết bị qua AI..."}
            )

            # 5. Chạy pipeline bóc tách
            pipeline_result = await AnalysisPipelineService.execute_analysis(
                project=project,
                project_files=project_files,
                active_ai=active_ai,
                current_user=current_user,
                fallback_to_standard_template=bool(fallback_to_standard_template),
                user_prompt=user_prompt,
                db=db,
                all_connections=all_connections,
                generate_cad_and_quotation=False
            )

            self.update_state(
                state="PROGRESS",
                meta={"progress": 85, "stage": "saving", "message": "Đang lưu trữ dữ liệu và hoàn tất..."}
            )

            extracted_devices = pipeline_result.get("devices", [])
            warnings = pipeline_result.get("warnings", [])
            enclosure_spec = pipeline_result.get("enclosure_spec")
            quotation_rows = pipeline_result.get("quotation_rows", [])
            tokens_consumed = pipeline_result.get("tokens_consumed", 0)

            if current_user.tokens >= tokens_consumed:
                current_user.tokens -= tokens_consumed

            # Lưu phiên ConversationSession
            sess_stmt = select(ConversationSession).where(
                ConversationSession.project_id == project_id,
                ConversationSession.status == "active"
            )
            sess_res = await db.execute(sess_stmt)
            active_session = sess_res.scalar_one_or_none()
            if not active_session:
                import uuid
                active_session = ConversationSession(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    user_id=user_id,
                    status="active"
                )
                db.add(active_session)
                await db.flush()

            # Lưu AnalysisIteration
            iter_stmt = select(AnalysisIteration).where(
                AnalysisIteration.session_id == active_session.id
            )
            iter_res = await db.execute(iter_stmt)
            existing_iters = iter_res.scalars().all()
            iter_num = len(existing_iters) + 1

            new_iter = AnalysisIteration(
                session_id=active_session.id,
                iteration_number=iter_num,
                trigger_type="async_celery_task",
                extracted_devices=extracted_devices,
                enclosure_spec=enclosure_spec,
                quotation_rows=quotation_rows,
                warnings=warnings,
                tokens_consumed=tokens_consumed,
                user_prompt=user_prompt or ""
            )
            db.add(new_iter)
            await db.commit()

            return {
                "success": True,
                "project_id": project_id,
                "session_id": active_session.id,
                "iteration_id": new_iter.id,
                "devices_count": len(extracted_devices),
                "devices": extracted_devices,
                "enclosure_spec": enclosure_spec,
                "quotation_rows": quotation_rows,
                "warnings": warnings,
                "tokens_consumed": tokens_consumed
            }

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_run())
        loop.close()
        return result
    except Exception as exc:
        logger.error(f"[Celery] Lỗi khi thực hiện task bóc tách: {exc}", exc_info=True)
        self.update_state(
            state="FAILURE",
            meta={"progress": 0, "stage": "error", "error": str(exc)}
        )
        raise exc


@celery_app.task(name="app.tasks.worker_tasks.process_cad_file")
def process_cad_file(file_path: str, project_id: str):
    """Heavy CAD parsing in background."""
    pass


@celery_app.task(name="app.tasks.worker_tasks.generate_excel_export")
def generate_excel_export(project_id: str, scope: str, layout: str):
    """Excel quotation generation in background."""
    pass
