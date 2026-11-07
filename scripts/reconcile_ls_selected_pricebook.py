"""Remove superseded LS offers from reviewed CAD browsing associations."""
import hashlib,json,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.services.ai.manufacturer_registry import canonical_brand
from app.services.published_catalog_information import apply_published_information,published_information
from app.services.pricebook_authority import published_row_allowed
from app.services.catalogtb_browser import _build_browser_data
CAT=ROOT/'data/CatalogTB'


def main():
 rows=[r for r in json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'] if canonical_brand(r.get('brand'))=='LS Electric']
 allowed={r['id'] for r in rows if published_row_allowed(r)};assert len(allowed)==517
 overlay_path=ROOT/'app/data/catalogtb_published_information.json';overlay=json.loads(overlay_path.read_text(encoding='utf8'));information=published_information()
 removed=0;changed=0;paths=list((CAT/'LS').rglob('thong_tin_thiet_bi.json'))
 for p in paths:
  raw=json.loads(p.read_text(encoding='utf8'));relative=p.relative_to(CAT).as_posix();current=apply_published_information(raw,relative,information)
  refs=dict(current.get('catalog_tham_khao') or {});options=refs.get('options',[])
  kept=[o for o in options if canonical_brand(o.get('brand') or 'LS Electric')!='LS Electric' or o.get('source_row_id') in allowed]
  if len(kept)==len(options):continue
  removed+=len(options)-len(kept);changed+=1;refs['options']=kept;raw['catalog_tham_khao']=refs
  p.write_text(json.dumps(raw,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
  cid='TB-'+hashlib.sha1(relative.encode()).hexdigest()[:16]
  overlay['profiles'].setdefault(cid,{})['catalog_tham_khao']=refs
  if relative in overlay['profiles']:overlay['profiles'][relative]['catalog_tham_khao']=refs
 pending=overlay_path.with_suffix('.tmp');pending.write_text(json.dumps(overlay,ensure_ascii=False,indent=2),encoding='utf8');pending.replace(overlay_path)
 ls_ids={'TB-'+hashlib.sha1(p.relative_to(CAT).as_posix().encode()).hexdigest()[:16] for p in paths}
 removed_maps={}
 for name,key in [('pricebook_library_links.json','links'),('library_price_options.json','options')]:
  p=ROOT/'app/data'/name
  if not p.is_file():continue
  data=json.loads(p.read_text(encoding='utf8'));entries=data.get(key,[])
  kept=[o for o in entries if o.get('equipment_catalog_id') not in ls_ids or o.get('price_row_id') in allowed]
  removed_maps[name]=len(entries)-len(kept)
  if len(kept)!=len(entries):
   data[key]=kept;pending=p.with_suffix('.tmp');pending.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8');pending.replace(p)
 # Rebuild the LS display from durable profile metadata, retaining the other
 # manufacturers' current snapshot records and their CAD associations.
 original=Path.rglob
 def limited(self,pattern,*args,**kw):return iter(paths) if self==CAT and pattern=='thong_tin_thiet_bi.json' else original(self,pattern,*args,**kw)
 with patch.object(Path,'rglob',limited):rebuilt=_build_browser_data()
 snapshot_path=CAT/'_agent_index/browser_display_v5.json';snapshot=json.loads(snapshot_path.read_text(encoding='utf8'))
 snapshot['items']=[d for d in snapshot['items'] if canonical_brand(d.get('brand'))!='LS Electric']+rebuilt['items']
 snapshot['total']=len(snapshot['items']);snapshot['view_count']=sum(len(d['views']) for d in snapshot['items'])
 snapshot['categories']=[{'name':name,'count':sum(d['category']==name for d in snapshot['items'])} for name in sorted({d['category'] for d in snapshot['items']})]
 pending=snapshot_path.with_suffix('.tmp');pending.write_text(json.dumps(snapshot,ensure_ascii=False),encoding='utf8');pending.replace(snapshot_path)
 report={'checked_on':'2026-11-06','exclusive_ls_rows':len(allowed),'profiles_with_removed_references':changed,'superseded_reference_options_removed':removed,'superseded_mapping_rows_removed':removed_maps,'published_ls_profiles':len(rebuilt['items']),'published_ls_views':sum(len(d['views']) for d in rebuilt['items'])}
 (ROOT/'app/data/ls_pricebook_reconciliation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(report),flush=True)

if __name__=='__main__':main()
