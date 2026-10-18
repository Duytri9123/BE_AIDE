"""Reviewed historical supplier rows for otherwise uncovered library makers.

Dates/editions remain visible; these are published references, not new quotes.
PDFs must first be downloaded and visually reviewed in tmp/.
"""
import hashlib
import json
import re
from datetime import datetime,timezone
from pathlib import Path
import pymupdf

ROOT=Path(__file__).resolve().parents[1]
SOURCES={
 'morele':('2021','https://vanvh.com/upload/files/BG2021morele1.pdf'),
 'lightstar':('2022','https://www.thegioidien.com/PrPricelist/Lightstar-Pricelist-2022.pdf'),
 'smartgen':('2023','https://diencongnghiephcm.com/wp-content/uploads/2023/10/BANG-GIA-SMARTGEN-DEEPSEA-2023.pdf')}


def main():
    rows=[]
    checked=datetime.now(timezone.utc).isoformat()
    def add(key,page,brand,sku,kind,price,spec,identity):
        edition,url=SOURCES[key]
        digest=hashlib.sha256((ROOT/f'tmp/{key}-external-pricebook.pdf').read_bytes()).hexdigest()
        cols=['Tên hàng',*spec,'Đơn giá']
        rows.append(dict(id='reviewed-pdf:'+hashlib.sha1((url+identity).encode()).hexdigest()[:20],
            sku=sku,item_name=sku,name=sku,brand=brand,category=kind,price=price,currency='VND',
            group=kind+' · '+edition,source_url=url,source_label='Bảng giá '+brand+' '+edition,
            source_kind='supplier_pricebook',source_page=page,source_sha256=digest,
            source_line=identity,edition=edition,effective_date='2021-04-01' if key=='morele' else '2023-07-01' if key=='smartgen' else None,
            checked_at=checked,vat_status='excluded' if key in {'morele','lightstar'} else 'unknown',
            specifications=spec,columns=cols,cells=[sku,*spec.values(),f'{price:,}'],
            price_note=f'Giá trong bản công bố {edition}; cần xác nhận báo giá hiện hành, không phải báo giá mới năm 2026.'))
    doc=pymupdf.open(ROOT/'tmp/morele-external-pricebook.pdf')
    for table in doc[0].find_tables().tables:
        for n,cells in enumerate(table.extract()):
            if len(cells)!=5:continue
            name,ratio,maker,unit,amount=[(s or '').strip() for s in cells]
            match=re.fullmatch(r'(MSQ-\s*\d+)\s+(\d+/5)\s+CLASS(\d)',name)
            if not match or maker!='MORELE/ CHINA' or not re.fullmatch(r'\d{1,3}(?:,\d{3})+',amount):continue
            # Source has a 75/5 title with a 50/5 code; leave that conflict out.
            if match[2]!=ratio:continue
            model=match[1].replace(' ','')
            add('morele',1,'Morele',model+' '+ratio+'A','CT',int(amount.replace(',','')),
                {'Họ thiết bị':model,'Tỷ số CT':ratio+'A','Cấp chính xác':match[3]},name+'|'+str(n))
    for table in doc[1].find_tables().tables:
        for cells in table.extract():
            if len(cells)!=5:continue
            description,sku,maker,unit,amount=[(s or '').strip() for s in cells]
            if sku not in {'RT18-32','AD22'} or maker!='MORELE/ CHINA' or not re.fullmatch(r'\d{1,3}(?:,\d{3})+',amount):continue
            kind='FUSE_HOLDER' if sku=='RT18-32' else 'BUZZER'
            spec={'Phạm vi giá':description} if sku=='RT18-32' else {'Mô tả':description,'Điện áp':'220VAC'}
            add('morele',2,'Morele',sku,kind,int(amount.replace(',','')),spec,sku)
    doc=pymupdf.open(ROOT/'tmp/lightstar-external-pricebook.pdf')
    for page_no in (8,9,10):
        for table in doc[page_no-1].find_tables().tables:
            for n,cells in enumerate(table.extract()):
                if len(cells)!=5:continue
                _,sku,description,variants,amount=[(s or '').strip() for s in cells]
                if not re.fullmatch(r'KB[DFCK]-\d+[A-Z]*',sku) or not re.fullmatch(r'\d{1,3}(?:,\d{3})+',amount):continue
                add('lightstar',page_no,'LightStar',sku,'CT',int(amount.replace(',','')),
                    {'Mô tả':description.replace('\n',' '),'Cấu hình theo bảng giá':variants.replace('\n',' ')},sku+'|'+str(n))
    # Inspected page 1 groups these exact models under one common price cell.
    for models,amount in [('HAT310',1200000),('HAT520N HAT530N',1800000),('HAT552 HAT553',2000000),
                          ('HAT560N HAT560NB HAT560NBC',3200000),('HAT600N HAT600NB HAT600NBC',3800000),('HAT700 HAT700B',4500000)]:
        for sku in models.split():
            add('smartgen',1,'SmartGen',sku,'ATS_CONTROLLER',amount,{'Loại':'Bộ điều khiển ATS'},sku)
    for sku,amount in [('DSE6110-MKII',7200000),('DSE6120-MKII',7200000),('DSE7310 MKII',8500000),
                       ('DSE7320 MKII',8500000),('DSE8610 MKII',30000000)]:
        add('smartgen',3,'Deep Sea Electronics',sku,'GENERATOR_CONTROLLER',amount,{'Loại':'Bộ điều khiển máy phát điện'},sku)
    path=ROOT/'app/data/supplier_pricebooks.json'
    data=json.loads(path.read_text(encoding='utf8'));merged={r['id']:r for r in data['items']}
    for row in rows:merged[row['id']]=row
    data['items']=list(merged.values())
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    from collections import Counter
    print(dict(Counter(r['brand'] for r in rows)))


if __name__=='__main__':main()
