"""One active project conversation; immutable result IDs retain every run."""
from sqlalchemy import select, update, case
from sqlalchemy.orm import load_only
from app.models.project import Project
from app.models.conversation_session import ConversationSession
from app.models.analysis_iteration import AnalysisIteration


async def project_session(db, project_id, user_id, provider=None, model_key=None):
    # Serialize first-use consolidation and concurrent chat/worker saves.
    await db.execute(update(Project).where(Project.id == project_id).values(updated_at=Project.updated_at))
    sessions = list((await db.execute(select(ConversationSession).where(
        ConversationSession.project_id == project_id).options(load_only(
            ConversationSession.id, ConversationSession.user_id, ConversationSession.status,
            ConversationSession.total_iterations, ConversationSession.total_tokens_used,
            ConversationSession.created_at)).order_by(ConversationSession.created_at, ConversationSession.id))).scalars())
    if not sessions:
        session = ConversationSession(project_id=project_id, user_id=user_id, provider=provider,
            model_key=model_key, status='active', total_iterations=0, total_tokens_used=0)
        db.add(session)
        await db.flush()
        return session
    session = sessions[0]
    ids = [s.id for s in sessions]
    # Archived empty parents are retained for compatibility, but never reused.
    runs = list((await db.execute(select(AnalysisIteration.id, AnalysisIteration.session_id)
        .where(AnalysisIteration.session_id.in_(ids))
        .order_by(AnalysisIteration.created_at, AnalysisIteration.id))).all())
    if any(row.session_id != session.id for row in runs):
        numbers = {row.id:index+1 for index,row in enumerate(runs)}
        await db.execute(update(AnalysisIteration).where(AnalysisIteration.id.in_(numbers)).values(
            session_id=session.id, iteration_number=case(numbers, value=AnalysisIteration.id))
            .execution_options(synchronize_session=False))
    session.total_tokens_used = sum(s.total_tokens_used or 0 for s in sessions)
    for old in sessions[1:]:
        old.status = 'archived'
        old.total_tokens_used = 0
        old.total_iterations = 0
    session.status = 'active'
    session.finalized_at = None
    session.total_iterations = len(runs)
    if provider is not None:
        session.provider = provider
        session.model_key = model_key
    await db.flush()
    return session
