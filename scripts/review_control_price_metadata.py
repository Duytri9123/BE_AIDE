"""Repair explicit accessory and switched-neutral model metadata, retaining prices."""
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
UA_SOURCE='https://gics.ls-electric.com/knowledgeBase/user/detail.do?baseId=170'
BH_SOURCE='https://www.mitsubishielectric.com/fa/sg_en/products/faspec/detail.page?category=ex&formNm=MCB_BH-DN_4892&id=spec&kisyu=%2Flvcb&lang=2'


def review(row):
    source=None
    name=str(row.get('item_name') or '')
    spec=dict(row.get('specifications') or {})
    if row.get('brand')=='LS Electric' and re.fullmatch(r'UA-1 \(bên hông\)',name):
        row['category']='AUX_CONTACT';row['group']='Tiếp điểm phụ · UA-1';source=UA_SOURCE
    elif row.get('brand')=='Mitsubishi Electric' and row.get('category')=='MCB' and re.fullmatch(r'BH-DN 1PN (?:6|10|16|20)A C',name):
        spec['Số cực']='1P+N';source=BH_SOURCE
    elif row.get('brand')=='Schneider Electric' and row.get('category')=='CONTACTOR':
        model=re.fullmatch(r'(LC1D(?:09|12|18|25|32|38))B7',str(row.get('sku') or '').upper())
        if model:
            spec.update({'Mã thân':model[1],'Số cực':'3P','Điện áp cuộn hút':'24V AC'})
            source='https://iportal.se.com/Contents/docs/SQD-LC1D25B7.PDF'
        elif str(row.get('sku') or '').upper() in {'LC1D098B7','LC1D128B7'}:
            spec.update({'Mã thân':row['sku'][:-2].upper(),'Số cực':'4P','Điện áp cuộn hút':'24V AC'})
            source='https://www.se.com/in/en/product/LC1D098B7/tesys-d-contactor-4p2-no-%2B-2-nc-ac1-440-v-20-a-24-v-ac-coil/'
    elif row.get('brand')=='Mikro' and row.get('sku')=='DIN310-230A':
        row['category']='EARTH_LEAKAGE_RELAY';row['group']='Rơ le dòng rò · DIN310'
        spec.pop('In (A)',None)
        spec.update({'Họ thiết bị':'DIN310','Điện áp cấp phụ trợ':'230V AC','Dải điện áp cấp phụ trợ':'184–276V AC'})
        source='https://itmikro.com.my/wp-content/uploads/2020/08/din310_man-1.pdf'
    if not source:return False
    row['specifications']=spec
    row['identity_metadata_review']={'source_url':source,'checked_date':'2026-10-14',
        'note':'Explicit manufacturer accessory type or switched-neutral configuration. Original price and row ID preserved.'}
    return True


if __name__=='__main__':
    for filename in ('supplier_pricebooks.json','web_catalog_offers.json'):
        path=ROOT/'app/data'/filename
        data=json.loads(path.read_text(encoding='utf8'))
        print(filename,sum(review(row) for row in data['items']))
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
