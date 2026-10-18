#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cập nhật giá thiết bị các hãng còn lại
"""
import json
import os
from pathlib import Path
from datetime import datetime

# Đường dẫn gốc
BASE_PATH = Path(r"e:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB")

# Các hãng đã xử lý - bỏ qua
PROCESSED_MANUFACTURERS = [
    'LS', 'Schneider', 'ABB', 'Mitsubishi', 'Chint', 'Shihlin',
    'design_references', '_agent_index', 'ProjectSamples'
]

def update_device_price(json_path, manufacturer):
    """Cập nhật giá cho một thiết bị"""
    try:
        # Đọc file JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Kiểm tra nếu đã có gia_ban thì bỏ qua
        if 'gia_ban' in data:
            return 'skipped'

        # Lấy thông tin thiết bị
        hang = data.get('hang_xac_nhan', manufacturer)
        if not hang:
            hang = data.get('nhom', manufacturer)

        ma_san_pham = data.get('ma_dong_san_pham', '')
        if not ma_san_pham:
            ma_san_pham = data.get('ten_kieu', '')

        ten_san_pham = data.get('ten_san_pham', '')

        # Thêm trường gia_ban với giá trị mặc định (chưa có giá)
        data['gia_ban'] = {
            "don_gia": "-",
            "don_vi_tien_te": "VND",
            "trang_thai": "Chưa có giá",
            "hang": hang,
            "ma_san_pham": ma_san_pham,
            "ghi_chu": f"Chưa tìm được báo giá tin cậy cho {ten_san_pham}. Cần liên hệ nhà cung cấp để có giá chính xác.",
            "nguon_tham_khao": [],
            "ngay_cap_nhat": datetime.now().strftime("%Y-%m-%d"),
            "muc_do_tin_cay": "Tham khảo - cần xác nhận với nhà cung cấp"
        }

        # Ghi lại file
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return 'updated'

    except Exception as e:
        print(f"  ✗ Lỗi {json_path}: {str(e)}")
        return 'error'

def main():
    """Xử lý tất cả thiết bị của các hãng còn lại"""
    print("=" * 80)
    print("CẬP NHẬT GIÁ THIẾT BỊ - CÁC HÃNG CÒN LẠI")
    print("=" * 80)

    # Tìm các thư mục hãng
    manufacturer_dirs = [d for d in BASE_PATH.iterdir()
                        if d.is_dir() and d.name not in PROCESSED_MANUFACTURERS]

    total_stats = {'updated': 0, 'skipped': 0, 'error': 0}
    manufacturer_stats = {}

    for mfr_dir in sorted(manufacturer_dirs):
        manufacturer = mfr_dir.name
        print(f"\n{'='*80}")
        print(f"HÃNG: {manufacturer}")
        print('='*80)

        # Tìm tất cả file thong_tin_thiet_bi.json
        json_files = list(mfr_dir.rglob("thong_tin_thiet_bi.json"))
        count = len(json_files)

        if count == 0:
            print(f"  Không có thiết bị")
            continue

        print(f"  Tìm thấy {count} thiết bị")

        stats = {'updated': 0, 'skipped': 0, 'error': 0}

        for json_file in json_files:
            result = update_device_price(json_file, manufacturer)
            stats[result] += 1
            total_stats[result] += 1

        print(f"  → Cập nhật: {stats['updated']}, Đã có: {stats['skipped']}, Lỗi: {stats['error']}")
        manufacturer_stats[manufacturer] = stats

    print("\n" + "=" * 80)
    print("TỔNG KẾT:")
    print("=" * 80)
    print(f"Tổng số thiết bị đã cập nhật: {total_stats['updated']}")
    print(f"Tổng số thiết bị đã có giá: {total_stats['skipped']}")
    print(f"Tổng số lỗi: {total_stats['error']}")
    print(f"Tổng cộng: {sum(total_stats.values())}")

    print("\nChi tiết theo hãng:")
    for mfr, stats in sorted(manufacturer_stats.items()):
        total = sum(stats.values())
        print(f"  - {mfr}: {total} thiết bị (cập nhật: {stats['updated']}, đã có: {stats['skipped']}, lỗi: {stats['error']})")

    print("=" * 80)

if __name__ == "__main__":
    main()
