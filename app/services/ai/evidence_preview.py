"""Compose checked source regions without including the space between them."""
import base64
import io
from PIL import Image


def device_preview(image, region):
    from app.services.ai.analysis_pipeline_service import AnalysisPipelineService as Pipeline
    parts = []
    seen = set()
    for key in ('symbol_box_2d', 'text_box_2d', 'tag_box_2d'):
        box = region.get(key)
        if not box or tuple(box) in seen:
            continue
        seen.add(tuple(box))
        pixels = Pipeline._evidence_crop_pixels(box, *image.size)
        if pixels:
            parts.append(image.crop(pixels).convert('RGB'))
    if not parts:
        return []
    gap = max(8, round(image.height * .003))
    canvas = Image.new('RGB', (max(p.width for p in parts), sum(p.height for p in parts) + gap * (len(parts)-1)), 'white')
    y = 0
    for part in parts:
        canvas.paste(part, ((canvas.width-part.width)//2, y))
        y += part.height + gap
    canvas.thumbnail((1200, 900), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    canvas.save(output, format='PNG')
    return [{'kind': 'device', 'label': 'Ký hiệu và nhãn · các vùng nguồn riêng',
             'evidence_image': 'data:image/png;base64,' + base64.b64encode(output.getvalue()).decode()}]
