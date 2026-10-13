"""Import only complete five-field price sequences from the observed INVT PDF."""
import hashlib
import json
import re
import sys
from pathlib import Path
from datetime import datetime,timezone
import pymupdf

def import_book(source):
    doc=pymupdf.open(source);items=[];checked=datetime.now(timezone.utc).isoformat()
    checksum=hashlib.sha256(Path(source).read_bytes()).hexdigest()
    for number,page in enumerate(doc,1):
        lines=[re.sub(r'\s+',' ',line).strip() for line in page.get_text().splitlines() if line.strip()]
        supply=''
        for i,line in enumerate(lines):
            if line.startswith('Đầu vào'):supply=line.removeprefix('Đầu vào').strip()
            if not re.fullmatch(r'GD[A-Z0-9./-]+',line) or i+4>=len(lines):continue
            kw,hp,current,amount=lines[i+1:i+5]
            if not re.fullmatch(r'\d+(?:\.\d+)? kW',kw) or not re.fullmatch(r'\d+(?:\.\d+)? HP',hp):continue
            if not re.fullmatch(r'\d+(?:\.\d+)? A',current) or not re.fullmatch(r'\d{1,3}(?:\.\d{3})+',amount):continue
            specs={'Công suất':kw,'HP':hp,'In (A)':current,'Nguồn vào':supply}
            row_id=hashlib.sha1(f'{number}:{i}:{line}'.encode()).hexdigest()[:16]
            items.append({'id':'invt-pdf:'+row_id,'sku':line,'item_name':line,'name':line,'brand':'INVT',
                'category':'VFD','group':'Biến tần INVT','price':int(amount.replace('.','')),'currency':'VND',
                'columns':['Tên hàng']+list(specs)+['Giá bán'],'cells':[line]+list(specs.values())+[amount],
                'specifications':specs,'source_kind':'supplier_pricebook','source_label':'Tự Động Hóa Toàn Cầu · INVT',
                'source_url':'https://tudonghoatoancau.com/wp-content/uploads/2026/04/Bien-tan-Trung-Quoc-INVT.pdf',
                'source_page':number,'source_sha256':checksum,'checked_at':checked,'edition':None,
                'effective_date':None,'vat_status':'unknown','price_note':'Ngày áp dụng và VAT chưa xác định; không suy ra từ thư mục tải lên.'})
    path=Path(__file__).resolve().parents[1]/'app/data/supplier_pricebooks.json';data=json.loads(path.read_text(encoding='utf8'))
    data['items']=[r for r in data['items'] if r['brand']!='INVT']+items
    data['manufacturers']['INVT']={'imported_rows':len(items),'source_pages':len(doc),'coverage':'complete_model_kw_hp_current_price_sequences'}
    pending=path.with_suffix('.json.tmp');pending.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8');pending.replace(path)
    print(json.dumps({'accepted':len(items),'source_pages':len(doc)}))

if __name__=='__main__':import_book(sys.argv[1])
