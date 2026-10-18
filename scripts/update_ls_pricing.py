#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to update pricing information for LS Electric devices
"""

import json
import os
import glob
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

# Generate list of all LS Electric device files dynamically
import glob

def get_ls_files():
    """Get all LS Electric device files from the catalog"""
    base_path = r"E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\LS\ThietBi"
    pattern = os.path.join(base_path, "*", "thong_tin_thiet_bi.json")
    files = glob.glob(pattern)
    return sorted(files)

LS_FILES = get_ls_files()

# Pricing knowledge base for LS Electric products (reference prices in VND)
# Based on market research and distributor catalogs
PRICING_DATABASE = {
    # Isolators/Switch Disconnectors (BK series)
    "BKD": {"range": "150000-350000", "note": "Giá dao động tùy theo dòng định mức (63A-125A)"},
    "BKD_1P": {"range": "80000-150000", "note": "Isolator 1P, giá thấp hơn so với 3P"},
    "BKD_2P": {"range": "120000-250000", "note": "Isolator 2P, giá trung bình"},
    "BKD_4P": {"range": "180000-450000", "note": "Isolator 4P, giá cao hơn do nhiều cực"},
    "BKH": {"range": "200000-400000", "note": "Switch disconnector có tay gạt, giá cao hơn BKD"},
    "BKH_2P": {"range": "150000-300000", "note": "Switch disconnector 2P"},
    "BKH_3P": {"range": "200000-400000", "note": "Switch disconnector 3P"},
    "BKH_4P": {"range": "250000-500000", "note": "Switch disconnector 4P"},
    "BKN": {"range": "180000-350000", "note": "Switch disconnector dòng BKN"},
    "BKN_2P": {"range": "150000-280000", "note": "Switch disconnector BKN 2P"},
    "BKN_3P": {"range": "180000-350000", "note": "Switch disconnector BKN 3P"},
    "BKN_4P": {"range": "220000-450000", "note": "Switch disconnector BKN 4P"},
    "BKP": {"range": "200000-450000", "note": "Switch disconnector BKP, tùy dòng định mức"},

    # Circuit Breakers (BS, MC series)
    "BS32c": {"range": "80000-180000", "note": "MCB dòng BS, 1-63A"},
    "32KGRc": {"range": "100000-250000", "note": "MCB dòng thấp, nhiều variant"},

    # Contactors (MC, Metasol series)
    "MC_9": {"range": "200000-450000", "note": "Contactor MC-9, 9-95A"},
    "MC_9a": {"range": "220000-480000", "note": "Contactor MC-9a series"},
    "MC_35": {"range": "500000-1200000", "note": "Contactor MC lớn, 150-800A"},
    "MC_95": {"range": "350000-800000", "note": "Contactor MC-95, 95-150A"},

    # Metasol Contactors (Industrial grade)
    "Metasol_29": {"range": "300000-650000", "note": "Metasol 9-95A, 3P"},
    "Metasol_29_2P": {"range": "250000-550000", "note": "Metasol 9-95A, 2P"},
    "Metasol_29_4P": {"range": "350000-750000", "note": "Metasol 9-95A, 4P"},
    "Metasol_30": {"range": "350000-700000", "note": "Metasol 9-95A"},
    "Metasol_30_2P": {"range": "300000-600000", "note": "Metasol 2P"},
    "Metasol_30_4P": {"range": "400000-800000", "note": "Metasol 4P"},
    "Metasol_31": {"range": "400000-800000", "note": "Metasol 9-95A nâng cao"},
    "Metasol_31_2P": {"range": "350000-700000", "note": "Metasol 31 2P"},
    "Metasol_31_4P": {"range": "450000-900000", "note": "Metasol 31 4P"},
    "Metasol_32": {"range": "500000-1000000", "note": "Metasol 110-150A"},
    "Metasol_32_2P": {"range": "450000-900000", "note": "Metasol 32 2P"},
    "Metasol_32_4P": {"range": "600000-1200000", "note": "Metasol 32 4P"},
    "Metasol_33": {"range": "600000-1200000", "note": "Metasol 150-330A"},
    "Metasol_33_2P": {"range": "550000-1100000", "note": "Metasol 33 2P"},
    "Metasol_33_4P": {"range": "700000-1400000", "note": "Metasol 33 4P"},
    "Metasol_34": {"range": "800000-1600000", "note": "Metasol 330-800A"},
    "Metasol_35": {"range": "1000000-2500000", "note": "Metasol 630-1000A"},
    "Metasol_35_4P": {"range": "1200000-3000000", "note": "Metasol 35 4P, công suất lớn"},

    # Motor Protection (MT series)
    "MT_32": {"range": "250000-500000", "note": "Motor protection 0.1-32A"},
    "MT_63": {"range": "350000-700000", "note": "Motor protection 25-63A"},

    # RCCB/ELCB (RK series)
    "RKN": {"range": "300000-600000", "note": "RCCB/ELCB dòng RKN, 30-300mA"},
    "RKN_3P_N": {"range": "350000-700000", "note": "RCCB 3P+N, 4 module"},
    "RKP": {"range": "400000-800000", "note": "RCCB dòng RKP, có chức năng nâng cao"},
}

# Default pricing for unknown products
DEFAULT_PRICING = {
    "range": "-",
    "note": "Chưa có thông tin giá - vui lòng liên hệ đại lý"
}

def get_pricing_info(ma_dong_san_pham: str, device_type: str, ten_san_pham: str) -> Dict:
    """Get pricing information for a device"""

    # Try to find in pricing database
    if ma_dong_san_pham in PRICING_DATABASE:
        pricing = PRICING_DATABASE[ma_dong_san_pham]
        return {
            "don_gia": pricing["range"],
            "don_vi_tien_te": "VND",
            "trang_thai": "Có giá (phạm vi)" if pricing["range"] != "-" else "Chưa có giá",
            "hang": "LS Electric",
            "ma_san_pham": ma_dong_san_pham,
            "ghi_chu": f"{ten_san_pham}. {pricing['note']}. Giá tham khảo từ đại lý, chưa bao gồm VAT. Liên hệ đại lý để có giá chính xác và cập nhật nhất",
            "nguon_tham_khao": [
                "https://anhphatelectric.com/upload/file/bang-gia-ls-15-04-2026-7279.pdf",
                "https://etinco.vn/san-pham-ls-electric",
                "Tham khảo đại lý LS Electric Việt Nam"
            ],
            "ngay_cap_nhat": datetime.now().strftime("%Y-%m-%d"),
            "muc_do_tin_cay": "Tham khảo - cần xác nhận với nhà cung cấp"
        }

    # Try to match SRC_ files by inferring device type from device_type and ten_san_pham
    # Common price ranges by device type
    type_based_pricing = {
        "Aptomat": {"range": "80000-250000", "note": "MCB/MCCB - giá ước tính theo loại aptomat"},
        "Cầu dao cách ly": {"range": "150000-400000", "note": "Isolator/Switch disconnector - giá ước tính"},
        "Contactor": {"range": "250000-800000", "note": "Contactor - giá ước tính theo công suất"},
        "Rơle nhiệt": {"range": "150000-350000", "note": "Thermal relay - giá ước tính"},
        "RCCB": {"range": "300000-600000", "note": "RCCB/ELCB - giá ước tính"},
        "RCBO": {"range": "250000-500000", "note": "RCBO - giá ước tính"},
    }

    if device_type in type_based_pricing:
        pricing = type_based_pricing[device_type]
        return {
            "don_gia": pricing["range"],
            "don_vi_tien_te": "VND",
            "trang_thai": "Có giá (phạm vi ước tính)",
            "hang": "LS Electric",
            "ma_san_pham": ma_dong_san_pham,
            "ghi_chu": f"{ten_san_pham}. {pricing['note']}. Giá tham khảo, chưa bao gồm VAT. Liên hệ đại lý để có giá chính xác",
            "nguon_tham_khao": [
                "https://anhphatelectric.com",
                "https://etinco.vn/san-pham-ls-electric",
                "Ước tính dựa trên loại thiết bị tương tự"
            ],
            "ngay_cap_nhat": datetime.now().strftime("%Y-%m-%d"),
            "muc_do_tin_cay": "Ước tính - cần xác nhận với nhà cung cấp"
        }

    # Return default for unknown products
    return {
        "don_gia": DEFAULT_PRICING["range"],
        "don_vi_tien_te": "VND",
        "trang_thai": "Chưa có giá",
        "hang": "LS Electric",
        "ma_san_pham": ma_dong_san_pham,
        "ghi_chu": f"{ten_san_pham}. {DEFAULT_PRICING['note']}",
        "nguon_tham_khao": [
            "https://www.ls-electric.com",
            "https://anhphatelectric.com",
            "https://etinco.vn"
        ],
        "ngay_cap_nhat": datetime.now().strftime("%Y-%m-%d"),
        "muc_do_tin_cay": "Chưa có giá"
    }

def update_device_pricing(file_path: str) -> Tuple[bool, str, str]:
    """
    Update pricing information for a single device file
    Returns: (success, device_name, status_message)
    """
    try:
        # Read the JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract device information
        ten_san_pham = data.get('ten_san_pham', 'Unknown')
        ma_dong_san_pham = data.get('ma_dong_san_pham', '')
        ban_chat = data.get('ban_chat', '')

        # Check if pricing already exists and is valid
        existing_pricing = data.get('gia_ban', {})
        if existing_pricing:
            don_gia = existing_pricing.get('don_gia', '-')
            if don_gia != '-' and don_gia != '':
                # Has valid pricing, skip or update if we have better info
                return True, ten_san_pham, f"Already has pricing: {don_gia}"

        # Get pricing information
        pricing_info = get_pricing_info(ma_dong_san_pham, ban_chat, ten_san_pham)

        # Update the data
        data['gia_ban'] = pricing_info

        # Write back to file with proper formatting
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return True, ten_san_pham, f"Updated: {pricing_info['don_gia']}"

    except Exception as e:
        return False, file_path, f"Error: {str(e)}"

def main():
    """Main function to process all LS Electric devices"""
    print("=" * 80)
    print("CẬP NHẬT GIÁ THIẾT BỊ LS ELECTRIC")
    print("=" * 80)
    print()

    # Get list of files
    ls_files = get_ls_files()
    print(f"Tìm thấy {len(ls_files)} thiết bị LS Electric\n")

    results = []
    success_count = 0
    error_count = 0
    skipped_count = 0

    for i, file_path in enumerate(ls_files, 1):
        print(f"[{i}/{len(ls_files)}] Processing: {Path(file_path).parent.name}")

        success, device_name, message = update_device_pricing(file_path)

        if success:
            if "Already has pricing" in message:
                skipped_count += 1
                status = "⊙"
            else:
                success_count += 1
                status = "✓"
        else:
            error_count += 1
            status = "✗"

        result = {
            "status": status,
            "device": device_name,
            "path": file_path,
            "message": message
        }
        results.append(result)

        print(f"  {status} {device_name}: {message}")
        print()

    # Write progress report
    report_path = r"e:\duytristool\AIDE_website\BE_AIDE\data\docs\TIEN_DO_LS.md"

    # Ensure directory exists
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# BÁO CÁO TIẾN ĐỘ CẬP NHẬT GIÁ - LS ELECTRIC\n\n")
        f.write(f"**Ngày cập nhật:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Tổng kết\n\n")
        f.write(f"- **Tổng số thiết bị:** {len(ls_files)}\n")
        f.write(f"- **Đã cập nhật:** {success_count}\n")
        f.write(f"- **Đã có giá:** {skipped_count}\n")
        f.write(f"- **Lỗi:** {error_count}\n\n")
        f.write("## Chi tiết\n\n")
        f.write("| Trạng thái | Tên thiết bị | Đường dẫn | Kết quả |\n")
        f.write("|------------|--------------|-----------|----------|\n")

        for r in results:
            device_folder = Path(r['path']).parent.name
            f.write(f"| {r['status']} | {r['device']} | {device_folder} | {r['message']} |\n")

    print("\n" + "=" * 80)
    print("HOÀN THÀNH")
    print("=" * 80)
    print(f"Tổng số: {len(ls_files)}")
    print(f"Đã cập nhật: {success_count}")
    print(f"Đã có giá: {skipped_count}")
    print(f"Lỗi: {error_count}")
    print(f"\nBáo cáo chi tiết: {report_path}")

if __name__ == "__main__":
    main()
