"""Inventory every active CAD and distinguish original-model vs reference prices."""
import json
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from app.services.catalogtb_browser import _build_browser_data
from app.services.ai.takeoff_pricebook import published_rows
from app.services.ai.manufacturer_registry import canonical_brand
from app.services.library_price_matching import configuration_links
from app.services.library_reference_prices import reference_rows,price_index

ROOT=Path(__file__).resolve().parents[1]


def main():
    devices=_build_browser_data()['items'];prices=published_rows();index=price_index(prices)
    makers=defaultdict(list)
    for r in prices:makers[canonical_brand(r['brand'])].append(r)
    details=[];counts=Counter()
    for d in devices:
        own=configuration_links(d,makers[canonical_brand(d.get('brand'))])
        refs=reference_rows(d,index)
        status='source_configuration_prices' if own else 'documented_reference_prices' if refs else 'no_published_reference_price'
        counts[status]+=1
        codes=list(dict.fromkeys(r['sku'] for r in refs))
        details.append(dict(id=d['id'],name=d['display'],brand=d.get('brand'),type=d['type'],source_code=d.get('product_code'),
                            status=status,price_choices=len(own) or len(refs),reference_models=codes))
    data=dict(checked_at=datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat(),cad_count=len(devices),
              published_price_count=len(prices),counts=dict(counts),items=details)
    (ROOT/'docs/all-library-price-update-2026-10-16.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    lines=['# Rà soát mã và giá toàn bộ thư viện — 16/10/2026','',
           f"Đã rà {len(devices)} CAD đang hoạt động; {len(prices)} dòng giá công bố.",'',
           f"- {counts['source_configuration_prices']} CAD có lựa chọn giá theo hãng/mã nguồn.",
           f"- {counts['documented_reference_prices']} CAD có giá của mã catalog tham khảo; không thay đổi mã hay thông số của CAD nguồn.",
           f"- {counts['no_published_reference_price']} CAD chưa có giá công bố trong các nguồn đã đọc.",'',
           'Dữ liệu giá hiện được đọc trực tiếp cho cả bảng giá chung, bảng giá trong thư viện và từng dòng thông tin catalog. Không còn ghi cứng --- khi có giá theo mã. Mã catalog tham khảo hiển thị riêng với mã nguồn.','',
           'Đã kiểm tra lại 22 hãng tại PLE (1.991 dòng), 8 nguồn Etinco (134 dòng). Thêm bảng công bố Morele 2021, LightStar 2022, SmartGen/Deep Sea 2023 và giá cầu đấu/lọc gió. Bảng lịch sử giữ nguyên năm, VAT, nguồn và ngày đọc; không trình bày thành báo giá mới.','',
           'Biến áp CHINT: sửa 22 NDK từ ACCESSORY thành TRANSFORMER; có mã, VA và giá trong bảng CHINT 2026. NDK là dòng tham khảo của mẫu CAD chưa có nhãn model; cần chọn đúng điện áp và công suất.','',
           '## Các mục còn thiếu giá trong nguồn đã đọc','',
           '| ID | Thiết bị | Mã trên nguồn |','| --- | --- | --- |']
    for d in details:
        if d['status']=='no_published_reference_price':
            lines.append('| '+' | '.join(str(d.get(k) or 'Chưa ghi trên nguồn').replace('|','/') for k in ['id','name','source_code'])+' |')
    (ROOT/'docs/all-library-price-update-2026-10-16.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in data.items() if k!='items'},ensure_ascii=False))


if __name__=='__main__':main()
