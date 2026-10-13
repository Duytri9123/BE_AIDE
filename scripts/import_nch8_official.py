"""Import source vector projections; keep coil/contact configuration unconfirmed."""
from pathlib import Path
import json,shutil,hashlib
import ezdxf
from ezdxf.addons.drawing import Frontend,RenderContext,svg,layout
from ezdxf.addons.drawing.recorder import Recorder

root=Path(__file__).resolve().parents[2]
out=root/'outputs/sample-cad-recovery'
folder=root/'BE_AIDE/data/CatalogTB/Chint/ThietBi/NCH8_20_25_2P'
folder.mkdir(parents=True,exist_ok=True)
url='https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/industrial-control/modular-ac-contactor/nch8/drawing/NCH8-20%EF%BD%9E25%202P-Modular%20AC%20Contactor-Drawing-2D.pdf'
shutil.copy2(out/'NCH8-2P-official.pdf',folder/'source-official.pdf')
paths=json.loads((out/'NCH8-official-paths.json').read_text())
views=[];checks=[]
for face,objects in paths.items():
    points=[s['point'] for p in objects for s in p]
    xmin=min(p[0] for p in points);xmax=max(p[0] for p in points);ymin=min(p[1] for p in points)
    factor=85/(xmax-xmin)
    transform=lambda p:((p[1]-ymin)*factor,(xmax-p[0])*factor)
    doc=ezdxf.new('R2018');doc.units=4;m=doc.modelspace()
    segments=0
    for path in objects:
        start=current=None;i=0
        while i<len(path):
            seg=path[i];point=transform(seg['point']);kind=seg['type']
            if kind==2:start=current=point
            elif kind==0:
                m.add_line(current,point);current=point;segments+=1
            elif kind==1:
                curve=path[i:i+3]
                if len(curve)!=3 or any(s['type']!=1 for s in curve):raise ValueError('Invalid cubic')
                spline=m.add_spline();spline.set_open_uniform([current]+[transform(s['point']) for s in curve],degree=3)
                current=transform(curve[-1]['point']);seg=curve[-1];i+=2;segments+=1
            else:raise ValueError('Unknown PDF segment')
            if seg['close'] and current!=start:m.add_line(current,start);current=start;segments+=1
            i+=1
    rec=Recorder();Frontend(RenderContext(doc),rec).draw_layout(m,finalize=True)
    bounds=rec.player().bbox();w,h=bounds.size.x,bounds.size.y
    nominal=18 if face=='front' else 66.5
    if abs(w-nominal)>.2 or abs(h-85)>.03:raise ValueError(f'Dimension mismatch {face}: {w}, {h}')
    dest=folder/'CadDon'/face;dest.mkdir(parents=True,exist_ok=True)
    doc.saveas(dest/'ban_ve.dxf')
    backend=svg.SVGBackend();rec.player().replay(backend)
    (dest/'xem_truoc.svg').write_text(backend.get_string(layout.Page(0,0)),encoding='utf8')
    provenance={'official_url':url,'sha256':hashlib.sha256((folder/'source-official.pdf').read_bytes()).hexdigest(),
                'orientation':'source projection rotated to upright DIN orientation',
                'scale_basis':'official 85 mm full length dimension; uniform scale',
                'source_paths':len(objects),'exported_curve_and_line_segments':segments,
                'nominal_width_mm':nominal,'vector_width_difference_mm':w-nominal,
                'dimension_review':'source vector is preserved; nominal dimensions remain separate'}
    (dest/'thong_tin_cad_chen.json').write_text(json.dumps({'hinh_hoc_lap_dat':{'don_vi':'mm',
        'bao_hinh_mm':{'min_x':bounds.extmin.x,'min_y':bounds.extmin.y,'max_x':bounds.extmax.x,'max_y':bounds.extmax.y},
        'status':'official_projection_envelope_not_mounting_hole_map'},'provenance':provenance,'fabrication_ready':False},indent=2),encoding='utf8')
    label='Mặt trước' if face=='front' else 'Mặt bên'
    views.append({'id_hinh_goc':face,'huong_nhin':label,'nhan_hien_thi':label,'duong_dan':f'CadDon/{face}/ban_ve.dxf',
        'bo_tri_trong_tu':{'cho_phep_chen':True,'fabrication_ready':False}})
    checks.append({'face':face,'width_mm':w,'height_mm':h,**provenance})
profile={'nhom':'Chint','ten_san_pham':'Contactor CHINT NCH8-20 / NCH8-25 · 2P',
    'ten_kieu':'NCH8-20 / NCH8-25 2P',
    'hang_xac_nhan':'CHINT','tu_khoa_tim_kiem':['NCH8-20','NCH8-25'],
    'nhan_dien_ai':{'loai_thiet_bi_code':'CONTACTOR','so_cuc':2,'exact_SKU_confirmed':False},
    'thong_so':{'dong_dinh_muc':'20 / 25 A','kich_thuoc':'18×85×66,5 mm; thân 82 mm'},
    'cad_don':views,'cad_chen_tu':views[0],
    'can_xac_minh':['Điện áp cuộn hút','Cấu hình NO/NC và mã đặt hàng','Dòng theo loại tải AC7a/AC7b','Khoảng đấu dây và điều kiện nhiệt'],
    'nguon_cad':[{'url':url,'type':'official manufacturer 2D vector PDF'}],'fabrication_ready':False}
(folder/'thong_tin_thiet_bi.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2),encoding='utf8')
(out/'NCH8-official-import-check.json').write_text(json.dumps(checks,indent=2),encoding='utf8')
print(json.dumps([{k:c[k] for k in ('face','width_mm','height_mm','source_paths')} for c in checks]))
