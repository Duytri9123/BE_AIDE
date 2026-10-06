from build_tudien_library import *
def load(p):return json.loads(p.read_text(encoding='utf8'))
media=load(OUT/'embedded_media.json')
notes=[
'Phiếu biến dòng 3 pha kiểu tròn KBD-13: 50/5A và 75/5A, 2.5VA 3%; LT-KBD-13-MCT-50A và LT-KBD-13-MCT-75A; cần đối chiếu OCR với ảnh gốc.',
'Phiếu Sino: SC108N, SC68N, SC45N, SOL68E, SBE203b, SBE63b, SBE103b; định mức và số lượng theo từng dòng ảnh.',
'Phiếu LS: SHT ABN/S400–800AF AC220V; MC-12b AC220V; MT-32 11–13A; AN-10D3-10H AH6 1000A 65kA; MI KIT WIRE 2WAY; LSLV0015G100-4EONN.',
'Thiết bị đo ME41; biến dòng TI1000 1000/5A, 15VA, CL0.5, FI=1, DK80.',
'Danh sách viết tay đèn/cầu chì/biến dòng; chữ và mã không đủ rõ ở ảnh tổng quan, giữ cần đối chiếu ảnh gốc.',
'Logo TUAN ANH; không phải thiết bị.',
'GG/Delta: EG15-32X vỏ cầu chì; GW1S-3E20 công tắc xoay; GW1P-1EQM3Y/R/G đèn báo; GW1L-MF2E1OQM3G/R nút nhấn; SG15-2A ruột cầu chì; PMT-24V50W2BA bộ nguồn.',
'Phiếu Sino nhiều dòng MCCB SBE103b/SBE63b/SBE203b, RCBO SOL68E và MCB SC108N/SC68N. Có số lượng viết tay, cần đối chiếu bản gốc.',
'Sino: SC68N 1P20A, SC68N 3P20A, SC68N 3P32A, SC108N 3P50A, SBE203b 3P250A.',
'CHINT NCH8-20/20 contactor; 5 chiếc.',
'LS: LA63N 3P20A/16A/10A, LB63N 1P+N16A30mA, LA63H 3P32A; ABN103C 3P75A/50A; ABN53C 3P30A; LA63H 3P10A; LA63N 1P10A. Mã SP là mã nội bộ phiếu.',
'Mikro PFR120-415V relay bù 12 cấp 415V.',
'Hyundai HGN 3P5000A 100kA có điện; HGC100 contactor 3P100A; HGM125S-F 3P100A 26kA.',
'Biến dòng hạ thế TI500, 500/5A,15VA, CL1; mã đọc trên ảnh là 8EMI418, cần đối chiếu ký tự.',
'Tụ bù hạ thế DAEJIN 50kVAr; mã phiếu TDACP3.',
'LS: ABS204C 4P250A, LB63N 1P+N16A, LA63N 1P10A, LA63H 3P32A, ABN103C 3P100A, LA63H 2P25A, ABS103C 3P100A, shunt ABN50C ABH250C.',
'Schneider nhãn hộp LV429387; phiếu bán hàng kèm ảnh sản phẩm.',
'Schneider: LV516302 CVS160B125A3P; EZC630H3500N EZC3P500A; EZC250F3125 EZC3P125A.',
'Biến dòng TI1000 1000/5A, 15VA, CL0.5, FI=1, DK80; số lượng trên phiếu.',
'ATS VAT-66WN 4P600A; phiếu ghi kiểu Front, mã hàng nhỏ cần đối chiếu.',
'LS: MT32, LA63H/LA63N nhiều cực và định mức; ABN53C/ABN63C/ABN203C; MC40a/MC18b. Phiếu nhiều dòng cần đối chiếu từng định mức ở ảnh gốc.',
'ABB 1SDA066705R1 3P125AF80AT18kA cố định từ nhiệt A1B; 1SDA066699R1 3P125AF25AT18kA A1B.',
'CHINT NXM series MCCB, NXB-63 MCB; các dòng NXM-63S/125S/250S/630S. Cần đọc ảnh đầy đủ trước liên kết SKU.',
'LS SHT ABN400–800; LA63N 1P20A; LA63N 2P25A; MC18b220V; LB63N 1P+N16A; LA63N 1P16A/10A; LA63N 2P20A; LA63H 3P32A.',
'JUDI TECH JT350-T3-2R2G/4R0PB biến tần; số lượng 4.',
'ATS VAT-64WN 3P400A (B60040WN); bộ điều khiển HAT553KM; số lượng 2 mỗi loại.',
'MCCB Sino SBE203c/250 3P250A42kA; số lượng 2.',
'ABB đồng hồ kỹ thuật số M4M20 MODBUS; mã nhìn thấy 2CSG251141R4051, cần xác minh ký tự trên ảnh gốc trước sử dụng.',
'Sino SMC-12, SMC-18b; SBE63b, SBS53C, SBE203b; SC108N và SC68N nhiều định mức.',
'Công tơ 1 pha 5(80)A 220V CE38; TI500 500/5A15VA CL0.5 FI=1 DK50.',
'LS LA63N1P10A/16A/20A; EBN104C4P30A; LA63N3P32A; LA63H2P40A; LB63N1P+N25A/20A; LA63N2P25A; ABN63C/ABN203C/ABN103C/ABN204C; SHT ABN400–800.'
]
for m,n in zip(media,notes):m.update(visual_review='reviewed_contact_sheet',observed_text=n,status='logo' if n.startswith('Logo') else 'device_document_requires_full_line_transcription')
save(OUT/'embedded_media.json',media)
save(OUT/'review_queue.json',{'embedded_images':[{'id':m['id'],'path':m['path'],'reason':'Full-resolution line-by-line transcription not completed; partial observations preserved.'} for m in media if m['status']!='logo'],'policy':'Do not treat contact-sheet reading as verified full SKU transcription.'})
