"""Publish actual plain-DC source-column front/side outlines, never 2a2b."""
import json,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from ezdxf import bbox
from import_ls_acb_full import groups
from ls_native_writer import ROOT,CAT,write_profile,price_option
OUT=ROOT/'docs/ls-targeted-review-2026-10-26'

def main():
    source=CAT/'LS/NguonBenNgoai/RU-660d12651a0f0c18'
    prices=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items']
    report=[]
    for frame,models in [('MC50-65',['MC-50a','MC-65a']),('MC75-100',['MC-75a','MC-85a','MC-100a'])]:
        doc=ezdxf.readfile(OUT/(frame+'-window.dxf'));assert doc.units==4 and not doc.audit().errors
        geometry=[(e,bbox.extents([e])) for e in doc.modelspace() if e.dxftype() in {'LINE','ARC','CIRCLE','SPLINE','ELLIPSE','LWPOLYLINE','POLYLINE'}]
        bands=groups([(b.extmin.x,b.extmax.x) for e,b in geometry if b.has_data]);assert len(bands)==3
        views=[]
        for code,label,band in [('FRONT','Mặt trước',bands[0]),('SIDE','Mặt bên',bands[1])]:
            es=[e for e,b in geometry if b.extmin.x>=band[0]-.001 and b.extmax.x<=band[1]+.001]
            views.append((code,label,es))
        rows=[r for r in prices if str(r.get('brand')).lower() in ['ls','ls electric'] and r.get('category')=='CONTACTOR' and r['sku'] in [m+' (VDC)' for m in models]]
        assert len(rows)==len(models) and all('1a1b' in str(r['specifications']) for r in rows)
        ev=json.loads((source/'source.json').read_text(encoding='utf8'))
        ev.update(source_dxf_sha256=hashlib.sha256((source/'source.dxf').read_bytes()).hexdigest(),native_style_preserved=True,
            reviewed_column='CONTACTOR DC; distinct from CONTACTOR 2a2b DC',reviewed_row=models,
            configuration_evidence='Manufacturer dimensional matrix separates plain DC from 2a2b DC. Plain DC front width 55 or 70 mm versus wider side auxiliary 2a2b frames; original complete front and side only, no assembly subtraction.',
            unit_evidence='Original INSUNITS=4; geometry preserved at native mm scale',six_views_verified=False,
            excluded_geometry='Third projection contains mounting holes and centerlines only; not published as a complete rear face.')
        profile=write_profile('PLAIN-DC-'+frame,'LS · Contactor · '+' / '.join(models)+' · 3P · DC · 1a1b',
            'CONTACTOR',models,'3P',[price_option(r) for r in rows],views,ev,
            {'Loại cuộn hút':'DC','Tiếp điểm phụ':'1a1b','Phạm vi CAD':'Hai mặt native của cột DC thường; không dùng cột 2a2b DC; chưa đủ sáu mặt'},native_document=doc)
        report.append(dict(profile=profile.relative_to(CAT).as_posix(),models=models,price_ids=[r['id'] for r in rows],views=2,evidence=ev))
    (OUT/'dc-additions.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    return report

if __name__=='__main__':main()
