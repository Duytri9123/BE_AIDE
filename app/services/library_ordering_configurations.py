"""Documented ordering variants are separate from prices and CAD approval."""
import re
from app.services.ai.manufacturer_registry import canonical_brand

SOURCE='https://iportal.se.com/Contents/docs/0100CT1501_SEC-18.PDF'


def ordering_configurations(device):
    if device.get('brand_identification_status')!='verified' or canonical_brand(device.get('brand'))!='Schneider Electric':
        return []
    code=str(device.get('product_code') or '').upper()
    if not re.fullmatch(r'LC1F(?:115|150|185|225|265|330)',code):
        return []
    # Manufacturer tables 18.31/18.32, page 12; never substitute a coil spare-part SKU.
    coils=[('M7','220 V AC','40–400 Hz'),('BD','24 V DC','DC'),('MD','220 V DC','DC')]
    if code in {'LC1F115','LC1F150','LC1F185','LC1F225'}:
        coils.append(('M5','220 V AC','50 Hz'))
    return [{'sku':code+suffix,'specifications':{'Dòng sản phẩm':code,'Số cực':'3P (3NO)',
                'Ie AC-3 (≤440 V)':code[4:]+' A','Điện áp cuộn hút':voltage,'Tần số cuộn hút':frequency},
             'source_url':SOURCE,'source_page':12,'price_status':'not_quoted',
             'note':'Mã cấu hình theo tài liệu hãng. Cần kiểm tra khả năng cung ứng dòng cũ và giá đúng mã; cấu hình được chọn không tự phê duyệt hình học CAD.'}
            for suffix,voltage,frequency in coils]
