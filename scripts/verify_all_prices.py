#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kiểm tra tổng hợp việc cập nhật giá toàn bộ thiết bị
"""
import json
from pathlib import Path

# Đường dẫn gốc
BASE_PATH = Path(r"e:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB")

# Các thư mục không phải hãng
EXCLUDE_DIRS = ['design_references', '_agent_index', 'ProjectSamples', 'Form tủ']

def check_price_field(json_path):
    """Kiểm tra xem file có trường gia_ban không"""
    try:
        with open(json_path, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)

        if 'gia_ban' in data:
            gia_ban = data['gia_ban']
            return {
                'status': 'has_price',
                'don_gia': gia_ban.get('don_gia', ''),
                'trang_thai': gia_ban.get('trang_thai', ''),
                'hang': gia_ban.get('hang', ''),
                'ma_san_pham': gia_ban.get('ma_san_pham', '')
            }
        else:
            return {'status': 'no_field'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

def main():
    """Kiểm tra tổng hợp"""
    print("=" * 80)
    print("KIỂM TRA TỔNG HỢP CẬP NHẬT GIÁ THIẾT BỊ")
    print("=" * 80)

    # Tìm tất cả thư mục hãng
    manufacturer_dirs = [d for d in BASE_PATH.iterdir()
                        if d.is_dir() and d.name not in EXCLUDE_DIRS]

    total_devices = 0
    total_with_price_field = 0
    total_with_actual_price = 0
    total_no_price = 0
    total_missing_field = 0
    total_errors = 0

    manufacturer_stats = {}

    for mfr_dir in sorted(manufacturer_dirs):
        manufacturer = mfr_dir.name

        # Tìm tất cả file thong_tin_thiet_bi.json
        json_files = list(mfr_dir.rglob("thong_tin_thiet_bi.json"))

        if len(json_files) == 0:
            continue

        stats = {
            'total': len(json_files),
            'with_field': 0,
            'with_price': 0,
            'no_price': 0,
            'missing': 0,
            'error': 0
        }

        for json_file in json_files:
            result = check_price_field(json_file)

            if result['status'] == 'has_price':
                stats['with_field'] += 1
                if result['don_gia'] != '-':
                    stats['with_price'] += 1
                else:
                    stats['no_price'] += 1
            elif result['status'] == 'no_field':
                stats['missing'] += 1
            else:
                stats['error'] += 1

        manufacturer_stats[manufacturer] = stats

        total_devices += stats['total']
        total_with_price_field += stats['with_field']
        total_with_actual_price += stats['with_price']
        total_no_price += stats['no_price']
        total_missing_field += stats['missing']
        total_errors += stats['error']

    # In kết quả
    print(f"\nTổng số hãng/nhóm: {len(manufacturer_stats)}")
    print(f"Tổng số thiết bị: {total_devices}")
    print()
    print(f"✅ Có trường gia_ban: {total_with_price_field} ({total_with_price_field*100//total_devices if total_devices else 0}%)")
    print(f"   - Có giá thực tế: {total_with_actual_price}")
    print(f"   - Chưa có giá (-): {total_no_price}")
    print(f"❌ Thiếu trường gia_ban: {total_missing_field}")
    print(f"⚠️  Lỗi đọc file: {total_errors}")

    print("\n" + "=" * 80)
    print("CHI TIẾT THEO HÃNG:")
    print("=" * 80)
    print(f"{'Hãng':<40} {'Tổng':>6} {'Có field':>10} {'Có giá':>8} {'Chưa có':>9} {'Thiếu':>6}")
    print("-" * 80)

    for mfr, stats in sorted(manufacturer_stats.items()):
        status = "✅" if stats['missing'] == 0 else "❌"
        print(f"{status} {mfr:<38} {stats['total']:>6} {stats['with_field']:>10} {stats['with_price']:>8} {stats['no_price']:>9} {stats['missing']:>6}")

    print("=" * 80)

    if total_missing_field == 0 and total_errors == 0:
        print("\n✅ HOÀN THÀNH: Tất cả thiết bị đã có trường gia_ban!")
    else:
        print(f"\n⚠️  CẦN KIỂM TRA: {total_missing_field + total_errors} thiết bị cần xử lý")

    print()

if __name__ == "__main__":
    main()
