"""Bounded recovery of missing device, branch tag and connected-load evidence."""
import json
import tempfile
from pathlib import Path
from app.services.ai.response_parser import ResponseParserService
from app.services.ai.el_progress import run_step


def evidence_gaps(device, box):
    gaps = []
    if not box or box.get('verified') is not True:
        gaps.append('ký hiệu và nhãn thiết bị')
    branch_tags = ((device.source_observations or {}).get('linked_device') or {}).get('branch_tags')
    if (device.tag or branch_tags) and (not box or not box.get('tag_box_2d') or box.get('tag_matches') is not True):
        gaps.append('nhãn lộ ' + (device.tag or ' / '.join(branch_tags)))
    if device.connected_load and (not box or not box.get('load_box_2d') or box.get('load_verified') is not True):
        gaps.append('phụ tải và quan hệ dây nối')
    return gaps


async def complete_evidence(image, image_path, devices, audited, call_image, *, concurrency=1, attempts=2, cache_scope=None):
    from app.services.ai.device_crop_audit import audit_device_previews
    boxes = {str(box['device_id']): box for box in audited.get('boxes', [])}
    attempted=set()
    for attempt in range(attempts):
        missing = [{'device_id': str(i), 'name': d.name, 'tag': d.tag, 'spec': d.spec,
                    'connected_load': d.connected_load, 'missing': evidence_gaps(d, boxes.get(str(i))),
                    'previous_error': (boxes.get(str(i)) or {}).get('audit_reason')}
                   for i, d in enumerate(devices) if evidence_gaps(d, boxes.get(str(i)))]
        if not missing:
            break
        prompt = (
            'Đọc LẠI ảnh nguồn để hoàn thiện minh chứng bị thiếu. Không sửa danh mục, không tự '
            'suy tag hoặc công năng từ tên lộ. Tìm đủ ký hiệu, nhãn thông số, nhãn tag riêng; '
            'với connected_load phải đọc nhãn tải và lần đúng dây nối từ thiết bị đến tải. '
            'Nếu nhánh dùng tiêu đề thông số chung, xuất text_box_2d riêng cho tiêu đề, '
            'shared_label=true và relationship_evidence chứng minh nhánh thuộc nhóm đó. '
            'Giữ device_id. Tọa độ [ymin,xmin,ymax,xmax] 0..1000 theo CHÍNH ảnh đầu vào. '
            'Không thấy thì verified=false và ghi reason cụ thể. Trả JSON '
            '{"boxes":[{"device_id":"0","verified":true,"symbol_verified":true,'
            '"symbol_box_2d":[],"text_box_2d":[],"tag_box_2d":[],"load_box_2d":[], '
            '"load_label":"nhãn tải nguyên văn","relationship_evidence":"dây nối quan sát được"}]}.'
            'Chữ/ký hiệu có thể đè nhau như nguồn; không cắt bớt nét để tránh nhánh khác. '
            '\nCác dòng cần đọc lại: ' + json.dumps(missing, ensure_ascii=False))
        frame = None
        with tempfile.TemporaryDirectory(prefix='aide_evidence_detail_') as folder:
            read_path = image_path
            anchors = [(boxes.get(r['device_id']) or {}).get('symbol_box_2d') for r in missing]
            if attempt == 0 and all(anchors):
                window = [max(0,min(b[0] for b in anchors)-80), max(0,min(b[1] for b in anchors)-80),
                          min(1000,max(b[2] for b in anchors)+80), min(1000,max(b[3] for b in anchors)+80)]
                if window[2]-window[0] <= 600 and window[3]-window[1] <= 600:
                    left, top = int(window[1]*image.width/1000), int(window[0]*image.height/1000)
                    right, bottom = round(window[3]*image.width/1000), round(window[2]*image.height/1000)
                    if right > left and bottom > top:
                        read_path = str(Path(folder)/'detail.png')
                        image.crop((left,top,right,bottom)).save(read_path)
                        frame = [top*1000/image.height,left*1000/image.width,bottom*1000/image.height,right*1000/image.width]
            signature=json.dumps({'missing':missing,'frame':frame},ensure_ascii=False,sort_keys=True)
            if signature in attempted:break
            attempted.add(signature)
            raw = await run_step('Đang bổ sung minh chứng: ' + ', '.join(str(r['tag'] or r['name']) for r in missing),
                call_image(read_path,prompt), detail=f"{len(missing)} dòng còn thiếu · Lần đọc lại {attempt+1}")
        payload = next((b for b in ResponseParserService.extract_json_blocks(raw)
                        if isinstance(b, dict) and isinstance(b.get('boxes'), list)), {})
        allowed = {row['device_id'] for row in missing}
        payload['boxes'] = [b for b in payload.get('boxes', []) if isinstance(b, dict) and str(b.get('device_id')) in allowed]
        for proposal in payload['boxes']:
            if frame:
                from app.services.ai.regional_takeoff import map_box
                for key in ('box_2d','symbol_box_2d','text_box_2d','tag_box_2d','load_box_2d'):
                    try:proposal[key]=map_box(proposal.get(key),frame)
                    except (TypeError,ValueError,OverflowError):proposal[key]=None
            old = boxes.get(str(proposal.get('device_id'))) or {}
            # A local reread may only repair one part. Keep existing anchors in
            # source coordinates; the combined exported parts are audited again.
            for key in ('symbol_box_2d','text_box_2d','tag_box_2d','load_box_2d',
                        'load_label','relationship_evidence'):
                if not proposal.get(key) and old.get(key):
                    proposal[key] = old[key]
            if old.get('shared_label') is True:
                proposal['shared_label'] = True
            if old.get('source_annotation') == 'shared_rating':
                proposal.update(source_annotation='shared_rating', group_reference_box_2d=old.get('group_reference_box_2d'))
        checked = await audit_device_previews(image, call_image, devices, payload, concurrency=concurrency, cache_scope=cache_scope)
        for box in checked.get('boxes', []):
            identity = str(box['device_id'])
            old = boxes.get(identity)
            if old and old.get('verified') is not True and box.get('verified') is not True:
                box = {**old, **box, **{key:old[key] for key in (
                    'symbol_box_2d','text_box_2d','tag_box_2d','load_box_2d') if old.get(key) and not box.get(key)}}
            if box.get('verified') is True or not old or old.get('verified') is not True:
                boxes[identity] = box
    return {'boxes': list(boxes.values())}
