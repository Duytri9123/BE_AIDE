"""Repair price metadata against explicit manufacturer model tables, retaining prices/IDs."""
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCES={
 'bv':'https://www.mitsubishielectric.com/fa/sg_en/products/faspec/detail.page?category=ex&formNm=RCCB_RCBO_BV-D_4885&id=spec&kisyu=%2Flvcb&lang=2',
 'st':'https://www.mitsubishielectric.com/dl/fa/document/catalog/lvsw/sh020011eng/SH%28NA%29020011ENG-A.pdf',
 'xj':'https://www.chintglobal.com/global/en/products/low-voltage/iec/industrial-control/xj3.html',
 'np':'https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/industrial-control/push-button/np2/catalog/NP2-Push-button-Catalog.pdf',
 'ic':'https://eshop.se.com/sg/ic60n-miniature-circuit-breaker-3p-2a-c-curve-a9f74302.html',
 'om':'https://www.ia.omron.com/products/family/3460/lineup.html',
}


def repair(row):
    name=str(row.get('item_name') or row.get('sku') or '')
    maker=row.get('brand');source=None
    spec=row.get('specifications') or {}
    if maker=='Mitsubishi Electric' and re.match(r'^BV-D\s+[24]P\s',name):
        row['category']='RCCB';row['group']='RCCB · BV-D';source=SOURCES['bv']
    elif maker=='Mitsubishi Electric' and row.get('category')=='CONTACTOR' and re.match(r'^S-T(?:10|12|20|21|25|35|50)\s',name):
        spec['Số cực']='3P';source=SOURCES['st']
    elif maker=='CHINT' and re.fullmatch(r'XJ3-G AC380V',name):
        row['category']='PHASE_RELAY';row['group']='XJ3 · PHASE_RELAY';source=SOURCES['xj']
    elif maker=='CHINT' and re.fullmatch(r'NP2-EA\d+',name) and row.get('category')=='PUSHBUTTON':
        spec['Họ thiết bị']='NP2';source=SOURCES['np']
    elif maker=='Schneider Electric' and name.upper()=='IC60N' and row.get('category')=='MCB':
        spec['Họ thiết bị']='IC60';source=SOURCES['ic']
    elif maker=='Omron' and row.get('sku')=='-S8FS-C05024J' and row.get('name')=='Bộ nguồn Omron-S8FS-C05024J':
        row['sku']='S8FS-C05024J';row['category']='POWER_SUPPLY';source=SOURCES['om']
    if source:
        row['specifications']=spec
        row['identity_metadata_review']={'source_url':source,'checked_date':'2026-10-14',
                                         'note':'Reviewed manufacturer type/family/poles. Price and source row ID retained; no CAD geometry or automatic variant approval.'}
    return bool(source)


if __name__=='__main__':
    for filename in ('supplier_pricebooks.json','web_catalog_offers.json'):
        path=ROOT/'app/data'/filename
        data=json.loads(path.read_text(encoding='utf8'))
        count=sum(repair(row) for row in data['items'])
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        print(filename,count)
