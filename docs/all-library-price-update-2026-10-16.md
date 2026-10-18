# Rà soát mã và giá toàn bộ thư viện — 16/10/2026

Đã rà 1304 CAD đang hoạt động; 9566 dòng giá công bố.

- 210 CAD có lựa chọn giá theo hãng/mã nguồn.
- 855 CAD có giá của mã catalog tham khảo; không thay đổi mã hay thông số của CAD nguồn.
- 239 CAD chưa có giá công bố trong các nguồn đã đọc.

Dữ liệu giá hiện được đọc trực tiếp cho cả bảng giá chung, bảng giá trong thư viện và từng dòng thông tin catalog. Không còn ghi cứng --- khi có giá theo mã. Mã catalog tham khảo hiển thị riêng với mã nguồn.

Đã kiểm tra lại 22 hãng tại PLE (1.991 dòng), 8 nguồn Etinco (134 dòng). Thêm bảng công bố Morele 2021, LightStar 2022, SmartGen/Deep Sea 2023 và giá cầu đấu/lọc gió. Bảng lịch sử giữ nguyên năm, VAT, nguồn và ngày đọc; không trình bày thành báo giá mới.

Biến áp CHINT: sửa 22 NDK từ ACCESSORY thành TRANSFORMER; có mã, VA và giá trong bảng CHINT 2026. NDK là dòng tham khảo của mẫu CAD chưa có nhãn model; cần chọn đúng điện áp và công suất.

## Các mục còn thiếu giá trong nguồn đã đọc

| ID | Thiết bị | Mã trên nguồn |
| --- | --- | --- |
| TB-1eaa9fd733e664be | Biến dòng đo lường MITEX BD01 | BD01 |
| TB-e1aae03ed2b9afda | Biến dòng · mẫu nguồn 112 | Chưa ghi trên nguồn |
| TB-0679d39feb15577a | Ổn áp ROBOT AP15 · 600 VA | AP15 |
| TB-7d563103819b0e05 | Ổn áp ROBOT AP15 · 350 VA | AP15 |
| TB-ec88a177231283ab | Chống sét lan truyền 3P+N · mẫu tủ điện | Chưa ghi trên nguồn |
| TB-21ba684edc717ea0 | Cuộn kháng ba pha lõi thép | Chưa ghi trên nguồn |
| TB-96b7f99924d77146 | Cuộn kháng · mẫu nguồn 127 | Chưa ghi trên nguồn |
| TB-bbae0a48c712b213 | Cuộn kháng · Cuộn kháng · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-9df20980174b9e96 | Quả cầu chữa cháy · mẫu nguồn 126 | Chưa ghi trên nguồn |
| TB-bbc513c7edcbae1b | Quả cầu chữa cháy · mẫu nguồn 128 | Chưa ghi trên nguồn |
| TB-e5159d050656dffb | Cuộn kháng · mẫu nguồn 130 | Chưa ghi trên nguồn |
| TB-6e6c11347caa054e | Cuộn kháng · Cuộn kháng · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-6a1b8e34ea32ada4 | Quả cầu chữa cháy · Quả cầu chữa cháy · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-54bcbdf3630d56dd | Quả cầu chữa cháy · mẫu nguồn 129 | Chưa ghi trên nguồn |
| TB-dfe3b29209c87d5d | Cuộn kháng · Cuộn kháng · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-9b1356790e518fd7 | Cuộn kháng · Cuộn kháng
Have co · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-cb9dfa1d48b9e388 | Cuộn kháng · Hình rời và chữ nguồn · C11_Cuộn_kháng | Chưa ghi trên nguồn |
| TB-a5afcdc890bd3cb2 | Chặn cuối dãy cầu đấu | Chưa ghi trên nguồn |
| TB-d8c40d8a89cfb999 | Nhãn tủ điện · OFF · NÚT NHẤN OFF · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-7f2679d77ca544b5 | Nhãn tủ điện · TÊN TỦ · (TỪ TỦ............) · TỦ CÓ ĐỘ CAO 1000mm<H<1900mm · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-10104eac05f63ee9 | Nhãn tủ điện · OVERLOAD · ĐÈN BÁO Q.TẢI · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-fe0258a408a59173 | Mô-đun I/O · 16di | 16di |
| TB-98dbe82bb6a78701 | Mô-đun I/O · 8AOOO | 8AO |
| TB-db3fb079e01460a9 | Mô-đun I/O · 8AOOO | Chưa ghi trên nguồn |
| TB-842422323a130c25 | Nhãn tủ điện · ĐÈN VÀNG · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-57b317ab052a7f9b | Nhãn tủ điện · TÊN TỦ · (TỪ TỦ............) · TỦ CÓ ĐỘ CAO 1800mm<H<2100mm · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-bcbfec6046b14c95 | Nhãn tủ điện · TÊN TỦ · (TỪ TỦ............) · TỦ CÓ ĐỘ CAO 500mm<H<1100mm · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-390b36b93b3c2559 | Mô-đun I/O · 8DOO | Chưa ghi trên nguồn |
| TB-9a190ca7b8d438a8 | Nhãn tủ điện · RUN · NÚT NHẤN CHẠY · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-2c559b1ac6b22441 | Nhãn tủ điện · NÚT NHẤN ON · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-0463d64fc9fa0b36 | Bộ điều khiển DDC · iq4 | iq4 |
| TB-0559f25dd9f7794b | Nhãn tủ điện · NHÃN CHO TỪNG CB · LƯỚI ĐIỆN · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-2e81295cbdcfd2f6 | Nhãn tủ điện · TÊN TỦ · (TỪ TỦ............) · TỦ CÓ ĐỘ CAO NHỎ HƠN 500mm · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-953e23af3c3abd3a | Mô-đun I/O · 16di | 16di / 16DI |
| TB-3bb15e7c9ea2ab7e | Nhãn tủ điện · TÊN TỦ · (TỪ TỦ............) · TỦ CÓ ĐỘ CAO H > 2000mm · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-fe8d10c058515939 | Mô-đun I/O · 8UI | 8UI |
| TB-065c20d8a619d4ca | Nhãn tủ điện · TR-O-GE · MẠCH ATS · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-40efe7d320832f12 | Bản vẽ tổng hợp · mẫu nguồn 359 | Chưa ghi trên nguồn |
| TB-35ab3c6519800929 | Nhãn tủ điện · ĐÈN ĐỎ · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-cea370bb6f8396f6 | Nhãn tủ điện · MANU-OFF-AUTO · CHẾ ĐỘ BƠM&ATS · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-a6e7f624be9a94d9 | Nhãn tủ điện · START · NÚT NHẤN CHẠY · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-8b29a1aa4c2c9ec0 | Mô-đun I/O · 8UI | 8UI |
| TB-d3902459713461d4 | Nhãn tủ điện · STT · TÊN NHÃN · GHI CHÚ NỘI DUNG · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-1f2ceefde3e4b7a0 | Mô-đun I/O · 8DOO | 8DO |
| TB-92fc5c6b501be56c | Nhãn tủ điện · www.trivietmec.com · NHÃN GÓC PHẢI NGOÀI CỬA · KHƠNG LÔGO CHÌM · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-07faec11b6b4fb91 | Nhãn tủ điện · MICA NỀN ĐEN CHỮ TRẮNG KHẮC MẶT TRƯỚC DẦY 1.5 mm-2mm · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-a4f54d3e203ae3d3 | Bản vẽ tổng hợp · mẫu nguồn 360 | Chưa ghi trên nguồn |
| TB-f8d9a8367f6350f8 | Nhãn tủ điện · mẫu nguồn 342 | Chưa ghi trên nguồn |
| TB-2f7edcd70ffd8a3b | Bộ điều khiển DDC · iq4 | iq4 |
| TB-5c983e3fff0850b6 | Nhãn tủ điện · ĐÈN XANH · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-bef65578a45598e2 | Nhãn tủ điện · TÊN TỦ · (TỪ TỦ............) · TỦ ĐƯỜNG · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-1d25a0ef890fab64 | Bản vẽ vỏ tủ · Vỏ tủ trong nhà · 800 × 600 × 250 mm | Chưa ghi trên nguồn |
| TB-febb10f684f667ca | Bản vẽ vỏ tủ · Vỏ tủ trong nhà · 800 × 600 × 250 mm | Chưa ghi trên nguồn |
| TB-0f320388698eced4 | Bản vẽ vỏ tủ · Vỏ tủ trong nhà · 1100 × 700 × 250 mm | Chưa ghi trên nguồn |
| TB-a077c6a4c028b8cc | Bản vẽ vỏ tủ · Vỏ tủ trong nhà · 1100 × 700 × 250 mm | Chưa ghi trên nguồn |
| TB-278af148351be520 | Khóa xoay tay nắm bầu dục A-19 | A-19 |
| TB-917f349e19cc1d42 | Khóa tay nắm âm A-480 | A-480 |
| TB-4e23ffa2136e6caf | Khóa tay nắm âm AB301-1-1 | AB301-1-1 |
| TB-b6df5404b4c838b3 | Khóa tay nắm âm AB301-2-1 | AB301-2-1 |
| TB-59d38955a177c6f2 | Khóa tay nắm âm AB301-3-1 | AB301-3-1 |
| TB-aff198a78bb9d890 | Khóa tay nắm âm C45-72 | C45-72 |
| TB-178b8d724531df1e | Chốt cửa tủ nằm ngang | Chưa ghi trên nguồn |
| TB-db1a21898be96568 | Khóa tay nắm âm cửa tủ | Chưa ghi trên nguồn |
| TB-3399f2b31daa8bdd | Khóa bật cửa tủ MS603-3 | Chưa ghi trên nguồn |
| TB-5435ff1c116936c8 | Khóa móc cửa tủ | Chưa ghi trên nguồn |
| TB-ade4d0f601d83bcf | Khóa xoay tay nắm MS301 | MS301 |
| TB-52b6f5f797f80fd1 | Khóa xoay tay nắm MS303 | MS303 |
| TB-29095fb35142be69 | Khóa tay nắm MS308-2 | MS308-2 |
| TB-36062c3659fd1a95 | Khóa cam đầu tam giác MS8712 | MS8712 |
| TB-ed1aa20ea6c4e319 | Tay nắm kéo cửa tủ dạng thanh | Chưa ghi trên nguồn |
| TB-8648167b225ed58d | Tay nắm kéo cửa tủ dạng chữ U | Chưa ghi trên nguồn |
| TB-52f744bc0a433e0d | Khóa xoay đầu tam giác TG-504 | TG-504 |
| TB-27b7e29c45c758e2 | Isolator LS BKD · 3P | BKD |
| TB-b16ce0d68da4dc63 | Isolator LS BKD · 1P | BKD |
| TB-f21cadf4596b45de | Isolator LS BKD · 2P | BKD |
| TB-314d7f80ed188be8 | Isolator LS BKD · 4P | BKD |
| TB-dbde2a18c2811f3d | RCBO LS BS32c · 2P | BS32c |
| TB-434752b0f363bb1d | Giá đỡ/phíp cách điện · MB — mặt bằng (tồn ô) | Chưa ghi trên nguồn |
| TB-1e1fe507f1d426a4 | Giá đỡ/phíp cách điện · MH — mặt hông (tồn ô) | Chưa ghi trên nguồn |
| TB-aba24d9cce6d00e5 | Giá đỡ/phíp cách điện · Thanh phíp JSJ 290-4P — M2 · cụm đầy đủ | JSJ 290-4P |
| TB-ad965509a19dc352 | Giá đỡ/phíp cách điện · JSJ 290-4P / JSJ 270-3P / H&T 10D3 | JSJ 290-4P / JSJ 270-3P / H&T 10D3 |
| TB-c8f1a081ce6c57dd | Giá đỡ/phíp cách điện · Thanh phíp JSJ 270-3P — M1 · cụm đầy đủ | JSJ 270-3P |
| TB-f76c68cc40cde375 | Giá đỡ/phíp cách điện · MB — mặt bằng (tồn ô) | Chưa ghi trên nguồn |
| TB-d711362b3639fccf | Giá đỡ/phíp cách điện · MH — mặt hông (tồn ô) | Chưa ghi trên nguồn |
| TB-770d6471aed252f1 | Giá đỡ/phíp cách điện · MH — mặt hông (tồn ô) | Chưa ghi trên nguồn |
| TB-585a02ca4b6547e4 | Giá đỡ/phíp cách điện · Thanh phíp EUROKLAS — MH1 · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-5f9318d30c4f7551 | Giá đỡ/phíp cách điện · MH — mặt hông (tồn ô) | Chưa ghi trên nguồn |
| TB-c2d76109021bc790 | Giá đỡ/phíp cách điện · Thanh phíp H&T 10D3 — M4 · cụm đầy đủ | H&T 10D3 |
| TB-87ba013967c85c6b | Giá đỡ/phíp cách điện · MB — mặt bằng (tồn ô) | Chưa ghi trên nguồn |
| TB-f5348f7c7388bc75 | Giá đỡ/phíp cách điện · Hàng dưới cùng · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-6b35d79b3f6eeec7 | Giá đỡ/phíp cách điện · Thanh E & N · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-1b154058d078ca1a | Giá đỡ/phíp cách điện · MB — mặt bằng (tồn ô) | Chưa ghi trên nguồn |
| TB-5ab4ab62e1d5e56b | Giá đỡ/phíp cách điện · MH — mặt hông (tồn ô) | Chưa ghi trên nguồn |
| TB-cdc81c0ba5c3bb8d | Giá đỡ/phíp cách điện · MB — mặt bằng (tồn ô) | Chưa ghi trên nguồn |
| TB-d64e1cc490e596f0 | Giá đỡ/phíp cách điện · Thanh phíp JSJ-180 — M3 · cụm đầy đủ | JSJ-180 |
| TB-44c960d7bffa3e9c | Giá đỡ/phíp cách điện · MB — mặt bằng (tồn ô) | Chưa ghi trên nguồn |
| TB-23c851b296a1a677 | Giá đỡ/phíp cách điện · MH — mặt hông (tồn ô) | Chưa ghi trên nguồn |
| TB-ff8105b159cebf76 | Giá đỡ/phíp cách điện · mẫu nguồn 424 | Chưa ghi trên nguồn |
| TB-0801a291eccbd761 | Giá đỡ/phíp cách điện · MB — mặt bằng (tồn ô) | Chưa ghi trên nguồn |
| TB-8c3c1a269c5e7ad6 | Giá đỡ/phíp cách điện · MH — mặt hông (tồn ô) | Chưa ghi trên nguồn |
| TB-249a571531c84756 | Giá đỡ/phíp cách điện · MB — mặt bằng (tồn ô) | Chưa ghi trên nguồn |
| TB-605b6d703d076ec6 | Giá đỡ/phíp cách điện · Thanh phíp EUROKLAS — MH2 · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-edb682f1343f233c | Sứ đỡ cách điện S25 | Chưa ghi trên nguồn |
| TB-02c312ff9f69419b | Sứ đỡ cách điện S35 | Chưa ghi trên nguồn |
| TB-79c4b9f34027f9ef | Sứ đỡ cách điện S50 | Chưa ghi trên nguồn |
| TB-4276dedb85f20711 | Sứ đỡ cách điện S54 | Chưa ghi trên nguồn |
| TB-ddfd20c4e271f155 | Thanh tiếp địa PE | Chưa ghi trên nguồn |
| TB-09ee6df659ecb5f8 | Thanh trung tính N | Chưa ghi trên nguồn |
| TB-52b8f3b17af76c76 | Thanh đỡ cách điện EUROKLAS MH1 | Chưa ghi trên nguồn |
| TB-46d01fae60b93ec8 | Thanh đỡ cách điện EUROKLAS MH2 | Chưa ghi trên nguồn |
| TB-4effe332de8fa479 | Thanh đỡ cách điện H&T 10D3 | Chưa ghi trên nguồn |
| TB-4bb799a046ad2806 | Thanh đỡ cách điện H&T 10D3 | Chưa ghi trên nguồn |
| TB-17afdfabc3e4057b | Thanh đỡ cách điện JSJ-180 | Chưa ghi trên nguồn |
| TB-b211712eaf306136 | Thanh đỡ cách điện JSJ 270-3P | Chưa ghi trên nguồn |
| TB-9ea6475ffef71e1a | Thanh đỡ cách điện JSJ 290-4P | Chưa ghi trên nguồn |
| TB-d72e1472ea3a3f71 | Bản lề cửa kiểu BL2 | Chưa ghi trên nguồn |
| TB-78852ac6d5db6f56 | Bản lề cửa kiểu BL1 | Chưa ghi trên nguồn |
| TB-38b41349cf9bd3fe | Bản lề lá | Chưa ghi trên nguồn |
| TB-8958fd73e1a7f2d5 | Bản lề rùa HL035-1 | Chưa ghi trên nguồn |
| TB-292c49007ad5cd6e | Bản lề HL012 | Chưa ghi trên nguồn |
| TB-f868c07981a83132 | Bản lề chốt nhỏ HL003-2 | Chưa ghi trên nguồn |
| TB-d7b2fbc71d514eb3 | Bản lề âm HL036 | Chưa ghi trên nguồn |
| TB-b0ffc62b3e2446a9 | Bản lề âm chốt nhỏ HL011-2 | Chưa ghi trên nguồn |
| TB-abdfe96cbfb4c565 | Bản lề âm chốt lớn HL011-1 | Chưa ghi trên nguồn |
| TB-1e8eeba3f18ee327 | Bản lề rùa HL044-1.3 | Chưa ghi trên nguồn |
| TB-487a516d2c45f4e6 | Bản lề BL1 | Chưa ghi trên nguồn |
| TB-72d6785bd2a7e302 | Bản lề HL009 | Chưa ghi trên nguồn |
| TB-377c5336fd89339a | Bản lề lá | Chưa ghi trên nguồn |
| TB-8ab08ccdc4115a1d | Bản lề lá | Chưa ghi trên nguồn |
| TB-b2bff9e1fedfd6c7 | Bản lề lá | Chưa ghi trên nguồn |
| TB-b30a6c1cc7a7f860 | Bu lông M6 | Chưa ghi trên nguồn |
| TB-8c2da17a8cf371d7 | Bu lông M8 | Chưa ghi trên nguồn |
| TB-e541a5f6070d4692 | Thanh đấu nối có vít · chưa xác định N hay PE | Chưa ghi trên nguồn |
| TB-cd98a2584706e8a1 | Chi tiết đỡ cách điện | Chưa ghi trên nguồn |
| TB-524e95a56f0db362 | Đầu cos đồng 120-2 | Chưa ghi trên nguồn |
| TB-a2f8e0f2ca77db6b | Đầu cos đồng 185-2 | Chưa ghi trên nguồn |
| TB-c010399c42fa1e51 | Đầu cos đồng 240-2 | Chưa ghi trên nguồn |
| TB-1839ab158418bb0f | Đầu cos đồng 300-2 | Chưa ghi trên nguồn |
| TB-42c91655b95ff19c | Đầu cos đồng 400-2 | Chưa ghi trên nguồn |
| TB-599aabab109fdb0f | Đầu cos đồng 70-2 | Chưa ghi trên nguồn |
| TB-3bb98751f69d0f9a | Cửa sổ quan sát công tơ | Chưa ghi trên nguồn |
| TB-9d529cb9d4d1bdf3 | Đai ốc M8 | Chưa ghi trên nguồn |
| TB-5c9512a18885aebd | Đai ốc M8 có vành | Chưa ghi trên nguồn |
| TB-0c95627f08a91c9b | Kẹp thanh đồng | Chưa ghi trên nguồn |
| TB-d4339effbd6dfd35 | Khay tài liệu gắn cửa tủ | Chưa ghi trên nguồn |
| TB-10b119b014db49a6 | Khóa bấm rời | Chưa ghi trên nguồn |
| TB-d6d6d1f66a58c42f | Khóa bấm cỡ lớn | Chưa ghi trên nguồn |
| TB-69f04cd2cff8f29e | Khóa bấm cỡ trung AB301-3-1 | Chưa ghi trên nguồn |
| TB-7556b9c95868d33f | Khóa bấm cỡ nhỏ AB301-2-1 | Chưa ghi trên nguồn |
| TB-72c746c9a65dbd42 | Khóa bấm A47036 | Chưa ghi trên nguồn |
| TB-da1c4a8b50f8a406 | Khóa bấm MS463-1-1A | Chưa ghi trên nguồn |
| TB-84585bcc45593871 | Khóa bấm | Chưa ghi trên nguồn |
| TB-a761005d52573288 | Khóa tay xoay MS306-1 | Chưa ghi trên nguồn |
| TB-762ef7c3f2c96e0b | Khóa tay xoay A2055 | Chưa ghi trên nguồn |
| TB-ff4208e8c88fbd54 | Khóa tay xoay A45 | Chưa ghi trên nguồn |
| TB-2483f10fd3a74fbf | Khóa tay xoay A19 | Chưa ghi trên nguồn |
| TB-1d2f81170dc95a44 | Khóa chìa hai ngạnh MS705-1 | Chưa ghi trên nguồn |
| TB-bc1d3104684ef2a5 | Máng đi dây nhựa | Chưa ghi trên nguồn |
| TB-4e6f35fc6906709b | Nhãn cài thiết bị | Chưa ghi trên nguồn |
| TB-b098a41ae7519cdf | Nhãn cảnh báo điện | Chưa ghi trên nguồn |
| TB-6902b698232ae235 | Cặp sứ đỡ thanh cái | Chưa ghi trên nguồn |
| TB-a23683c6bce4fdcc | Đế sứ đỡ thanh cái | Chưa ghi trên nguồn |
| TB-35d5f6ac06c62b1a | Giá kẹp thanh cái | Chưa ghi trên nguồn |
| TB-a05cb5784ea023a1 | Thanh kẹp cách điện | Chưa ghi trên nguồn |
| TB-a9917dfc9cda12e9 | Thanh kẹp cách điện | Chưa ghi trên nguồn |
| TB-2ce8034a8f9668e5 | Sứ kẹp thanh cái C100 | Chưa ghi trên nguồn |
| TB-5b69345b0ea9f644 | Bộ kẹp thanh cái EL | Chưa ghi trên nguồn |
| TB-664d771fc2e9d481 | Móc cẩu tủ M10 | Chưa ghi trên nguồn |
| TB-4a012ca97d55686c | Tai cẩu dạng bản mã | Chưa ghi trên nguồn |
| TB-190d4f1dac101777 | Tai treo tủ | Chưa ghi trên nguồn |
| TB-7f2505fa52e94f12 | Thanh đỡ cách điện | Chưa ghi trên nguồn |
| TB-27108f58f410eb3c | Thanh đỡ cách điện | Chưa ghi trên nguồn |
| TB-32c71b5463817fd5 | Vít vặn cửa tủ | Chưa ghi trên nguồn |
| TB-f1eb7e2f7467e500 | Bộ lọc gió tủ điện | Chưa ghi trên nguồn |
| TB-87ad208976fb3917 | Bộ lọc gió tủ điện | Chưa ghi trên nguồn |
| TB-c325b83cc0142751 | Bộ lọc gió tủ điện | Chưa ghi trên nguồn |
| TB-500a3daeec15006f | Lưới thông gió tủ điện | Chưa ghi trên nguồn |
| TB-5fb4ad731f287a45 | Lưới thông gió tủ điện | Chưa ghi trên nguồn |
| TB-8e7495f0e0375022 | Chụp che quạt · mẫu nguồn 455 | Chưa ghi trên nguồn |
| TB-37b0c9db1c56b2c5 | Chụp che quạt · mẫu nguồn 486 | Chưa ghi trên nguồn |
| TB-a5929e58be9b9f65 | Chụp che quạt · CHỤP CHE QUẠT D120 · CHỤP CHE D150 · Rainbow · cụm đầy đủ | Chưa ghi trên nguồn |
| TB-d8f354a43b66380a | Chụp che quạt · KQ | Chưa ghi trên nguồn |
| TB-3d10ba6edee36321 | Chụp che quạt · KQ | Chưa ghi trên nguồn |
| TB-21713c983692514d | Lưới bảo vệ quạt | Chưa ghi trên nguồn |
| TB-bb5602d5a042b864 | RMU CCVV-24kV | CCVV-24kV |
| TB-c3480c14384412ab | RMU CV-24kV | CV-24kV |
| TB-8ba80bde8d79739e | RMU CCV-24kV | CCV-24kV |
| TB-09a12e70ee0e2c12 | RMU CCV-40.5kV | CCV-40.5kV |
| TB-c49963cb873aedf1 | RMU CCVVV-40.5kV | CCVVV-40.5kV |
| TB-4886467a0a9e0fef | RMU RM6-NE:DI | RM6-NE:DI |
| TB-974341d8618d129d | RMU RM6-NE:IiI | RM6-NE:IiI |
| TB-13a413428ea18f5c | Mẫu khoét/lắp đặt Schneider · MCCB LỖ ĐỤC ROTARY HANDLE | Chưa ghi trên nguồn |
| TB-a867fda856a6f81b | Mẫu khoét/lắp đặt Schneider · MCCB LỖ ĐỤC NS06b~160N3M2 3~4 PHASE | Chưa ghi trên nguồn |
| TB-26df5a39993a5d8d | Mẫu khoét/lắp đặt Schneider · MCCB LÕ ĐỤC EZC100 3 PHASE | Chưa ghi trên nguồn |
| TB-8364b6075caa2a48 | Cụm chuyển nguồn Schneider · CAD lắp đặt | Chưa ghi trên nguồn |
| TB-8d768ae917ba96e2 | Mẫu khoét/lắp đặt Schneider · MCCB LÕ ĐỤC EZC100 3~4 PHASE | Chưa ghi trên nguồn |
| TB-cb75104f47e9c48c | Mẫu khoét/lắp đặt Schneider · MCCB LỖ ĐỤC CVS400~630F~N 3~4 PHASE | Chưa ghi trên nguồn |
| TB-2101095072707459 | Mẫu khoét/lắp đặt Schneider · MCB LỖ ĐỤC 2 PHASE | Chưa ghi trên nguồn |
| TB-a9db091b2354a6a6 | Mẫu khoét/lắp đặt Schneider · MCCB LÕ ĐỤC EZC100 2 PHASE | Chưa ghi trên nguồn |
| TB-117815138f330cbe | Cụm chuyển nguồn Schneider · CAD lắp đặt | Chưa ghi trên nguồn |
| TB-36a21d6f19764e8a | Mẫu khoét/lắp đặt Schneider · MCCB LỖ ĐỤC EZC400~630 4 PHASE | Chưa ghi trên nguồn |
| TB-7330d99b1d6effe0 | Mẫu khoét/lắp đặt Schneider · MCCB LỖ ĐỤC EZC250 3 PHASE | Chưa ghi trên nguồn |
| TB-b1cfdedd7e8799ba | Mẫu khoét/lắp đặt Schneider · MCB LỖ ĐỤC 1 PHASE | Chưa ghi trên nguồn |
| TB-ce816ff51360718d | Mẫu khoét/lắp đặt Schneider · MCCB LỖ ĐỤC CVS100~250B~F 3~4 PHASE | Chưa ghi trên nguồn |
| TB-2a096f089f93e3e4 | Mẫu khoét/lắp đặt Schneider · MCCB LỖ ĐỤC EZC250 4 PHASE | Chưa ghi trên nguồn |
| TB-a7617860678230c6 | Mẫu khoét/lắp đặt Schneider · CTT LỖ ĐỤC 1P A9C20731 | Chưa ghi trên nguồn |
| TB-ac81b98b36e67e01 | Mẫu khoét/lắp đặt Schneider · ACB LÕ ĐỤC DRAWOUT | Chưa ghi trên nguồn |
| TB-4577d82dd63da27b | Mẫu khoét/lắp đặt Schneider · MCCB LỖ ĐỤC EZC400~630 3 PHASE | Chưa ghi trên nguồn |
| TB-5c29a91a45b1fb78 | Mẫu khoét/lắp đặt Schneider · MCCB LỖ ĐỤC EZC250 3~4 PHASE | Chưa ghi trên nguồn |
| TB-4d1383db7342995a | Mẫu khoét/lắp đặt Schneider · MCB LỖ ĐỤC 4 PHASE | Chưa ghi trên nguồn |
| TB-a2b48f372146a81f | Cụm chuyển nguồn Schneider · CAD lắp đặt | Chưa ghi trên nguồn |
| TB-ceb791cdafbe0a60 | Cụm chuyển nguồn Schneider · CAD lắp đặt | Chưa ghi trên nguồn |
| TB-ecc9581650e4ccba | Mẫu khoét/lắp đặt Schneider · RCCB LỖ ĐỤC 2 PHASE | Chưa ghi trên nguồn |
| TB-0c0511a6f25efb20 | Mẫu khoét/lắp đặt Schneider · MCCB LỖ ĐỤC-2 CVS100~250B~F 4 PHASE | Chưa ghi trên nguồn |
| TB-dddeabc7ba9f70fb | Mẫu khoét/lắp đặt Schneider · MCCB LỖ ĐỤC NSX100~250BFNH 3 PHASE | Chưa ghi trên nguồn |
| TB-571c337cecd22fa5 | Mẫu khoét/lắp đặt Schneider · MCCB LỖ ĐỤC EZC400~630F~N 3~4 PHASE | Chưa ghi trên nguồn |
| TB-7fcf4a8ea71420a6 | Mẫu khoét/lắp đặt Schneider · MCCB LỖ ĐỤC NS06b~160N4DM2 4 PHASE | Chưa ghi trên nguồn |
| TB-9f7cb0f837b9b0b7 | Mẫu khoét/lắp đặt Schneider · RCCB LỖ ĐỤC 4 PHASE | Chưa ghi trên nguồn |
| TB-e904b26ea73664e1 | Mẫu khoét/lắp đặt Schneider · ACB LÕ ĐỤC FIXED | Chưa ghi trên nguồn |
| TB-1db6ca6b2e8499f5 | Mẫu khoét/lắp đặt Schneider · RCBO LỖ ĐỤC 2 PHASE | Chưa ghi trên nguồn |
| TB-40c7757b4dae8e61 | Mẫu khoét/lắp đặt Schneider · MCB LỖ ĐỤC 3 PHASE | Chưa ghi trên nguồn |
| TB-6f45494575c1fa54 | Mẫu khoét/lắp đặt Schneider · MCCB LÕ ĐỤC EZC100 4 PHASE | Chưa ghi trên nguồn |
| TB-4feb0addbd4ba9a7 | Xa sau (Rev CDTA) · 20×55 mm | Chưa ghi trên nguồn |
| TB-5f085e6a095ca117 | Thanh U ngang 1.5 (Rev CDTA) · 667×120 mm | Chưa ghi trên nguồn |
| TB-4359ec61aa9f2d9f | Thanh U ngang 1.5 (Rev CDTA) · 719×750 mm | Chưa ghi trên nguồn |
| TB-a3f10b1394418a04 | Thanh U ngang 1.5 (Rev CDTA) · 667×205 mm | Chưa ghi trên nguồn |
| TB-dccd5af580ee2c2e | Thanh U ngang 1.5 (Rev CDTA) · 667×40 mm | Chưa ghi trên nguồn |
| TB-6e74839d1dc62eae | Thanh U ngang 1.5 (Rev CDTA) · 719×370 mm | Chưa ghi trên nguồn |
| TB-d5caf273729f9522 | Thanh U ngang 1.5 (Rev CDTA) · 719×165 mm | Chưa ghi trên nguồn |
| TB-0f6222095da388b5 | Thanh U ngang 1.5 (Rev CDTA) · 919×40 mm | Chưa ghi trên nguồn |
| TB-93b1f61c66452a57 | Thanh U ngang 1.5 (Rev CDTA) · 667×80 mm | Chưa ghi trên nguồn |
| TB-8ec1988286a0f3a5 | Thanh U ngang 1.5 (Rev CDTA) · 20×40 mm | Chưa ghi trên nguồn |
| TB-360cfdd102827c3a | Thanh U ngang 1.5 (Rev CDTA) · 667×260 mm | Chưa ghi trên nguồn |
| TB-7681f8de5efe45f5 | Thanh U ngang 1.5 (Rev CDTA) · 719×40 mm | Chưa ghi trên nguồn |
| TB-ddb723ad073a318a | Thanh U ngang 1.5 (Rev CDTA) · 30×165 mm | Chưa ghi trên nguồn |
| TB-4fcb410cf8cd361b | Thanh U ngang 1.5 (Rev CDTA) · 919×552 mm | Chưa ghi trên nguồn |
| TB-56c348456def811f | Thanh U ngang 1.5 (Rev CDTA) · 919×697 mm | Chưa ghi trên nguồn |
| TB-b003255da8ed373b | Thanh U ngang 1.5 (Rev CDTA) · 919×130 mm | Chưa ghi trên nguồn |
| TB-77ff3efd9e0c7692 | Thanh đồng uốn Cu 20×5 mm | Chưa ghi trên nguồn |


## Kiểm tra triển khai

- 62 kiểm thử backend đạt (đối chiếu hãng/loại/mã, giữ tách mã CAD và mã tham khảo, tìm NDK-25VA theo dòng NDK, không tự chọn giá bộ phận).
- Vite production build đạt.
- Kiểm thử trình duyệt dùng dữ liệu xuất từ API: NDK 22 mã, SmartGen, LightStar, Phoenix, NCH8, NP2, NZ7 và RT36; thư viện desktop/mobile và bảng giá chung đạt; không có lỗi JavaScript.
- Backend được khởi động lại để áp dụng liên kết và tìm kiếm mới.
