"""Audit every declared device view, without changing source geometry."""
import json, sys
from pathlib import Path
from collections import Counter
import ezdxf
BASE=Path(__file__).resolve().parents[1];ROOT=BASE/'data/CatalogTB'
OUT=BASE.parent/'outputs/catalogtb-linework-audit';OUT.mkdir(exist_ok=True)
sys.stdout.reconfigure(encoding='utf8')
rows=[]
for p in ROOT.rglob('thong_tin_thiet_bi.json'):
 data=json.loads(p.read_text(encoding='utf8'))
 for v in data.get('cad_don',[]):
  path=p.parent/v['duong_dan'];folder=path.parent
  row={'profile':p.relative_to(ROOT).as_posix(),'name':data.get('ten_san_pham'), 'view':v['id_hinh_goc'],'path':str(path),'findings':[]}
  try:
   d=ezdxf.readfile(path)
   types=Counter(e.dxftype() for b in d.blocks for e in b)
   row['entity_types']=dict(types)
   row['hidden_entities']=sum(bool(e.dxf.get('invisible',0)) for b in d.blocks for e in b)
   row['hidden_nested_inserts']=sum(bool(e.dxf.get('invisible',0)) for b in d.blocks for e in b.query('INSERT'))
   marker=folder/'native_preview.json'
   native=json.loads(marker.read_text()) if marker.exists() else {}
   row['native_preview']=native
   if types['REGION'] and not native:row['findings'].append('REGION_WITHOUT_NATIVE_PREVIEW')
   if types['3DSOLID'] or types['BODY'] or types['SURFACE']:row['findings'].append('ACIS_REQUIRES_NATIVE_RENDER')
   if row['hidden_nested_inserts']:row['findings'].append('HIDDEN_NESTED_VARIANTS_REQUIRE_SOURCE_COMPARISON')
   svg=folder/'xem_truoc.svg'
   row['preview_exists']=svg.exists()
   if not svg.exists():row['findings'].append('NO_SVG_PREVIEW')
   row['readable']=True
  except Exception as e:row.update(readable=False,error=str(e));row['findings'].append('DXF_READ_FAILURE')
  rows.append(row)
  if len(rows)%100==0:print('Audited',len(rows),flush=True)
report={'summary':{'profiles':len(list(ROOT.rglob('thong_tin_thiet_bi.json'))),'views':len(rows),'readable':sum(r['readable'] for r in rows),'findings':dict(Counter(f for r in rows for f in r['findings']))},'views':rows,'limitations':['Hidden variants are not proof of missing linework; do not unhide all entities.','Native DWG visual equivalence is not established by successful DXF parsing.']}
(OUT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report['summary'],ensure_ascii=False),flush=True)
