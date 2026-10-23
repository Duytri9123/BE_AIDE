"""Archive the unlabeled one-face candidate now replaced by manufacturer KG316T CAD."""
import hashlib,json,shutil,sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB';OUT=ROOT/'docs/four-brands-additions-2026-10-22'
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
def main():
 relative='Chint/ThietBi/KG316T/thong_tin_thiet_bi.json';p=CAT/relative;raw=json.loads(p.read_text(encoding='utf8'));assert not raw.get('browser_hidden')
 ident=(raw.get('catalog_tham_khao') or {}).get('source_identification') or {};assert ident.get('status')=='source_geometry_without_model_label' and ident.get('ordering_code_verified') is False
 replacement=CAT/'Chint/ThietBi/OFFICIAL-TIMER-KG316T/thong_tin_thiet_bi.json';new=json.loads(replacement.read_text(encoding='utf8'));assert len(new['cad_don'])==6
 backup=OUT/'before'/relative;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,backup)
 cid='TB-'+hashlib.sha1(relative.encode()).hexdigest()[:16];ledger=ROOT/'app/data/catalog_quarantined_views.json';quarantine=json.loads(ledger.read_text(encoding='utf8'))
 for view in raw['cad_don']:
  source=(p.parent/view['duong_dan']).parent.resolve();dest=(OUT/'quarantined-cad'/view['id_hinh_goc']).resolve()
  assert source.is_relative_to(p.parent.resolve()) and dest.is_relative_to(OUT.resolve()) and source.is_dir() and not dest.exists()
  dest.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(source),str(dest));quarantine['items'].append({'catalog_id':cid,'view_id':view['id_hinh_goc'],'reason':'Unlabeled legacy model candidate superseded by manufacturer six-view KG316T; not a certified ordering-code match','archived_path':dest.relative_to(ROOT).as_posix()})
 raw.update(browser_hidden=True,superseded_by=replacement.relative_to(CAT).as_posix(),quarantined_cad_views=raw['cad_don'],cad_don=[],cac_hinh_cad=[],cad_chen_tu={});save(p,raw);save(ledger,quarantine)
 with sqlite3.connect(CAT/'_agent_index/equipment_catalog.sqlite') as db:
  db.execute('DELETE FROM equipment WHERE catalog_id=?',(cid,));db.execute('DELETE FROM equipment_fts WHERE catalog_id=?',(cid,))
 save(OUT/'replaced-legacy-kg316t.json',{'catalog_id':cid,'profile':relative,'replacement':raw['superseded_by'],'archived_view_ids':[v['id_hinh_goc'] for v in raw['quarantined_cad_views']]})
 print('Unlabeled one-view KG316T archived; manufacturer six-view family retained')
if __name__=='__main__':main()
