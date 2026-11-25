"""Compose checked source regions with whitespace-snapped continuity."""
import base64
import io
import math
from PIL import Image


def trim_native_text(crop):
    """Remove empty caption margins without painting over any source pixels."""
    if crop.height<=crop.width*4:return crop
    import cv2
    import numpy as np
    ink=(np.asarray(crop.convert('L'))<240).astype('uint8')*255
    borders=cv2.bitwise_or(cv2.morphologyEx(ink,cv2.MORPH_OPEN,np.ones((max(9,round(crop.height*.7)),1),'uint8')),
        cv2.morphologyEx(ink,cv2.MORPH_OPEN,np.ones((1,max(7,round(crop.width*.9))),'uint8')))
    ys,xs=np.nonzero(cv2.bitwise_and(ink,cv2.bitwise_not(borders)))
    if not len(xs):return crop
    pad=max(3,round(crop.width*.3))
    bounds=(max(0,int(xs.min())-pad),max(0,int(ys.min())-pad),
            min(crop.width,int(xs.max())+pad+1),min(crop.height,int(ys.max())+pad+1))
    return crop.crop(bounds) if bounds[3]-bounds[1]<crop.height*.8 else crop


def _device_preview(image, region, *, tight=False):
    from app.services.ai.evidence_crops import evidence_crop_pixels

    def crop_pixels(box):
        if not tight:
            return evidence_crop_pixels(box, *image.size, image=image)
        from app.schemas.ai import ExtractedDeviceSchema
        box = ExtractedDeviceSchema.normalize_evidence_box(box)
        if not box:
            return None
        y1, x1, y2, x2 = box
        # Dense CAD circuits have neighbouring symbols only a few pixels away.
        # Following wire ink into whitespace or enforcing a minimum crop size
        # can pull an entire measurement cluster into one device's thumbnail.
        is_native = str(region.get('geometry_source') or '').startswith('native_')
        pad_x = 2 if is_native else max(14, min(42, round(image.width * .015)))
        pad_y = 2 if is_native else max(8, min(24, round(image.height * .010)))
        left, top = max(0, int(x1*image.width/1000)-pad_x), max(0, int(y1*image.height/1000)-pad_y)
        right, bottom = min(image.width, math.ceil(x2*image.width/1000)+pad_x+1), min(image.height, math.ceil(y2*image.height/1000)+pad_y+1)
        # Source symbols/text may overlap. A neighbour is not a clipping boundary.
        return (left,top,right,bottom) if right>left and bottom>top else None

    valid_boxes = []
    box_labels = []
    labels_by_key = {'symbol_box_2d': 'Ký hiệu thiết bị', 'text_box_2d': 'Nhãn và thông số', 'tag_box_2d': 'Ký hiệu lộ'}
    seen = set()
    box_keys=[]
    for key in ('symbol_box_2d', 'text_box_2d', 'tag_box_2d'):
        box = region.get(key)
        if not box or len(box) != 4 or tuple(box) in seen:
            continue
        seen.add(tuple(box))
        valid_boxes.append(box)
        box_keys.append(key)
        box_labels.append(labels_by_key[key])

    if not valid_boxes:
        return []

    # Group nearby source parts even when another part (e.g. the tag) is distant.
    # A horizontal breaker and its adjacent rating stay one continuous source crop.
    groups = []
    for box, label, key in zip(valid_boxes, box_labels,box_keys):
        for group in ([] if region.get('shared_label') is True else groups):
            merged = [min(group['box'][0], box[0]), min(group['box'][1], box[1]),
                      max(group['box'][2], box[2]), max(group['box'][3], box[3])]
            gap_x=max(0,box[1]-group['box'][3],group['box'][1]-box[3])
            gap_y=max(0,box[0]-group['box'][2],group['box'][0]-box[2])
            near=max(6,min(box[2]-box[0],group['box'][2]-group['box'][0])*2)
            if merged[2]-merged[0] <= 240 and merged[3]-merged[1] <= 220 and max(gap_x,gap_y)<=near:
                group['box'] = merged
                group['labels'].append(label)
                group['keys'].append(key)
                break
        else:
            groups.append({'box': list(box), 'labels': [label],'keys':[key]})

    images = []
    for group in groups:
        pixels = crop_pixels(group['box'])
        if not pixels:
            continue
        crop = image.crop(pixels).convert('RGB')
        if ('symbol_box_2d' not in group['keys'] and str(region.get('geometry_source') or '').startswith('native_')):
            crop=trim_native_text(crop)
        crop.thumbnail((1200, 900), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        crop.save(output, format='PNG')
        label = ('Ghi chú vật tư và số lượng trên nguồn' if region.get('evidence_kind')=='material_note'
                 else 'Ký hiệu và thông số trên sơ đồ gốc' if len(group['labels']) > 1 else group['labels'][0])
        images.append({'kind': 'device', 'label': label,'source_parts':group['keys'],
            'evidence_image': 'data:image/png;base64,' + base64.b64encode(output.getvalue()).decode()})

    return images



def device_preview(image, region, *, tight=False):
    images = _device_preview(image, region, tight=tight)
    shared_relation = region.get('shared_label_relationship') or region.get('relationship_evidence')
    if region.get('shared_label') is True and shared_relation and region.get('symbol_box_2d') and region.get('text_box_2d'):
        boxes = [region['symbol_box_2d'], region['text_box_2d']]
        strip = [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]
        from app.services.ai.evidence_crops import evidence_crop_pixels
        pixels = evidence_crop_pixels(strip, *image.size)
        if pixels:
            crop = image.crop(pixels).convert('RGB')
            crop.thumbnail((1800, 1000), Image.Resampling.LANCZOS)
            output = io.BytesIO(); crop.save(output, format='PNG')
            images.append({'kind': 'relationship', 'label': 'Tiêu đề thông số chung và nhóm nhánh',
                'relationship_evidence': shared_relation,
                'evidence_image': 'data:image/png;base64,' + base64.b64encode(output.getvalue()).decode()})
    if region.get('load_verified') is True and region.get('load_box_2d') and region.get('relationship_evidence'):
        load = _device_preview(image, {'text_box_2d': region['load_box_2d'],
            'geometry_source':region.get('geometry_source')}, tight=tight)
        images.extend({**item, 'kind': 'load', 'label': 'Nhãn phụ tải: ' + str(region.get('load_label') or ''),
                       'relationship_evidence': region['relationship_evidence']} for item in load)
        # Keep a continuous source strip so the user can inspect the actual wire,
        # in addition to the readable close-ups of symbol/tag and load label.
        boxes = [region[k] for k in ('symbol_box_2d', 'text_box_2d', 'tag_box_2d', 'load_box_2d', 'group_reference_box_2d') if region.get(k)]
        strip = [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]
        from app.services.ai.evidence_crops import evidence_crop_pixels
        pixels = evidence_crop_pixels(strip, *image.size)
        if pixels:
            crop = image.crop(pixels).convert('RGB')
            crop.thumbnail((1800, 1000), Image.Resampling.LANCZOS)
            output = io.BytesIO(); crop.save(output, format='PNG')
            images.append({'kind': 'relationship', 'label': 'Đường nối thiết bị · lộ · phụ tải',
                'relationship_evidence': region['relationship_evidence'],
                'evidence_image': 'data:image/png;base64,' + base64.b64encode(output.getvalue()).decode()})
    unique=[];seen={}
    for item in images:
        key=item['evidence_image']
        if key in seen:
            if item.get('relationship_evidence'):seen[key]['relationship_evidence']=item['relationship_evidence']
            if item.get('kind')=='load':seen[key]['label']='Nhãn lộ và phụ tải: '+str(region.get('load_label') or '')
        else:seen[key]=item;unique.append(item)
    return unique
