"""Import only actual BK05S-T3 native outlines, rejecting mislabeled TS250."""
import json,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from ezdxf import bbox
from import_ls_wide_native_supplements import source_entities
from ls_native_writer import ROOT,CAT,write_profile,price_option
OUT=ROOT/'docs/ls-all-cad-2026-10-24'

def main():
    folder=CAT/'LS/NguonBenNgoai/2SK-BK05S-T3'
    doc=ezdxf.readfile(folder/'source.dxf');assert doc.units==4 and not doc.audit().errors
    texts=[e.dxf.text if e.dxftype()=='TEXT' else e.plain_text() for e in doc.modelspace() if e.dxftype() in ['TEXT','MTEXT']]
    assert 'BK05S-T3 2P,4P' in texts and '2P' in texts and '4P' in texts
    prices=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items']
    additions=[]
    for poles,window in [('2P',(3285,1310,3306,1405)),('4P',(3379,1310,3420,1405))]:
        rows=[r for r in prices if str(r.get('brand')).lower() in ['ls','ls electric'] and r.get('category')=='SPD' and r['sku']=='BK05S-T3 '+poles]
        assert len(rows)==1
        windows=[('FRONT','Mặt trước',window),('SIDE','Mặt bên',(3137,1310,3212,1405))]
        views=[(code,label,[e for e in source_entities(doc,w) if e.dxf.layer in ['0','HID']]) for code,label,w in windows]
        source=json.loads((folder/'source.json').read_text(encoding='utf8'))
        source.update(source_dxf_sha256=hashlib.sha256((folder/'source.dxf').read_bytes()).hexdigest(),
            native_style_preserved=True,review_status='native_model_and_pole_labels_verified_partial_views',
            six_views_verified=False,unit_evidence='Native INSUNITS=4, title block mm and 1:1. Geometry retained at source scale.',
            dimension_review='Some native dimensions have nominal text overrides (90 vs measured 90.517; 69.5 vs 70.377). No stretch or rescale applied; confirm installation dimensions before fabrication.',
            model_evidence='Title BK05S-T3 2P,4P plus separately labeled 2P and 4P front outlines; one common side outline on the same sheet.',
            reviewed_windows=[dict(face=c,window=w) for c,l,w in windows])
        path=write_profile('BK05S-T3-'+poles,'LS · SPD · BK05S-T3 · '+poles,'SPD',['BK05S-T3 '+poles],poles,
            [price_option(r) for r in rows],views,source,{'Phạm vi CAD':'Hai mặt gốc; thiếu sau, trái, phải, trên, dưới; không đủ sáu mặt để bố trí',
                'Kích thước':'Bản vẽ có kích thước danh định ghi đè; đối chiếu kích thước lắp thực tế trước gia công'},native_document=doc)
        additions.append(dict(model='BK05S-T3',poles=poles,profile=path.relative_to(CAT).as_posix(),price_ids=[r['id'] for r in rows],views=2,source=source))
    wrong=CAT/'LS/NguonBenNgoai/2SK-BK10-40S/source.json'
    d=json.loads(wrong.read_text(encoding='utf8'));d.update(review_status='rejected_for_spd_mislabeled_download',native_drawing_model='TS250 ATU',imported_to_catalog=False)
    wrong.write_text(json.dumps(d,indent=2),encoding='utf8')
    (OUT/'bk05s-additions-20261026.json').write_text(json.dumps(additions,ensure_ascii=False,indent=2),encoding='utf8')
    return additions

if __name__=='__main__':main()
