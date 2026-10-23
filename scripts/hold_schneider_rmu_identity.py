"""Remove unsupported maker attribution explicitly prohibited by CatalogTB rules."""
import hashlib,json,shutil,sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB';OUT=ROOT/'docs/schneider-update-2026-10-21'

def main():
 ep=ROOT/'app/data/library_manufacturer_evidence.json';evidence=json.loads(ep.read_text(encoding='utf8'));shutil.copy2(ep,OUT/'manufacturer-evidence.before-rmu.json')
 qp=ROOT/'app/data/catalog_quarantined_views.json';q=json.loads(qp.read_text(encoding='utf8'));holds=[]
 for name in ['E01','E02','E03']:
  path=CAT/'RMU/ThietBi'/name/'thong_tin_thiet_bi.json';raw=json.loads(path.read_text(encoding='utf8'));cid='TB-'+hashlib.sha1(path.relative_to(CAT).as_posix().encode()).hexdigest()[:16]
  old=evidence['evidence'][cid];assert not raw.get('hang_xac_nhan') and not old.get('original_labels') and not old.get('sources')
  backup=OUT/'before'/path.relative_to(CAT);backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,backup)
  reason='RMU E01-E03 have no manufacturer label/document evidence; CatalogTB AGENTS forbids assigning ABB/Schneider without verification'
  raw['browser_hidden']=True;raw['auto_select']=False;raw['identity_review_exclusion']=reason
  path.write_text(json.dumps(raw,ensure_ascii=False,indent=2),encoding='utf8')
  evidence['evidence'][cid]={'brand':None,'status':'needs_manufacturer_review','reason':reason,'invalidated_evidence':old}
  for view in raw['cad_don']:q['items'].append({'catalog_id':cid,'view_id':view['id_hinh_goc'],'reason':reason})
  holds.append({'id':cid,'profile':path.relative_to(CAT).as_posix(),'name':raw.get('ten_san_pham'),'views_held':len(raw['cad_don']),'reason':reason})
  with sqlite3.connect(CAT/'_agent_index/equipment_catalog.sqlite') as db:
   db.execute('DELETE FROM equipment WHERE catalog_id=?',(cid,));db.execute('DELETE FROM equipment_fts WHERE catalog_id=?',(cid,))
 for p,data in [(ep,evidence),(qp,q)]:
  stage=p.with_suffix('.pending');stage.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8');stage.replace(p)
 cp=OUT/'changes.json';changes=json.loads(cp.read_text(encoding='utf8'));changes['identity_holds']=holds;cp.write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf8')
 print('Held 3 unsupported RMU maker attributions / 7 views')

if __name__=='__main__':main()
