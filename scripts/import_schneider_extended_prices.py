"""Read reviewed C120/iIDK/CVS/EasyTeSys sections of the official pricebook."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import pymupdf

ROOT=Path(__file__).resolve().parents[1]
SOURCE='https://www.se.com/vn/vi/download/document/MasterPriceBook/'
DOWNLOAD='https://download.schneider-electric.com/files?p_Doc_Ref=MasterPriceBook&p_File_Ext=.PDF'
MONEY=r'\d{1,3}(?:\.\d{3})+'


def extract(path):
    doc=pymupdf.open(path)
    if len(doc)!=282:raise ValueError('Expected reviewed 282-page master pricebook')
    rows=[];checksum=hashlib.sha256(path.read_bytes()).hexdigest()
    checked=datetime.now(timezone.utc).isoformat()
    def add(page,model,sku,category,poles,current,price,spec):
        spec={'Họ thiết bị':model,'Số cực':poles,'In (A)':str(current),**spec}
        rows.append(dict(id='schneider-2026-extended:'+sku,sku=sku,item_name=f'{model} {poles} {current}A',
            name=f'{model} {poles} {current}A',brand='Schneider Electric',category=category,
            group=category+' · '+spec.get('Họ thiết bị',model),
            price=int(price.replace('.','')),currency='VND',specifications=spec,
            columns=['Tên hàng','Mã đặt hàng','Thông tin','Giá bán'],
            cells=[f'{model} {poles} {current}A',sku,' · '.join(f'{k}: {v}' for k,v in spec.items()),price],
            source_label='Schneider Việt Nam 07/2026',source_url=SOURCE,download_url=DOWNLOAD,
            source_kind='supplier_pricebook',source_page=page,source_sha256=checksum,checked_at=checked,
            edition='07/2026',vat_status='included',price_note='Giá niêm yết đã gồm VAT; chọn cấu hình điện và kiểm tra CAD trước sử dụng.'))
    # Headers distinguish N/H and the left/right pole columns; never infer poles from ordering-code digits.
    text=doc[46].get_text(sort=True);model=None;left=right=None
    for line in text.splitlines():
        heading=re.search(r'C120([NH])\s*-\s*([13])P\s*&\s*([24])P',line)
        if heading:model='C120'+heading[1];left,right=heading[2]+'P',heading[3]+'P'
        matches=list(re.finditer(r'(A9N\d{5})\s+('+MONEY+r')',line))
        if not matches:continue
        if not model or not left:raise ValueError('Missing C120 column header')
        current=re.search(r'^\s*(?:C120\w*-\dP\s+)?(63|80|100|125)\s+',line)
        if not current:raise ValueError('Missing C120 current: '+line)
        for match in matches:
            x=next(w[0] for w in doc[46].get_text('words') if w[4]==match[1])
            poles=left if x<350 else right
            add(47,model,match[1],'MCB',poles,current[1],match[2],{'Họ thiết bị':'C120','Dòng sản phẩm':model,'Đặc tuyến':'C'})
    # Keep residual-current sensitivity as stated in each block; blank cells inherit within that block only.
    text=doc[48].get_text(sort=True);poles=None;residual=None
    for line in text.splitlines():
        heading=re.search(r'Acti\s*9\s+iIDK,\s*([24])P',line)
        if heading:poles=heading[1]+'P';residual=None
        if 'Acti9 iID RCCB' in line:break
        match=re.search(r'^\s*(25|40|63)\s+(?:(30|300)\s+)?(A9R\d{5})\s+('+MONEY+r')',line)
        if not match:continue
        if match[2]:residual=match[2]
        if not poles or not residual:raise ValueError('Missing iIDK configuration')
        add(49,'iIDK',match[3],'RCCB',poles,match[1],match[4],{'Dòng rò':residual+' mA','Loại dòng rò':'AC'})
    model=None
    for page in (58,59):
        for line in doc[page-1].get_text(sort=True).splitlines():
            if 'New Vigi Add-on' in line or 'Motor Mechanism' in line:break
            match=re.search(r'^\s*(?:(CVS\d+[BFN]S?)\s+)?(\d+)\s+(LV\d{6})\s+('+MONEY+r')\s+(LV\d{6})\s+('+MONEY+r')',line)
            if not match:continue
            if match[1]:model=match[1]
            if not model:raise ValueError('Missing CVS model')
            family=re.match(r'CVS\d+',model)[0]
            if family not in {'CVS100','CVS160','CVS250','CVS400','CVS630'}:
                continue  # source prints CVS639F; do not silently assign its continuation to CVS400F
            suffix=model[len(family)]
            for poles,sku,price in [('3P',match[3],match[4]),('4P',match[5],match[6])]:
                add(page,model,sku,'MCCB',poles,match[2],price,{'Họ thiết bị':model if model.endswith('BS') else family,'Dòng sản phẩm':model,
                    'Trip':'TMD','Icu (kA)':{'B':'25','F':'36','N':'50'}[suffix],'Điện áp Icu':'380 V' if model.endswith('BS') else '415 V'})
    for page,coil in ((164,'220 V AC'),(165,'24 V DC')):
        for line in doc[page-1].get_text(sort=True).splitlines():
            match=re.search(r'\b(LC1E(\d{2})(?:10|01)?(?:M7|BD))\s+('+MONEY+r')',line)
            if not match:continue  # starred entries explicitly require the current price to be requested
            code=match[1];model='LC1E'+match[2]
            add(page,model,code,'CONTACTOR','3P',int(match[2]),match[3],{'Mã thân':model,'Điện áp cuộn hút':coil})
    if len({r['sku'] for r in rows})!=len(rows):raise ValueError('Duplicate ordering codes')
    return rows


if __name__=='__main__':
    rows=extract(ROOT/'tmp/folder-web-review/schneider-2026.pdf')
    if len(rows)!=167:raise ValueError('Reviewed section counts changed; inspect the PDF before publishing')
    path=ROOT/'app/data/supplier_pricebooks.json';data=json.loads(path.read_text(encoding='utf8'))
    merged={r['id']:r for r in data['items'] if not r['id'].startswith('schneider-2026-extended:')};merged.update({r['id']:r for r in rows})
    data['items']=list(merged.values());path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Added reviewed rows:',len(rows))
