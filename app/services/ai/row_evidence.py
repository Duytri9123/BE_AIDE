"""Measure horizontal feeder rows from OCR anchors; never synthesize a symbol."""
import re
import statistics
import unicodedata
from app.services.ai.ocr_source_evidence import bounds, text_key

def horizontal_feeder_boxes(image,devices,rows):
    tags=[r for r in rows if r.get('confidence',0)>=.55 and re.fullmatch(r'L\d+(?:/[RYBST])?',text_key(r.get('text')))]
    if len(tags)<3:return {'boxes':[]}
    # Horizontal diagrams repeat tags vertically in a common left column.
    left=statistics.median(bounds(r)[0] for r in tags)
    height=statistics.median(bounds(r)[3]-bounds(r)[1] for r in tags)
    tags=[r for r in tags if abs(bounds(r)[0]-left)<3*height]
    tags.sort(key=lambda r:bounds(r)[1])
    gaps=[bounds(b)[1]-bounds(a)[1] for a,b in zip(tags,tags[1:]) if bounds(b)[1]>bounds(a)[1]+height]
    if len(tags)<3 or not gaps:return {'boxes':[]}
    pitch=statistics.median(gaps)
    if pitch<height*1.3:return {'boxes':[]}
    heads=[r for r in rows if re.search(r'^(?:MCCB|MCB|CB|RCBO|RCCB)[- ]*[1-4]P',text_key(r.get('text'))) and bounds(r)[0]>left+height]
    def normalize(box):
        l,t,r,b=box
        return [round(max(0,t)/image.height*1000),round(max(0,l)/image.width*1000),round(min(image.height,b)/image.height*1000),round(min(image.width,r)/image.width*1000)]
    result=[]
    for index,d in enumerate(devices):
        tag=re.sub(r'/[RYBST]$','',text_key(d.tag))
        matched=[r for r in tags if re.sub(r'/[RYBST]$','',text_key(r['text']))==tag]
        spare=not matched and 'dự phòng' in (str(d.name)+' '+str(d.spec)).lower()
        if len(matched)==1:
            anchor=matched[0];l,t,r,b=bounds(anchor)
            following=[bounds(x)[1] for x in tags if bounds(x)[1]>t+height]
            bottom=min(following)-height*.15 if following else t+pitch-height*.15
            top=t-height*.2
            local_heads=[h for h in heads if top<=bounds(h)[1]<bottom and bounds(h)[0]-r < image.width*.25]
            if not local_heads:continue
            right=max(bounds(h)[2] for h in local_heads)+height*.7
            box=normalize((l-height*.25,top,right,bottom))
            tag_box=normalize(bounds(anchor))
        elif spare:
            labels=[r for r in rows if re.sub(r'[^A-Z]', '', ''.join(c for c in unicodedata.normalize('NFD',str(r.get('text') or '').upper().replace('Đ','D')) if not unicodedata.combining(c))) == 'DUPHONG']
            if len(labels)!=1:continue
            _,t,_,b=bounds(labels[0])
            preceding=[r for r in tags if bounds(r)[1]<t]
            if not preceding:continue
            last=max(preceding,key=lambda r:bounds(r)[1])
            if t-bounds(last)[1]>2*pitch:continue
            nearby=[h for h in heads if abs(bounds(h)[1]-bounds(last)[1])<height]
            if not nearby:continue
            box=normalize((left-height*.25,t-height*.4,max(bounds(h)[2] for h in nearby)+height*.7,b+height*.5))
            tag_box=[]
        else:continue
        result.append({'device_id':str(index),'verified':True,'symbol_verified':True,
            'symbol_box_2d':box,'text_box_2d':box,'tag_box_2d':tag_box,'observed_tag':anchor['text'] if matched else '',
            'coordinate_basis':'measured_horizontal_ocr_row','load_verified':False})
    return {'boxes':result}


def measure_horizontal_rows(image, devices):
    import numpy as np
    from PIL import Image
    from rapidocr_onnxruntime import RapidOCR
    scale=min(1,2600/max(image.size))
    preview=image.resize((round(image.width*scale),round(image.height*scale)),Image.Resampling.LANCZOS)
    found,_=RapidOCR(intra_op_num_threads=1,inter_op_num_threads=1)(np.asarray(preview))
    rows=[{'polygon':[[x/scale,y/scale] for x,y in poly],'text':text,'confidence':float(conf)} for poly,text,conf in found or []]
    return horizontal_feeder_boxes(image,devices,rows)
