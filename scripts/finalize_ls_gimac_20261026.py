"""Validate/index the GIMAC increment and reconcile the complete LS queue."""
import csv,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from ls_native_writer import ROOT,CAT
from publish_abb_ct_index import main as publish
OUT=ROOT/'docs/ls-gimac-review-2026-10-26'

def main():
    adds=json.loads((OUT/'additions.json').read_text(encoding='utf8'));views=[];checks=[]
    current=ROOT/'docs/ls-all-cad-2026-10-24'
    previous=json.loads((current/'pricebook-cad-coverage.json').read_text(encoding='utf8'))
    (OUT/'coverage-before.json').write_text(json.dumps(previous,ensure_ascii=False,indent=2),encoding='utf8')
    for a in adds:
        p=CAT/a['profile'];d=json.loads(p.read_text(encoding='utf8'))
        assert len(d['cad_don'])==6
        assert {x['source_row_id'] for x in d['catalog_tham_khao']['options']}==set(a['price_ids'])
        for v in d['cad_don']:
            path=p.parent/v['duong_dan'];doc=ezdxf.readfile(path);audit=doc.audit()
            assert doc.units==4 and not audit.errors and not audit.fixes
            views.append(dict(family=p.parent.name,view=v['huong_nhin'],path=path.parent.relative_to(CAT).as_posix()))
            checks.append(dict(path=path.relative_to(CAT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),units_mm=True,audit_errors=0,audit_fixes=0))
    (OUT/'validation.json').write_text(json.dumps(checks,indent=2),encoding='utf8')
    name='ls-gimac-20261026'
    (ROOT/'docs'/f'{name}.json').write_text(json.dumps(views,ensure_ascii=False,indent=2),encoding='utf8')
    publish([(CAT/a['profile']).parent.name for a in adds],report_name=name,brand='LS',category='METER',profile_root='LS/ThietBi',refresh=True)
    import audit_ls_pricebook_cad_coverage as audit
    audit.OUT=OUT;result=audit.main()
    old={r['price_row_id']:r for r in previous['rows']}
    changes=[dict(id=r['price_row_id'],sku=r['sku'],before=old[r['price_row_id']]['status'],after=r['status']) for r in result['rows'] if r['status']!=old[r['price_row_id']]['status']]
    assert len(changes)==1 and changes[0]['id']==adds[0]['price_ids'][0],changes
    (OUT/'coverage-changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf8')
    from continue_ls_cad_coverage import reconcile
    for name in ['pricebook-cad-coverage.json','pricebook-cad-coverage.csv']:(current/name).write_bytes((OUT/name).read_bytes())
    reconcile(result)
    matrix=json.loads((current/'remaining-gap-dispositions-20261026.json').read_text(encoding='utf8'))
    queue=json.loads((current/'cad-supplement-queue.json').read_text(encoding='utf8'))
    gapids={r['id'] for r in queue['items']}
    matrix['rows']=[r for r in matrix['rows'] if r['price_row_id'] in gapids];matrix['summary']=queue['summary']
    assert len(matrix['rows'])==len(gapids)
    (current/'remaining-gap-dispositions-20261026.json').write_text(json.dumps(matrix,ensure_ascii=False,indent=2),encoding='utf8')
    with (current/'remaining-gap-dispositions-20261026.csv').open('w',newline='',encoding='utf-8-sig') as f:
        fields=['price_row_id','sku','category','status','linked_partial','missing_faces','blocker','required_evidence','candidate_sources','review_scope']
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(matrix['rows'])
    print(json.dumps(result['summary'],ensure_ascii=True),flush=True)

if __name__=='__main__':main()
