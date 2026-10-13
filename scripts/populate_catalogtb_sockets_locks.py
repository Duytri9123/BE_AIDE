"""Curate separate socket and cabinet-lock projections, preserving source drawings."""
import json
import shutil
from pathlib import Path
import ezdxf
from ezdxf import bbox
from ezdxf.addons import Importer
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page
from ezdxf.addons.drawing.properties import LayoutProperties

ROOT=Path(__file__).resolve().parents[1]/'data'/'CatalogTB'
SOURCE=Path(__file__).resolve().parents[2]/'Tudien'/'CATALOG_PHU_KIEN_DOC_LAP'
ROWS={r['id']:r for r in json.loads((SOURCE/'full_accessory_cad_inventory.json').read_text(encoding='utf-8'))['records']}
PROFILES=[]

def save(category,key,title,code,brand,kind,views,spec=None,source=None,features=None):
    folder=ROOT/category/'ThietBi'/key
    folder.mkdir(parents=True,exist_ok=True)
    ids=[]
    for id_,face,doc in views:
        dest=folder/'HinhChieu'/id_;dest.mkdir(parents=True,exist_ok=True)
        doc.units=4;doc.saveas(dest/'ban_ve.dxf')
        ext=bbox.extents(doc.modelspace(),fast=True)
        assert ext.has_data
        backend=SVGBackend();Frontend(RenderContext(doc),backend).draw_layout(doc.modelspace(),layout_properties=LayoutProperties('Model','#ffffff','#243b53',units=4,dark_background=False))
        (dest/'xem_truoc.svg').write_text(backend.get_string(Page(max(35,ext.size.x+20),max(35,ext.size.y+20))),encoding='utf-8')
        data={'id':id_,'thiet_bi':key,'loai_hinh':'view','ten_hinh':face,'tep':{'cad_dxf':'ban_ve.dxf','preview':'xem_truoc.svg'},'kich_thuoc_hinh_mm':{'ngang':round(ext.size.x,1),'cao':round(ext.size.y,1)}}
        (dest/'thong_tin.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');ids.append(id_)
    lock=category=='Khóa'
    first=json.loads((folder/'HinhChieu'/ids[0]/'thong_tin.json').read_text(encoding='utf-8'))['kich_thuoc_hinh_mm']
    parameters=dict(spec or {})
    parameters['kich_thuoc_mat_truoc_mm']=f"{first['ngang']:g} × {first['cao']:g}"
    profile={'nhom':category,'ten_kieu':title,'ten_san_pham':title,'ma_dong_san_pham':code,'hang_xac_nhan':brand,'ban_chat':kind,
      'cong_dung':'Giữ cửa tủ đóng và điều khiển việc mở cửa.' if lock else 'Tạo điểm cấp điện tháo lắp bằng phích cắm cho thiết bị hoặc dụng cụ bảo trì.',
      'vi_tri_lap_dat':'Trên cánh cửa; cơ cấu chốt làm việc phía trong tủ.' if lock else 'Trên mặt tủ hoặc bảng phụ; chừa khoảng trống phía sau để đấu dây và phía trước để cắm/rút phích.',
      'thong_so':parameters,'dac_diem':features or [],'cac_hinh_cad':ids,
      'lua_chon_ky_thuat':(['Chọn kiểu tay nắm, ổ chìa hoặc đầu tam giác phù hợp cách vận hành.', 'Đối chiếu lỗ khoét cửa, chiều dày tôn, chiều dài thân và vị trí lưỡi chốt.'] if lock else ['Chọn dòng, điện áp, số cực và kiểu phích cắm tương thích.', 'Đối chiếu kích thước bích, khoảng cách vít, độ sâu đấu dây và cấp bảo vệ cần thiết.']),
      'muc_do_xac_nhan':'Chưa xác định mã đặt hàng đầy đủ; cần đối chiếu kiểu lắp và cấu hình trước khi chọn sản phẩm.',
      'tai_lieu_hang':source,'nguon_tham_khao':[source] if source else []}
    (folder/'thong_tin_thiet_bi.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2),encoding='utf-8')
    PROFILES.append((category,key,len(ids)))

def from_rows(prefix,faces):
    result=[]
    for n,face in faces:
        id_=f'{prefix}-V{n:03d}';result.append((id_,face,ezdxf.readfile(SOURCE/ROWS[id_]['cad_dxf'])))
    return result

locks=[
('A19','Khóa xoay tay nắm bầu dục A-19','A-19','Khóa xoay tay nắm','A04_a19',[(2,'Mặt trước'),(1,'Mặt bên'),(3,'Mặt nhìn dọc thân khóa')],'https://www.takigen.co.jp/products/detail/A-19'),
('A480','Khóa tay nắm âm A-480','A-480','Khóa tay nắm âm','A04_a480',[(2,'Mặt trước'),(1,'Mặt bên')],None),
('C45_72','Khóa tay nắm âm C45-72','C45-72','Khóa tay nắm âm','A04_c4572',[(1,'Mặt trước'),(2,'Mặt bên'),(3,'Mặt sau')],None),
('MS301','Khóa xoay tay nắm MS301','MS301','Khóa xoay tay nắm','A04_ms301',[(1,'Mặt trước')],'https://www.haixianglock.com/en/product_view.asp?t_p_id=610'),
('MS303','Khóa xoay tay nắm MS303','MS303','Khóa xoay tay nắm','A04_ms303',[(1,'Mặt trước')],None),
('TG504','Khóa xoay đầu tam giác TG-504','TG-504','Khóa cam dùng chìa tam giác','A04_tg504',[(4,'Mặt trước'),(5,'Mặt bên')],None),
('KhoaAm','Khóa tay nắm âm cửa tủ',None,'Khóa tay nắm âm','A04_unnamed_lock',[(1,'Mặt trước'),(2,'Mặt bên')],None),
('AB301_1_1','Khóa tay nắm âm AB301-1-1 · cỡ lớn','AB301-1-1','Khóa tay nắm âm','A08_cluster9',[(1,'Mặt trước')],None),
('AB301_2_1','Khóa tay nắm âm AB301-2-1 · cỡ vừa','AB301-2-1','Khóa tay nắm âm','A08_cluster10',[(1,'Mặt trước')],None),
('AB301_3_1','Khóa tay nắm âm AB301-3-1 · cỡ nhỏ','AB301-3-1','Khóa tay nắm âm','A08_cluster11',[(1,'Mặt trước')],None),
('KhoaBat','Khóa bật cửa tủ',None,'Khóa bật','A08_cluster12',[(2,'Mặt trước'),(3,'Mặt bên')],None),
('KhoaMoc','Khóa móc cửa tủ',None,'Khóa móc','A08_cluster13',[(1,'Mặt trước'),(2,'Mặt bên')],None),
('MS308','Khóa tay nắm MS308-2','MS308-2','Khóa xoay tay nắm','A08_cluster14',[(1,'Mặt trước'),(2,'Mặt bên')],'https://www.haixianglock.com/productshow/273.html'),
('MS8712','Khóa cam đầu tam giác MS8712','MS8712','Khóa cam dùng chìa tam giác','A08_cluster16',[(1,'Mặt trước'),(2,'Mặt bên')],None),
('TayNamU','Tay nắm kéo cửa tủ dạng chữ U',None,'Tay nắm cửa tủ','A08_cluster4',[(1,'Mặt trước')],None),
('TayNamThang','Tay nắm kéo cửa tủ dạng thanh',None,'Tay nắm cửa tủ','A08_cluster5',[(1,'Mặt trước')],None),
('ChotNgang','Chốt cửa tủ nằm ngang',None,'Chốt trượt cửa tủ','A08_cluster8',[(1,'Mặt trước'),(2,'Mặt bên')],None),
]
for key,title,code,kind,prefix,faces,source in locks:
    save('Khóa',key,title,code,None,kind,from_rows(prefix,faces),source=source)

source_doc=ezdxf.readfile(SOURCE/ROWS['A10-LOOSE-CONTEXT']['cad_dxf'])
def crop(id_,face,rect):
    x1,y1,x2,y2=rect;entities=[]
    for e in source_doc.modelspace():
        if e.dxftype() in ('TEXT','MTEXT','DIMENSION','LEADER'):continue
        b=bbox.extents([e],fast=True)
        if b.has_data and x1<=b.extmin.x and b.extmax.x<=x2 and y1<=b.extmin.y and b.extmax.y<=y2:entities.append(e)
    assert entities,id_
    doc=ezdxf.new('R2018');imp=Importer(source_doc,doc);imp.import_entities(entities);imp.finalize()
    return (id_,face,doc)

sockets=[
('Clipsal_Doi','Ổ cắm đôi CLIPSAL · mặt 65,7 × 114 mm','CLIPSAL',None,[('A10_SOCKET_CLIPSAL_DOUBLE','Mặt trước',(-20848,85130,-20777,85248))],{},'https://www.clipsal.com/products/power-points-switches/standard-series'),
('ChengLi_Doi','Ổ cắm đôi CHENG LI · mặt 76 × 118 mm','CHENG LI',None,[('A10_SOCKET_CHENGLI_DOUBLE','Mặt trước',(-20614,85125,-20535,85248))],{},None),
('Clipsal_Don','Ổ cắm đơn CLIPSAL · mặt 86 × 86 mm','CLIPSAL',None,[('A10_SOCKET_CLIPSAL_SINGLE','Mặt trước',(-20376,85150,-20287,85240))],{},None),
('VanlockDelta','Ổ cắm công nghiệp VANLOCK-DELTA','VANLOCK-DELTA',None,[('A10_SOCKET_VANLOCK_FRONT','Mặt trước',(-19880,85143,-19796,85235)),('A10_SOCKET_VANLOCK_SIDE','Mặt bên',(-19740,85143,-19655,85235))],{},None),
('CongNghiep3P','Ổ cắm công nghiệp 3 tiếp điểm · bích 80 mm',None,None,[('A10_SOCKET_3P_FRONT','Mặt trước',(-19393,85143,-19308,85235)),('A10_SOCKET_3P_SIDE','Mặt bên',(-19253,85143,-19167,85235)),('A10_SOCKET_3P_OPEN','Mặt trước mở nắp',(-19090,85143,-19004,85235))],{'so_tiep_diem':3},None),
('CongNghiep4P','Ổ cắm công nghiệp 4 tiếp điểm · bích 80 mm',None,None,[('A10_SOCKET_4P_FRONT','Mặt trước',(-19398,84927,-19313,85020)),('A10_SOCKET_4P_SIDE','Mặt bên',(-19254,84927,-19168,85020)),('A10_SOCKET_4P_OPEN','Mặt trước mở nắp',(-19080,84927,-18994,85020))],{'so_tiep_diem':4},None),
('PCE_5P_63A','Ổ cắm công nghiệp PCE · 5 cực · 63 A · 6h','PCE',None,[('A10_SOCKET_PCE63_FRONT','Mặt trước',(-19383,84480,-19268,84607)),('A10_SOCKET_PCE63_OPEN','Mặt trước mở nắp',(-19383,84265,-19268,84392))],{'so_cuc':5,'dong_dinh_muc_A':63,'vi_tri_chan_PE':'6h'},'https://www.pce.pl/produkt/gniazdo-tablicowe-proste-63a-5p-6h-ip66-67/'),
]
for key,title,brand,code,rects,spec,source in sockets:
    save('Ổ cắm',key,title,code,brand,'Ổ cắm điện', [crop(*r) for r in rects],spec,source)
print(json.dumps({'profiles':len(PROFILES),'views':sum(p[2] for p in PROFILES),'items':PROFILES},ensure_ascii=False))
