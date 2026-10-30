"""Bounded reads and bulk deletes for saved takeoff sessions."""
import logging
import os

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import load_only

from app.models.analysis_iteration import AnalysisIteration
from app.models.conversation_session import ConversationSession
from app.models.project_file import ProjectFile
from app.services.analysis_reads import require_project


async def iteration_detail(db, iteration_id, user):
    row = (await db.execute(
        select(AnalysisIteration, ConversationSession.project_id)
        .join(ConversationSession, AnalysisIteration.session_id == ConversationSession.id)
        .where(AnalysisIteration.id == iteration_id)
        .options(load_only(
            AnalysisIteration.id, AnalysisIteration.session_id,
            AnalysisIteration.iteration_number, AnalysisIteration.ai_parsed_devices,
            AnalysisIteration.confidence_scores,
        ))
    )).first()
    if row is None:
        raise HTTPException(404, 'Không tìm thấy phiên bóc tách')
    iteration, project_id = row
    await require_project(db, project_id, user)
    cad = (await db.execute(
        select(ProjectFile)
        .where(ProjectFile.project_id == project_id,
               ProjectFile.filename.like('BanVe_%') | ProjectFile.filename.like('PhacThao_%'))
        .options(load_only(ProjectFile.id, ProjectFile.filename, ProjectFile.file_path, ProjectFile.file_size))
        .order_by(ProjectFile.created_at.desc(), ProjectFile.id.desc()).limit(1)
    )).scalar_one_or_none()
    return iteration, cad


async def remove_iteration(db, iteration_id, user):
    row = (await db.execute(
        select(AnalysisIteration.session_id, ConversationSession.project_id)
        .join(ConversationSession, AnalysisIteration.session_id == ConversationSession.id)
        .where(AnalysisIteration.id == iteration_id)
    )).first()
    if row is None:
        raise HTTPException(404, 'Phiên bóc tách không tồn tại')
    session_id, project_id = row
    await require_project(db, project_id, user)
    await db.execute(delete(AnalysisIteration).where(AnalysisIteration.id == iteration_id))
    # Do not load remaining iterations (which may contain large AI/image blobs).
    remaining = select(AnalysisIteration.id).where(AnalysisIteration.session_id == session_id).exists()
    await db.execute(delete(ConversationSession).where(
        ConversationSession.id == session_id, ~remaining,
    ).execution_options(synchronize_session=False))
    await db.commit()


async def remove_project_sessions(db, project_id, user):
    await require_project(db, project_id, user)
    sessions = select(ConversationSession.id).where(ConversationSession.project_id == project_id)
    await db.execute(delete(AnalysisIteration).where(
        AnalysisIteration.session_id.in_(sessions),
    ).execution_options(synchronize_session=False))
    await db.execute(delete(ConversationSession).where(
        ConversationSession.project_id == project_id,
    ).execution_options(synchronize_session=False))
    generated = (
        ProjectFile.filename.like('BanVe_%') |
        ProjectFile.filename.like('PhacThao_%') |
        ProjectFile.filename.like('BaoGia_%')
    )
    # Select paths only; physical cleanup runs after the transaction/response.
    paths = list((await db.execute(select(ProjectFile.file_path).where(
        ProjectFile.project_id == project_id, generated,
    ))).scalars())
    await db.execute(delete(ProjectFile).where(
        ProjectFile.project_id == project_id, generated,
    ).execution_options(synchronize_session=False))
    await db.commit()
    return paths


def cleanup_session_files(paths):
    for path in set(paths):
        if not path:
            continue
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        except OSError:
            logging.getLogger(__name__).warning('Could not remove generated session file: %s', path, exc_info=True)
