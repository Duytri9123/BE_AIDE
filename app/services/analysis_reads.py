"""Bounded relational read models; large AI prompts stay in detail records."""
from fastapi import HTTPException
from sqlalchemy import select, func, cast, String, case
from sqlalchemy.orm import load_only
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.conversation_session import ConversationSession
from app.models.analysis_iteration import AnalysisIteration


async def require_project(db, project_id, user):
    query = select(Project.id).where(Project.id == project_id, Project.deleted_at.is_(None))
    if not user.is_superuser:
        query = query.where(Project.user_id == user.id)
    if (await db.execute(query)).scalar_one_or_none() is None:
        raise HTTPException(404, 'Dự án không tồn tại')


async def session_page(db, project_id, user, skip=0, limit=50):
    await require_project(db, project_id, user)
    relation = (AnalysisIteration.session_id == ConversationSession.id)
    filters = (ConversationSession.project_id == project_id, AnalysisIteration.status == 'completed')
    total = (await db.execute(select(func.count(AnalysisIteration.id))
             .join(ConversationSession, relation).where(*filters))).scalar_one()
    query = (select(AnalysisIteration, ConversationSession).join(ConversationSession, relation)
             .where(*filters).options(
                 load_only(AnalysisIteration.id, AnalysisIteration.session_id,
                           AnalysisIteration.iteration_number, AnalysisIteration.trigger_type,
                           AnalysisIteration.ai_parsed_devices, AnalysisIteration.confidence_scores,
                           AnalysisIteration.files_analyzed, AnalysisIteration.created_at),
                 load_only(ConversationSession.id, ConversationSession.status))
             .order_by(AnalysisIteration.created_at.desc(), AnalysisIteration.id.desc())
             .offset(skip).limit(limit))
    return (await db.execute(query)).all(), total


async def latest_analysis(db, project_id, user):
    await require_project(db, project_id, user)
    # An explicit chat deletion is a valid empty result. Prefer the newest
    # usable revision across project sessions, including edits of older sessions.
    populated = cast(AnalysisIteration.ai_parsed_devices, String).notin_(['null', '[]', '{}'])
    usable = populated | (AnalysisIteration.trigger_type == 'chat_update')
    iteration = (await db.execute(select(AnalysisIteration)
                 .join(ConversationSession, AnalysisIteration.session_id == ConversationSession.id)
                 .where(ConversationSession.project_id == project_id, AnalysisIteration.status == 'completed')
                 .options(load_only(AnalysisIteration.id, AnalysisIteration.session_id,
                                    AnalysisIteration.iteration_number, AnalysisIteration.ai_parsed_devices,
                                    AnalysisIteration.confidence_scores))
                 .order_by(case((usable, 0), else_=1), AnalysisIteration.created_at.desc(),
                           AnalysisIteration.id.desc()).limit(1))).scalar_one_or_none()
    if iteration is None:
        return None, None, None
    session = iteration.session_id
    cad = (await db.execute(select(ProjectFile).where(ProjectFile.project_id == project_id,
           ProjectFile.filename.like('BanVe_%') | ProjectFile.filename.like('PhacThao_%'))
           .options(load_only(ProjectFile.id, ProjectFile.filename, ProjectFile.file_path, ProjectFile.file_size))
           .order_by(ProjectFile.created_at.desc(), ProjectFile.id.desc()).limit(1))).scalar_one_or_none()
    return session, iteration, cad
