"""Validate actual SPD additions and account explicitly for every remaining gap."""
import csv,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from ls_native_writer import ROOT,CAT
OUT=ROOT/'docs/ls-all-cad-2026-10-24'

def main():
    additions=json.loads((OUT/'bk05s-additions-20261026.json').read_text(encoding='utf8'))
    checks=[]
    for row in additions:
        profile=CAT/row['profile'];p=json.loads(profile.read_text(encoding='utf8'))
        assert p['thong_so']['so_cuc']==row['poles'] and len(p['cad_don'])==2
        for v in p['cad_don']:
            path=profile.parent/v['duong_dan'];d=ezdxf.readfile(path);a=d.audit()
            assert d.units==4 and not a.errors and not a.fixes
            checks.append(dict(profile=row['profile'],face=v['huong_nhin'],path=path.relative_to(CAT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),audit_errors=0,audit_fixes=0))
    from app.services.catalogtb_browser import _refresh_browser_data,browser_data
    _refresh_browser_data(CAT)
    from app.services.price_row_cad_detail import linked_cad_for_row
    prices=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items']
    devices=browser_data()['items']
    for row in additions:
        price=next(r for r in prices if r['id']==row['price_ids'][0])
        matches=linked_cad_for_row(price,devices)
        assert len(matches)==1 and len(matches[0]['views'])==2
        assert matches[0]['selected_model']=='BK05S-T3 '+row['poles']
    import audit_ls_pricebook_cad_coverage as audit
    audit.OUT=OUT;result=audit.main()
    from continue_ls_cad_coverage import reconcile
    reconcile(result)
    q=json.loads((OUT/'cad-supplement-queue.json').read_text(encoding='utf8'))
    matrix=[]
    for row in q['items']:
        sku=row['sku'];kind=row['category'];sources=[]
        if row['linked']:
            blocker='Source views remain incomplete for a single matching CAD variant.'
            needed='Source-backed '+', '.join(row['missing_faces'])+' of the same model and configuration; generic side is not proof of left and right.'
        else:
            blocker='No reviewed CAD source currently establishes this exact model and configuration.'
            needed='Manufacturer CAD with model, configuration, units and identifiable orthographic views.'
        if sku.startswith('BK05S-T3'):
            sources=['LS/NguonBenNgoai/2SK-BK05S-T3/source.dxf']
            blocker='Two native views verified; nominal dimension overrides retained without rescaling. Other orientations unavailable.'
        elif kind=='SPD':
            sources=['LS/NguonBenNgoai/2SK-BK10-40S/source.dxf']
            blocker='Distributor filename advertises BK10/20/30/40S, but drawing identifies TS250 MCCB. Rejected.'
        elif kind=='MCB' or sku.startswith('LB63N'):
            blocker='Available LA63Hd/HDCd, LA63HU and BK63 sources do not establish the priced AC model/generation and pole configuration.'
        elif sku.startswith('Any Trip Alarm Switch: LA '):
            sources=['LS/NguonBenNgoai/50481/model-019/source.step']
            blocker='LA has separate MMS-32 and MMS-63/100 mating variants; priced parent variant not established.'
        elif sku in ['AC-9','AC-50','AC-75']:
            sources=['LS/NguonBenNgoai/55731/model-001/source.step']
            blocker='AC9_50 contact mechanism lacks the external preloading resistor leads of the complete capacitor unit; AC-75 is not established by this source.'
        elif kind=='CONTACTOR' and '(VDC)' in sku:
            blocker='Candidate DC STEP uses a different auxiliary contact configuration or cannot identify a complete, supported 1A1B/1A assembly. No source parts removed by guesswork.'
        elif (sku.startswith(('DH','EH','MOP')) and 'TS' in sku) or sku.startswith(('DH1','EH1','MOP1')):
            blocker='Available UTE/UTS UL accessory drawings do not establish compatibility with the priced TD/TS IEC parent frame.'
        row.update(gap_reason=blocker,required_evidence=needed,resolution_status='gap')
        matrix.append(dict(price_row_id=row['id'],sku=sku,category=kind,status='gap',linked_partial=row['linked'],missing_faces=row['missing_faces'],blocker=blocker,required_evidence=needed,candidate_sources=sources,
                           review_scope='Current source-inventory compatibility triage; unresolved candidates are not approved evidence.'))
    (OUT/'cad-supplement-queue.json').write_text(json.dumps(q,ensure_ascii=False,indent=2),encoding='utf8')
    (OUT/'remaining-gap-dispositions-20261026.json').write_text(json.dumps(dict(summary=q['summary'],rows=matrix),ensure_ascii=False,indent=2),encoding='utf8')
    (OUT/'bk05s-validation-20261026.json').write_text(json.dumps(checks,indent=2),encoding='utf8')
    with (OUT/'remaining-gap-dispositions-20261026.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=['price_row_id','sku','category','status','linked_partial','missing_faces','blocker','required_evidence','candidate_sources','review_scope']);writer.writeheader();writer.writerows(matrix)
    assert len(matrix)==q['summary']['missing']+q['summary']['partial']
    return result

if __name__=='__main__':main()
