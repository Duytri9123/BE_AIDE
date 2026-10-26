"""Verify image inventory and locate evidence in the original coordinate system."""
import json
import tempfile
import os
from PIL import Image, ImageOps
from app.services.ai.inventory_validation import (
    extract_with_retry, count_with_retry, independent_count_prompt,
    repair_counted_inventory, inventory_kind,
)
from app.services.ai.response_parser import ResponseParserService
from app.schemas.ai import ExtractedDeviceSchema


def oriented_source(path):
    with Image.open(path) as image:
        source = ImageOps.exif_transpose(image)
        if source.mode in ('RGBA', 'LA') or (source.mode == 'P' and 'transparency' in source.info):
            rgba=source.convert('RGBA')
            background=Image.new('RGBA',rgba.size,'white')
            return Image.alpha_composite(background,rgba).convert('RGB')
        return source.convert('RGB')


def strip_edges(image):
    """Snap detail boundaries to a repeated drawing grid, avoiding half symbols."""
    import cv2
    import numpy as np
    gray = np.asarray(image.convert('L'))
    ink = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 15)
    lines = cv2.HoughLinesP(ink, 1, np.pi / 180, 70,
        minLineLength=max(60, image.height // 5), maxLineGap=30)
    coordinates = [] if lines is None else sorted({round((int(x1)+int(x2))/2)
        for x1,y1,x2,y2 in lines.reshape(-1,4)
        if abs(int(x1)-int(x2)) < max(4, image.width / 125)
        and abs(int(y2)-int(y1)) > image.height / 4
        and .12 * image.width < (x1+x2)/2 < .95 * image.width})
    best = None
    for step in np.arange(image.width * .02, image.width * .06, max(.25, image.width / 4000)):
        for origin in coordinates:
            support = sum(abs((x-origin)/step - round((x-origin)/step)) * step < image.width / 400 for x in coordinates)
            if best is None or support > best[0]: best = (support, origin, step)
    edges = [0]
    for fraction in (.30, .55, .75):
        target = image.width * fraction
        if best and best[0] >= 5:
            _, origin, step = best
            target = origin + round((target-origin)/step) * step
        edges.append(round(target))
    return [*edges, image.width]


async def count_source_tiles(image, call_image, prompt):
    """Non-overlapping strips stop the model counting neighbouring columns twice."""
    result = {'counts': [], 'uncertain_regions': []}
    boundaries = strip_edges(image)
    for index in range(4):
        start, end = boundaries[index:index + 2]
        left, right = start, end
        crop = image.crop((left, 0, right, image.height))
        crop = crop.resize((crop.width * 2, crop.height * 2), Image.Resampling.LANCZOS)
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as file:
            path = file.name
        try:
            crop.save(path)
            async def tile_call(instruction):
                return await call_image(path, instruction)
            counts = await count_with_retry(tile_call, prompt
                + f'\nĐây là dải ảnh chi tiết {index + 1}/4 giữ TOÀN chiều cao nguồn; chỉ đếm ký hiệu thấy ở dải này. '
                  'Đếm từng thân CB theo từng cột lộ, không đếm lại tên phụ tải là CB. '
                  'Không đếm ký hiệu cắt cụt tại mép trái/phải dải: thân đầy đủ đã nằm ở dải kế bên. '
                  'Giữ category theo chữ ghi trên ảnh, phân biệt MCCB với MCB. '
                  '2A là dòng cầu chì, KHÔNG phải 2 cầu chì; hai đầu nối nối nhau là một thân. '
                  '3XCT 63/5 nghĩa là 3 CT, không đếm thêm 3 CT ở nhãn 63A. '
                  'Các vòng tròn A/B/C ghi pha trên thanh cái không phải CT; chỉ CT khi có ký hiệu biến dòng trên dây và nhãn tỷ số hoặc bằng chứng biến dòng riêng. '
                  'Giữ đúng mã tủ đã cung cấp; kích thước 1200x800x400 không phải mã tủ. '
                  'Khi không thấy thân trong phạm vi thì quantity=0; không suy các thiết bị thường đi kèm.')
            result['counts'].extend(counts['counts'])
            result['uncertain_regions'].extend(counts.get('uncertain_regions') or [])
        finally:
            os.remove(path)
    return result


async def refine_locations(image, call_image, devices, initial):
    """Locate small groups in native-aspect detail images, then map to the source."""
    proposals = {str(row.get('device_id')): row for row in initial.get('boxes', []) if isinstance(row, dict)}
    output = []
    for start in range(0, len(devices), 6):
        batch = devices[start:start+6]
        boxes = [row.get(key) for i in range(start,start+len(batch))
                 for row in [proposals.get(str(i), {})]
                 for key in ('symbol_box_2d', 'text_box_2d', 'load_box_2d')
                 if isinstance(row.get(key), list) and len(row[key]) == 4]
        if boxes:
            # Vision providers occasionally return the two corners reversed.
            # Normalize every candidate before deriving the shared crop so PIL
            # never receives right < left or bottom < top.
            normalized = [
                (min(b[0], b[2]), min(b[1], b[3]), max(b[0], b[2]), max(b[1], b[3]))
                for b in boxes
            ]
            left = max(0, round(min(b[1] for b in normalized)*image.width/1000)-60)
            right = min(image.width, round(max(b[3] for b in normalized)*image.width/1000)+60)
            top = max(0, round(min(b[0] for b in normalized)*image.height/1000)-60)
            bottom = min(image.height, round(max(b[2] for b in normalized)*image.height/1000)+60)
            if right <= left or bottom <= top:
                left, top, right, bottom = 0, 0, image.width, image.height
        else:
            left, top, right, bottom = 0,0,image.width,image.height
        crop = image.crop((left,top,right,bottom))
        rows = [{'device_id':str(start+i), 'category':d.category, 'tag':d.tag, 'name':'Biến dòng' if d.category=='CT' else d.name,
                 'spec':d.spec, 'poles':d.poles,'in_a':d.in_a,'icu_ka':d.icu_ka,'load':d.connected_load}
                for i,d in enumerate(batch)]
        instruction = ('Đọc trực tiếp ảnh CHI TIẾT này, không dùng tọa độ ảnh toàn trang. '
            f'Ảnh có tỷ lệ gốc {crop.width}x{crop.height}; mọi box chuẩn hóa 0..1000 theo chính ảnh này. '
            'Không sao chép vị trí giữa các hàng. R,Y,B phải đúng từng chữ; AS/VS tách chuyển mạch khỏi đồng hồ A/V. '
            'Với lộ M/L: tìm tag thật trên hàng lộ, lần đúng cột lên ký hiệu và xuống tải, không lấy cột bên cạnh. '
            'symbol_box_2d bao hết HÌNH ký hiệu; text_box_2d chỉ bao đủ thông số ngay ký hiệu, không dùng ô tên tải. '
            'tag_box_2d bao chữ tag thật để đối chiếu đúng cột; không bao tag lộ bên cạnh. '
            'observed_tag là chữ thật đọc trên ảnh; không điền theo danh sách nếu không thấy. '
            'load_box_2d bao cả tên tải và thông số cuối nhánh. verified=true chỉ khi khớp chữ và hình, không bịa vị trí. '
            'Trả JSON {"boxes":[{"device_id":"0","verified":true,"symbol_verified":true,"observed_tag":"",'
            '"symbol_box_2d":[],"text_box_2d":[],"tag_box_2d":[],"load_verified":false,"load_box_2d":[],"load_label":"",'
            '"relationship_evidence":"","branch_quad":[]}]}\n'+json.dumps(rows,ensure_ascii=False))
        with tempfile.NamedTemporaryFile(suffix='.png',delete=False) as file: path=file.name
        try:
            crop.save(path)
            response = await call_image(path,instruction)
            payload = next((b for b in ResponseParserService.extract_json_blocks(response)
                            if isinstance(b,dict) and isinstance(b.get('boxes'),list)), {})
            for row in payload.get('boxes', []):
                if not isinstance(row,dict) or str(row.get('device_id')) not in {r['device_id'] for r in rows}: continue
                requested = devices[int(row['device_id'])]
                import re
                if re.fullmatch(r'[ML]\d+(?:/[RYB])?',str(requested.tag or ''),re.I) and str(row.get('observed_tag') or '').upper() != str(requested.tag).upper():
                    row['verified'] = False
                for key in ('box_2d','symbol_box_2d','text_box_2d','tag_box_2d','load_box_2d'):
                    if isinstance(row.get(key),list) and len(row[key]) == 4 and all(isinstance(v,(int,float)) and not isinstance(v,bool) and 0 <= v <= 1000 for v in row[key]):
                        y1,x1,y2,x2 = row[key]
                        row[key] = [round((top+y1*crop.height/1000)/image.height*1000), round((left+x1*crop.width/1000)/image.width*1000),
                                    round((top+y2*crop.height/1000)/image.height*1000), round((left+x2*crop.width/1000)/image.width*1000)]
                    else:
                        row[key] = []
                if isinstance(row.get('branch_quad'),list) and len(row['branch_quad']) == 4 and all(isinstance(pt,list) and len(pt)==2 and all(isinstance(v,(int,float)) and not isinstance(v,bool) and 0<=v<=1000 for v in pt) for pt in row['branch_quad']):
                    row['branch_quad'] = [[(left+x*crop.width/1000)/image.width*1000,(top+y*crop.height/1000)/image.height*1000] for x,y in row['branch_quad']]
                else:
                    row['branch_quad'] = []
                if requested.category == 'LIGHT' and not row.get('text_box_2d'):
                    row['text_box_2d'] = row.get('tag_box_2d') or []
                if proposals.get(str(row['device_id']),{}).get('source_region'):
                    row['source_region']=proposals[str(row['device_id'])]['source_region']
                output.append(row)
        finally:
            os.remove(path)
    return {'boxes':output}


async def verify_pdf_measurement_crops(image, call_image, devices):
    """Validate the dense measurement cluster from detail crops before export."""
    selected = [device for device in devices if device.category in
                {'VOLTMETER', 'AMMETER', 'METER', 'MULTIMETER', 'SELECTOR'}]
    if not selected:
        return []
    proposals = {'boxes': [{'device_id': str(index), 'box_2d': device.box_2d}
                           for index, device in enumerate(selected)]}
    refined = await refine_locations(image, call_image, selected, proposals)
    audited = await audit_crops(image, call_image, selected, refined)
    from app.services.ai.analysis_pipeline_service import AnalysisPipelineService
    AnalysisPipelineService._apply_verified_boxes(selected, audited, require_symbols=True)
    return [device for device in selected if not device.box_2d]


async def audit_crops(image, call_image, devices, payload):
    from PIL import ImageDraw, ImageOps
    rows_by_id = {str(row.get('device_id')): row for row in payload['boxes']}
    for start in range(0,len(devices),6):
        rows = []
        canvas = Image.new('RGB',(1000,220*min(6,len(devices)-start)), 'white')
        draw = ImageDraw.Draw(canvas)
        for local,d in enumerate(devices[start:start+6]):
            index = str(start+local); row = rows_by_id.get(index,{})
            if row.get('verified') is not True: continue
            region=row.get('source_region')
            if region and any(not row.get(key) or row[key][0]<region[0] or row[key][1]<region[1]
                              or row[key][2]>region[2] or row[key][3]>region[3]
                              for key in ('symbol_box_2d','text_box_2d')):
                row['verified']=False
                row['audit_observed']='Vùng ký hiệu/thông số nằm ngoài lộ đã định vị trên ảnh nguồn.'
                continue
            draw.text((8,local*220+8),'ID '+index,fill='black')
            present = []
            for column,key in enumerate(('symbol_box_2d','text_box_2d','tag_box_2d')):
                box = row.get(key)
                if not box or len(box)!=4: continue
                y1,x1,y2,x2 = box
                crop = image.crop((max(0,round(x1*image.width/1000)),max(0,round(y1*image.height/1000)),
                                   min(image.width,round(x2*image.width/1000)),min(image.height,round(y2*image.height/1000))))
                if crop.width<=0 or crop.height<=0: continue
                crop=ImageOps.contain(crop,(300,185),Image.Resampling.LANCZOS)
                canvas.paste(crop,(column*330+8,local*220+30));present.append(key)
            rows.append({'device_id':index,'category':d.category,'tag':d.tag,'available_crops':present})
        if not rows: continue
        with tempfile.NamedTemporaryFile(suffix='.png',delete=False) as file:path=file.name
        try:
            canvas.save(path)
            answer=await call_image(path,'Kiểm tra CHÍNH ẢNH ĐÃ CẮT, không tin vào tên yêu cầu. Mỗi ID: ảnh trái là ký hiệu, giữa là thông số, phải là tag. '
                'Chỉ matches=true nếu ảnh có hình ký hiệu đầy đủ của đúng thiết bị/tag, không lẫn lộ. '
                'R/Y/B phải đọc đúng chữ, AS/VS không được dùng ảnh đồng hồ làm chuyển mạch. '
                'Với M/L phải đọc đúng tag phía phải và thông số cùng hàng; thiếu ảnh tag thì false. '
                'Đọc lại thông số ĐỘC LẬP từ chữ trong ảnh giữa: source_spec, poles, in_a, icu_ka. '
                'source_category là mã loại đọc thực trên ảnh; category yêu cầu có thể đọc sai trước đó. '
                'Nếu tag và hình đúng nhưng loại/định mức đọc trước đó sai, vẫn matches=true và trả loại/thông số đúng từ ảnh. '
                'Giữ đúng loại ghi trên ảnh kể cả MCCB dòng nhỏ. Không suy dòng định mức từ số lộ/tag; không thấy thì null. '
                'Ảnh CT có thể là một ký hiệu 3XCT cho cả ba biến dòng; không yêu cầu chữ pha riêng trên glyph nhóm. '
                'Đồng hồ A/V: kiểm tra hình đo và dải đo, tag A/V là nhãn loại không bắt buộc có riêng trên ảnh tag. '
                'Không thấy hình hoặc chữ cần thiết thì false; không suy hình từ yêu cầu. '
                'Trả JSON {"checks":[{"device_id":"0","matches":true,"observed":"chữ và hình thực thấy",'
                '"source_category":"loại thực trên nhãn", "source_spec":"thông số đọc thực tế","poles":null,"in_a":null,"icu_ka":null}]}.\n'+json.dumps(rows,ensure_ascii=False))
            blocks=ResponseParserService.extract_json_blocks(answer)
            checks=next((b.get('checks') for b in blocks if isinstance(b,dict) and isinstance(b.get('checks'),list)),[])
            for request in rows:
                matches=[c for c in checks if isinstance(c,dict) and str(c.get('device_id'))==request['device_id']]
                if len(matches)==1:
                    rows_by_id[request['device_id']]['audit_observed']=str(matches[0].get('observed') or '')
                if len(matches)!=1 or matches[0].get('matches') is not True:
                    rows_by_id[request['device_id']]['verified']=False
                elif matches[0].get('observed'):
                    reading=matches[0]
                    device=devices[int(request['device_id'])]
                    rows_by_id[request['device_id']]['audit_observed']=str(reading['observed'])
                    if reading.get('source_spec'):
                        device.spec=str(reading['source_spec'])
                    source_category=inventory_kind(reading.get('source_category'))
                    if device.category in {'CB','MCB','MCCB','RCBO','RCCB'} and source_category in {'MCB','MCCB','RCBO','RCCB'}:
                        device.category=source_category
                    import math
                    for field in ('poles','in_a','icu_ka'):
                        value=reading.get(field)
                        if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>0:
                            if field=='poles' and (value not in (1,2,3,4)):continue
                            setattr(device,field,int(value) if field=='poles' else float(value))
        finally:
            os.remove(path)
    return payload


async def retry_unverified_evidence(image,call_image,devices,payload):
    """Re-read unresolved source regions; preserve already confirmed evidence."""
    by_id={str(row.get('device_id')):row for row in payload.get('boxes',[])}
    failed=[i for i in range(len(devices)) if by_id.get(str(i),{}).get('verified') is not True]
    if not failed:return payload
    subset=[devices[i] for i in failed]
    proposed={'boxes':[{**by_id.get(str(index),{}),'device_id':str(local)} for local,index in enumerate(failed)]}
    refined=await refine_locations(image,call_image,subset,proposed)
    audited=await audit_crops(image,call_image,subset,refined)
    for row in audited['boxes']:
        local=int(row['device_id'])
        if row.get('verified') is True:
            identity=str(failed[local])
            by_id[identity]={**row,'device_id':identity}
    return {'boxes':list(by_id.values())}


async def verify_image_inventory(call, prompt, devices, image_size, detail_call=None, tile_count=None, locate_detail=None, supplement_source=None):
    prompt += ('\nCategory chỉ dùng MCB,MCCB,RCBO,RCCB,CT,AMMETER,VOLTMETER,SELECTOR,LIGHT,FUSE,TIMER,CONTACTOR,SPD. '
               'Không dùng Aptomat hay Thiết bị đo lường làm category. AS và VS là SELECTOR riêng; '
               'ampe kế AMMETER riêng; vôn kế VOLTMETER riêng. Giữ nguyên mã loại ghi trực tiếp trên nguồn.')
    prompt += ('\nĐể sửa kiểm đếm, trả JSON gọn chỉ có devices; không lặp file_assessment, panels hoặc phân tích sản phẩm. '
               'Giữ mọi hàng riêng, không gộp M1..M28. Chỉ các trường category,name,spec,tag,panel_code,quantity,poles,in_a,icu_ka,connected_load. '
               'Không dấu đầu dòng, không dấu sao, không Markdown hoặc dấu ...; JSON phải đóng đầy đủ.')
    prompt += '\nGiữ mã tủ theo danh mục nguồn; không lấy kích thước vỏ tủ làm panel_code. '
    counts = await count_with_retry(call, independent_count_prompt(devices))
    if supplement_source:
        devices = await supplement_source(devices, counts)
    try:
        _, devices = await repair_counted_inventory(call, prompt, devices, counts, attempts=1)
    except ValueError:
        if detail_call is None:
            raise
        # The independent count can also misread tiny repeated labels. Re-read
        # source detail before rejecting; never change counts to fit the list.
        counts = await tile_count(independent_count_prompt(devices)) if tile_count else await count_with_retry(detail_call, independent_count_prompt(devices)
            + '\nKiểm tra lại nhãn MCB và MCCB theo chữ thực sự, không suy theo dòng nhỏ. '
              'Ảnh chi tiết cùng nguồn; kiểm đếm lại độc lập, không dùng danh mục trước làm căn cứ số lượng.')
        if supplement_source:
            devices = await supplement_source(devices, counts)
        # A single fuse body with two terminals is not two fuses. Only correct
        # that quantity when the detailed independent source count confirms one.
        from app.services.ai.inventory_validation import panel_key
        for device in devices:
            if inventory_kind(device.category, device.name, device.spec) != 'FUSE': continue
            same = [d for d in devices if inventory_kind(d.category,d.name,d.spec) == 'FUSE'
                    and panel_key(d.panel_code) == panel_key(device.panel_code)]
            source = [r for r in counts['counts'] if inventory_kind(r['category']) == 'FUSE'
                      and panel_key(r['panel_code']) == panel_key(device.panel_code)]
            if len(same) == 1 and device.quantity == 2 and sum(r['quantity'] for r in source) == 1:
                device.quantity = 1
        try:
            _, devices = await repair_counted_inventory(detail_call, prompt, devices, counts, attempts=1)
        except ValueError:
            # The extraction is still useful when an independent recount cannot
            # converge. Evidence location below marks rows that need review;
            # do not discard the complete Gemini inventory after two reads.
            pass
    devices = [d if isinstance(d, ExtractedDeviceSchema) else ExtractedDeviceSchema(**vars(d)) for d in devices]
    for device in devices:
        device.category = inventory_kind(device.category, device.name, device.spec)
    rows = [{k: getattr(d, k, None) for k in ('category', 'tag', 'name', 'spec', 'connected_load')}
            | {'device_id': str(i)} for i, d in enumerate(devices)]
    instruction = (
        'Định vị trực tiếp trên ảnh nguồn, không sửa hoặc suy diễn danh mục. '
        f'Ảnh sau áp dụng EXIF có kích thước {image_size[0]}x{image_size[1]} pixel. '
        'Giữ nguyên tỷ lệ và hướng ảnh; tọa độ chuẩn hóa 0..1000 trên TOÀN ảnh này, '
        'box=[ymin,xmin,ymax,xmax]. Không dùng tỷ lệ của ảnh khác hoặc ảnh vuông. '
        'Mỗi hàng phải đối chiếu đúng tag, chữ và ký hiệu; R không lấy Y, fuse không lấy đèn, CT không lấy đồng hồ. '
        'Chỉ verified=true khi thấy đúng hình ký hiệu và thông số; cần symbol_verified=true, '
        'symbol_box_2d bao TOÀN ký hiệu, text_box_2d bao đủ thông số. '
        'Thiết bị bổ sung theo yêu cầu hoặc suy luận không có ký hiệu: verified=false, không bịa ảnh. '
        'Nếu nhánh có tải: lần dây tới đúng nhãn tải, load_verified=true chỉ khi có relationship_evidence; '
        'load_box_2d phải bao đủ tên tải, tag và các thông số cuối nhánh. '
        'Với nhánh nghiêng có thể trả branch_quad bốn điểm [x,y] chuẩn hóa theo thứ tự TL,TR,BR,BL '
        'bao đủ từ ký hiệu đến cuối nhánh; không cắt chữ hoặc lộ kế bên. '
        'Trả JSON {"boxes":[{"device_id":"0","verified":true,"symbol_verified":true, '
        '"symbol_box_2d":[],"text_box_2d":[],"load_verified":false,"load_box_2d":[], '
        '"relationship_evidence":"","load_label":"","branch_quad":[]}]}\n'
        + json.dumps(rows, ensure_ascii=False)
    )
    answer = await call(instruction)
    payload = next((b for b in ResponseParserService.extract_json_blocks(answer)
                    if isinstance(b, dict) and isinstance(b.get('boxes'), list)), None)
    if payload is None:
        raise ValueError('Chưa đọc được dữ liệu đối chiếu vị trí ảnh nguồn')
    if locate_detail:
        payload = await locate_detail(devices,payload)
    return devices, payload
