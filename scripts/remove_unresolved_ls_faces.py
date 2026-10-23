"""Remove unresolved LS projections from published profiles and download records."""
import json,hashlib,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));CAT=ROOT/'data/CatalogTB'
from app.services.cad.catalogtb_assets import face_code
out=ROOT/'docs/ls-library-rebuild-2026-10-20';out.mkdir(parents=True,exist_ok=True);removed=[]
with sqlite3.connect(CAT/'_agent_index/equipment_catalog.sqlite') as db:
 for p in CAT.rglob('thong_tin_thiet_bi.json'):
  d=json.loads(p.read_text(encoding='utf8'));rel=p.relative_to(CAT)
  if rel.parts[0]!='LS' and str(d.get('hang_xac_nhan','')).upper() not in ['LS','LS ELECTRIC']:continue
  bad=[v for v in d.get('cad_don',[]) if face_code(v.get('huong_nhin'))=='unknown' or any(x in str(v.get('nhan_hien_thi','')).lower() for x in ['chưa xác','chua xac'])]
  if not bad:continue
  backup=out/'before'/rel;backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(p.read_bytes())
  ids={v['id_hinh_goc'] for v in bad};d['cad_don']=[v for v in d['cad_don'] if v['id_hinh_goc'] not in ids];d['cac_hinh_cad']=[v['id_hinh_goc'] for v in d['cad_don']]
  if not d['cad_don']:d.update(browser_hidden=True,cad_chen_tu={})
  elif (d.get('cad_chen_tu') or {}).get('id_hinh_goc') in ids:d['cad_chen_tu']={k:d['cad_don'][0][k] for k in ['id_hinh_goc','huong_nhin','duong_dan']}
  p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8');cid='TB-'+hashlib.sha1(rel.as_posix().encode()).hexdigest()[:16]
  record=db.execute('SELECT record_json FROM equipment WHERE catalog_id=?',(cid,)).fetchone()
  if record:
   if not d['cad_don']:
    db.execute('DELETE FROM equipment WHERE catalog_id=?',(cid,));db.execute('DELETE FROM equipment_fts WHERE catalog_id=?',(cid,))
   else:
    r=json.loads(record[0]);r['cad']['views']=[v for v in r['cad']['views'] if v['id'] not in ids];first=r['cad']['views'][0];r['cad'].update(default_view_id=first['id'],preview=first['preview'],dxf=first['dxf']);db.execute('UPDATE equipment SET record_json=? WHERE catalog_id=?',(json.dumps(r,ensure_ascii=False),cid))
  removed.append({'profile':rel.as_posix(),'removed_view_ids':sorted(ids),'hidden':d.get('browser_hidden',False)})
(out/'removed-views.json').write_text(json.dumps(removed,ensure_ascii=False,indent=2),encoding='utf8');print('Removed LS unresolved views:',sum(len(r['removed_view_ids']) for r in removed))
