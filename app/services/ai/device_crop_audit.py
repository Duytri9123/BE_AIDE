"""Audit the exact exported device preview, rather than a different intermediate crop."""
import base64
import asyncio
import io
import json
import os
import tempfile
from collections import Counter
from PIL import Image, ImageDraw, ImageOps
from app.schemas.ai import ExtractedDeviceSchema
from app.services.ai.evidence_crops import evidence_crop_pixels
from app.services.ai.evidence_preview import device_preview
from app.services.ai.response_parser import ResponseParserService


async def audit_device_previews(image, call_image, devices, payload, *, concurrency=1):
    proposals = [r for r in payload.get('boxes', []) if isinstance(r, dict)]
    counts = Counter(str(r.get('device_id')) for r in proposals)
    rows = {}
    for row in proposals:
        identity = str(row.get('device_id'))
        if counts[identity] != 1 or not identity.isdigit() or int(identity) >= len(devices):
            continue
        row = dict(row)
        try:
            for key in ('symbol_box_2d', 'text_box_2d', 'tag_box_2d', 'load_box_2d'):
                row[key] = ExtractedDeviceSchema.normalize_evidence_box(row.get(key))
        except (ValueError, TypeError, OverflowError):
            continue
        if row.get('verified') is not True or row.get('symbol_verified') is not True:
            continue
        if not row.get('symbol_box_2d') or not row.get('text_box_2d'):
            continue
        rows[identity] = row
    identities = list(rows)
    semaphore = asyncio.Semaphore(max(1, min(concurrency, 2)))

    async def audit_batch(batch):
        async with semaphore:
            sheet = Image.new('RGB', (1200, 270*len(batch)), 'white')
            draw = ImageDraw.Draw(sheet)
            requests = []
            for local, identity in enumerate(batch):
                row = rows[identity]
                previews = device_preview(image, row, tight=True)
                if not previews:
                    row['verified'] = False
                    continue
                # Audit every exported part for this device, including distant tag/text crops.
                tile_height = max(1, 225 // len(previews))
                for part_index, part in enumerate(previews):
                    data = base64.b64decode(part['evidence_image'].split(',')[1])
                    preview = Image.open(io.BytesIO(data)).convert('RGB')
                    preview = ImageOps.contain(preview, (570, tile_height), Image.Resampling.LANCZOS)
                    sheet.paste(preview, (10, local*270+25+part_index*tile_height))
                draw.text((10, local*270+5), 'ID '+identity+' - EXPORTED CROP', fill='black')
                parts = [row[k] for k in ('symbol_box_2d', 'text_box_2d', 'tag_box_2d', 'load_box_2d') if row.get(k)]
                box = [min(b[0] for b in parts), min(b[1] for b in parts),
                       max(b[2] for b in parts), max(b[3] for b in parts)]
                context = [max(0, box[0]-25), max(0, box[1]-25), min(1000, box[2]+25), min(1000, box[3]+25)]
                pixels = evidence_crop_pixels(context, *image.size)
                if pixels:
                    detail = ImageOps.contain(image.crop(pixels), (570, 235), Image.Resampling.LANCZOS)
                    sheet.paste(detail, (610, local*270+25))
                device = devices[int(identity)]
                requests.append({'device_id': identity, 'name': device.name, 'tag': device.tag, 'spec': device.spec, 'quantity': device.quantity, 'unit': device.unit, 'connected_load': device.connected_load, 'load_label': row.get('load_label'), 'relationship_evidence': row.get('relationship_evidence')})
                row['verified'] = False
            if not requests:
                return
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as handle:
                path = handle.name
            try:
                sheet.save(path)
                raw = await call_image(path,
                    'Kiểm tra ĐỘC LẬP ảnh cắt sẽ hiển thị cho người dùng. Cột trái là CHÍNH ẢNH XUẤT RA, '
                    'cột phải là ngữ cảnh nguồn. Nếu cột trái có nhiều ảnh, đó là các ảnh riêng của cùng ID; kiểm đủ tất cả ảnh.  Không tin danh mục ứng viên. Mỗi ID: ảnh trái phải có '
                    'đủ ký hiệu điện thực và nhãn của đúng thiết bị, đúng nhánh. Cho phép nhãn và ký hiệu '
                    'của CHÍNH thiết bị cùng nằm trong ảnh; isolated=false chỉ khi lẫn thiết bị/nhãn khác '
                    'gây nhầm nhận diện. Với dòng có quantity>1, ảnh có thể bao đúng nhóm thiết bị cùng loại '
                    'theo số lượng đã khai báo (ví dụ ba ampe kế); không bác bỏ chỉ vì có nhiều phần tử '
                    'của CHÍNH dòng đó. Phải kiểm tra nhóm khớp số lượng/nhãn, không chấp nhận ảnh một '
                    'phần tử để chứng minh cả nhóm nếu nguồn không ghi hệ số. Dây nối đi qua không phải thiết bị khác. Kiểm tra mất nét/tiếp điểm '
                    'hoặc chữ số do cắt mép. Không lấy chữ từ ngữ cảnh để bù phần thiếu của ảnh xuất ra. '
                    'Nếu có tag, kiểm tra ảnh xuất có đúng NHÃN TAG; không lấy tag từ danh mục để xác nhận. '
                    'Nếu có tải, kiểm tra nhãn tải và quan hệ dây nối trong ảnh ngữ cảnh bên phải; '
                    'load_matches và relationship_verified chỉ true khi thấy đúng nhãn và lần được dây. '
                    'Không sửa danh mục, không tự điền thông số không thấy. Trả JSON '
                    '{"checks":[{"device_id":"0","matches":true,"symbol_complete":true,'
                    '"label_complete":true,"isolated":true,"tag_matches":true,"load_matches":true,"relationship_verified":true,"observed":"chữ/hình thực thấy",'
                    '"reason":"lỗi cụ thể nếu có"}]}.\n' + json.dumps(requests, ensure_ascii=False))
                blocks = ResponseParserService.extract_json_blocks(raw)
                checks = next((b['checks'] for b in blocks if isinstance(b, dict) and isinstance(b.get('checks'), list)), [])
                for identity in batch:
                    matches = [c for c in checks if isinstance(c, dict) and str(c.get('device_id')) == identity]
                    if len(matches) != 1:
                        continue
                    check = matches[0]
                    rows[identity]['verified'] = all(check.get(k) is True
                        for k in ('matches', 'symbol_complete', 'label_complete', 'isolated'))
                    device = devices[int(identity)]
                    rows[identity]['tag_matches'] = check.get('tag_matches') is True
                    if device.tag and (not rows[identity].get('tag_box_2d') or check.get('tag_matches') is not True):
                        rows[identity]['verified'] = False
                    rows[identity]['load_verified'] = bool(rows[identity].get('load_box_2d') and
                        rows[identity].get('relationship_evidence') and check.get('load_matches') is True and
                        check.get('relationship_verified') is True)
                    rows[identity]['audit_observed'] = str(check.get('observed') or '')
                    rows[identity]['audit_reason'] = str(check.get('reason') or '')
            finally:
                os.remove(path)

    await asyncio.gather(*(audit_batch(identities[start:start+6])
                           for start in range(0, len(identities), 6)))
    return {'boxes': list(rows.values())}
