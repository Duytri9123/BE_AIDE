from pathlib import Path
import json,re,os
from ezdxf import bbox
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.config import Configuration,ColorPolicy
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page
from ezdxf.addons.drawing.properties import LayoutProperties
ROOT=Path(__file__).resolve().parents[2];OUT=Path(os.environ['FORM_OUTPUT']) if os.environ.get('FORM_OUTPUT') else ROOT/'BE_AIDE/data/CatalogTB/Form tủ'
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def bounds(e):
 try:
  b=bbox.extents([e],fast=True)
  return (b.extmin.x,b.extmin.y,b.extmax.x,b.extmax.y) if b.has_data else None
 except:return None
def inside(b,r):return b and b[0]>=r[0]-.1 and b[1]>=r[1]-.1 and b[2]<=r[2]+.1 and b[3]<=r[3]+.1
def render(doc,path):
 be=SVGBackend();Frontend(RenderContext(doc),be,config=Configuration(color_policy=ColorPolicy.BLACK)).draw_layout(doc.modelspace(),layout_properties=LayoutProperties('Model','#ffffff','#000000',units=4,dark_background=False))
 svg=be.get_string(Page(0,0));svg=re.sub(r'stroke-width: ([0-9.]+)',lambda m:'stroke-width: '+str(max(1000,float(m[1]))),svg);path.write_text(svg,encoding='utf-8')
