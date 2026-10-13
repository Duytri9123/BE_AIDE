"""Restore supplier dynamic states exported by AutoCAD, including native ACIS."""
import json,logging,re,shutil,os,subprocess
from pathlib import Path
import ezdxf
from ezdxf import bbox,transform
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page
from ezdxf.addons.drawing.properties import LayoutProperties
logging.disable(logging.CRITICAL)
base=Path(__file__).resolve().parents[1];root=base/'data/CatalogTB';w=base/'tmp/accessory_source_review'
rows=json.loads((w/'front-state-jobs.json').read_text(encoding='utf-8'));jobs=[]
rows=[row for row in rows if not ((root/row['profile']).parent/'CadDon'/row['view']/'native_preview.json').exists()
      or json.loads(((root/row['profile']).parent/'CadDon'/row['view']/'native_preview.json').read_text(encoding='utf-8')).get('state')!=row['option']]
if not rows:
 print('All requested native states already restored');raise SystemExit(0)
inventory_path=w/'supplier-inventory.json'
inventory={r['handle']:r for r in json.loads(inventory_path.read_text(encoding='utf-8-sig'))} if inventory_path.exists() else {}
for row in rows:
 source=w/(row['view']+'-native-state.dxf');assert source.with_suffix(source.suffix+'.ok').read_text()==row['option']
 doc=ezdxf.readfile(source);ins=list(doc.modelspace().query('INSERT'));assert len(ins)==1
 ext=bbox.extents(doc.modelspace(),fast=True);assert ext.has_data
 folder=(root/row['profile']).parent/'CadDon'/row['view'];backup=w/'before-native-state-restoration'/folder.parent.parent.name/row['view']
 if not backup.exists():shutil.copytree(folder,backup)
 transform.translate(doc.modelspace(),(-ext.center.x,-ext.center.y,0));doc.units=4;doc.saveas(folder/'ban_ve.dxf')
 shutil.copy2(source,folder.parent.parent/'HinhChieu'/row['view']/'ban_ve.dxf')
 meta_path=folder.parent.parent/'HinhChieu'/row['view']/'thong_tin.json'
 meta=json.loads(meta_path.read_text(encoding='utf-8'))
 attrs={k.upper():v for k,v in inventory.get(row['handle'],{}).get('attributes',{}).items()}
 if attrs.get('BRAND0'):attrs.setdefault('ORIGIN',attrs['BRAND0'])
 if attrs.get('TYPE0'):attrs.setdefault('TYPE',attrs['TYPE0'])
 if 'POLES' in attrs and row['option'].split(':')[0].upper() not in attrs['POLES'].upper():attrs.pop('POLES')
 meta.update(source_attributes=attrs,source_handle=row['handle'],source_state_verified=True,trang_thai_block=row['option'],kich_thuoc_hinh_mm={'ngang':round(ext.size.x,3),'cao':round(ext.size.y,3)})
 meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
 jobs.append((folder,w/(row['view']+'-state-preview.dxf')))
(w/'preview-jobs.txt').write_text('\n'.join(str(f/'ban_ve.dxf')+'\t'+str(o) for f,o in jobs),encoding='utf-8')
env=os.environ.copy();env['AIDE_PREVIEW_JOBS']=str(w/'preview-jobs.txt')
with (w/'state-preview.log').open('wb') as log:subprocess.run(['C:/Program Files/Autodesk/AutoCAD 2022/accoreconsole.exe','/i',str(w/'input.dwg'),'/s',str(w/'regions.scr'),'/l','en-US'],env=env,stdout=log,stderr=log,timeout=240,creationflags=subprocess.CREATE_NO_WINDOW)
for row,(folder,output) in zip(rows,jobs):
 doc=ezdxf.readfile(output)
 # Native masks can cover subsequent strokes in SVG. Omit masks in memory
 # for the preview only; downloadable CAD retains the original WIPEOUTs.
 for block in doc.blocks:
  for mask in list(block.query('WIPEOUT')):block.delete_entity(mask)
 backend=SVGBackend();Frontend(RenderContext(doc),backend).draw_layout(doc.modelspace(),layout_properties=LayoutProperties('Model','#212830','#ffffff',units=4,dark_background=True))
 svg=re.sub(r'(stroke-width: )(\d+)',lambda m:m[1]+str(max(1500,int(m[2]))),backend.get_string(Page(0,0)))
 (folder/'xem_truoc.svg').write_text(svg,encoding='utf-8');shutil.copy2(folder/'xem_truoc.svg',folder.parent.parent/'HinhChieu'/row['view']/'xem_truoc.svg')
 (folder/'native_preview.json').write_text(json.dumps({'renderer':'AutoCAD native dynamic state and REGION outlines','state':row['option'],'regions':int(output.with_suffix(output.suffix+'.count').read_text())}),encoding='utf-8')
 p=root/row['profile'];data=json.loads(p.read_text(encoding='utf-8'))
 if data.get('cad_chen_tu',{}).get('id_hinh_goc')==row['view']:
  for filename in ('ban_ve.dxf','xem_truoc.svg'):shutil.copy2(folder/filename,p.parent/'CadChenTu'/filename)
 print(row['view'],row['option'],flush=True)
