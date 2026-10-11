"""Heavy jobs run outside the API, including on Windows with Celery solo."""
import asyncio
from datetime import datetime, timezone
import logging
import threading
import time

from celery.signals import worker_ready, worker_shutdown
from sqlalchemy import select, update

from app.tasks.celery_app import celery_app
from app.db.session import AsyncSessionLocal, engine
from app.models.user import User
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.conversation_session import ConversationSession
from app.models.analysis_iteration import AnalysisIteration
from app.services.ai.analysis_pipeline_service import AnalysisPipelineService
from app.services.ai.analysis_result import _build_analysis_result_schema
from app.services.ai.connection_pool import ConnectionPoolService
from app.services import job_queue
from app.core.config import settings

logger = logging.getLogger(__name__)
_heartbeat_stop = threading.Event()


@worker_ready.connect
def ready(**kwargs):
    _heartbeat_stop.clear()
    def heartbeat():
        while not _heartbeat_stop.is_set():
            try:
                with job_queue.sync_client() as client:
                    client.set(job_queue.READY_KEY,'1',ex=20)
            except Exception:
                logger.exception('Worker heartbeat failed')
            _heartbeat_stop.wait(4)
    threading.Thread(target=heartbeat,daemon=True).start()


@worker_shutdown.connect
def stopped(**kwargs):
    _heartbeat_stop.set()


async def _project_user(db, project_id, user_id):
    project = (await db.execute(select(Project).where(Project.id==project_id,
                  Project.user_id==user_id,Project.deleted_at.is_(None)))).scalar_one_or_none()
    user = (await db.execute(select(User).where(User.id==user_id,
                  User.deleted_at.is_(None)))).scalar_one_or_none()
    if not project or not user or not user.is_active:
        raise ValueError('Dự án hoặc tài khoản không còn hoạt động.')
    return project,user


async def run_analysis(project_id, user_id, payload, progress):
    """Also callable with an isolated DB/pipeline in integration tests."""
    started = time.perf_counter()
    async with AsyncSessionLocal() as db:
        project,user = await _project_user(db,project_id,user_id)
        if user.tokens <= 0:
            raise ValueError('Tài khoản không còn token phân tích.')
        files = (await db.execute(select(ProjectFile).where(ProjectFile.project_id==project_id))).scalars().all()
        fid = payload.get('file_id')
        if fid:
            chosen = next((f for f in files if f.id==fid),None)
            if not chosen:
                raise ValueError('Không tìm thấy tệp nguồn của dự án.')
            if not chosen.is_generated:
                files = [chosen]
        files = [f for f in files if not f.is_generated]
        if not files:
            raise ValueError('Không có tệp nguồn để phân tích.')
        connections = await ConnectionPoolService.get_ordered_connections(db)
        if not connections:
            raise ValueError('Chưa có kết nối AI đang hoạt động.')
        ai = connections[0]
        result = await AnalysisPipelineService.execute_analysis(
            project=project,project_files=files,active_ai=ai,current_user=user,db=db,
            all_connections=connections,user_prompt=payload.get('user_prompt'),
            fallback_to_standard_template=bool(payload.get('fallback_to_standard_template')),
            target_page=payload.get('target_page'),generate_cad_and_quotation=False,
            progress_callback=progress,persist_partial_iterations=False)
        consumed = max(0,int(result.get('tokens_consumed') or 0))
        progress({'type':'log','stage':'saving','title':'Đang lưu kết quả phân tích'})
        charged = await db.execute(update(User).where(User.id==user_id,User.tokens>=consumed)
                       .values(tokens=User.tokens-consumed).execution_options(synchronize_session=False))
        if charged.rowcount != 1:
            raise ValueError('Không đủ token để lưu kết quả phân tích.')
        session = (await db.execute(select(ConversationSession).where(
            ConversationSession.project_id==project_id,ConversationSession.status=='active')
            .order_by(ConversationSession.created_at.desc()))).scalars().first()
        if session and payload.get('is_new_session'):
            session.status='archived'
            session=None
        if session is None:
            session=ConversationSession(project_id=project_id,user_id=user_id,
                provider=ai.provider,model_key=ai.selected_model,status='active',
                total_iterations=0,total_tokens_used=0)
            db.add(session)
            await db.flush()
        session.total_iterations += 1
        session.total_tokens_used += consumed
        devices=[d.model_dump(mode='json') if hasattr(d,'model_dump') else dict(d)
                 for d in result.get('devices',[])]
        conf={key:result.get(key) for key in ('warnings','quotation_rows','technical_proposals',
              'conclusion','panel_info','panels','enclosure_spec','technical_audit',
              'evidence_overviews','file_assessment','files_assessment','circuit_assessment',
              'overall_assessment','execution_logs','process_steps','physical_layout',
              'layout_conflicts','analysis_mode','log_version') if result.get(key) is not None}
        iteration=AnalysisIteration(session_id=session.id,iteration_number=session.total_iterations,
            trigger_type='async_celery_task',user_message=payload.get('user_prompt'),
            files_analyzed={'file_ids':[f.id for f in files],'file_names':[f.filename for f in files],
                            'count':len(files)},ai_parsed_devices=devices,confidence_scores=conf,
            tokens_used=consumed,processing_time_ms=int((time.perf_counter()-started)*1000),
            status='completed')
        db.add(iteration)
        project.updated_at=datetime.now(timezone.utc)
        await db.flush()
        response=_build_analysis_result_schema(session.id,session.total_iterations,devices,conf,
                                                iteration_id=iteration.id).model_dump(mode='json')
        await db.commit()
        return response


async def run_cad(project_id,user_id,payload,progress):
    async with AsyncSessionLocal() as db:
        project,_ = await _project_user(db,project_id,user_id)
        devices=payload.get('devices') or []
        latest=(await db.execute(select(AnalysisIteration).join(ConversationSession)
            .where(ConversationSession.project_id==project_id)
            .order_by(AnalysisIteration.created_at.desc(),AnalysisIteration.id.desc()))).scalars().first()
        if latest and str(latest.trigger_type or '').startswith('partial_panel'):
            raise ValueError('Bóc tách chưa hoàn tất toàn bộ trang. Chưa được tạo thiết kế từ bản tạm.')
        if not devices:
            devices=latest.ai_parsed_devices if latest else []
        if not devices:
            raise ValueError('Chưa có thiết bị; hãy phân tích bản vẽ trước.')
        return await AnalysisPipelineService.generate_cad_and_quotation(project=project,db=db,
            devices=devices,brand_preference=payload.get('brand_preference') or settings.DEFAULT_BRAND,
            user_prompt=payload.get('user_prompt'),enclosure_dimensions=payload.get('enclosure_dimensions'),
            source_configuration=payload.get('source_configuration') or 'schematic',
            panel_code=payload.get('panel_code'),panel_name=payload.get('panel_name'),
            per_panel=bool(payload.get('per_panel')),progress_callback=progress)


def _execute(task,kind,project_id,user_id,payload):
    job_id=task.request.id
    try:
        if job_queue.cancelled(job_id):
            raise ValueError('Tác vụ đã bị hủy.')
        async def execute():
            def progress(event):
                if job_queue.cancelled(job_id):
                    raise ValueError('Tác vụ đã bị hủy.')
                job_queue.publish(job_id,event)
            try:
                return await asyncio.wait_for((run_analysis if kind=='analysis' else run_cad)(
                    project_id,user_id,payload,progress),timeout=1800)
            finally:
                # Async pools must not retain connections bound to a previous job's loop.
                await engine.dispose()
        result=asyncio.run(execute())
        job_queue.publish(job_id,{'type':'complete','result':result,'progress':100},'SUCCESS',result)
        return result
    except Exception as exc:
        logger.exception('Background %s job failed',kind)
        # Let Celery serialize failures itself; malformed FAILURE metadata breaks AsyncResult.
        try:
            status='CANCELLED' if job_queue.cancelled(job_id) else 'FAILURE'
            job_queue.publish(job_id,{'type':'error','stage':kind,'title':'Xử lý đã dừng',
                              'detail':str(exc),'message':str(exc)},status)
        except Exception:
            logger.warning('Unable to deliver terminal job event; API can recover Celery terminal state.')
        raise
    finally:
        try:
            job_queue.release(job_id,project_id)
        except Exception:
            logger.warning('Unable to release job slot; retain original error and recover terminal state later.')


@celery_app.task(bind=True,name='app.tasks.worker_tasks.analyze_project_async_task')
def analyze_project_async_task(self,project_id,user_id,payload=None,**legacy):
    return _execute(self,'analysis',project_id,user_id,payload or legacy)


@celery_app.task(bind=True,name='app.tasks.worker_tasks.generate_cad_async_task')
def generate_cad_async_task(self,project_id,user_id,payload):
    return _execute(self,'cad',project_id,user_id,payload)
