# Hướng dẫn cập nhật giá hàng loạt cho Catalog thiết bị

## Tổng quan

Nhiều thiết bị trong catalog đã có thông tin kỹ thuật và CAD nhưng chưa có thông tin giá bán (`gia_ban`). Tài liệu này hướng dẫn quy trình cập nhật giá hàng loạt.

## Hiện trạng

### Các hãng cần cập nhật giá (ưu tiên cao):
1. **LS Electric** - Hãng chính, nhiều thiết bị nhất
2. **Schneider Electric** - Phổ biến tại VN
3. **ABB** - Đã bắt đầu cập nhật (OVR series)
4. **Mitsubishi** - Nhiều thiết bị công nghiệp
5. **CHINT** - Phổ biến phân khúc giá rẻ
6. **Shihlin** - Phổ biến tại VN

### Các nhóm thiết bị cần cập nhật:

#### 1. Thiết bị bảo vệ
- **MCB** (Aptomat miniat): BKD, MC, S200, iC60, NF, NCH8...
- **MCCB** (Aptomat dòng lớn): NS, NF-SS, ABS, NM8...
- **RCBO** (Aptomat chống giật): BKD-R, DPN Vigi, DS201...
- **RCD/RCCB** (Chống giật thuần): F360, FH200, RCD...
- **SPD** (Chống sét): OVR, PRD, SPD...

#### 2. Thiết bị điều khiển
- **Contactor** (Khởi động từ): MC, LC1D, AX, S-T...
- **Thermal Relay** (Rơ le nhiệt): GTH, LRD, TA...
- **Timer/Counter**: AT, RE, TMR...

#### 3. Phụ kiện
- **Auxiliary Contact** (Tiếp điểm phụ)
- **Coil** (Cuộn dây)
- **Busbar/Terminal** (Thanh cái, cầu đấu)

## Quy trình cập nhật

### Bước 1: Xác định thiết bị cần cập nhật

```bash
# Chạy script quét (nếu có quyền)
python scripts/scan_missing_prices.py

# Kết quả: devices_missing_prices.json, priority_update_list.json
```

### Bước 2: Nghiên cứu giá từ nguồn đáng tin cậy

#### Nguồn giá chính thức:
1. **Bảng giá chính thức từ hãng/đại lý**
   - LS Electric: https://anhphatelectric.com/upload/file/bang-gia-ls-*.pdf
   - Schneider: schneider.net.vn, catalog PDF
   - ABB: shop.in.abb.com, distributor catalogs
   - Mitsubishi: mitsubishielectric.com pricing
   - CHINT: chintglobal.com, distributor pricing

2. **Website đại lý uy tín tại VN**
   - Etinco, Điện Quang, Anh Phát Electric
   - Các đại lý ủy quyền chính thức

3. **Marketplace quốc tế** (để tham khảo)
   - shop.in.abb.com (India)
   - Alibaba (giá sỉ tham khảo)
   - Các distributor châu Âu

#### Lưu ý khi nghiên cứu giá:
- ✅ Ưu tiên bảng giá chính thức từ hãng/đại lý VN
- ✅ Ghi rõ nguồn và ngày cập nhật
- ✅ Đánh dấu mức độ tin cậy
- ❌ KHÔNG tự bịa giá
- ❌ KHÔNG copy giá từ nguồn không rõ ràng

### Bước 3: Cập nhật vào file JSON

Thêm object `gia_ban` vào cuối file `thong_tin_thiet_bi.json`:

```json
{
  "... các trường hiện có ...",
  "gia_ban": {
    "don_gia": "150000-250000",
    "don_vi_tien_te": "VND",
    "trang_thai": "Có giá (phạm vi)",
    "hang": "LS Electric",
    "ma_san_pham": "BKD-3P",
    "ghi_chu": "MCB 3 pha. Giá dao động từ 150K (63A) đến 250K (125A) tùy dòng định mức. Tham khảo từ bảng giá LS Electric 04/2026",
    "nguon_tham_khao": [
      "https://anhphatelectric.com/upload/file/bang-gia-ls-15-04-2026-7279.pdf",
      "Tham khảo đại lý LS Electric Việt Nam"
    ],
    "ngay_cap_nhat": "2026-10-15",
    "muc_do_tin_cay": "Tham khảo - cần xác nhận với nhà cung cấp"
  }
}
```

#### Giải thích các trường:

| Trường | Bắt buộc | Mô tả | Ví dụ |
|--------|----------|-------|-------|
| `don_gia` | ✅ | Giá bán hoặc phạm vi giá | `"250000"` hoặc `"150000-250000"` hoặc `"-"` nếu không có |
| `don_vi_tien_te` | ✅ | Đơn vị tiền tệ | `"VND"` |
| `trang_thai` | ✅ | Trạng thái giá | `"Có giá"`, `"Có giá (phạm vi)"`, `"Chưa có giá"` |
| `hang` | ✅ | Tên hãng | `"LS Electric"`, `"Schneider"`, `"ABB"` |
| `ma_san_pham` | ✅ | Mã sản phẩm cụ thể | `"BKD-3P-63A"` |
| `ghi_chu` | ⭕ | Ghi chú về giá, điều kiện | Mô tả chi tiết về giá |
| `nguon_tham_khao` | ✅ | Array các nguồn tham khảo | Links hoặc tên bảng giá |
| `ngay_cap_nhat` | ✅ | Ngày cập nhật | `"2026-10-15"` |
| `muc_do_tin_cay` | ✅ | Mức độ tin cậy | `"Chính thức"`, `"Tham khảo - cần xác nhận"` |

### Bước 4: Kiểm tra và xác nhận

```bash
# Validate JSON syntax
python -m json.tool path/to/thong_tin_thiet_bi.json

# Test API endpoint
curl http://localhost:8000/device-catalog?brand=LS
```

## Chiến lược cập nhật ưu tiên

### Giai đoạn 1: Các thiết bị phổ biến nhất (1-2 tuần)
- LS Electric MCB: BKD, MC series
- Schneider MCB: iC60, Easy9
- ABB MCB: S200 series
- Contactor phổ biến: MC, LC1D, AX

### Giai đoạn 2: Thiết bị công nghiệp (2-3 tuần)
- MCCB các hãng
- Thermal relay
- SPD đầy đủ

### Giai đoạn 3: Phụ kiện và thiết bị đặc biệt
- Auxiliary contacts
- Coils
- Timers, Counters

## Script hỗ trợ

### 1. Script quét thiết bị chưa có giá
```bash
python scripts/scan_missing_prices.py
```

Output:
- `devices_missing_prices.json`: Danh sách đầy đủ
- `priority_update_list.json`: Danh sách ưu tiên

### 2. Script cập nhật giá từ database có sẵn
```bash
python scripts/batch_update_prices.py --brand LS --category MCB
```

### 3. Script kiểm tra giá đã cập nhật
```bash
python scripts/audit_and_update_prices.py --check-only
```

## Tham khảo giá trung bình thị trường VN (2026)

### MCB (Aptomat miniat)
| Hãng | Dòng | Giá ước tính (VND) |
|------|------|-------------------|
| LS | BKD 1P 6-63A | 50K - 120K |
| LS | BKD 3P 16-63A | 150K - 250K |
| LS | MC 1P 6-63A | 80K - 150K |
| Schneider | iC60 1P 6-63A | 120K - 200K |
| Schneider | iC60 3P 16-63A | 300K - 500K |
| ABB | S200 1P 6-63A | 100K - 180K |
| ABB | S200 3P 16-63A | 280K - 450K |
| Mitsubishi | NF 3P 50-225A | 800K - 2.5M |
| CHINT | NCH8 1P 6-63A | 40K - 80K |
| CHINT | NCH8 3P 16-63A | 100K - 180K |

### Contactor (Khởi động từ)
| Hãng | Dòng | Giá ước tính (VND) |
|------|------|-------------------|
| LS | MC-9 | 120K - 180K |
| LS | MC-22 | 250K - 350K |
| LS | MC-50 | 500K - 700K |
| Schneider | LC1D09 | 180K - 250K |
| Schneider | LC1D25 | 350K - 500K |
| ABB | AX25 | 400K - 550K |
| Mitsubishi | S-T20 | 300K - 450K |

### SPD (Chống sét)
| Hãng | Type | Giá ước tính (VND) |
|------|------|-------------------|
| ABB OVR T1 3N 25-255 | Type 1 | 3.5M - 4.5M |
| ABB OVR T2 3N 40-275 | Type 2 | 1.5M - 2.5M |
| Schneider PRD1 | Type 1+2 | 3M - 4M |
| LS SPD | Type 2 | 1M - 2M |

## Lưu ý quan trọng

### ✅ NÊN:
1. Tham khảo nhiều nguồn trước khi cập nhật
2. Ghi rõ nguồn và ngày cập nhật
3. Dùng phạm vi giá khi không chắc chắn
4. Đánh dấu mức độ tin cậy thấp nếu giá chưa xác nhận
5. Cập nhật theo nhóm thiết bị cùng loại
6. Kiểm tra JSON syntax sau khi chỉnh sửa

### ❌ KHÔNG NÊN:
1. Tự bịa giá khi không có nguồn
2. Copy giá từ nguồn không tin cậy
3. Quên ghi nguồn tham khảo
4. Dùng giá quá cũ (>1 năm)
5. Cập nhật giá không có VAT rõ ràng

## Liên hệ hỗ trợ

- Khi gặp vấn đề về giá, liên hệ đại lý chính thức
- Khi cần bảng giá mới nhất, check website hãng
- Khi không chắc, để `don_gia: "-"` và `trang_thai: "Chưa có giá"`

---

**Cập nhật**: 2026-10-15
**Người thực hiện**: AI Assistant
**Trạng thái**: Đang triển khai
