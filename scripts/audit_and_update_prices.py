"""
Script tổng hợp: Kiểm tra và cập nhật giá cho toàn bộ catalog.
Tạo báo cáo chi tiết về các file còn thiếu dữ liệu.
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any

# Đường dẫn
CATALOG_TB_ROOT = Path(__file__).resolve().parents[1] / 'data' / 'CatalogTB'
OUTPUT_DIR = Path(__file__).resolve().parents[1] / 'tmp'

# Bảng giá tham khảo từ web research
PRICE_DATABASE = {
    'LS Electric': {
        'BKD': {
            'description': 'Isolator/Switch Disconnector',
            'prices': {
                '1P': {'range': '80000-120000', 'note': '1 pole'},
                '2P': {'range': '120000-180000', 'note': '2 pole'},
                '3P': {'range': '150000-250000', 'note': '3 pole 63A-125A'},
                '4P': {'range': '200000-320000', 'note': '4 pole'}
            }
        },
        'MC': {
            'description': 'Contactor AC',
            'prices': {
                '9A': {'price': 120000, 'note': 'MC-9 9A 5.5kW'},
                '12A': {'price': 135000, 'note': 'MC-12 12A 5.5kW'},
                '18A': {'price': 165000, 'note': 'MC-18 18A 7.5kW'},
                '22A': {'price': 195000, 'note': 'MC-22 22A 11kW'},
                '32A': {'price': 245000, 'note': 'MC-32 32A 15kW'},
                '40A': {'price': 295000, 'note': 'MC-40 40A 18.5kW'},
                '50A': {'price': 350000, 'note': 'MC-50 50A 22kW'},
                '65A': {'price': 420000, 'note': 'MC-65 65A 30kW'},
                '85A': {'price': 520000, 'note': 'MC-85 85A 37kW'},
                '100A': {'price': 650000, 'note': 'MC-100 100A 45kW'}
            }
        },
        'Metasol': {
            'description': 'MCCB (Molded Case Circuit Breaker)',
            'prices': {
                '50A': {'range': '380000-520000', 'note': 'Metasol 3P 50A'},
                '63A': {'range': '420000-580000', 'note': 'Metasol 3P 63A'},
                '100A': {'range': '480000-680000', 'note': 'Metasol 3P 100A'},
                '125A': {'range': '580000-820000', 'note': 'Metasol 3P 125A'},
                '160A': {'range': '720000-1000000', 'note': 'Metasol 3P 160A'},
                '225A': {'range': '900000-1300000', 'note': 'Metasol 3P 225A'},
                '400A': {'range': '1800000-2600000', 'note': 'Metasol 3P 400A'},
                '630A': {'range': '3200000-4500000', 'note': 'Metasol 3P 630A'}
            }
        },
        'Susol': {
            'description': 'MCCB High Performance',
            'prices': {
                '100A': {'range': '550000-780000', 'note': 'Susol 3P 100A'},
                '225A': {'range': '1100000-1600000', 'note': 'Susol 3P 225A'},
                '400A': {'range': '2200000-3200000', 'note': 'Susol 3P 400A'}
            }
        },
        'TS': {
            'description': 'Thermal Switch',
            'prices': {
                '100A': {'range': '580000-780000', 'note': 'TS 3P 100A'},
                '160A': {'range': '720000-950000', 'note': 'TS 3P 160A'},
                '250A': {'range': '980000-1350000', 'note': 'TS 3P 250A'}
            }
        },
        'RKN': {
            'description': 'RCCB (Residual Current Circuit Breaker)',
            'prices': {
                '40A': {'range': '320000-450000', 'note': 'RKN 2P/4P 40A 30mA'},
                '63A': {'range': '380000-520000', 'note': 'RKN 2P/4P 63A 30mA'}
            }
        }
    },
    'Schneider Electric': {
        'iC60': {
            'description': 'MCB Acti9',
            'prices': {
                '1P': {'range': '45000-85000', 'note': 'iC60 1P C-curve'},
                '2P': {'range': '90000-150000', 'note': 'iC60 2P'},
                '3P': {'range': '135000-220000', 'note': 'iC60 3P'}
            }
        },
        'iID': {
            'description': 'RCCB Acti9',
            'prices': {
                '2P': {'range': '280000-420000', 'note': 'iID 2P 40-63A'},
                '4P': {'range': '420000-620000', 'note': 'iID 4P 40-63A'}
            }
        },
        'Compact NSX': {
            'description': 'MCCB Easypact',
            'prices': {
                '100A': {'range': '580000-850000', 'note': 'NSX100 3P'},
                '160A': {'range': '850000-1200000', 'note': 'NSX160 3P'},
                '250A': {'range': '1300000-1850000', 'note': 'NSX250 3P'}
            }
        },
        'TeSys D': {
            'description': 'Contactor',
            'prices': {
                '9A': {'range': '150000-220000', 'note': 'LC1D09 9A'},
                '18A': {'range': '210000-310000', 'note': 'LC1D18 18A'},
                '32A': {'range': '320000-450000', 'note': 'LC1D32 32A'}
            }
        }
    },
    'Mitsubishi': {
        'NF': {
            'description': 'MCCB',
            'prices': {
                '50A': {'range': '450000-620000', 'note': 'NF50 3P'},
                '100A': {'range': '580000-820000', 'note': 'NF100 3P'},
                '225A': {'range': '1100000-1600000', 'note': 'NF225 3P'}
            }
        },
        'S-N': {
            'description': 'Contactor',
            'prices': {
                '10A': {'range': '180000-260000', 'note': 'S-N10 10A'},
                '20A': {'range': '250000-360000', 'note': 'S-N20 20A'},
                '35A': {'range': '380000-540000', 'note': 'S-N35 35A'}
            }
        }
    },
    'CHINT': {
        'NXB-63': {
            'description': 'MCB',
            'prices': {
                '1P': {'range': '35000-65000', 'note': 'NXB-63 1P C-curve'},
                '2P': {'range': '70000-120000', 'note': 'NXB-63 2P'},
                '3P': {'range': '105000-180000', 'note': 'NXB-63 3P'}
            }
        },
        'NM8': {
            'description': 'MCCB',
            'prices': {
                '100A': {'range': '420000-620000', 'note': 'NM8 3P 100A'},
                '225A': {'range': '850000-1250000', 'note': 'NM8 3P 225A'}
            }
        },
        'NC1': {
            'description': 'Contactor',
            'prices': {
                '9A': {'range': '95000-145000', 'note': 'NC1-09 9A'},
                '18A': {'range': '145000-220000', 'note': 'NC1-18 18A'},
                '32A': {'range': '220000-330000', 'note': 'NC1-32 32A'}
            }
        }
    },
    'ABB': {
        'S200': {
            'description': 'MCB',
            'prices': {
                '1P': {'range': '55000-95000', 'note': 'S200 1P C-curve'},
                '2P': {'range': '110000-180000', 'note': 'S200 2P'},
                '3P': {'range': '165000-270000', 'note': 'S200 3P'}
            }
        },
        'Tmax': {
            'description': 'MCCB',
            'prices': {
                '100A': {'range': '650000-950000', 'note': 'Tmax T2 100A'},
                '160A': {'range': '950000-1400000', 'note': 'Tmax T2 160A'},
                '250A': {'range': '1500000-2200000', 'note': 'Tmax T3 250A'}
            }
        },
        'A': {
            'description': 'Contactor',
            'prices': {
                '9A': {'range': '180000-270000', 'note': 'A9 9A'},
                '16A': {'range': '240000-360000', 'note': 'A16 16A'},
                '30A': {'range': '360000-520000', 'note': 'A30 30A'}
            }
        }
    },
    'Hyundai': {
        'HGD': {
            'description': 'MCB/MCCB',
            'prices': {
                '50A': {'range': '320000-480000', 'note': 'HGD 3P 50A'},
                '100A': {'range': '480000-720000', 'note': 'HGD 3P 100A'}
            }
        }
    }
}

# Nguồn tham khảo
SOURCES = {
    'LS Electric': [
        'https://anhphatelectric.com/upload/file/bang-gia-ls-15-04-2026-7279.pdf',
        'https://etinco.vn/wp-content/uploads/2025/05/catalogue-ls-l-series-mcb-rccb-rcbo.pdf',
        'Tham khảo đại lý LS Electric Việt Nam'
    ],
    'Schneider Electric': [
        'https://schneider.net.vn/',
        'https://www.se.com/vn/en/',
        'Tham khảo đại lý Schneider Việt Nam'
    ],
    'Mitsubishi': [
        'http://www.mitsubishielectric.com/fa/products/lvd/lvcb/',
        'Alibaba: $120-200 for 100A MCCB',
        'Tham khảo đại lý Mitsubishi Việt Nam'
    ],
    'CHINT': [
        'https://www.chintglobal.com/',
        'Scribd: CHINT price lists',
        'Tham khảo đại lý CHINT Việt Nam'
    ],
    'ABB': [
        'https://library.e.abb.com/',
        'Thailand price list 2024',
        'Tham khảo đại lý ABB Việt Nam'
    ],
    'Hyundai': [
        'Điện Sài Gòn price book 2026-04-20',
        'Tham khảo đại lý Hyundai Việt Nam'
    ]
}


def find_price_for_device(brand: str, product_code: str, device_name: str) -> Dict[str, Any]:
    """
    Tìm giá phù hợp cho thiết bị dựa trên tên hãng và mã sản phẩm.
    """
    # Chuẩn hóa tên hãng
    brand_normalized = brand.strip() if brand else ''

    # Tìm trong database
    for db_brand, products in PRICE_DATABASE.items():
        if db_brand.lower() in brand_normalized.lower():
            # Tìm theo product code
            for prod_key, prod_data in products.items():
                if prod_key in product_code.upper() or prod_key in device_name.upper():
                    # Tìm giá phù hợp nhất
                    for size_key, price_info in prod_data.get('prices', {}).items():
                        if size_key in device_name or size_key in product_code:
                            return {
                                'found': True,
                                'brand': db_brand,
                                'product': prod_key,
                                'size': size_key,
                                'price_info': price_info,
                                'description': prod_data.get('description', '')
                            }

                    # Nếu không tìm thấy size cụ thể, trả về giá chung
                    prices_list = list(prod_data.get('prices', {}).values())
                    if prices_list:
                        return {
                            'found': True,
                            'brand': db_brand,
                            'product': prod_key,
                            'size': 'general',
                            'price_info': prices_list[0],  # Lấy giá đầu tiên
                            'description': prod_data.get('description', ''),
                            'note_extra': f'Giá dao động tùy theo dòng định mức. Xem chi tiết bảng giá {db_brand}.'
                        }

    return {'found': False}


def create_price_entry(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tạo entry giá cho thiết bị.
    """
    brand = profile.get('hang_xac_nhan', '')
    product_code = profile.get('ma_dong_san_pham', '')
    device_name = profile.get('ten_san_pham', '')

    # Tìm giá
    result = find_price_for_device(brand, product_code, device_name)

    if result['found']:
        price_info = result['price_info']

        # Xử lý giá
        if 'range' in price_info:
            don_gia = price_info['range']
            trang_thai = 'Có giá (phạm vi)'
        elif 'price' in price_info:
            don_gia = price_info['price']
            trang_thai = 'Có giá'
        else:
            don_gia = '-'
            trang_thai = 'Chưa có giá'

        # Tạo ghi chú
        notes = [
            f"{result['description']}",
            price_info.get('note', ''),
            result.get('note_extra', ''),
            'Giá tham khảo từ web research, chưa bao gồm VAT',
            'Liên hệ đại lý để có giá chính xác và cập nhật nhất'
        ]
        ghi_chu = '. '.join([n for n in notes if n])

        return {
            'don_gia': don_gia,
            'don_vi_tien_te': 'VND',
            'trang_thai': trang_thai,
            'hang': result['brand'],
            'ma_san_pham': f"{result['product']}-{result['size']}",
            'ghi_chu': ghi_chu,
            'nguon_tham_khao': SOURCES.get(result['brand'], []),
            'ngay_cap_nhat': datetime.now().strftime('%Y-%m-%d'),
            'muc_do_tin_cay': 'Tham khảo - cần xác nhận với nhà cung cấp'
        }
    else:
        # Không tìm thấy giá
        return {
            'don_gia': '-',
            'don_vi_tien_te': 'VND',
            'trang_thai': 'Chưa có giá',
            'ghi_chu': f'Chưa có dữ liệu giá cho {brand} {product_code}. Liên hệ đại lý để được báo giá chính xác.',
            'nguon_tham_khao': [],
            'ngay_cap_nhat': datetime.now().strftime('%Y-%m-%d'),
            'muc_do_tin_cay': 'Chưa xác định'
        }


def audit_catalog_files() -> Dict[str, Any]:
    """
    Kiểm tra toàn bộ catalog và tạo báo cáo.
    """
    stats = {
        'total_files': 0,
        'files_with_price': 0,
        'files_without_price': 0,
        'updated_files': 0,
        'by_brand': defaultdict(int),
        'missing_data': [],
        'updated_list': []
    }

    # Tìm tất cả file
    catalog_files = list(CATALOG_TB_ROOT.rglob('thong_tin_thiet_bi.json'))
    stats['total_files'] = len(catalog_files)

    print(f"Tìm thấy {len(catalog_files)} file catalog\n")
    print("Đang phân tích và cập nhật...\n")

    for file_path in catalog_files:
        try:
            # Đọc file
            with open(file_path, 'r', encoding='utf-8') as f:
                profile = json.load(f)

            brand = profile.get('hang_xac_nhan', 'Unknown')
            device_name = profile.get('ten_san_pham', 'Unknown')
            product_code = profile.get('ma_dong_san_pham', '')

            stats['by_brand'][brand] += 1

            # Kiểm tra xem đã có giá chưa
            has_price = 'gia_ban' in profile

            if has_price:
                stats['files_with_price'] += 1
            else:
                stats['files_without_price'] += 1

                # Tạo entry giá mới
                price_entry = create_price_entry(profile)
                profile['gia_ban'] = price_entry

                # Ghi lại file
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(profile, f, ensure_ascii=False, indent=2)

                stats['updated_files'] += 1

                # Ghi log
                relative_path = file_path.relative_to(CATALOG_TB_ROOT)
                if price_entry['don_gia'] == '-':
                    stats['missing_data'].append({
                        'file': str(relative_path),
                        'brand': brand,
                        'name': device_name,
                        'code': product_code
                    })
                    print(f"  - {relative_path}")
                    print(f"    {device_name} - Chưa có giá")
                else:
                    stats['updated_list'].append({
                        'file': str(relative_path),
                        'brand': brand,
                        'name': device_name,
                        'price': price_entry['don_gia']
                    })
                    print(f"  ✓ {relative_path}")
                    print(f"    {device_name}: {price_entry['don_gia']} VND")

        except Exception as e:
            print(f"  ✗ Lỗi: {file_path}: {e}")

    return stats


def generate_report(stats: Dict[str, Any]):
    """
    Tạo báo cáo chi tiết.
    """
    report = {
        'generated_at': datetime.now().isoformat(),
        'summary': {
            'total_files': stats['total_files'],
            'files_with_price': stats['files_with_price'],
            'files_without_price': stats['files_without_price'],
            'updated_files': stats['updated_files'],
            'still_missing': len(stats['missing_data'])
        },
        'by_brand': dict(stats['by_brand']),
        'missing_data_details': stats['missing_data'][:100],  # Top 100
        'updated_files': stats['updated_list'][:100],  # Top 100
        'price_sources': SOURCES,
        'notes': [
            'Giá tham khảo từ web research tháng 10/2026',
            'Chưa bao gồm VAT',
            'Cần xác nhận với nhà cung cấp trước khi sử dụng',
            'Giá có thể thay đổi tùy theo đại lý và số lượng'
        ]
    }

    # Ghi báo cáo
    OUTPUT_DIR.mkdir(exist_ok=True)
    report_file = OUTPUT_DIR / f'catalog_price_audit_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\nBáo cáo đã được lưu tại: {report_file}")
    return report_file


def main():
    """
    Hàm chính.
    """
    print("="*70)
    print("KIỂM TRA VÀ CẬP NHẬT GIÁ CHO TOÀN BỘ CATALOG")
    print("="*70)
    print()

    # Kiểm tra và cập nhật
    stats = audit_catalog_files()

    # In tóm tắt
    print("\n" + "="*70)
    print("TÓM TẮT KẾT QUẢ")
    print("="*70)
    print(f"Tổng số file catalog:        {stats['total_files']}")
    print(f"Đã có giá trước đó:          {stats['files_with_price']}")
    print(f"Chưa có giá:                 {stats['files_without_price']}")
    print(f"Đã cập nhật trong lần này:   {stats['updated_files']}")
    print(f"Vẫn còn thiếu dữ liệu:       {len(stats['missing_data'])}")
    print()

    print("Thống kê theo hãng:")
    for brand, count in sorted(stats['by_brand'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {brand:30s}: {count:4d} file")

    # Tạo báo cáo
    report_file = generate_report(stats)

    print("\n" + "="*70)
    print("HOÀN TẤT!")
    print("="*70)
    print(f"\nĐã cập nhật {stats['updated_files']} file")
    print(f"Xem báo cáo chi tiết tại: {report_file}")

    if stats['missing_data']:
        print(f"\nLưu ý: Vẫn còn {len(stats['missing_data'])} file chưa có dữ liệu giá")
        print("Các file này cần được cập nhật thủ công hoặc bổ sung vào PRICE_DATABASE")


if __name__ == '__main__':
    main()
