"""Project chat replies and persisted follow-up edits; never rerun extraction."""
import asyncio
import logging
import uuid
from copy import deepcopy

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.models.project import Project
from app.models.conversation_session import ConversationSession
from app.models.analysis_iteration import AnalysisIteration
from app.schemas.ai import ChatRequest, ChatResponse
from app.services.ai.connection_pool import ConnectionPoolService
from app.services.ai.vision_analyzer import VisionAnalyzerService
from app.services.ai.project_chat import conversation_prompt, parse_plan, apply_plan, updated_confidence

logger = logging.getLogger(__name__)
router = APIRouter()


def saved_response(iteration, project_id):
    meta = iteration.user_corrections or {}
    return ChatResponse(reply=meta["reply"], action_type="update_devices",
        devices=iteration.ai_parsed_devices or [], project_id=project_id,
        base_iteration_id=meta.get("base_iteration_id"), iteration_id=iteration.id,
        iteration_number=iteration.iteration_number, session_id=iteration.session_id)


async def replay(db, project_id, request_id):
    if request_id is None:
        return None
    return (await db.execute(select(AnalysisIteration)
        .join(ConversationSession, AnalysisIteration.session_id == ConversationSession.id)
        .where(ConversationSession.project_id == project_id,
            AnalysisIteration.trigger_type == "chat_update",
            AnalysisIteration.user_corrections["request_id"].as_string() == str(request_id))
        .limit(1))).scalar_one_or_none()


@router.post("/", response_model=ChatResponse)
async def chat_with_cad_agent(request: ChatRequest, db: AsyncSession = Depends(get_db),
                             current_user: User = Depends(get_current_active_user)):
    project = (await db.execute(select(Project).where(Project.id == request.project_id,
        Project.user_id == current_user.id, Project.deleted_at.is_(None)))).scalar_one_or_none()
    if project is None:
        raise HTTPException(404, "Dự án không tồn tại")
    previous = await replay(db, project.id, request.request_id)
    if previous:
        return saved_response(previous, project.id)

    base_id = (request.context or {}).get("iteration_id")
    if base_id is not None and (type(base_id) is not int or base_id <= 0):
        raise HTTPException(422, "Phiên thiết bị không hợp lệ.")
    statement = select(AnalysisIteration).join(ConversationSession,
        AnalysisIteration.session_id == ConversationSession.id).where(
            ConversationSession.project_id == project.id,
            ConversationSession.user_id == current_user.id,
            AnalysisIteration.status == "completed")
    if base_id is not None:
        statement = statement.where(AnalysisIteration.id == base_id)
    source = (await db.execute(statement.order_by(AnalysisIteration.created_at.desc(),
        AnalysisIteration.id.desc()).limit(1))).scalar_one_or_none()
    if base_id is not None and source is None:
        raise HTTPException(404, "Phiên thiết bị không thuộc dự án này.")
    devices = deepcopy(request.current_devices if request.current_devices is not None
                       else (source.ai_parsed_devices if source else []) or [])
    if len(devices) > 5000:
        raise HTTPException(413, "Danh sách thiết bị quá lớn cho một lượt chat.")
    prompt = conversation_prompt(request.message, devices, request.context)
    if len(prompt) > 600000:
        raise HTTPException(413, "Ngữ cảnh hội thoại quá dài. Vui lòng rút gọn yêu cầu.")
    connections = await ConnectionPoolService.get_ordered_connections(db)
    if not connections:
        raise HTTPException(503, "Chưa có kết nối AI khả dụng cho chat. Vui lòng thử lại sau.")
    try:
        raw, _ = await asyncio.wait_for(ConnectionPoolService.call_with_fallback(
            db=db, connections=connections, call_fn=VisionAnalyzerService.analyze_text,
            prompt=prompt), timeout=90)
    except Exception:
        logger.exception("Project chat inference failed")
        raise HTTPException(502, "AI chưa phản hồi thành công. Chưa có thay đổi nào được áp dụng.")
    try:
        plan = parse_plan(raw)
        edited = apply_plan(devices, plan)
    except Exception:
        logger.warning("Invalid project chat plan", exc_info=True)
        raise HTTPException(502, "AI trả về chỉnh sửa chưa hợp lệ. Chưa có thay đổi nào được áp dụng; vui lòng thử lại.")
    if edited == devices:
        return ChatResponse(reply=plan.reply, action_type="general_chat", project_id=project.id,
                            base_iteration_id=base_id)

    # Serialize saves for this project, then recheck retry idempotency. Provider
    # fallback may commit connection health earlier, so take the lock only now.
    if db.bind.dialect.name == "sqlite":
        # SQLite ignores FOR UPDATE. Release the read transaction and acquire
        # a writer reservation before replay/save, including across workers.
        await db.commit()
        await db.execute(text("BEGIN IMMEDIATE"))
    else:
        await db.execute(select(Project.id).where(Project.id == project.id).with_for_update())
    previous = await replay(db, project.id, request.request_id)
    if previous:
        return saved_response(previous, project.id)
    if source:
        session = (await db.execute(select(ConversationSession)
            .where(ConversationSession.id == source.session_id))).scalar_one()
    else:
        session = ConversationSession(id=uuid.uuid4(), project_id=project.id,
                                      user_id=current_user.id, total_iterations=0)
        db.add(session)
        await db.flush()
    latest_number = (await db.execute(select(func.max(AnalysisIteration.iteration_number))
        .where(AnalysisIteration.session_id == session.id))).scalar_one() or 0
    reply = plan.reply.strip() + "\n\nĐã lưu danh sách thiết bị cập nhật vào project."
    iteration = AnalysisIteration(session_id=session.id, iteration_number=latest_number + 1,
        trigger_type="chat_update", user_message=request.message,
        user_corrections={"request_id": str(request.request_id) if request.request_id else None,
                          "base_iteration_id": base_id, "reply": reply},
        files_analyzed=deepcopy(source.files_analyzed) if source else {},
        ai_parsed_devices=edited, devices_after_validation=edited,
        confidence_scores=updated_confidence(source.confidence_scores if source else {}, edited),
        status="completed")
    db.add(iteration)
    session.total_iterations = latest_number + 1
    await db.commit()
    await db.refresh(iteration)
    return saved_response(iteration, project.id)
