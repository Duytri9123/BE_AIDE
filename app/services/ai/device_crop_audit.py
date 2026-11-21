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
from app.services.ai.el_progress import run_step
from app.core.exceptions import AIVisionError
from app.services.ai.material_note_evidence import material_annotation


async def audit_device_previews(image, call_image, devices, payload, *, concurrency=1, cache_scope=None, batch_size=4):
    proposals = [r for r in payload.get('boxes', []) if isinstance(r, dict)]
    counts = Counter(str(r.get('device_id')) for r in proposals)
    rows = {}
    for row in proposals:
        identity = str(row.get('device_id'))
        if counts[identity] != 1 or not identity.isdigit() or int(identity) >= len(devices):
            continue
        row = dict(row)
        device=devices[int(identity)]
        branch_tags=((getattr(device,'source_observations',None) or {}).get('linked_device') or {}).get('branch_tags')
        if not device.tag and not branch_tags:
            row['tag_box_2d']=None
        note=(getattr(device,'source_observations',None) or {}).get('material_annotation') or material_annotation(
            {'name':device.name,'category':getattr(device,'category',''),'quantity':device.quantity,
             'observed_text':(getattr(device,'source_observations',None) or {}).get('observed_text')})
        if note:
            row['evidence_kind']='material_note'
            row['material_annotation']=note
            row['symbol_box_2d']=row.get('text_box_2d')
        try:
            for key in ('symbol_box_2d', 'text_box_2d', 'tag_box_2d', 'load_box_2d', 'group_reference_box_2d'):
                row[key] = ExtractedDeviceSchema.normalize_evidence_box(row.get(key))
        except (ValueError, TypeError, OverflowError):
            continue
        # Missing proposal flags must not prevent an independent pixel check.
        # An explicit rejection still requires relocation before checking again.
        if row.get('verified') is False or row.get('symbol_verified') is False and not note or not row.get('symbol_box_2d') or not row.get('text_box_2d'):
            row['verified'] = False
            row['audit_reason'] = row.get('reason') or 'Vị trí đề xuất chưa đủ ký hiệu và nhãn để kiểm chứng.'
            rows[identity] = row
            continue
        row.update(verified=True, symbol_verified=True)
        rows[identity] = row
    # Reused text coordinates are shared-header claims even if the model omitted
    # the flag. They still need an independent branch/group relationship check.
    for identity, row in rows.items():
        if row.get('text_box_2d') and any(
                other_id != identity and other.get('text_box_2d') == row['text_box_2d']
                and other.get('symbol_box_2d') != row.get('symbol_box_2d')
                for other_id, other in rows.items()):
            row['shared_label'] = True
    from app.services.ai.audit_checkpoint import AuditCheckpoint
    checkpoint = AuditCheckpoint(image, cache_scope)
    identities = []
    for identity, row in rows.items():
        if row.get('verified') is True:
            cached = await checkpoint.get(identity, devices[int(identity)], row)
            if cached is not None:
                rows[identity] = cached
            else:
                identities.append(identity)
    semaphore = asyncio.Semaphore(max(1, min(concurrency, 6)))
    retryable_batches = []

    async def audit_batch(batch, *, retry=False):
        async with semaphore:
            sheet = Image.new('RGB', (2400, 900*len(batch)), 'white')
            draw = ImageDraw.Draw(sheet)
            requests = []
            for local, identity in enumerate(batch):
                row = rows[identity]
                device = devices[int(identity)]
                proposed_preview={**row,'load_verified':bool(device.connected_load and row.get('load_box_2d') and row.get('relationship_evidence'))}
                previews = device_preview(image, proposed_preview, tight=True)
                if not previews:
                    row['verified'] = False
                    continue
                # Audit every exported part for this device, including distant tag/text crops.
                tile_height = max(1, 825 // ((len(previews)+1)//2))
                exported_parts = []
                for part_index, part in enumerate(previews):
                    data = base64.b64decode(part['evidence_image'].split(',')[1])
                    preview = Image.open(io.BytesIO(data)).convert('RGB')
                    preview = ImageOps.contain(preview, (740, max(1, tile_height-18)), Image.Resampling.LANCZOS)
                    tile_x, tile_y = 10+(part_index%2)*760, local*900+35+(part_index//2)*tile_height
                    keys=part.get('source_parts') or []
                    role = ('CONTEXT' if part.get('kind')=='relationship' else 'LOAD' if part.get('kind')=='load'
                        else 'MATERIAL_NOTE' if row.get('evidence_kind')=='material_note'
                        else 'LABELED_BLOCK' if 'symbol_box_2d' in keys and row.get('source_annotation') in {'adjacent_control_functions','native_control_label'}
                        else 'SYMBOL' if 'symbol_box_2d' in keys else 'TAG' if 'tag_box_2d' in keys else 'RATING')
                    draw.text((tile_x, tile_y), f'ID {identity} / PART {part_index} / {role}', fill='black')
                    sheet.paste(preview, (tile_x, tile_y+18))
                    exported_parts.append({'part': part_index, 'role': role, 'label': part.get('label')})
                draw.text((10, local*900+5), 'ID '+identity+' - EXPORTED CROP', fill='black')
                draw.text((1570,local*900+5),'TARGET SOURCE / RED BOX',fill='black')
                parts = [row[k] for k in ('symbol_box_2d', 'text_box_2d', 'tag_box_2d', 'load_box_2d') if row.get(k)]
                box = [min(b[0] for b in parts), min(b[1] for b in parts),
                       max(b[2] for b in parts), max(b[3] for b in parts)]
                context = [max(0, box[0]-25), max(0, box[1]-25), min(1000, box[2]+25), min(1000, box[3]+25)]
                pixels = evidence_crop_pixels(context, *image.size)
                if pixels:
                    draw.text((1570,local*900+450),'TARGET WIRE / LOAD CONTEXT',fill='black')
                    detail = ImageOps.contain(image.crop(pixels), (820, 410), Image.Resampling.LANCZOS)
                    sheet.paste(detail, (1570, local*900+465))
                # A distant vertical load label must not shrink the source glyph
                # to a few pixels. Give the verifier a separate local source view.
                symbol = row['symbol_box_2d']
                near = [max(0, symbol[0]-35), max(0, symbol[1]-35),
                        min(1000, symbol[2]+35), min(1000, symbol[3]+35)]
                near_pixels = evidence_crop_pixels(near, *image.size)
                if near_pixels:
                    closeup = image.crop(near_pixels)
                    detail = ImageOps.contain(closeup, (820, 220 if row.get('group_reference_box_2d') else 410), Image.Resampling.LANCZOS)
                    sx, sy = detail.width/closeup.width, detail.height/closeup.height
                    outline = [(symbol[1]*image.width/1000-near_pixels[0])*sx,
                               (symbol[0]*image.height/1000-near_pixels[1])*sy,
                               (symbol[3]*image.width/1000-near_pixels[0])*sx,
                               (symbol[2]*image.height/1000-near_pixels[1])*sy]
                    ImageDraw.Draw(detail).rectangle(outline, outline='red', width=2)
                    sheet.paste(detail, (1570, local*900+35))
                if row.get('audit_comparison_box_2d') or row.get('group_reference_box_2d'):
                    reference = evidence_crop_pixels(row.get('audit_comparison_box_2d') or row['group_reference_box_2d'], *image.size)
                    if reference:
                        caption='OTHER GROUP / COMPARISON ONLY / NOT TARGET' if row.get('audit_comparison_box_2d') else 'TARGET SHARED HEADING / GROUP'
                        draw.text((1570,local*900+270),caption,fill='black')
                        detail = ImageOps.contain(image.crop(reference), (820, 150), Image.Resampling.LANCZOS)
                        sheet.paste(detail, (1570, local*900+290))
                device = devices[int(identity)]
                requests.append({'device_id': identity, 'shared_label': row.get('shared_label') is True, 'name': device.name, 'tag': device.tag, 'spec': device.spec, 'in_a':getattr(device,'in_a',None),'poles':getattr(device,'poles',None),'icu_ka':getattr(device,'icu_ka',None), 'quantity': device.quantity, 'unit': device.unit, 'drawing_quantity': getattr(device,'drawing_quantity',None), 'quantity_basis': getattr(device,'quantity_basis',None), 'connected_load': device.connected_load, 'load_label': row.get('load_label'), 'relationship_evidence': row.get('relationship_evidence')})
                requests[-1]['exported_parts'] = exported_parts
                requests[-1]['linked_device'] = (getattr(device,'source_observations',None) or {}).get('linked_device')
                requests[-1]['source_annotation'] = row.get('source_annotation')
                requests[-1]['has_comparison_reference']=bool(row.get('audit_comparison_box_2d'))
                requests[-1]['material_annotation']=row.get('material_annotation')
                requests[-1]['quantity_review']=getattr(device,'quantity_review',None)
                row['verified'] = False
            if not requests:
                return
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as handle:
                path = handle.name
            try:
                sheet.save(path)
                raw = await run_step('Đang đối chiếu ảnh và dây nối: ' + ', '.join(str(r['tag'] or r['name']) for r in requests), call_image(path,
                    'Kiểm tra ĐỘC LẬP ảnh cắt sẽ hiển thị cho người dùng. Cột trái là CHÍNH ẢNH XUẤT RA, '
                    'cột phải trên là ảnh nguồn phóng to quanh ký hiệu (khung đỏ chỉ vị trí ứng viên), '
                    'cột phải dưới là ngữ cảnh dây/nhãn tải. Khung đỏ không phải nét thiết bị. '
                    'Vùng trái mỗi ID là các ảnh xuất riêng trong lưới hai cột. Kiểm đủ tất cả ảnh. '
                    'Mỗi PART có vai trò trong exported_parts: SYMBOL chứa ký hiệu; RATING chỉ chứa nhãn thông số; '
                    'TAG chỉ chứa mã lộ. RATING và TAG không cần chứa ký hiệu điện. MATERIAL_NOTE là ghi chú vật tư. '
                    'LABELED_BLOCK là chính ô khung có chữ Contactor/24H/DOL thực vẽ, được dùng làm ký hiệu '
                    'của bộ phận trên sơ đồ này; kiểm đầy đủ ô và chữ, không bắt có thêm tiếp điểm/cuộn dây '
                    'chuẩn ngoài ô khi nguồn không vẽ. Aptomat thượng nguồn không phải ký hiệu/định mức của ô này. '
                    'LOAD là nhãn tải; CONTEXT là ảnh liên tục chứng minh nhãn chung/dây nối, được phép '
                    'chứa các nhánh bên cạnh và lặp lại cùng ký hiệu từ ảnh chi tiết. Không đếm ảnh lặp '
                    'cùng vị trí thành thiết bị khác; không bác isolated chỉ vì ảnh CONTEXT có nhánh khác. '
                    'symbol_complete chỉ kiểm PART SYMBOL hoặc LABELED_BLOCK; không bác bỏ vì PART RATING/TAG không có ký hiệu. '
                    'So ký hiệu trái với đúng ký hiệu trong NGUỒN bên phải; chỉ yêu cầu các nét nguồn thực vẽ. '
                    'Ảnh nguồn có thể có chữ/ký hiệu/vị trí chồng lên nhau. Không yêu cầu tách chúng '
                    'hoặc bác ảnh chỉ vì có chữ/thiết bị khác đè vào. Khi chồng lấn thực sự có trên '
                    'nguồn, source_overlap=true; identity_unambiguous=true chỉ khi vẫn xác định rõ '
                    'đúng thiết bị, đủ nét/nhãn và đúng tag/dây, không mượn thông số của nhánh khác. '
                    'isolated không phải điều kiện bắt buộc: vùng chứng minh có thể chứa chữ/ký hiệu '
                    'ngay bên cạnh hoặc dùng chung, miễn identity_unambiguous=true. '
                    'Không suy thêm cực theo catalog. Không tin danh mục ứng viên. Mỗi ID: ảnh trái phải có '
                    'đủ ký hiệu điện thực và nhãn của đúng thiết bị, đúng nhánh. Cho phép nhãn và ký hiệu '
                    'của CHÍNH thiết bị cùng nằm trong ảnh; isolated=false chỉ khi lẫn thiết bị/nhãn khác '
                    'gây nhầm nhận diện. Nếu nguồn thực sự không có nhãn/thông số riêng và dòng không khẳng định '
                    'thông số ấy (ví dụ CT chưa ghi tỷ số), text_box có thể trùng symbol_box; label_complete '
                    'chỉ kiểm phần nguồn/danh mục thực sự khẳng định, không bắt có chữ nguồn vốn không ghi. '
                    'Trong sơ đồ một sợi, một ký hiệu CB có thể đại diện thiết bị nhiều cực (2P/3P/4P); '
                    'kiểm nét ký hiệu so với NGUỒN, không yêu cầu sơ đồ phải vẽ riêng từng cực của thiết bị. '
                    'Với linked_device: các phần tử là cực có liên động của CÙNG thiết bị, quantity=1 '
                    'và drawing_quantity đếm các ký hiệu cực. Kiểm đủ toàn cụm liên động trong ảnh ký hiệu, '
                    'và kiểm mọi branch_tags trong ảnh nhãn; không coi hai nhãn tải là hai thiết bị riêng. '
                    'Với source_annotation=shared_rating, ảnh nguồn tham chiếu giữa cột phải cho thấy '
                    'cùng kiểu đường ngang/mũi tên chạy qua nhiều nhánh hơn số cực ghi trên nhãn. '
                    'Ảnh này chỉ so sánh quy ước nhãn dùng chung trên CÙNG bản vẽ, không mượn định mức '
                    'của nhóm ví dụ cho ứng viên. Kiểm nhãn định mức ứng viên ở PART trái và nguồn ngay quanh ứng viên. '
                    'So mẫu dùng nhãn chung này trước khi kết luận đường ngang là liên động cơ khí. '
                    'Vẫn bác bỏ ký hiệu bị cắt so với nguồn hoặc thông số tự thêm. Với dòng có quantity>1, ảnh có thể bao đúng nhóm thiết bị cùng loại '
                    'Với source_annotation=adjacent_control_functions, Contactor và 24H có hai ô khung kề nhau: '
                    'kiểm đủ khung và chữ của chính ô ứng viên, dùng ảnh tham chiếu để hiểu quan hệ; '
                    'không buộc ảnh ô 24H chứa cả chữ Contactor của ô bên cạnh hoặc ngược lại. '
                    'theo số lượng đã khai báo (ví dụ ba ampe kế); không bác bỏ chỉ vì có nhiều phần tử '
                    'của CHÍNH dòng đó. Phải kiểm tra nhóm khớp số lượng/nhãn, không chấp nhận ảnh một '
                    'phần tử để chứng minh cả nhóm nếu nguồn không ghi hệ số và cũng không có căn cứ logic mạch. '
                    'Nếu quantity_basis nêu suy luận số vật tư (ví dụ CT đo ba pha qua AS), kiểm độc lập logic '
                    'đó bằng ngữ cảnh nguồn; giữ drawing_quantity là số ký hiệu, không máy móc coi một ký hiệu '
                    'luôn bằng một vật tư. Không đủ căn cứ thì bác bỏ. '
                    'Khi unit=Cụm và quantity_review chưa chốt vật tư, quantity là số cụm, không khẳng định '
                    'số CT vật lý. AS chung có nhiều kiểu đấu; không mặc định số CT bằng số pha khi nguồn không ghi. '
                    'Dây nối đi qua không phải thiết bị khác. Kiểm tra mất nét/tiếp điểm '
                    'hoặc chữ số do cắt mép. Aptomat nằm ngang có nhãn phía trên và tiếp điểm trên dây '
                    'vẫn hợp lệ nếu đầy đủ nét; không ép thành ký hiệu dọc hay chỉ lấy nhãn.  Không lấy chữ từ ngữ cảnh để bù phần thiếu của ảnh xuất ra. '
                    'Nếu có tag, kiểm tra ảnh xuất có đúng NHÃN TAG; không lấy tag từ danh mục để xác nhận. '
                    'tag_matches chỉ yêu cầu đủ mã tag như P19; không đòi ảnh tag phải chứa hết tên tải '
                    'khi đã có ảnh nhãn tải riêng để kiểm load_matches. '
                    'Nếu có tải, kiểm tra nhãn tải và quan hệ dây nối trong ảnh ngữ cảnh bên phải; '
                    'load_matches và relationship_verified chỉ true khi thấy đúng nhãn và lần được dây. '
                    'Không sửa danh mục, không tự điền thông số không thấy. Trả JSON '
                    'Phân biệt thông số với ký hiệu và suy luận: A/V trong vòng tròn chỉ loại đo, '
                    'R/Y/B chỉ nhãn pha, tên tải và chức năng không phải định mức. Không xác nhận '
                    '220V của đèn, kiểu kim/số hay thang 5A của đồng hồ nếu nguồn không ghi. '
                    'Với material_annotation, nguồn nêu trực tiếp vật tư và số lượng trong GHI CHÚ: '
                    'kiểm độc lập ảnh xuất có đủ nguyên văn tên vật tư và số lượng khớp ứng viên. '
                    'Đây là bằng chứng ghi chú, không phải ký hiệu điện; không bắt ghi chú vẽ đủ từng vật tư. '
                    'Trả note_complete, note_matches, quantity_matches cho trường hợp này; không xác nhận '
                    'từ danh mục hoặc suy số nút ấn bằng số nhánh. Thiếu chữ/số nguồn thì bác bỏ. '
                    'unsupported_claims liệt kê mọi định mức/cấu tạo ứng viên khẳng định nhưng không thấy '
                    'trên nhãn nguồn; không có thì []. '
                    'Với shared_label=true, nhãn thông số là tiêu đề dùng chung phải xuất ở ảnh trái riêng; '
                    'kiểm thêm dây/ranh giới nhóm bên phải để chứng minh tiêu đề áp dụng cho đúng ký hiệu này. '
                    'Không bác chỉ vì tiêu đề có nhiều nhánh dùng chung, nhưng shared_label_matches chỉ true '
                    'khi đã chứng minh quan hệ đó, không chỉ vì gần nhau. '
                    '{"checks":[{"device_id":"0","matches":true,"symbol_complete":true,'
                    '"label_complete":true,"note_complete":true,"note_matches":true,"quantity_matches":true,"unsupported_claims":[],"isolated":true,"source_overlap":false,"identity_unambiguous":true,"shared_label_matches":true,"tag_matches":true,"load_matches":true,"relationship_verified":true,"observed":"chữ/hình thực thấy",'
                    '"reason":"lỗi cụ thể nếu có"}]}.\n' + json.dumps(requests, ensure_ascii=False)))
                blocks = ResponseParserService.extract_json_blocks(raw)
                checks = next((b['checks'] for b in blocks if isinstance(b, dict) and isinstance(b.get('checks'), list)), [])
                for identity in batch:
                    matches = [c for c in checks if isinstance(c, dict) and str(c.get('device_id')) == identity]
                    if len(matches) != 1:
                        continue
                    check = matches[0]
                    rows[identity].pop('processing_interrupted',None)
                    source_overlap = check.get('source_overlap') is True
                    clear_identity = check.get('identity_unambiguous') is True
                    identity_checked = clear_identity if 'identity_unambiguous' in check else check.get('isolated') is True
                    rows[identity]['verified'] = all(check.get(k) is True
                        for k in ('matches', 'symbol_complete', 'label_complete')) and identity_checked
                    if rows[identity].get('evidence_kind')=='material_note':
                        rows[identity]['note_verified']=all(check.get(k) is True for k in ('note_complete','note_matches','quantity_matches'))
                        rows[identity]['verified']=rows[identity]['note_verified']
                        rows[identity]['symbol_verified']=False
                    if check.get('unsupported_claims'):
                        rows[identity]['verified'] = False
                        check['reason'] = '; '.join(map(str,check['unsupported_claims']))
                    rows[identity].update(source_overlap=source_overlap, identity_unambiguous=clear_identity)
                    device = devices[int(identity)]
                    if rows[identity].get('shared_label') is True and (check.get('shared_label_matches') is not True or not rows[identity].get('relationship_evidence')):
                        rows[identity]['verified'] = False
                    rows[identity]['tag_matches'] = check.get('tag_matches') is True
                    branch_tags = ((getattr(device,'source_observations',None) or {}).get('linked_device') or {}).get('branch_tags')
                    if (device.tag or branch_tags) and (not rows[identity].get('tag_box_2d') or check.get('tag_matches') is not True):
                        rows[identity]['verified'] = False
                    rows[identity]['load_verified'] = bool(rows[identity].get('load_box_2d') and
                        rows[identity].get('relationship_evidence') and check.get('load_matches') is True and
                        check.get('relationship_verified') is True)
                    rows[identity]['audit_observed'] = str(check.get('observed') or '')
                    rows[identity]['audit_reason'] = str(check.get('reason') or '')
                    await checkpoint.save(identity, device, rows[identity])
            except AIVisionError as exc:
                from app.services.ai.connection_pool import transient_transport_failure
                if not retry and transient_transport_failure(exc):
                    retryable_batches.append(batch)
                for identity in batch:
                    rows[identity].update(verified=False, processing_interrupted=True,
                        audit_reason='Máy chủ AI gián đoạn hoặc hết thời gian chờ khi kiểm ảnh; Agent chưa kiểm xong vị trí này.')
            finally:
                os.remove(path)

    batch_size=max(1,min(6,int(batch_size)))
    tasks=[asyncio.create_task(audit_batch(identities[start:start+batch_size])) for start in range(0,len(identities),batch_size)]
    try:
        await asyncio.gather(*tasks)
    except BaseException:
        for task in tasks:task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)
        raise
    if 0<len(retryable_batches)<=2:
        # Recover an isolated network interruption once, after sibling checks
        # finish. Never rerun successful batches or start waves during an outage.
        for batch in retryable_batches:
            await audit_batch(batch,retry=True)
    return {'boxes': list(rows.values()),
            'processing_interrupted':any(row.get('processing_interrupted') for row in rows.values())}
