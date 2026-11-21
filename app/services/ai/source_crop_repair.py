"""Propose local repairs from source pixels; every proposal is audited again."""
import math


def local_source_repairs(image,devices,audited):
    import cv2
    import numpy as np
    from app.services.ai.takeoff_evidence_completion import evidence_gaps
    gray=cv2.cvtColor(np.asarray(image.convert('RGB')),cv2.COLOR_RGB2GRAY)
    height,width=gray.shape
    boxes={str(b.get('device_id')):b for b in audited.get('boxes',[])}
    def pixels(box):
        return (max(0,int(box[1]*width/1000)),max(0,int(box[0]*height/1000)),
                min(width,math.ceil(box[3]*width/1000)),min(height,math.ceil(box[2]*height/1000)))
    def normalized(left,top,right,bottom):return [top*1000/height,left*1000/width,bottom*1000/height,right*1000/width]
    proposals=[]
    for index,device in enumerate(devices):
        old=boxes.get(str(index)) or {}
        region=((device.source_observations or {}).get('coverage_review') or {}).get('region') or {}
        if not region.get('wire_band') or not evidence_gaps(device,old) or old.get('evidence_kind')=='material_note':continue
        proposal=dict(old);changed=False
        symbol=old.get('symbol_box_2d')
        if old.get('verified') is not True and symbol:
            refs=[(i,boxes.get(str(i),{})) for i,d in enumerate(devices) if i!=index
                  and d.category==device.category and d.quantity==device.quantity==1
                  and boxes.get(str(i),{}).get('verified') is True and boxes.get(str(i),{}).get('symbol_box_2d')]
            refs.sort(key=lambda pair:abs(sum(pair[1]['symbol_box_2d'][::2])-sum(symbol[::2])))
            cy,cx=(symbol[0]+symbol[2])/2,(symbol[1]+symbol[3])/2
            roi_box=[max(0,cy-32),max(0,cx-40),min(1000,cy+32),min(1000,cx+40)]
            left,top,right,bottom=pixels(roi_box);roi=gray[top:bottom,left:right]
            best=None
            for _,reference in refs[:3]:
                l,t,r,b=pixels(reference['symbol_box_2d']);template=gray[t:b,l:r]
                if min(template.shape,default=0)<8 or float(np.std(template))<12:continue
                for scale in (.8,.9,1,1.1,1.2):
                    tw,th=round(template.shape[1]*scale),round(template.shape[0]*scale)
                    if min(tw,th)<8 or tw>=roi.shape[1] or th>=roi.shape[0]:continue
                    detail=cv2.resize(template,(tw,th),interpolation=cv2.INTER_LINEAR)
                    score_map=cv2.matchTemplate(roi,detail,cv2.TM_CCOEFF_NORMED)
                    _,score,_,where=cv2.minMaxLoc(score_map)
                    x,y=left+where[0],top+where[1]
                    distance=math.hypot((x+tw/2)/width*1000-cx,(y+th/2)/height*1000-cy)
                    ranked=float(score)-distance*.006
                    if score>=.72 and distance<=26 and (best is None or ranked>best[0]):
                        best=(ranked,normalized(max(0,x-3),max(0,y-3),min(width,x+tw+3),min(height,y+th+3)))
            if best:
                proposal['symbol_box_2d']=best[1];changed=True
        # Label extents are proposals too. A small context margin retains the
        # printed digit/diacritic without manufacturing or changing its value.
        for key,needed in (('text_box_2d',old.get('verified') is not True),
                           ('tag_box_2d',bool(device.tag and old.get('tag_matches') is not True)),
                           ('load_box_2d',bool(device.connected_load and old.get('load_verified') is not True))):
            box=old.get(key)
            if not needed or not box:continue
            l,t,r,b=pixels(box)
            if r<=l or b<=t or float(np.std(gray[t:b,l:r]))<8:continue
            proposal[key]=[max(0,box[0]-6),max(0,box[1]-10),min(1000,box[2]+6),min(1000,box[3]+10)]
            changed=True
        if changed:
            proposal.update(device_id=str(index),verified=True,symbol_verified=True)
            proposals.append(proposal)
    return proposals
