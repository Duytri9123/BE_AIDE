"""Installation recommendations by device function, separate from projection direction."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'data'/'CatalogTB'
SOURCES={
 'door':'https://www.rittal.com/ca-en/products/PG20231215ZUB101/PG20240411ZUB101',
 'operator':'https://download.se.com/files?p_Doc_Ref=DIA5ED2120503EN&p_File_Name=DIA5ED2120503EN.pdf&p_enDocType=Catalog',
 'internal':'https://www.rittal.com/com-en/products/PG20231215ZUB101/PG20240403ZUB102/PG20240403ZUB107',
 'fan':'https://files.danfoss.com/download/Drives/Rittal_description_fans.pdf'}

def classify(category, kind, name):
    # Interior door means the dead-front operator panel, not the equipment backplate.
    if category=='Khóa' or kind in ('Khóa cửa tủ điện','Chốt vặn cửa tủ','Bản lề cửa tủ'):
        return 'canh_ngoai',['canh_ngoai','canh_trong'],'Gắn trên cánh và mép khung tương ứng. Phần tay nắm ở mặt thao tác; chốt hoặc bản lề làm việc phía sau/mép cánh.','door'
    if kind in ('Điểm nâng tủ','Bản mã nâng tủ','Bản mã treo tủ'):
        return 'khung_vo',['khung_vo'],'Gắn trên khung, nóc hoặc vách chịu lực; không bố trí trên cánh thao tác.','internal'
    if kind in ('Nhãn an toàn','Cửa sổ quan sát','Giá giữ nhãn'):
        return 'canh_ngoai',['canh_ngoai','canh_trong'],'Đặt ở mặt cánh có thể nhìn thấy; cửa sổ cần lỗ khoét và vị trí quan sát phù hợp.','door'
    if kind=='Túi đựng sơ đồ':
        return 'mat_sau_canh',['mat_sau_canh'],'Gắn ở mặt sau cánh ngoài hoặc cánh trong để lấy tài liệu khi mở cửa.','door'
    if category=='Quạt':
        return 'vach_tu',['vach_tu','canh_ngoai'],'Ưu tiên vách tủ; có thể đặt trên cánh ngoài nếu chừa khoảng mở cửa, dây cấp và đường gió. Không đặt tấm lọc trên cánh trong làm kín đường gió.','fan'
    if category=='Ổ cắm':
        return 'ben_trong',['ben_trong','canh_trong','canh_ngoai'],'Ổ bảo trì ưu tiên bảng phụ bên trong; ổ gắn cánh phải đúng kiểu gắn bảng, cấp bảo vệ và chừa khoảng cắm phích.','door'
    if category=='ThietBiDoLuongHienThi':
        if kind.startswith('Công tơ'):
            return 'ben_trong',['ben_trong','canh_trong'],'Ưu tiên tấm lắp hoặc ngăn đo đếm. Chỉ gắn cánh trong khi có gá chịu lực và đường dây phù hợp; dùng cửa sổ để đọc từ bên ngoài.','internal'
        return 'canh_ngoai',['canh_ngoai','canh_trong'],'Mặt hiển thị hoặc núm chọn hướng về người thao tác; thân và đầu dây nằm phía sau cánh.','operator'
    if category=='DenBaoNutNhanCauChiContactor' and any(x in kind for x in ('Đèn báo','Nút nhấn','Công tắc chọn')):
        return 'canh_ngoai',['canh_ngoai','canh_trong'],'Đầu đèn/nút hướng ra mặt thao tác; thân và tiếp điểm nằm sau cánh. Chọn cánh trong nếu điều khiển chỉ cần dùng sau khi mở cửa ngoài.','operator'
    if category=='Bộ điều khiển' and any(x in kind for x in ('hệ số công suất','chuyển nguồn','hòa đồng bộ')):
        return 'canh_ngoai',['canh_ngoai','canh_trong'],'Bộ có màn hình và phím ưu tiên gắn cánh; cần đối chiếu kiểu gá. Bộ không hỗ trợ gắn bảng phải đặt trên tấm lắp bên trong.','operator'
    if category=='LS' and any(x in kind for x in ('MCB','MCCB','ELCB','RCBO','RCCB','Cầu dao','Thiết bị chống rò')):
        return 'ben_trong',['ben_trong','canh_trong'],'Thân thiết bị cố định trên ray DIN hoặc tấm lắp bên trong. Cánh trong chỉ để lộ tay gạt qua lỗ khoét; không treo toàn bộ thiết bị nặng lên cánh.','internal'
    return 'ben_trong',['ben_trong'],'Gắn cố định trên tấm lắp, ray, khung đỡ hoặc thanh dẫn bên trong theo cấu tạo; chừa khoảng đấu dây và bảo trì.','internal'

counts={}
for path in ROOT.rglob('thong_tin_thiet_bi.json'):
    profile=json.loads(path.read_text(encoding='utf-8'))
    cat=path.relative_to(ROOT).parts[0]
    primary,allowed,note,source=classify(cat,profile.get('ban_chat',''),profile.get('ten_san_pham',''))
    mounting={'vi_tri_uu_tien':primary,'vi_tri_phu_hop':allowed,'huong_dan':note,
              'muc_do':'Gợi ý bố trí theo chức năng và kiểu gá; cần đối chiếu biến thể khi lắp thực tế.',
              'nguon_tham_khao':[SOURCES[source]]}
    profile['bo_tri_lap_dat']=mounting
    for entry in profile.get('cad_don',[]):
        entry['bo_tri_lap_dat']=mounting
        meta_path=path.parent/'CadDon'/entry['id_hinh_goc']/'thong_tin_cad_chen.json'
        meta=json.loads(meta_path.read_text(encoding='utf-8'));meta['bo_tri_lap_dat']=mounting
        meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        if entry['id_hinh_goc']==profile.get('cad_chen_tu',{}).get('id_hinh_goc'):
            (path.parent/'CadChenTu'/'thong_tin_cad_chen.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    path.write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    counts[primary]=counts.get(primary,0)+1
print(json.dumps(counts))
