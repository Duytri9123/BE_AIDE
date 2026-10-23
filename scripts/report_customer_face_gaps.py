"""Report visible profile view gaps; never count drawing states as directions."""
import collections,csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.services.cad.ls_view_coverage import view_coverage
from app.services.ai.manufacturer_registry import canonical_brand

def main():
 snapshot=json.loads((ROOT/'data/CatalogTB/_agent_index/browser_display_v5.json').read_text(encoding='utf8'))
 counts=collections.defaultdict(collections.Counter);gaps=[]
 for d in snapshot['items']:
  maker=canonical_brand(d.get('brand')) or 'Generic';views=d.get('views') or [];status=view_coverage(views);count=counts[maker]
  count['profiles']+=1;count['single_drawing_profiles']+=len(views)==1;count['profiles_with_six_direction_roles']+=status['complete']
  if not status['complete']:
   count['profiles_with_missing_direction_roles']+=1
   gaps.append({'brand':maker,'catalog_id':d['id'],'model':d.get('product_code'),'type':d.get('type'),'drawing_count':len(views),'available_faces':' | '.join(status['available_faces']),'missing_faces':' | '.join(status['missing_faces'])})
 out=ROOT/'docs/catalog-completion-2026-10-23'
 (out/'visible-face-gaps.json').write_text(json.dumps({'scope':'Current visible profile direction roles, not per-ordering-code certification. Repeated FRONT states are one role; unqualified SIDE does not prove left/right. Different configurations still require separate pairing review.','counts':counts,'gaps':gaps},ensure_ascii=False,indent=2),encoding='utf8')
 with (out/'visible-face-gaps.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['brand','catalog_id','model','type','drawing_count','available_faces','missing_faces']);w.writeheader();w.writerows(gaps)
 print(json.dumps(counts,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
