"""Plan/apply evidenced price-to-CAD links across all priced manufacturers."""
import collections,csv,hashlib,json,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.catalog_price_geometry_links import family_link
from app.services.ai.manufacturer_registry import canonical_brand
from app.services.catalog_view_health import source_displayable
from scripts.ls_native_writer import price_option
ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB';OUT=ROOT/'docs/all-brands-price-cad-links-2026-10-22'
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
def main():
 OUT.mkdir(exist_ok=True);snapshot=json.loads((CAT/'_agent_index/browser_display_v5.json').read_text(encoding='utf8'));devices={d['id']:d for d in snapshot['items'] if d.get('brand') and d.get('views')}
 for d in list(devices.values()):
  for cid in d.get('member_profile_ids',[]):devices.setdefault(cid,d)
 rows=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'];bybrand=collections.defaultdict(list)
 for row in rows:bybrand[canonical_brand(row['brand'])].append(row)
 existing=set();profiles=[]
 for p in CAT.rglob('thong_tin_thiet_bi.json'):
  rel=p.relative_to(CAT).as_posix();cid='TB-'+hashlib.sha1(rel.encode()).hexdigest()[:16]
  if cid not in devices:continue
  raw=json.loads(p.read_text(encoding='utf-8-sig'))
  if raw.get('browser_hidden'):continue
  device=devices[cid];profiles.append((p,rel,cid,raw,device))
  existing.update(o['source_row_id'] for o in (raw.get('catalog_tham_khao') or {}).get('options',[]) if o.get('source_row_id') and canonical_brand(o.get('brand'))==canonical_brand(device.get('brand')))
 candidates=collections.defaultdict(list);held=[];validated={}
 for p,rel,cid,raw,d in profiles:
  for row in bybrand[canonical_brand(d['brand'])]:
   if row['id'] in existing:continue
   match=family_link(raw,d,row)
   if match:
    reason=None
    if canonical_brand(d['brand'])=='Shihlin':reason='Suffix/frame variant requires manufacturer dimensional evidence'
    if match['source_model'] in {'LRD21','LRD14','CVS400'}:reason='Conflicting price current or multiple CAD variants require individual review'
    if row['sku']=='A9C20731':reason='Modular contactor configuration requires individual dimensional review'
    if canonical_brand(d['brand'])=='Mitsubishi Electric' and row['category']=='CONTACTOR':reason='Built-in auxiliary contact variant requires individual dimensional review'
    if reason:
     held.append({'price_row_id':row['id'],'profile':rel,'reason':reason});continue
    if rel not in validated:validated[rel]=bool(raw.get('cad_don')) and all(source_displayable(v,p) for v in raw['cad_don'])
    if not validated[rel]:
     held.append({'price_row_id':row['id'],'profile':rel,'reason':'Source view/unit/audit validation failed'});continue
    score=(len(d['views'])>=6,len(str(match['source_model'])),len(d['views']),'OFFICIAL-' in rel)
    candidates[row['id']].append((score,rel,cid,match))
 plan=[];rowbyid={r['id']:r for r in rows}
 for rid,options in candidates.items():
  score,rel,cid,match=max(options,key=lambda a:a[0]);row=rowbyid[rid]
  plan.append({'price_row_id':rid,'brand':canonical_brand(row['brand']),'sku':row['sku'],'item_name':row['item_name'],'category':row['category'],'profile':rel,'catalog_id':cid,'review':match,'alternatives':len(options)-1})
 save(OUT/'plan.json',plan);summary={'priced_rows':len(rows),'previously_explicitly_linked_rows':len(existing),'proposed_new_unique_rows':len(plan),'by_brand':dict(collections.Counter(r['brand'] for r in plan)),'by_category':dict(collections.Counter(r['category'] for r in plan))};save(OUT/'plan-summary.json',summary)
 with (OUT/'plan.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['brand','sku','item_name','category','profile','price_row_id']);w.writeheader();w.writerows({k:r[k] for k in w.fieldnames} for r in plan)
 save(OUT/'held-links.json',held)
 print(json.dumps(summary),flush=True)
 if '--apply' not in sys.argv:return
 assert not (OUT/'applied.json').exists(),'Already applied'
 overlay_path=ROOT/'app/data/catalogtb_published_information.json';overlay=json.loads(overlay_path.read_text(encoding='utf8'));save(OUT/'published-information.before.json',overlay)
 grouped=collections.defaultdict(list)
 for r in plan:grouped[r['profile']].append(r)
 for rel,links in grouped.items():
  p=CAT/rel;raw=json.loads(p.read_text(encoding='utf-8-sig'));backup=OUT/'before'/rel;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,backup)
  refs=raw.setdefault('catalog_tham_khao',{});options=refs.setdefault('options',[])
  for link in links:
   row=rowbyid[link['price_row_id']];option=price_option(row,brand=canonical_brand(row['brand']));option.update(price='---',basis='reviewed_named_body_family',geometry_link_review=link['review'])
   old=next((o for o in options if canonical_brand(o.get('brand'))==option['brand'] and o.get('model')==option['model']),None)
   if old:old.update(option)
   else:options.append(option)
  refs['price_cad_link_review']={'checked_at':'2026-10-22','scope':'Same named model/body, maker, type, poles and explicit frame bounds; electrical ratings belong to each price row, not CAD geometry','added_price_row_ids':[r['price_row_id'] for r in links]}
  save(p,raw)
  published=overlay.setdefault('profiles',{}).get(rel) or overlay['profiles'].get('TB-'+hashlib.sha1(rel.encode()).hexdigest()[:16])
  if published is not None:published['catalog_tham_khao']=refs
 save(overlay_path,overlay);save(OUT/'applied.json',{'links':plan,'changed_profiles':len(grouped),'supplier_pricebook_sha256':hashlib.sha256((ROOT/'app/data/supplier_pricebooks.json').read_bytes()).hexdigest()});print('Applied',len(plan),'links to',len(grouped),'profiles',flush=True)
if __name__=='__main__':main()
