"""Count actual files and six distinct orientations per physical CAD variant."""
import json,csv,hashlib,collections,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.cad.ls_view_coverage import view_coverage,view_role
ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB';OUT=ROOT/'docs/ls-chint-view-counts-2026-10-21'

def main():
 OUT.mkdir(exist_ok=True)
 snapshot=CAT/'_agent_index/browser_display_v5.json';data=json.loads(snapshot.read_text(encoding='utf8'));index={}
 for p in CAT.rglob('thong_tin_thiet_bi.json'):
  raw=json.loads(p.read_text(encoding='utf-8-sig'));cid='TB-'+hashlib.sha1(p.relative_to(CAT).as_posix().encode()).hexdigest()[:16]
  if raw.get('browser_hidden'):continue
  for v in raw.get('cad_don',[]):index.setdefault(v['id_hinh_goc'],[]).append({'profile_id':cid,'profile':p.relative_to(CAT).as_posix(),'variant':v.get('bien_the_cad') or v.get('bien_the'),'file':p.parent/v.get('duong_dan','')})
 rows=[]
 for item in data['items']:
  maker=str(item.get('brand') or '').upper()
  if maker not in {'LS','LS ELECTRIC','CHINT'}:continue
  brand='CHINT' if maker=='CHINT' else 'LS';groups=collections.defaultdict(list);details=[]
  members={item['id'],*(item.get('member_profile_ids') or [])}
  for v in item.get('views',[]):
   candidates=index.get(v['id'],[]);preferred=[s for s in candidates if s['profile_id'] in members];sources=preferred or candidates
   paths={str(s['file'].resolve()) for s in sources if s['file'].is_file()};available=bool(paths)
   # Browser merges do not prove two different profiles are one variant.
   variants={s['profile_id']+':'+str(s['variant'] or 'unspecified') for s in sources}
   key=v.get('cad_variant_id') or (next(iter(variants)) if len(variants)==1 else 'unpaired:'+v['id'])
   detail={'id':v['id'],'label':v.get('label'),'face':v.get('face'),'role':view_role(v),'available':available,'variant':key,'source_profiles':sorted({s['profile'] for s in sources})}
   details.append(detail);groups[key].append({**v,'available':available})
  sets=[{'variant':key,'view_files':len(values),**view_coverage(values)} for key,values in groups.items()]
  best=min(sets,key=lambda x:len(x['missing_faces'])) if sets else view_coverage([])
  count=sum(v['available'] for v in details);roles=[v['role'] for v in details if v['available'] and v['role']]
  rows.append({'brand':brand,'id':item['id'],'name':item['display'],'type':item.get('type'),'view_count':len(details),'available_view_count':count,'distinct_required_directions':len(set(roles)),'duplicate_direction_files':len(roles)-len(set(roles)),'generic_side_files':sum(str(v.get('face') or '').split(' · ')[0]=='Mặt bên' for v in details),'complete_six_view_variant':any(s['complete'] for s in sets),'missing_faces_best_variant':best['missing_faces'],'missing_labels_best_variant':best['missing_labels'],'variants':sets,'views':details})
 summary={}
 for brand in ['LS','CHINT']:
  selected=[r for r in rows if r['brand']==brand]
  summary[brand]={'visible_items':len(selected),'visible_view_files':sum(r['view_count'] for r in selected),'view_count_histogram':dict(sorted(collections.Counter(r['view_count'] for r in selected).items())),'one_view_items':sum(r['view_count']==1 for r in selected),'two_to_five_view_items':sum(2<=r['view_count']<=5 for r in selected),'six_or_more_files_but_incomplete':sum(r['view_count']>=6 and not r['complete_six_view_variant'] for r in selected),'complete_six_view_items':sum(r['complete_six_view_variant'] for r in selected),'incomplete_items':sum(not r['complete_six_view_variant'] for r in selected),'missing_file_references':sum(r['view_count']-r['available_view_count'] for r in selected)}
 report={'snapshot_sha256':hashlib.sha256(snapshot.read_bytes()).hexdigest(),'rules':'Count real referenced files; six distinct orientations of the same variant are required. Generic side does not establish both left and right. Separate profiles/variants are not combined to make a complete set. Counts describe library entries, not pricebook rows.','summary':summary,'items':rows}
 (OUT/'all-items.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
 for name,selected in [('all-items',rows),('one-view-items',[r for r in rows if r['view_count']==1]),('incomplete-items',[r for r in rows if not r['complete_six_view_variant']])]:
  with (OUT/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
   writer=csv.writer(f);writer.writerow(['Hãng','ID','Tên thiết bị','Loại','Số tệp mặt','Tệp tồn tại','Số hướng chính khác nhau','Số bộ biến thể','Có bộ đủ 6 hướng','Các mặt thiếu của bộ tốt nhất','Nhãn các mặt hiện có'])
   for r in selected:writer.writerow([r['brand'],r['id'],r['name'],r['type'],r['view_count'],r['available_view_count'],r['distinct_required_directions'],len(r['variants']),'Có' if r['complete_six_view_variant'] else 'Không','; '.join(r['missing_labels_best_variant']),'; '.join(v['label'] or v['face'] or '' for v in r['views'])])
 print(json.dumps(summary,indent=2),flush=True)
 for r in rows:
  if r['view_count']>=6 and not r['complete_six_view_variant']:print(json.dumps({'brand':r['brand'],'name':r['name'],'count':r['view_count'],'missing':r['missing_faces_best_variant']},ensure_ascii=True))
if __name__=='__main__':main()
