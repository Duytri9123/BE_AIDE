"""Quarantine mismatched ABB projections; clean metadata without geometry changes."""
import hashlib, json, shutil, sqlite3, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from ezdxf.lldxf.tagwriter import TagCollector
from app.services.library_manufacturer_identity import EVIDENCE_PATH
ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB'
OUT=ROOT/'docs/catalog-error-repair-2026-10-21'

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def geometry(doc):
    return [(block.name,[(e.dxftype(),repr(TagCollector.dxftags(e))) for e in block]) for block in doc.blocks]
def write(path,data):
    stage=path.with_suffix(path.suffix+'.pending');stage.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8');stage.replace(path)
def replace_hashes(value,mapping):
    if isinstance(value,dict):return {k:replace_hashes(v,mapping) for k,v in value.items()}
    if isinstance(value,list):return [replace_hashes(v,mapping) for v in value]
    return mapping.get(value,value) if isinstance(value,str) else value

def main():
    OUT.mkdir(exist_ok=True)
    report_path=OUT/'repairs.json'
    if report_path.exists():raise RuntimeError('Already repaired; use verification instead of repeating mutations')
    source=json.loads((ROOT/'docs/abb-ls-chint-current-audit-2026-10-21/dxf-in-memory-fixes.json').read_text(encoding='utf8'))
    repairs=[];mapping={}
    for row in source:
        path=CAT/row['path'];doc=ezdxf.readfile(path);before=geometry(doc);old=digest(path);audit=doc.audit()
        assert not audit.errors and audit.fixes and all(f.code in {102,202} for f in audit.fixes)
        assert geometry(doc)==before,'Audit altered drawing entities'
        backup=OUT/'before'/row['path'];backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,backup)
        stage=path.with_name('ban_ve.metadata-clean.dxf');doc.saveas(stage)
        checked=ezdxf.readfile(stage);check=checked.audit()
        assert not check.errors and not check.fixes and geometry(checked)==before,'Saved geometry changed or metadata still invalid'
        stage.replace(path);new=digest(path);mapping[old]=new
        repairs.append({'path':row['path'],'old_sha256':old,'new_sha256':new,'fixes':row['fixes'],'block_and_modelspace_tags_unchanged':True})
        print('Cleaned',row['path'],flush=True)
    # Preserve manufacturer review attribution only after the exact drawing
    # entity tags have been proved unchanged. Source DWG/document hashes stay intact.
    evidence=json.loads(EVIDENCE_PATH.read_text(encoding='utf8'))
    shutil.copy2(EVIDENCE_PATH,OUT/'manufacturer-evidence.before.json')
    write(EVIDENCE_PATH,replace_hashes(evidence,mapping))
    profile=CAT/'BienDong/ABB/ZCT-300A/thong_tin_thiet_bi.json';raw=json.loads(profile.read_text(encoding='utf8'))
    shutil.copy2(profile,OUT/'abb-zct-profile.before.json')
    bad={'A02_abb-V002','A02_abb-V003'};removed=[v for v in raw['cad_don'] if v['id_hinh_goc'] in bad]
    assert len(removed)==2
    cid='TB-'+hashlib.sha1(profile.relative_to(CAT).as_posix().encode()).hexdigest()[:16]
    quarantine=[]
    for view in removed:
        source_dir=(profile.parent/view['duong_dan']).parent.resolve();target=(OUT/'quarantined-cad'/view['id_hinh_goc']).resolve()
        assert source_dir.is_relative_to((CAT/'BienDong/ABB/ZCT-300A/CadDon').resolve()) and target.is_relative_to(OUT.resolve()) and not target.exists()
        target.parent.mkdir(exist_ok=True);shutil.move(str(source_dir),str(target))
        quarantine.append({'catalog_id':cid,'view_id':view['id_hinh_goc'],'reason':'unresolved identity; not established as a projection of the ZCT ring','archived_path':str(target.relative_to(ROOT))})
    raw['cad_don']=[v for v in raw['cad_don'] if v['id_hinh_goc'] not in bad]
    raw['cac_hinh_cad']=[v for v in raw.get('cac_hinh_cad',[]) if v not in bad]
    raw['quarantined_cad_views']=quarantine;write(profile,raw)
    qp=ROOT/'app/data/catalog_quarantined_views.json';existing=json.loads(qp.read_text(encoding='utf8')) if qp.exists() else {'items':[]}
    existing['items']+=quarantine;write(qp,existing)
    with sqlite3.connect(CAT/'_agent_index/equipment_catalog.sqlite') as db:
        row=db.execute('SELECT record_json FROM equipment WHERE catalog_id=?',(cid,)).fetchone()
        if row:
            record=json.loads(row[0]);record['cad']['views']=[v for v in record['cad'].get('views',[]) if v['id'] not in bad]
            db.execute('UPDATE equipment SET record_json=? WHERE catalog_id=?',(json.dumps(record,ensure_ascii=False),cid))
    write(report_path,{'metadata_repairs':repairs,'quarantined_views':quarantine})
    print(json.dumps({'repaired_files':len(repairs),'quarantined_views':len(quarantine)}),flush=True)

if __name__=='__main__':main()
