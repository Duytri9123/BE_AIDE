"""Apply user's exact form ID and undo the initial screenshot-based selection."""
import json,re
import ezdxf
from ezdxf.addons import Importer
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.config import Configuration
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page,Margins
from ezdxf.addons.drawing.properties import LayoutProperties
from extract_project_helpers import ROOT,OUT,save
def render(doc,path):
 b=SVGBackend();Frontend(RenderContext(doc),b,config=Configuration()).draw_layout(doc.modelspace(),layout_properties=LayoutProperties('Model','#212830','#ffffff',units=4,dark_background=True));svg=b.get_string(Page(0,0,margins=Margins(10,10,10,10)));svg=re.sub(r'stroke-width: ([0-9.]+)',lambda m:'stroke-width: '+str(max(1000,float(m[1]))),svg);path.write_text(svg,encoding='utf-8')
d=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'))
for r in d['shells']:
 if r['id'] not in ('09196d73d654cef5-111BA76','0785608caf266cc1-107DB6E'):continue
 folder=OUT/'Mau'/r['id'];src=ezdxf.readfile(ROOT/r['original_dxf'])
 for fn in ('ban_ve.dxf','ban_ve_co_khung_goc.dxf'):
  doc=ezdxf.readfile(folder/fn)
  if r['id']=='09196d73d654cef5-111BA76':
   existing={tuple(round(v,4) for v in e.dxf.insert) for e in doc.modelspace().query('INSERT')}
   entities=[src.entitydb[h] for h in ('111BA5E','111BA72','111BA73','111BA74','111BA75') if tuple(round(v,4) for v in src.entitydb[h].dxf.insert) not in existing]
   imp=Importer(src,doc);imp.import_entities(entities);imp.finalize();print('Restored original 1100 form',fn,len(entities))
  else:
   bad=[e for e in doc.modelspace().query('INSERT') if 'Ổ CẮM CN' in e.dxf.name];[doc.modelspace().delete_entity(e) for e in bad];print('Removed sockets from selected 900 form',fn,len(bad));assert not any('Ổ CẮM CN' in e.dxf.name for e in doc.modelspace().query('INSERT'))
  doc.saveas(folder/fn)
  if fn=='ban_ve_co_khung_goc.dxf':render(doc,folder/'xem_truoc.svg')
 r.pop('confirmed_device_exclusions',None);save(folder/'thong_tin.json',r)
save(OUT/'catalog.json',d)
