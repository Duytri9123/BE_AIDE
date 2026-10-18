"""
Script ví dụ: Cập nhật giá cho thiết bị LS dựa trên bảng giá tham khảo.
Đây là script mẫu để minh họa cách cập nhật giá thủ công.
"""

import json
from pathlib import Path
from datetime import datetime

# Đường dẫn
CATALOG_TB_ROOT = Path(__file__).resolve().parents[1] / 'data' / 'CatalogTB'

# Bảng giá tham khảo LS Electric (từ nguồn tìm kiếm web)
# Đây là giá ước tính - cần xác nhận với bảng giá chính thức
LS_PRICE_REFERENCE = {
    'BKD': {
        '63A': {
            'price_range': '150000-200000',
            'note': 'Isolator 3P 63A'
        },
        '80A': {
            'price_range': '180000-230000',
            'note': 'Isolator 3P 80A'
        },
        '100A': {
            'price_range': '220000-280000',
            'note': 'Isolator 3P 100A'
        },
        '125A': {
            'price_range': '280000-350000',
            'note': 'Isolator 3P 125A'
        }
    },
    'MC': {
        '9A': {
            'price': 120000,
            'note': 'Contactor MC-9 9A 5.5kW'
        },
        '12A': {
            'price': 135000,
            'note': 'Contactor MC-12 12A 5.5kW'
        },
        '18A': {
            'price': 165000,
            'note': 'Contactor MC-18 18A 7.5kW'
        },
        '22A': {
            'price': 195000,
            'note': 'Contactor MC-22 22A 11kW'
        },
        '32A': {
            'price': 245000,
            'note': 'Contactor MC-32 32A 15kW'
        }
    },
    'Metasol': {
        '100A': {
            'price_range': '450000-650000',
            'note': 'MCCB Metasol 3P 100A (phụ thuộc Icu)'
        },
        '225A': {
            'price_range': '850000-1200000',
            'note': 'MCCB Metasol 3P 225A'
        },
        '400A': {
            'price_range': '1800000-2500000',
            'note': 'MCCB Metasol 3P 400A'
        }
    },
    'TS': {
        '100A': {
            'price_range': '580000-780000',
            'note': 'Thermal Switch 3P 100A'
        },
        '160A': {
            'price_range': '720000-950000',
            'note': 'Thermal Switch 3P 160A'
        }
    }
}

# Thông tin nguồn
SOURCE_INFO = {
    'date': '2026-10-15',
    'sources': [
        'https://anhphatelectric.com/upload/file/bang-gia-ls-15-04-2026-7279.pdf',
        'https://etinco.vn/wp-content/uploads/2025/05/catalogue-ls-l-series-mcb-rccb-rcbo.pdf',
        'Tham khảo từ các đại lý LS Electric Việt Nam'
    ],
    'note': 'Giá tham khảo, chưa bao gồm VAT. Liên hệ đại lý để có giá chính xác.'
}


def create_price_info(price_data: dict, product_info: str) -> dict:
    """
    Tạo thông tin giá theo cấu trúc chuẩn.
    """
    if 'price_range' in price_data:
        don_gia = price_data['price_range']
        trang_thai = 'Có giá (phạm vi)'
        ghi_chu = f"{product_info}. {price_data.get('note', '')}. {SOURCE_INFO['note']}"
    elif 'price' in price_data:
        don_gia = price_data['price']
        trang_thai = 'Có giá'
        ghi_chu = f"{product_info}. {price_data.get('note', '')}. {SOURCE_INFO['note']}"
    else:
        don_gia = '-'
        trang_thai = 'Chưa có giá'
        ghi_chu = 'Liên hệ để được báo giá chính xác.'

    return {
        'don_gia': don_gia,
        'don_vi_tien_te': 'VND',
        'trang_thai': trang_thai,
        'ghi_chu': ghi_chu,
        'nguon_tham_khao': SOURCE_INFO['sources'],
        'ngay_cap_nhat': SOURCE_INFO['date']
    }


def update_device_price(file_path: Path, price_info: dict) -> bool:
    """
    Cập nhật giá cho một file thiết bị.
    """
    try:
        # Đọc file
        with open(file_path, 'r', encoding='utf-8') as f:
            profile = json.load(f)

        # Cập nhật giá
        profile['gia_ban'] = price_info

        # Ghi lại file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)

        device_name = profile.get('ten_san_pham', 'Unknown')
        print(f"  ✓ Cập nhật giá: {device_name}")
        print(f"    Giá: {price_info['don_gia']} VND")

        return True

    except Exception as e:
        print(f"  ✗ Lỗi: {file_path}: {e}")
        return False


def main():
    """
    Hàm chính - cập nhật giá cho các thiết bị LS mẫu.
    """
    print("=== CẬP NHẬT GIÁ MẪU CHO THIẾT BỊ LS ===\n")
    print(f"Nguồn tham khảo:")
    for src in SOURCE_INFO['sources']:
        print(f"  - {src}")
    print(f"\nNgày cập nhật: {SOURCE_INFO['date']}\n")

    updated_count = 0

    # Ví dụ 1: Cập nhật BKD
    bkd_path = CATALOG_TB_ROOT / 'LS' / 'ThietBi' / 'BKD' / 'thong_tin_thiet_bi.json'
    if bkd_path.exists():
        print("1. Cập nhật LS BKD Isolator:")
        price_info = create_price_info(
            LS_PRICE_REFERENCE['BKD']['63A'],
            'Isolator LS BKD 3P'
        )
        # Thêm thông tin cho nhiều dòng định mức
        price_info['ghi_chu'] += ' Giá dao động từ 150,000 VND (63A) đến 350,000 VND (125A) tùy theo dòng định mức.'

        if update_device_price(bkd_path, price_info):
            updated_count += 1
        print()

    # Ví dụ 2: Tìm và cập nhật các thiết bị MC (Contactor)
    print("2. Tìm và cập nhật các Contactor MC:")
    mc_folders = list((CATALOG_TB_ROOT / 'LS' / 'ThietBi').glob('MC_*'))

    for folder in mc_folders[:3]:  # Cập nhật 3 file đầu làm ví dụ
        catalog_file = folder / 'thong_tin_thiet_bi.json'
        if catalog_file.exists():
            # Đọc để lấy thông tin
            with open(catalog_file, 'r', encoding='utf-8') as f:
                profile = json.load(f)

            # Tạo giá mặc định
            price_info = create_price_info(
                {'price_range': '120000-300000', 'note': 'Contactor MC Series'},
                f"LS {profile.get('ten_san_pham', 'MC Contactor')}"
            )

            if update_device_price(catalog_file, price_info):
                updated_count += 1
    print()

    # Ví dụ 3: Cập nhật Metasol MCCB
    print("3. Tìm và cập nhật Metasol MCCB:")
    metasol_folders = list((CATALOG_TB_ROOT / 'LS' / 'ThietBi').glob('Metasol_*'))

    for folder in metasol_folders[:3]:  # Cập nhật 3 file đầu
        catalog_file = folder / 'thong_tin_thiet_bi.json'
        if catalog_file.exists():
            with open(catalog_file, 'r', encoding='utf-8') as f:
                profile = json.load(f)

            price_info = create_price_info(
                {'price_range': '450000-2500000',
                 'note': 'MCCB Metasol - giá phụ thuộc dòng định mức và khả năng cắt'},
                f"LS {profile.get('ten_san_pham', 'Metasol MCCB')}"
            )

            if update_device_price(catalog_file, price_info):
                updated_count += 1
    print()

    # Tóm tắt
    print(f"{'='*60}")
    print(f"Tổng kết:")
    print(f"  - Đã cập nhật: {updated_count} file")
    print(f"  - Nguồn: Bảng giá LS Electric và đại lý")
    print(f"\nLưu ý:")
    print(f"  - Đây là giá THAM KHẢO, chưa bao gồm VAT")
    print(f"  - Giá thực tế có thể khác tùy đại lý và số lượng")
    print(f"  - Cần xác nhận với bảng giá chính thức trước khi sử dụng")
    print(f"\nĐể cập nhật toàn bộ catalog:")
    print(f"  python scripts/sync_prices_to_catalog.py")


if __name__ == '__main__':
    main()
