"""Validate targeted DC additions and recompute coverage after series-scope repair."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from PIL import Image,ImageOps,ImageDraw
from ls_native_writer import ROOT,CAT
from publish_abb_ct_index import main as publish
OUT=ROOT/'docs/ls-targeted-review-2026-10-26'

def main(refresh=True):
    adds=json.loads((OUT/'dc-additions.json').read_text(encoding='utf8'))+json.loads((OUT/'mccb-additions.json').read_text(encoding='utf8'));views=[];checks=[]
    canvas=Image.new('RGB',(1000,350*len(adds)),'white');draw=ImageDraw.Draw(canvas)
    for row,a in enumerate(adds):
        p=CAT/a['profile'];d=json.loads(p.read_text(encoding='utf8'))
        for col,v in enumerate(d['cad_don']):
            path=p.parent/v['duong_dan'];doc=ezdxf.readfile(path);audit=doc.audit()
            assert doc.units==4 and not audit.errors and not audit.fixes
            views.append(dict(family=p.parent.name,view=v['huong_nhin'],path=path.parent.relative_to(CAT).as_posix()))
            checks.append(dict(path=path.relative_to(CAT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),units_mm=True,audit_errors=0,audit_fixes=0))
            im=ImageOps.contain(Image.open(path.with_name('preview.png')).convert('RGB'),(480,310));canvas.paste(im,(col*500,row*350+30));draw.text((col*500+5,row*350+5),p.parent.name+' '+v['id_hinh_goc'].rsplit('-',1)[-1],fill='black')
    canvas.save(OUT/'dc-contact-sheet.png')
    (OUT/'dc-validation.json').write_text(json.dumps(checks,indent=2),encoding='utf8')
    name='ls-targeted-20261026';(ROOT/'docs'/f'{name}.json').write_text(json.dumps(views,ensure_ascii=False,indent=2),encoding='utf8')
    publish([(CAT/a['profile']).parent.name for a in adds],report_name=name,brand='LS',category='MIXED',profile_root='LS/ThietBi',refresh=refresh)
    import audit_ls_pricebook_cad_coverage as audit
    audit.OUT=OUT;result=audit.main()
    previous=json.loads((ROOT/'docs/ls-recheck-2026-10-26/pricebook-cad-coverage.json').read_text(encoding='utf8'))
    old={r['price_row_id']:r for r in previous['rows']}
    changes=[dict(sku=r['sku'],id=r['price_row_id'],old_status=old[r['price_row_id']]['status'],new_status=r['status'],old_profiles=[x['profile'] for x in old[r['price_row_id']]['profiles']],new_profiles=[x['profile'] for x in r['profiles']]) for r in result['rows'] if r['status']!=old[r['price_row_id']]['status'] or {x['profile'] for x in r['profiles']}!={x['profile'] for x in old[r['price_row_id']]['profiles']}]
    (OUT/'coverage-changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf8')
    report=dict(summary=result['summary'],focus_notes=[
        'MCCB category includes 12 accessory price rows; do not describe all 22 previously pending rows as breaker bodies.',
        'Official 45195 DWG title explicitly includes ABS1003b/1004b; native front/side exists but six orthographic faces are not established.',
        'Official MR8 50373 DWG has separate AC/DC panels and three source views; no six-face completion inferred.',
        'GMP22/40 native title and catalog establish models/contact variants; missing orientations remain gaps.',
        'Series-only price fallback was incorrectly promoted to source-family scope. Corrected without promoting arbitrary same-prefix frames; exact ACB model alternatives remain supported.'
    ])
    (OUT/'review-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    from continue_ls_cad_coverage import OUT as current,reconcile
    for name in ['pricebook-cad-coverage.json','pricebook-cad-coverage.csv']:
        (current/name).write_bytes((OUT/name).read_bytes())
    reconcile(result)
    old_matrix=json.loads((current/'remaining-gap-dispositions-20261026.json').read_text(encoding='utf8'))
    by_id={r['price_row_id']:r for r in old_matrix['rows']}
    q=json.loads((current/'cad-supplement-queue.json').read_text(encoding='utf8'))
    matrix=[]
    for item in q['items']:
        row=by_id.get(item['id'],dict(price_row_id=item['id'],sku=item['sku'],category=item['category'],candidate_sources=[],required_evidence='Exact model/configuration source CAD with verifiable units and views.'))
        row.update(status='gap',linked_partial=item['linked'],missing_faces=item['missing_faces'],
                   blocker=item['gap_reason'] if item['linked'] else 'No model/configuration-specific CAD link after rejecting series-only frame matches.',
                   review_scope='Updated targeted MCCB/DC/relay review; same-prefix series reference is not a CAD match.')
        matrix.append(row)
    (current/'remaining-gap-dispositions-20261026.json').write_text(json.dumps(dict(summary=q['summary'],rows=matrix),ensure_ascii=False,indent=2),encoding='utf8')
    import csv
    with (current/'remaining-gap-dispositions-20261026.csv').open('w',newline='',encoding='utf-8-sig') as f:
        fields=['price_row_id','sku','category','status','linked_partial','missing_faces','blocker','required_evidence','candidate_sources','review_scope']
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(matrix)
    return result

if __name__=='__main__':main()
