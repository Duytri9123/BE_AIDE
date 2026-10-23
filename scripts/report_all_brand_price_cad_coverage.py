"""Report explicit row links separately from the completeness of CAD views."""
import collections,csv,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/all-brands-price-cad-links-2026-10-22'
def main():
 import sys
 sys.path.insert(0,str(ROOT))
 from app.services.ai.manufacturer_registry import canonical_brand
 from app.services.cad.catalogtb_assets import face_code
 data=json.loads((ROOT/'data/CatalogTB/_agent_index/browser_display_v5.json').read_text(encoding='utf8'))
 rows=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'];links=collections.defaultdict(list)
 for d in data['items']:
  faces={face_code(v.get('face') or v.get('label')) for v in d['views']}
  for o in (d.get('catalog_references') or {}).get('options',[]):
   if o.get('source_row_id') and canonical_brand(o.get('brand'))==canonical_brand(d.get('brand')):
    links[o['source_row_id']].append({'catalog_id':d['id'],'views':len(d['views']),'faces':sorted(faces),'model':d.get('product_code')})
 devices={d['id']:d for d in data['items']}
 for d in list(devices.values()):
  for cid in d.get('member_profile_ids',[]):devices.setdefault(cid,d)
 for p in (ROOT/'data/CatalogTB').rglob('thong_tin_thiet_bi.json'):
  cid='TB-'+hashlib.sha1(p.relative_to(ROOT/'data/CatalogTB').as_posix().encode()).hexdigest()[:16]
  if cid not in devices:continue
  raw=json.loads(p.read_text(encoding='utf-8-sig'));d=devices[cid]
  if raw.get('browser_hidden'):continue
  for o in (raw.get('catalog_tham_khao') or {}).get('options',[]):
   rid=o.get('source_row_id')
   if rid and canonical_brand(o.get('brand'))==canonical_brand(d.get('brand')) and not any(x['catalog_id']==cid for x in links[rid]):
    links[rid].append({'catalog_id':cid,'views':len(d['views']),'model':d.get('product_code')})
 report=[];summary=collections.defaultdict(collections.Counter)
 for row in rows:
  maker=canonical_brand(row['brand']);attached=links.get(row['id'],[]);status='explicit_family_link' if attached else 'needs_explicit_link_or_source'
  summary[maker]['price_rows']+=1;summary[maker][status]+=1
  report.append({'brand':maker,'sku':row['sku'],'category':row['category'],'price_row_id':row['id'],'status':status,'catalog_ids':' | '.join(x['catalog_id'] for x in attached)})
 (OUT/'coverage-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
 with (OUT/'all-price-rows.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(report[0]));w.writeheader();w.writerows(report)
 print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
