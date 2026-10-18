# Hướng Dẫn Cập Nhật Giá Cho Catalog Thiết Bị

## Tổng Quan

Tài liệu này hướng dẫn cách cập nhật thông tin giá và thông số thiết bị vào các file `thong_tin_thiet_bi.json` trong thư mục CatalogTB.

## Nguồn Thông Tin Bảng Giá Đã Tìm Thấy (Tháng 10/2026)

### 1. **LS Electric**
- **Bảng giá chính thức**: [Anh Phát Electric - LS 15/04/2026](https://anhphatelectric.com/upload/file/bang-gia-ls-15-04-2026-7279.pdf)
- **Catalog kỹ thuật**: [Etinco - LS L-Series MCB/RCCB/RCBO](https://etinco.vn/wp-content/uploads/2025/05/catalogue-ls-l-series-mcb-rccb-rcbo.pdf)
- **Website chính**: [LS Electric Official](https://www.ls-electric.com/)
- **Sản phẩm**: MCB, MCCB, Contactor (MC Series), Isolator (BKD), Metasol, Susol

### 2. **Schneider Electric**
- **Bảng giá**: Có sẵn qua đại lý chính thức tại Việt Nam
- **Siemens PDF**: [Bảng giá thiết bị điện 06/2025](https://assets.new.siemens.com/siemens/assets/api/uuid:bbad6f92-f7ea-4477-b0ad-1cfb2df93ea3/Bang-gia-thiet-bi-dien-Master-06-2025_original.pdf)
- **Website**: [schneider.net.vn](https://schneider.net.vn/), [se.com](https://www.se.com/vn/en/)
- **Sản phẩm**: MCB, MCCB, Contactor, Acti9, Easypact

### 3. **CHINT**
- **Bảng giá**: Có trong Drive link từ các nhà phân phối
- **Website**: [CHINT Global Vietnam](https://www.chintglobal.com/)
- **Sản phẩm**: NXB-63, NM8N, NPB-63R, MCCB, Smart monitoring devices

### 4. **ABB**
- **Bảng giá Thailand 2024**: [ABB All Product Price List](https://library.e.abb.com/)
- **Website**: [new.abb.com](https://new.abb.com/news/)
- **Sản phẩm**: Tmax, S200, ACB, Lite Panel Pro, Farmiga switches

### 5. **Mitsubishi Electric**
- **Catalog**: [MCCB/Breaker Lineup](http://www.mitsubishielectric.com/fa/products/lvd/lvcb/)
- **Giá tham khảo**: 100A 3P: $120-200, 800A-1200A: >$1,000
- **Sản phẩm**: NF Series MCCB, WS-V Series, Contactor

### 6. **Hyundai**
- **Bảng giá**: Có trong PDF của Điện Sài Gòn (2026-04-20)
- **Sản phẩm**: Protection devices, MCB, MCCB

### Nguồn Tổng Hợp
- **Scribd**: [Bảng giá Huỳnh Lai (nhiều hãng)](https://www.scribd.com/document/521970954/)
  - Bao gồm: Neiken, Hyundai, LS, Mitsubishi, Chint, Schneider, Fuji, Socomec

## Cấu Trúc Trường Giá Trong File JSON

```json
{
  "gia_ban": {
    "don_gia": 150000,          // Số hoặc "-" nếu không có
    "don_vi_tien_te": "VND",    // VND, USD, EUR
    "trang_thai": "Có giá",     // "Có giá", "Chưa có giá", "Liên hệ"
    "sku": "BKD-3P-63A",        // Mã sản phẩm (nếu có)
    "giam_gia_pct": 0.0,        // Phần trăm giảm giá
    "ma_hang": "...",           // Mã hàng catalog
    "ghi_chu": "Giá từ bảng giá LS Electric 15/04/2026",
    "nguon_tham_khao": [
      "https://anhphatelectric.com/upload/file/bang-gia-ls-15-04-2026-7279.pdf",
      "Database webbaogia.db"
    ],
    "ngay_cap_nhat": "2026-10-15"
  }
}
```

### Quy Tắc Quan Trọng

1. **Khi KHÔNG có giá**: Dùng dấu gạch `-`
   ```json
   {
     "don_gia": "-",
     "trang_thai": "Chưa có giá",
     "ghi_chu": "Liên hệ để được báo giá chính xác."
   }
   ```

2. **Khi có nhiều biến thể**: Ghi rõ phạm vi hoặc điều kiện
   ```json
   {
     "don_gia": "150000-300000",
     "ghi_chu": "Giá phụ thuộc vào dòng định mức (63A-125A)"
   }
   ```

3. **Nguồn tham khảo**: Luôn ghi nguồn để kiểm chứng

## Scripts Đã Tạo

### 1. Script Thêm Trường Giá Cơ Bản
```bash
python scripts/add_price_field_to_catalog.py
```
- Thêm trường `gia_ban` vào tất cả file catalog
- Mặc định là dấu gạch `-` nếu chưa có giá
- Sử dụng `--dry-run` để xem trước không ghi file

### 2. Script Đồng Bộ Giá Từ Database
```bash
python scripts/sync_prices_to_catalog.py
```
- Tìm giá từ `webbaogia.db`
- Tìm giá từ `app/data/supplier_pricebooks.json`
- Cập nhật vào file `thong_tin_thiet_bi.json`
- Nếu không tìm thấy, giữ dấu gạch `-`

## Quy Trình Cập Nhật Thủ Công

### Bước 1: Tải Bảng Giá Mới

1. Download các file PDF bảng giá từ nhà cung cấp
2. Lưu vào thư mục `storage/catalog-pricebooks/`
3. Đặt tên theo quy ước: `{hang}-{ngay}.pdf`
   - Ví dụ: `ls-2026-10-15.pdf`, `schneider-2026-09.pdf`

### Bước 2: Import Vào Database (Nếu Có Script)

Các script import có sẵn:
- `scripts/import_ls_pricebook.py <PDF path>`
- `scripts/import_chint_pricebook.py <PDF path>`
- `scripts/import_mitsubishi_pricebook.py`
- `scripts/import_hyundai_pricebook.py <PDF path>`

### Bước 3: Cập Nhật Catalog

```bash
# 1. Chạy dry-run để xem trước
python scripts/sync_prices_to_catalog.py --dry-run

# 2. Nếu OK, chạy thật
python scripts/sync_prices_to_catalog.py

# 3. Kiểm tra kết quả
git diff data/CatalogTB/
```

### Bước 4: Cập Nhật Thủ Công (Nếu Cần)

Đối với các thiết bị đặc biệt hoặc giá từ nguồn web:

1. Mở file `thong_tin_thiet_bi.json` cần cập nhật
2. Tìm hoặc tạo trường `gia_ban`
3. Điền thông tin theo cấu trúc ở trên
4. Lưu file

**Ví dụ cập nhật cho LS BKD:**
```json
{
  "ten_san_pham": "Isolator LS BKD · 3P",
  "hang_xac_nhan": "LS Electric",
  "ma_dong_san_pham": "BKD",
  "gia_ban": {
    "don_gia": "180000-250000",
    "don_vi_tien_te": "VND",
    "trang_thai": "Có giá",
    "ghi_chu": "Giá dao động theo dòng định mức 63A-125A. Tham khảo bảng giá LS 15/04/2026",
    "nguon_tham_khao": [
      "https://anhphatelectric.com/upload/file/bang-gia-ls-15-04-2026-7279.pdf",
      "Đại lý Etinco"
    ],
    "ngay_cap_nhat": "2026-10-15"
  }
}
```

## Lưu Ý Quan Trọng

### Về Giá Cả

1. **Giá chưa bao gồm VAT**: Ghi rõ trong `ghi_chu`
2. **Giá có thể thay đổi**: Luôn ghi `ngay_cap_nhat`
3. **Giá theo số lượng**: Nếu có bậc giá, ghi trong `ghi_chu`
4. **Không bịa giá**: Nếu không chắc chắn, dùng dấu `-`

### Về Nguồn

1. **Ưu tiên**: Bảng giá chính thức > Đại lý > Web
2. **Ghi rõ nguồn**: URL, tên file PDF, ngày phát hành
3. **Kiểm chứng**: So sánh nhiều nguồn nếu có thể

### Về Database

- Giá trong database (`webbaogia.db`) được ưu tiên nếu có
- File JSON là backup và cho các trường hợp đặc biệt
- Đồng bộ hai chiều: DB ↔ JSON

## Tài Liệu Tham Khảo

Xem thêm:
- `BE_AIDE/docs/device-pricebooks.md` - Chi tiết về hệ thống bảng giá
- `BE_AIDE/API_DOCUMENTATION.md` - API endpoints liên quan
- `BE_AIDE/app/services/device_catalog_engine.py` - Engine xử lý catalog

## Liên Hệ & Hỗ Trợ

Nếu cần hỗ trợ:
1. Kiểm tra logs trong `tmp/*.log`
2. Xem test cases trong `scripts/test_*.py`
3. Review code trong `app/services/library_price_matching.py`

---

**Cập nhật lần cuối**: 15/10/2026
**Người thực hiện**: AI Assistant
**Trạng thái**: Đã tạo scripts và tài liệu hướng dẫn
