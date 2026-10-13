"""Native ACIS outlines for previews only. Downloadable CAD remains untouched."""
import os,subprocess,json,re,shutil,logging
from pathlib import Path
import ezdxf
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page
from ezdxf.addons.drawing.properties import LayoutProperties
logging.disable(logging.CRITICAL)
base=Path(__file__).resolve().parents[1];root=base/'data/CatalogTB';work=base/'tmp/accessory_source_review'
records=json.loads((root/'LS/kiem_tra_khoi_dong_dau_noi_goc.json').read_text(encoding='utf-8'))
jobs=[]
for row in records:
    folder=(root/row['profile']).parent/'CadDon'/row['view'];output=work/(row['view']+'-preview.dxf')
    jobs.append((folder,output))
(work/'preview-jobs.txt').write_text('\n'.join(str(folder/'ban_ve.dxf')+'\t'+str(output) for folder,output in jobs),encoding='utf-8')
script=work/'regions.scr';script.write_text('SECURELOAD\n0\n_.NETLOAD\n'+(work/'PreviewRegions.dll').as_posix()+'\nAIDEPREVIEWREGIONS\n_.QUIT\n_Y\n',encoding='ascii')
env=os.environ.copy();env['AIDE_PREVIEW_JOBS']=str(work/'preview-jobs.txt')
with (work/'preview-regions.log').open('wb') as log:
    result=subprocess.run(['C:/Program Files/Autodesk/AutoCAD 2022/accoreconsole.exe','/i',str(work/'input.dwg'),'/s',str(script),'/l','en-US'],env=env,stdout=log,stderr=log,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
for folder,output in jobs:
    assert output.is_file(), 'Native region rendering failed: see preview-regions.log'
    doc=ezdxf.readfile(output);backend=SVGBackend()
    Frontend(RenderContext(doc),backend).draw_layout(doc.modelspace(),layout_properties=LayoutProperties('Model','#212830','#ffffff',units=4,dark_background=True))
    svg=re.sub(r'(stroke-width: )(\d+)',lambda m:m[1]+str(max(1500,int(m[2]))),backend.get_string(Page(0,0)))
    (folder/'xem_truoc.svg').write_text(svg,encoding='utf-8')
    shutil.copy2(folder/'xem_truoc.svg',folder.parent.parent/'HinhChieu'/folder.name/'xem_truoc.svg')
    (folder/'native_preview.json').write_text(json.dumps({'renderer':'AutoCAD REGION outlines','regions':int(output.with_suffix(output.suffix+'.count').read_text()),'download_geometry_unchanged':True}),encoding='utf-8')
    print(folder.name,'native regions:',output.with_suffix(output.suffix+'.count').read_text(),flush=True)
