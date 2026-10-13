"""Exercise every converted view through the portable insertion path."""
import json,sys,logging
from pathlib import Path
import ezdxf
from ezdxf.disassemble import recursive_decompose
from ezdxf.addons import Importer
BASE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BASE));sys.stdout.reconfigure(encoding='utf8')
logging.disable(logging.CRITICAL)
from app.services.cad.catalogtb_assets import insertion_source
OUT=BASE.parent/'outputs/catalogtb-linework-audit'
report=json.loads((OUT/'all-region-insertions.json').read_text(encoding='utf8'));results=[]
for i,r in enumerate(report['results'],1):
 row={'profile':r['profile'],'view':r['view']}
 try:
  original=BASE/'data/CatalogTB'/Path(r['profile']).parent/'CadDon'/r['view']/'ban_ve.dxf'
  doc=ezdxf.readfile(insertion_source(original))
  assert not any(e.dxftype()=='REGION' for b in doc.blocks for e in b),'Unconverted nested REGION remains'
  target=ezdxf.new('R2018');target.units=doc.units
  importer=Importer(doc,target);importer.import_entities(list(recursive_decompose(doc.modelspace())));importer.finalize()
  assert len(target.modelspace()),'Portable insertion is empty'
  audit=target.audit();assert not audit.errors,[(e.code,e.message) for e in audit.errors]
  row.update(passed=True,insert_entities=len(target.modelspace()),units=target.units)
 except Exception as e:row.update(passed=False,error=str(e))
 results.append(row)
 if i%50==0:print('Verified',i,'/',len(report['results']),flush=True)
summary={'views':len(results),'passed':sum(r['passed'] for r in results),'failed':sum(not r['passed'] for r in results),'native_dwg_visual_equivalence_verified':False}
(OUT/'insertion-verification.json').write_text(json.dumps({'summary':summary,'results':results},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(summary),flush=True)
if summary['failed']:raise SystemExit(1)
