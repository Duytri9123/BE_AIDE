"""Record supported MMS links and explicitly withhold unresolved configurations."""
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from ls_native_writer import CAT,ROOT
OUT=ROOT/'docs/ls-all-cad-2026-10-24'

def main():
    profile=CAT/'LS/ThietBi/OFFICIAL-STEP-50481-model-019/thong_tin_thiet_bi.json'
    d=json.loads(profile.read_text(encoding='utf8'))
    pdf=OUT/'research-gap-20261025/mms-catalog-ko.pdf'
    evidence=dict(source_url='https://www.ls-electric.com/ko/cat/%5BMetasol_MMS%5D_KO_C01821-06-202609.pdf',
                  sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),pdf_pages=[16,24],
                  reviewed_models=['LX','LAM'],contact_configuration='1NO+1NC',
                  source_step='LS/NguonBenNgoai/50481/model-019/source.step',
                  geometry_scope='Shared manufacturer LX,LA,LAM body; left-mounted MMS accessory. No exact ordering SKU or parent mating approval.',
                  withheld='LA has separate MMS-32 and MMS-63/100 mating variants. The price row does not identify one; no supported parent variant established.')
    for o in d['catalog_tham_khao']['options']:
        if o['model'].startswith('Any Trip Alarm Switch: LA '):
            if o.get('source_row_id'):o['unresolved_source_row_id']=o.pop('source_row_id')
            o['configuration_gap']=evidence['withheld']
        else:
            o['configuration_evidence']=evidence
    d['reviewed_configuration_evidence']=evidence
    profile.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    validation=[]
    for view in d['cad_don']:
        path=profile.parent/view['duong_dan'];doc=ezdxf.readfile(path);a=doc.audit()
        assert doc.units==4 and not a.errors and not a.fixes
        validation.append(dict(path=path.relative_to(CAT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),audit_errors=0,audit_fixes=0))
    review=dict(date='2026-10-26',mms=evidence,validation=validation,
                new_cad_faces=0,restored_supported_price_rows=['ls-pdf:46324bfb04bb21ee','ls-pdf:d8b8b1b0b925c8fa'],
                source_rejections=[
                    dict(source='55731/model-001',model='AC-9 / AC-50',decision='gap',reason='STEP product AC9_50 is a contact mechanism without the external capacitor preloading resistor leads shown in catalog page 91. Not approved as the complete priced capacitor unit.'),
                    dict(source='AMERICA-23721 / AMERICA-26774',model='MC-50a/65a/75a/85a/100a DC',decision='gap',reason='Source names explicitly identify 2A2B while price rows require 1A1B. Components are unnamed COMPOUND bodies; no supported named 1A1B assembly can be isolated.'),
                    dict(source='LS America Susol MCCB download listing',model='DH1..DH5 / EH1..EH5',decision='gap',reason='Available sources identify UTE/UTS UL parent frames; price rows specify TD/TS IEC. No manufacturer compatibility evidence equates those accessory configurations.'),
                    dict(source='LS America LA63 / BK listings',model='LA63N/H/L / BKxxS SPD',decision='gap',reason='Returned CAD covers BK63H/HU MCB or unrelated UL frames; not evidence for the priced LA63 or BKxxS SPD variants.')])
    review['source_rejections'].append(dict(source='45351/model-000',model='MC-150a DC 1A1B',decision='gap',reason='Repeated auxiliary assemblies and an AC-named PCB remain unresolved. The AC_DC filename does not establish the priced DC 1A1B configuration; no parts removed.'))
    (OUT/'gap-review-20261026.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf8')
    # Update this one reviewed record in the persisted display index. All CAD
    # geometry, view IDs and all unrelated catalog records remain untouched.
    snapshot=CAT/'_agent_index/browser_display_v5.json'
    data=json.loads(snapshot.read_text(encoding='utf8'))
    cid='TB-'+hashlib.sha1(profile.relative_to(CAT).as_posix().encode()).hexdigest()[:16]
    record=next(r for r in data['items'] if r['id']==cid)
    record['catalog_references']=d['catalog_tham_khao']
    snapshot.write_text(json.dumps(data,ensure_ascii=False),encoding='utf8')
    import audit_ls_pricebook_cad_coverage as audit
    audit.OUT=OUT;result=audit.main()
    from continue_ls_cad_coverage import reconcile
    reconcile(result)
    queue=OUT/'cad-supplement-queue.json'
    q=json.loads(queue.read_text(encoding='utf8'))
    for row in q['items']:
        if row['sku'].startswith('Any Trip Alarm Switch: LA '):row['gap_reason']=evidence['withheld']
        elif row['sku'] in ['AC-9','AC-50']:row['gap_reason']=review['source_rejections'][0]['reason']
        elif row['sku']=='MC-150a (VDC)':row['gap_reason']=review['source_rejections'][-1]['reason']
    queue.write_text(json.dumps(q,ensure_ascii=False,indent=2),encoding='utf8')
    return result

if __name__=='__main__':main()
