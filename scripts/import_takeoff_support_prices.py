"""Import visually reviewed exact fan/ATS rows from supplier PDF tables."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import pymupdf

ROOT=Path(__file__).resolve().parents[1]
FAN_SOURCE='https://dge.vn/uploads/bao-gia/435736_20260114_122258.pdf'
ATS_SOURCE='https://etinco.vn/wp-content/uploads/2025/05/bang-gia-bo-chuyen-nguon-ats-osemco-osung.pdf'


def row(source, path, page, brand, category, model, poles, current, price, edition, spec):
    sku=model+(f' {poles}P' if poles else '')
    return dict(id='reviewed-pdf:'+hashlib.sha1((source+'|'+sku).encode()).hexdigest()[:16],
        sku=sku,item_name=sku,name=sku,brand=brand,category=category,price=price,currency='VND',
        group=('Quạt thông gió' if category=='FAN' else 'ATS')+' · '+model,
        source_label=brand+' · '+edition,source_url=source,source_kind='supplier_pricebook',
        source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),source_page=page,
        checked_at=datetime.now(timezone.utc).isoformat(),edition=edition,
        vat_status='excluded',
        effective_date='2026-03-15' if category=='ATS' else None,
        price_note='Giá trong bảng nhà cung cấp; cần xác nhận tồn kho trước đặt hàng.',
        specifications={**spec,**({'Số cực':f'{poles}P','In (A)':str(current)} if poles else {})},
        columns=['Tên hàng','Thông tin','Giá bán'],
        cells=[sku,' · '.join(f'{k}: {v}' for k,v in spec.items())+(f' · {poles}P · {current}A' if poles else ''),str(price)])


def extract(fan_path, ats_path):
    rows=[]
    fan=pymupdf.open(fan_path)[3].get_text(sort=True)
    for model,price in re.findall(r'\b(FKL662[123]\.230)\s+Cái\s+(\d{1,3}(?:,\d{3})+)',fan):
        rows.append(row(FAN_SOURCE,fan_path,4,'Leipole','FAN',model,0,0,int(price.replace(',','')),'01/2026',
            {'Điện áp':'230 VAC','Màu':'RAL7032','Cấp bảo vệ':'IP54','Bộ sản phẩm':'Quạt kèm miệng gió có lọc bụi'}))
    if len(rows)!=3:raise ValueError('Expected three explicit FKL66 fan rows')
    ats=pymupdf.open(ats_path)[0].get_text(sort=True)
    if '15.03.2026' not in ats:raise ValueError('Expected ATS effective date')
    matches=re.findall(r'\b(OSS-\d+-(?:PC|TN))\s+(\d+)A\s+(ON-OFF-ON|ON-ON)\s+(\d{1,3}(?:,\d{3})+)\s+(\d{1,3}(?:,\d{3})+)',ats)
    if len(matches)!=14:raise ValueError('Expected 14 ATS models with separate 3P/4P prices')
    for model,current,cycle,three,four in matches:
        for poles,price in zip((3,4),(three,four)):
            rows.append(row(ATS_SOURCE,ats_path,1,'O-Sung / OSEMCO','ATS',model,poles,int(current),
                int(price.replace(',','')),'15/03/2026',{'Chu kỳ':cycle}))
    return rows


if __name__=='__main__':
    rows=extract(ROOT/'tmp/folder-web-review/leipole-2026.pdf',ROOT/'tmp/folder-web-review/osemco-2026.pdf')
    target=ROOT/'app/data/supplier_pricebooks.json'
    payload=json.loads(target.read_text(encoding='utf8'))
    merged={r['id']:r for r in payload['items']}
    merged.update({r['id']:r for r in rows})
    payload['items']=list(merged.values())
    target.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps([(r['sku'],r['price']) for r in rows]))
