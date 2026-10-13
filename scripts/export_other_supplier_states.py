import json,re,os,subprocess
from pathlib import Path
base=Path.cwd();root=base/'data/CatalogTB';w=base/'tmp/accessory_source_review';inventory=json.loads((w/'supplier-inventory.json').read_text(encoding='utf-8-sig'));rows=[];unmatched=[]
for item in inventory:
 attrs={k.upper():v for k,v in item['attributes'].items()};attrs.setdefault('ORIGIN',attrs.get('BRAND0'));attrs.setdefault('TYPE',attrs.get('TYPE0'));item['attributes']=attrs
slug=lambda s:re.sub('[^A-Z0-9]+','-',s.upper()).strip('-')
for brand in ['Schneider','ABB','Mitsubishi','Shihlin','Chint']:
 for p in (root/brand).rglob('thong_tin_thiet_bi.json'):
  d=json.loads(p.read_text(encoding='utf-8'));code=d.get('ma_dong_san_pham');code='ilDK' if code=='iIDK' else code
  candidates=[x for x in inventory if {k.upper():v for k,v in x['attributes'].items()}.get('ORIGIN')==brand and {k.upper():v for k,v in x['attributes'].items()}.get('TYPE')==code]
  if len(candidates)!=1:unmatched.append(str(p.relative_to(root)));continue
  src=candidates[0];allowed=src['properties'].get('Options',{}).get('allowed',[])
  for v in d.get('cad_don',[]):
   f=p.parent/'HinhChieu'/v['id_hinh_goc']/'thong_tin.json'
   if not f.exists():continue
   m=json.loads(f.read_text(encoding='utf-8'));options=[s for s in allowed if s==m.get('trang_thai_block') or v['id_hinh_goc'].endswith('-STATE-'+slug(s)) or v['id_hinh_goc'].endswith('-VIEW-'+slug(s))]
   if len(options)==1:rows.append({'profile':str(p.relative_to(root)),'view':v['id_hinh_goc'],'option':options[0],'handle':src['handle']})
(w/'other-brand-state-jobs.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8');print('Matched',len(rows),'views',flush=True)
(w/'other-state-jobs.txt').write_text('\n'.join(r['handle']+'\t'+r['option']+'\t'+str(w/(r['view']+'-native-state.dxf')) for r in rows if not (w/(r['view']+'-native-state.dxf.ok')).exists()),encoding='utf-8')
env=os.environ.copy();env['AIDE_STATE_JOBS']=str(w/'other-state-jobs.txt')
with (w/'other-states.log').open('wb') as log:subprocess.run(['C:/Program Files/Autodesk/AutoCAD 2022/accoreconsole.exe','/i',str(w/'input.dwg'),'/s',str(w/'states.scr'),'/l','en-US'],env=env,stdout=log,stderr=log,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
valid=[r for r in rows if (w/(r['view']+'-native-state.dxf.ok')).exists()];(w/'front-state-jobs.json').write_text(json.dumps(valid,ensure_ascii=False,indent=2),encoding='utf-8');print('Verified',len(valid))

