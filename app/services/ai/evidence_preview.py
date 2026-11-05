"""Compose checked source regions with whitespace-snapped continuity."""
import base64
import io
from PIL import Image


def device_preview(image, region):
    from app.services.ai.analysis_pipeline_service import AnalysisPipelineService as Pipeline

    valid_boxes = []
    seen = set()
    for key in ('symbol_box_2d', 'text_box_2d', 'tag_box_2d'):
        box = region.get(key)
        if not box or len(box) != 4 or tuple(box) in seen:
            continue
        seen.add(tuple(box))
        valid_boxes.append(box)

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
        pixels = Pipeline._evidence_crop_pixels([ymin, xmin, ymax, xmax], *image.size, image=image)
        if pixels:
            crop = image.crop(pixels).convert('RGB')
            crop.thumbnail((1200, 900), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            crop.save(output, format='PNG')
            return [{'kind': 'device', 'label': 'Ký hiệu và thông số trên sơ đồ gốc',
                     'evidence_image': 'data:image/png;base64,' + base64.b64encode(output.getvalue()).decode()}]

    # 2. Trường hợp nhãn và ký hiệu nằm quá xa nhau (ví dụ nhãn nằm ở bảng thông số đáy bản vẽ),
    # crop từng phần có bảo vệ bắt dính khoảng trắng rồi ghép nối.
    parts = []
    for box in valid_boxes:
        pixels = Pipeline._evidence_crop_pixels(box, *image.size, image=image)
        if pixels:
            parts.append(image.crop(pixels).convert('RGB'))

    if not parts:
        return []

    gap = max(8, round(image.height * .003))
    canvas = Image.new('RGB', (max(p.width for p in parts), sum(p.height for p in parts) + gap * (len(parts) - 1)), 'white')
    y = 0
    for part in parts:
        canvas.paste(part, ((canvas.width - part.width) // 2, y))
        y += part.height + gap
    canvas.thumbnail((1200, 900), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    canvas.save(output, format='PNG')
    return [{'kind': 'device', 'label': 'Ký hiệu và nhãn đối chiếu',
             'evidence_image': 'data:image/png;base64,' + base64.b64encode(output.getvalue()).decode()}]

