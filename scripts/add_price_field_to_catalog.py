"""
Script để thêm trường giá vào tất cả các file thong_tin_thiet_bi.json trong CatalogTB.
Nếu không có giá thì để dấu gạch (-).
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
import sys

# Đường dẫn đến thư mục CatalogTB
CATALOG_TB_ROOT = Path(__file__).resolve().parents[1] / 'data' / 'CatalogTB'


def add_price_info(profile: Dict[str, Any], default_price: Optional[str] = "-") -> Dict[str, Any]:
    """
    Thêm thông tin giá vào profile thiết bị.

    Args:
        profile: Dictionary chứa thông tin thiết bị
        default_price: Giá trị mặc định nếu không có giá (mặc định là "-")

    Returns:
        Dictionary đã được bổ sung thông tin giá
    """
    # Nếu chưa có trường giá, thêm vào
    if 'gia_ban' not in profile:
        profile['gia_ban'] = {
            'don_gia': default_price,
            'don_vi_tien_te': 'VND',
            'trang_thai': 'Chưa có giá',
            'ghi_chu': 'Liên hệ để được báo giá chính xác.',
            'nguon_tham_khao': [],
            'ngay_cap_nhat': None
        }

    # Nếu đã có trường giá nhưng không có don_gia, đảm bảo có dấu gạch
    if 'gia_ban' in profile:
        if 'don_gia' not in profile['gia_ban'] or profile['gia_ban']['don_gia'] is None:
            profile['gia_ban']['don_gia'] = default_price

    return profile


def process_catalog_file(file_path: Path, dry_run: bool = False) -> bool:
    """
    Xử lý một file thong_tin_thiet_bi.json.

    Args:
        file_path: Đường dẫn đến file JSON
        dry_run: Nếu True, chỉ in thông tin không ghi file

    Returns:
        True nếu file được xử lý thành công
    """
    try:
        # Đọc file hiện tại
        with open(file_path, 'r', encoding='utf-8') as f:
            profile = json.load(f)

        # Kiểm tra xem đã có trường giá chưa
        has_price = 'gia_ban' in profile

        # Thêm thông tin giá
        updated_profile = add_price_info(profile)

        # In thông tin
        device_name = profile.get('ten_san_pham', 'Unknown')
        relative_path = file_path.relative_to(CATALOG_TB_ROOT)

        if has_price:
            print(f"  ✓ {relative_path} - '{device_name}' (đã có giá)")
        else:
            print(f"  + {relative_path} - '{device_name}' (thêm giá mới)")

        # Ghi file nếu không phải dry_run
        if not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(updated_profile, f, ensure_ascii=False, indent=2)

        return True

    except Exception as e:
        print(f"  ✗ Lỗi khi xử lý {file_path}: {e}")
        return False


def main():
    """
    Hàm chính để xử lý tất cả các file catalog.
    """
    # Kiểm tra tham số dòng lệnh
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print("=== CHẾ ĐỘ KIỂM TRA (DRY RUN) - Không ghi file ===\n")
    else:
        print("=== BẮT ĐẦU CÂP NHẬT GIÁ CHO CATALOG ===\n")

    # Tìm tất cả các file thong_tin_thiet_bi.json
    catalog_files = list(CATALOG_TB_ROOT.rglob('thong_tin_thiet_bi.json'))

    print(f"Tìm thấy {len(catalog_files)} file catalog\n")

    # Xử lý từng file
    success_count = 0
    error_count = 0

    for file_path in sorted(catalog_files):
        if process_catalog_file(file_path, dry_run):
            success_count += 1
        else:
            error_count += 1

    # In tóm tắt
    print(f"\n{'='*60}")
    print(f"Tổng kết:")
    print(f"  - Tổng số file: {len(catalog_files)}")
    print(f"  - Thành công: {success_count}")
    print(f"  - Lỗi: {error_count}")

    if dry_run:
        print(f"\nĐể áp dụng thay đổi, chạy lại không có --dry-run")
    else:
        print(f"\nHoàn tất cập nhật catalog!")

    return error_count == 0


if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
