"""Bounded relational read models; large AI prompts stay in detail records."""
from fastapi import HTTPException
from sqlalchemy import select, func, case
from sqlalchemy.orm import load_only
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.conversation_session import ConversationSession
from app.models.analysis_iteration import AnalysisIteration
from app.models.analysis_summary import AnalysisSummary


async def require_project(db, project_id, user):
    query = select(Project.id).where(Project.id == project_id, Project.deleted_at.is_(None))
    if not user.is_superuser:
        query = query.where(Project.user_id == user.id)
    if (await db.execute(query)).scalar_one_or_none() is None:
        raise HTTPException(404, 'Dự án không tồn tại')


SAVED_STATUSES = ('completed', 'needs_review')


async def session_page(db, project_id, user, skip=0, limit=50):
    await require_project(db, project_id, user)
    relation = AnalysisSummary.session_id == ConversationSession.id
    filters = (ConversationSession.project_id == project_id,
               AnalysisSummary.status.in_(SAVED_STATUSES))
    total = (await db.execute(select(func.count(AnalysisSummary.id))
             .join(ConversationSession, relation).where(*filters))).scalar_one()
    rows = (await db.execute(select(AnalysisSummary, ConversationSession.status)
            .join(ConversationSession, relation).where(*filters)
            .options(load_only(AnalysisSummary.id, AnalysisSummary.session_id,
                AnalysisSummary.iteration_number, AnalysisSummary.trigger_type,
                AnalysisSummary.user_message, AnalysisSummary.files_analyzed,
                AnalysisSummary.created_at, AnalysisSummary.status,
                AnalysisSummary.devices, AnalysisSummary.confidence))
            .order_by(AnalysisSummary.created_at.desc(), AnalysisSummary.id.desc())
            .offset(skip).limit(limit))).all()
    return [(AnalysisIteration(id=r.id, session_id=r.session_id,
                iteration_number=r.iteration_number, trigger_type=r.trigger_type,
                user_message=r.user_message, files_analyzed=r.files_analyzed,
                created_at=r.created_at, status=r.status,
                devices_after_validation=None, ai_parsed_devices=r.devices,
                confidence_scores=r.confidence),
             ConversationSession(id=r.session_id, status=status)) for r, status in rows], total


async def latest_analysis(db, project_id, user):
    await require_project(db, project_id, user)
    # Sort only small metadata. Fetch the large result by its primary key once.
    usable = AnalysisSummary.has_devices | (AnalysisSummary.trigger_type == 'chat_update')
    iteration_id = (await db.execute(select(AnalysisSummary.id)
        .join(ConversationSession, AnalysisSummary.session_id == ConversationSession.id)
        .where(ConversationSession.project_id == project_id,
               AnalysisSummary.status.in_(SAVED_STATUSES))
        .order_by(case((usable, 0), else_=1), AnalysisSummary.created_at.desc(),
                  AnalysisSummary.id.desc()).limit(1))).scalar_one_or_none()
    from app.services.analysis_payloads import saved_iteration
    iteration = await saved_iteration(db, iteration_id) if iteration_id is not None else None
    if iteration is None:
        return None, None, None
    session = iteration.session_id
    cad = (await db.execute(select(ProjectFile).where(ProjectFile.project_id == project_id,
           ProjectFile.filename.like('BanVe_%') | ProjectFile.filename.like('PhacThao_%'))
           .options(load_only(ProjectFile.id, ProjectFile.filename, ProjectFile.file_path, ProjectFile.file_size))
           .order_by(ProjectFile.created_at.desc(), ProjectFile.id.desc()).limit(1))).scalar_one_or_none()
    return session, iteration, cad
