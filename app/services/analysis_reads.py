"""Bounded relational read models; large AI prompts stay in detail records."""
from fastapi import HTTPException
from sqlalchemy import select, func, cast, String, case, JSON, type_coerce
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
    if db.bind.dialect.name == 'sqlite' and db.bind.url.database not in (None, '', ':memory:'):
        from app.services.session_summaries import get_summary
        query = (select(AnalysisIteration.id, AnalysisIteration.session_id,
                        AnalysisIteration.iteration_number, AnalysisIteration.trigger_type,
                        AnalysisIteration.files_analyzed, AnalysisIteration.created_at, AnalysisIteration.updated_at,
                        ConversationSession.status.label('session_status'))
                 .join(ConversationSession, relation).where(*filters)
                 .order_by(AnalysisIteration.created_at.desc(), AnalysisIteration.id.desc())
                 .offset(skip).limit(limit))
        rows = (await db.execute(query)).all()
        result = []
        for row in rows:
            summary = await get_summary(db, row)
            result.append((AnalysisIteration(id=row.id, session_id=row.session_id,
                iteration_number=row.iteration_number, trigger_type=row.trigger_type,
                files_analyzed=row.files_analyzed, created_at=row.created_at,
                ai_parsed_devices=summary['devices'], confidence_scores=summary['conf']),
                ConversationSession(id=row.session_id, status=row.session_status)))
        return result, total
    if db.bind.dialect.name == 'sqlite':
        # Project history needs counts and panel labels, never image blobs or
        # the full confidence payload. Project inside SQLite before transport.
        entries = func.json_each(AnalysisIteration.ai_parsed_devices).table_valued('value').alias('history_device')
        summary = (select(func.json_group_array(func.json_object(
            'panel_code', func.json_extract(entries.c.value, '$.panel_code'),
            'panel_name', func.json_extract(entries.c.value, '$.panel_name'),
            'quantity', func.json_extract(entries.c.value, '$.quantity'),
        ))).select_from(entries).where(func.json_type(AnalysisIteration.ai_parsed_devices) == 'array')
                   .correlate(AnalysisIteration).scalar_subquery())
        conf = func.json_object(*[part for key in ('panel_code','panel_name','panel_info')
                                 for part in (key, func.json_extract(AnalysisIteration.confidence_scores, '$.'+key))])
        query = (select(AnalysisIteration.id, AnalysisIteration.session_id,
                        AnalysisIteration.iteration_number, AnalysisIteration.trigger_type,
                        AnalysisIteration.files_analyzed, AnalysisIteration.created_at,
                        type_coerce(summary, JSON).label('devices'), type_coerce(conf, JSON).label('conf'),
                        ConversationSession.status.label('session_status'))
                 .join(ConversationSession, relation).where(*filters)
                 .order_by(AnalysisIteration.created_at.desc(), AnalysisIteration.id.desc())
                 .offset(skip).limit(limit))
        rows = (await db.execute(query)).all()
        return [(AnalysisIteration(id=r.id, session_id=r.session_id, iteration_number=r.iteration_number,
                                   trigger_type=r.trigger_type, files_analyzed=r.files_analyzed,
                                   created_at=r.created_at, ai_parsed_devices=r.devices or [],
                                   confidence_scores=r.conf or {}),
                 ConversationSession(id=r.session_id, status=r.session_status)) for r in rows], total
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
