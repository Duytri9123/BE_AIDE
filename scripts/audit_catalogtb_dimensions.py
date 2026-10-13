"""Record original CAD envelopes without changing geometry or inferring depth."""
import json, math, logging
from collections import Counter
from pathlib import Path
import ezdxf
from ezdxf import bbox
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.cad.catalogtb_assets import normalized_source
logging.getLogger('ezdxf').setLevel(logging.ERROR)

ROOT=Path(__file__).resolve().parents[1]/'data/CatalogTB'
OUT=ROOT.parents[2]/'outputs/catalogtb-dimension-audit'
OUT.mkdir(parents=True,exist_ok=True)
rows=[]
for profile in sorted(ROOT.rglob('thong_tin_thiet_bi.json')):
    data=json.loads(profile.read_text(encoding='utf8'))
    for view in data.get('cad_don',[]):
        row={'profile':profile.relative_to(ROOT).as_posix(),'view':view['id_hinh_goc'],'face':view.get('huong_nhin'),'findings':[]}
        try:
            drawing=profile.parent/view['duong_dan']
            doc=ezdxf.readfile(normalized_source(drawing))
            box=bbox.extents(doc.modelspace(),fast=True,cache=bbox.Cache())
            row['units']=doc.units
            row['unit_verification']=view.get('unit_verification') or {}
            if doc.units!=4:row['findings'].append('UNITS_NOT_MM')
            if not box.has_data:row['findings'].append('NO_COMPUTABLE_ENVELOPE')
            else:
                row['cad_envelope']={'x':box.size.x,'y':box.size.y,'z':box.size.z}
                if not all(math.isfinite(v) and v>0 for v in [box.size.x,box.size.y]):row['findings'].append('INVALID_2D_ENVELOPE')
            if 'Chưa' in (row['face'] or ''):row['findings'].append('FACE_UNRESOLVED')
            row['readable']=True
        except Exception as exc:
            row.update(readable=False,error=str(exc)[:200]);row['findings'].append('READ_FAILURE')
        rows.append(row)
        if len(rows)%200==0:print('Measured',len(rows),flush=True)
report={'summary':{'profiles':len(list(ROOT.rglob('thong_tin_thiet_bi.json'))),'views':len(rows),'readable':sum(r['readable'] for r in rows),'findings':dict(Counter(f for r in rows for f in r['findings']))},'views':rows,'limitations':['CAD envelope may include annotation and hidden entities; it is not a verified mounting envelope.','Zero Z in a 2D face is not physical depth.','Manufacturer dimensions must be paired with the correct face and model; approximate brand does not authorize resizing.']}
(OUT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report['summary']),flush=True)
