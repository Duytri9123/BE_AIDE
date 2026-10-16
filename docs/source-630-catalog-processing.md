# Xử lý toàn bộ 630 mục CAD nguồn — 16/10/2026

Bảng tra cứu dùng thông tin thiết bị và catalog tham khảo, độc lập dữ liệu giá. Giá hiển thị `---`. Mã tương tự là lựa chọn dùng chung hình CAD, không đổi nhãn hãng gốc hoặc tự xác nhận thông số từ hình dáng.

- 467 hồ sơ thông tin nguồn đưa vào tra cứu; 160 bản lặp hình học liên kết về hồ sơ tương ứng.
- 2 bản form rỗng được ghi nhận bằng thông tin nguồn; 1 DWG là kho thư viện tổng, không tính thành thiết bị mới.
- Đọc chữ/thuộc tính nguồn, xem các bảng ảnh tổng hợp và bổ sung 143 ảnh xem trước trước đây chưa có.
- Thư viện hiển thị 1304 mục với 1915 mặt CAD; không có bảng thông tin trống.
- Bổ sung bảng hãng/mã/thông số và tài liệu cho 5 mẫu chống sét; mẫu trong ảnh có sơ đồ cực 3P+N đọc từ nguồn.
- Bỏ tra cứu giá tự động và thông báo thiếu giá khỏi trang thư viện.

## Tài liệu hãng đã tra cứu

- [Schneider iPRD40r A9L40601](https://www.se.com/in/en/product/A9L40601/iprd40r-modular-surge-arrester-3p-%2B-n-350v-with-remote-transfert/)
- [Suntree SUP2](https://www.chinasuntree.com/ac-spd/scup2-surge-protector.htm)
- [Mikro ZCT40S–210S](https://itmikro.com.my/wp-content/uploads/2020/08/zct40_60_80_120_210s_man-1.pdf)
- [Socomec TCA21 100/5 A](https://emea.socomec.com/en/generate-pdf/192T2010)
- [Trend/Honeywell IQ4 I/O](https://prod-edam.honeywell.com/content/dam/honeywell-edam/hbt/en-us/documents/literature-and-specs/datasheets/trends-110725/hon-ba-bms-en-ta201341-uk8pr0823n.pdf?download=false)
- [Siemens S7-1200](https://cache.industry.siemens.com/dl/files/829/109814829/att_1120874/v1/s71200_system_manual_en-US_en-US.pdf)
- [Leipole FKL6622](https://leipole.pl/en/products/fkl6622/)
- Các nguồn khác được ghi ở từng lựa chọn trong `source_reference_research.json` và các hồ sơ catalog.

## Kiểm tra

- 56 kiểm thử backend đạt, gồm kiểm đủ 630 nguồn, giữ nguyên SHA-256 nguồn, bảng thông tin, liên kết preview/DXF và mã tham khảo chống sét.
- 13 kiểm tra cuối đạt; đã sửa và kiểm đủ 17 mặt thuộc 8 nhóm CAD ghép nhiều hồ sơ, không cho phép lấy nhầm mặt từ nhóm khác.
- Vite build đạt; kiểm tra giao diện desktop/mobile với API giả lập đạt và không gọi API tra giá.
- Bảng ảnh kiểm tra: `outputs/source-630-review/`. Dữ liệu đầy đủ và liên kết từng nguồn: `source-630-catalog-processing.json`.

## Danh sách 630 mục

| STT | Nguồn | Nhóm | Mã/dòng đọc từ nguồn | Kết quả |
| ---: | --- | --- | --- | --- |
| 1 | BienDong/TuLieuBanVe/A02_HinhBoSung/ThanhPhanCAD/B_02b84f712da7/ban_ve.dxf | CT | ZCT 80S | Đã lập bảng thông tin |
| 2 | BienDong/TuLieuBanVe/A02_HinhBoSung/ThanhPhanCAD/B_1a2b319dce8d/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 3 | BienDong/TuLieuBanVe/A02_HinhBoSung/ThanhPhanCAD/B_32473c702808/ban_ve.dxf | CT | ZCT 40S | Đã lập bảng thông tin |
| 4 | BienDong/TuLieuBanVe/A02_HinhBoSung/ThanhPhanCAD/B_34096afc564b/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 5 | BienDong/TuLieuBanVe/A02_HinhBoSung/ThanhPhanCAD/B_34d8fb899836/ban_ve.dxf | CT | ZCT 40S | Đã lập bảng thông tin |
| 6 | BienDong/TuLieuBanVe/A02_HinhBoSung/ThanhPhanCAD/B_7efea112d0fe/ban_ve.dxf | CT | ZCT 80S | Đã lập bảng thông tin |
| 7 | BienDong/TuLieuBanVe/BanVeTongHop_A02/BanVeVung/A02-LOOSE-CONTEXT/ban_ve.dxf | CT | ZCT 40S / ZCT 80S | Đã lập bảng thông tin |
| 8 | BienDong/TuLieuBanVe/BanVeTongHop_C08/BanVeVung/C08-LOOSE-CONTEXT/ban_ve.dxf | CT | zct120 / MSQ-125 / MSQ 30 / MSQ-30 / MSQ 40 / MSQ 60 / MSQ 100 / MSQ 125 / EM4H05 / EM4H04 / EM4H03 / EM4H06 / EM4H07 | Đã lập bảng thông tin |
| 9 | BienDong/TuLieuBanVe/BanVeTongHop_C12/BanVeVung/C12-LOOSE-CONTEXT/ban_ve.dxf | CT | MSQ-30 / MSQ-40 / MSQ-60 / MSQ-100 / RCT 35 / RCT 60 / RCT 90 / RCT 110 | Đã lập bảng thông tin |
| 10 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_028fd18345d2/ban_ve.dxf | CT | ZCT-D40 | Đã lập bảng thông tin |
| 11 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_051e49a10b0d/ban_ve.dxf | CT | KDE 1200 | Đã lập bảng thông tin |
| 12 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_07369b552e91/ban_ve.dxf | CT | MSQ-30 | Đã lập bảng thông tin |
| 13 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_07694028a2ed/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 14 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_0f7139f859a5/ban_ve.dxf | CT | KDE 800A / KDE 800 | Đã lập bảng thông tin |
| 15 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_15d1c3e0c18e/ban_ve.dxf | CT | CML 250 | Đã lập bảng thông tin |
| 16 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_17520622073d/ban_ve.dxf | CT | CML3200A | Đã lập bảng thông tin |
| 17 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_1aceb8eaaad7/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 18 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_1d39f975c2ba/ban_ve.dxf | CT | CML800A / CML 800 | Đã lập bảng thông tin |
| 19 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_1fb023b958ce/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 20 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_213b74ef4473/ban_ve.dxf | CT | CML3200A | Đã lập bảng thông tin |
| 21 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_25a71c0fabb6/ban_ve.dxf | CT | CML500A | Đã lập bảng thông tin |
| 22 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_266fa1a62de2/ban_ve.dxf | CT | KDE 800A / KDE 800 | Đã lập bảng thông tin |
| 23 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_29c32c650ad4/ban_ve.dxf | CT | CML250A | Đã lập bảng thông tin |
| 24 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_2b05a1c25364/ban_ve.dxf | CT | CML400A | Đã lập bảng thông tin |
| 25 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_2ebfb3794c25/ban_ve.dxf | CT | MSQ-40 | Đã lập bảng thông tin |
| 26 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_3498b0f69a25/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 27 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_390730bd1f8b/ban_ve.dxf | CT | CML3200A / CML 3200 | Đã lập bảng thông tin |
| 28 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_3afdc96b35e6/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 29 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_3d66e17f7807/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 30 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_3e2270387fe0/ban_ve.dxf | CT | CML400A | Đã lập bảng thông tin |
| 31 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_3f8ecf9c2d18/ban_ve.dxf | CT | CML500A / CML 500 | Đã lập bảng thông tin |
| 32 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_40eaec578417/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 33 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_4281aac825cf/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 34 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_4919ab9424be/ban_ve.dxf | CT | CML500A | Đã lập bảng thông tin |
| 35 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_4ab8a4f623b7/ban_ve.dxf | CT | ZCT-D40 | Đã lập bảng thông tin |
| 36 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_531f93c6e9df/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 37 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_54f1e1f6161e/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 38 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_5c29ae902547/ban_ve.dxf | CT | CML800A | Đã lập bảng thông tin |
| 39 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_5d70f028272c/ban_ve.dxf | CT | MSQ-30 | Đã lập bảng thông tin |
| 40 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_5f7fda713afe/ban_ve.dxf | CT | MSQ-40 | Đã lập bảng thông tin |
| 41 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_6596c89691e3/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 42 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_6a7c147ac67b/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 43 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_6b603137ab7d/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 44 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_6ee573a7d5e8/ban_ve.dxf | CT | MSQ-125 | Đã lập bảng thông tin |
| 45 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_7041fb11f4a9/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 46 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_725c9d6a06f7/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 47 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_74a951467be4/ban_ve.dxf | CT | KDE 1200 | Đã lập bảng thông tin |
| 48 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_866dab86858d/ban_ve.dxf | CT | KDE 400 | Đã lập bảng thông tin |
| 49 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_9356491d433e/ban_ve.dxf | CT | CML 400 | Đã lập bảng thông tin |
| 50 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_9e6d9705df9e/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 51 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_a01219cc9872/ban_ve.dxf | CT | CML800A | Đã lập bảng thông tin |
| 52 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_a1eb2f5745cb/ban_ve.dxf | CT | CML250A | Đã lập bảng thông tin |
| 53 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_b6f8f7e2ebfd/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 54 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_b87135bd529b/ban_ve.dxf | CT | KDE 300A / KDE 300 | Đã lập bảng thông tin |
| 55 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_bad775d4e441/ban_ve.dxf | CT | KDE 300A / KDE 300 | Đã lập bảng thông tin |
| 56 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_c08714b7b4ac/ban_ve.dxf | CT | MSQ-125 | Đã lập bảng thông tin |
| 57 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_c47f0d6ea2b5/ban_ve.dxf | CT | MSQ-125 | Đã lập bảng thông tin |
| 58 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_ce8e7351011a/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 59 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_d00c1a19a890/ban_ve.dxf | CT | ZCT-D40 | Đã lập bảng thông tin |
| 60 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_dddcd80b3706/ban_ve.dxf | CT | KDE 1200 | Đã lập bảng thông tin |
| 61 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_dde41e5f0c67/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 62 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_de60a22b063f/ban_ve.dxf | CT | KDE 300A / KDE 300 | Đã lập bảng thông tin |
| 63 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_e5418220102f/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 64 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_ece65c87126f/ban_ve.dxf | CT | MSQ-60 | Đã lập bảng thông tin |
| 65 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_fa20026c4679/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 66 | BienDong/TuLieuBanVe/C08_HinhBoSung/ThanhPhanCAD/B_fbec7714486d/ban_ve.dxf | CT | KDE 800A / KDE 800 | Đã lập bảng thông tin |
| 67 | BienDong/TuLieuBanVe/C08_HinhBoSung_CML/HinhChieu/C08_cluster9-V014/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 68 | BienDong/TuLieuBanVe/C08_HinhBoSung_CML/HinhChieu/C08_cluster9-V015/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 69 | BienDong/TuLieuBanVe/C08_HinhBoSung_EM4H/ThanhPhanCAD/B_21b82d8686a1/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 70 | BienDong/TuLieuBanVe/C08_HinhBoSung_EM4H/ThanhPhanCAD/B_68bf5b4b64cd/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 71 | BienDong/TuLieuBanVe/C08_HinhBoSung_EM4H/ThanhPhanCAD/B_85850de99a06/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 72 | BienDong/TuLieuBanVe/C08_HinhBoSung_EM4H/ThanhPhanCAD/B_bec2d68db498/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 73 | BienDong/TuLieuBanVe/C08_HinhBoSung_EM4H/ThanhPhanCAD/B_d29bd4f0ce44/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 74 | BienDong/TuLieuBanVe/C08_HinhBoSung_MSQ-125_LienQuan/HinhChieu/C08_cluster8-V009/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 75 | BienDong/TuLieuBanVe/C08_HinhBoSung_MSQ-125_LienQuan/HinhChieu/C08_cluster8-V013/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 76 | BienDong/TuLieuBanVe/C08_HinhBoSung_MSQ-125_LienQuan/HinhChieu/C08_cluster8-V014/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 77 | BienDong/TuLieuBanVe/C08_HinhBoSung_MSQ-125_LienQuan/HinhChieu/C08_cluster8-V017/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 78 | BienDong/TuLieuBanVe/C12_HinhBoSung/HinhChieu/C12_cluster1-V004/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 79 | BienDong/TuLieuBanVe/C12_HinhBoSung/ThanhPhanCAD/B_04bd7bddb814/ban_ve.dxf | CT | MSQ-30 | Đã lập bảng thông tin |
| 80 | BienDong/TuLieuBanVe/C12_HinhBoSung/ThanhPhanCAD/B_090c79fafc3e/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 81 | BienDong/TuLieuBanVe/C12_HinhBoSung/ThanhPhanCAD/B_170c009a16e9/ban_ve.dxf | CT | RCT35 | Đã lập bảng thông tin |
| 82 | BienDong/TuLieuBanVe/C12_HinhBoSung/ThanhPhanCAD/B_2fe0977dd1f5/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 83 | BienDong/TuLieuBanVe/C12_HinhBoSung/ThanhPhanCAD/B_303470efdbdd/ban_ve.dxf | CT | RCT90 | Đã lập bảng thông tin |
| 84 | BienDong/TuLieuBanVe/C12_HinhBoSung/ThanhPhanCAD/B_39ef495efde0/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 85 | BienDong/TuLieuBanVe/C12_HinhBoSung/ThanhPhanCAD/B_468751e389d8/ban_ve.dxf | CT | RCT60 | Đã lập bảng thông tin |
| 86 | BienDong/TuLieuBanVe/C12_HinhBoSung/ThanhPhanCAD/B_69ceb2700fa6/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 87 | BienDong/TuLieuBanVe/C12_HinhBoSung/ThanhPhanCAD/B_7a95ad8691ae/ban_ve.dxf | CT | RCT110 | Đã lập bảng thông tin |
| 88 | BienDong/TuLieuBanVe/C12_HinhBoSung/ThanhPhanCAD/B_7c88204c5386/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 89 | BienDong/TuLieuBanVe/C12_HinhBoSung/ThanhPhanCAD/B_885ec23dd836/ban_ve.dxf | CT | RCT60 | Đã lập bảng thông tin |
| 90 | BienDong/TuLieuBanVe/C12_HinhBoSung/ThanhPhanCAD/B_8e3e83a55696/ban_ve.dxf | CT | RCT35 | Đã lập bảng thông tin |
| 91 | BienDong/TuLieuBanVe/C12_HinhBoSung/ThanhPhanCAD/B_961b26ed5e78/ban_ve.dxf | CT | RCT90 | Đã lập bảng thông tin |
| 92 | BienDong/TuLieuBanVe/C12_HinhBoSung/ThanhPhanCAD/B_9ecec2535c43/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 93 | BienDong/TuLieuBanVe/C12_HinhBoSung/ThanhPhanCAD/B_9f7aac653f04/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 94 | BienDong/TuLieuBanVe/C12_HinhBoSung/ThanhPhanCAD/B_a6f0bd3c2905/ban_ve.dxf | CT | RCT110 | Đã lập bảng thông tin |
| 95 | BienDong/TuLieuBanVe/C12_HinhBoSung/ThanhPhanCAD/B_bb06261e37c3/ban_ve.dxf | CT | RCT35 | Đã lập bảng thông tin |
| 96 | BienDong/TuLieuBanVe/C12_HinhBoSung/ThanhPhanCAD/B_bff1d044a699/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 97 | BienDong/TuLieuBanVe/C12_HinhBoSung/ThanhPhanCAD/B_c0039ba72a9b/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 98 | BienDong/TuLieuBanVe/C12_HinhBoSung/ThanhPhanCAD/B_d6b08c66afd5/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 99 | BienDong/TuLieuBanVe/C12_HinhBoSung/ThanhPhanCAD/B_e2bd47fd30d6/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 100 | BienDong/TuLieuBanVe/CumTongHop_A02/BanVeCum/A02_abb-COMPLETE/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 101 | BienDong/TuLieuBanVe/CumTongHop_A02/BanVeCum/A02_set1-COMPLETE/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 102 | BienDong/TuLieuBanVe/CumTongHop_A02/BanVeCum/A02_set2-COMPLETE/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 103 | BienDong/TuLieuBanVe/CumTongHop_A02/BanVeCum/A02_set3-COMPLETE/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 104 | BienDong/TuLieuBanVe/CumTongHop_A02/BanVeCum/A02_set4-COMPLETE/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 105 | BienDong/TuLieuBanVe/CumTongHop_A02/BanVeCum/A02_set5-COMPLETE/ban_ve.dxf | CT | ZCT 40S | Đã lập bảng thông tin |
| 106 | BienDong/TuLieuBanVe/CumTongHop_A02/BanVeCum/A02_set6-COMPLETE/ban_ve.dxf | CT | ZCT 80S | Đã lập bảng thông tin |
| 107 | BienDong/TuLieuBanVe/CumTongHop_A02/BanVeCum/A02_set7-COMPLETE/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 108 | BienDong/TuLieuBanVe/CumTongHop_C08/BanVeCum/C08_cluster10-COMPLETE/ban_ve.dxf | CT | EM4H05 / EM4H04 / EM4H03 / EM4H06 / EM4H07 | Đã lập bảng thông tin |
| 109 | BienDong/TuLieuBanVe/CumTongHop_C08/BanVeCum/C08_cluster11-COMPLETE/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 110 | BienDong/TuLieuBanVe/CumTongHop_C08/BanVeCum/C08_cluster2-COMPLETE/ban_ve.dxf | CT | zct120 / ZCT-D40 | Đã lập bảng thông tin |
| 111 | BienDong/TuLieuBanVe/CumTongHop_C08/BanVeCum/C08_cluster3-COMPLETE/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 112 | BienDong/TuLieuBanVe/CumTongHop_C08/BanVeCum/C08_cluster4-COMPLETE/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 113 | BienDong/TuLieuBanVe/CumTongHop_C08/BanVeCum/C08_cluster5-COMPLETE/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 114 | BienDong/TuLieuBanVe/CumTongHop_C08/BanVeCum/C08_cluster6-COMPLETE/ban_ve.dxf | CT | Theo mẫu CAD | Đã lập bảng thông tin |
| 115 | BienDong/TuLieuBanVe/CumTongHop_C08/BanVeCum/C08_cluster7-COMPLETE/ban_ve.dxf | CT | MSQ 30 / MSQ-30 / MSQ 40 / MSQ 60 / MSQ 100 / MSQ 125 / MSQ-40 / MSQ-60 | Đã lập bảng thông tin |
| 116 | BienDong/TuLieuBanVe/CumTongHop_C08/BanVeCum/C08_cluster8-COMPLETE/ban_ve.dxf | CT | MSQ-125 / MSQ-30 / KDE 800 / KDE 300 / KDE 400 / KDE 1200 | Đã lập bảng thông tin |
| 117 | BienDong/TuLieuBanVe/CumTongHop_C08/BanVeCum/C08_cluster9-COMPLETE/ban_ve.dxf | CT | CML 500 / CML 800 / CML 3200 / CML 250 / CML 400 | Đã lập bảng thông tin |
| 118 | BienDong/TuLieuBanVe/CumTongHop_C12/BanVeCum/C12_cluster1-COMPLETE/ban_ve.dxf | CT | MSQ-30 / MSQ-40 / MSQ-60 / MSQ-100 / RCT 35 / RCT 60 / RCT 90 / RCT 110 | Đã lập bảng thông tin |
| 119 | Cuộn kháng/TuLieuBanVe/C11/BanVeCum/C11_cluster2-COMPLETE/ban_ve.dxf | REACTOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 120 | Cuộn kháng/TuLieuBanVe/C11/BanVeCum/C11_cluster3-COMPLETE/ban_ve.dxf | REACTOR | Theo mẫu CAD | Đã liên kết hình lặp |
| 121 | Cuộn kháng/TuLieuBanVe/C11/BanVeCum/C11_cluster4-COMPLETE/ban_ve.dxf | REACTOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 122 | Cuộn kháng/TuLieuBanVe/C11/BanVeCum/C11_cluster5-COMPLETE/ban_ve.dxf | FIRE_SUPPRESSION_REFERENCE | Theo mẫu CAD | Đã lập bảng thông tin |
| 123 | Cuộn kháng/TuLieuBanVe/C11/BanVeCum/C11_cluster6-COMPLETE/ban_ve.dxf | REACTOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 124 | Cuộn kháng/TuLieuBanVe/C11/BanVeCum/C11_cluster7-COMPLETE/ban_ve.dxf | REACTOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 125 | Cuộn kháng/TuLieuBanVe/C11/BanVeVung/C11-LOOSE-CONTEXT/ban_ve.dxf | REACTOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 126 | Cuộn kháng/TuLieuBanVe/C11/HinhChieu/C11_cluster5-V001/ban_ve.dxf | FIRE_SUPPRESSION_REFERENCE | Theo mẫu CAD | Đã lập bảng thông tin |
| 127 | Cuộn kháng/TuLieuBanVe/C11/ThanhPhanCAD/B_3da1423429a4/ban_ve.dxf | REACTOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 128 | Cuộn kháng/TuLieuBanVe/C11/ThanhPhanCAD/B_8e89ee13e5cd/ban_ve.dxf | FIRE_SUPPRESSION_REFERENCE | Theo mẫu CAD | Đã lập bảng thông tin |
| 129 | Cuộn kháng/TuLieuBanVe/C11/ThanhPhanCAD/B_bb5de15b6680/ban_ve.dxf | FIRE_SUPPRESSION_REFERENCE | Theo mẫu CAD | Đã lập bảng thông tin |
| 130 | Cuộn kháng/TuLieuBanVe/C11/ThanhPhanCAD/B_bde97dbb7a03/ban_ve.dxf | REACTOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 131 | Cầu đấu/TuLieuBanVe/C09/BanVeCum/C09_cluster2-COMPLETE/ban_ve.dxf | TERMINAL_BLOCK | Theo mẫu CAD | Đã lập bảng thông tin |
| 132 | Cầu đấu/TuLieuBanVe/C09/BanVeCum/C09_cluster3-COMPLETE/ban_ve.dxf | TERMINAL_BLOCK | Theo mẫu CAD | Đã lập bảng thông tin |
| 133 | Cầu đấu/TuLieuBanVe/C09/BanVeCum/C09_cluster4-COMPLETE/ban_ve.dxf | TERMINAL_BLOCK | CTS25 / CTS6 / CTS4 | Đã lập bảng thông tin |
| 134 | Cầu đấu/TuLieuBanVe/C09/BanVeCum/C09_cluster5-COMPLETE/ban_ve.dxf | TERMINAL_BLOCK | HYT-603 / HYT-604 / HYT-1003 / HYT-1004 / HYT-1503 / HYT-1504 / HYT-2003 / HYT-2004 / HYT-3003 / HYT-3004 / HYT-4003 / HYT-4004 / HYT-5003 / HYT-5004 / HYT-203 / HYT-204 / HYT-303 / HYT-304 | Đã lập bảng thông tin |
| 135 | Cầu đấu/TuLieuBanVe/C09/BanVeCum/C09_cluster6-COMPLETE/ban_ve.dxf | TERMINAL_BLOCK | HYT-1010 / HYT-20 / HYT-30 | Đã lập bảng thông tin |
| 136 | Cầu đấu/TuLieuBanVe/C09/BanVeCum/C09_cluster7-COMPLETE/ban_ve.dxf | TERMINAL_BLOCK | Theo mẫu CAD | Đã lập bảng thông tin |
| 137 | Cầu đấu/TuLieuBanVe/C09/BanVeVung/C09-LOOSE-CONTEXT/ban_ve.dxf | TERMINAL_BLOCK | HYT-1010 / HYT-20 / HYT-30 / HYT-603 / HYT-604 / HYT-1003 / HYT-1004 / HYT-1503 / HYT-1504 / HYT-2003 / HYT-2004 / HYT-3003 / HYT-3004 / HYT-4003 / HYT-4004 / HYT-5003 / HYT-5004 / HYT-203 / HYT-204 / HYT-303 / HYT-304 / CTS25 / CTS6 / CTS4 | Đã lập bảng thông tin |
| 138 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V001/ban_ve.dxf | TERMINAL_BLOCK | Theo mẫu CAD | Đã lập bảng thông tin |
| 139 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V004/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã lập bảng thông tin |
| 140 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V005/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 141 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V006/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 142 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V007/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 143 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V008/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 144 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V009/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 145 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V010/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 146 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V011/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 147 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V012/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 148 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V013/ban_ve.dxf | TERMINAL_STOP | Theo mẫu CAD | Đã lập bảng thông tin |
| 149 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V014/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 150 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V015/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 151 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V016/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 152 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V017/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 153 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V018/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 154 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V019/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 155 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V020/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 156 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V021/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 157 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V022/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 158 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V023/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 159 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V024/ban_ve.dxf | TERMINAL_STOP | Theo mẫu CAD | Đã liên kết hình lặp |
| 160 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V025/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 161 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V026/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 162 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V027/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 163 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V028/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 164 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster2-V029/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 165 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster3-V011/ban_ve.dxf | TERMINAL_BLOCK | Theo mẫu CAD | Đã lập bảng thông tin |
| 166 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V004/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã lập bảng thông tin |
| 167 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V005/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 168 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V006/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 169 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V007/ban_ve.dxf | TERMINAL_STOP | Theo mẫu CAD | Đã liên kết hình lặp |
| 170 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V008/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 171 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V009/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 172 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V010/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 173 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V011/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 174 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V012/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 175 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V013/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 176 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V014/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 177 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V015/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 178 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V016/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 179 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V017/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 180 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V018/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 181 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V019/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 182 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V020/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 183 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V021/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 184 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V022/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 185 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V023/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 186 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V024/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 187 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V025/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 188 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V026/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 189 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V027/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 190 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V028/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 191 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V029/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 192 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V030/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 193 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V031/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 194 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V032/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 195 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V033/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 196 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V034/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 197 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V035/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 198 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V036/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 199 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V037/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 200 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V038/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 201 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V039/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 202 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V040/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 203 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V041/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 204 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V042/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 205 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V043/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 206 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V044/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 207 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V045/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 208 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V046/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 209 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V047/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 210 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V048/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 211 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V049/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 212 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V050/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 213 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V051/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 214 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V052/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 215 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V053/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 216 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V054/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 217 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V055/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 218 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V056/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 219 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V057/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 220 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V058/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 221 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V059/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 222 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V060/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 223 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V061/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 224 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V062/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 225 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V063/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 226 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V064/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 227 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V065/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 228 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V066/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 229 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V067/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 230 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V068/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 231 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V069/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 232 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V070/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 233 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V071/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 234 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V072/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 235 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V073/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 236 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V074/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 237 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V075/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 238 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V076/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 239 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V077/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 240 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V078/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 241 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V079/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 242 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V080/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 243 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V081/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 244 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V082/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 245 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V083/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 246 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V084/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 247 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V085/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 248 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V086/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 249 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V087/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 250 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V088/ban_ve.dxf | TERMINAL_STOP | Theo mẫu CAD | Đã liên kết hình lặp |
| 251 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V089/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 252 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V090/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 253 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V091/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 254 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V092/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 255 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V093/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 256 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V094/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 257 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V095/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 258 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V096/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 259 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V097/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 260 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V098/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 261 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V099/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 262 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V100/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 263 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V101/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 264 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V102/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 265 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V103/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã liên kết hình lặp |
| 266 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V104/ban_ve.dxf | TERMINAL_STOP | Theo mẫu CAD | Đã liên kết hình lặp |
| 267 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster4-V105/ban_ve.dxf | TERMINAL_BLOCK | Theo mẫu CAD | Đã lập bảng thông tin |
| 268 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster5-V019/ban_ve.dxf | TERMINAL_BLOCK | CD_3P-60A | Đã lập bảng thông tin |
| 269 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster5-V020/ban_ve.dxf | TERMINAL_BLOCK | CD_4P-60A | Đã lập bảng thông tin |
| 270 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster6-V004/ban_ve.dxf | TERMINAL_BLOCK | Theo mẫu CAD | Đã lập bảng thông tin |
| 271 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster6-V006/ban_ve.dxf | TERMINAL_BLOCK | Theo mẫu CAD | Đã lập bảng thông tin |
| 272 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster6-V007/ban_ve.dxf | TERMINAL_BLOCK | Theo mẫu CAD | Đã lập bảng thông tin |
| 273 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster6-V008/ban_ve.dxf | TERMINAL_BLOCK | Theo mẫu CAD | Đã lập bảng thông tin |
| 274 | Cầu đấu/TuLieuBanVe/C09/HinhChieu/C09_cluster6-V009/ban_ve.dxf | TERMINAL_BLOCK | Theo mẫu CAD | Đã lập bảng thông tin |
| 275 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_018cd89f31fa/ban_ve.dxf | TERMINAL_BLOCK | Theo mẫu CAD | Đã lập bảng thông tin |
| 276 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_051ae4fda0c8/ban_ve.dxf | TERMINAL_BLOCK | HYT304 | Đã lập bảng thông tin |
| 277 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_0996df36cf57/ban_ve.dxf | TERMINAL_BLOCK | Theo mẫu CAD | Đã lập bảng thông tin |
| 278 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_10ca797eca9d/ban_ve.dxf | TERMINAL_BLOCK | CD_4P-300A | Đã lập bảng thông tin |
| 279 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_1975a2645735/ban_ve.dxf | TERMINAL_BLOCK | CD_3P-300A | Đã lập bảng thông tin |
| 280 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_1c93b9d7e8aa/ban_ve.dxf | TERMINAL_BLOCK | CD_20P-20A | Đã lập bảng thông tin |
| 281 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_34d16a95dc67/ban_ve.dxf | TERMINAL_BLOCK | TB-4P-20A | Đã lập bảng thông tin |
| 282 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_417522d613d0/ban_ve.dxf | TERMINAL_BLOCK | Theo mẫu CAD | Đã lập bảng thông tin |
| 283 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_42a435c4dea5/ban_ve.dxf | TERMINAL_BLOCK | CD_4P-100A | Đã lập bảng thông tin |
| 284 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_44073c2da812/ban_ve.dxf | TERMINAL_BLOCK | CTS4 | Đã lập bảng thông tin |
| 285 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_4a13f094fda2/ban_ve.dxf | TERMINAL_BLOCK | CD_3P-500A | Đã lập bảng thông tin |
| 286 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_4cfd8443645b/ban_ve.dxf | TERMINAL_BLOCK | CD_10P-30A | Đã lập bảng thông tin |
| 287 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_4faf60fc696e/ban_ve.dxf | TERMINAL_BLOCK | CD_3P-150A | Đã lập bảng thông tin |
| 288 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_50d00e7d30ae/ban_ve.dxf | TERMINAL_BLOCK | CD_3P-60A | Đã lập bảng thông tin |
| 289 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_512c06118b1b/ban_ve.dxf | TERMINAL_BLOCK | TB-4P-200A | Đã lập bảng thông tin |
| 290 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_57ead0e23ceb/ban_ve.dxf | TERMINAL_BLOCK | TB-4P-150A | Đã lập bảng thông tin |
| 291 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_597937b323a5/ban_ve.dxf | TERMINAL_BLOCK | TB-12P-20A | Đã lập bảng thông tin |
| 292 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_5e13f10a10e4/ban_ve.dxf | TERMINAL_BLOCK | Theo mẫu CAD | Đã lập bảng thông tin |
| 293 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_61f306e4e9d7/ban_ve.dxf | TERMINAL_BLOCK | CD_4P-150A | Đã lập bảng thông tin |
| 294 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_64eb65b22ca3/ban_ve.dxf | TERMINAL_STOP | Theo mẫu CAD | Đã lập bảng thông tin |
| 295 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_69f6f9d0f57b/ban_ve.dxf | TERMINAL_BLOCK | Theo mẫu CAD | Đã liên kết hình lặp |
| 296 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_6a4c64c9dd11/ban_ve.dxf | TERMINAL_BLOCK | Theo mẫu CAD | Đã lập bảng thông tin |
| 297 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_752f2c3f9c75/ban_ve.dxf | TERMINAL_BLOCK | CD_4P-60A | Đã lập bảng thông tin |
| 298 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_78c92d975a9e/ban_ve.dxf | TERMINAL_BLOCK | TB-4P-60A | Đã lập bảng thông tin |
| 299 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_8b32e9c8660b/ban_ve.dxf | TERMINAL_BLOCK | CD_3P-400A | Đã lập bảng thông tin |
| 300 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_8bf53558b4f8/ban_ve.dxf | TERMINAL_BLOCK | TB-12P-15A | Đã lập bảng thông tin |
| 301 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_8fc9e50bcba3/ban_ve.dxf | TERMINAL_BLOCK | CD_4P-400A | Đã lập bảng thông tin |
| 302 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_8fd43c815d25/ban_ve.dxf | TERMINAL_BLOCK | TB-4P-15A | Đã lập bảng thông tin |
| 303 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_a95b12fd8284/ban_ve.dxf | TERMINAL_BLOCK | TB-4P-30A | Đã lập bảng thông tin |
| 304 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_ac01150fb8aa/ban_ve.dxf | TERMINAL_BLOCK | Theo mẫu CAD | Đã lập bảng thông tin |
| 305 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_ad9456ed21f4/ban_ve.dxf | TERMINAL_BLOCK | CD_1P-100A | Đã lập bảng thông tin |
| 306 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_aea56c49da9d/ban_ve.dxf | TERMINAL_BLOCK | Theo mẫu CAD | Đã lập bảng thông tin |
| 307 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_bbcb1e157a04/ban_ve.dxf | TERMINAL_BLOCK | CTS25 | Đã lập bảng thông tin |
| 308 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_bbdee585ea1a/ban_ve.dxf | TERMINAL_BLOCK | TB-6P-20A | Đã lập bảng thông tin |
| 309 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_bd8174fcc159/ban_ve.dxf | TERMINAL_BLOCK | UK3N | Đã lập bảng thông tin |
| 310 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_be8e2a9063a0/ban_ve.dxf | TERMINAL_BLOCK | CD_4P-200A | Đã lập bảng thông tin |
| 311 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_ccbed7ec68b7/ban_ve.dxf | TERMINAL_BLOCK | CD_4P-500A | Đã lập bảng thông tin |
| 312 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_cdfc03b0d8c1/ban_ve.dxf | TERMINAL_BLOCK | CD_3P-200A | Đã lập bảng thông tin |
| 313 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_e16614710061/ban_ve.dxf | TERMINAL_BLOCK | Theo mẫu CAD | Đã lập bảng thông tin |
| 314 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_eb2470941cb0/ban_ve.dxf | TERMINAL_BLOCK | Theo mẫu CAD | Đã lập bảng thông tin |
| 315 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_ecbc5ebf8da4/ban_ve.dxf | TERMINAL_BLOCK | HYT-203 | Đã lập bảng thông tin |
| 316 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_ee1827a5f8e2/ban_ve.dxf | TERMINAL_BLOCK | HYT-204 | Đã lập bảng thông tin |
| 317 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_ee20b992fa20/ban_ve.dxf | TERMINAL_BLOCK | CTS6 | Đã lập bảng thông tin |
| 318 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_f0325fc56aec/ban_ve.dxf | TERMINAL_BLOCK | CD_10P-10A | Đã lập bảng thông tin |
| 319 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_f453d1fb74e8/ban_ve.dxf | TERMINAL_BLOCK | CD_3P-100A | Đã lập bảng thông tin |
| 320 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_fb0afc7a96bd/ban_ve.dxf | TERMINAL_BLOCK | TB-4P-300A | Đã lập bảng thông tin |
| 321 | Cầu đấu/TuLieuBanVe/C09/ThanhPhanCAD/B_fd325b7a2b51/ban_ve.dxf | TERMINAL_BLOCK | HYT30 | Đã lập bảng thông tin |
| 322 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/A13/BanVeCum/A13_cluster1-COMPLETE/ban_ve.dxf | NAMEPLATE | Theo mẫu CAD | Đã lập bảng thông tin |
| 323 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/A13/BanVeCum/A13_cluster10-COMPLETE/ban_ve.dxf | NAMEPLATE | Theo mẫu CAD | Đã lập bảng thông tin |
| 324 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/A13/BanVeCum/A13_cluster11-COMPLETE/ban_ve.dxf | NAMEPLATE | Theo mẫu CAD | Đã lập bảng thông tin |
| 325 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/A13/BanVeCum/A13_cluster12-COMPLETE/ban_ve.dxf | NAMEPLATE | Theo mẫu CAD | Đã lập bảng thông tin |
| 326 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/A13/BanVeCum/A13_cluster13-COMPLETE/ban_ve.dxf | NAMEPLATE | Theo mẫu CAD | Đã lập bảng thông tin |
| 327 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/A13/BanVeCum/A13_cluster14-COMPLETE/ban_ve.dxf | NAMEPLATE | Theo mẫu CAD | Đã lập bảng thông tin |
| 328 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/A13/BanVeCum/A13_cluster15-COMPLETE/ban_ve.dxf | NAMEPLATE | Theo mẫu CAD | Đã lập bảng thông tin |
| 329 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/A13/BanVeCum/A13_cluster16-COMPLETE/ban_ve.dxf | NAMEPLATE | Theo mẫu CAD | Đã lập bảng thông tin |
| 330 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/A13/BanVeCum/A13_cluster17-COMPLETE/ban_ve.dxf | NAMEPLATE | Theo mẫu CAD | Đã lập bảng thông tin |
| 331 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/A13/BanVeCum/A13_cluster18-COMPLETE/ban_ve.dxf | NAMEPLATE | Theo mẫu CAD | Đã lập bảng thông tin |
| 332 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/A13/BanVeCum/A13_cluster19-COMPLETE/ban_ve.dxf | NAMEPLATE | Theo mẫu CAD | Đã lập bảng thông tin |
| 333 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/A13/BanVeCum/A13_cluster2-COMPLETE/ban_ve.dxf | NAMEPLATE | Theo mẫu CAD | Đã lập bảng thông tin |
| 334 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/A13/BanVeCum/A13_cluster20-COMPLETE/ban_ve.dxf | NAMEPLATE | Theo mẫu CAD | Đã lập bảng thông tin |
| 335 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/A13/BanVeCum/A13_cluster3-COMPLETE/ban_ve.dxf | NAMEPLATE | Theo mẫu CAD | Đã lập bảng thông tin |
| 336 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/A13/BanVeCum/A13_cluster4-COMPLETE/ban_ve.dxf | NAMEPLATE | Theo mẫu CAD | Đã lập bảng thông tin |
| 337 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/A13/BanVeCum/A13_cluster5-COMPLETE/ban_ve.dxf | NAMEPLATE | Theo mẫu CAD | Đã lập bảng thông tin |
| 338 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/A13/BanVeCum/A13_cluster6-COMPLETE/ban_ve.dxf | NAMEPLATE | Theo mẫu CAD | Đã lập bảng thông tin |
| 339 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/A13/BanVeCum/A13_cluster7-COMPLETE/ban_ve.dxf | NAMEPLATE | Theo mẫu CAD | Đã lập bảng thông tin |
| 340 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/A13/BanVeCum/A13_cluster8-COMPLETE/ban_ve.dxf | NAMEPLATE | Theo mẫu CAD | Đã lập bảng thông tin |
| 341 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/A13/BanVeCum/A13_cluster9-COMPLETE/ban_ve.dxf | NAMEPLATE | Theo mẫu CAD | Đã lập bảng thông tin |
| 342 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/A13/BanVeVung/A13-LOOSE-CONTEXT/ban_ve.dxf | NAMEPLATE | Theo mẫu CAD | Đã lập bảng thông tin |
| 343 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/A13/ThanhPhanCAD/B_26452904477c/ban_ve.dxf | LIGHT | Theo mẫu CAD | Đã lập bảng thông tin |
| 344 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/BanVeCum/C03_cluster2-COMPLETE/ban_ve.dxf | PLC | LOGO / 8DO / 16DI / 8UI / 8AO | Đã lập bảng thông tin |
| 345 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/BanVeCum/C03_cluster3-COMPLETE/ban_ve.dxf | CONTACTOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 346 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/BanVeCum/C03_cluster4-COMPLETE/ban_ve.dxf | FUSE_HOLDER | RT18-32 / RT36-00 / RT-32A | Đã lập bảng thông tin |
| 347 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/BanVeCum/C03_cluster5-COMPLETE/ban_ve.dxf | SELECTOR_SWITCH | NP2 | Đã lập bảng thông tin |
| 348 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/BanVeCum/C03_cluster6-COMPLETE/ban_ve.dxf | LIGHT | NP2 | Đã lập bảng thông tin |
| 349 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/BanVeCum/C03_cluster7-COMPLETE/ban_ve.dxf | FUSE_HOLDER | Theo mẫu CAD | Đã lập bảng thông tin |
| 350 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/BanVeVung/C03-LOOSE-CONTEXT/ban_ve.dxf | PLC | LOGO | Đã lập bảng thông tin |
| 351 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/HinhChieu/C03_cluster2-V001/ban_ve.dxf | DDC | iq4 | Đã lập bảng thông tin |
| 352 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/HinhChieu/C03_cluster2-V002/ban_ve.dxf | IO_MODULE | Theo mẫu CAD | Đã lập bảng thông tin |
| 353 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/HinhChieu/C03_cluster2-V003/ban_ve.dxf | IO_MODULE | 16di | Đã lập bảng thông tin |
| 354 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/HinhChieu/C03_cluster2-V004/ban_ve.dxf | IO_MODULE | 8UI | Đã lập bảng thông tin |
| 355 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/HinhChieu/C03_cluster2-V005/ban_ve.dxf | IO_MODULE | Theo mẫu CAD | Đã lập bảng thông tin |
| 356 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/HinhChieu/C03_cluster2-V006/ban_ve.dxf | PLC | S7-1200 | Đã lập bảng thông tin |
| 357 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/HinhChieu/C03_cluster2-V007/ban_ve.dxf | PLC | S7-1200 | Đã lập bảng thông tin |
| 358 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/HinhChieu/C03_cluster2-V008/ban_ve.dxf | PLC | Logo | Đã lập bảng thông tin |
| 359 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/HinhChieu/C03_cluster3-V007/ban_ve.dxf | SOURCE_REFERENCE | Theo mẫu CAD | Đã lập bảng thông tin |
| 360 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/HinhChieu/C03_cluster3-V008/ban_ve.dxf | SOURCE_REFERENCE | Theo mẫu CAD | Đã lập bảng thông tin |
| 361 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/HinhChieu/C03_cluster4-V003/ban_ve.dxf | CONTACTOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 362 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/HinhChieu/C03_cluster4-V005/ban_ve.dxf | CONTACTOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 363 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/HinhChieu/C03_cluster4-V006/ban_ve.dxf | CONTACTOR | Theo mẫu CAD | Đã liên kết hình lặp |
| 364 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/HinhChieu/C03_cluster4-V007/ban_ve.dxf | CONTACTOR | Theo mẫu CAD | Đã liên kết hình lặp |
| 365 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/HinhChieu/C03_cluster4-V008/ban_ve.dxf | TERMINAL_STOP | Theo mẫu CAD | Đã lập bảng thông tin |
| 366 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/HinhChieu/C03_cluster4-V009/ban_ve.dxf | TERMINAL_STOP | Theo mẫu CAD | Đã lập bảng thông tin |
| 367 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/HinhChieu/C03_cluster5-V008/ban_ve.dxf | SELECTOR_SWITCH | Theo mẫu CAD | Đã lập bảng thông tin |
| 368 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/HinhChieu/C03_cluster5-V010/ban_ve.dxf | LIGHT | Theo mẫu CAD | Đã lập bảng thông tin |
| 369 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/HinhChieu/C03_cluster5-V011/ban_ve.dxf | PUSHBUTTON | Theo mẫu CAD | Đã lập bảng thông tin |
| 370 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/HinhChieu/C03_cluster5-V012/ban_ve.dxf | SELECTOR_SWITCH | Theo mẫu CAD | Đã lập bảng thông tin |
| 371 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/HinhChieu/C03_cluster6-V001/ban_ve.dxf | LIGHT | Theo mẫu CAD | Đã lập bảng thông tin |
| 372 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/HinhChieu/C03_cluster6-V012/ban_ve.dxf | LIGHT | Theo mẫu CAD | Đã lập bảng thông tin |
| 373 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_02772f51fb63/ban_ve.dxf | CONTACTOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 374 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_0433dbe5b05f/ban_ve.dxf | SELECTOR_SWITCH | Theo mẫu CAD | Đã lập bảng thông tin |
| 375 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_079301176663/ban_ve.dxf | BUZZER | Theo mẫu CAD | Đã lập bảng thông tin |
| 376 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_1bdf96abf968/ban_ve.dxf | PUSHBUTTON | NP2 | Đã lập bảng thông tin |
| 377 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_1d686a825497/ban_ve.dxf | PUSHBUTTON | NP2 | Đã lập bảng thông tin |
| 378 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_25dfa8083c51/ban_ve.dxf | TERMINAL_STOP | Theo mẫu CAD | Đã lập bảng thông tin |
| 379 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_32d2dc02a930/ban_ve.dxf | SELECTOR_SWITCH | Theo mẫu CAD | Đã lập bảng thông tin |
| 380 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_36cfedb349d8/ban_ve.dxf | CONTACTOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 381 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_456f08e986ba/ban_ve.dxf | PLC | S7-1200 | Đã lập bảng thông tin |
| 382 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_476108a2e1be/ban_ve.dxf | IO_MODULE | 16di / 16DI | Đã lập bảng thông tin |
| 383 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_4965ba35e795/ban_ve.dxf | LIGHT | Theo mẫu CAD | Đã lập bảng thông tin |
| 384 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_5283c21afc31/ban_ve.dxf | DDC | iq4 | Đã lập bảng thông tin |
| 385 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_6160429bf62f/ban_ve.dxf | PUSHBUTTON | Theo mẫu CAD | Đã lập bảng thông tin |
| 386 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_61f9f7632ef6/ban_ve.dxf | SELECTOR_SWITCH | Theo mẫu CAD | Đã lập bảng thông tin |
| 387 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_696b26c03c1d/ban_ve.dxf | FUSE | RT36-00 | Đã lập bảng thông tin |
| 388 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_6e463c907ad4/ban_ve.dxf | SELECTOR_SWITCH | Theo mẫu CAD | Đã lập bảng thông tin |
| 389 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_6ea56fae9eac/ban_ve.dxf | SELECTOR_SWITCH | Theo mẫu CAD | Đã lập bảng thông tin |
| 390 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_702b65c26683/ban_ve.dxf | LIGHT | Theo mẫu CAD | Đã lập bảng thông tin |
| 391 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_70b7bc617371/ban_ve.dxf | FUSE_HOLDER | RT-32A | Đã lập bảng thông tin |
| 392 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_75f5a5e52b93/ban_ve.dxf | LIGHT | Theo mẫu CAD | Đã lập bảng thông tin |
| 393 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_761d14ab3f64/ban_ve.dxf | LIGHT | Theo mẫu CAD | Đã lập bảng thông tin |
| 394 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_7f76c8fb858b/ban_ve.dxf | PUSHBUTTON | NP2 | Đã lập bảng thông tin |
| 395 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_7fdef9e4c32b/ban_ve.dxf | CONTACTOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 396 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_8784dd585f9e/ban_ve.dxf | CONTACTOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 397 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_8d4406ea5d6c/ban_ve.dxf | IO_MODULE | 8UI | Đã lập bảng thông tin |
| 398 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_963696cf729c/ban_ve.dxf | SELECTOR_SWITCH | Theo mẫu CAD | Đã lập bảng thông tin |
| 399 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_9bd5deacc0b0/ban_ve.dxf | LIGHT | Theo mẫu CAD | Đã lập bảng thông tin |
| 400 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_9cf64fc3bafd/ban_ve.dxf | PUSHBUTTON | NP2 | Đã lập bảng thông tin |
| 401 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_a49e46e84440/ban_ve.dxf | PUSHBUTTON | Theo mẫu CAD | Đã lập bảng thông tin |
| 402 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_a879ec09848c/ban_ve.dxf | IO_MODULE | 8AO | Đã lập bảng thông tin |
| 403 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_a9e59a86e10c/ban_ve.dxf | IO_MODULE | 8DO | Đã lập bảng thông tin |
| 404 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_ab67e6f100c1/ban_ve.dxf | PUSHBUTTON | Theo mẫu CAD | Đã lập bảng thông tin |
| 405 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_b6b4207944fa/ban_ve.dxf | CONTACTOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 406 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_baa958404624/ban_ve.dxf | LIGHT | Theo mẫu CAD | Đã lập bảng thông tin |
| 407 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_bbcfb9fdc6b6/ban_ve.dxf | PLC | S7-1200 | Đã lập bảng thông tin |
| 408 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_c32a8831399c/ban_ve.dxf | SELECTOR_SWITCH | Theo mẫu CAD | Đã liên kết hình lặp |
| 409 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_d60153bf10b2/ban_ve.dxf | PLC | Theo mẫu CAD | Đã lập bảng thông tin |
| 410 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_dcae49a71397/ban_ve.dxf | PUSHBUTTON | NP2 | Đã lập bảng thông tin |
| 411 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_ddf3ad451d44/ban_ve.dxf | SELECTOR_SWITCH | Theo mẫu CAD | Đã lập bảng thông tin |
| 412 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_eb09086dbbcb/ban_ve.dxf | CONTACTOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 413 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_ec939d33e0eb/ban_ve.dxf | PUSHBUTTON | Theo mẫu CAD | Đã lập bảng thông tin |
| 414 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_ef3d2aa6c00d/ban_ve.dxf | FUSE_HOLDER | RT18-32 | Đã lập bảng thông tin |
| 415 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_f50be8ccdc10/ban_ve.dxf | CONTACTOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 416 | DenBaoNutNhanCauChiContactor/TuLieuBanVe/C03/ThanhPhanCAD/B_f98bf060b099/ban_ve.dxf | FUSE_HOLDER | Theo mẫu CAD | Đã lập bảng thông tin |
| 417 | Form tủ/Mau/32466f8928b02fdd-107195C/ban_ve.dxf | ENCLOSURE_REFERENCE | Theo mẫu CAD | Đã ghi nhận form rỗng |
| 418 | Form tủ/Mau/32466f8928b02fdd-107195C/ban_ve_co_khung_goc.dxf | ENCLOSURE_REFERENCE | Theo mẫu CAD | Đã lập bảng thông tin |
| 419 | Form tủ/Mau/32466f8928b02fdd-107195C/tham_chieu_dong_goc.dxf | ENCLOSURE_REFERENCE | Theo mẫu CAD | Đã lập bảng thông tin |
| 420 | Form tủ/Mau/72ac9276cbceebee-1086D13/ban_ve.dxf | ENCLOSURE_REFERENCE | Theo mẫu CAD | Đã ghi nhận form rỗng |
| 421 | Form tủ/Mau/72ac9276cbceebee-1086D13/ban_ve_co_khung_goc.dxf | ENCLOSURE_REFERENCE | Theo mẫu CAD | Đã lập bảng thông tin |
| 422 | Form tủ/Mau/72ac9276cbceebee-1086D13/tham_chieu_dong_goc.dxf | ENCLOSURE_REFERENCE | Theo mẫu CAD | Đã lập bảng thông tin |
| 423 | Phíp/TuLieuBanVe/A03/BanVeCum/A03_set1-COMPLETE/ban_ve.dxf | INSULATING_SUPPORT | Theo mẫu CAD | Đã lập bảng thông tin |
| 424 | Phíp/TuLieuBanVe/A03/BanVeCum/A03_set2-COMPLETE/ban_ve.dxf | INSULATING_SUPPORT | Theo mẫu CAD | Đã lập bảng thông tin |
| 425 | Phíp/TuLieuBanVe/A03/BanVeCum/A03_set3-COMPLETE/ban_ve.dxf | INSULATING_SUPPORT | JSJ 270-3P | Đã lập bảng thông tin |
| 426 | Phíp/TuLieuBanVe/A03/BanVeCum/A03_set4-COMPLETE/ban_ve.dxf | INSULATING_SUPPORT | JSJ 290-4P | Đã lập bảng thông tin |
| 427 | Phíp/TuLieuBanVe/A03/BanVeCum/A03_set5-COMPLETE/ban_ve.dxf | INSULATING_SUPPORT | JSJ-180 | Đã lập bảng thông tin |
| 428 | Phíp/TuLieuBanVe/A03/BanVeCum/A03_set6-COMPLETE/ban_ve.dxf | INSULATING_SUPPORT | Theo mẫu CAD | Đã lập bảng thông tin |
| 429 | Phíp/TuLieuBanVe/A03/BanVeCum/A03_set7-COMPLETE/ban_ve.dxf | INSULATING_SUPPORT | Theo mẫu CAD | Đã lập bảng thông tin |
| 430 | Phíp/TuLieuBanVe/A03/BanVeCum/A03_set8-COMPLETE/ban_ve.dxf | INSULATING_SUPPORT | H&T 10D3 | Đã lập bảng thông tin |
| 431 | Phíp/TuLieuBanVe/A03/BanVeCum/A03_set9-COMPLETE/ban_ve.dxf | INSULATING_SUPPORT | Theo mẫu CAD | Đã lập bảng thông tin |
| 432 | Phíp/TuLieuBanVe/A03/BanVeVung/A03-LOOSE-CONTEXT/ban_ve.dxf | INSULATING_SUPPORT | JSJ 290-4P / JSJ 270-3P / H&T 10D3 | Đã lập bảng thông tin |
| 433 | Phíp/TuLieuBanVe/A03/HinhChieu/A03_set1-V001/ban_ve.dxf | INSULATING_SUPPORT | Theo mẫu CAD | Đã lập bảng thông tin |
| 434 | Phíp/TuLieuBanVe/A03/HinhChieu/A03_set1-V002/ban_ve.dxf | INSULATING_SUPPORT | Theo mẫu CAD | Đã lập bảng thông tin |
| 435 | Phíp/TuLieuBanVe/A03/HinhChieu/A03_set2-V001/ban_ve.dxf | INSULATING_SUPPORT | Theo mẫu CAD | Đã lập bảng thông tin |
| 436 | Phíp/TuLieuBanVe/A03/HinhChieu/A03_set3-V001/ban_ve.dxf | INSULATING_SUPPORT | Theo mẫu CAD | Đã lập bảng thông tin |
| 437 | Phíp/TuLieuBanVe/A03/HinhChieu/A03_set3-V002/ban_ve.dxf | INSULATING_SUPPORT | Theo mẫu CAD | Đã lập bảng thông tin |
| 438 | Phíp/TuLieuBanVe/A03/HinhChieu/A03_set4-V001/ban_ve.dxf | INSULATING_SUPPORT | Theo mẫu CAD | Đã lập bảng thông tin |
| 439 | Phíp/TuLieuBanVe/A03/HinhChieu/A03_set4-V002/ban_ve.dxf | INSULATING_SUPPORT | Theo mẫu CAD | Đã lập bảng thông tin |
| 440 | Phíp/TuLieuBanVe/A03/HinhChieu/A03_set5-V001/ban_ve.dxf | INSULATING_SUPPORT | Theo mẫu CAD | Đã lập bảng thông tin |
| 441 | Phíp/TuLieuBanVe/A03/HinhChieu/A03_set5-V002/ban_ve.dxf | INSULATING_SUPPORT | Theo mẫu CAD | Đã lập bảng thông tin |
| 442 | Phíp/TuLieuBanVe/A03/HinhChieu/A03_set6-V001/ban_ve.dxf | INSULATING_SUPPORT | Theo mẫu CAD | Đã lập bảng thông tin |
| 443 | Phíp/TuLieuBanVe/A03/HinhChieu/A03_set6-V002/ban_ve.dxf | INSULATING_SUPPORT | Theo mẫu CAD | Đã lập bảng thông tin |
| 444 | Phíp/TuLieuBanVe/A03/HinhChieu/A03_set7-V001/ban_ve.dxf | INSULATING_SUPPORT | Theo mẫu CAD | Đã lập bảng thông tin |
| 445 | Phíp/TuLieuBanVe/A03/HinhChieu/A03_set7-V002/ban_ve.dxf | INSULATING_SUPPORT | Theo mẫu CAD | Đã lập bảng thông tin |
| 446 | Phíp/TuLieuBanVe/A03/HinhChieu/A03_set8-V001/ban_ve.dxf | INSULATING_SUPPORT | Theo mẫu CAD | Đã lập bảng thông tin |
| 447 | Phíp/TuLieuBanVe/A03/HinhChieu/A03_set8-V002/ban_ve.dxf | INSULATING_SUPPORT | Theo mẫu CAD | Đã lập bảng thông tin |
| 448 | Phíp/TuLieuBanVe/A03/HinhChieu/A03_set9-V001/ban_ve.dxf | INSULATING_SUPPORT | Theo mẫu CAD | Đã liên kết hình lặp |
| 449 | Quạt/TuLieuBanVe/A11/BanVeCum/A11_cluster1-COMPLETE/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã lập bảng thông tin |
| 450 | Quạt/TuLieuBanVe/A11/BanVeCum/A11_cluster2-COMPLETE/ban_ve.dxf | FILTER | Theo mẫu CAD | Đã lập bảng thông tin |
| 451 | Quạt/TuLieuBanVe/A11/BanVeCum/A11_cluster3-COMPLETE/ban_ve.dxf | FAN | Theo mẫu CAD | Đã lập bảng thông tin |
| 452 | Quạt/TuLieuBanVe/A11/BanVeCum/A11_cluster4-COMPLETE/ban_ve.dxf | FAN | Theo mẫu CAD | Đã lập bảng thông tin |
| 453 | Quạt/TuLieuBanVe/A11/BanVeCum/A11_cluster5-COMPLETE/ban_ve.dxf | FAN | Theo mẫu CAD | Đã lập bảng thông tin |
| 454 | Quạt/TuLieuBanVe/A11/BanVeVung/A11-LOOSE-CONTEXT/ban_ve.dxf | FAN | Theo mẫu CAD | Đã lập bảng thông tin |
| 455 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V001/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã lập bảng thông tin |
| 456 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V002/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 457 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V003/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 458 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V004/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 459 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V005/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 460 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V006/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 461 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V007/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 462 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V008/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 463 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V009/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 464 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V010/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 465 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V011/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 466 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V012/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 467 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V013/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 468 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V014/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 469 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V015/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 470 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V016/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã lập bảng thông tin |
| 471 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V017/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 472 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V018/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 473 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V019/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 474 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V020/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 475 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V021/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 476 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V022/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 477 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V023/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 478 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V024/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 479 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V025/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 480 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V026/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 481 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V027/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 482 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V028/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 483 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V029/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 484 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V030/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 485 | Quạt/TuLieuBanVe/A11/HinhChieu/A11_cluster4-V031/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã liên kết hình lặp |
| 486 | Quạt/TuLieuBanVe/A11/ThanhPhanCAD/B_81cc5b170186/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã lập bảng thông tin |
| 487 | Quạt/TuLieuBanVe/A11/ThanhPhanCAD/B_8624d012acae/ban_ve.dxf | VENT_HOOD | Theo mẫu CAD | Đã lập bảng thông tin |
| 488 | Quạt/TuLieuBanVe/A16/BanVeCum/A16_cluster1-COMPLETE/ban_ve.dxf | FILTER | Theo mẫu CAD | Đã lập bảng thông tin |
| 489 | Quạt/TuLieuBanVe/A16/BanVeVung/A16-LOOSE-CONTEXT/ban_ve.dxf | FILTER | Theo mẫu CAD | Đã lập bảng thông tin |
| 490 | Quạt/TuLieuBanVe/A16/ThanhPhanCAD/B_07cd52baae11/ban_ve.dxf | FAN | FKL6621.230 | Đã lập bảng thông tin |
| 491 | Quạt/TuLieuBanVe/A16/ThanhPhanCAD/B_09ff9e95fcd4/ban_ve.dxf | FAN | FKL6622 | Đã lập bảng thông tin |
| 492 | Quạt/TuLieuBanVe/A16/ThanhPhanCAD/B_3ecb7b4780b1/ban_ve.dxf | FAN | FKL6621.230 | Đã lập bảng thông tin |
| 493 | Quạt/TuLieuBanVe/A16/ThanhPhanCAD/B_4f733998ae0d/ban_ve.dxf | FILTER | FKL6623.300 | Đã lập bảng thông tin |
| 494 | Quạt/TuLieuBanVe/A16/ThanhPhanCAD/B_5687e7ce67f4/ban_ve.dxf | FILTER | FKL6622.300 | Đã lập bảng thông tin |
| 495 | Quạt/TuLieuBanVe/A16/ThanhPhanCAD/B_63f23d15641b/ban_ve.dxf | FILTER | FKL6623.300 | Đã lập bảng thông tin |
| 496 | Quạt/TuLieuBanVe/A16/ThanhPhanCAD/B_83d4d97534de/ban_ve.dxf | FILTER | FKL6622.300 | Đã lập bảng thông tin |
| 497 | Quạt/TuLieuBanVe/A16/ThanhPhanCAD/B_b94bea970d0f/ban_ve.dxf | FAN | FKL6622.230 | Đã lập bảng thông tin |
| 498 | Quạt/TuLieuBanVe/A16/ThanhPhanCAD/B_bce1eb242d83/ban_ve.dxf | FAN | FKL6623.230 | Đã lập bảng thông tin |
| 499 | Quạt/TuLieuBanVe/A16/ThanhPhanCAD/B_bed80d663d3d/ban_ve.dxf | FILTER | FKL6623.300 | Đã lập bảng thông tin |
| 500 | Quạt/TuLieuBanVe/A16/ThanhPhanCAD/B_c872c1a8fee7/ban_ve.dxf | FILTER | FKL6621.300 | Đã lập bảng thông tin |
| 501 | Quạt/TuLieuBanVe/A16/ThanhPhanCAD/B_cf727c6449b0/ban_ve.dxf | FILTER | FKL6621.300 | Đã lập bảng thông tin |
| 502 | Quạt/TuLieuBanVe/A16/ThanhPhanCAD/B_cf83ae8f331a/ban_ve.dxf | FILTER | FKL6622.300 | Đã lập bảng thông tin |
| 503 | Quạt/TuLieuBanVe/A16/ThanhPhanCAD/B_e06350e7b5f0/ban_ve.dxf | FILTER | FKL6621.300 | Đã lập bảng thông tin |
| 504 | Quạt/TuLieuBanVe/A16/ThanhPhanCAD/B_f0ae74b78d60/ban_ve.dxf | FILTER | FKL6623.300 | Đã lập bảng thông tin |
| 505 | Quạt/TuLieuBanVe/C01/BanVeCum/C01_cluster2-COMPLETE/ban_ve.dxf | FAN | Theo mẫu CAD | Đã lập bảng thông tin |
| 506 | Quạt/TuLieuBanVe/C01/BanVeCum/C01_cluster3-COMPLETE/ban_ve.dxf | FAN | Theo mẫu CAD | Đã lập bảng thông tin |
| 507 | Quạt/TuLieuBanVe/C01/BanVeCum/C01_cluster4-COMPLETE/ban_ve.dxf | FAN | Theo mẫu CAD | Đã lập bảng thông tin |
| 508 | Quạt/TuLieuBanVe/C01/BanVeCum/C01_cluster5-COMPLETE/ban_ve.dxf | FAN | Theo mẫu CAD | Đã lập bảng thông tin |
| 509 | Quạt/TuLieuBanVe/C01/BanVeCum/C01_cluster6-COMPLETE/ban_ve.dxf | FILTER | FKL6621.230 / FKL6621.300 / FKL6622.230 / FKL6622.300 / FKL6623.230 / FKL6623.300 / FKL6625.230 / FKL6625.300 / FKL6626.230 / FKL6626.300 | Đã lập bảng thông tin |
| 510 | Quạt/TuLieuBanVe/C01/BanVeCum/C01_cluster7-COMPLETE/ban_ve.dxf | FAN | Theo mẫu CAD | Đã lập bảng thông tin |
| 511 | Quạt/TuLieuBanVe/C01/BanVeVung/C01-LOOSE-CONTEXT/ban_ve.dxf | FILTER | FKL6621.230 / FKL6621.300 / FKL6622.230 / FKL6622.300 / FKL6623.230 / FKL6623.300 / FKL6625.230 / FKL6625.300 / FKL6626.230 / FKL6626.300 | Đã lập bảng thông tin |
| 512 | Quạt/TuLieuBanVe/C01/ThanhPhanCAD/B_a3e0de082bf5/ban_ve.dxf | FILTER | Theo mẫu CAD | Đã lập bảng thông tin |
| 513 | Quạt/TuLieuBanVe/C01/ThanhPhanCAD/B_b3bb79329a05/ban_ve.dxf | FILTER | Theo mẫu CAD | Đã lập bảng thông tin |
| 514 | ThietBiDoLuongHienThi/TuLieuBanVe/A01/BanVeCum/A01_cluster2-COMPLETE/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 515 | ThietBiDoLuongHienThi/TuLieuBanVe/A01/BanVeCum/A01_cluster3-COMPLETE/ban_ve.dxf | METER | CV131 / CV141 | Đã lập bảng thông tin |
| 516 | ThietBiDoLuongHienThi/TuLieuBanVe/A01/BanVeCum/A01_cluster4-COMPLETE/ban_ve.dxf | METER | CV130 / CV140 | Đã lập bảng thông tin |
| 517 | ThietBiDoLuongHienThi/TuLieuBanVe/A01/BanVeCum/A01_cluster5-COMPLETE/ban_ve.dxf | METER | CV130 / CV140 | Đã lập bảng thông tin |
| 518 | ThietBiDoLuongHienThi/TuLieuBanVe/A01/BanVeCum/A01_cluster6-COMPLETE/ban_ve.dxf | METER | MV-3Tb | Đã lập bảng thông tin |
| 519 | ThietBiDoLuongHienThi/TuLieuBanVe/A01/BanVeCum/A01_cluster7-COMPLETE/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 520 | ThietBiDoLuongHienThi/TuLieuBanVe/A01/BanVeVung/A01-LOOSE-CONTEXT/ban_ve.dxf | METER | CV131 / CV141 / CV130 / CV140 | Đã lập bảng thông tin |
| 521 | ThietBiDoLuongHienThi/TuLieuBanVe/A01/ThanhPhanCAD/B_0292e6f21087/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 522 | ThietBiDoLuongHienThi/TuLieuBanVe/A01/ThanhPhanCAD/B_0f60a9e6ca64/ban_ve.dxf | METER | MV-3Tb | Đã lập bảng thông tin |
| 523 | ThietBiDoLuongHienThi/TuLieuBanVe/A01/ThanhPhanCAD/B_5e119579364c/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 524 | ThietBiDoLuongHienThi/TuLieuBanVe/A01/ThanhPhanCAD/B_62c1a6c4c71b/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 525 | ThietBiDoLuongHienThi/TuLieuBanVe/A01/ThanhPhanCAD/B_6d29fe570e80/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 526 | ThietBiDoLuongHienThi/TuLieuBanVe/A01/ThanhPhanCAD/B_96dc8ce8ab5f/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 527 | ThietBiDoLuongHienThi/TuLieuBanVe/A01/ThanhPhanCAD/B_d71ec568992e/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 528 | ThietBiDoLuongHienThi/TuLieuBanVe/A01/ThanhPhanCAD/B_e3a25aac577a/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 529 | ThietBiDoLuongHienThi/TuLieuBanVe/A01/ThanhPhanCAD/B_f2ceb9ea2c63/ban_ve.dxf | METER | Theo mẫu CAD | Đã liên kết hình lặp |
| 530 | ThietBiDoLuongHienThi/TuLieuBanVe/A01/ThanhPhanCAD/B_fb10c4e175cb/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 531 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/BanVeCum/C04_cluster2-COMPLETE/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 532 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/BanVeCum/C04_cluster3-COMPLETE/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 533 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/BanVeCum/C04_cluster4-COMPLETE/ban_ve.dxf | METER | PM710 / PM2220 | Đã lập bảng thông tin |
| 534 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/BanVeCum/C04_cluster5-COMPLETE/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 535 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/BanVeCum/C04_cluster6-COMPLETE/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 536 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/BanVeCum/C04_cluster7-COMPLETE/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 537 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/BanVeVung/C04-LOOSE-CONTEXT/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 538 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/HinhChieu/C04_cluster5-V005/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 539 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/HinhChieu/C04_cluster5-V006/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 540 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/HinhChieu/C04_cluster5-V007/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 541 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_061450cc578c/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 542 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_12c35ee3855d/ban_ve.dxf | SELECTOR_METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 543 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_18efc2513a1d/ban_ve.dxf | SELECTOR_METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 544 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_42ad09fd9052/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 545 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_633139d0396a/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 546 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_6471db47fa8f/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 547 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_70597f5b77bb/ban_ve.dxf | SELECTOR_METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 548 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_7569a6298a9d/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 549 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_791dbe26d740/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 550 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_7dfb9fe177f7/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 551 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_7e717b45bed6/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 552 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_855ede0ec7e9/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 553 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_90feb505697d/ban_ve.dxf | SELECTOR_METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 554 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_916773670467/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 555 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_96c6e3e04749/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 556 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_98eaedeba0bb/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 557 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_9f362c00169b/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 558 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_b4bc9ba7086f/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 559 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_b552423b2e91/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 560 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_b6602f58690c/ban_ve.dxf | METER | PM2220 | Đã lập bảng thông tin |
| 561 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_c5ec27bda0c3/ban_ve.dxf | SELECTOR_METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 562 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_d99a0957816d/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 563 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_e73534b1141f/ban_ve.dxf | METER | Theo mẫu CAD | Đã lập bảng thông tin |
| 564 | ThietBiDoLuongHienThi/TuLieuBanVe/C04/ThanhPhanCAD/B_eca080d36a07/ban_ve.dxf | METER | PM710 | Đã lập bảng thông tin |
| 565 | THƯ VIỆN PHỤ KIỆN( Mới nhất).dwg | SOURCE_REFERENCE | Theo mẫu CAD | Đã phân loại kho DWG |
| 566 | Tụ bù/TuLieuBanVe/C10/BanVeCum/C10_cluster2-COMPLETE/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 567 | Tụ bù/TuLieuBanVe/C10/BanVeCum/C10_cluster3-COMPLETE/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 568 | Tụ bù/TuLieuBanVe/C10/BanVeCum/C10_cluster4-COMPLETE/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 569 | Tụ bù/TuLieuBanVe/C10/BanVeCum/C10_cluster5-COMPLETE/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 570 | Tụ bù/TuLieuBanVe/C10/BanVeCum/C10_cluster6-COMPLETE/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 571 | Tụ bù/TuLieuBanVe/C10/BanVeCum/C10_cluster7-COMPLETE/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 572 | Tụ bù/TuLieuBanVe/C10/BanVeVung/C10-LOOSE-CONTEXT/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 573 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_077455dab6ec/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 574 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_14a6e4145ece/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 575 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_20031a0fa2c3/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 576 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_2fa531910b99/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 577 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_33ee377a85d1/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 578 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_363ab30022dc/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 579 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_38485e2151cc/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 580 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_3c12c03595ee/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 581 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_3f458601cf7a/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 582 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_43a75389b9a3/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 583 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_5c8e3e9b0b85/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 584 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_64382c39c83e/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 585 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_777ce83d70ab/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 586 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_8a7528524aac/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 587 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_906ec1a2c8f3/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 588 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_945db2da1999/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 589 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_97d21cd8b013/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 590 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_9abaf5891ba9/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 591 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_9e9bc8788323/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 592 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_a69bf6c0517f/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 593 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_afc70d866f2c/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 594 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_b3fedb2cb842/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 595 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_b468af406c2a/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 596 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_c378b91a413c/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 597 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_d16ed1f94eac/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 598 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_d672c2d5b6c2/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 599 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_dcbe5c5519a1/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 600 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_e302e4ad3228/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 601 | Tụ bù/TuLieuBanVe/C10/ThanhPhanCAD/B_ef25b0e3e0f0/ban_ve.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 602 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster2-V001.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 603 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster2-V002.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 604 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster2-V003.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 605 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster2-V004.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 606 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster2-V005.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 607 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster2-V006.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 608 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster2-V007.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 609 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster3-V001.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 610 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster3-V002.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 611 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster4-V001.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 612 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster4-V002.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 613 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster4-V003.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 614 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster4-V004.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 615 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster4-V005.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 616 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster4-V006.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 617 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster4-V007.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 618 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster5-V001.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 619 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster5-V002.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 620 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster5-V003.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 621 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster5-V004.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 622 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster5-V005.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 623 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster5-V006.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 624 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster5-V007.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 625 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster6-V001.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 626 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster6-V002.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 627 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster6-V003.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 628 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster6-V004.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 629 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster6-V005.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
| 630 | Tụ bù/TuLieuBanVe/CADGoc/C10_cluster6-V006.dxf | CAPACITOR | Theo mẫu CAD | Đã lập bảng thông tin |
