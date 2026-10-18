#!/usr/bin/env python3
"""
Script để quét toàn bộ catalog và tìm các thiết bị chưa có thông tin giá
"""
import json
import os
from pathlib import Path
from collections import defaultdict

# Đường dẫn thư mục catalog
CATALOG_ROOT = Path(__file__).parent.parent / "data" / "CatalogTB"

def scan_catalog_for_missing_prices():
    """Quét catalog và tìm thiết bị chưa có giá"""

    missing_prices = defaultdict(list)
    devices_with_prices = defaultdict(list)
    total_devices = 0

    # Duyệt qua tất cả các hãng
    for brand_dir in CATALOG_ROOT.iterdir():
        if not brand_dir.is_dir():
            continue

        brand_name = brand_dir.name

        # Bỏ qua các thư mục đặc biệt
        if brand_name.startswith('_') or brand_name in ['design_references', 'ProjectSamples']:
            continue

        # Tìm thư mục ThietBi
        thiet_bi_dir = brand_dir / "ThietBi"
        if not thiet_bi_dir.exists():
            continue

        # Duyệt qua từng thiết bị
        for device_dir in thiet_bi_dir.iterdir():
            if not device_dir.is_dir():
                continue

            info_file = device_dir / "thong_tin_thiet_bi.json"
            if not info_file.exists():
                continue

            total_devices += 1

            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                device_name = data.get('ten_san_pham', device_dir.name)
                model = data.get('ma_dong_san_pham', device_dir.name)

                # Kiểm tra có trường gia_ban không
                if 'gia_ban' not in data:
                    missing_prices[brand_name].append({
                        'path': str(info_file.relative_to(CATALOG_ROOT.parent.parent)),
                        'name': device_name,
                        'model': model,
                        'category': data.get('ban_chat', 'N/A')
                    })
                else:
                    devices_with_prices[brand_name].append({
                        'name': device_name,
                        'model': model,
                        'price': data['gia_ban'].get('don_gia', 'N/A')
                    })

            except Exception as e:
                print(f"❌ Lỗi đọc file {info_file}: {e}")

    return missing_prices, devices_with_prices, total_devices

def generate_report():
    """Tạo báo cáo chi tiết"""

    print("🔍 QUÉT CATALOG THIẾT BỊ - TÌM THIẾT BỊ CHƯA CÓ GIÁ")
    print("=" * 80)

    missing, with_prices, total = scan_catalog_for_missing_prices()

    # Thống kê tổng quan
    total_missing = sum(len(devices) for devices in missing.values())
    total_with_prices = sum(len(devices) for devices in with_prices.values())

    print(f"\n📊 TỔNG QUAN:")
    print(f"   Tổng số thiết bị: {total}")
    print(f"   ✅ Đã có giá: {total_with_prices} ({total_with_prices/total*100:.1f}%)")
    print(f"   ❌ Chưa có giá: {total_missing} ({total_missing/total*100:.1f}%)")

    # Chi tiết theo hãng
    print(f"\n📋 CHI TIẾT THEO HÃNG:")
    print("-" * 80)

    for brand in sorted(missing.keys()):
        devices = missing[brand]
        with_price_count = len(with_prices.get(brand, []))
        total_brand = len(devices) + with_price_count

        print(f"\n🏢 {brand}:")
        print(f"   Tổng: {total_brand} | Có giá: {with_price_count} | Chưa có giá: {len(devices)}")

        # Nhóm theo loại thiết bị
        by_category = defaultdict(list)
        for device in devices:
            by_category[device['category']].append(device)

        for category, items in sorted(by_category.items()):
            print(f"\n   📦 {category} ({len(items)} thiết bị):")
            for item in items[:5]:  # Hiển thị tối đa 5 thiết bị mỗi loại
                print(f"      - {item['name']} ({item['model']})")
            if len(items) > 5:
                print(f"      ... và {len(items) - 5} thiết bị khác")

    # Xuất file JSON để xử lý tiếp
    output_file = Path(__file__).parent / "devices_missing_prices.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': {
                'total_devices': total,
                'with_prices': total_with_prices,
                'missing_prices': total_missing,
                'scan_date': '2026-10-15'
            },
            'missing_by_brand': missing,
            'with_prices_by_brand': with_prices
        }, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Đã lưu báo cáo chi tiết: {output_file}")
    print("\n✅ QUÉT HOÀN TẤT!")

    return missing, with_prices, total

def export_priority_list():
    """Xuất danh sách ưu tiên cập nhật (các hãng phổ biến)"""

    missing, _, _ = scan_catalog_for_missing_prices()

    priority_brands = ['LS', 'Schneider', 'ABB', 'Mitsubishi', 'Chint', 'Shihlin']

    priority_list = []
    for brand in priority_brands:
        if brand in missing:
            for device in missing[brand]:
                priority_list.append({
                    'brand': brand,
                    'name': device['name'],
                    'model': device['model'],
                    'category': device['category'],
                    'path': device['path']
                })

    output_file = Path(__file__).parent / "priority_update_list.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(priority_list, f, ensure_ascii=False, indent=2)

    print(f"\n📌 Đã xuất danh sách ưu tiên ({len(priority_list)} thiết bị): {output_file}")

if __name__ == "__main__":
    generate_report()
    export_priority_list()
