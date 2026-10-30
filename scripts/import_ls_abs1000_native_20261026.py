"""Exact manufacturer ABS1003b/1004b label, native terminal-bar configuration."""
import json,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from ezdxf import bbox
from ls_native_writer import ROOT,CAT,write_profile,price_option
OUT=ROOT/'docs/ls-targeted-review-2026-10-26'

def main():
    folder=CAT/'LS/NguonBenNgoai/45195';doc=ezdxf.readfile(folder/'source.dxf')
    assert not doc.audit().errors
    text=' '.join(e.dxf.text for e in doc.modelspace() if e.dxftype()=='TEXT')
    assert 'ABS 1003b, 1004b, 1203b, 1204b' in text
    dims=[e for e in doc.modelspace() if e.dxftype()=='DIMENSION']
    assert len(dims)>50 and all(abs(e.override().get('dimlfac',1)-1)<.0001 for e in dims)
    assert any(abs(e.get_measurement()-400)<.001 and not e.dxf.get('text') for e in dims)
    geo=[(e,bbox.extents([e])) for e in doc.modelspace() if e.dxf.layer=='3' and e.dxftype() in {'LINE','ARC','CIRCLE','SPLINE','LWPOLYLINE','POLYLINE','ELLIPSE'}]
    def crop(x,X):return [e for e,b in geo if b.has_data and b.extmin.x>=x and b.extmax.x<=X and b.extmin.y>1100 and b.extmax.y<1800]
    side=crop(1500,1800);assert len(side)>25
    prices=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'];report=[]
    for model,poles,x,X,width in [('ABS1003b','3P',100,400,220),('ABS1004b','4P',570,900,290)]:
        front=crop(x,X);assert abs(bbox.extents(front).size.x-width)<.01
        rows=[r for r in prices if r['sku']==model and str(r.get('brand')).lower() in ['ls','ls electric']];assert len(rows)==1
        ev=json.loads((folder/'source.json').read_text(encoding='utf8'))
        ev.update(source_dxf_sha256=hashlib.sha256((folder/'source.dxf').read_bytes()).hexdigest(),native_style_preserved=True,
            unit_evidence='Original INSUNITS=0; native 400 mm body dimension measures 400, all dimension scale factors=1; no geometric scaling.',
            reviewed_models=[model],model_evidence='Explicit manufacturer title ABS 1003b,1004b,1203b,1204b and separate 3P/4P outlines.',
            configuration='Native terminal-bar outline; family reference only. No parent electrical rating or ordering SKU inferred.',six_views_verified=False)
        path=write_profile(model+'-NATIVE-BARS','LS · MCCB · '+model+' · '+poles+' · Có thanh đầu nối','MCCB',[model],poles,[price_option(r) for r in rows],
            [('FRONT','Mặt trước',front),('SIDE','Mặt bên',side)],ev,{'Kiểu đầu nối theo CAD':'Có thanh đầu nối theo bản vẽ hãng','Phạm vi CAD':'Hai mặt gốc; chưa đủ sáu mặt'},native_document=doc)
        report.append(dict(profile=path.relative_to(CAT).as_posix(),models=[model],price_ids=[r['id'] for r in rows],views=2,evidence=ev))
    (OUT/'mccb-additions.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    return report

if __name__=='__main__':main()
