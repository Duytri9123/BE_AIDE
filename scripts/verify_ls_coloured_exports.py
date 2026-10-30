from pathlib import Path
import json,io,hashlib,collections,sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from app.services.cad.ls_colored_views import colored_dxf
from app.services.cad.device_block_export import native_visibility_insert
root=Path('data/CatalogTB');out=Path('docs/ls-all-cad-2026-10-24');snapshot=json.loads((root/'_agent_index/browser_display_v5.json').read_text(encoding='utf8'));measure=json.loads(Path('app/data/catalog_customer_cad_measurements.json').read_text(encoding='utf8'))['views'];rows=[];seen={}
def signatures(doc):
 return [(block.name,[(e.dxftype(),str({k:v for k,v in e.dxf.all_existing_dxf_attribs().items() if k not in ('color','true_color')})) for e in block]) for block in doc.blocks]
for d in snapshot['items']:
 if d.get('brand') not in ('LS','LS Electric'):continue
 for v in d['views']:
  m=measure[d['id']+':'+v['id']];path=root/m['path'];raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
  if sha not in seen:
   before=ezdxf.read(io.StringIO(raw.decode('utf-8-sig'),newline=None));result=colored_dxf(raw);after=ezdxf.read(io.StringIO(result.decode('utf8'),newline=None));assert signatures(before)==signatures(after),(d['id'],v['id'],'Source geometry/style changed beyond colours');assert after.units==before.units==4;assert not after.audit().errors
   native=native_visibility_insert(before)
   if native:assert native_visibility_insert(after)
   colours=collections.Counter(e.dxf.get('true_color') for block in after.blocks for e in block if e.dxf.hasattr('true_color'))
   assert colours,(d['id'],v['id'],'No coloured linework')
   seen[sha]={'native_visibility_preserved':native,'coloured_entities':sum(colours.values()),'output_sha256':hashlib.sha256(result).hexdigest()}
  rows.append({'catalog_id':d['id'],'view_id':v['id'],'source_sha256':sha,**seen[sha]})
  if len(rows)%50==0:print('CHECKED',len(rows),'views',flush=True)
(out/'all-ls-colour-validation.json').write_text(json.dumps({'views':len(rows),'unique_sources':len(seen),'geometry_units_layers_lineweights_unchanged':True,'items':rows},ensure_ascii=False,indent=2),encoding='utf8');print('ALL COLOUR CHECKS PASSED',len(rows),flush=True)
