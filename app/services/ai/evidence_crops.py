"""Source evidence helpers without catalog or analysis startup costs."""
import logging
from typing import Any, Dict, List, Optional, Tuple
from app.schemas.ai import ExtractedDeviceSchema
logger = logging.getLogger(__name__)

def apply_verified_boxes(devices: List[ExtractedDeviceSchema], payload: Any, require_symbols: bool = False) -> None:
    """Join verifier results by request-local identity, never by repeated tags."""
    candidates = payload.get("boxes", []) if isinstance(payload, dict) else []
    by_id: Dict[str, list] = {}
    for candidate in candidates if isinstance(candidates, list) else []:
        if isinstance(candidate, dict):
            by_id.setdefault(str(candidate.get("device_id", "")), []).append(candidate)
    for index, device in enumerate(devices):
        matches = by_id.get(str(index), [])
        if len(matches) != 1 or matches[0].get("verified") is not True:
            device.box_2d = None
            device.evidence_image = None
            device.evidence_images = []
            pcode = getattr(device, 'panel_code', None) or ''
            device.evidence_region = {'status': 'unverified',
                'verification_status': 'needs_review',
                'reason': f'Đọc danh mục từ sơ đồ tủ {pcode}; chưa xác minh được ký hiệu và nhãn riêng.' if pcode else 'Đọc danh mục từ ảnh tủ; chưa xác minh được vùng ký hiệu và nhãn của riêng thiết bị.'}
            continue
        device.box_2d = None
        device.evidence_image = None
        device.evidence_images = []
        device.evidence_region = {'status':'unverified',
            'reason':'Đọc danh mục từ ảnh tủ; chưa xác minh được vùng ký hiệu và nhãn của riêng thiết bị.'}
        box = matches[0].get("box_2d")
        if require_symbols and (matches[0].get('symbol_verified') is not True or not matches[0].get('symbol_box_2d')):
            continue
        if require_symbols and not matches[0].get('text_box_2d') and not matches[0].get('audit_observed'):
            continue
        if matches[0].get('symbol_verified') is False:
            continue
        if str(device.category).upper() == 'LIGHT' and device.quantity == 1:
            duplicate = any(other is not device and str(other.category).upper() == 'LIGHT'
                and other.quantity == 1 and other.tag != device.tag
                and by_id.get(str(other_index), [{}])[0].get('symbol_box_2d') == matches[0].get('symbol_box_2d')
                for other_index, other in enumerate(devices))
            if duplicate:
                continue
        if matches[0].get('symbol_box_2d'):
            if not matches[0].get('text_box_2d'):
                matches[0]['text_box_2d'] = matches[0]['symbol_box_2d']
            try:
                symbol = ExtractedDeviceSchema.normalize_evidence_box(matches[0]['symbol_box_2d'])
                text = ExtractedDeviceSchema.normalize_evidence_box(matches[0]['text_box_2d'])
            except (TypeError, ValueError, OverflowError):
                continue
            if not symbol or not text:
                continue
            tag_box = ExtractedDeviceSchema.normalize_evidence_box(matches[0].get('tag_box_2d'))
            parts = [symbol, text] + ([tag_box] if tag_box else [])
            box = [min(p[0] for p in parts), min(p[1] for p in parts),
                   max(p[2] for p in parts), max(p[3] for p in parts)]

        try:
            device.box_2d = ExtractedDeviceSchema.normalize_evidence_box(box)
            if not device.box_2d:continue
            device.evidence_region.update(status='verified',reason='Đã đối chiếu ký hiệu và nhãn trên vùng ảnh nguồn.')
            device.evidence_region.update(coordinate_space='normalized_1000', box_2d=list(device.box_2d))
            for key in ('symbol_box_2d','text_box_2d','tag_box_2d'):
                device.evidence_region[key] = ExtractedDeviceSchema.normalize_evidence_box(matches[0].get(key))
            quad = matches[0].get('branch_quad')
            if isinstance(quad, list) and len(quad) == 4 and all(
                isinstance(pt, list) and len(pt) == 2 and all(isinstance(v, (int, float)) and 0 <= v <= 1000 for v in pt)
                for pt in quad):
                device.evidence_region['branch_quad'] = quad
                device.evidence_region['branch_header_separate'] = matches[0].get('branch_header_separate') is True
            load_box = matches[0].get('load_box_2d')
            if matches[0].get('load_verified') is True and load_box and matches[0].get('relationship_evidence'):
                device.evidence_region = {**(getattr(device, 'evidence_region', None) or {}),
                    'load_box_2d': ExtractedDeviceSchema.normalize_evidence_box(load_box),
                    'load_verified': True, 'load_label': str(matches[0].get('load_label') or ''),
                    'relationship_evidence': str(matches[0]['relationship_evidence'])}
        except (TypeError, ValueError, OverflowError):
            pass

def evidence_crop_pixels(box: List[int], width: int, height: int, image: Any = None) -> Optional[Tuple[int, int, int, int]]:
    """Crop around the verified symbol and label, with safe context margin and whitespace snapping."""
    if not box or len(box) != 4 or width <= 0 or height <= 0:
        return None
    try:
        ymin, xmin, ymax, xmax = [max(0.0, min(1000.0, float(value))) for value in box]
    except (TypeError, ValueError):
        return None
    if xmax <= xmin or ymax <= ymin:
        return None
    left, top = int(xmin * width / 1000), int(ymin * height / 1000)
    right, bottom = int(xmax * width / 1000), int(ymax * height / 1000)
    if right <= left or bottom <= top:
        return None

    # Adequate context margin for electrical symbols, wire leads, and complete character bounds
    bw = right - left
    bh = bottom - top
    pad_x = max(14, round(width * 0.006), round(bw * 0.16))
    pad_y = max(12, round(height * 0.005), round(bh * 0.16))

    left = max(0, left - pad_x)
    top = max(0, top - pad_y)
    right = min(width, right + pad_x)
    bottom = min(height, bottom + pad_y)

    # Enforce minimum dimension so crops are not narrow slivers
    min_dim = max(48, round(min(width, height) * 0.025))
    if (right - left) < min_dim:
        diff = min_dim - (right - left)
        left = max(0, left - diff // 2)
        right = min(width, right + (diff - diff // 2))
    if (bottom - top) < min_dim:
        diff = min_dim - (bottom - top)
        top = max(0, top - diff // 2)
        bottom = min(height, bottom + (diff - diff // 2))

    # Whitespace / Ink Snapping
    if image is not None:
        try:
            import numpy as np
            from app.services.ai.evidence_geometry import expand_to_whitespace
            img_np = np.asarray(image)
            left, top, right, bottom = expand_to_whitespace(img_np, left, top, right, bottom, max_pad=40, min_pad=4)
        except Exception as snap_err:
            logger.debug(f"Whitespace snap error: {snap_err}")

    return left, top, right, bottom
