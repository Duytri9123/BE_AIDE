import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json,hashlib
from pathlib import Path
from app.services.cad.ls_native_visibility import device_visibility_dxf
from app.services.cad.ls_view_coverage import is_ls
from app.services.catalog_publication_policy import public_device_allowed
from app.services.cad.device_block_export import native_visibility_insert
import ezdxf,io,collections
root=Path('data/CatalogTB');s=json.loads((root/'_agent_index/browser_display_v5.json').read_text(encoding='utf8'));measure=json.loads(Path('app/data/catalog_customer_cad_measurements.json').read_text(encoding='utf8'))['views'];out=Path('tmp/ls-visibility/batch');out.mkdir(exist_ok=True);report=[]
report_path=Path('docs/ls-all-cad-2026-10-24/native-visibility-batch.json')
previous=json.loads(report_path.read_text(encoding='utf8')) if report_path.exists() else {}
previous_rows={(r['catalog_id'],r['variant_id']):r for r in previous.get('items',[])}
generator_sha=hashlib.sha256(b''.join(Path(p).read_bytes() for p in ['app/services/cad/ls_native_visibility.py','app/services/cad/layer_resource_links.py','scripts/resources/ls_visibility_template.dxf'])).hexdigest()
for d in s['items']:
 if not is_ls(d.get('brand')) or not public_device_allowed(d):continue
 groups=collections.defaultdict(list)
 for v in d['views']:groups[v.get('cad_variant_id') or d['id']].append(v)
 for key,vs in groups.items():
  if not all(d['id']+':'+v['id'] in measure for v in vs):continue
  sources={v['id']:(root/measure[d['id']+':'+v['id']]['path']).read_bytes() for v in vs}
  if all(b'BLOCKVISIBILITYPARAMETER' in x for x in sources.values()):continue
  path=out/(d['id']+'-'+key+'.dxf')
  hashes=[hashlib.sha256(sources[v['id']]).hexdigest() for v in vs]
  old=previous_rows.get((d['id'],key),{})
  cached=path.read_bytes() if path.exists() else None
  valid=(cached and previous.get('generator_sha256')==generator_sha and old.get('source_sha256s')==hashes and old.get('export_sha256')==hashlib.sha256(cached).hexdigest())
  result=cached if valid else device_visibility_dxf(d,vs[0]['id'],sources.__getitem__)
  if not result:print('HELD',d['id'],key,len(vs),flush=True);continue
  doc=ezdxf.read(io.StringIO(result.decode()));assert native_visibility_insert(doc) and not doc.audit().errors
  path=out/(d['id']+'-'+key+'.dxf');path.write_bytes(result)
  report.append({'catalog_id':d['id'],'variant_id':key,'faces':len(vs),'file':str(path.resolve()),'source_sha256s':hashes,'view_ids':[v['id'] for v in vs],'export_sha256':hashlib.sha256(result).hexdigest()})
  print('BUILT',len(report),d['id'],len(vs),flush=True)
report_path.write_text(json.dumps({'generator_sha256':generator_sha,'groups':len(report),'faces':sum(r['faces'] for r in report),'items':report},ensure_ascii=False,indent=2),encoding='utf8')
