"""Import only explicit model -> material code -> VND price sequences."""
import json,re,hashlib,shutil,sys
from pathlib import Path
from datetime import datetime,timezone
import pymupdf
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.pricebook_columns import page_price_columns

def import_book(source):
    root=Path(__file__).resolve().parents[1];doc=pymupdf.open(source);items=[];quoted=0
    checked=datetime.now(timezone.utc).isoformat();checksum=hashlib.sha256(Path(source).read_bytes()).hexdigest()
    enriched=0
    for number,page in enumerate(doc,1):
        page_start=len(items)
        lines=[re.sub(r'\s+',' ',x).strip() for x in page.get_text().splitlines() if x.strip()]
        for n,line in enumerate(lines):
            match=re.fullmatch(r'VND (\d{1,3}(?:,\d{3})+)',line)
            if not match:continue
            quoted+=1
            if n<2 or not re.fullmatch(r'\d{5,8}|-',lines[n-1]):continue
            model=lines[n-2];code=lines[n-1]
            identity=re.sub(r'^BASE\s+','',model,flags=re.I)
            if not re.match(r'^[A-Z][A-Za-z0-9()/._-]*\d',identity) or len(model)>110:continue
            price=int(match[1].replace(',',''))
            prefix=model.split()[0]
            category=next((cat for stems,cat in [
                (('NXBLE','NB1L'),'RCBO'),(('NXB','NB1'),'MCB'),(('NM','NXM'),'MCCB'),
                (('NA','NXA'),'ACB'),(('NXC','NC1','NC2','NCH8'),'CONTACTOR'),(('NXR','NR2'),'THERMAL_RELAY'),
                (('ND16','ND9'),'LIGHT'),(('NJS','JSS','KG316'),'TIMER'),(('NP2','NP8'),'PUSHBUTTON'),
                (('XJ3-G',),'PHASE_RELAY'),
                (('NDK',),'TRANSFORMER'),
                (('RT28','RT36'),'FUSE'),(('NU6','NXU'),'SPD'),(('BH','LMZ','NCT'),'CT'),
                (('DTS','DT','DDS','DSS','PS','PA','PV','NP96','NP72'),'METER'),(('JQX','JZX','NJ','NXJ','JTX'),'RELAY'),
                (('YBLX',),'LIMIT_SWITCH')]
                if prefix.startswith(stems)), 'ACCESSORY')
            if re.fullmatch(r'NP2-E[DJG]\d+', model):
                category='SELECTOR_SWITCH'
            fingerprint=hashlib.sha1((str(number)+str(n)+model+code).encode()).hexdigest()[:16]
            items.append({'id':'chint-pdf:'+fingerprint,'sku':model,'item_name':model,'name':model,'brand':'CHINT',
                'category':category,'group':prefix.split('-')[0]+' · '+category,'price':price,'currency':'VND',
                'specifications':{'Mã đặt hàng':code},'columns':['Tên hàng','Mã đặt hàng','Giá bán'],
                'cells':[model,code,match[1]],'source_kind':'supplier_pricebook',
                'source_label':'Bảng giá CHINT 2026 · DGP','source_url':'/device-catalog/documents/chint-2026',
                'source_page':number,'source_sha256':checksum,'edition':'2026','effective_date':None,
                'checked_at':checked,'vat_status':'included' if 'Giá trên đã bao gồm VAT' in page.get_text() else 'unknown',
                'price_note':'Giá niêm yết CHINT 2026; ngày áp dụng cần đối chiếu nguồn.'})
        enriched+=page_price_columns(page,items[page_start:])
    target=root/'app/data/supplier_pricebooks.json';payload=json.loads(target.read_text(encoding='utf8'))
    payload['items']=[i for i in payload['items'] if i['brand']!='CHINT']+items
    models={}
    for item in items:models.setdefault(item['item_name'],[]).append(item['id'])
    payload['manufacturers']['CHINT']={'models':models}
    target.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf8')
    pdf=root/'storage/catalog-pricebooks/chint-2026.pdf';pdf.parent.mkdir(parents=True,exist_ok=True)
    if Path(source).resolve()!=pdf.resolve():shutil.copy2(source,pdf)
    print(json.dumps({'accepted_rows':len(items),'price_quotes':quoted,'model_names':len(models),'pages':len(doc),'rows_with_source_columns':enriched}))

if __name__=='__main__':import_book(sys.argv[1])
