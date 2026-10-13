"""Separate three copper bar templates from D09 without changing geometry."""
import json,sys,ezdxf
from ezdxf.addons import Importer
from pathlib import Path
from populate_catalogtb_chint import ROOT,save
from populate_catalogtb_abb_rmu_osung import profile
base=ROOT.parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
source=next((base/'04_BO_THIET_BI_DXF/D09').glob('*/002_Hinh_roi_002.dxf'))
src=ezdxf.readfile(source);out=ROOT.parents[1]/'tmp/copper_source';out.mkdir(parents=True,exist_ok=True)
states=[];evidence=[]
for i,handles in enumerate([['3F','42','45'],['40','43','46'],['41','44','47']],1):
 doc=ezdxf.new('R2018');doc.units=4;imp=Importer(src,doc);imp.import_entities([src.entitydb[h] for h in handles]);imp.finalize();f=out/f'Cu_bent_{i}.dxf';doc.saveas(f)
 states.append((f'D09-CU-{i}','Mặt trước',f'Mặt rộng · thanh {i}',f))
 evidence.append({'cad_id':f'D09-CU-{i}','source_file':source.relative_to(ROOT.parents[2]).as_posix(),'source_handles_in_extracted_dxf':handles})
d,folder=profile('Đồng','Cu_20x5_Uon','Busbar','Cu 20×5 mm',None,states,[],
 ['Cu 20×5 mm là nhãn nguồn; bề rộng nét CAD có đoạn 25/30 mm, chưa xác nhận tiết diện thực tế.',
 'Ba thanh là ba mẫu đường đi khác nhau, không phải ba góc nhìn của cùng thanh.',
 'Lỗ tròn rời và cụm ATS trong D09 giữ tham khảo, không tự gán lỗ lên thanh.',
 'Chọn đường đi, mặt rộng, chiều sâu, uốn và cọc nối theo bố trí thực tế; chưa đủ dữ liệu gia công.'],True,
 {'vat_lieu':'Cu theo nhãn nguồn','rong_nhan_nguon_mm':20,'day_nhan_nguon_mm':5,'tiet_dien_nhan_nguon_mm2':100,'tiet_dien_da_xac_nhan_mm2':None,'dong_cho_phep_A':None})
d['ten_kieu']=d['ten_san_pham']='Thanh đồng uốn Cu 20×5 mm';d['tu_khoa_tim_kiem']+=['thanh cái','thanh dong','dong uon','copper busbar','đồng thanh','đồng xương cá']
d['nhan_dien_ai']['loai_thiet_bi_code']='CopperBusbar';d['nhan_dien_ai']['hang']=None;d['hang_xac_nhan']=None;d['ma_dong_san_pham']=None;d['nhan_dien_ai']['cac_ma_dong_san_pham']=[]
d['nhan_dien_ai']['pham_vi_ma']='custom_busbar_template';d['nhan_dien_ai']['cac_cad_la_bien_the_duong_di']=True;d['nguon_tach_cad']=evidence
save(folder/'thong_tin_thiet_bi.json',d)
save(ROOT/'Đồng/kiem_tra_dong.json',{'profiles':1,'views':3,'source':source.relative_to(ROOT.parents[2]).as_posix(),'evidence':evidence,'pending':['Xác nhận tiết diện thực tế','Lỗ nối và đầu nối','Đồng xương cá chưa có mẫu CAD xác nhận riêng'],'excluded':'Không nhập cả cụm ATS hoặc khung bản vẽ làm thanh đồng.'})
print('Copper: 1 profile, 3 standalone CAD templates')
