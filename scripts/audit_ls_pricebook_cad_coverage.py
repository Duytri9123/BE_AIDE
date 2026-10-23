"""Audit every LS price row against explicit, visible CAD profile links."""
import json,csv,collections,hashlib,sqlite3
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.cad.ls_view_coverage import view_coverage
ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB';OUT=ROOT/'docs/ls-library-rebuild-2026-10-20';OUT.mkdir(exist_ok=True)
def main():
 prices=[r for r in json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'] if str(r.get('brand','')).lower() in ['ls','ls electric']]
 links=collections.defaultdict(list);profiles=0;faces=0;errors=[]
 for p in CAT.rglob('thong_tin_thiet_bi.json'):
  d=json.loads(p.read_text(encoding='utf8'))
  if d.get('browser_hidden') or (p.relative_to(CAT).parts[0]!='LS' and str(d.get('hang_xac_nhan','')).upper() not in ['LS','LS ELECTRIC']):continue
  views=d.get('cad_don') or []
  if not views:continue
  profiles+=1;faces+=len(views);valid=[]
  for v in views:
   f=p.parent/v.get('duong_dan','');label=v.get('huong_nhin','')
   if not f.is_file():errors.append({'profile':str(p.relative_to(CAT)),'view':v.get('id_hinh_goc'),'error':'missing DXF'})
   if not label or 'chưa xác định' in label.lower():errors.append({'profile':str(p.relative_to(CAT)),'error':'unresolved view'})
   valid.append(label)
  groups=collections.defaultdict(list)
  for v in views:
   groups[v.get('bien_the_cad') or v.get('bien_the') or 'default'].append({**v,'available':(p.parent/v.get('duong_dan','')).is_file()})
  sets=[{'variant':key,**view_coverage(values)} for key,values in groups.items()]
  best=min(sets,key=lambda v:len(v['missing_faces']))
  for o in (d.get('catalog_tham_khao') or {}).get('options',[]):
   if o.get('source_row_id'):links[o['source_row_id']].append({'profile':p.relative_to(CAT).as_posix(),'name':d.get('ten_san_pham'),'views':valid,'view_sets':sets,'six_views_complete':best['complete'],'missing_faces':best['missing_faces'],'missing_labels':best['missing_labels'],'exact_sku_verified':o.get('exact_cad_match') is True,'source_urls':d.get('nguon_tham_khao') or []})
 results=[]
 for r in prices:
  matches=links[r['id']];results.append({'price_row_id':r['id'],'sku':r['sku'],'category':r['category'],'group':r.get('group'),'price_vnd':r.get('price'),'specifications':r.get('specifications'),'status':('six_view_family_reference_requires_configuration_check' if any(p['six_views_complete'] for p in matches) else 'linked_cad_missing_views') if matches else 'missing_verified_pricebook_cad','profiles':matches})
 categories={c:{'total':sum(r['category']==c for r in results),'linked':sum(r['category']==c and bool(r['profiles']) for r in results)} for c in sorted({r['category'] for r in results})}
 summary={'total_price_rows':len(prices),'linked_price_rows':sum(bool(r['profiles']) for r in results),'missing_price_rows':sum(not r['profiles'] for r in results),'six_view_price_rows':sum(any(p['six_views_complete'] for p in r['profiles']) for r in results),'incomplete_view_price_rows':sum(bool(r['profiles']) and not any(p['six_views_complete'] for p in r['profiles']) for r in results),'visible_ls_profiles':profiles,'visible_ls_views':faces,'validation_errors':errors,'categories':categories,'note':'A family CAD link does not prove exact SKU, terminal, coil or electrical compatibility. Missing verified CAD remains explicitly uncovered.'}
 pending=[]
 for r in results:
  if any(p['six_views_complete'] for p in r['profiles']):continue
  best=min(r['profiles'],key=lambda p:len(p['missing_faces'])) if r['profiles'] else None
  coverage=best or view_coverage([])
  pending.append({**{k:r[k] for k in ['price_row_id','sku','category','specifications','status']},'missing_faces':coverage['missing_faces'],'missing_labels':coverage['missing_labels'],'best_profile':best['profile'] if best else None})
 (OUT/'cad-supplement-queue.json').write_text(json.dumps({'required_views':'front,rear,left,right,top,bottom of one CAD variant','items':pending},ensure_ascii=False,indent=2),encoding='utf8')
 report={'summary':summary,'rows':results};(OUT/'pricebook-cad-coverage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
 with (OUT/'pricebook-cad-coverage.csv').open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.writer(f);w.writerow(['Ma dong gia','Ma thiet bi','Loai','Gia VND','Trang thai','So ho CAD','Cac mat CAD','Ho CAD'])
  for r in results:w.writerow([r['price_row_id'],r['sku'],r['category'],r['price_vnd'],r['status'],len(r['profiles']),' | '.join(sorted({v for p in r['profiles'] for v in p['views']})),' | '.join(p['name'] for p in r['profiles'])])
 print(json.dumps(summary,ensure_ascii=True,indent=2));assert not errors
 return report
if __name__=='__main__':main()
