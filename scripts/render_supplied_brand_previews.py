"""Keep source colors visible, including ACI 255 white geometry."""
import logging,re,shutil,sys
import ezdxf
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page
from ezdxf.addons.drawing.properties import LayoutProperties
from update_supplied_brand_libraries import ROOT,read
logging.disable(logging.CRITICAL)
for brand in sys.argv[1:]:
    items=read(ROOT/brand/'kiem_tra_nguon_bo_sung.json')['added']
    for item in items:
        folder=(ROOT/item['profile']).parent;view=folder/'HinhChieu'/item['id'];doc=ezdxf.readfile(view/'ban_ve.dxf')
        backend=SVGBackend();Frontend(RenderContext(doc),backend).draw_layout(doc.modelspace(),layout_properties=LayoutProperties('Model','#212830','#ffffff',units=doc.units,dark_background=True))
        preview=view/'xem_truoc.svg'
        # A minimum preview stroke keeps large devices visible as thumbnails.
        # This changes only SVG presentation, never the source CAD lineweights.
        svg=re.sub(r'(stroke-width: )(\d+)',lambda m:m[1]+str(max(1500,int(m[2]))),backend.get_string(Page(0,0)))
        preview.write_text(svg,encoding='utf-8')
        for dest in [folder/'CadDon'/item['id'],folder/'CadChenTu']:shutil.copy2(preview,dest/preview.name)
    print(brand,'source-color previews:',len(items),flush=True)
