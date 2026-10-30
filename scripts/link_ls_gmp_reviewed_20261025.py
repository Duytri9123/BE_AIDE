"""Link only the GMP models whose 1a1b configuration has manufacturer evidence."""
import json
import hashlib
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ls_native_writer import ROOT,CAT,price_option

def main():
    prices=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items']
    out=ROOT/'docs/ls-all-cad-2026-10-24'
    catalog=out/'research-2026-10-25/gmp.pdf'
    assert catalog.read_bytes().startswith(b'%PDF')
    reports=[]
    for family,models,page in [('RU-GMP22-3P',['GMP22-3P'],10),('RU-GMP40-P',['GMP40-2P','GMP40-3P'],11)]:
        path=CAT/'LS/ThietBi'/('OFFICIAL-'+family)/'thong_tin_thiet_bi.json'
        p=json.loads(path.read_text(encoding='utf8'))
        rows=[r for r in prices if str(r.get('brand')).lower() in ['ls','ls electric'] and r.get('category')=='RELAY'
              and r['sku'] in [m+' (1a1b)' for m in models]]
        assert len(rows)==len(models)*2
        evidence={'source_url':'https://www.ls-electric.com/upload/customer/download/1556/G_EMPR-DMPR.pdf',
                  'pdf_page':page,'sha256':hashlib.sha256(catalog.read_bytes()).hexdigest(),
                  'finding':'Specification table establishes 2SPST (1a1b), terminals 95/96 and 97/98; pin-type model matches source title. Family reference, not exact ordering SKU approval.',
                  'geometry_scope':'Use complete source set only; no mixing with earlier 2-view GMP source. Older native source dimensions are retained, not rescaled to newer catalog outlines.'}
        p['catalog_tham_khao']['options']=[dict(price_option(r),configuration_evidence=evidence) for r in rows]
        p['thong_so']['Tiếp điểm phụ']='1a1b'
        p['source_configuration_review']=evidence
        p['nguon_tham_khao']=list(dict.fromkeys(p['nguon_tham_khao']+[evidence['source_url']]))
        path.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        reports.append(dict(profile=path.relative_to(CAT).as_posix(),price_ids=[r['id'] for r in rows],evidence=evidence))
    (out/'gmp-price-links-20261025.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf8')
    return reports

if __name__=='__main__':main()
