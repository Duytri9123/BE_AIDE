"""Restore commercial family metadata from explicit manufacturer model syntax.

Preserves price, source ID and selected ratings. Does not approve CAD geometry.
"""
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LS_SOURCE='https://www.ls-electric.com/ko/cat/%5BSusol%20MCCB%5D_Catalog_EN_202006.pdf'
SE_SOURCE='https://www.se.com/ph/en/product/EZC100H1015/circuit-breaker-easypact-ezc100h-tmd-15-a-1-pole-1d/'


def review(row):
    name=str(row.get('item_name') or '').upper()
    source=None
    spec=dict(row.get('specifications') or {})
    if row.get('brand')=='LS Electric' and row.get('category')=='MCCB':
        model=re.match(r'^((?:TD|TS)(?:100|160|250|400|630|800|1000|1250|1600))[NHL](?=\s)',name)
        if model:
            spec['Họ thiết bị']=model[1];source=LS_SOURCE
    elif row.get('brand')=='Schneider Electric' and row.get('category')=='MCCB':
        model=re.fullmatch(r'(EZC(?:100|250|400))[BFHN]([1-4])(\d{3})N?',str(row.get('sku') or '').upper())
        if model:
            spec.update({'Họ thiết bị':model[1],'Số cực':model[2]+'P','In (A)':str(int(model[3]))})
            source=SE_SOURCE
    if not source:return False
    row['specifications']=spec
    row['identity_metadata_review']={'source_url':source,'checked_date':'2026-10-14',
        'note':'Manufacturer frame/model syntax reviewed. Commercial choices only; retain original price and row ID.'}
    return True


if __name__=='__main__':
    for filename in ('supplier_pricebooks.json','web_catalog_offers.json'):
        path=ROOT/'app/data'/filename
        data=json.loads(path.read_text(encoding='utf8'))
        count=sum(review(row) for row in data['items'])
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        print(filename,count)
