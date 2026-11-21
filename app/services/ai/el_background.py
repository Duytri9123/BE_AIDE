"""Server-owned EL loop. Browser disconnects never cancel accepted work."""
import asyncio
import hashlib
import json
import logging
import uuid

from starlette.requests import Request
from app.services.el_run_store import RunStore

logger = logging.getLogger(__name__)


async def dispatch(run_id):
    from app.tasks.celery_app import celery_app
    try:
        await asyncio.to_thread(celery_app.send_task, 'app.tasks.el_tasks.run_el',
                                kwargs={'run_id': run_id}, queue='aide_el')
    except Exception:
        await asyncio.to_thread(RunStore().dispatch_failed, run_id)
        raise


async def run(run_id, store=None):
    from app.api.v1.endpoints import el_agent
    from app.db.session import AsyncSessionLocal
    from app.tasks.worker_tasks import _project_user
    from app.main import app
    from app.schemas.ai import ChatRequest
    from app.services.ai.el_conversation import resolve_confirmed_takeoff, resolve_request
    from app.services.ai.el_progress import _sink, public_activity
    from app.core.security import create_access_token

    store = store or RunStore()
    lease = uuid.uuid4().hex
    row = await asyncio.to_thread(store.claim, run_id, lease)
    if row is None or row == 'BUSY':
        return row
    state = row['checkpoint'] or {'observations': [], 'activities': [], 'completed_writes': []}
    async def heartbeat():
        while True:
            await asyncio.sleep(20)
            await asyncio.to_thread(store.save, run_id, lease)
    pulse = asyncio.create_task(heartbeat())

    def activity(event):
        item = public_activity(event.get('activity') or {})
        if not item or not item.get('id'):
            return
        items = state.setdefault('activities', [])
        index = next((i for i, prior in enumerate(items) if prior['id'] == item['id']), None)
        if index is None:
            items.append(item)
        else:
            items[index] = item
        state['activities'] = items[-200:]
        store.save(run_id, lease, state)

    token = _sink.set(activity)
    try:
        async with AsyncSessionLocal() as db:
            _, user = await _project_user(db, row['project'], row['owner'])
            context = dict(row['payload'].get('context') or {})
            from app.services.ai.takeoff_regions import sign_scope
            accepted_scope = context.pop('_background_confirmed_scope', [])
            if accepted_scope:
                context['takeoff_scope'] = [{'scope_token': sign_scope(panel, row['project'])} for panel in accepted_scope]
            message = row['payload']['message']
            if not state.get('resolution'):
                state['resolution'] = resolve_confirmed_takeoff(message, context, accepted_scope)
                if not state['resolution']:
                    state['resolution'] = await resolve_request(db, message, context)
                store.save(run_id, lease, state)
            message = state['resolution']['effective']
            context.update(resolved_request=state['resolution'], run_id=run_id, execution_mode='server_background')
            registered = el_agent.api_tools(app)
            source_tool = {'name': 'read_project_sources', 'label': 'Đọc nguồn dự án', 'kind': 'source', 'writes': False,
                           'description': 'Đọc file nguồn đã chọn. source_page bắt đầu từ 1, source_region=[left,top,right,bottom] chuẩn hóa 0..1.',
                           'input_schema': {'type': 'object', 'properties': {'file_ids': {'type': 'array', 'items': {'type': 'integer'}}, 'source_page': {'type': 'integer'}, 'source_region': {'type': 'array', 'items': {'type': 'number'}}}}}
            context['tools'] = [source_tool, *registered.values()]

            # A worker interruption during a planner call may have saved an iteration.
            # Require review instead of repeating a possibly completed write.
            if state.get('phase') == 'planning':
                store.save(run_id, lease, state, 'FAILED', error='Worker đã gián đoạn khi lưu kết quả. Hãy kiểm tra kết quả dự án trước khi tiếp tục.')
                return
            while True:
                current = store.get(run_id)
                if current['pause']:
                    store.save(run_id, lease, state, 'PAUSED')
                    return
                context['observations'] = state.setdefault('observations', [])[-18:]
                headers = [(b'authorization', ('Bearer '+create_access_token(user.id)).encode())]
                request = Request({'type': 'http', 'app': app, 'headers': headers, 'method': 'POST', 'path': '/'})
                decision = state.get('pending')
                if not decision:
                    state['phase'] = 'planning'
                    store.save(run_id, lease, state)
                    decision = await el_agent.next_action(ChatRequest(project_id=row['project'], message=message, context=context), request, db, user)
                    state['phase'] = 'ready'
                    state['pending'] = decision
                    store.save(run_id, lease, state)
                if store.get(run_id)['pause']:
                    store.save(run_id, lease, state, 'PAUSED')
                    return
                if decision.get('verification_feedback'):
                    state['observations'].append({'tool': 'verify_project_extraction', 'arguments': {}, 'result': {
                        'ok': False, 'feedback': decision['verification_feedback'], 'candidate': decision.get('candidate')}})
                    state['pending'] = None
                    store.save(run_id, lease, state)
                    if len(state['observations']) >= 18:
                        store.save(run_id, lease, state, 'FAILED', error='Kết quả cần kiểm chứng thêm. Có thể tiếp tục từ tiến độ đã lưu.')
                        return
                    continue
                if decision.get('reply'):
                    store.save(run_id, lease, state, 'COMPLETED', result={**decision, 'artifacts': state.get('artifacts', []), 'outputs': state.get('outputs', [])})
                    return
                name, args = decision.get('tool'), decision.get('arguments') or {}
                tool = source_tool if name == source_tool['name'] else registered.get(name)
                if not tool:
                    raise ValueError('Thao tác cần trình biên tập CAD chưa có công cụ server tương ứng.')
                signature = hashlib.sha256(json.dumps([name, args], sort_keys=True).encode()).hexdigest()
                if tool.get('writes') and signature in state.setdefault('completed_writes', []):
                    raise ValueError('Thao tác đã thực hiện. Tiến độ được giữ để kiểm tra, không tự chạy lại.')
                event = {'id': uuid.uuid4().hex, 'tool': name, 'label': decision.get('activity') or tool['label'], 'state': 'running', 'changesProject': bool(tool.get('writes'))}
                activity({'activity': event})
                if name == 'read_project_sources':
                    from app.services.ai.requirement_analysis import analyze_requirements
                    ids = args.get('file_ids') or context.get('file_ids') or []
                    if context.get('file_ids') and any(i not in context['file_ids'] for i in ids):
                        raise ValueError('File đọc nằm ngoài nguồn đã chọn.')
                    connections = await el_agent.ConnectionPoolService.get_ordered_connections(db)
                    plan = await analyze_requirements(db, connections, row['project'], message, {
                        **context, 'file_ids': ids, 'source_page': args.get('source_page'), 'source_region': args.get('source_region')})
                    result = {'information': plan.reply}
                else:
                    result = await el_agent.execute(el_agent.ToolRequest(project_id=row['project'], tool=name, arguments=args,
                                                                         user_message=message, run_id=run_id), request, db, user)
                data = result.get('data') if isinstance(result.get('data'), dict) else result
                artifact_url = result.get('artifact_url') or data.get('download_url')
                if isinstance(artifact_url, str) and artifact_url.startswith('/api/v1/'):
                    state.setdefault('artifacts', []).append({'url': artifact_url, 'filename': result.get('filename') or data.get('filename') or 'Kết quả EL'})
                for file in (data.get('cad_file'), data.get('quotation_file')):
                    if isinstance(file, dict) and file.get('id'):
                        state.setdefault('outputs', []).append({'fileId': file['id'], 'filename': file.get('filename'), 'label': file.get('filename') or 'Kết quả EL'})
                serialized = json.dumps(result, ensure_ascii=False, default=str)
                observation = result if len(serialized) <= 12000 else {'truncated': True, 'excerpt': serialized[:12000], 'notice': 'Dùng bộ lọc/phân trang để đọc phần cần thiết.'}
                state['observations'].append({'tool': name, 'arguments': args, 'result': observation})
                state['observations'] = state['observations'][-18:]
                if tool.get('writes'):
                    state['completed_writes'].append(signature)
                state['pending'] = None
                state['phase'] = 'ready'
                activity({'activity': {**event, 'state': 'error' if result.get('ok') is False else 'success'}})
                store.save(run_id, lease, state)
    except Exception:
        logger.exception('EL background run failed: %s', run_id)
        # Retain checkpoints, but keep provider diagnostics out of the customer UI.
        for item in state.get('activities', []):
            if item.get('state') == 'running':
                item['state'] = 'error'
        store.save(run_id, lease, state, 'FAILED', error='EL gặp gián đoạn khi xử lý. Tiến độ đã lưu; bạn có thể tiếp tục.')
    finally:
        _sink.reset(token)
        pulse.cancel()
        await asyncio.gather(pulse, return_exceptions=True)
