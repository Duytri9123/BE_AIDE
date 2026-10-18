# Rà soát 18 CAD điều khiển và đo lường

Đã xác định hãng/dòng cho 13/18 CAD; còn 5 CAD chưa đủ bằng chứng hãng/mã. Đây là số trong nhóm 18 CAD, không phải số toàn thư viện. Giá không phải điều kiện xác nhận.

| CAD | Thiết bị | Hãng | Mã/dòng |
| --- | --- | --- | --- |
| TB-8c40e2d424325405 | Bộ điều khiển · màn hình và 6 phím (chưa rõ chức năng) |  |  |
| TB-2cc9ba3420f74b4e | Bộ điều khiển ATS OSEMCO ACD-III | OSEMCO | ACD-III |
| TB-cd1c538175f9a6ae | Bộ điều khiển ATS SmartGen · chưa rõ mã | SmartGen |  |
| TB-489e1696d1c01dd8 | Rơ le bảo vệ pha CHINT XJ3-G | CHINT | XJ3-G |
| TB-e178aa3c9dd67cc7 | Rơ le bảo vệ dòng rò Mikro DIN300 | Mikro | DIN300 |
| TB-df6642c0e15a7c33 | Rơ le bảo vệ pha Selec 600PSR | Selec | 600PSR |
| TB-6afd381f8090861a | Biến tần SUMO · nhãn CAD 1.5 kW | SUMO |  |
| TB-de4306f8b83b75df | Biến tần Schneider ATV320D11N4B | Schneider Electric | ATV320D11N4B |
| TB-c6b859d113fa6bca | Bản vẽ biến tần · mặt quạt, block BT7.5 |  |  |
| TB-0679d39feb15577a | Ổn áp ROBOT AP15 · 600 VA | ROBOT | AP15 |
| TB-7d563103819b0e05 | Ổn áp ROBOT AP15 · 350 VA | ROBOT | AP15 |
| TB-eeb533e15b1abd01 | Ampe kế kim gắn tủ |  |  |
| TB-f9ed176ec4ac1425 | Công tơ EMIC · nhãn kWh/kvarh | EMIC |  |
| TB-991b8c4a7bab4123 | Công tơ điện tử Elster A1700 (dòng ABB Vision) | Elster | A1700 |
| TB-2250a9171c9f2733 | Đồng hồ đo điện dạng kim |  |  |
| TB-177f377fb9b8a5a8 | Đồng hồ đa năng Selec MFM383 | Selec | MFM383 |
| TB-20ef8236d4d75c8b | Đồng hồ Selec · block VAF36 / MFM384 | Selec |  |
| TB-83c508f9a35bfbcf | Vôn kế kim gắn tủ |  |  |

## Sáu CAD đã tra cứu lại

Block gốc ghi A1700; đối chiếu datasheet Elster trên website Honeywell và tài liệu ABB Vision/Elster của ESB. Xác nhận dòng A1700, chưa xác nhận đời nhãn, mã đặt hàng, kiểu đấu hoặc kích thước lắp của bản CAD này.
Nguồn A1700: https://prod-edam.honeywell.com/content/dam/honeywell-edam/pmt/hps/products/sme/electricity/commercial-and-industrial-meters/a1700/A1700-31052012.pdf

- TB-8c40e2d424325405: ATL20/30 có 8 phím, mặt 144×144; không khớp hình đứng 6 phím. MicroLogic P cũng có 6 phím nhưng chưa có nhãn hoặc bố trí đầy đủ để nhận hãng. Không đủ căn cứ giữ ATS là chức năng đã xác nhận. Nguồn: https://catalogue.lovatoelectric.com/gl_en/ATL20A240/snp
- TB-c6b859d113fa6bca: BT7.5 chỉ là tên block; mặt quạt/tản nhiệt không có chữ. Không đủ căn cứ gán LS iG5A hoặc coi 7.5 là công suất đã xác nhận. Nguồn: https://sol.ls-electric.com/uploads/document/16411846892410/iG5A_User%2BManual%28Standard%29_Eng_210303.pdf
- TB-eeb533e15b1abd01: KDSI BE-96 có 96×96 và thang 500A nhưng có thể OEM, bản tham khảo DC60mV; CAD không xác nhận AC/DC hay CT/shunt. Không gán hãng theo kích thước. Nguồn: https://www.kdsimeter.com/New-Model-BE-96-DC60mV-500A-Analog-Panel-DC-High-Precision-Ammeter-pd508517068.html
- TB-83c508f9a35bfbcf: BE-96 500VAC là mẫu tham khảo 96×96. CAD chỉ có V và thang 500; chưa có logo/AC/DC. Không tự điền AC500V hay hãng EM. Nguồn: https://www.em.co.za/BE-96-500VAC
- TB-2250a9171c9f2733: Block nguồn có A/V, 400 và ký hiệu AC; ba hình gồm hai cấu hình đo khác nhau và mặt bên. Không có nhãn hãng/model, chưa xác nhận tỉ số CT hoặc kiểu đấu. Giữ loại ampe kế/vôn kế AC và thang 400 đã đọc được.
