"""Build a conservative, auditable catalog of empty enclosure drawings.

This is a data quality filter, not an IEC 61439 certification. Original DXFs and
manifest remain available for manual review, but rejected sheets are not served
as cabinet templates.
"""
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import ezdxf


ROOT = Path(__file__).resolve().parents[1] / 'data' / 'cabinet_templates' / 'formtu'
EQUIPMENT_BLOCK = re.compile(
    r'(^|\W)(mccb|mcb|acb|rcbo|rccb|contactor|relay|timer|plc|vfd|ats|'
    r'breaker|fuse|ls\s*\d+af|nxm|nxb|bkn|den\s*(xanh|do|vang)|e.stop)(\W|$)', re.I
)
EQUIPMENT_LABEL = re.compile(
    r'\b(mccb|mcb|acb|rcbo|rccb|contactor|relay|timer|plc|vfd|ats|'
    r'cau chi|bien tan|khoi dong tu|dong ho|bo tri thiet bi|e.stop)\b', re.I
)


def plain(value):
    value = unicodedata.normalize('NFD', value).replace('đ', 'd').replace('Đ', 'D')
    return ''.join(char for char in value if unicodedata.category(char) != 'Mn').lower()


def assess(item):
    reasons = []
    dims = item.get('dimensions')
    if item.get('status') != 'source' or not dims:
        reasons.append('thiếu kích thước hoặc nguồn cần kiểm tra')
    elif not (300 <= dims['height'] <= 3000 and 250 <= dims['width'] <= 3000
              and 150 <= dims['depth'] <= 1200):
        reasons.append('kích thước vỏ bất thường')
    if item.get('kind') not in ('indoor', 'outdoor'):
        reasons.append('chưa xác định môi trường lắp đặt')
    if any(EQUIPMENT_LABEL.search(plain(label)) for label in item.get('labels', [])):
        reasons.append('nhãn thể hiện bố trí hoặc thiết bị điện')
    source = ROOT / item['filename']
    if not source.is_file():
        reasons.append('thiếu file CAD nguồn')
    else:
        doc = ezdxf.readfile(source)
        blocks = [entity.dxf.name for entity in doc.modelspace().query('INSERT')]
        if any(EQUIPMENT_BLOCK.search(plain(block)) for block in blocks):
            reasons.append('block thiết bị điện đã đặt trong bản vẽ')
        if len(doc.modelspace()) < 40:
            reasons.append('bản vẽ quá ít hình học để xác nhận vỏ')
    return reasons


def main():
    source = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
    accepted, rejected = [], []
    for item in source['items']:
        reasons = assess(item)
        if reasons:
            rejected.append({'id': item['id'], 'filename': item['filename'], 'reasons': reasons})
        else:
            accepted.append(item)
    (ROOT / 'curated_manifest.json').write_text(json.dumps({
        'source_file': source['source_file'],
        'policy': 'Vỏ tủ trống; kích thước hợp lý; nguồn CAD có hình học; chưa xác nhận IEC/IP/IK bằng thử nghiệm.',
        'items': accepted,
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / 'excluded_manifest.json').write_text(json.dumps({
        'source_file': source['source_file'], 'items': rejected,
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Accepted {len(accepted)}; excluded {len(rejected)}')
    print(Counter(reason for row in rejected for reason in row['reasons']))


if __name__ == '__main__':
    main()
