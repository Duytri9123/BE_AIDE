"""Inventory CAD work and current commercial choices without guessing a price."""
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.services.catalogtb_browser import _build_browser_data
from app.services.ai.takeoff_pricebook import published_rows
from app.services.ai.manufacturer_registry import canonical_brand
from scripts.audit_library_price_gaps import audit
from scripts.audit_library_catalog_status import status

ROOT = Path(__file__).resolve().parents[1]


def main():
    # Audit disk contents synchronously: the UI snapshot can be stale.
    devices = _build_browser_data()['items']
    prices = published_rows()
    result = audit(devices, prices)
    linked = {r['id']: r['choices'] for r in result['linked']}
    gaps = {r['id']: r['reason'] for r in result['gaps']}
    counts = defaultdict(Counter)
    details = []
    for d in devices:
        brand = canonical_brand(d.get('brand')) or 'Chưa xác định'
        c = counts[brand]
        c['cad'] += 1
        c['with_price_options'] += int(d['id'] in linked)
        c['verified_price_gap'] += int(d['id'] in gaps)
        c['identity_pending'] += int(d.get('brand_identification_status') not in {'verified', 'not_applicable'})
        details.append(dict(id=d['id'], name=d.get('display'), brand=brand,
                            code=d.get('product_code'), catalog_status=status(d),
                            price_options=linked.get(d['id'], 0), price_gap=gaps.get(d['id'])))
    for p in prices:
        counts[canonical_brand(p.get('brand'))]['published_prices'] += 1
    before = json.loads((ROOT/'tmp/web_catalog_offers.before-20261016.json').read_text(encoding='utf-8'))['items']
    after = json.loads((ROOT/'app/data/web_catalog_offers.json').read_text(encoding='utf-8'))['items']
    old = {r['source_url']: r for r in before}
    changes = defaultdict(Counter)
    for r in after:
        previous = old.get(r['source_url'])
        c = changes[canonical_brand(r.get('brand'))]
        if previous is None:
            c['added'] += 1
        elif r.get('checked_at') != previous.get('checked_at'):
            c['rechecked'] += 1
            c['price_changed'] += int(r.get('price') != previous.get('price'))
    payload = dict(checked_at=datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat(),
                   cad_count=len(devices), linked_count=len(linked), verified_price_gap_count=len(gaps),
                   published_price_count=len(prices), brands=dict(counts), source_changes=dict(changes), items=details)
    dest = ROOT/'docs/cad-price-completion-2026-10-16'
    dest.with_suffix('.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    lines = ['# Kiểm kê CAD và giá ngày 16/10/2026', '',
             f"Đã kiểm kê {len(devices)} CAD; {len(linked)} có lựa chọn giá phù hợp; {len(gaps)} CAD đã xác nhận hãng vẫn thiếu lựa chọn giá.",
             'Lựa chọn giá theo cấu hình không phải giá tự động chốt cho CAD. Các CAD chưa đủ hãng/mã và bản vẽ lắp đặt vẫn cần xử lý riêng.', '',
             '| Hãng | CAD | CAD có lựa chọn giá | CAD đã rõ hãng thiếu giá | Cần xác minh hãng | Dòng giá công bố |',
             '| --- | ---: | ---: | ---: | ---: | ---: |']
    for brand, c in sorted(counts.items()):
        lines.append('| '+' | '.join([brand]+[str(c[k]) for k in ('cad','with_price_options','verified_price_gap','identity_pending','published_prices')])+' |')
    lines += ['', '## Giá bán đã kiểm tra và bổ sung', '', '| Hãng | Dòng mới | Kiểm tra lại | Đổi giá |', '| --- | ---: | ---: | ---: |']
    for brand, c in sorted(changes.items()):
        if sum(c.values()):
            lines.append(f"| {brand} | {c['added']} | {c['rechecked']} | {c['price_changed']} |")
    lines += ['', 'Nguồn và thời điểm kiểm tra nằm trong app/data/web_catalog_offers.json. Tài liệu bảng giá chưa nhập nằm trong app/data/catalog_documents.json. Chưa có giá công bố hoặc chưa khớp mã/cấu hình thì giữ thiếu, không điền giá ước lượng.', '',
              '## CAD còn cần xử lý', '', '| ID | Thiết bị | Trạng thái catalog | Lý do thiếu giá |', '| --- | --- | --- | --- |']
    for d in details:
        if not d['price_options']:
            lines.append('| '+' | '.join(str(d.get(k) or '').replace('|','/') for k in ('id','name','catalog_status','price_gap'))+' |')
    dest.with_suffix('.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in payload.items() if k not in {'items','brands','source_changes'}}, ensure_ascii=False))
    print(json.dumps(dict(changes), ensure_ascii=False))


if __name__ == '__main__':
    main()
