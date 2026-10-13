"""Rebuild native preview images without SVG masking artifacts; preserve CAD."""
import json,re,shutil,logging
from pathlib import Path
import ezdxf
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page
from ezdxf.addons.drawing.properties import LayoutProperties
logging.disable(logging.CRITICAL)
base=Path(__file__).resolve().parents[1];root=base/'data/CatalogTB';w=base/'tmp/accessory_source_review';rows=[]
for name in ['all-ls-state-jobs.json','other-brand-state-jobs.json']:rows+=json.loads((w/name).read_text(encoding='utf-8'))
count=0;report=[]
for row in rows:
 folder=(root/row['profile']).parent/'CadDon'/row['view'];output=w/(row['view']+'-state-preview.dxf')
 assert output.exists(),output
 doc=ezdxf.readfile(output);masks=0
 for block in doc.blocks:
  for e in list(block.query('WIPEOUT')):block.delete_entity(e);masks+=1
 if not masks:continue
 backend=SVGBackend();Frontend(RenderContext(doc),backend).draw_layout(doc.modelspace(),layout_properties=LayoutProperties('Model','#212830','#ffffff',units=4,dark_background=True))
 svg=re.sub(r'(stroke-width: )(\d+)',lambda m:m[1]+str(max(1500,int(m[2]))),backend.get_string(Page(0,0)))
 (folder/'xem_truoc.svg').write_text(svg,encoding='utf-8');shutil.copy2(folder/'xem_truoc.svg',folder.parent.parent/'HinhChieu'/row['view']/'xem_truoc.svg')
 p=root/row['profile'];data=json.loads(p.read_text(encoding='utf-8'))
 if data.get('cad_chen_tu',{}).get('id_hinh_goc')==row['view']:shutil.copy2(folder/'xem_truoc.svg',p.parent/'CadChenTu/xem_truoc.svg')
 count+=1;report.append({**row,'preview_masks_omitted':masks})
 if count%20==0:print('Fixed preview masks:',count,flush=True)
(root/'kiem_tra_loi_lop_che_anh_cad.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print('Fixed native preview masks:',count)
