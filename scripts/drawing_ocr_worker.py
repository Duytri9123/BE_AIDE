"""Isolated PaddleOCR process. JSON request on stdin, JSON result in output file.

Keep third-party model/download logs out of the result protocol.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import sys

os.environ.setdefault('PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK', 'True')
os.environ.setdefault('OMP_NUM_THREADS', '4')


def same_label_location(first, second):
    if first['text'] != second['text']:
        return False
    a, b = first['box_2d'], second['box_2d']
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    union = area_a + area_b - intersection
    return union > 0 and intersection / union > .6


def read_image(path, language='vi'):
    import numpy as np
    from PIL import Image, ImageOps
    from paddleocr import PaddleOCR

    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert('RGBA')
        background = Image.new('RGBA', image.size, 'white')
        image = Image.alpha_composite(background, image).convert('RGB')
    width, height = image.size
    engine = PaddleOCR(
        lang=language, ocr_version='PP-OCRv5', device='cpu', cpu_threads=4,
        text_detection_model_name='PP-OCRv5_mobile_det',
        text_det_limit_side_len=1280, text_det_limit_type='max',
        use_doc_orientation_classify=False, use_doc_unwarping=False,
        use_textline_orientation=False,
        enable_mkldnn=os.environ.get('DRAWING_OCR_MKLDNN', 'false').lower() in {'1', 'true', 'yes'},
    )
    # Overlap preserves labels at tile boundaries. Never claim full resolution
    # if an unusually large sheet exceeds the bounded image size.
    tile, stride = 1280, 1120
    scale = min(1.0, 6000 / max(width, height))
    preview = image.resize((max(1, round(width * scale)), max(1, round(height * scale))))
    def starts(length):
        positions = [0]
        while positions[-1] + tile < length:
            positions.append(positions[-1] + stride)
        return positions
    xs, ys = starts(preview.width), starts(preview.height)
    rows = []
    for top in ys:
        for left in xs:
            crop = preview.crop((left, top, min(left + tile, preview.width), min(top + tile, preview.height)))
            for result in engine.predict(np.asarray(crop)[:, :, ::-1].copy()):
                for text, score, polygon in zip(result['rec_texts'], result['rec_scores'], result['rec_polys']):
                    if not str(text).strip() or not math.isfinite(float(score)):
                        continue
                    points = [[(float(x) + left) / scale, (float(y) + top) / scale] for x, y in polygon]
                    box = [min(p[0] for p in points), min(p[1] for p in points),
                           max(p[0] for p in points), max(p[1] for p in points)]
                    row = {'text': str(text), 'confidence': float(score), 'polygon': points,
                           'box_2d': [round(box[1] / height * 1000), round(box[0] / width * 1000),
                                      round(box[3] / height * 1000), round(box[2] / width * 1000)],
                           'engine': 'paddleocr', 'needs_visual_verification': True}
                    # Deduplicate overlap by location, preserving repeated labels
                    # elsewhere in the drawing.
                    previous = next((r for r in rows if same_label_location(r, row)), None)
                    if previous is None:
                        rows.append(row)
                    elif row['confidence'] > previous['confidence']:
                        previous.update(row)
    rows.sort(key=lambda r: (r['box_2d'][0], r['box_2d'][1]))
    return {'engine': 'paddleocr', 'width': width, 'height': height, 'rows': rows,
            'tile_count': len(xs) * len(ys), 'needs_visual_verification': True,
            'warnings': ['OCR image downscaled; inspect small labels on source.'] if scale < 1 else []}


if __name__ == '__main__':
    request = json.loads(sys.stdin.read())
    try:
        payload = read_image(request['path'], request.get('language', 'vi'))
    except Exception as exc:
        payload = {'error': f'{type(exc).__name__}: {exc}'}
    output = Path(request['output'])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    sys.exit(1 if 'error' in payload else 0)
