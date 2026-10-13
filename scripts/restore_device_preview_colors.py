"""Render every device view with its original CAD colors and complete geometry."""
import json,re,logging,shutil
from pathlib import Path
import ezdxf
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page
from ezdxf.addons.drawing.properties import LayoutProperties
logging.disable(logging.CRITICAL)
root=Path(__file__).resolve().parents[1]/'data/CatalogTB'
count=0;brands={}
for profile in root.rglob('thong_tin_thiet_bi.json'):
    data=json.loads(profile.read_text(encoding='utf-8'))
    for view in data.get('cad_don',[]):
        folder=profile.parent/'CadDon'/view['id_hinh_goc']
        # ACIS outlines require the native preview renderer; ezdxf alone drops them.
        if (folder/'native_preview.json').exists():
            continue
        doc=ezdxf.readfile(folder/'ban_ve.dxf')
        backend=SVGBackend()
        Frontend(RenderContext(doc),backend).draw_layout(doc.modelspace(),layout_properties=LayoutProperties('Model','#212830','#ffffff',units=doc.units,dark_background=True))
        svg=backend.get_string(Page(0,0))
        svg=re.sub(r'(stroke-width: )(\d+)',lambda m:m[1]+str(max(1500,int(m[2]))),svg)
        (folder/'xem_truoc.svg').write_text(svg,encoding='utf-8')
        if view['id_hinh_goc']==data.get('cad_chen_tu',{}).get('id_hinh_goc'):
            shutil.copy2(folder/'xem_truoc.svg',profile.parent/'CadChenTu/xem_truoc.svg')
        count+=1;brand=profile.relative_to(root).parts[0];brands[brand]=brands.get(brand,0)+1
        if count%100==0:print('Source-color previews',count,flush=True)
report={'views':count,'brands':brands,'policy':'Giữ màu CAD, toàn bộ đồng/đầu nối và hình học nguồn. Chỉ đổi nền và độ dày nét ảnh xem trước cho dễ đọc; không sửa DXF.'}
(root/'kiem_tra_mau_cad_thiet_bi.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False),flush=True)
