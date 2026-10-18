#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to update ABB device prices
Date: 2026-10-16
Task: Add gia_ban field to all ABB device JSON files
"""

import json
import os
from pathlib import Path
from datetime import date

# List of all ABB device JSON files
ABB_FILES = [
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\A1_1P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\A1_2P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\A1_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\A1_4P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\A2_1P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\A2_2P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\A2_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\A2_4P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\A3_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\A3_4P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\ABB_D03_C2_I08\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\AX115_30_11_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\AX12_30_10_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\AX150_30_11_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\AX18_30_10_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\AX25_30_10_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\AX32_30_10_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\AX40_30_10_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\AX50_30_11_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\AX65_30_11_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\AX80_30_11_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\AX95_30_11_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\AX9_30_10_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\CAL5_11\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\DS201L_1P+N\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\FH202_2P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\FH204_4P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\OVR_T1_25_255\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\OVR_T1_25_440_50\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\OVR_T1_2L_25_255\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\OVR_T1_2L_25_255_TS\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\OVR_T1_3L_25_255\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\OVR_T1_3L_25_255_TS\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\OVR_T1_3N_25_255\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\OVR_T1_3N_25_255_TS\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\OVR_T1_4L_25_255\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\OVR_T1_4L_25_255_TS\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\S200_1P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\S200_2P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\S200_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\S200_4P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\S280UC_K_1P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\S280UC_K_2P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\S280UC_K_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\S280UC_K_4P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\SH200_1P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\SH200_2P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\SH200_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\SH200_4P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\T1_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\T1_4P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\T2_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\T2_4P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\T3_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\T3_4P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\T4_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\T4_4P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\T5_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\T5_4P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\T6_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\T6_4P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\T7M_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\T7M_4P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\T7_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\T7_4P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\TA25_DU\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\TA42_DU\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\TA75_DU\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\TA80_DU\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\VE5_1\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\VE5_2\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\XT1_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\XT1_4P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\XT2_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\XT2_4P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\XT3_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\XT3_4P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\XT4_3P\thong_tin_thiet_bi.json",
    r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\ABB\ThietBi\XT4_4P\thong_tin_thiet_bi.json"
]

def update_single_file(file_path):
    """Update a single JSON file with gia_ban field"""
    try:
        # Read existing JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract product code for reference
        ma_san_pham = data.get('ma_dong_san_pham', 'N/A')
        ten_san_pham = data.get('ten_san_pham', 'N/A')

        # Check if gia_ban already exists
        if 'gia_ban' in data:
            print(f"⚠️  {Path(file_path).parent.name}: Đã có gia_ban, bỏ qua")
            return 'skipped'

        # Add gia_ban field
        data['gia_ban'] = {
            "don_gia": "-",
            "don_vi_tien_te": "VND",
            "trang_thai": "Chưa có giá",
            "hang": "ABB",
            "ma_san_pham": ma_san_pham,
            "ghi_chu": "Chưa tìm được giá tin cậy từ nguồn chính thức ABB hoặc đại lý VN. Cần liên hệ đại lý để báo giá chính xác.",
            "nguon_tham_khao": [
                "https://new.abb.com/low-voltage",
                "https://new.abb.com/products"
            ],
            "ngay_cap_nhat": str(date.today()),
            "muc_do_tin_cay": "Tham khảo - cần xác nhận với nhà cung cấp"
        }

        # Write back to file with proper formatting
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✓ {Path(file_path).parent.name}: {ten_san_pham}")
        return 'success'

    except Exception as e:
        print(f"✗ {Path(file_path).parent.name}: Lỗi - {str(e)}")
        return 'error'

def main():
    """Main function to update all ABB files"""
    print("=" * 70)
    print("CẬP NHẬT GIÁ THIẾT BỊ ABB")
    print("=" * 70)
    print(f"Tổng số file: {len(ABB_FILES)}")
    print(f"Ngày cập nhật: {date.today()}")
    print("=" * 70)
    print()

    success_count = 0
    skip_count = 0
    error_count = 0

    for file_path in ABB_FILES:
        result = update_single_file(file_path)
        if result == 'success':
            success_count += 1
        elif result == 'skipped':
            skip_count += 1
        else:
            error_count += 1

    print()
    print("=" * 70)
    print("KẾT QUẢ")
    print("=" * 70)
    print(f"✓ Thành công: {success_count}")
    print(f"⚠ Bỏ qua: {skip_count}")
    print(f"✗ Lỗi: {error_count}")
    print(f"Tổng: {len(ABB_FILES)}")
    print("=" * 70)

    return success_count, skip_count, error_count

if __name__ == "__main__":
    main()
