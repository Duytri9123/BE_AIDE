"""Exact CAD labels and relative viewports. Coordinates are navigation, not dimensions."""
import hashlib
import re
import unicodedata
from copy import deepcopy
from functools import lru_cache
from pathlib import Path


def plain(value):
    return ''.join(c for c in unicodedata.normalize('NFD', str(value).upper().replace('Đ', 'D')) if not unicodedata.combining(c))


def validate_region(region):
    import math
    if region is None:
        return None
    if (not isinstance(region, (list, tuple)) or len(region) != 4
            or any(type(v) not in (float, int) or not math.isfinite(v) or not 0 <= v <= 1 for v in region)
            or region[0] >= region[2] or region[1] >= region[3]):
        raise ValueError('source_region phải là [trái,trên,phải,dưới] trong 0..1.')
    return list(region)


def region_world(bounds, region=None):
    left, bottom, right, top = bounds
    if region is None:
        return list(bounds)
    x1, y1, x2, y2 = validate_region(region)
    return [left + x1*(right-left), top-y2*(top-bottom), left+x2*(right-left), top-y1*(top-bottom)]


def region_normalized(bounds, window):
    left, bottom, right, top = bounds
    x1, y1, x2, y2 = window
    return [max(0, (x1-left)/(right-left)), max(0, (top-y2)/(top-bottom)),
            min(1, (x2-left)/(right-left)), min(1, (top-y1)/(top-bottom))]


@lru_cache(maxsize=8)
def _metadata(path, mtime, size):
    import ezdxf
    from ezdxf import bbox
    from app.services.ingestion.cad_parser import CadParserService
    doc = ezdxf.readfile(path)
    labels = CadParserService.extract_text_labels(doc)
    for n, row in enumerate(labels):
        row['text'] = CadParserService._sanitize_text(row['text'])
        row['id'] = 'cad_label_' + str(n)
    # An overview must cover every panel. Bare labels such as "MCB" are
    # frequently separated from their ratings, and cannot define a safe crop.
    if labels:
        focus = labels
        h = max(r['height'] for r in focus)
        left = min(r['x'] for r in focus); right = max(r['x'] + min(len(r['text']), 100)*r['height']*.55 for r in focus)
        bottom = min(r['y'] for r in focus)-h*5; top = max(r['y'] for r in focus)+h*3
    else:
        extent = bbox.extents(doc.modelspace(), fast=True)
        if not extent.has_data:
            return {'bounds': None, 'labels': labels, 'rows': [], 'panels': []}
        left, bottom, right, top = extent.extmin.x, extent.extmin.y, extent.extmax.x, extent.extmax.y
    pad = max(right-left, top-bottom, 1)*.015
    bounds = [left-pad, bottom-pad, right+pad, top+pad]
    titles = [r for r in labels if 'SO DO NGUYEN LY' in plain(r['text']) or 'SINGLE LINE' in plain(r['text'])]
    panels = []
    for t in titles:
        same_column = [q for q in titles if q['y'] < t['y'] and abs(q['x']-t['x']) < max(t['height'],q['height'])*20]
        lower = max((q['y']+q['height']*1.5 for q in same_column), default=bounds[1])
        window = [bounds[0], lower, bounds[2], min(bounds[3],t['y']+t['height']*3)]
        panels.append({'title': t['text'], 'region': region_normalized(bounds, window), 'title_id': t['id'], 'y_top': t['y'], 'y_bottom': lower})
    rows = []
    for anchor in labels:
        tag = anchor['text'].strip()
        if not re.fullmatch(r'(?:[A-ZĐ]{1,3}\d+(?:[./-][A-Z0-9]+)?|DP)', tag, re.I):
            continue
        near = [r for r in labels if abs(r['y']-anchor['y']) <= max(r['height'],anchor['height'],1)*1.6]
        ratings = [r for r in near if re.match(r'^(?:MCCB|MCB|RCBO|RCCB|ACB|CB)[ -]', plain(r['text']))]
        if len(ratings) != 1:
            continue  # Ambiguous rows must not establish a rating.
        candidates = [p for p in panels if p['y_bottom'] <= anchor['y'] <= p['y_top']]
        panel = min(candidates, key=lambda p:p['y_top']-anchor['y']) if candidates else None
        rows.append({'id': anchor['id'], 'tag': tag, 'panel': panel['title'] if panel else '',
                     'rating': ratings[0]['text'], 'rating_id': ratings[0]['id'],
                     'x': anchor['x'], 'y': anchor['y']})
    bound_ids = {r['rating_id'] for r in rows}
    for label in labels:
        if label['id'] in bound_ids or not re.match(r'^(?:MCCB|MCB|RCBO|RCCB|ACB|CB)[ -]', plain(label['text'])):
            continue
        candidates = [p for p in panels if p['y_bottom'] <= label['y'] <= p['y_top']]
        panel = min(candidates, key=lambda p:p['y_top']-label['y']) if candidates else None
        rows.append({'id':label['id'],'tag':'','panel':panel['title'] if panel else '',
                     'rating':label['text'],'rating_id':label['id'],'x':label['x'],'y':label['y']})
    from app.services.ingestion.cad_viewports import schematic_sheet_windows
    return {'bounds': bounds, 'labels': labels, 'rows': rows, 'panels': panels,
            'discovery_regions': schematic_sheet_windows(doc, labels, bounds)}


def cad_evidence(path, region=None):
    path = Path(path).resolve(); stat = path.stat()
    data = deepcopy(_metadata(str(path),stat.st_mtime_ns,stat.st_size))
    if data['bounds'] is None:
        return data
    left,bottom,right,top = region_world(data['bounds'],region)
    data['labels'] = [r for r in data['labels'] if left<=r['x']<=right and bottom<=r['y']<=top]
    data['rows'] = [r for r in data['rows'] if left<=r['x']<=right and bottom<=r['y']<=top]
    data['view_bounds'] = [left,bottom,right,top]
    data['region'] = region
    return data


def cad_transcript(evidence, max_chars=55000):
    # Original text only; never synthesize incomers, device counts, or ratings.
    lines = ['Nhãn CAD nguyên văn; tọa độ chỉ để định vị tương đối, không phải kích thước chính xác.']
    lines += [f"{r['id']} X={r['x']:g} Y={r['y']:g}: {r['text']}" for r in evidence['labels']]
    lines += ['Hàng nhãn xác định không mơ hồ: '+str(evidence['rows'])]
    result='\n'.join(lines)
    return result[:max_chars]+ ('\n[TRUNCATED: cần đọc vùng nhỏ hơn]' if len(result)>max_chars else '')


def signature(text):
    text=plain(text).replace(',', '.')
    result={}
    for value,unit in re.findall(r'(?<![\w.])(\d+(?:\.\d+)?)\s*(KA|MA|A|V|KV|P)(?!\w)',text):
        result.setdefault(unit,set()).add(float(value))
    return result


def audit_cad_ratings(evidence, devices):
    """Check only uniquely bound label rows. A blurry visual read cannot override them."""
    issues=[]; checked=[]
    for d in devices:
        # A model may quote the correct ratio and still rewrite it in spec.
        # Compare only labels actually present in this selected source region.
        quote = str(d.get('observed_text') or d.get('evidence') or '')
        referenced = [r['text'] for r in evidence['labels'] if plain(r['text']) in plain(quote)]
        ratio_pattern = r'(?<!\d)(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*A?'
        ratios = {m for text in referenced for m in re.findall(ratio_pattern, text, re.I)}
        actual_ratios = set(re.findall(ratio_pattern, str(d.get('spec') or ''), re.I))
        if len(ratios) == 1 and actual_ratios and not actual_ratios.issubset(ratios):
            issues.append(f"{d.get('tag') or d.get('name')}: tỷ số nhãn CAD được trích là {next(iter(ratios))}, khác thông số {d.get('spec')}.")
        panel=plain(d.get('panel_code') or d.get('panel') or '')
        ids=set(d.get('source_evidence_ids') or [])
        choices=[r for r in evidence['rows'] if ids.intersection({r['id'],r['rating_id']})
                 and (not panel or panel in plain(r['panel']))]
        if not choices:
            match=re.search(r'\b([A-Z]{1,3}\d+|DP)\b',plain(d.get('tag','')))
            if match:
                choices=[r for r in evidence['rows'] if plain(r['tag'])==match[1]
                         and (not panel or panel in plain(r['panel']))]
            elif any(term in plain(d.get('tag','')) for term in ('TONG','INCOMER','DAU VAO')):
                choices=[r for r in evidence['rows'] if not r['tag'] and panel and panel in plain(r['panel'])]
        if len(choices)!=1:
            continue
        row=choices[0]; expected=signature(row['rating']); actual=signature(str(d.get('name',''))+' '+str(d.get('spec','')))
        checked.append({'tag':row['tag'],'panel':row['panel'],'rating':row['rating'],'source_id':row['rating_id']})
        for unit,values in actual.items():
            if unit in expected and not values.issubset(expected[unit]):
                issues.append(f"{d.get('panel_code','')} / {row['tag']}: nhãn {row['rating_id']} ghi nguyên văn {row['rating']}; không được đổi thành {d.get('spec','')}.")
    return {'passed':not issues,'issues':issues,'checked':checked}
