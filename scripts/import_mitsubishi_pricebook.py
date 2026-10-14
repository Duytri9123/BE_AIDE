"""Read labelled model/material/price columns from the June-2026 supplier workbook."""
import hashlib
import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone
import openpyxl

SOURCE_URL='https://www.saigonelectric.vn/images/prices/Mitsubishi_Summary_LVS_06.2026.2.xlsx'

def import_book(source):
    workbook=openpyxl.load_workbook(source,read_only=True,data_only=True)
    checked=datetime.now(timezone.utc).isoformat()
    checksum=hashlib.sha256(Path(source).read_bytes()).hexdigest()
    items=[];audit={}
    for sheet in workbook:
        pairs=[];shared_capacity='';shared_capacity_row=0;local_capacity={};accepted=0;field_headers={}
        for number,row in enumerate(sheet.iter_rows(values_only=True),1):
            values=[str(v).strip() if v is not None else '' for v in row]
            headers=[i for i,v in enumerate(values) if 'unit price' in v.lower()]
            if headers:
                pairs=[];local_capacity={}
                field_headers={i:v.splitlines()[0].strip() for i,v in enumerate(values) if v}
                if number-shared_capacity_row>2:shared_capacity=''
                for price_col in headers:
                    model_cols=[i for i in range(price_col) if 'model name' in values[i].lower()]
                    code_cols=[i for i in range(price_col) if 'material code' in values[i].lower()]
                    if model_cols and code_cols and max(model_cols)<max(code_cols):
                        pairs.append((max(model_cols),max(code_cols),price_col))
                continue
            if not pairs:continue
            has_price=any(isinstance(row[p],(int,float)) and not isinstance(row[p],bool) and row[p]>0 for _,_,p in pairs)
            if not has_price:
                for model,_,_ in pairs:
                    if re.search(r'\bIcu\s*=',values[model],re.I):local_capacity[model]=values[model].splitlines()[0]
                for i,value in enumerate(values):
                    if i not in {m for m,_,_ in pairs} and re.search(r'\bIcu\s*=',value,re.I):
                        shared_capacity=value.splitlines()[0];shared_capacity_row=number;local_capacity={}
                continue
            for model_col,code_col,price_col in pairs:
                model,code,price=values[model_col],values[code_col],row[price_col]
                if not isinstance(price,(int,float)) or isinstance(price,bool) or price<=0 or int(price)!=price:continue
                if not model or not code or not re.search(r'\d',model) or not re.match(r'^[A-Z]',model):continue
                category=('ACCESSORY' if 'Accessory' in sheet.title else 'ACB' if sheet.title.startswith('ACB')
                          else 'MCB' if sheet.title.startswith('MCB') else 'ELCB' if sheet.title.startswith('ELCB')
                          else 'MCCB' if sheet.title.startswith('MCCB') else 'CONTACTOR' if sheet.title=='S-T S-N'
                          else 'THERMAL_RELAY' if sheet.title=='TH-T TH-N' else 'CB' if sheet.title=='CP'
                          else 'RELAY' if 'Relay' in sheet.title else 'METER')
                if re.match(r'^BV-D(?:\s|$)',model):category='RCCB'
                specs={'Mã đặt hàng':code}
                poles=re.search(r'\b([1-4]P(?:\+N)?)\b',model)
                current=re.search(r'\b(\d+(?:\.\d+)?)A\b',model)
                if poles:specs['Số cực']=poles[1]
                if current:specs['In (A)']=current[1]
                capacity=local_capacity.get(model_col) or shared_capacity
                if capacity:specs['Khả năng cắt và điện áp']=capacity
                # Other labelled source columns belong to the same row, no forward-fill.
                if len(pairs)==1:
                    for i,value in enumerate(values[:model_col]):
                        label=field_headers.get(i)
                        if label and value and len(value)<700 and not value.startswith('*'):
                            specs.setdefault(label,re.sub(r'\s+',' ',value))
                columns=['Tên hàng']+list(specs)+['Giá bán'];cells=[model]+list(specs.values())+[str(int(price))]
                fingerprint=hashlib.sha1(f'{sheet.title}:{number}:{price_col}:{code}'.encode()).hexdigest()[:16]
                items.append({'id':'mitsubishi-xlsx:'+fingerprint,'sku':code,'item_name':model,'name':model,
                    'brand':'Mitsubishi Electric','category':category,'group':sheet.title,'price':int(price),'currency':'VND',
                    'specifications':specs,'columns':columns,'cells':cells,'source_kind':'supplier_pricebook',
                    'source_label':'Mitsubishi 06-2026 · Điện Sài Gòn','source_url':SOURCE_URL,
                    'source_sheet':sheet.title,'source_row':number,'source_sha256':checksum,
                    'edition':'06/2026','effective_date':None,'vat_status':'unknown','checked_at':checked,
                    'price_note':'Ngày áp dụng và VAT chưa xác định trong bảng; không suy ra từ ngày đăng.'})
                accepted+=1
        audit[sheet.title]=accepted
    root=Path(__file__).resolve().parents[1];path=root/'app/data/supplier_pricebooks.json'
    payload=json.loads(path.read_text(encoding='utf8'))
    payload['items']=[r for r in payload['items'] if r['brand']!='Mitsubishi Electric']+items
    payload['manufacturers']['Mitsubishi Electric']={'sheets':audit,'coverage':'explicit_labelled_model_material_numeric_price_rows'}
    pending=path.with_suffix('.json.tmp');pending.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf8');pending.replace(path)
    print(json.dumps({'accepted':len(items),'sheets':audit}))

if __name__=='__main__':import_book(sys.argv[1])
