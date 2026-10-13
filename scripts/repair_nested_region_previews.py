"""Rebuild previews where one-level REGION conversion previously lost edges."""
import sys,json,re,shutil,logging,hashlib
from pathlib import Path
import ezdxf
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page
from ezdxf.addons.drawing.properties import LayoutProperties
BASE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BASE));sys.stdout.reconfigure(encoding='utf8');logging.disable(logging.CRITICAL)
from app.services.cad.catalogtb_assets import insertion_source
ROOT=BASE/'data/CatalogTB';OUT=BASE.parent/'outputs/catalogtb-linework-audit'
rows=[r for r in json.loads((OUT/'insertion-verification-first-pass.json').read_text(encoding='utf8'))['results'] if not r['passed']]
results=[]
for i,r in enumerate(rows,1):
 p=ROOT/r['profile'];folder=p.parent/'CadDon'/r['view'];doc=ezdxf.readfile(insertion_source(folder/'ban_ve.dxf'))
 assert not any(e.dxftype()=='REGION' for b in doc.blocks for e in b),r['view']
 for b in doc.blocks:
  for mask in list(b.query('WIPEOUT')):b.delete_entity(mask)
 backend=SVGBackend();Frontend(RenderContext(doc),backend).draw_layout(doc.modelspace(),layout_properties=LayoutProperties('Model','#212830','#ffffff',units=4,dark_background=True))
 svg=re.sub(r'(stroke-width: )(\d+)',lambda m:m[1]+str(max(1500,int(m[2]))),backend.get_string(Page(0,0)))
 preview=folder/'xem_truoc.svg';backup=OUT/'before-nested'/hashlib.sha1(r['profile'].encode()).hexdigest()/r['view'];backup.mkdir(parents=True,exist_ok=True)
 shutil.copy2(preview,backup/'xem_truoc.svg');preview.write_text(svg,encoding='utf8')
 companion=p.parent/'HinhChieu'/r['view']/'xem_truoc.svg'
 if companion.parent.exists():shutil.copy2(preview,companion)
 data=json.loads(p.read_text(encoding='utf8'))
 if data.get('cad_chen_tu',{}).get('id_hinh_goc')==r['view']:shutil.copy2(preview,p.parent/'CadChenTu/xem_truoc.svg')
 results.append({**r,'preview_rebuilt':True,'before_svg':str(backup/'xem_truoc.svg'),'after_svg':str(preview)})
 if i%10==0:print('Rebuilt nested previews',i,'/',len(rows),flush=True)
(OUT/'nested-preview-repairs.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
print('Rebuilt',len(results),'nested REGION previews',flush=True)
