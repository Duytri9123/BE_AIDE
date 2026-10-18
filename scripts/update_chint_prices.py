#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cập nhật giá thiết bị CHINT
"""
import json
import os
from pathlib import Path
from datetime import datetime

# Đường dẫn gốc
BASE_PATH = Path(r"e:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\Chint\ThietBi")

def update_device_price(json_path):
    """Cập nhật giá cho một thiết bị"""
    try:
        # Đọc file JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Kiểm tra nếu đã có gia_ban thì bỏ qua
        if 'gia_ban' in data:
            print(f"  ✓ Đã có giá: {json_path.parent.name}")
            return 'skipped'

        # Lấy thông tin thiết bị
        hang = data.get('hang_xac_nhan', 'CHINT')
        ma_san_pham = data.get('ma_dong_san_pham', '')
        ten_san_pham = data.get('ten_san_pham', '')

        # Thêm trường gia_ban với giá trị mặc định (chưa có giá)
        data['gia_ban'] = {
            "don_gia": "-",
            "don_vi_tien_te": "VND",
            "trang_thai": "Chưa có giá",
            "hang": hang,
            "ma_san_pham": ma_san_pham,
            "ghi_chu": f"Chưa tìm được báo giá tin cậy cho {ten_san_pham}. Cần liên hệ đại lý CHINT tại Việt Nam để có giá chính xác.",
            "nguon_tham_khao": [
                "https://chintglobal.com",
                "https://www.alibaba.com"
            ],
            "ngay_cap_nhat": datetime.now().strftime("%Y-%m-%d"),
            "muc_do_tin_cay": "Tham khảo - cần xác nhận với nhà cung cấp"
        }

        # Ghi lại file
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"  ✓ Cập nhật: {json_path.parent.name} - {ma_san_pham}")
        return 'updated'

    except Exception as e:
        print(f"  ✗ Lỗi {json_path.parent.name}: {str(e)}")
        return 'error'

def main():
    """Xử lý tất cả thiết bị CHINT"""
    print("=" * 60)
    print("CẬP NHẬT GIÁ THIẾT BỊ CHINT")
    print("=" * 60)

    # Tìm tất cả file thong_tin_thiet_bi.json
    json_files = list(BASE_PATH.rglob("thong_tin_thiet_bi.json"))
    total = len(json_files)

    print(f"\nTìm thấy {total} thiết bị CHINT\n")

    stats = {'updated': 0, 'skipped': 0, 'error': 0}

    for i, json_file in enumerate(json_files, 1):
        print(f"[{i}/{total}] {json_file.parent.name}")
        result = update_device_price(json_file)
        stats[result] += 1

    print("\n" + "=" * 60)
    print("KẾT QUẢ:")
    print(f"  - Đã cập nhật: {stats['updated']}")
    print(f"  - Đã có giá: {stats['skipped']}")
    print(f"  - Lỗi: {stats['error']}")
    print("=" * 60)

if __name__ == "__main__":
    main()
