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
    return (panel_identity(a.panel_code),a.source_filename,a.source_page)==(panel_identity(b.panel_code),b.source_filename,b.source_page)

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
                lamp.box_2d=[box[0],box[1],meter.box_2d[0]-1,box[3]]
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
    refine_spare_symbol(image,devices)
