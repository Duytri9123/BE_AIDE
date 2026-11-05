"""Discover real business APIs as project-bound EL tools, not arbitrary HTTP access."""
import hashlib
import json
import re
import unicodedata
from urllib.parse import quote

from fastapi import HTTPException
from sqlalchemy import select

READ_PREFIXES = ('equipment-library', 'cad-library', 'cabinet-templates', 'curated-library',
                 'device-catalog', 'device-library', 'catalog-prices', 'user-library')
ANALYSIS_READS = ('device-details', 'device-recommendations', 'manufacturer-information')


def plain(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower().replace('đ', 'd')) if not unicodedata.combining(c))


def permits_write(message, label=''):
    text = re.sub(r'\bban ve\b', 'drawing', plain(message))
    if re.search(r'\b(?:chi phan tich|chi doc|(?:chua|khong|dung)\s+(?:(?:can|tu dong|tu)\s+)?(?:ve|tao|doi|sua|cap nhat))\b', text):
        return False
    return bool(re.search(r'\b(?:ve|tao|xuat|luu|boc tach|boc|tach|cap nhat|chinh sua|sua lai|sua|doi ten|tinh|lap bao gia|bao gia|chen|di chuyen|xoay|sao chep|them)\b', text))


def permits_tool(tool, message):
    text = plain(message)
    path = tool.get('path', '')
    if any('/' + prefix in path for prefix in READ_PREFIXES) or 'search_aide_device_catalog' in tool.get('name', ''):
        if re.search(r'\b(?:khong|chua|dung)\s+(?:can\s+)?(?:doi chieu|tra cuu|so sanh|tim|dung\s+thu\s+vien|xem\s+catalog)', text):
            return False
        return True
    if not tool.get('writes'):
        return True
    if not permits_write(message):
        return False
    if path.endswith(('/analyze/start', '/analyze/async-start')):
        return any(k in text for k in ('boc tach', 'boc', 'tach', 'analyze', 'sld', 'so do', 'thiet bi'))
    if 'generate-quotation-cad' in path:
        edit_text = re.sub(r'\bban ve\b', 'drawing', text)
        return bool(re.search(r'\bve\b|tao.*\b(?:cad|dxf|drawing)\b', edit_text))
    if '/projects/' in path:
        return bool(re.search(r'doi ten|(?:cap nhat|sua).*du an', text))
    if tool.get('kind') == 'cad':
        edit_text = re.sub(r'\bban ve\b', 'drawing', text)
        return bool(re.search(r'(?:^|\b(?:hay|vui long|giup toi|toi muon|toi can|can|va|roi|sau do|ban|el)\s+)(?:ve|chen|di chuyen|xoay|sao chep|chinh sua|sua lai|cap nhat|them)\b', edit_text))
    if '/export/' in path and not path.endswith('/design-cost'):
        return bool(re.search(r'\b(?:tao|xuat|luu|lap bao gia)\b', text))
    return True


def resolve_schema(value, spec, depth=0):
    if depth > 6:
        return {}
    if isinstance(value, list):
        return [resolve_schema(item, spec, depth + 1) for item in value]
    if not isinstance(value, dict):
        return value
    if '$ref' in value:
        target = spec
        for part in value['$ref'].removeprefix('#/').split('/'):
            target = target.get(part, {})
        return resolve_schema(target, spec, depth + 1)
    return {key: resolve_schema(item, spec, depth + 1) for key, item in value.items()
            if key not in {'examples', 'example', 'default'}}


def api_tools(app):
    spec = app.openapi()
    tools = {}
    for full_path, methods in spec['paths'].items():
        path = full_path.removeprefix('/api/v1/')
        for method, operation in methods.items():
            if method not in {'get', 'post', 'put', 'patch'}:
                continue
            root = path.split('/')[0]
            library_read = root in READ_PREFIXES and method == 'get'
            project_read = bool(re.fullmatch(r'projects/\{id\}(?:/files)?', path)) and method == 'get'
            analysis_read = (bool(re.fullmatch(r'analyze/project/\{project_id\}/(?:latest|sessions)', path))
                             or bool(re.fullmatch(r'analyze/(?:iteration|task)/\{\w+\}', path))) and method == 'get'
            computed = path.startswith('bom/') or path in {'analyze/' + name for name in ANALYSIS_READS}
            action = path in {'analyze/start', 'analyze/async-start', 'analyze/generate-quotation-cad',
                              'analyze/refine', 'analyze/finalize', 'export/design-cost'}
            action = action or (path.startswith('export/') and method == 'post')
            action = action or (bool(re.fullmatch(r'projects/\{id\}', path)) and method in {'put', 'patch'})
            if not (library_read or project_read or analysis_read or computed or action):
                continue
            if 'multipart/form-data' in operation.get('requestBody', {}).get('content', {}):
                continue
            groups = {}
            bound = {}
            for parameter in operation.get('parameters', []):
                location, name = parameter.get('in'), parameter.get('name')
                if location not in {'path', 'query'}:
                    continue
                if name == 'project_id' or (root == 'projects' and location == 'path' and name == 'id'):
                    bound[name] = location
                    continue
                group = groups.setdefault(location, {'type': 'object', 'properties': {}, 'required': []})
                group['properties'][name] = resolve_schema(parameter.get('schema', {}), spec)
                if parameter.get('required'):
                    group['required'].append(name)
            body = operation.get('requestBody', {}).get('content', {}).get('application/json', {}).get('schema')
            if body:
                groups['body'] = resolve_schema(body, spec)
                groups['body'].get('properties', {}).pop('project_id', None)
                groups['body']['required'] = [key for key in groups['body'].get('required', []) if key != 'project_id']
            name = 'api_' + operation.get('operationId', root)[:44] + '_' + hashlib.sha256((method + full_path).encode()).hexdigest()[:6]
            tools[name] = {'name': name, 'label': operation.get('summary') or f'{method.upper()} {path}',
                'description': (operation.get('description') or operation.get('summary') or path)[:450],
                'input_schema': {'type': 'object', 'properties': groups, 'additionalProperties': False},
                'kind': 'api', 'writes': bool(action), 'method': method.upper(), 'path': full_path, 'bound': bound}
    return tools


async def check_resource_scope(db, project_id, parameters):
    from app.models.project_file import ProjectFile
    from app.models.analysis_iteration import AnalysisIteration
    from app.models.conversation_session import ConversationSession
    for name in ('file_id', 'iteration_id', 'session_id'):
        value = parameters.get(name)
        if value is None:
            continue
        if name == 'file_id':
            statement = select(ProjectFile.id).where(ProjectFile.id == value, ProjectFile.project_id == project_id)
        elif name == 'iteration_id':
            statement = select(AnalysisIteration.id).join(ConversationSession,
                ConversationSession.id == AnalysisIteration.session_id).where(
                AnalysisIteration.id == value, ConversationSession.project_id == project_id)
        else:
            statement = select(ConversationSession.id).where(ConversationSession.id == value, ConversationSession.project_id == project_id)
        if (await db.execute(statement)).scalar_one_or_none() is None:
            raise HTTPException(404, 'Tài nguyên của tool không thuộc dự án đang mở.')
    if parameters.get('task_id'):
        from app.services import job_queue
        with job_queue.sync_client() as client:
            info = client.hgetall(job_queue.PREFIX + str(parameters['task_id']))
        if info.get('project_id') != str(project_id):
            raise HTTPException(404, 'Tác vụ không thuộc dự án đang mở.')


async def execute_api_tool(app, db, user_id, project_id, tool, arguments, headers):
    import httpx
    arguments = arguments or {}
    path_args = dict(arguments.get('path') or {})
    query = dict(arguments.get('query') or {})
    body = dict(arguments.get('body') or {})
    for group in (path_args, query, body):
        if 'project_id' in group:
            group['project_id'] = project_id
        if 'user_id' in group:
            group['user_id'] = user_id
        scoped = {key: value for key, value in group.items()
                  if not (key == 'file_id' and '/user-library/' in tool['path'])}
        await check_resource_scope(db, project_id, scoped)
    for name, location in tool['bound'].items():
        (path_args if location == 'path' else query)[name] = project_id
    if 'body' in tool['input_schema']['properties']:
        body['project_id'] = project_id
    path = tool['path']
    for name in re.findall(r'\{(\w+)\}', path):
        if name not in path_args:
            raise HTTPException(422, f'Tool thiếu tham số {name}.')
        path = path.replace('{' + name + '}', quote(str(path_args[name]), safe=''))
    # Only known local endpoints; the model cannot supply a host or raw URL.
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://127.0.0.1',
                                 timeout=180, follow_redirects=False) as client:
        response = await client.request(tool['method'], path, params=query,
            json=body if tool['method'] != 'GET' else None, headers=headers)
        if not response.is_success:
            try:
                detail = response.json().get('detail', 'Tool không hoàn tất.')
            except ValueError:
                detail = f'Tool trả HTTP {response.status_code}.'
            return {'ok': False, 'status_code': response.status_code, 'detail': str(detail)[:1200]}
        if 'json' not in response.headers.get('content-type', ''):
            if tool['method'] != 'GET':
                from email.message import Message
                from pathlib import Path
                import uuid
                from app.core.config import settings
                from app.models.project_file import ProjectFile
                header = Message()
                header['content-disposition'] = response.headers.get('content-disposition', '')
                filename = Path(header.get_filename() or 'EL-result.bin').name
                folder = Path(settings.EXPORT_DIR) / 'el' / str(project_id)
                folder.mkdir(parents=True, exist_ok=True)
                target = folder / (uuid.uuid4().hex + '-' + filename)
                target.write_bytes(response.content)
                await db.rollback()
                record = ProjectFile(project_id=project_id, filename=filename, file_path=str(target),
                    file_type=response.headers.get('content-type', 'application/octet-stream'),
                    file_size=len(response.content), is_generated=True)
                db.add(record)
                await db.commit()
                await db.refresh(record)
                return {'ok': True, 'artifact_url': f'/api/v1/projects/{project_id}/files/{record.id}/download',
                        'filename': filename, 'message': 'Kết quả tool đã được lưu vào dự án.'}
            return {'ok': True, 'artifact_url': path, 'content_type': response.headers.get('content-type'),
                    'message': 'Tool đã trả file; dùng đường dẫn có xác thực để mở hoặc tải.'}
        payload = response.json()
        def bounded(value):
            if isinstance(value, dict):
                return {key: bounded(item) for key, item in value.items()
                        if key not in {'evidence_image', 'panel_images', 'evidence_overviews', 'api_key', 'access_token'}}
            if isinstance(value, list):
                return [bounded(item) for item in value[:50]]
            if isinstance(value, str) and len(value) > 8000:
                return value[:8000] + ' [truncated]'
            return value
        return {'ok': True, 'data': bounded(payload), 'limits': 'Danh sách tool được giới hạn 50 dòng; dùng phân trang khi cần.'}
