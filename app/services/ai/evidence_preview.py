"""Compose checked source regions with whitespace-snapped continuity."""
import base64
import io
from PIL import Image


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
        return (max(0, int(x1*image.width/1000)-2), max(0, int(y1*image.height/1000)-2),
                min(image.width, int(x2*image.width/1000)+3), min(image.height, int(y2*image.height/1000)+3))

    valid_boxes = []
    box_labels = []
    labels_by_key = {'symbol_box_2d': 'Ký hiệu thiết bị', 'text_box_2d': 'Nhãn và thông số', 'tag_box_2d': 'Ký hiệu lộ'}
    seen = set()
    for key in ('symbol_box_2d', 'text_box_2d', 'tag_box_2d'):
        box = region.get(key)
        if not box or len(box) != 4 or tuple(box) in seen:
            continue
        seen.add(tuple(box))
        valid_boxes.append(box)
        box_labels.append(labels_by_key[key])

    if not valid_boxes:
        return []

    # 1. Nếu các phần (ký hiệu, nhãn, tag) nằm trong cùng một vùng mạch lân cận,
    # giữ ảnh liền mạch nguyên bản thay vì cắt xẻ làm đứt nét và chèn dải trắng giả lập.
    ymin = min(b[0] for b in valid_boxes)
    xmin = min(b[1] for b in valid_boxes)
    ymax = max(b[2] for b in valid_boxes)
    xmax = max(b[3] for b in valid_boxes)
    span_y = ymax - ymin
    span_x = xmax - xmin

    if span_y <= 240 and span_x <= 220:
        pixels = crop_pixels([ymin, xmin, ymax, xmax])
        if pixels:
            crop = image.crop(pixels).convert('RGB')
            crop.thumbnail((1200, 900), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            crop.save(output, format='PNG')
            return [{'kind': 'device', 'label': 'Ký hiệu và thông số trên sơ đồ gốc',
                     'evidence_image': 'data:image/png;base64,' + base64.b64encode(output.getvalue()).decode()}]

    # Distant parts stay separate source crops. Never stack them into a synthetic image.
    images = []
    for index, box in enumerate(valid_boxes):
        pixels = crop_pixels(box)
        if not pixels:
            continue
        crop = image.crop(pixels).convert('RGB')
        crop.thumbnail((1200, 900), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        crop.save(output, format='PNG')
        images.append({'kind': 'device', 'label': box_labels[index],
            'evidence_image': 'data:image/png;base64,' + base64.b64encode(output.getvalue()).decode()})
    return images



def device_preview(image, region, *, tight=False):
    images = _device_preview(image, region, tight=tight)
    if region.get('load_verified') is True and region.get('load_box_2d') and region.get('relationship_evidence'):
        load = _device_preview(image, {'text_box_2d': region['load_box_2d']}, tight=tight)
        images.extend({**item, 'kind': 'load', 'label': 'Nhãn phụ tải: ' + str(region.get('load_label') or ''),
                       'relationship_evidence': region['relationship_evidence']} for item in load)
        # Keep a continuous source strip so the user can inspect the actual wire,
        # in addition to the readable close-ups of symbol/tag and load label.
        boxes = [region[k] for k in ('symbol_box_2d', 'text_box_2d', 'tag_box_2d', 'load_box_2d') if region.get(k)]
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
    return images
