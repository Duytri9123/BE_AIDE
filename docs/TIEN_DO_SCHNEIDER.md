# Báo cáo tiến độ cập nhật giá Schneider Electric

**Thời gian thực hiện:** 16/10/2026
**Agent:** Autonomous Research Subagent
**Workflow:** wf_bd77b1b3bfbdd91a

## Tóm tắt

Đã cập nhật thành công thông tin giá tham khảo cho thiết bị Schneider Electric trong hệ thống catalog.

## Thống kê

- **Tổng số file thiết bị Schneider:** 237 files
- **Đã cập nhật giá:** 62 files (26.2%)
- **Chưa cập nhật:** 175 files (73.8%)
  - 174 files SRC (CAD nguồn chưa xác định mã)
  - 1 file khác
- **Lỗi:** 0 files

## Chi tiết cập nhật

### Các dòng sản phẩm đã cập nhật giá

#### 1. MCB (Miniature Circuit Breaker - Aptomat tép)

| Dòng sản phẩm | Số file | Phạm vi giá (VND) | Ghi chú |
|---------------|---------|-------------------|---------|
| iC60 | 4 | 150,000 - 500,000 | Theo dòng 6A-63A, đường cong B/C/D |
| C120 | 4 | 200,000 - 600,000 | MCB công nghiệp |
| iK60N | 4 | 100,000 - 400,000 | MCB phổ thông |
| iCT | 1 | 80,000 - 300,000 | MCB cơ bản |

**Tổng MCB:** 13 files

#### 2. MCCB (Molded Case Circuit Breaker - Aptomat khối)

| Dòng sản phẩm | Số file | Phạm vi giá (VND) | Ghi chú |
|---------------|---------|-------------------|---------|
| NS100 | 3 | 1,500,000 - 4,000,000 | Compact NS 100A |
| NS400 | 2 | 4,000,000 - 12,000,000 | Compact NS 400A |
| NS630b | 2 | 8,000,000 - 20,000,000 | Compact NS 630A |
| EZC100 | 4 | 800,000 - 2,500,000 | EasyPact CVS 100A |
| EZC250 | 3 | 2,000,000 - 5,000,000 | EasyPact CVS 250A |
| EZC400 | 2 | 3,500,000 - 8,000,000 | EasyPact CVS 400A |
| EZS100 | 4 | 600,000 - 2,000,000 | EasyPact EZS 100A |
| EZS250 | 3 | 1,800,000 - 4,500,000 | EasyPact EZS 250A |
| EZS400 | 2 | 3,000,000 - 7,000,000 | EasyPact EZS 400A |
| EZCV250 | 2 | 2,500,000 - 6,000,000 | CVS 250A electronic |
| CVS100 | 2 | 1,200,000 - 3,500,000 | ComPacT CVS 100A |
| CVS400 | 2 | 4,500,000 - 11,000,000 | ComPacT CVS 400A |

**Tổng MCCB:** 31 files

#### 3. RCD (Residual Current Device - Thiết bị chống rò)

| Dòng sản phẩm | Số file | Phạm vi giá (VND) | Ghi chú |
|---------------|---------|-------------------|---------|
| A9D | 2 | 400,000 - 1,200,000 | RCCB/RCBO iDPN |
| iIDK | 2 | 300,000 - 900,000 | RCCB dòng iID |

**Tổng RCD:** 4 files

#### 4. Contactor (Khởi động từ)

| Dòng sản phẩm | Số file | Phạm vi giá (VND) | Ghi chú |
|---------------|---------|-------------------|---------|
| LC1D9 | 1 | 250,000 - 450,000 | TeSys D 9-18A |
| LC1D25 | 1 | 350,000 - 650,000 | TeSys D 25-38A |
| LC1D40 | 2 | 500,000 - 900,000 | TeSys D 40-65A |
| LC1E06 | 1 | 800,000 - 1,500,000 | TeSys E 06-32A |
| LC1E25 | 1 | 900,000 - 1,600,000 | TeSys E 25-32A |
| LC1E32 | 1 | 1,000,000 - 1,700,000 | TeSys E 32A |
| LC1E160 | 1 | 3,500,000 - 6,000,000 | TeSys E 160A |
| LC1F115 | 1 | 2,000,000 - 3,800,000 | TeSys F 115A |
| LC1F150 | 1 | 2,500,000 - 4,500,000 | TeSys F 150A |
| LC1F185 | 1 | 3,000,000 - 5,500,000 | TeSys F 185A |
| LC1F225 | 1 | 3,500,000 - 6,500,000 | TeSys F 225A |
| LC1F265 | 1 | 4,000,000 - 7,500,000 | TeSys F 265A |
| LC1F330 | 1 | 5,000,000 - 9,000,000 | TeSys F 330A |

**Tổng Contactor:** 14 files

## Cấu trúc dữ liệu giá

Mỗi file thiết bị đã được bổ sung trường `gia_ban` với cấu trúc:

```json
{
  "gia_ban": {
    "don_gia": "150,000 - 500,000",
    "don_vi_tien_te": "VND",
    "trang_thai": "Co gia (pham vi)",
    "hang": "Schneider Electric",
    "ma_san_pham": "iC60",
    "ghi_chu": "Gia thay doi theo dong dinh muc (6A-63A) va duong cong (B,C,D)",
    "nguon_tham_khao": [
      "https://schneider.net.vn",
      "https://www.se.com/vn/vi/",
      "https://etinco.vn",
      "https://dienquang.com"
    ],
    "ngay_cap_nhat": "2026-10-16",
    "muc_do_tin_cay": "Tham khao - can xac nhan voi nha cung cap"
  }
}
```

## Nguồn tham khảo giá

1. **Schneider Electric Vietnam:** https://schneider.net.vn
2. **Schneider Global Catalog:** https://www.se.com/vn/vi/
3. **Đại lý Etinco:** https://etinco.vn
4. **Đại lý Điện Quang:** https://dienquang.com

## File chưa cập nhật

### SRC Files (174 files)

Đây là các file CAD nguồn được trích xuất từ thư viện AutoCAD của Schneider. Các file này:
- Chưa có `ma_dong_san_pham` xác định
- Cần được xác định và ánh xạ tới mã sản phẩm chính thức
- Đặt giá mặc định: `"-"` với trạng thái `"Chua co gia"`

**Ví dụ:**
- `SRC_SCHNEIDER_03e9216c2c59` - "06 - N - SC CTT CHIẾU HÔNG LC1D40~65"
- `SRC_SCHNEIDER_058bf2c8b2fe` - ...
- (và 172 files khác)

### File đặc biệt (1 file)

- `SCH_D01_C2_I01`: Cần xác định loại thiết bị

## Lưu ý quan trọng

⚠️ **Giá trị tham khảo:** Tất cả giá được cập nhật là giá tham khảo từ thị trường Việt Nam (2026).

⚠️ **Cần xác nhận:** Khách hàng phải liên hệ trực tiếp với nhà cung cấp/đại lý để có báo giá chính thức.

⚠️ **Biến động giá:** Giá có thể thay đổi theo:
- Số lượng đặt hàng (giá sỉ vs lẻ)
- Thời điểm mua (khuyến mãi, thay đổi tỷ giá)
- Đại lý/nhà phân phối khác nhau
- Cấu hình chi tiết (Trip unit, phụ kiện, accessories)
- Điều kiện nhập khẩu và thuế

⚠️ **Phạm vi giá:**
- Giá "min - max" phản ánh sự khác biệt giữa các variant trong cùng dòng sản phẩm
- Ví dụ: iC60 6A rẻ hơn iC60 63A, đường cong C khác đường cong D

## Phương pháp nghiên cứu

1. **Phân tích cấu trúc catalog:** Đọc và hiểu schema JSON của thiết bị
2. **Phân loại sản phẩm:** MCB, MCCB, RCD, Contactor
3. **Tra cứu giá tham khảo:**
   - Website chính thức Schneider VN
   - Catalog online toàn cầu
   - Đại lý ủy quyền tại VN (Etinco, Điện Quang)
4. **Xây dựng price mapping:** Tạo bảng ánh xạ mã sản phẩm → phạm vi giá
5. **Script tự động:** PowerShell script để cập nhật hàng loạt
6. **Validation:** Kiểm tra JSON syntax và logic

## Bước tiếp theo

### Ưu tiên cao

1. ✅ **Đã hoàn thành:** Cập nhật giá cho các dòng sản phẩm chính (62 files)
2. ⏳ **Cần làm:** Xác định và ánh xạ 174 SRC files
   - Phân tích nhãn block CAD
   - Tra cứu mã sản phẩm tương ứng
   - Cập nhật giá chi tiết

### Ưu tiên trung bình

3. ⏳ Cập nhật giá chi tiết theo variant cụ thể
   - Tách giá theo dòng định mức (6A, 10A, 16A, 20A, 32A, 40A, 63A...)
   - Tách giá theo đường cong (B, C, D, K, Z)
   - Tách giá theo khả năng cắt (Icu: 6kA, 10kA, 15kA, 25kA...)

4. ⏳ Liên hệ đại lý để xác nhận giá chính xác
   - Lấy bảng giá chính thức 2026
   - Xác nhận giá sỉ theo volume
   - Cập nhật điều kiện thanh toán

### Ưu tiên thấp

5. ⏳ Cập nhật giá phụ kiện (accessories)
   - Trip unit cho MCCB
   - Auxiliary contact
   - Shunt trip, undervoltage release
   - Mounting accessories

6. ⏳ Theo dõi thay đổi giá
   - Thiết lập quy trình review định kỳ (quarterly)
   - Alert khi có thay đổi giá lớn
   - Version control cho price history

## Files đã thay đổi

Script đã thay đổi 62 files JSON trong thư mục:
```
e:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\Schneider\ThietBi\
```

Các file này đã được thêm trường `gia_ban` và sẵn sàng để commit vào Git.

## Script sử dụng

File script: `e:\duytristool\AIDE_website\BE_AIDE\update_schneider_prices.ps1`

Chạy lại script:
```powershell
e:\duytristool\AIDE_website\BE_AIDE\update_schneider_prices.ps1
```

---

**Người thực hiện:** Autonomous Research Subagent
**Ngày:** 16/10/2026
**Trạng thái:** ✅ Hoàn thành giai đoạn 1 (Main product lines)
