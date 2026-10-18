"""
Script để đồng bộ giá từ database/pricebook vào file thong_tin_thiet_bi.json.
Nếu tìm thấy giá phù hợp thì cập nhật, nếu không thì giữ nguyên dấu gạch (-).
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import sys

# Đường dẫn
CATALOG_TB_ROOT = Path(__file__).resolve().parents[1] / 'data' / 'CatalogTB'
DB_PATH = Path(__file__).resolve().parents[1] / 'webbaogia.db'
PRICEBOOK_PATH = Path(__file__).resolve().parents[1] / 'app' / 'data' / 'supplier_pricebooks.json'


def load_pricebook_data() -> List[Dict[str, Any]]:
    """Tải dữ liệu giá từ file JSON pricebook."""
    try:
        if PRICEBOOK_PATH.exists():
            with open(PRICEBOOK_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('items', [])
    except Exception as e:
        print(f"Không thể tải pricebook: {e}")
    return []


def load_db_prices() -> Dict[str, Any]:
    """Tải dữ liệu giá từ database."""
    prices = {}
    try:
        if DB_PATH.exists():
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Lấy thông tin từ device_models
            cur.execute("""
                SELECT dm.id, dm.sku, dm.name, dm.price, dm.discount_pct,
                       ds.name as series_name, dc.name as category_name,
                       b.name as brand_name
                FROM device_models dm
                JOIN device_series ds ON dm.device_series_id = ds.id
                JOIN device_categories dc ON ds.device_category_id = dc.id
                JOIN brands b ON ds.brand_id = b.id
                WHERE dm.price > 0
            """)

            for row in cur.fetchall():
                key = f"{row['brand_name']}_{row['name']}"
                prices[key] = {
                    'sku': row['sku'],
                    'name': row['name'],
                    'brand': row['brand_name'],
                    'price': row['price'],
                    'discount_pct': row['discount_pct'],
                    'series': row['series_name'],
                    'category': row['category_name']
                }

            conn.close()
            print(f"Đã tải {len(prices)} giá từ database")
    except Exception as e:
        print(f"Không thể tải giá từ database: {e}")

    return prices


def find_price_for_device(device_profile: Dict[str, Any],
                          db_prices: Dict[str, Any],
                          pricebook_items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Tìm giá phù hợp cho thiết bị từ các nguồn.

    Returns:
        Dict chứa thông tin giá hoặc None nếu không tìm thấy
    """
    device_name = device_profile.get('ten_san_pham', '')
    brand = device_profile.get('hang_xac_nhan', '')
    product_code = device_profile.get('ma_dong_san_pham', '')

    if not device_name or not brand:
        return None

    # Tìm trong database
    key = f"{brand}_{device_name}"
    if key in db_prices:
        price_info = db_prices[key]
        return {
            'don_gia': price_info['price'],
            'don_vi_tien_te': 'VND',
            'trang_thai': 'Có giá',
            'sku': price_info['sku'],
            'giam_gia_pct': price_info['discount_pct'],
            'ghi_chu': f"Giá từ database - {price_info['series']}",
            'nguon_tham_khao': ['Database webbaogia.db'],
            'ngay_cap_nhat': datetime.now().strftime('%Y-%m-%d')
        }

    # Tìm trong pricebook
    for item in pricebook_items:
        item_brand = item.get('brand', '').lower()
        item_name = item.get('item_name', '').lower()

        if brand.lower() in item_brand and product_code and product_code.lower() in item_name:
            price = item.get('price')
            if price and price != '-':
                return {
                    'don_gia': price,
                    'don_vi_tien_te': item.get('currency', 'VND'),
                    'trang_thai': 'Có giá',
                    'ma_hang': item.get('material_code', '-'),
                    'ghi_chu': f"Giá từ pricebook - {item.get('source', 'Unknown')}",
                    'nguon_tham_khao': [item.get('source_page', 'Supplier pricebook')],
                    'ngay_cap_nhat': item.get('effective_date') or datetime.now().strftime('%Y-%m-%d')
                }

    return None


def update_catalog_with_prices(file_path: Path,
                               db_prices: Dict[str, Any],
                               pricebook_items: List[Dict[str, Any]],
                               dry_run: bool = False) -> bool:
    """
    Cập nhật giá vào file catalog.
    """
    try:
        # Đọc file
        with open(file_path, 'r', encoding='utf-8') as f:
            profile = json.load(f)

        # Tìm giá
        price_info = find_price_for_device(profile, db_prices, pricebook_items)

        device_name = profile.get('ten_san_pham', 'Unknown')
        relative_path = file_path.relative_to(CATALOG_TB_ROOT)

        if price_info:
            # Cập nhật giá
            profile['gia_ban'] = price_info
            print(f"  💰 {relative_path}")
            print(f"      {device_name}: {price_info.get('don_gia', '-')} {price_info.get('don_vi_tien_te', 'VND')}")
        else:
            # Giữ dấu gạch nếu chưa có
            if 'gia_ban' not in profile:
                profile['gia_ban'] = {
                    'don_gia': '-',
                    'don_vi_tien_te': 'VND',
                    'trang_thai': 'Chưa có giá',
                    'ghi_chu': 'Liên hệ để được báo giá chính xác.',
                    'nguon_tham_khao': [],
                    'ngay_cap_nhat': None
                }
            print(f"  - {relative_path} - {device_name}: Không tìm thấy giá")

        # Ghi file
        if not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(profile, f, ensure_ascii=False, indent=2)

        return True

    except Exception as e:
        print(f"  ✗ Lỗi: {file_path}: {e}")
        return False


def main():
    """Hàm chính."""
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print("=== CHẾ ĐỘ KIỂM TRA (DRY RUN) ===\n")
    else:
        print("=== ĐỒNG BỘ GIÁ VÀO CATALOG ===\n")

    # Tải dữ liệu giá
    print("Đang tải dữ liệu giá...")
    db_prices = load_db_prices()
    pricebook_items = load_pricebook_data()
    print(f"Đã tải {len(pricebook_items)} mục từ pricebook\n")

    # Tìm tất cả file catalog
    catalog_files = list(CATALOG_TB_ROOT.rglob('thong_tin_thiet_bi.json'))
    print(f"Tìm thấy {len(catalog_files)} file catalog\n")

    # Xử lý
    success = 0
    with_price = 0
    without_price = 0

    for file_path in sorted(catalog_files):
        if update_catalog_with_prices(file_path, db_prices, pricebook_items, dry_run):
            success += 1

            # Kiểm tra xem có tìm thấy giá không
            with open(file_path, 'r', encoding='utf-8') as f:
                profile = json.load(f)
                if profile.get('gia_ban', {}).get('don_gia', '-') != '-':
                    with_price += 1
                else:
                    without_price += 1

    # Tóm tắt
    print(f"\n{'='*60}")
    print(f"Tổng kết:")
    print(f"  - Tổng số file: {len(catalog_files)}")
    print(f"  - Xử lý thành công: {success}")
    print(f"  - Có giá: {with_price}")
    print(f"  - Chưa có giá (dấu gạch): {without_price}")

    if dry_run:
        print(f"\nĐể áp dụng, chạy lại không có --dry-run")
    else:
        print(f"\nHoàn tất!")


if __name__ == '__main__':
    main()
