"""Hide a known missing-terminal projection including its old download URLs."""
import hashlib,json,shutil,sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB';OUT=ROOT/'docs/schneider-update-2026-10-21'
def main():
 p=CAT/'Schneider/ThietBi/EZS400_4P/thong_tin_thiet_bi.json';raw=json.loads(p.read_text(encoding='utf8'));vid='SCH-D01-C6-I05-STATE-4P-FRONT-VIEW';v=next(v for v in raw['cad_don'] if v['id_hinh_goc']==vid)
 assert v['kiem_tra_net_cad']['status']=='unresolved_visible_geometry_defect'
 cid='TB-'+hashlib.sha1(p.relative_to(CAT).as_posix().encode()).hexdigest()[:16]
 backup=OUT/'before'/p.relative_to(CAT);backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,backup)
 source=(p.parent/v['duong_dan']).parent.resolve();dest=(OUT/'quarantined-cad'/vid).resolve();assert source.is_relative_to(CAT.resolve()) and dest.is_relative_to(OUT.resolve()) and not dest.exists();shutil.move(str(source),str(dest))
 raw['cad_don']=[x for x in raw['cad_don'] if x['id_hinh_goc']!=vid];raw['cac_hinh_cad']=[x for x in raw.get('cac_hinh_cad',[]) if x!=vid];assert raw['cad_don']
 raw['quarantined_cad_views']=[v];raw['cad_chen_tu']={k:raw['cad_don'][0][k] for k in ['id_hinh_goc','huong_nhin','duong_dan']};p.write_text(json.dumps(raw,ensure_ascii=False,indent=2),encoding='utf8')
 row={'catalog_id':cid,'view_id':vid,'reason':'front projection missing terminal geometry','archived_path':dest.relative_to(ROOT).as_posix()};qp=ROOT/'app/data/catalog_quarantined_views.json';q=json.loads(qp.read_text(encoding='utf8'));q['items'].append(row);qp.write_text(json.dumps(q,ensure_ascii=False,indent=2),encoding='utf8')
 with sqlite3.connect(CAT/'_agent_index/equipment_catalog.sqlite') as db:
  r=json.loads(db.execute('SELECT record_json FROM equipment WHERE catalog_id=?',(cid,)).fetchone()[0]);r['cad']['views']=[x for x in r['cad']['views'] if x['id']!=vid];first=r['cad']['views'][0];r['cad'].update(default_view_id=first['id'],preview=first['preview'],dxf=first['dxf']);db.execute('UPDATE equipment SET record_json=? WHERE catalog_id=?',(json.dumps(r,ensure_ascii=False),cid))
 cp=OUT/'changes.json';change=json.loads(cp.read_text(encoding='utf8'));change['linework_quarantine']=row;cp.write_text(json.dumps(change,ensure_ascii=False,indent=2),encoding='utf8');print('Quarantined defective EZS400 4P front; preserved remaining valid view')
if __name__=='__main__':main()
