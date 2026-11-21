"""Bounded recovery of missing device, branch tag and connected-load evidence."""
import json
import asyncio
import tempfile
from pathlib import Path
from app.services.ai.response_parser import ResponseParserService
from app.services.ai.el_progress import run_step
from app.core.exceptions import AIVisionError


def evidence_gaps(device, box):
    gaps = []
    if not box or box.get('verified') is not True:
        note=(device.source_observations or {}).get('material_annotation') or (box or {}).get('evidence_kind')=='material_note'
        gaps.append('ghi chú vật tư và số lượng' if note else 'ký hiệu và nhãn thiết bị')
    branch_tags = ((device.source_observations or {}).get('linked_device') or {}).get('branch_tags')
    if (device.tag or branch_tags) and (not box or not box.get('tag_box_2d') or box.get('tag_matches') is not True):
        gaps.append('nhãn lộ ' + (device.tag or ' / '.join(branch_tags)))
    if device.connected_load and (not box or not box.get('load_box_2d') or box.get('load_verified') is not True):
        gaps.append('phụ tải và quan hệ dây nối')
    return gaps


async def complete_evidence(image, image_path, devices, audited, call_image, *, concurrency=1, attempts=2, cache_scope=None, local_recovery=True):
    from app.services.ai.device_crop_audit import audit_device_previews
    # A provider outage is not missing source content. Keep successful checks
    # and do not turn the failed batch into another expensive recovery cycle.
    if audited.get('processing_interrupted'):
        return audited
    boxes = {str(box['device_id']): box for box in audited.get('boxes', [])}
    if local_recovery and attempts:
        from app.services.ai.source_crop_repair import local_source_repairs
        proposals=await asyncio.to_thread(local_source_repairs,image,devices,audited)
        if proposals:
            checked=await audit_device_previews(image,call_image,devices,{'boxes':proposals},
                concurrency=concurrency,cache_scope=cache_scope)
            for box in checked.get('boxes',[]):
                identity=str(box['device_id']);device=devices[int(identity)]
                if len(evidence_gaps(device,box))<len(evidence_gaps(device,boxes.get(identity))):boxes[identity]=box
            if checked.get('processing_interrupted'):
                return {'boxes':list(boxes.values()),'processing_interrupted':True}
    missing_ids=[str(i) for i,d in enumerate(devices) if evidence_gaps(d,boxes.get(str(i)))]
    if len(missing_ids)>4:
        # Bound each repair to nearby source rows. A single whole-panel request
        # for dozens of missing parts repeatedly produces tiny, inaccurate boxes.
        groups={}
        for identity in missing_ids:
            observed=devices[int(identity)].source_observations or {}
            region=(observed.get('coverage_review') or {}).get('region') or {}
            groups.setdefault(json.dumps(region,sort_keys=True),[]).append(identity)
        gate=asyncio.Semaphore(max(1,min(concurrency,4)))
        async def repair(identities):
            async with gate:
                # Keep request-local IDs stable without rechecking completed rows.
                subset=[devices[int(identity)] for identity in identities]
                local={'boxes':[{**boxes[identity],'device_id':str(i)} for i,identity in enumerate(identities) if identity in boxes]}
                checked=await complete_evidence(image,image_path,subset,local,call_image,
                    concurrency=concurrency,attempts=attempts,cache_scope=cache_scope,local_recovery=False)
                return {**checked,'boxes':[{**box,'device_id':identities[int(box['device_id'])]} for box in checked['boxes']]}
        tasks=[asyncio.create_task(repair(ids[start:start+4])) for ids in groups.values() for start in range(0,len(ids),4)]
        try:
            results=await asyncio.gather(*tasks)
        except BaseException:
            for task in tasks:task.cancel()
            await asyncio.gather(*tasks,return_exceptions=True)
            raise
        for result in results:
            boxes.update({str(box['device_id']):box for box in result['boxes']})
        return {'boxes':list(boxes.values()), 'processing_interrupted':any(r.get('processing_interrupted') for r in results)}
    attempted=set()
    for attempt in range(attempts):
        missing = [{'device_id': str(i), 'name': d.name, 'tag': d.tag, 'spec': d.spec,
                    'source_region':((d.source_observations or {}).get('coverage_review') or {}).get('region'),
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
            '\nCác dòng cần đọc lại: ' + json.dumps(
                [{key:value for key,value in row.items() if key!='source_region'} for row in missing],ensure_ascii=False))
        frame = None
        with tempfile.TemporaryDirectory(prefix='aide_evidence_detail_') as folder:
            read_path = image_path
            region_boxes=[(r.get('source_region') or {}).get('box_2d') for r in missing]
            source_window=None
            if attempt==0 and region_boxes and all(b and b==region_boxes[0] for b in region_boxes):
                from app.schemas.ai import ExtractedDeviceSchema
                try:
                    source_window=ExtractedDeviceSchema.normalize_evidence_box(region_boxes[0])
                except (ValueError,TypeError,OverflowError):
                    source_window=None
                if source_window:
                    source_window=[max(0,source_window[0]-50),max(0,source_window[1]-40),
                                   min(1000,source_window[2]+50),min(1000,source_window[3]+40)]
            anchors = [(boxes.get(r['device_id']) or {}).get('symbol_box_2d') for r in missing]
            anchored_parts = all(
                (not devices[int(r['device_id'])].connected_load or (boxes.get(r['device_id']) or {}).get('load_box_2d'))
                and (not devices[int(r['device_id'])].tag or (boxes.get(r['device_id']) or {}).get('tag_box_2d'))
                for r in missing)
            if source_window or attempt == 0 and all(anchors) and anchored_parts:
                # Include distant rating/tag/load parts that the repair must read.
                # A symbol-only crop cannot repair a load column outside it.
                anchors += [b for r in missing for key in ('text_box_2d','tag_box_2d','load_box_2d')
                            if (b := (boxes.get(r['device_id']) or {}).get(key))]
                window = source_window or [max(0,min(b[0] for b in anchors)-80), max(0,min(b[1] for b in anchors)-80),
                          min(1000,max(b[2] for b in anchors)+80), min(1000,max(b[3] for b in anchors)+80)]
                if source_window or window[2]-window[0] <= 600 and window[3]-window[1] <= 600:
                    left, top = int(window[1]*image.width/1000), int(window[0]*image.height/1000)
                    right, bottom = round(window[3]*image.width/1000), round(window[2]*image.height/1000)
                    if right > left and bottom > top:
                        read_path = str(Path(folder)/'detail.png')
                        image.crop((left,top,right,bottom)).save(read_path)
                        frame = [top*1000/image.height,left*1000/image.width,bottom*1000/image.height,right*1000/image.width]
            signature=json.dumps({'missing':missing,'frame':frame},ensure_ascii=False,sort_keys=True)
            if signature in attempted:break
            attempted.add(signature)
            try:
                raw = await run_step('Đang xử lý lại vị trí ảnh: ' + ', '.join(str(r['tag'] or r['name']) for r in missing),
                    call_image(read_path,prompt), detail=f"{len(missing)} dòng còn thiếu · Lần đọc lại {attempt+1}")
            except AIVisionError:
                for row in missing:
                    identity=row['device_id']
                    boxes[identity]={**(boxes.get(identity) or {}),'device_id':identity,
                        'processing_interrupted':True,
                        'audit_reason':'Máy chủ AI gián đoạn hoặc hết thời gian chờ khi định vị ảnh; Agent chưa xử lý xong.'}
                return {'boxes':list(boxes.values()),'processing_interrupted':True}
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
        if checked.get('processing_interrupted'):
            return {'boxes':list(boxes.values()),'processing_interrupted':True}
    return {'boxes': list(boxes.values())}
