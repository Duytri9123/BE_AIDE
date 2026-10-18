"""Inventory catalog evidence for every CAD without conflating it with price."""
import sys
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.catalogtb_browser import browser_data

def status(d):
    if d.get('catalog_reference'):
        return 'Đã bổ sung thông số catalog đối chiếu'
    if d.get('type') in {'MOUNTING_TEMPLATE', 'ASSEMBLY_REFERENCE'}:
        return 'Bản vẽ lắp đặt/cụm: cần nhận diện thành phần'
    if d.get('brand_identification_status') == 'not_applicable':
        return 'Phụ kiện phổ thông: không bắt buộc hãng/giá'
    if d.get('brand_identification_status') != 'verified':
        return 'Cần xác minh hãng/mã từ bản vẽ và catalog'
    if not d.get('product_code'):
        return 'Đã ghi hãng; cần mã/dòng thiết bị'
    if not d.get('manufacturer_document'):
        return 'Đã ghi hãng và mã/dòng; cần nguồn catalog'
    return 'Có hãng, mã/dòng và tài liệu; cần đối chiếu cấu hình cụ thể'

if __name__ == '__main__':
    items = browser_data()['items']
    counts = Counter(status(d) for d in items)
    lines = ['# Kiểm kê bằng chứng catalog toàn thư viện', '',
             'Thời điểm: ' + datetime.now(timezone.utc).isoformat(), '',
             f'Đã kiểm kê {len(items)} CAD. Giá không phải điều kiện để có hồ sơ catalog. Liên kết tài liệu có sẵn không đồng nghĩa đã đọc và xác minh mọi cấu hình/hình học.', '',
             '| Trạng thái | Số CAD |', '| --- | ---: |']
    lines += [f'| {s} | {n} |' for s,n in sorted(counts.items())]
    lines += ['', '| ID | Thiết bị | Mã/dòng | Trạng thái | Tài liệu |', '| --- | --- | --- | --- | --- |']
    for d in sorted(items,key=lambda d:d['display']):
        source=(d.get('catalog_reference') or {}).get('source_url') or d.get('manufacturer_document') or ''
        cells=[d['id'],d['display'],d.get('product_code') or '',status(d),source]
        lines.append('| ' + ' | '.join(str(v).replace('|','/').replace('\n',' ') for v in cells) + ' |')
    (ROOT/'docs/library-catalog-verification.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(len(items),dict(counts))
