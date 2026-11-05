"""Tighten evidence using measured source pixels, without changing inventory."""
import math
import re
import cv2
import numpy as np

METER_TYPES={'METER','VOLTMETER','AMMETER','MULTIMETER'}

def _pixels(box,w,h):
    if not box or len(box)!=4:return None
    y1,x1,y2,x2=box
    return [round(x1*w/1000),round(y1*h/1000),round(x2*w/1000),round(y2*h/1000)]

def _normal(box,w,h):
    l,t,r,b=box
    return [max(0,math.floor(t/h*1000)),max(0,math.floor(l/w*1000)),min(1000,math.ceil(b/h*1000)),min(1000,math.ceil(r/w*1000))]

def _same_page(a,b):
    from app.services.ai.panel_identity import panel_identity
    return (panel_identity(getattr(a, 'panel_code', None)), getattr(a, 'source_filename', None), getattr(a, 'source_page', None)) == (panel_identity(getattr(b, 'panel_code', None)), getattr(b, 'source_filename', None), getattr(b, 'source_page', None))

def expand_to_whitespace(image_np, left, top, right, bottom, max_pad=45, min_pad=12):
    """
    Tự động mở rộng viền crop (pixel) ra ngoài cho đến khi 4 cạnh tiếp giáp vùng giấy trắng,
    tránh hoàn toàn việc cắt đứt nét chữ, cắt ngang ký hiệu thiết bị hoặc đường dây dẫn.
    """
    if image_np is None:
        return left, top, right, bottom
    
    if len(image_np.shape) == 3:
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = image_np

    h, w = gray.shape[:2]
    left = max(0, int(left - min_pad))
    top = max(0, int(top - min_pad))
    right = min(w, int(right + min_pad))
    bottom = min(h, int(bottom + min_pad))

    ink_thresh = 230  # Mọi pixel tối hơn 230 được coi là nét vẽ / chữ số

    # 1. Đẩy cạnh trên (top) lên trên đến khi gặp khoảng trắng
    steps = 0
    while top > 0 and steps < max_pad:
        row = gray[top, max(0, left):min(w, right)]
        if len(row) > 0 and np.min(row) < ink_thresh:
            top -= 1
            steps += 1
        else:
            break
    top = max(0, top - 3)

    # 2. Đẩy cạnh dưới (bottom) xuống dưới đến khi gặp khoảng trắng
    steps = 0
    while bottom < h - 1 and steps < max_pad:
        row = gray[bottom, max(0, left):min(w, right)]
        if len(row) > 0 and np.min(row) < ink_thresh:
            bottom += 1
            steps += 1
        else:
            break
    bottom = min(h, bottom + 3)

    # 3. Đẩy cạnh trái (left) sang trái đến khi gặp khoảng trắng
    steps = 0
    while left > 0 and steps < max_pad:
        col = gray[max(0, top):min(h, bottom), left]
        if len(col) > 0 and np.min(col) < ink_thresh:
            left -= 1
            steps += 1
        else:
            break
    left = max(0, left - 3)

    # 4. Đẩy cạnh phải (right) sang phải đến khi gặp khoảng trắng
    steps = 0
    while right < w - 1 and steps < max_pad:
        col = gray[max(0, top):min(h, bottom), right]
        if len(col) > 0 and np.min(col) < ink_thresh:
            right += 1
            steps += 1
        else:
            break
    right = min(w, right + 3)

    return left, top, right, bottom

def refine_phase_indicator_groups(image, devices):
    """
    Đảm bảo các cụm đèn báo pha 3 pha (R-Y-B hoặc R-S-T) hoặc cầu chì bảo vệ tín hiệu
    được gom đủ độ rộng ngang, bao trọn vẹn cả 3 pha và ký hiệu đèn thay vì chỉ cắt 1 chữ hẹp.
    """
    w, h = image.size
    for dev in devices:
        name_or_cat = (str(getattr(dev, 'name', '')) + ' ' + str(getattr(dev, 'category', '')) + ' ' +
                       str(getattr(dev, 'tag', '')) + ' ' + str(getattr(dev, 'spec', ''))).upper()
        is_lamp = getattr(dev, 'category', '') in {'LIGHT', 'INDICATOR'} or 'ĐÈN' in name_or_cat or 'PHASE' in name_or_cat or 'CHỈ THỊ' in name_or_cat
        if not is_lamp or not getattr(dev, 'box_2d', None):
            continue

        box = list(dev.box_2d)
        is_multiphase = any(k in name_or_cat for k in ['R, Y, B', 'R,Y,B', 'R - Y - B', 'R-S-T', 'R, S, T', 'R,S,T', '3 PHA', 'BA PHA'])
        bw = box[3] - box[1]

        # Tìm các thiết bị đèn / nhãn pha đồng cấp cùng trang/tủ
        peers = [p for p in devices if p is not dev and _same_page(p, dev) and getattr(p, 'box_2d', None)
                 and (getattr(p, 'category', '') in {'LIGHT', 'INDICATOR', 'FUSE'} or any(c in str(getattr(p, 'tag', '')).upper() for c in ['R', 'S', 'T', 'Y', 'B']))]
        aligned_peers = [p for p in peers if abs(p.box_2d[0] - box[0]) < 60 and abs(p.box_2d[1] - box[1]) < 250]

        if aligned_peers:
            all_boxes = [box] + [p.box_2d for p in aligned_peers]
            ymin = max(0, min(b[0] for b in all_boxes) - 10)
            xmin = max(0, min(b[1] for b in all_boxes) - 10)
            ymax = min(1000, max(b[2] for b in all_boxes) + 10)
            xmax = min(1000, max(b[3] for b in all_boxes) + 10)
            dev.box_2d = [ymin, xmin, ymax, xmax]
            reg = dev.evidence_region or {}
            dev.evidence_region = {**reg, 'box_2d': dev.box_2d,
                                   'symbol_box_2d': [ymin, xmin, min(ymax, ymin + int((ymax-ymin)*0.6)), xmax],
                                   'text_box_2d': [max(ymin, ymax - int((ymax-ymin)*0.5)), xmin, ymax, xmax],
                                   'multiphase_unified': True}
        elif (is_multiphase or getattr(dev, 'quantity', 1) >= 3) and bw < 75:
            # Hộp bị bó quá hẹp (chỉ bao quanh 1 pha như chữ 'R')
            extra_w = max(45, int(bw * 1.8))
            new_xmin = max(0, box[1] - int(extra_w * 0.15))
            new_xmax = min(1000, box[3] + int(extra_w * 1.6))
            new_ymin = max(0, box[0] - 15)
            new_ymax = min(1000, box[2] + 15)
            dev.box_2d = [new_ymin, new_xmin, new_ymax, new_xmax]
            reg = dev.evidence_region or {}
            dev.evidence_region = {**reg, 'box_2d': dev.box_2d,
                                   'symbol_box_2d': [new_ymin, new_xmin, min(new_ymax, new_ymin + int((new_ymax-new_ymin)*0.6)), new_xmax],
                                   'text_box_2d': [max(new_ymin, new_ymax - int((new_ymax-new_ymin)*0.5)), new_xmin, new_ymax, new_xmax],
                                   'multiphase_expanded': True}

def refine_dense_measurement(image,devices):
    w,h=image.size
    for meter in devices:
        if meter.category not in METER_TYPES or not meter.box_2d:continue
        l,t,r,b=_pixels(meter.box_2d,w,h)
        bw,bh=r-l,b-t
        if bw<=0 or bh<=0:continue
        region=(max(0,l-2*bw),max(0,t-bh),min(w,r+2*bw),min(h,b+bh))
        left,top,right,bottom=region
        gray=cv2.cvtColor(np.asarray(image.crop(region).convert('RGB')),cv2.COLOR_RGB2GRAY)
        circles=cv2.HoughCircles(cv2.GaussianBlur(gray,(3,3),0),cv2.HOUGH_GRADIENT,1,max(10,h*.003),
            param1=90,param2=24,minRadius=max(4,round(h*.0015)),maxRadius=max(10,round(h*.012)))
        if circles is None:continue
        candidates=[(float(x)+left,float(y)+top,float(radius)) for x,y,radius in circles[0]]
        matching=[c for c in candidates if l<=c[0]<=r and (t+b)/2<=c[1]<=b]
        if not matching:continue
        x,y,radius=max(matching,key=lambda c:c[2])
        pad=max(2,radius*.12)
        symbol=_normal([x-radius-pad,y-radius-pad,x+radius+pad,y+radius+pad],w,h)
        # The range label is above the meter; do not union it with the selector.
        label=_normal([l,t,r,max(t+1,y-radius)],w,h)
        meter.evidence_region={**(meter.evidence_region or {}),'symbol_box_2d':symbol,
            'text_box_2d':label,'coordinate_basis':'measured_source_circle','primary_symbol_only':True,
            'symbol_circle':[x/w*1000,y/h*1000,radius/w*1000,radius/h*1000]}
        peers=[d for d in devices if d is not meter and _same_page(d,meter)]
        selectors=[d for d in peers if d.category=='SELECTOR']
        adjacent=[c for c in candidates if abs(c[1]-y)<=max(3,radius*.4)
                  and x+radius*1.3<c[0]<r+3*radius and c[2]<radius*.9]
        if len(selectors)==1 and adjacent:
            sx,sy,sr=min(adjacent,key=lambda c:abs(c[0]-x))
            selector=selectors[0];margin=max(2,sr*.18)
            selector.box_2d=_normal([sx-sr-margin,sy-sr-margin,sx+sr+margin,sy+sr+margin],w,h)
            selector.evidence_region={**(selector.evidence_region or {}),'box_2d':selector.box_2d,
                'symbol_box_2d':selector.box_2d,'text_box_2d':None,'verification_status':'verified',
                'coordinate_basis':'measured_source_circle_next_to_meter'}
        for lamp in peers:
            box=lamp.box_2d
            if lamp.category not in {'LIGHT','INDICATOR'} or not box:continue
            if box[0]<meter.box_2d[0]<box[2] and min(box[3],meter.box_2d[3])>max(box[1],meter.box_2d[1]):
                new_bottom = meter.box_2d[0] - 1
                if new_bottom - box[0] >= 25:
                    lamp.box_2d=[box[0],box[1],new_bottom,box[3]]
                    lamp.evidence_region={**(lamp.evidence_region or {}),'box_2d':lamp.box_2d,
                        'symbol_box_2d':lamp.box_2d,'text_box_2d':None,
                        'coordinate_basis':'separated_from_meter_range','verification_status':'verified'}
                if re.fullmatch(r'\s*0\s*[-–]\s*\d+\s*V\s*',str(lamp.spec or ''),re.I) and lamp.spec==meter.spec:
                    lamp.spec=''
                    lamp.notes='Chưa có điện áp định mức đèn trên nguồn; dải đo thuộc vôn kế bên dưới.'

def refine_spare_symbol(image,devices):
    w,h=image.size
    for device in devices:
        if device.box_2d or device.category not in {'CB','MCB','MCCB'}:continue
        if 'dự phòng' not in (str(device.name)+' '+str(device.spec)).lower():continue
        evidence=device.evidence_region or {}
        symbol=_pixels(evidence.get('symbol_box_2d'),w,h)
        label=_pixels(evidence.get('text_box_2d'),w,h)
        extent=_pixels(evidence.get('box_2d'),w,h)
        if not symbol or not label or not extent or label[0]<=symbol[2]:continue
        sl,st,sr,sb=symbol;sw,sh=sr-sl,sb-st
        left=max(0,sl-max(2,round(sw*.2)))
        right=min(w,label[0]-2,sl+max(sw*8,sh*4))
        top=max(0,min(st,extent[1])-2);bottom=min(h,max(sb,extent[3])+2)
        if right<=left or bottom<=top:continue
        gray=np.asarray(image.crop((left,top,right,bottom)).convert('L'))
        ink=(gray<140).astype('uint8')*255
        horizontal=cv2.morphologyEx(ink,cv2.MORPH_OPEN,np.ones((1,max(30,ink.shape[1]//2)),np.uint8))
        vertical=cv2.morphologyEx(ink,cv2.MORPH_OPEN,np.ones((max(15,ink.shape[0]//2),1),np.uint8))
        remaining=cv2.subtract(cv2.subtract(ink,horizontal),vertical)
        count,_,stats,_=cv2.connectedComponentsWithStats(remaining)
        parts=[s for s in stats[1:] if s[4]>=max(5,sh*.2)]
        if len(parts)<2:continue
        x1=min(s[0] for s in parts);y1=min(s[1] for s in parts)
        x2=max(s[0]+s[2] for s in parts);y2=max(s[1]+s[3] for s in parts)
        if not (1.2<(x2-x1)/max(1,y2-y1)<12):continue
        device.box_2d=_normal([left+x1-3,top+y1-3,left+x2+3,top+y2+3],w,h)
        device.evidence_region={**evidence,'box_2d':device.box_2d,'symbol_box_2d':device.box_2d,
            'text_box_2d':None,'verification_status':'verified','coordinate_basis':'measured_spare_ink_components',
            'load_verified':False}

def tighten_evidence_geometry(image,devices):
    refine_dense_measurement(image,devices)
    refine_phase_indicator_groups(image,devices)
    refine_spare_symbol(image,devices)

