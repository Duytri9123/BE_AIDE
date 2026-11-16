"""Drawing-region discovery and explicit, source-bound panel confirmation."""
import asyncio
import base64
import hashlib
import hmac
import json
import tempfile
import time
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from app.core.config import settings
from app.models.project_file import ProjectFile
from app.services.ai.connection_pool import ConnectionPoolService
from app.services.ai.response_parser import ResponseParserService
from app.services.ai.vision_analyzer import VisionAnalyzerService
from app.services.ingestion.cad_source_evidence import validate_region

_DISCOVERY_CACHE = {}


def discovery_response(panels, project_id):
    # Refresh signatures on every response; a cached preview is never approval.
    result = [{**p, 'scope_token': sign_scope(p, project_id)} for p in panels]
    return {'reply': ('Đã xác định vùng bản vẽ. Kiểm tra ảnh khoanh đỏ và xác nhận các tủ cần bóc tách.' if result
                     else 'Chưa nhận diện rõ vùng tủ. Hãy chọn trang hoặc cung cấp ảnh phóng to vùng cần bóc; chưa có thiết bị nào được lưu.'),
            'requires_confirmation': True, 'detected_panels': result}


def sign_scope(panel, project_id):
    data = {k: panel.get(k) for k in ('panel_code', 'source_file_id', 'source_page', 'source_region')}
    data.update(project_id=project_id, expires=int(time.time()) + 3600)
    payload = base64.urlsafe_b64encode(json.dumps(data, sort_keys=True).encode()).decode()
    signature = hmac.new(settings.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return payload + '.' + signature


def confirmed_scope(context, project_id):
    scope = context.get('takeoff_scope')
    if scope is None:
        return []
    if not isinstance(scope, list) or not 1 <= len(scope) <= 64:
        raise HTTPException(422, 'Chọn ít nhất một vùng tủ để xác nhận.')
    panels = []
    identities = set()
    for selected in scope:
        try:
            payload, signature = selected['scope_token'].rsplit('.', 1)
            expected = hmac.new(settings.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, signature):
                raise ValueError('signature')
            panel = json.loads(base64.urlsafe_b64decode(payload))
            if panel['project_id'] != project_id or panel['expires'] < time.time():
                raise ValueError('expired')
            if panel['source_file_id'] not in context.get('file_ids', []):
                raise ValueError('file')
            validate_region(panel['source_region'])
            identity = (panel['source_file_id'], panel.get('source_page'), panel['panel_code'])
            if identity in identities:
                raise ValueError('duplicate')
            identities.add(identity)
            panels.append(panel)
        except (KeyError, TypeError, ValueError, AttributeError):
            raise HTTPException(422, 'Vùng xác nhận đã hết hạn hoặc không thuộc nguồn đang chọn. Đọc lại vùng tủ.')
    return panels


async def discover_panels(db, project_id, file_ids):
    from app.services.ai.requirement_analysis import render_pdf_page
    from app.services.ingestion.cad_parser import CadParserService
    from app.services.ingestion.cad_visual_source import render_schematic_source
    from PIL import Image, ImageDraw
    import pymupdf

    if not isinstance(file_ids, list) or not 1 <= len(file_ids) <= 8 or any(type(i) is not int or i <= 0 for i in file_ids):
        raise HTTPException(422, 'Chọn tối đa 8 file nguồn để xác định vùng tủ.')
    files = (await db.execute(select(ProjectFile).where(ProjectFile.project_id == project_id,
                          ProjectFile.id.in_(file_ids)))).scalars().all()
    if {f.id for f in files} != set(file_ids):
        raise HTTPException(404, 'File nguồn không thuộc dự án này.')
    fingerprints = []
    for file in files:
        path = Path(file.file_path)
        if not path.is_file():
            raise HTTPException(404, 'Không tìm thấy file nguồn: ' + file.filename)
        stat = path.stat()
        fingerprints.append((file.id, str(path.resolve()), stat.st_size, stat.st_mtime_ns))
    cache_key = (project_id, tuple(sorted(fingerprints)))
    cached = _DISCOVERY_CACHE.get(cache_key)
    if cached and time.monotonic() - cached[0] < 600:
        return discovery_response(cached[1], project_id)
    connections = await ConnectionPoolService.get_ordered_connections(db)
    if not connections:
        raise HTTPException(503, 'Chưa có kết nối AI để xác định vùng tủ.')
    panels = []
    with tempfile.TemporaryDirectory(prefix='aide_scope_') as tmp:
        for file in files:
            path = Path(file.file_path)
            if not path.is_file():
                raise HTTPException(404, 'Không tìm thấy file nguồn: ' + file.filename)
            pages = []
            cad_bounds = None
            if path.suffix.lower() == '.pdf':
                with pymupdf.open(path) as pdf:
                    if len(pdf) > 8:
                        raise HTTPException(422, 'PDF trên 8 trang: hãy chọn phạm vi trang hoặc tách phần bản vẽ cần bóc.')
                    count = len(pdf)
                for n in range(1, count + 1):
                    image = Path(tmp) / f'{file.id}-{n}.png'
                    await asyncio.to_thread(render_pdf_page, path, n, image)
                    pages.append((image, n))
            elif path.suffix.lower() in ('.dwg', '.dxf'):
                from app.services.ingestion.cad_source_evidence import cad_evidence
                analysis = await asyncio.to_thread(CadParserService.prepare_analysis_path, str(path))
                cad_bounds = (await asyncio.to_thread(cad_evidence, analysis)).get('bounds')
                image = await asyncio.to_thread(render_schematic_source, analysis)
                if image:
                    pages.append((Path(image), None))
            elif path.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp'):
                pages.append((path, 1))
            for image, number in pages:
                raw, _ = await ConnectionPoolService.call_with_fallback(
                    db=db, connections=connections, call_fn=VisionAnalyzerService.analyze_image,
                    image_path=str(image), prompt='Chỉ xác định CÁC VÙNG SƠ ĐỒ TỦ ĐIỆN trong ảnh. Chưa bóc thiết bị, chưa tra bảng giá. '
                    'Mỗi tủ: mã đọc được, tên và source_region=[trái,trên,phải,dưới] chuẩn hóa 0..1 bao trọn sơ đồ tủ, gồm đầu vào/đo lường/mọi lộ ra. '
                    'Không dùng khung tên, bảng tải, mặt bằng làm tủ. Nếu tên không đọc rõ dùng VUNG-1... và ghi chưa rõ. '
                    'Không gộp các sơ đồ tầng khác nhau. Trả JSON {"panels":[{"panel_code":"...","panel_name":"...","source_region":[0,0,1,1],"position":"vị trí trên trang"}]}.')
                obj = next((v for v in ResponseParserService.extract_json_blocks(raw) if isinstance(v, dict) and isinstance(v.get('panels'), list)), {})
                for item in obj.get('panels', [])[:64]:
                    try:
                        region = validate_region(item.get('source_region'))
                        if region is None:
                            continue
                        code = str(item['panel_code']).strip()[:100]
                        if not code:
                            continue
                    except (ValueError, KeyError, TypeError):
                        continue
                    panel = dict(panel_code=code, panel_name=str(item.get('panel_name') or code)[:200],
                        source_file_id=file.id, file_name=file.filename, source_page=number,
                        source_region=region, position=str(item.get('position') or '')[:300])
                    if cad_bounds:
                        from app.services.ingestion.cad_source_evidence import region_world
                        x1,y1,x2,y2 = region_world(cad_bounds, region)
                        panel['cad_bounds'] = {'x_min':x1,'y_min':y1,'x_max':x2,'y_max':y2,'coordinate_space':'cad_world'}
                    with Image.open(image) as original:
                        preview = original.convert('RGB'); preview.thumbnail((1400, 1400))
                        w, h = preview.size
                        ImageDraw.Draw(preview).rectangle((region[0]*w,region[1]*h,region[2]*w,region[3]*h), outline='red', width=4)
                        import io
                        buf=io.BytesIO();preview.save(buf,format='JPEG',quality=82)
                        panel['preview_image']='data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode()
                    panel['scope_token']=sign_scope(panel, project_id)
                    panels.append(panel)
    if panels:
        if len(_DISCOVERY_CACHE) >= 8:
            _DISCOVERY_CACHE.pop(next(iter(_DISCOVERY_CACHE)))
        _DISCOVERY_CACHE[cache_key] = (time.monotonic(), panels)
    return discovery_response(panels, project_id)
