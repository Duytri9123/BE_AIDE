"""Explicit EX/M485 mechanical linkage backed by manufacturer ordering/dimension sheet."""
import hashlib,json,urllib.request,urllib.parse
from pathlib import Path
from ls_native_writer import ROOT,CAT,write_profile,price_option
OUT=ROOT/'docs/ls-gimac-review-2026-10-26'
OUT.mkdir(exist_ok=True)
url='https://www.ls-electric.com/ko/cat/HOMEPAGE/SUMMARY/전력기기 제품총람/C. 계전 · 계측 · 계량기기/C2. 디지털 보호계측기 (Measurement)/C2-5. 디지털 전력 계측장치 (GIMAC1000)/C2-5. 디지털 전력 계측장치 (GIMAC1000).pdf'
url=urllib.parse.quote(url,safe=':/()')
pdf=OUT/'manufacturer-catalog.pdf'
if not pdf.exists():
    pdf.write_bytes(urllib.request.urlopen(url,timeout=90).read())
import fitz
book=fitz.open(pdf)
book[13].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(OUT/'dimensions-ordering-page14.png')
(OUT/'manufacturer-pages.txt').write_text('\n'.join(book[i].get_text() for i in [3,4,13]),encoding='utf8')
if __name__=='__main__':
    # Reuse only the six original source crops; do not execute the NO profile writer.
    original=(ROOT/'scripts/import_ls_gimac_faces.py').read_text(encoding='utf8')
    scope={}
    exec(compile(original.split('rows=json.loads')[0],'<original GIMAC native crops>','exec'),scope)
    rows=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items']
    selected=[r for r in rows if r.get('brand') in ['LS','LS Electric'] and r['sku']=='GIMAC-1000 EX,M485,5A,50Hz,AC/DC100~240V']
    assert len(selected)==1
    p=CAT/'LS/NguonBenNgoai/55455'
    source=json.loads((p/'source.json').read_text(encoding='utf8'))
    source.update(source_dxf_sha256=hashlib.sha256((p/'source.dxf').read_bytes()).hexdigest(),
        configuration_catalog_url=url,configuration_catalog_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),configuration_catalog_pages=[4,5,14],
        configuration_evidence='Manufacturer page 14 separates function NO/EX from NOCOMM/M485/ETH and gives one NOCOMM/M485 outline; page 5 supports 5A,50Hz,AC/DC100-240V. EX/M485 uses upper M485 native outline, not Ethernet.',
        unit_evidence='Original DWG/DXF INSUNITS=4; front 110 x 110 mm; catalog p14 M485 body depth 84.6 mm plus front projections.',
        projection_method='Original six native upper NOCOMM/M485 projections; manufacturer common mechanical outline, not confirmation of electrical performance from CAD.')
    options=[price_option(r) for r in selected]
    for o in options:o['configuration_evidence']=source['configuration_evidence']
    path=write_profile('GIMAC1000-EX-M485','LS · Đồng hồ GIMAC-1000 · EX · M485','METER',['GIMAC-1000 EX,M485'],None,options,scope['views'],source,{'Giao tiếp':'M485','Biến thể':'EX'})
    adds=[dict(profile=path.relative_to(CAT).as_posix(),models=[r['sku'] for r in selected],price_ids=[r['id'] for r in selected],faces=6,source=source)]
    (OUT/'additions.json').write_text(json.dumps(adds,ensure_ascii=False,indent=2),encoding='utf8')
