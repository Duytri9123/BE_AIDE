"""
Script cập nhật hàng loạt giá cho catalog - phiên bản đơn giản.
Cập nhật trực tiếp vào file JSON.
"""

import json
from pathlib import Path
from datetime import datetime

CATALOG_ROOT = Path(__file__).resolve().parents[1] / 'data' / 'CatalogTB'

# Danh sách cập nhật chi tiết
UPDATES = [
    # LS Electric
    {
        'path': 'LS/ThietBi/BKD_1P/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '80000-120000',
            'hang': 'LS Electric',
            'ma_san_pham': 'BKD-1P',
            'ghi_chu': 'Isolator LS BKD 1P. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'LS/ThietBi/BKD_2P/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '120000-180000',
            'hang': 'LS Electric',
            'ma_san_pham': 'BKD-2P',
            'ghi_chu': 'Isolator LS BKD 2P. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'LS/ThietBi/BKD_4P/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '200000-320000',
            'hang': 'LS Electric',
            'ma_san_pham': 'BKD-4P',
            'ghi_chu': 'Isolator LS BKD 4P. Giá tham khảo, chưa bao gồm VAT.'
        }
    },

    # LS MC Series Contactors
    {
        'path': 'LS/ThietBi/MC_9/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': 120000,
            'hang': 'LS Electric',
            'ma_san_pham': 'MC-9',
            'ghi_chu': 'Contactor MC-9 9A 5.5kW. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'LS/ThietBi/MC_95/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': 135000,
            'hang': 'LS Electric',
            'ma_san_pham': 'MC-12',
            'ghi_chu': 'Contactor MC-12 12A. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'LS/ThietBi/MC_35/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': 245000,
            'hang': 'LS Electric',
            'ma_san_pham': 'MC-32',
            'ghi_chu': 'Contactor MC-32 32A 15kW. Giá tham khảo, chưa bao gồm VAT.'
        }
    },

    # LS Metasol MCCB
    {
        'path': 'LS/ThietBi/Metasol_29/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '380000-520000',
            'hang': 'LS Electric',
            'ma_san_pham': 'Metasol-50A',
            'ghi_chu': 'MCCB Metasol 3P 50A. Giá phụ thuộc khả năng cắt. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'LS/ThietBi/Metasol_30/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '420000-580000',
            'hang': 'LS Electric',
            'ma_san_pham': 'Metasol-63A',
            'ghi_chu': 'MCCB Metasol 3P 63A. Giá phụ thuộc khả năng cắt. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'LS/ThietBi/Metasol_31/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '480000-680000',
            'hang': 'LS Electric',
            'ma_san_pham': 'Metasol-100A',
            'ghi_chu': 'MCCB Metasol 3P 100A. Giá phụ thuộc khả năng cắt. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'LS/ThietBi/Metasol_32/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '580000-820000',
            'hang': 'LS Electric',
            'ma_san_pham': 'Metasol-125A',
            'ghi_chu': 'MCCB Metasol 3P 125A. Giá phụ thuộc khả năng cắt. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'LS/ThietBi/Metasol_33/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '720000-1000000',
            'hang': 'LS Electric',
            'ma_san_pham': 'Metasol-160A',
            'ghi_chu': 'MCCB Metasol 3P 160A. Giá phụ thuộc khả năng cắt. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'LS/ThietBi/Metasol_34/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '900000-1300000',
            'hang': 'LS Electric',
            'ma_san_pham': 'Metasol-225A',
            'ghi_chu': 'MCCB Metasol 3P 225A. Giá phụ thuộc khả năng cắt. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'LS/ThietBi/Metasol_35/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '1800000-2600000',
            'hang': 'LS Electric',
            'ma_san_pham': 'Metasol-400A',
            'ghi_chu': 'MCCB Metasol 3P 400A. Giá phụ thuộc khả năng cắt. Giá tham khảo, chưa bao gồm VAT.'
        }
    },

    # LS Thermal Switch
    {
        'path': 'LS/ThietBi/TS100_TS160_TS250/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '580000-780000',
            'hang': 'LS Electric',
            'ma_san_pham': 'TS-100',
            'ghi_chu': 'Thermal Switch 3P 100A. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'LS/ThietBi/TD100_TD160/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '720000-950000',
            'hang': 'LS Electric',
            'ma_san_pham': 'TD-160',
            'ghi_chu': 'Thermal Switch 3P 160A. Giá tham khảo, chưa bao gồm VAT.'
        }
    },

    # LS RCCB
    {
        'path': 'LS/ThietBi/RKN/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '320000-450000',
            'hang': 'LS Electric',
            'ma_san_pham': 'RKN-40A',
            'ghi_chu': 'RCCB RKN 2P/4P 40A 30mA. Giá tham khảo, chưa bao gồm VAT.'
        }
    },

    # Schneider Electric
    {
        'path': 'Schneider/ThietBi/iC60_1P/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '45000-85000',
            'hang': 'Schneider Electric',
            'ma_san_pham': 'iC60-1P',
            'ghi_chu': 'MCB Acti9 iC60 1P C-curve. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'Schneider/ThietBi/iC60_2P/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '90000-150000',
            'hang': 'Schneider Electric',
            'ma_san_pham': 'iC60-2P',
            'ghi_chu': 'MCB Acti9 iC60 2P. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'Schneider/ThietBi/iC60_3P/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '135000-220000',
            'hang': 'Schneider Electric',
            'ma_san_pham': 'iC60-3P',
            'ghi_chu': 'MCB Acti9 iC60 3P. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'Schneider/ThietBi/iIDK_2P/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '280000-420000',
            'hang': 'Schneider Electric',
            'ma_san_pham': 'iID-2P',
            'ghi_chu': 'RCCB Acti9 iID 2P 40-63A. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'Schneider/ThietBi/iIDK_4P/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '420000-620000',
            'hang': 'Schneider Electric',
            'ma_san_pham': 'iID-4P',
            'ghi_chu': 'RCCB Acti9 iID 4P 40-63A. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'Schneider/ThietBi/EZC100_3P/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '580000-850000',
            'hang': 'Schneider Electric',
            'ma_san_pham': 'NSX100-3P',
            'ghi_chu': 'MCCB Easypact NSX100 3P. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'Schneider/ThietBi/EZC250_3P/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '1300000-1850000',
            'hang': 'Schneider Electric',
            'ma_san_pham': 'NSX250-3P',
            'ghi_chu': 'MCCB Easypact NSX250 3P. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'Schneider/ThietBi/LC1D9_18/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '150000-220000',
            'hang': 'Schneider Electric',
            'ma_san_pham': 'LC1D09',
            'ghi_chu': 'Contactor TeSys D LC1D09 9A. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'Schneider/ThietBi/LC1D25_38/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '320000-450000',
            'hang': 'Schneider Electric',
            'ma_san_pham': 'LC1D32',
            'ghi_chu': 'Contactor TeSys D LC1D32 32A. Giá tham khảo, chưa bao gồm VAT.'
        }
    },

    # Mitsubishi
    {
        'path': 'Mitsubishi/ThietBi/NF63_SV_3P/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '450000-620000',
            'hang': 'Mitsubishi Electric',
            'ma_san_pham': 'NF63-SV',
            'ghi_chu': 'MCCB NF50-63 3P. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'Mitsubishi/ThietBi/NF125_CV_3P/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '580000-820000',
            'hang': 'Mitsubishi Electric',
            'ma_san_pham': 'NF125-CV',
            'ghi_chu': 'MCCB NF100-125 3P. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'Mitsubishi/ThietBi/NF250_CV_3P/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '1100000-1600000',
            'hang': 'Mitsubishi Electric',
            'ma_san_pham': 'NF250-CV',
            'ghi_chu': 'MCCB NF225-250 3P. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'Mitsubishi/ThietBi/S_T10_3P/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '180000-260000',
            'hang': 'Mitsubishi Electric',
            'ma_san_pham': 'S-N10',
            'ghi_chu': 'Contactor S-N10 10A. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'Mitsubishi/ThietBi/S_T21_S_T25_3P/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '250000-360000',
            'hang': 'Mitsubishi Electric',
            'ma_san_pham': 'S-N20',
            'ghi_chu': 'Contactor S-N20/25 20A. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
    {
        'path': 'Mitsubishi/ThietBi/S_T35_S_T50_3P/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '380000-540000',
            'hang': 'Mitsubishi Electric',
            'ma_san_pham': 'S-N35',
            'ghi_chu': 'Contactor S-N35/50 35A. Giá tham khảo, chưa bao gồm VAT.'
        }
    },

    # CHINT
    {
        'path': 'Chint/ThietBi/NCH8_20_25_2P/thong_tin_thiet_bi.json',
        'price': {
            'don_gia': '95000-145000',
            'hang': 'CHINT',
            'ma_san_pham': 'NCH8-20',
            'ghi_chu': 'Contactor NCH8-20/25 20A. Giá tham khảo, chưa bao gồm VAT.'
        }
    },
]

SOURCES = [
    'https://anhphatelectric.com/upload/file/bang-gia-ls-15-04-2026-7279.pdf',
    'https://etinco.vn/wp-content/uploads/2025/05/catalogue-ls-l-series-mcb-rccb-rcbo.pdf',
    'https://schneider.net.vn/',
    'http://www.mitsubishielectric.com/fa/products/lvd/lvcb/',
    'https://www.chintglobal.com/',
    'Tham khảo đại lý và web research tháng 10/2026'
]

def update_file(file_path: Path, price_data: dict) -> bool:
    """Cập nhật giá vào một file."""
    try:
        if not file_path.exists():
            print(f"  ⚠ File không tồn tại: {file_path}")
            return False

        # Đọc file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Tạo entry giá
        price_entry = {
            'don_gia': price_data['don_gia'],
            'don_vi_tien_te': 'VND',
            'trang_thai': 'Có giá (phạm vi)' if isinstance(price_data['don_gia'], str) and '-' in str(price_data['don_gia']) else 'Có giá',
            'hang': price_data['hang'],
            'ma_san_pham': price_data['ma_san_pham'],
            'ghi_chu': price_data['ghi_chu'] + ' Liên hệ đại lý để có giá chính xác và cập nhật nhất.',
            'nguon_tham_khao': SOURCES,
            'ngay_cap_nhat': datetime.now().strftime('%Y-%m-%d'),
            'muc_do_tin_cay': 'Tham khảo - cần xác nhận với nhà cung cấp'
        }

        # Cập nhật hoặc thêm mới
        data['gia_ban'] = price_entry

        # Ghi lại
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        device_name = data.get('ten_san_pham', 'Unknown')
        print(f"  ✓ {file_path.name}: {device_name}")
        print(f"    Giá: {price_data['don_gia']} VND")
        return True

    except Exception as e:
        print(f"  ✗ Lỗi {file_path}: {e}")
        return False

def main():
    print("="*70)
    print("CẬP NHẬT GIÁ HÀNG LOẠT CHO CATALOG")
    print("="*70)
    print()

    success = 0
    failed = 0
    notfound = 0

    for item in UPDATES:
        file_path = CATALOG_ROOT / item['path']
        print(f"\n[{UPDATES.index(item)+1}/{len(UPDATES)}] {item['path']}")

        if update_file(file_path, item['price']):
            success += 1
        elif not file_path.exists():
            notfound += 1
        else:
            failed += 1

    print("\n" + "="*70)
    print("TÓM TẮT")
    print("="*70)
    print(f"Tổng số: {len(UPDATES)}")
    print(f"Thành công: {success}")
    print(f"Không tìm thấy file: {notfound}")
    print(f"Lỗi: {failed}")
    print("\nHoàn tất!")

if __name__ == '__main__':
    main()
