"""Bounded recovery of missing device, branch tag and connected-load evidence."""
import json
from app.services.ai.response_parser import ResponseParserService
from app.services.ai.el_progress import run_step


def evidence_gaps(device, box):
    gaps = []
    if not box or box.get('verified') is not True:
        gaps.append('ký hiệu và nhãn thiết bị')
    if device.tag and (not box or not box.get('tag_box_2d') or box.get('tag_matches') is not True):
        gaps.append('nhãn lộ ' + device.tag)
    if device.connected_load and (not box or not box.get('load_box_2d') or box.get('load_verified') is not True):
        gaps.append('phụ tải và quan hệ dây nối')
    return gaps


async def complete_evidence(image, image_path, devices, audited, call_image, *, concurrency=1, attempts=2):
    from app.services.ai.device_crop_audit import audit_device_previews
    boxes = {str(box['device_id']): box for box in audited.get('boxes', [])}
    for attempt in range(attempts):
        missing = [{'device_id': str(i), 'name': d.name, 'tag': d.tag, 'spec': d.spec,
                    'connected_load': d.connected_load, 'missing': evidence_gaps(d, boxes.get(str(i))),
                    'previous_error': (boxes.get(str(i)) or {}).get('audit_reason')}
                   for i, d in enumerate(devices) if evidence_gaps(d, boxes.get(str(i)))]
        if not missing:
            break
        raw = await run_step('Đang bổ sung minh chứng: ' + ', '.join(str(r['tag'] or r['name']) for r in missing), call_image(image_path,
            'Đọc LẠI ảnh nguồn để hoàn thiện minh chứng bị thiếu. Không sửa danh mục, không tự '
            'suy tag hoặc công năng từ tên lộ. Tìm đủ ký hiệu, nhãn thông số, nhãn tag riêng; '
            'với connected_load phải đọc nhãn tải và lần đúng dây nối từ thiết bị đến tải. '
            'Giữ device_id. Tọa độ [ymin,xmin,ymax,xmax] 0..1000 theo CHÍNH ảnh đầu vào. '
            'Không thấy thì verified=false và ghi reason cụ thể. Trả JSON '
            '{"boxes":[{"device_id":"0","verified":true,"symbol_verified":true,'
            '"symbol_box_2d":[],"text_box_2d":[],"tag_box_2d":[],"load_box_2d":[], '
            '"load_label":"nhãn tải nguyên văn","relationship_evidence":"dây nối quan sát được"}]}.'
            '\nCác dòng cần đọc lại: ' + json.dumps(missing, ensure_ascii=False)), detail=f"{len(missing)} dòng còn thiếu · Lần đọc lại {attempt+1}")
        payload = next((b for b in ResponseParserService.extract_json_blocks(raw)
                        if isinstance(b, dict) and isinstance(b.get('boxes'), list)), {})
        allowed = {row['device_id'] for row in missing}
        payload['boxes'] = [b for b in payload.get('boxes', []) if isinstance(b, dict) and str(b.get('device_id')) in allowed]
        checked = await audit_device_previews(image, call_image, devices, payload, concurrency=concurrency)
        for box in checked.get('boxes', []):
            identity = str(box['device_id'])
            old = boxes.get(identity)
            if box.get('verified') is True or not old or old.get('verified') is not True:
                boxes[identity] = box
    return {'boxes': list(boxes.values())}
