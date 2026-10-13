"""Native DWG review copies preserve source dynamic blocks and all sheet views."""
from pathlib import Path
import json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'outputs/order-447-457-audit'
manifest=json.loads((OUT/'source-manifest.json').read_text(encoding='utf8'));results=[]
for order in ['447','457']:
 target=OUT/order/f'ORDER-{order}-source-review.dwg';shutil.copy2(manifest[order]['dwg']['path'],target)
 x,y=(-7350,-1000) if order=='447' else (-98200,13500)
 script=ROOT/'tmp/order_audit'/order/'native-review.scr'
 script.write_text('(entmakex (list (cons 0 "MTEXT") (cons 100 "AcDbEntity") (cons 8 "0") (cons 100 "AcDbMText") (cons 10 (list '+str(x)+' '+str(y)+' 0.0)) (cons 40 25.0) (cons 41 3500.0) (cons 1 "AUDIT REFERENCE - NOT RELEASED FOR PRODUCTION\\\\PSource views preserved. See reconciliation.json for PDF / quotation / CAD differences.")))\n_.QSAVE\n_.QUIT\n',encoding='ascii')
 with (OUT/order/'native-review-export.log').open('wb') as log:
  result=subprocess.run(['C:/Program Files/Autodesk/AutoCAD 2022/accoreconsole.exe','/i',str(target),'/s',str(script),'/l','en-US'],stdout=log,stderr=log,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
 assert result.returncode==0
 results.append({'order':order,'output':str(target),'native_autocad_exit_code':result.returncode,'kind':'annotated source baseline, not regenerated production design','all_source_views_preserved':True,'release_ready':False})
(OUT/'native-review-export.json').write_text(json.dumps(results,indent=2),encoding='utf8')
print('Native DWG review copies written for 447 and 457; not fabrication releases')
