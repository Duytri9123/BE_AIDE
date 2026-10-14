"""Record the scope of this web/metadata pass; unresolved identification remains explicit."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def record(note, urls=(), status='reviewed_metadata_and_family_sources'):
    return {'status':status,'checked_date':'2026-10-14',
        'scope':'Đã rà danh sách từng CAD, metadata, kết quả chữ DXF và giá công bố; tài liệu web đối chiếu theo dòng/nhóm. Không phải xác nhận kỹ thuật hoặc đọc bằng mắt mọi mặt vẽ.',
        'note':note,'sources':[{'title':title,'url':url} for title,url in urls]}


def update():
    path=ROOT/'docs/library-folder-web-sources.json'
    reviews=json.loads(path.read_text(encoding='utf8'))
    reviews.update({
        'Biến tần':record('Rà CAD FR-S500. Tài liệu hãng xác nhận dòng biến tần cũ; nhãn hãng trong hồ sơ vẫn là ứng viên, thiếu mã đầy đủ, kW và điện áp. Không lấy giá FR-D/FR-E hiện hành thay FR-S500.',[
            ('Mitsubishi — manual FR-S500','https://dl.mitsubishielectric.com/dl/fa/document/manual/inv/ib0600027/ib0600027c.pdf')]),
        'Chint':record('Rà 23 CAD. NCH8-20/25 là CAD dùng chung hai dòng, cần chọn dòng/tiếp điểm/điện áp cuộn hút. NP2 là họ nút nhấn/đèn/công tắc xoay, không áp giá nút nhấn NP2-EA cho đèn hay selector. Transformer thiếu mã/VA/điện áp. 13 CAD từ @CHINT vẫn thiếu xác nhận thiết bị; NXB/NXM/NM1 không coi tương đương nhau.',[
            ('CHINT NCH8 — tài liệu và CAD dùng chung','https://www.chintglobal.com/mx/es/products/low-voltage/iec/industrial-control/nch8.html'),
            ('CHINT NP2 — cấu trúc mã theo chức năng','https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/industrial-control/push-button/np2/catalog/NP2-Pushbuttons-catalog.pdf'),
            ('CHINT Industrial Control','https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/industrial-control/-cluster-/Industrial%20Control-Low%20Voltage-Master%20Catalog.pdf')]),
        'Chống sét':record('Rà 5 CAD: 3 chưa rõ hãng, 2 có nhãn Suntree nhưng chưa có mã. Cần Uc, loại AC/DC, Type 1/2, Iimp/In/Imax và số cực. Không gán SUP2-PV hoặc SPD hãng khác chỉ từ số mô-đun.',[
            ('Suntree — catalogue DC SPD','https://www.chinasuntree.com/upload/1c/pdf/DC-SPD-T1-T2.pdf')]),
        'Cuộn kháng':record('Rà CAD cuộn kháng ba pha. Chưa có hãng/mã, kvar, điện áp, Hz và hệ số p%. Một kích thước chung có thể dùng cho nhiều mức kvar; không áp mã Schneider từ hình dạng.',[
            ('Schneider — lựa chọn tụ/kháng','https://www.se.com/hk/en/download/document/26679713/'),
            ('Schneider — CAD chung cho nhiều mức kvar','https://www.se.com/ng/en/faqs/FA401137/')]),
        'Cầu đấu':record('Rà 37 CAD về nhóm, tên và bản vẽ. Theo yêu cầu người dùng, không bắt buộc tìm đúng mã/giá cầu đấu. Giữ hãng chưa rõ/ứng viên, không suy hãng chỉ từ CTS/UK/CD/TB.',[], 'reviewed_optional_price_scope'),
        'DenBaoNutNhanCauChiContactor':record('Rà 20 CAD. Giữ đúng chức năng đèn, nút nhấn, selector, cụm cầu chì và khởi động từ. IDEC có nhãn hãng nhưng SW0.1 không phải mã đặt hàng; các đèn chưa rõ mã cần màu, điện áp và tiếp điểm. Không đổi tên chung thành mã NP2/ND16 tùy ý.',[
            ('CHINT NP2 — các chức năng và mã','https://www.chintglobal.com/sa/en/products/low-voltage/iec/industrial-control/np2.html?section=Catalog'),
            ('IDEC — công tắc và đèn báo','https://www.idec.com/en-us/switches-indicator-lights/switches-pushbuttons/pushbuttons-pilot-lights')]),
        'LS':record('Rà 123 CAD, giữ riêng mã khung, số cực và loại. MC-40 không tự đổi MC-40a; ABN/ABH/ABS, TD/TS và EBS khác chức năng/dòng. BKN 4P có giá BKN 1P/2P/3P nhưng thiếu 4P trong dữ liệu, đã sửa chẩn đoán. 65 CAD thư viện nguồn chưa được tự nâng thành nhãn hãng/mã đã xác nhận.',[
            ('LS — công cụ tìm dòng sản phẩm','https://lens.ls-electric.com/'),
            ('LS Metasol MCCB/ELCB','https://www.ls-electric.com/upload/customer/download/0f7505a1-9187-42e2-bc87-d6f557990b24/Metasol%20MCCB_E_1907%280%29.pdf'),
            ('LS — Metasol contactor, khác biệt dòng cũ/mới','https://www.ls-electric.com/upload/customer/download/4d8b99a1-c93d-4cd3-807b-1382f0c39384/Metasol_MS_E_180903.pdf')]),
        'Mitsubishi':record('Rà 38 CAD. 5 CAD 4P NF125-CV/NF250-CV/NF400-CW/NF630-CW/NF800-CEW hiện thiếu giá đúng 4P, không lấy 2P/3P; đã sửa thông báo để thể hiện nguyên nhân này. NF30-CS/NF63-CW và NF-SDW DC còn thiếu nguồn giá đúng mã; không thay bằng dòng CV/SV/SEW mới. Trang CAD hãng là nguồn đối chiếu, không phải chứng nhận thông số của CAD đang có.',[
            ('Mitsubishi — CAD theo mã và số cực','https://www.mitsubishielectric.com/fa/download/cad/search.page?category1=102&kisyu=%2Flvcb&mode=cad'),
            ('Mitsubishi — catalogue MCCB','https://dl.mitsubishielectric.com/dl/fa/document/catalog/lvcb/yn-c-0720/y0720c1609.pdf')]),
        'Nguồn và biến áp':record('Rà 4 CAD. Nhãn TR/24VAC/24VDC không đủ xác định hãng và mã. Nguồn DC không phải biến áp AC; cần công suất, đầu vào/đầu ra và kiểu lắp. Không áp mã chỉ từ nhãn điện áp.',[
            ('Schneider — control transformers','https://www.se.com/us/en/product-range/7278-control-transformers/'),
            ('Omron — S8FS, phân biệt phiên bản','https://www.ia.omron.com/products/family/3460/lineup.html')]),
        'O-Sung':record('Rà ATS OSS-612-PC 4P. Bổ sung bảng giá ETINCO áp dụng 15/03/2026: 14 mã, mỗi mã có 3P/4P, chưa VAT. OSS-612-PC 4P 1250A có giá 70.150.000 đồng, giữ riêng giá 3P 56.500.000 đồng. PC/PCN và cách lắp không tự xem tương đương.',[
            ('ETINCO — bảng giá OSEMCO 15/03/2026','https://etinco.vn/wp-content/uploads/2025/05/bang-gia-bo-chuyen-nguon-ats-osemco-osung.pdf')]),
        'ProjectSamples':record('Rà 9 CAD từ dự án. Mã S8FS-C05024J trong tên block có tài liệu Omron, nhưng hình chỉ ghi POWER SUPPLY/DC ON/V.ADJ; giữ là tham chiếu nguồn, chưa tự xác nhận thông số hình học. BKN-LS thiếu mã mua hàng và dòng điện; MC 12AF không phải mã contactor đầy đủ; TIMER 24H chưa có mã. RISESUN RT18-32 không dùng giá CHINT cùng tên.',[
            ('Omron S8FS-C05024J','https://industrial.omron.eu/en/products/S8FS-C05024J'),
            ('LS — product match guide','https://pmg.ls-electric.com/'),
            ('CHINT — timer NJS1','https://www.chintglobal.com/in/en/products/low-voltage/iec/industrial-control/njs1.html')]),
        'Quạt':record('Rà 9 CAD: 3 quạt Leipole có mã xác nhận và 6 miệng/lưới lọc phổ thông. Bổ sung giá FKL6621.230/FKL6622.230/FKL6623.230 từ bảng DGE 01/2026 chưa VAT, giữ màu RAL7032/IP54 và điện áp 230VAC. Miệng gió rời không lấy giá cả quạt.',[
            ('Leipole — FKL66','https://vi.leipole.net/products/fkl66-fan-and-filter.html'),
            ('DGE — bảng giá Leipole 01/2026','https://dge.vn/uploads/bao-gia/435736_20260114_122258.pdf')]),
        'RMU':record('Rà 7 CAD: tổ hợp CCV/CCVV và RM6 NE. Cần hãng, cấp điện áp, số lộ, chức năng D/I, bộ bảo vệ và cấu hình đặt hàng. 40.5kV không lấy giá RM6 24kV. Các tổ hợp cần báo giá dự án; không dựng giá từ số ngăn.',[
            ('Schneider — RM6 và tổ hợp NE/DI','https://ckm-content.se.com/ckmContent/sfc/servlet.shepherd/document/download/0691H00000FJtkaQAD')]),
        'Schneider':record('Rà 236 CAD. Bổ sung 167 dòng từ Master Pricebook 07/2026 chính hãng: C120N/H, iIDK, CVS và LC1E. Giá gồm VAT; giữ dòng rò, 3P/4P, bộ trip và cuộn 220VAC/24VDC. CVS100BS không gộp với CVS100B/F/N vì cấu tạo/phụ kiện khác. PDF ghi CVS639F: bỏ nhóm chưa rõ, không gán sang CVS400F hay tự đổi 630F. Các LC1E có dấu * yêu cầu liên hệ giá hiện tại được bỏ khỏi nhập tự động. A9D chưa đủ mã; NS không tự đổi NSX; 173 CAD thư viện nguồn vẫn chưa xác nhận thiết bị thực.',[
            ('Schneider — Master Pricebook 2026','https://www.se.com/vn/vi/download/document/MasterPriceBook/'),
            ('Schneider — CAD hãng','https://www.se.com/us/en/work/support/resources-and-tools/cad-drawings/'),
            ('Schneider — A9D là tiền tố có nhiều cấu hình','https://www.se.com/es/es/faqs/FAQ000234157/')]),
        'Shihlin':record('Rà 20 CAD. BHA là MCB, BHL là RCBO; không đổi BHL thành RCCB hoặc tự thay BHA bằng BHA-B3/RPL. Giá BHA/BHL tìm được có bản cũ 2017, chưa dùng thành giá hiện tại. Các mã BM đã có giá giữ đúng dòng và số cực; 4 MCB không có mã vẫn cần đọc nhãn.',[
            ('Shihlin — BHA/BHL/BHN','https://global.seec.com.tw/ja/product/7100.html'),
            ('Shihlin — BHL-A RCBO','https://en.seec.com.tw/Content/Goods/GCont.aspx?CatId=2016011810180707458&MSID=746515325375074434&MmmID=707031024777534630&SiteID=30')]),
        'ThietBiDoLuongHienThi':record('Rà 21 CAD. EMIC CV130/140/131/141 cần hệ số đo, dòng và biến thể nắp; không lấy giá CE/ME khác dòng. PM710 được hãng thông báo ngừng thương mại năm 2015; PM51xx là gợi ý thay thế, không gán giá hoặc CAD thay thế tự động. Holley/Omega BE-96 và đồng hồ chưa rõ mã còn thiếu nguồn đúng mã.',[
            ('EMIC — công tơ CV/MV/CE/ME','https://emic.com.vn/vn/cong-to-dien'),
            ('Schneider — PM710 ngừng thương mại','https://www.se.com/uk/en/faqs/FA264122/')]),
        'Tụ bù':record('Rà 29 CAD Nuintek/Samwha. Có giá theo hãng nhưng các CAD chưa ghi mã/kvar/điện áp/Hz để chốt giá. Tài liệu Samwha cho thấy nhiều kvar/điện áp có kích thước trùng nhau. Mã suy từ kích thước vẫn là ứng viên, không dùng làm mã đã xác nhận.',[
            ('Samwha — bảng biến thể tụ công suất','https://www.samwha.com/fc/010102.asp'),
            ('NuinTEK — trang sản phẩm do hãng cung cấp','https://nuintek.en.ec21.com/product_list.html')]),
        'Ổ cắm':record('Rà 7 CAD. Giữ riêng CHENG LI, CLIPSAL, PCE, VANLOCK-DELTA và 2 mẫu chưa rõ hãng. 63A/5p/6h xác định cấu hình PCE nhưng chưa đủ SKU/kiểu lắp/IP; không tự gán 135-6 chỉ từ số tiếp điểm.',[
            ('PCE — ví dụ cấu hình 63A 5p 6h','https://www.pce.pl/images/produkty/135-6_EN.PDF')]),
    })
    for folder in ('Khóa','Phíp','Phụ kiện tủ điện','Đố','Đồng'):
        reviews[folder]=record('Đã rà từng mục về tên, phân nhóm, mặt vẽ và dữ liệu nguồn. Theo yêu cầu người dùng, phụ kiện không cần khớp chính xác mã/giá. Giữ kích thước/mã hình nguồn nếu có; không gán Asian hoặc Rittal thành hãng của phụ kiện phổ thông.',[], 'reviewed_optional_price_scope')
    reviews['Bộ điều khiển']['status']='reviewed_metadata_and_family_sources'
    if 'Đã kết thúc lượt rà danh sách 19 CAD' not in reviews['Bộ điều khiển']['note']:
        reviews['Bộ điều khiển']['note']+=' Đã kết thúc lượt rà danh sách 19 CAD và nguồn theo dòng; 11 mẫu chưa rõ hãng vẫn chưa đủ nhãn/mã để chọn giá.'
    path.write_text(json.dumps(reviews,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    assert len(reviews)==26


if __name__=='__main__':update()
