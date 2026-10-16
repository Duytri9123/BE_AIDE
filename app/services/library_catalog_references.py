"""Manufacturer catalog facts, independent of price coverage or CAD approval."""
import re
from app.services.ai.manufacturer_registry import canonical_brand


def catalog_reference(device):
    if device.get('brand_identification_status') != 'verified':
        return None
    brand = canonical_brand(device.get('brand'))
    code = re.sub(r'[^A-Z0-9]', '', str(device.get('product_code') or '').upper())
    if brand == 'ABB' and code == 'OVRT12544050':
        return {'model': 'OVR T1 25 440-50', 'source_url': 'https://new.abb.com/docs/librariesprovider63/niederspannungsprodukte/downloads/40_ovr-ger%C3%A4te-2010.pdf?sfvrsn=2',
                'specifications': {'Mã đặt hàng': '2CTB815101R9300', 'Loại': 'SPD Type 1', 'Số cực': '1P', 'Un': '400 V', 'Uc': '440 V', 'Iimp (10/350 µs)': '25 kA', 'Ifi': '50 kA', 'Up': '2 kV'},
                'note': 'Catalog dòng cũ; thông số sản phẩm không phụ thuộc việc đã có giá. Cần kiểm tra khả năng cung ứng khi đặt hàng.'}
    if str(brand).lower() == 'lightstar' and code == 'KBF43':
        return {'model': 'KBF-43', 'source_url': 'https://lightstar.co.jp/product/view&idx=200',
                'specifications': {'Loại': 'Biến dòng 3 lõi', 'Cửa sổ': '30 × 20 mm', 'Tần số': '50/60 Hz', 'Dòng thứ cấp lựa chọn': '1 A hoặc 5 A', 'Khung MCCB tham chiếu': '400AF'},
                'note': 'Chọn tỷ số biến dòng, VA và cấp chính xác theo công trình. Chưa tự chọn các thông số này từ hình CAD.'}
    return None
