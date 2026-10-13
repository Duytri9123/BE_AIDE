"""Import source table cells without expanding current ranges into invented SKUs."""
import hashlib,json,re,shutil,sys
from pathlib import Path
from datetime import datetime,timezone
import pymupdf

def split_position(page):
    edges={}
    for drawing in page.get_drawings():
        for item in drawing['items']:
            if item[0]!='re' or item[1].height<10: continue
            for x in (item[1].x0,item[1].x1):
                x=round(x,1);edges[x]=edges.get(x,0)+item[1].height
    xs=sorted(x for x,total in edges.items() if total>300 and page.rect.width*.38<x<page.rect.width*.6)
    gaps=[(a,b) for a,b in zip(xs,xs[1:]) if 5<b-a<25]
    if not gaps: raise ValueError('Cannot establish source table gutter')
    a,b=min(gaps,key=lambda pair:abs(sum(pair)/2-page.rect.width/2))
    return (a+b)/2

def category_for(group):
    text=group.upper()
    if 'PHỤ KIỆN' in text or 'CUỘN HÚT' in text:return 'ACCESSORY'
    for code in ('RCBO','RCCB','ELCB','MCB','MCCB','ACB'):
        if re.search(r'\b'+code+r'\b',text):return code
    if 'CHỐNG SÉT' in text:return 'SPD'
    if 'KHỞI ĐỘNG TỪ' in text:return 'CONTACTOR'
    if 'RƠ LE NHIỆT' in text:return 'THERMAL_RELAY'
    if 'MOTOR STARTER' in text:return 'MOTOR_PROTECTION'
    if 'ĐỒNG HỒ' in text:return 'METER'
    return 'RELAY' if 'RƠ LE' in text else 'ACCESSORY'

def import_book(source):
    root=Path(__file__).resolve().parents[1];source=Path(source)
    checksum=hashlib.sha256(source.read_bytes()).hexdigest();doc=pymupdf.open(source)
    date=re.search(r'Áp dụng từ ngày\s+(\d{2})-(\d{2})-(\d{4})',doc[0].get_text())
    if not date:raise ValueError('Missing effective date in source')
    effective=f'{date[3]}-{date[2]}-{date[1]}';checked=datetime.now(timezone.utc).isoformat();items=[]
    for number,page in enumerate(doc,1):
        split=split_position(page)
        for left,right in ((0,split),(split,page.rect.width)):
            for table in page.find_tables(clip=pymupdf.Rect(left,45,right,page.rect.height-20)).tables:
                group='';headers=[];previous_label='';current_category='ACCESSORY'
                above=page.get_text(clip=pymupdf.Rect(left,max(45,table.bbox[1]-24),right,table.bbox[1])).strip().splitlines()
                if above:group=above[-1]
                for index,raw in enumerate(table.extract()):
                    cells=[re.sub(r'\s+',' ',str(c or '')).strip() for c in raw]
                    if any(c=='Giá bán' for c in cells): headers=cells;continue
                    nonempty=[c for c in cells if c]
                    if len(nonempty)==1 and not re.fullmatch(r'[\d,.]+',nonempty[0]) and len(nonempty[0])<170:
                        group=nonempty[0];previous_label='';headers=[]
                        candidate_category=category_for(group)
                        if candidate_category!='ACCESSORY' or 'PHỤ KIỆN' in group.upper() or 'CUỘN HÚT' in group.upper():current_category=candidate_category
                        continue
                    if not cells or not re.fullmatch(r'\d{1,3}(?:,\d{3})+',cells[-1]):continue
                    if not any(cells[:-1]):continue
                    if not cells[0] and previous_label:cells[0]=previous_label
                    elif cells[0]:previous_label=cells[0]
                    if not headers or len(headers)!=len(cells):headers=['Tên hàng']+['Thông tin']*(len(cells)-2)+['Giá bán']
                    sku=cells[0]
                    # Accessory tables put the actual item identity in the second column.
                    if len(cells)>2 and cells[1] and re.search(r'\bfor\b',cells[1],re.I):
                        sku=cells[1];cells=[sku,cells[0],cells[-1]];headers=['Tên hàng','Loại phụ kiện','Giá bán'];current_category='ACCESSORY'
                    params={h:v for h,v in zip(headers[1:-1],cells[1:-1]) if v and h}
                    fingerprint=hashlib.sha1((str(number)+group+json.dumps(cells,ensure_ascii=False)).encode()).hexdigest()[:16]
                    items.append({'id':'ls-pdf:'+fingerprint,'sku':sku,'item_name':sku,'name':sku,'brand':'LS Electric',
                        'category':current_category if current_category!='ACCESSORY' else category_for(group),'group':group,'price':int(cells[-1].replace(',','')),
                        'currency':'VND','specifications':params,'columns':headers,'cells':cells,
                        'source_kind':'supplier_pricebook','source_label':'Bảng giá LS 01/10/2026',
                        'source_url':'/device-catalog/documents/ls-2026-10-01','source_page':number,
                        'source_filename':source.name,'source_sha256':checksum,'effective_date':effective,
                        'checked_at':checked,'vat_status':'excluded','price_note':'Giá bảng LS áp dụng 01/10/2026, chưa gồm VAT.'})
    # Primary identity is the item name inside each manufacturer; ratings remain variants.
    models={}
    for item in items:models.setdefault(item['item_name'],[]).append(item['id'])
    dest=root/'app/data/supplier_pricebooks.json';dest.write_text(json.dumps({'primary_key':'item_name','manufacturers':{'LS Electric':{'models':models}},'items':items},ensure_ascii=False,indent=2),encoding='utf8')
    pdf=root/'storage/catalog-pricebooks/ls-2026-10-01.pdf';pdf.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,pdf)
    print(json.dumps({'rows':len(items),'item_names':len(models),'pages':len(doc),'groups':sorted({i['group'] for i in items})},ensure_ascii=False))

if __name__=='__main__':import_book(sys.argv[1])
