"""Manufacturer pages researched 2026-10-16; independent of pricebook coverage."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def ref(brand,model,name,specifications,url):
    return dict(brand=brand,model=model,specifications={'Tên hàng':name,**specifications},source_url=url)


def main():
    path=ROOT/'app/data/source_reference_research.json'
    data=json.loads(path.read_text(encoding='utf8'));research=data['references']
    references=[
        (['TERMINAL_STOP','PHỤ_KIỆN_CỐ_ĐỊNH_CẦU_ĐẤU'],ref('Phoenix Contact','CLIPFIX 35-5 / 3022276','Chặn cuối dãy cầu đấu',{'Ray lắp':'NS 35/7.5 hoặc NS 35/15','Rộng':'5.2 mm','Vật liệu':'PA'},'https://www.phoenixcontact.com/en-us/products/end-block-clipfix-35-5-3022276')),
        (['SELECTOR_METER'],ref('Schneider Electric','K1F027MLH','Công tắc chuyển mạch vôn kế Harmony K',{'Chức năng':'Đo 3 điện áp dây và 3 điện áp pha–N','Góc chuyển':'45°','Dòng nhiệt':'12 A'},'https://www.se.com/uk/en/product/K1F027MLH/harmony-k1-k2-cam-voltmeter-switch-3l-and-3ln-45-12-a-screw-mounting/')),
        (['VENT_HOOD'],ref('Pfannenberg','PTFA 60.000 / 11786001055','Chụp thoát khí có lọc trên nóc tủ',{'Động cơ':'Không có; bộ lọc thoát khí thụ động','Lỗ khoét':'291 × 291 mm','Cấp bảo vệ biến thể':'IP54','Màu':'RAL7035'},'https://www.pfannenberg.com/en/thermal-management/filterfans/top-exhaust-filter/ptfa-60000/')),
        (['BẢN_LỀ_CỬA_TỦ'],ref('Rittal','SZ 2449.000','Bản lề mở rộng góc mở cửa',{'Góc mở danh nghĩa':'180°','Dòng tủ tham khảo':'AE; chọn theo cửa và bộ gá'},'https://www.rittal.com/uk-en/products/PG20231215ZUB101/PG20240411ZUB101/PG20240327ZUB104/PRO35433?variantId=2449000')),
        (['KHÓA_CỬA_TỦ_ĐIỆN','CHỐT_VẶN_CỬA_TỦ'],ref('EMKA','1000-U859-IA','Khóa nén xoay cửa tủ',{'Vật liệu':'Kẽm đúc mạ crôm','Lõi thao tác':'Vuông 7','Chiều cao thân GH':'18 mm','Hành trình nén':'4.5 mm'},'https://www.emka.com/products/1000-u859-ia')),
        (['TAY_NẮM_CỬA_TỦ'],ref('EMKA','1095-27-128AA','Tay nắm kéo dạng cầu',{'Vật liệu':'Nhôm phủ nhựa đen','Khoảng tâm A':'128 mm','Chiều cao H':'55 mm'},'https://www.emka.com/products/1095-27-128aa')),
        (['TRỤ_ĐỠ_CÁCH_ĐIỆN'],ref('Cnhici / Suntree Insulator','SM-25 / SM-35 / SM-50','Trụ đỡ cách điện thanh cái dòng SM',{'Vật liệu lựa chọn':'BMC / SMC','Nhiệt độ làm việc dòng':'−40…+140 °C','Ren và kích thước':'Chọn biến thể theo bản vẽ sản phẩm'},'https://www.suntreeinsulator.com/sm-lnsulator-series')),
        (['INSULATING_SUPPORT','THANH_ĐỠ_CÁCH_ĐIỆN','GIÁ_ĐỠ_CÁCH_ĐIỆN','BỘ_ĐỠ_CÁCH_ĐIỆN'],ref('Wöhner','01485 000','Bộ đỡ thanh cái 4 cực',{'Cấu hình':'4 cực, lỗ vít phía trong','Thanh cái phù hợp':'Rộng 12/15/20/25/30 mm; dày 5/10 mm'},'https://pim.woehner.de/EN/NL/System/60Classic_4P/Busbar_supports_busbars_and_covers/4-pole_60mm_system')),
        (['ĐẦU_CỐT_CÁP_BẮT_BU_LÔNG'],ref('Klauke','6R10','Đầu cốt ống đồng bắt bu lông',{'Tiết diện':'50 mm²','Lỗ bu lông':'M10','Vật liệu':'Đồng mạ thiếc, dòng R'},'https://www.klauke.com/Media/Default/Downloads/CatalogsBrochures/BRBESTOFR21GB_07-2021_I_GB.pdf')),
        (['CỬA_SỔ_QUAN_SÁT'],ref('Rittal','FT 2734.000','Cửa sổ quan sát tủ điện',{'Kích thước W×H×D':'597 × 197 × 34 mm','Khung':'Nhôm'},'https://www.rittal.com/pdf-creator/variant/gr-en/2734000')),
        (['TÚI_ĐỰNG_SƠ_ĐỒ'],ref('Rittal','2515200','Túi đựng sơ đồ bằng thép, thay đổi bề rộng',{'Bề rộng biến thể':'400 mm','Lắp đặt':'Trong cửa tủ, chọn bộ gá phù hợp'},'https://www.rittal.com/com-en/products/PG20231215ZUB101/PG20240411ZUB101/PG20240327ZUB105/PRO99664')),
        (['MÁNG_DÂY_TRONG_TỦ'],ref('Rittal','TS 8800.750','Máng đi dây có nắp',{'Kích thước':'Rộng 30 × sâu 80 × dài 2000 mm','Vật liệu':'PVC cứng','Màu':'RAL7030'},'https://www.rittal.com/com-en/products/PG20231215ZUB101/PG20240405ZUB003/PG20240405ZUB008/PRO13416?variantId=8800750')),
        (['ĐIỂM_NÂNG_TỦ'],ref('Rittal','4568000','Bu lông vòng nâng tủ',{'Ren':'M12','Vật liệu':'Thép carbon','Dòng tủ':'VX / TS / VX SE; tải nâng chọn theo tài liệu bộ tủ'},'https://www.rittal.com/us-en_US/products/PG20231215ZUB101/PG20240411ZUB102/PG20240402ZUB103/PRO13662')),
        (['BẢN_MÃ_TREO_TỦ'],ref('Rittal','SZ 2508.010','Tai gá treo tủ lên tường',{'Vật liệu':'Thép mạ kẽm','Khoảng cách tường':'10 mm','Dòng tham khảo':'KL/EB/BG/AE/EL; mẫu catalog cũ'},'https://www.rittal.com/com-en/products/PG20231215ZUB101/PG20240402ZUB104/PRO11706?variantId=2508010')),
        (['NAMEPLATE','GIÁ_GIỮ_NHÃN'],ref('Phoenix Contact','STP 5-2 / 0800967','Giá giữ nhãn cầu đấu',{'Cỡ cầu đấu tham khảo':'>5 mm','Nhãn tương thích':'UCT-TM 5 / 0828734'},'https://blog.phoenixcontact.com/marketing-hr/wp-content/uploads/sites/16/2017/06/1005361_EN_HQ_Thermotansferdruck_LoRes.pdf')),
        (['TẤM_CHE_BẢO_VỆ_QUẠT'],ref('Rittal','SK 3237.080','Chụp bảo vệ quạt/lọc tủ',{'Vật liệu':'Inox AISI304','Kích thước W×H×D':'150 × 230 × 40 mm','Dùng với':'Quạt/lọc dòng 3237'},'https://www.rittal.com/us-en_US/products/PG20231215KLI101/PG20231215KLI1007/PRO0305?variantId=3237080')),
        (['ENCLOSURE_REFERENCE'],ref('Rittal','AX 1058.000','Vỏ tủ compact có tấm lắp',{'Kích thước W×H×D':'600 × 800 × 250 mm','Vật liệu':'Thép tấm','Cấp bảo vệ mẫu catalog':'IP66','Ghi chú':'Vỏ tủ tham khảo; bản CAD khác kích thước chọn mã khác'},'https://www.rittal.com/com-en/products/PG20231215SCH101/PG20231512SCH301/PRO70850?variantId=1058000')),
        (['FIRE_SUPPRESSION_REFERENCE'],ref('ELIDE FIRE','ELIDE FIRE BALL','Bóng chữa cháy tự kích hoạt',{'Chức năng':'Kích hoạt khi tiếp xúc ngọn lửa','Phương án sử dụng':'Cố định tại vùng nguy cơ hoặc sử dụng theo hướng dẫn hãng'},'https://www.elidefire.com/')),
        (['THERMAL_RELAY'],ref('ABB','TF42-3.1 / 1SAZ721201R1033','Rơ le nhiệt bảo vệ quá tải động cơ',{'Dải chỉnh mẫu':'2.30–3.10 A','Dòng sản phẩm':'TF42; chọn dải theo dòng động cơ'},'https://empower.abb.com/ecatalog/ec/EN_CA/p/1SAZ721201R1033')),
    ]
    for categories,row in references:
        for category in categories:
            options=research.setdefault(category,[])
            options[:]=[o for o in options if (o['brand'],o['model'])!=(row['brand'],row['model'])]
            options.append(row)
    # Functional visual recognition only: the pictured ABB drawing is an
    # overload relay reference. TF42 is a selectable catalog family, not proof
    # of the exact legacy drawing's ordering code or dimensions.
    p=ROOT/'data/CatalogTB/ABB/ThietBi/ABB_D03_C2_I08/thong_tin_thiet_bi.json'
    raw=json.loads(p.read_text(encoding='utf-8-sig'))
    raw.update(ten_san_pham='Rơ le nhiệt ABB · CAD tham khảo',ten_kieu='Rơ le nhiệt ABB',ban_chat='THERMAL_RELAY',cong_dung='Tham khảo bố trí rơ le bảo vệ quá tải động cơ; chọn mã và dải chỉnh từ catalog.')
    raw['nhan_dien_ai']['loai_thiet_bi_code']='THERMAL_RELAY'
    raw['nhan_dien_web']={'status':'functional_type_reference','user_accepts_approximate_family':True,'model_candidate':'TF42',
                         'basis':'Visual review of three-pole overload-relay structure and manufacturer catalog; exact source model remains unassigned.'}
    p.write_text(json.dumps(raw,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Added',len(references),'manufacturer web reference families across',len(research),'functional categories')


if __name__=='__main__':main()
