from pathlib import Path
import json,hashlib,io,collections,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from app.services.cad.layer_resource_links import repair_invalid_layer_resources
from app.services.cad.device_block_export import single_device_block
root=Path('data/CatalogTB');report=Path('docs/ls-all-cad-2026-10-24');mp=root/'_agent_index/ls_device_exports/manifest.json';manifest=json.loads(mp.read_text(encoding='utf8'));vp=report/'new-source-validation.json';validation=json.loads(vp.read_text(encoding='utf8'));cachep=Path('app/data/catalog_customer_cad_measurements.json');cache=json.loads(cachep.read_text(encoding='utf8'));repairs=[]
def sig(d):return [(e.dxftype(),str({k:v for k,v in e.dxf.all_existing_dxf_attribs().items() if k not in ('owner','handle')})) for e in d.modelspace()]
for p in (root/'LS/ThietBi').glob('OFFICIAL-RU-*/thong_tin_thiet_bi.json'):
 data=json.loads(p.read_text(encoding='utf8'));dirty=False
 if data.get('browser_hidden'):continue
 cid='TB-'+hashlib.sha1(p.relative_to(root).as_posix().encode()).hexdigest()[:16]
 for v in data['cad_don']:
  f=p.parent/v['duong_dan'];raw=f.read_bytes();d=ezdxf.readfile(f);before=sig(d);n=repair_invalid_layer_resources(d)
  if not n:continue
  backup=report/'layer-resource-before'/f.relative_to(root);backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(raw);old=hashlib.sha256(raw).hexdigest();d.saveas(f);after=hashlib.sha256(f.read_bytes()).hexdigest();assert before==sig(ezdxf.readfile(f));v['unit_verification']['sha256']=after;dirty=True
  for name in ('evidence.json','thong_tin_cad_chen.json'):
   ep=f.with_name(name);ev=json.loads(ep.read_text(encoding='utf8'));(ev['evidence'] if name.startswith('thong') else ev)['sha256']=after;ep.write_text(json.dumps(ev,ensure_ascii=False,indent=2),encoding='utf8')
  cache['views'][cid+':'+v['id_hinh_goc']]['sha256']=after
  for row in manifest['items']:
   if row['source_sha256']!=old:continue
   output=single_device_block(f.read_bytes(),cid+'-'+hashlib.sha256(v['id_hinh_goc'].encode()).hexdigest()[:16]);(root/row['export_path']).write_bytes(output);row['source_sha256']=after;row['export_sha256']=hashlib.sha256(output).hexdigest()
  for row in validation['items']:
   if row['source_sha256']==old:row['source_sha256']=after;row['export_sha256']=hashlib.sha256((root/row['export_path']).read_bytes()).hexdigest()
  repairs.append({'catalog_id':cid,'view_id':v['id_hinh_goc'],'pointers_rebound':n,'source_before':old,'source_after':after,'geometry_colors_layers_lineweights_unchanged':True})
 if dirty:p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
for p,data in [(mp,manifest),(vp,validation),(cachep,cache)]:p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
(report/'layer-resource-repair.json').write_text(json.dumps({'views':len(repairs),'items':repairs},ensure_ascii=False,indent=2),encoding='utf8');print('Repaired',len(repairs),'source faces without changing entities',flush=True)
