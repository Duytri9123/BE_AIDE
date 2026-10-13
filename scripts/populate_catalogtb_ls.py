"""Curate LS devices with independent projections and explicit variant boundaries."""
import json
import shutil
from pathlib import Path
import ezdxf
from ezdxf import bbox

BASE = Path(__file__).resolve().parents[2]
SOURCE = BASE/'Tudien'/'CATALOG_PHU_KIEN_DOC_LAP'
TARGET = BASE/'BE_AIDE'/'data'/'CatalogTB'/'LS'
rows = json.loads(Path(__file__).with_name('catalogtb_ls_source_map.json').read_text(encoding='utf-8'))
dataset = {d['cad_dxf']:d for d in json.loads((SOURCE/'LS_D02_DU_LIEU_MOI'/'devices.json').read_text(encoding='utf-8'))}
MC = 'https://www.ls-electric.com/upload/customer/download/1412/Susol_MC_E_1108.pdf'
TOR = 'https://www.ls-electric.com/upload/customer/download/4d8b99a1-c93d-4cd3-807b-1382f0c39384/Metasol_MS_E_180903.pdf'
MCB = 'https://www.ls-electric.com/upload/customer/download/1483/150905_MCB_E.pdf'
MCCB = 'https://pfinder.ls-electric.com/IEC/product/mccb_susol.do?region=IEC&spg=mccb_susol'
PROFILES = []

def save(key,title,code,kind,use,indices,faces=None,spec=None,url=None,notes=None):
    folder=TARGET/'ThietBi'/key
    ids=[]
    for n,i in enumerate(indices):
        row=rows[i];ident=row['id'];ids.append(ident)
        dest=folder/'HinhChieu'/ident;dest.mkdir(parents=True,exist_ok=True)
        shutil.copy2(SOURCE/row['cad_dxf'],dest/'ban_ve.dxf')
        shutil.copy2(SOURCE/row['preview'],dest/'xem_truoc.svg')
        doc=ezdxf.readfile(dest/'ban_ve.dxf');ext=bbox.extents(doc.modelspace(),fast=True)
        assert ext.has_data
        face=faces[n] if faces else 'Mặt trước'
        record={'id':ident,'thiet_bi':key,'loai_hinh':'view','ten_hinh':face,
                'tep':{'cad_dxf':'ban_ve.dxf','preview':'xem_truoc.svg'},
                'kich_thuoc_hinh_mm':{'ngang':round(ext.size.x,2),'cao':round(ext.size.y,2)}}
        (dest/'thong_tin.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    p={'nhom':'LS','ten_kieu':title,'ten_san_pham':title,'hang_xac_nhan':'LS Electric',
       'ma_dong_san_pham':code,'ban_chat':kind,'cong_dung':use,
       'vi_tri_lap_dat':'Trên ray DIN hoặc tấm lắp trong ngăn điều khiển/động lực, theo kiểu gá của thiết bị.',
       'thong_so':spec or {},'dac_diem':notes or [],'cac_hinh_cad':ids,
       'tai_lieu_hang':url,'nguon_tham_khao':[url] if url else [],
       'muc_do_xac_nhan':'Đã xác định dòng thiết bị; mã đặt hàng đầy đủ và cấu hình điện cần chọn theo biến thể.',
       'lua_chon_ky_thuat':(['Chọn cấp sử dụng AC-3/AC-1, dòng tải và điện áp cuộn hút.', 'Kiểm tra tiếp điểm phụ, rơ le nhiệt tương thích và khoảng trống lắp.'] if kind=='Khởi động từ' else
                           ['Chọn dải chỉnh dòng theo dòng định mức động cơ và contactor tương thích.'] if kind=='Rơ le nhiệt' else
                           ['Chọn dòng làm việc, điện áp, số cực và khả năng cắt theo hệ thống.', 'Với thiết bị chống rò, chọn dòng rò tác động và phối hợp bảo vệ quá dòng.'])}
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'thong_tin_thiet_bi.json').write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    PROFILES.append(key)

save('UA_1','Tiếp điểm phụ LS UA-1','UA-1','Khối tiếp điểm phụ','Đưa trạng thái đóng/mở contactor về mạch điều khiển.',[0],['Mặt đấu dây'],notes=['Chưa xác nhận số tiếp điểm NO/NC và kiểu gá của đúng biến thể.'],url=MC)
for i,code,frame in [(1,'MC-9a','12AF'),(2,'MC-9','32AF'),(3,'MC-35','63AF'),(4,'MC-95','95AF')]:
    save(code.replace('-','_'),f'Khởi động từ LS {code} · 3 cực',code,'Khởi động từ','Đóng cắt tải động lực bằng tín hiệu điều khiển cuộn hút.',[i],spec={'so_cuc_chinh':3,'co_khung':frame,'dien_ap_cuon_hut':'Chưa xác định','dong_ac3_cua_bien_the':'Chưa xác định'},url=MC)
save('MT_32','Rơ le nhiệt LS MT-32','MT-32','Rơ le nhiệt','Bảo vệ động cơ quá tải; tiếp điểm phụ ngắt mạch điều khiển contactor.',[5],url=TOR,notes=['MT-32 là dòng rơ le; không có nghĩa dòng chỉnh định cố định 32 A.'])
save('MT_63','Rơ le nhiệt LS MT-63','MT-63','Rơ le nhiệt','Bảo vệ động cơ quá tải, phối hợp với contactor và bảo vệ ngắn mạch.',[6,7],['Mặt trước · cấu tạo A','Mặt trước · cấu tạo B'],url=TOR,notes=['Hai cấu tạo mặt trước có cùng kích thước bao; chọn cấu tạo đúng với biến thể lắp.', 'Dải chỉnh dòng chưa xác định.'])
types={9:('BKD','Cầu dao cách ly',3),10:('BKH','MCB bảo vệ quá tải và ngắn mạch',1),11:('BKN','MCB bảo vệ quá tải và ngắn mạch',1),12:('BKP','MCB bảo vệ quá tải và ngắn mạch','1P+N'),13:('32KGRc','RCBO chống rò và bảo vệ quá dòng','1P+N'),14:('RKP','RCBO chống rò và bảo vệ quá dòng','1P+N'),15:('BS32c','Thiết bị chống rò và bảo vệ quá dòng',2),16:('RKN','RCCB bảo vệ dòng rò','1P+N')}
for i,(code,kind,poles) in types.items():
    use='Cách ly nguồn khi thao tác; cần bảo vệ quá dòng riêng.' if i==9 else 'Phát hiện dòng rò; phối hợp thiết bị bảo vệ quá dòng riêng.' if i==16 else 'Bảo vệ mạch trước quá tải, ngắn mạch'+(' và dòng rò.' if i in (13,14,15) else '.')
    save(code, f'LS {code} · {kind}',code,kind,use,[i],spec={'so_cuc':poles,'dong_dinh_muc':'Chưa xác định','kha_nang_cat':'Chưa xác định'},url=MCB)
for i,code,poles in [(18,'TD100_TD160',3),(19,'TD160',1),(20,'TS100_TS160_TS250',3),(21,'TS400_TS630',3),(22,'TS800',3)]:
    save(code,f'MCCB LS Susol {code.replace("_"," / ")} · {poles} cực',code.replace('_',' / '),'MCCB dạng khối','Bảo vệ mạch động lực trước quá tải và ngắn mạch; đóng cắt và cách ly mạch.',[i],spec={'so_cuc':poles,'dong_chinh_dinh':'Chưa xác định','cap_cat_N_H_L':'Chưa xác định'},url=MCCB)
for key,poles,indices in [('TS_Large_3P',3,[23,26,27]),('TS_Large_4P',4,[24,25,27])]:
    save(key,f'MCCB LS Susol TS · khung lớn {poles} cực','TS1000 / TS1250 / TS1600','MCCB dạng khối','Bảo vệ và đóng cắt lộ động lực dòng lớn.',indices,['Mặt trước','Mặt dưới','Mặt bên'],spec={'so_cuc':poles,'dong_dinh_muc':'Chưa xác định'},url=MCCB,notes=['Chưa xác nhận mã TS và bộ bảo vệ của đúng biến thể.','Mặt dưới được ghép theo bề rộng: 3 cực 210 mm, 4 cực 280 mm.','Mặt bên dùng chung để thể hiện chiều sâu khung; cần đối chiếu phụ kiện và đầu nối khi chọn biến thể.'])
for i in range(29,36):
    d=dataset[rows[i]['cad_dxf']];name=d['name'].replace('ABN/ABH/ABS','ABN / ABH / ABS');code=name.replace(' AF','')
    kind='ELCB dạng khối' if i==34 else 'MCCB dạng khối'
    save(f'Metasol_{i}',f'LS Metasol {name}',code,kind,'Bảo vệ mạch động lực trước quá tải và ngắn mạch'+('; có chức năng bảo vệ dòng rò theo biến thể ELCB.' if i==34 else '.'),[i],spec={'so_cuc':3,'dong_chinh_dinh':'Chưa xác định','kha_nang_cat':'Chưa xác định'},url='https://pfinder.ls-electric.com/IEC/product/mccb_metasol.do',notes=['Cỡ khung không thay thế cho dòng chỉnh định hoặc mã đặt hàng đầy đủ.'])

# Preserve context and duplicate source blocks for later comparison, outside insertable profiles.
for row in rows:
    dest=TARGET/'TuLieuBanVe'/row['id'];dest.mkdir(parents=True,exist_ok=True)
    (dest/'nguon.json').write_text(json.dumps(row,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'profiles':len(PROFILES),'source_records':len(rows)},ensure_ascii=False))
