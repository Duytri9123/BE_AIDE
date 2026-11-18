"""Apply documented follow-up research without turning candidates into confirmed SKUs."""
import hashlib
import html
import json
import os
import re
import shutil
import sqlite3
import sys
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
ROOT = BACKEND / 'data/CatalogTB'
FOLDER = ROOT / 'NguonCapNhat/20261118_a72a95b79f48'
REVIEW = BACKEND / 'app/data/accessory_revision_review_20261118.json'
RESEARCH = BACKEND / 'app/data/accessory_remaining25_research_20261118.json'
OUT = FOLDER / 'research_25'
DOC = {
    'trend': 'https://prod-edam.honeywell.com/content/dam/honeywell-edam/hbt/en-us/documents/manuals-and-guides/installation-guides/trends-110725/hon-ba-bms-en-tg201342-uk8pr0923k.pdf',
    'honeywell_io': 'https://prod-edam.honeywell.com/content/dam/honeywell-edam/hbt/en-us/documents/literature-and-specs/datasheets/IO-Modules-Product-Datasheet-31-00588-03.pdf?download=false',
    'schneider_meter': 'https://iportal.se.com/Contents/docs/ELECTRICAL%20NETWORK%20MANAGEMENT_CATALOG.PDF',
    'dh_any': 'https://www.timer-switch.com/twin-time-dh48s-s.html',
    'dh_lorentzzi': 'https://lorentzzi.com/products/timer-switch-and-counter/time-delay-relay/dh48s-s-programmable-repeating-cycle-time-delay-relay/',
    'selector_kn': 'https://flippingbook.krausnaimer.com/Control_Load_Switch_Catalogue/',
    'selector_sigma': 'https://sigmaelektrik.com/img/Order_Catalogue_02_06_2025_web.pdf',
    'lamp': 'https://sieuthi.rangdong.com.vn/dui-den-chong-tham-nuoc-e27-ip65',
    'fire_dongan': 'https://www.donganfirefighting.com/product/automatic-fire-extinguisher/6kg-automatic-hanging-abc-dry-powder-fire-extinguisher.html',
    'fire_xingli': 'https://www.xlfireextinguisher.com/fire-extinguisher-cylinder/automatic-fire-extinguisher-cylinder/6kg-auto-fire-extinguisher-cylinder.html',
    'nkg_weilan': 'https://wzazure.en.made-in-china.com/product/TOytALrEJIkb/China-Nkg-5-Dual-Circuit-Time-Controller-Microcomputer-Time-Controlled-Switch-Street-Lamp-Controller.html',
    'nkg_senyi': 'https://senyiele.en.made-in-china.com/product-group/GbzAoqclYDkf/NKG5-1.html',
    'clipsal': 'https://www.se.com/th/en/product/E426UEST2%252FT/s-classic-16a-250v-3pin-duplex-universal-socket-outlet/',
    'ilec': 'https://ilec.vn/wp-content/uploads/2025/08/rct-catalogue-ilec.pdf',
    'ilec_mirror': 'https://www.ple.vn/images/virtuemart/datasheet-2/ilec-rct-cate.pdf',
    'cml_listing': 'https://vanvh.com/upload/files/BG2021morele1.pdf',
    'cml_misnamed': 'https://www.scribd.com/document/771968153/rct-catalogue-CML',
    'gtpro': 'https://dientugtpro.com/bo-dieu-khien-auto-star-v1-1/',
    'gtpro_diagram': 'https://www.scribd.com/document/462297413/s%C6%A1-%C4%91%E1%BB%93-%C4%91%E1%BA%A5u-n%E1%BB%91i-auto-start',
    'deree': 'https://www.deree.com.tw/de-80.html',
    'dixsen': 'https://www.mph-elec.co.il/GenericHendler/GetFile.ashx?DG=3635',
    'transformer_zx': 'https://www.zx-ele.com/power-supply-transformer/',
    'transformer_cnc': 'https://www.cncele.com/uploads/JBK-%E6%A0%B7%E6%9C%AC-23.11.181.pdf',
    'terminal_kasuga': 'https://www.otax-en.com/wp-content/uploads/2026/02/20260213-KASUGA-Terminal-Block-aggregated-brochure-R01.pdf',
    'terminal_idec': 'https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/7466/EP1147-0Terminalblock_070308.pdf',
    'phase_anly': 'https://anly.com.tw/downloadfile.php?file=APR_WA.pdf',
    'phase_multispan': 'https://multispanindia.com/varient.php/voltage-protection-relay-3-knob',
    'sunon': 'https://www.sunon.com.cn/MANAGE/Docs/PRODUCT/313/359/SUNON%20AC%20Fan_%28257-C%29.pdf',
    'fan_wolun': 'https://wolunele.en.made-in-china.com/product/SKgEVrflgHUj/China-200-200-61-Mini-AC-Axial-Cooling-Fan-Exhaust-Fan.html',
}

# The text below describes identity evidence, not approved electrical ratings.
CASES = {
4: dict(queries=['terminal block 79 50.5 10', 'Kasuga IDEC terminal block dimensions'],
    docs=['terminal_kasuga','terminal_idec'],
    note='Dãy 10 vị trí vít, bước hình học 6 mm; bao CAD 79 × 50,5. Catalogue Kasuga/IDEC có nhiều dãy cầu đấu nhưng chưa khớp đồng thời đế kẹp ba vít, bước và bao hình. Không có logo hay mã thân để chốt hãng.',
    missing=['Ảnh hoặc nhãn hãng trên thân cầu đấu','Mã từng phiến và đế chặn']),
6: dict(queries=['8AO Trend module', '8AO 16 DDC module Honeywell'], docs=['trend','honeywell_io'],
    brand='Trend', model='IQ4/IO/8AO · họ ứng viên', display='Mô-đun Trend IQ4/IO/8AO · ứng viên từ CAD',
    note='Nhãn 8AO, cọc 1–16, bốn biểu tượng nguồn/watchdog/I-O bus/service và bao CAD khoảng 70,22 × 116 khớp họ nhỏ IQ4/IO trong tài liệu Trend TG201342 trang 1, 10. Nhận diện tương đối IQ4/IO/8AO; chưa có nhãn hãng/mã đầy đủ trên CAD, chưa chốt phiên bản, phụ kiện hoặc cấu hình điện.',
    missing=['Tem Trend và mã đầy đủ của mô-đun','Phiên bản và điều kiện cấp nguồn']),
7: dict(queries=['96 voltmeter 500 front Schneider PowerLogic', 'Morele V-96x96'],docs=['schneider_meter'],
    note='Vôn kế CAD 96 × 96, nhãn V/0/500. Nhiều hãng có đồng hồ cùng kích thước và thang đo. Chú thích Schneider thuộc vùng đồng hồ khác; chưa có logo/mã gắn trực tiếp với mẫu này. Không gán 16075 chỉ từ kích thước.',
    missing=['Logo hoặc tem mặt đồng hồ','Mã và kiểu đo trực tiếp/qua biến áp']),
10: dict(queries=['96 ammeter front 500 Schneider PowerLogic', 'Morele AC-96x96'],docs=['schneider_meter'],
    note='Ampe kế CAD 96 × 96, nhãn A/0/500. Tài liệu PowerLogic và các dòng đồng hồ 96 mm không đủ phân biệt mẫu CAD không logo. Không suy 500/5 A, loại thang hoặc gán hãng theo chữ Schneider ở vùng lân cận.',
    missing=['Logo hoặc tem mặt đồng hồ','Mã cơ cấu đo, thang và tỷ số CT']),
22: dict(queries=['DH48S-S manufacturer', 'DH48S-S site:timer-switch.com', 'DH48S-S site:lorentzzi.com'],docs=['dh_any','dh_lorentzzi'],
    note='Đã xác minh DH48S-S là tên họ timer lặp hai khoảng T1/T2 qua tài liệu chính chủ Any Electronics và Lorentzzi. Hai nhà sản xuất cùng công bố mã này, CAD không có logo. Chốt tên họ DH48S-S, giữ hãng chưa xác định; không suy nguồn nuôi hay số tiếp điểm.',
    model='DH48S-S · họ đa hãng', missing=['Tem hãng trên mặt hoặc vỏ','Hậu tố 1Z/2Z và điện áp']),
43: dict(queries=['voltmeter selector 64 78', 'CA10 64 78 voltmeter selector manufacturer'],docs=['selector_kn','selector_sigma'],
    note='Có 7 vị trí 0/RS/ST/TR/RN/SN/TN và hai mặt CAD; bao mặt 64 × 78. Kraus & Naimer có mặt S1 gần kích thước, Sigma có cùng nhóm ký hiệu nhưng kích thước khác. Các đặc trưng chưa xác định duy nhất hãng/mã hoặc sơ đồ cam, nên giữ chưa xác định.',
    missing=['Logo và mã thân chuyển mạch','Sơ đồ tiếp điểm/cam và kiểu gá']),
46: dict(queries=['đui đèn 60 63 Vinakip', 'đui đèn E27 site:rangdong.com.vn'],docs=['lamp'],
    note='CAD thể hiện đế nghiêng, hai vị trí gá cách nhau 50 theo tọa độ nguồn, không có ký hiệu ren hoặc logo. Tài liệu đui E27 chỉ là mẫu đối chiếu, chưa đủ xác nhận chuẩn đui, hãng hay mã; không gán Rạng Đông/Vinakip từ hình dáng.',
    missing=['Ký hiệu loại đui/ren và tem hãng','Ảnh cạnh hoặc nhãn mã']),
49: dict(queries=['6kg 270 automatic extinguisher manufacturer', '6kg auto fire extinguisher cylinder'],docs=['fire_dongan','fire_xingli'],
    note='Đối chiếu bình treo tự động Dongan và Xingli đều có cỡ 6 kg/đường kính 270; vì có nhiều nguồn cùng cỡ, CAD chỉ ghi 6 KG không đủ chốt hãng/model. Giữ đúng loại bình treo có đầu phun, không xác nhận chất chữa cháy, nhiệt kích hoạt hay chứng nhận.',
    missing=['Nhãn nhà sản xuất và model bình','Nhãn đầu phun và hồ sơ sản phẩm']),
52: dict(queries=['NKG-5 manufacturer timer', 'NKG-5 site:chintglobal.com', 'NKG5 NAKO'],docs=['nkg_weilan','nkg_senyi'],
    note='NKG-5 là mã được nhiều nhà sản xuất/OEM công bố (Weilan, Senyi); CAD 36 × 82 chỉ có NKG-5/AUTO/LOCK. Chưa tìm được căn cứ chính chủ CHINT gắn với mẫu nguồn. Giữ mã NKG-5, hãng chưa xác định; không suy số kênh hay điện áp.',
    missing=['Tem hãng và mã phiên bản','Sơ đồ chân đúng mẫu']),
54: dict(queries=['E426UEST2/T site:se.com', 'Clipsal 72 114 universal socket'],docs=['clipsal'],
    brand='Clipsal', model='Ổ cắm đôi · ứng viên họ E426UEST2/T', display='Ổ cắm đôi Clipsal · ứng viên họ S-Classic',
    note='Đối chiếu tọa độ DWG: mẫu A$Cf470d8ba nằm trực tiếp phía trên chữ CLIPSAL, tách khỏi cột CHENG LI. Trang chính chủ Schneider xác nhận họ ổ cắm đôi universal E426UEST2/T; mặt nguồn phù hợp dạng này nhưng chưa đủ chốt mã đặt hàng hoặc dòng định mức. Lưu hãng/họ ứng viên, không xác nhận biến thể.',
    missing=['Tem mặt sau và mã đặt hàng','Dữ liệu cơ khí đúng biến thể']),
55: dict(queries=['CHENG LI ổ cắm đôi model', 'CHENG LI công tắc ổ cắm Thành Lợi'],docs=[],
    brand='CHENG LI', model='Ổ cắm đôi · nhãn CHENG LI nguồn', display='Ổ cắm đôi CHENG LI · nhãn nguồn',
    note='Đối chiếu tọa độ và hai cột trong DWG: A$Cb343c03b nằm phía trên chữ CHENG LI, còn mẫu bên trái thuộc CLIPSAL. Xác định nhãn hãng ứng viên từ chính nguồn CAD; chưa có catalogue chính chủ khớp mặt 76 × 118 hoặc mã sản phẩm. Không gán pháp nhân hay mã Clipsal cho mẫu này.',
    missing=['Tem CHENG LI và mã trên thân','Catalogue gốc đúng mẫu']),
63: dict(queries=['BGVFG Block reactor', 'cuộn kháng Haveco 7.5kW'],docs=[],
    note='Tên BGVFG không phải mã đặt hàng đủ nhận diện. Hình giống cụm lõi/cuộn kháng; chú thích Cuộn kháng/Have co/7.5kW nằm ở các vị trí khác nhau, không có dây dẫn nhãn hoặc logo nối riêng mẫu này. Giữ chưa xác định hãng/model; không chuyển 7,5 kW thành công suất đã chọn.',
    missing=['Tem cuộn kháng và mã đặt hàng','Tài liệu hoặc chú thích gốc xác định quan hệ nhãn–hình']),
75: dict(queries=['Auto Start V1.0 GTpro', 'site:dientugtpro.com V1.0', 'sơ đồ đấu nối auto start GTPRO'],docs=['gtpro','gtpro_diagram'],
    brand='GTpro', model='Auto Start V1.0 · ứng viên GTpro', display='Bo điều khiển GTpro Auto Start V1.0 · ứng viên',
    note='Trang chính chủ GTpro nêu V1.1 phát triển từ Auto Start V1.0. Sơ đồ mang nhãn GTPRO/AUTO START V1.0 đối chiếu đủ 11 cọc: 1 B+, 2 B−, 3 Heater, 4 Crank, 5 Fuel, 6 Stop, 7 Remote, 8 Water, 9 Oil, 10 Gens(N), 11 Gens(L), phù hợp CAD. Nhận diện tương đối GTpro V1.0, không đổi thành V1.1 hoặc chốt điện áp/firmware.',
    missing=['Tem GTpro trên bo gốc','Phiên bản phần cứng/firmware và tài liệu đúng bo']),
76: dict(queries=['analog panel meter 81 81', 'DE-80 analog meter manufacturer'],docs=['deree','dixsen'],
    model='DE-80 · họ hình học ứng viên đa hãng',
    note='Bao CAD 81 × 81, vòng tròn Ø65 và bốn lỗ gá gần góc phù hợp họ DE-80. DER EE và catalogue Dixsen đều công bố DE-80; không thể chọn một hãng từ cùng hình học. Nhiều nét chồng ở phần dưới nên vẫn giữ mặt nguồn tham khảo, chưa coi là mặt lắp đã xác minh.',
    missing=['Logo hoặc tem hãng','Phân biệt mặt thân với phần hình chồng, mã và thang đo']),
113: dict(queries=['1000VA control transformer 176 170', 'JBK3-1000 dimensions manufacturer'],docs=['transformer_zx','transformer_cnc'],
    note='Mặt trước biến áp nguồn 1000VA không có tem. Đã đối chiếu JBK3/JBK5 của Zhengxi và CNC: chưa khớp đồng thời bao CAD khoảng 176,04 × 170,35, hai dãy cọc và gá. Không gán Omron từ bộ nguồn S8FS ở ô gần bên, không coi công suất trong tên file là thông số đã duyệt.',
    missing=['Tem hãng và mã biến áp','Điện áp từng cuộn và bản vẽ gá đúng mã']),
114: dict(queries=['1000VA control transformer side dimensions', 'JBK3-1000 176 transformer'],docs=['transformer_zx','transformer_cnc'],
    note='Mặt bên nguồn side-1000va không có tem; đối chiếu họ JBK phổ biến chưa xác định duy nhất hãng/mã. Chỉ cùng hậu tố 1000va không đủ ghép chắc chắn với front-1000va, vì chưa có mốc và dữ liệu đồng nhất giữa hai hình.',
    missing=['Tem mã hoặc liên kết mặt gốc','Bản vẽ đúng mã cho mặt trước và mặt bên']),
115: dict(queries=['500VA control transformer 147 155', 'JBK5-500 dimensions transformer'],docs=['transformer_zx','transformer_cnc'],
    note='Mặt trước nguồn 500VA không có logo hoặc cọc được ghi điện áp. Tài liệu JBK/BK không đủ khớp riêng hình 147,54 × 155,44; giữ loại biến áp tham khảo, chưa xác định hãng/model và không gán nhãn Omron của bộ nguồn ở gần.',
    missing=['Tem hãng và mã biến áp','Điện áp cuộn dây, công suất và gá đúng mã']),
129: dict(queries=['terminal block 74.5 50.5', '20A 5 poles terminal block IDEC Kasuga'],docs=['terminal_kasuga','terminal_idec'],
    note='CAD có 5 cặp vít làm việc và hai đế kẹp, nhãn 20A*5; bao 74,5 × 50,5, bước vít theo CAD khoảng 11,1. Đối chiếu Kasuga/IDEC chưa có mã khớp đầy đủ đế, bước và kích thước; không nâng nhãn 20A thành định mức đã xác minh hoặc gán hãng.',
    missing=['Logo và mã phiến cầu đấu/đế chặn','Catalogue đúng tổ hợp 5 vị trí']),
150: dict(queries=['phase protector 17.5 90 three LED', 'ANLY APR-3 dimensions', 'Multispan VPR-17 dimensions'],docs=['phase_anly','phase_multispan'],
    note='Mặt ghi PHASE PROTECTOR, bao 17,5 × 90 và ba vòng đèn; không phải cầu chì. ANLY APR-3 là kiểu đế/chân và bao khác; Multispan VPR-17 cùng cỡ nhưng có núm chỉnh, không giống CAD. Đã loại các gán hãng này, chưa tìm được model duy nhất.',
    missing=['Tem hãng/model và sơ đồ cọc','Mặt cạnh hoặc ảnh đủ đọc đèn/núm']),
152: dict(queries=['200 200 61 AC axial fan manufacturer', 'SUNON 200 200 60 fan datasheet'],docs=['sunon','fan_wolun'],
    model='20060/20061 · cỡ hình học tham khảo',
    note='Nguồn có mặt cánh 200 × 200 và mặt bên dày 61. Nhà sản xuất Wolun có họ 20060 cùng cỡ; catalogue SUNON và chú thích Morele/Sunon gần đó chưa đủ buộc một nhãn vào mẫu này. Giữ chưa xác định hãng, mã 20060/20061 chỉ là gợi ý tìm theo cỡ; không xác nhận nguồn AC, lưu lượng hoặc vòng bi.',
    missing=['Tem trên tâm quạt và mã đầy đủ','Điện áp, dây/cọc và bản vẽ lỗ gá đúng mã']),
}

for n, label in [(64,'250/5A'),(65,'400/5A · chú thích 400/600'),(66,'500/5A'),
                 (67,'800/5A · chú thích 800/2000'),(68,'3200/5A')]:
    CASES[n] = dict(queries=['CML biến dòng catalogue', 'CML RCT current transformer manufacturer', 'RCT catalogue CML ILEC'],
        docs=['cml_listing','ilec_mirror'],brand='CML',model='CML · nhãn '+label,
        display='Biến dòng nhãn CML · '+label,
        note='Đọc trực tiếp nhãn CML '+label+' trên CAD và phân biệt với hàng EMIC phía trên. CML được lưu như nhãn/ứng viên thương hiệu, chưa xác định pháp nhân nhà sản xuất. Catalogue mang tiêu đề CML trên Scribd thực tế là iLEC: đã loại làm bằng chứng hãng, không đổi mẫu thành iLEC/EMIC hoặc tự chọn mã RCT. Tỷ số trong nhãn nguồn chưa phải cấu hình điện được duyệt.',
        missing=['Catalogue hoặc tem gốc xác định nhà sản xuất CML','Mã thân, tỷ số và thông số đúng biến thể'])


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')


def apply_followup(data, research):
    by_n = {r['n']:r for r in data['items']}
    for item in research['items']:
        row = by_n[item['n']]
        for field in ('brand','model','display'):
            if field in item['update']:
                row[field] = item['update'][field]
        row['brand_candidate_only'] = bool(row['brand'])
        row['note'] = item['note']
        row['documents'] = item['document_urls']
        row['mode'] = 'publish_reference' if item['reference_admitted'] else 'identity_partial'
        row['research_followup'] = {k:item[k] for k in ('conclusion','missing_evidence','checked_queries','document_urls')}
    return data


def write_report(research):
    esc=html.escape
    current={r['n']:r for r in read(REVIEW)['items']}
    report=read(FOLDER/'review_157_report.json')
    assert report['summary']['newly_visible_profiles']==133
    sections=['<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Đối chiếu hãng/model 25 hồ sơ</title>',
        '<style>body{font:15px "Segoe UI",Arial;background:#eef3f6;color:#20384a;margin:0}main{max-width:1200px;margin:auto;padding:28px}h1{font-size:28px}h2{font-size:20px}.summary,article{background:white;padding:22px;border-radius:12px;margin:18px 0}p,li{line-height:1.65}.stats{display:flex;gap:12px;flex-wrap:wrap}.stats b{padding:12px 16px;background:#e5f2ee;border-radius:8px}.status{color:#0b6a5d;font-weight:600}.pending .status{color:#936012}.views{display:flex;gap:12px;flex-wrap:wrap}figure{margin:0;width:250px}img{width:250px;height:220px;object-fit:contain;background:#20242b;border-radius:8px}figcaption{font-size:12px;padding:8px}a{color:#087c70;overflow-wrap:anywhere}details{padding:10px 0}.controls{position:sticky;top:0;background:#eef3f6;padding:12px 0;display:flex;gap:10px;flex-wrap:wrap}input,select{font:inherit;padding:10px;border:1px solid #bdcdd7;border-radius:7px}input{flex:1;min-width:180px}article[hidden]{display:none}@media(max-width:600px){main{padding:14px}h1{font-size:23px}article,.summary{padding:16px}figure,img{max-width:100%}}</style><main>',
        '<h1>Đối chiếu hãng/model cho 25 hồ sơ còn lại</h1><p>Ngày 18/11/2026 · DWG nguồn được giữ nguyên</p>',
        '<section class="summary"><div class="stats"><b>25 hồ sơ đã tra cứu</b><b>9 hãng/họ ứng viên</b><b>16 chưa rõ hãng/model</b></div><p>Đã bổ sung 9 hồ sơ có căn cứ nhận diện tương đối vào danh mục tham khảo. Chưa có mã đặt hàng hoặc nhà sản xuất thực tế nào được xác nhận hoàn toàn trong lượt này. Toàn đợt nhập hiện có 185/209 hồ sơ trong danh mục thiết bị tham khảo; cả 157 hồ sơ rà soát vẫn có trong mục CAD nguồn đã rà soát.</p><p>Phân biệt rõ nhãn thương mại trong bản vẽ, hãng ứng viên, họ model và cấu hình mua hàng. Không tự gán thông số điện, giá, hướng nhìn mới hoặc thay đổi tỷ lệ CAD.</p><p><a href="../bao_cao_xac_minh_157.html">Xem toàn bộ 157 hồ sơ</a> · <a href="research_25_report.json">Dữ liệu đối chiếu và danh sách còn thiếu</a></p></section>',
        '<div class="controls"><input id="query" placeholder="Tìm tên, mã hoặc hãng" aria-label="Tìm hồ sơ"><select id="status" aria-label="Lọc kết quả"><option value="all">Tất cả 25 hồ sơ</option><option value="candidate">Có hãng/họ ứng viên</option><option value="pending">Chưa rõ hãng/model</option></select><span id="count"></span></div>']
    for item in research['items']:
        row=current[item['n']];status='candidate' if item['reference_admitted'] else 'pending'
        sections.append(f'<article class="{status}" data-status="{status}"><h2>{item["n"]}. {esc(row["display"])}</h2><p class="status">'+('Hãng/họ ứng viên · chưa xác nhận mã đặt hàng' if status=='candidate' else 'Chưa xác định hãng/model duy nhất')+f'</p><p>{esc(item["note"])}</p><div class="views">')
        for view in item['views']:
            preview=ROOT/Path(view['path']).with_name('xem_truoc.svg')
            relative=Path(os.path.relpath(preview,OUT)).as_posix()
            sections.append(f'<figure><img loading="lazy" src="{esc(relative,quote=True)}" alt="{esc(row["display"],quote=True)}"><figcaption>{esc(view["face"])}</figcaption></figure>')
        sections.append('</div><h3>Căn cứ còn thiếu</h3><ul>'+''.join(f'<li>{esc(v)}</li>' for v in item['missing_evidence'])+'</ul><details><summary>Tài liệu và truy vấn đã đối chiếu</summary>')
        for url in item['document_urls']:
            sections.append(f'<p><a target="_blank" rel="noopener noreferrer" href="{esc(url,quote=True)}">{esc(url)}</a></p>')
        if not item['document_urls']:sections.append('<p>Chưa tìm được tài liệu chính chủ đủ gắn với mẫu này; đã kiểm tra nhãn và vị trí trong DWG.</p>')
        sections.append('<ul>'+''.join(f'<li>{esc(q)}</li>' for q in item['checked_queries'])+'</ul></details></article>')
    sections.append('''<script>const q=document.querySelector('#query'),s=document.querySelector('#status'),cards=[...document.querySelectorAll('article')];const norm=t=>t.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').replace(/đ/g,'d').toLowerCase();function filter(){let n=0;for(const c of cards){c.hidden=(s.value!=='all'&&c.dataset.status!==s.value)||!norm(c.textContent).includes(norm(q.value));if(!c.hidden)n++}document.querySelector('#count').textContent=n+' / 25 hồ sơ'}q.oninput=filter;s.onchange=filter;filter();</script></main></html>''')
    (OUT/'bao_cao_doi_chieu_25.html').write_text('\n'.join(sections),encoding='utf8')
    original=FOLDER/'bao_cao_cap_nhat.html'
    text=original.read_text(encoding='utf8')
    text=re.sub(r'(<section id="followup-157".*?</section>)',
        '<section id="followup-157" class="summary"><h2>Kết quả cập nhật sau đối chiếu 25 hồ sơ</h2><p>Hiện có 185/209 hồ sơ trong danh mục tham khảo. Đã bổ sung 9 hãng/họ ứng viên, còn 16 hồ sơ chưa đủ căn cứ xác định hãng/model. Nội dung bên dưới lưu kết quả nhập ban đầu.</p><a href="research_25/bao_cao_doi_chieu_25.html">Báo cáo mới nhất cho 25 hồ sơ</a> · <a href="bao_cao_xac_minh_157.html">Toàn bộ 157 hồ sơ rà soát</a></section>',text,count=1,flags=re.S)
    original.write_text(text,encoding='utf8')
    readme=FOLDER/'README.md';text=readme.read_text(encoding='utf8')
    text=text.replace('176/209','185/209').replace('52 hồ sơ đợt đầu và 124 hồ sơ được bổ sung sau rà soát','52 hồ sơ đợt đầu và 133 hồ sơ được bổ sung sau rà soát/đối chiếu')
    text=text.replace('25 hồ sơ chưa đủ căn cứ chốt hãng/model','16 hồ sơ chưa đủ căn cứ chốt hãng/model')
    marker='## Đối chiếu tiếp 25 hồ sơ'
    if marker not in text:
        text+='\n'+marker+'\n\nĐã tìm và đối chiếu tài liệu cho cả 25 hồ sơ. Bổ sung 9 hãng/họ ứng viên (Trend, Clipsal, CHENG LI, 5 nhãn CML, GTpro); 16 hồ sơ chưa xác định được hãng/model duy nhất. Chưa xác nhận mã đặt hàng đầy đủ hoặc cấu hình điện trong lượt này.\n\n[**Báo cáo chi tiết và hình của 25 hồ sơ**](research_25/bao_cao_doi_chieu_25.html)\n'
    readme.write_text(text,encoding='utf8')
    print(json.dumps({'report':str(OUT/'bao_cao_doi_chieu_25.html'),'profiles':25,'views':sum(len(i['views']) for i in research['items'])}))


def main():
    frozen = read(FOLDER / 'remaining25_initial.json')
    assert len(frozen) == len(CASES) == 25
    assert {r['n'] for r in frozen} == set(CASES)
    OUT.mkdir(parents=True, exist_ok=True)
    backup = BACKEND / 'tmp/runtime/remaining25-research/before_followup'
    backup.mkdir(parents=True, exist_ok=True)
    for path in [REVIEW, BACKEND/'app/data/library_manufacturer_evidence.json',
                 BACKEND/'app/data/catalogtb_published_information.json',
                 *[ROOT/r['profile'] for r in frozen]]:
        relative = path.relative_to(BACKEND)
        target = backup / relative
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True);shutil.copy2(path,target)
    if not (backup/'equipment_catalog.sqlite').exists():
        with sqlite3.connect(ROOT/'_agent_index/equipment_catalog.sqlite') as db:
            with sqlite3.connect(backup/'equipment_catalog.sqlite') as destination:db.backup(destination)
    items=[]
    for row in frozen:
        case=CASES[row['n']]
        items.append({'n':row['n'],'profile':row['profile'],'source_name':row['source_name'],
            'views':row['views'],'checked_queries':case['queries'],
            'document_urls':[DOC[k] for k in case['docs']],
            'reference_admitted':bool(case.get('brand')),
            'conclusion':'candidate_brand_or_family' if case.get('brand') else 'identity_unresolved',
            'manufacturer_confirmed':False,'exact_ordering_code_verified':False,
            'electrical_configuration_verified':False,
            'note':case['note'],'missing_evidence':case['missing'],
            'update':{k:case[k] for k in ('brand','model','display') if k in case}})
    research={'reviewed_on':'2026-11-18','scope':'25 unresolved profiles after the individual 157-profile review',
        'source_sha256':read(REVIEW)['source_sha256'],
        'summary':{'researched':25,'additional_reference_candidates':sum(i['reference_admitted'] for i in items),
            'remaining_identity_unresolved':sum(not i['reference_admitted'] for i in items),
            'new_exact_ordering_codes_verified':0,'new_manufacturers_confirmed':0,
            'geometry_modified':False},'documents':DOC,'items':items}
    write(RESEARCH,research)
    write(OUT/'research_25_report.json',research)
    write(REVIEW,apply_followup(read(REVIEW),research))
    for name in ('trend_iq4_io.pdf','ilec_rct.pdf','dh48ss_any.pdf','manifest.json'):
        source=BACKEND/'tmp/pdfs/remaining25'/name
        if source.is_file():shutil.copy2(source,OUT/name)
    context=BACKEND/'tmp/runtime/remaining25-research/context-sockets.png'
    if context.is_file():shutil.copy2(context,OUT/'source_socket_context.png')
    print(json.dumps(research['summary'],ensure_ascii=False))


if __name__=='__main__':
    if '--report-only' in sys.argv:write_report(read(RESEARCH))
    else:main()
