# Scripts Cập Nhật Giá Catalog

## Tổng Quan

Bộ scripts này giúp cập nhật thông tin giá và thông số thiết bị vào catalog CatalogTB. Nếu không có giá, hệ thống sẽ tự động đặt dấu gạch (-).

## Các Scripts Có Sẵn

### 1. `add_price_field_to_catalog.py`
**Mục đích**: Thêm trường giá cơ bản vào tất cả file catalog

**Cách dùng**:
```bash
# Xem trước (không ghi file)
python scripts/add_price_field_to_catalog.py --dry-run

# Chạy thật
python scripts/add_price_field_to_catalog.py
```

**Kết quả**:
- Thêm trường `gia_ban` với giá trị mặc định là dấu gạch `-`
- Không ghi đè nếu đã có trường giá

### 2. `sync_prices_to_catalog.py`
**Mục đích**: Đồng bộ giá từ database và pricebook vào catalog

**Cách dùng**:
```bash
# Xem trước
python scripts/sync_prices_to_catalog.py --dry-run

# Chạy thật
python scripts/sync_prices_to_catalog.py
```

**Nguồn dữ liệu**:
- Database: `webbaogia.db`
- Pricebook: `app/data/supplier_pricebooks.json`
- Web offers: `app/data/web_catalog_offers.json`

**Kết quả**:
- Tìm và cập nhật giá từ database
- Nếu không tìm thấy → giữ dấu gạch `-`
- Báo cáo số lượng có/không có giá

### 3. `update_sample_ls_prices.py`
**Mục đích**: Script ví dụ cập nhật giá LS Electric

**Cách dùng**:
```bash
python scripts/update_sample_ls_prices.py
```

**Chức năng**:
- Cập nhật giá cho BKD, MC, Metasol (ví dụ)
- Sử dụng giá tham khảo từ web research
- Minh họa cách cập nhật giá thủ công

## Cấu Trúc Trường Giá

```json
{
  "gia_ban": {
    "don_gia": 150000,               // hoặc "-" hoặc "150000-200000"
    "don_vi_tien_te": "VND",
    "trang_thai": "Có giá",          // "Có giá", "Chưa có giá", "Liên hệ"
    "sku": "BKD-3P-63A",
    "giam_gia_pct": 0.0,
    "ma_hang": "...",
    "ghi_chu": "Giá từ bảng giá...",
    "nguon_tham_khao": ["URL1", "URL2"],
    "ngay_cap_nhat": "2026-10-15"
  }
}
```

## Quy Trình Đề Xuất

### Lần Đầu Tiên
```bash
# Bước 1: Thêm trường giá cho tất cả file
python scripts/add_price_field_to_catalog.py --dry-run
python scripts/add_price_field_to_catalog.py

# Bước 2: Đồng bộ giá từ database
python scripts/sync_prices_to_catalog.py --dry-run
python scripts/sync_prices_to_catalog.py

# Bước 3: Xem kết quả
git status
git diff data/CatalogTB/
```

### Cập Nhật Định Kỳ
```bash
# Sau khi import bảng giá mới vào database
python scripts/sync_prices_to_catalog.py

# Hoặc cập nhật thủ công cho một số thiết bị
# Edit file trực tiếp hoặc tạo script tương tự update_sample_ls_prices.py
```

## Nguồn Thông Tin Giá

### Đã Tìm Được (Tháng 10/2026)

**LS Electric**
- Bảng giá: https://anhphatelectric.com/upload/file/bang-gia-ls-15-04-2026-7279.pdf
- Etinco catalog: https://etinco.vn/

**Schneider Electric**
- Website: schneider.net.vn
- Siemens: Bảng giá 06/2025

**CHINT**
- Website: chintglobal.com
- Đại lý Việt Nam

**ABB**
- Thailand price list 2024
- library.e.abb.com

**Mitsubishi**
- MCCB catalog: mitsubishielectric.com
- Giá tham khảo: $120-200 (100A)

**Hyundai**
- PDF Điện Sài Gòn (2026-04-20)

### Import Scripts Có Sẵn
```bash
# LS
python scripts/import_ls_pricebook.py <path-to-pdf>

# CHINT
python scripts/import_chint_pricebook.py <path-to-pdf>

# Mitsubishi
python scripts/import_mitsubishi_pricebook.py

# Hyundai
python scripts/import_hyundai_pricebook.py <path-to-pdf>

# INVT
python scripts/import_invt_pricebook.py

# Web offers
python scripts/refresh_web_catalog.py
```

## Lưu Ý Quan Trọng

### ⚠️ Về Giá Cả
1. **Không bịa giá**: Nếu không chắc → dùng dấu `-`
2. **Ghi rõ nguồn**: URL, file PDF, ngày
3. **VAT**: Ghi rõ có/không bao gồm
4. **Ngày cập nhật**: Luôn ghi để biết giá cũ hay mới

### ⚠️ Về Dữ Liệu
1. **Backup trước**: `git commit` trước khi chạy script
2. **Dry-run đầu tiên**: Luôn dùng `--dry-run` để xem trước
3. **Xem diff**: `git diff` để kiểm tra thay đổi
4. **Không xóa thông tin cũ**: Chỉ cập nhật/thêm mới

### ⚠️ Về Quy Trình
1. **Import vào DB trước**: Dùng scripts import_*_pricebook.py
2. **Đồng bộ vào catalog sau**: Dùng sync_prices_to_catalog.py
3. **Review kết quả**: Kiểm tra một số file mẫu
4. **Commit từng bước**: Dễ rollback nếu có lỗi

## Ví Dụ Sử Dụng

### Ví Dụ 1: Thêm Giá Lần Đầu
```bash
# Kiểm tra hiện trạng
python scripts/add_price_field_to_catalog.py --dry-run | grep "thêm giá mới"

# Thêm trường giá
python scripts/add_price_field_to_catalog.py

# Kết quả: Tất cả file có trường gia_ban với giá "-"
```

### Ví Dụ 2: Cập Nhật Từ Bảng Giá LS Mới
```bash
# 1. Import bảng giá vào database
python scripts/import_ls_pricebook.py storage/catalog-pricebooks/ls-2026-10-15.pdf

# 2. Đồng bộ vào catalog
python scripts/sync_prices_to_catalog.py --dry-run
python scripts/sync_prices_to_catalog.py

# 3. Kiểm tra kết quả
git diff data/CatalogTB/LS/
```

### Ví Dụ 3: Cập Nhật Thủ Công
```python
# Tạo script riêng hoặc edit trực tiếp file JSON
import json
from pathlib import Path

file_path = Path('data/CatalogTB/LS/ThietBi/BKD/thong_tin_thiet_bi.json')
with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

data['gia_ban'] = {
    'don_gia': 185000,
    'don_vi_tien_te': 'VND',
    'trang_thai': 'Có giá',
    'ghi_chu': 'Giá BKD 3P 63A từ đại lý Etinco',
    'nguon_tham_khao': ['https://etinco.vn'],
    'ngay_cap_nhat': '2026-10-15'
}

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

## Kiểm Tra Kết Quả

### Thống Kê
```bash
# Đếm file có giá
grep -r '"don_gia": "-"' data/CatalogTB/ | wc -l

# Đếm file có giá thực
grep -r '"trang_thai": "Có giá"' data/CatalogTB/ | wc -l

# Xem file được cập nhật gần đây
git log --since="1 day ago" --name-only -- data/CatalogTB/
```

### Validation
```python
# Script kiểm tra tính hợp lệ
python scripts/validate_catalog_prices.py  # (cần tạo nếu chưa có)
```

## Troubleshooting

### Lỗi: File không tìm thấy
```bash
# Kiểm tra đường dẫn
ls data/CatalogTB/LS/ThietBi/*/thong_tin_thiet_bi.json | head
```

### Lỗi: JSON không hợp lệ
```bash
# Kiểm tra syntax JSON
python -m json.tool data/CatalogTB/LS/ThietBi/BKD/thong_tin_thiet_bi.json
```

### Lỗi: Database không connect được
```bash
# Kiểm tra database
sqlite3 webbaogia.db "SELECT COUNT(*) FROM device_models WHERE price > 0;"
```

## Tài Liệu Liên Quan

- [HUONG_DAN_CAP_NHAT_GIA_CATALOG.md](../docs/HUONG_DAN_CAP_NHAT_GIA_CATALOG.md)
- [device-pricebooks.md](../docs/device-pricebooks.md)
- [API_DOCUMENTATION.md](../API_DOCUMENTATION.md)

## Hỗ Trợ

Nếu gặp vấn đề:
1. Đọc logs: `tmp/*.log`
2. Xem test: `scripts/test_*.py`
3. Review code: `app/services/library_price_matching.py`

---

**Cập nhật**: 15/10/2026
**Version**: 1.0
**Tác giả**: AI Assistant
