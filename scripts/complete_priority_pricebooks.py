"""Scan every page of published pricebooks; import explicit product/price rows.

No CAD matching, family expansion, or invented ordering-code combinations.
Private page/position diagnostics stay in tmp; only product facts are published.
"""
import hashlib,json,re
from pathlib import Path
from collections import Counter
import pymupdf

ROOT=Path(__file__).resolve().parents[1]
BOOKS=[
 ('ABB','tmp/abb-2026.pdf','https://library.e.abb.com/public/8fa0d161aec14871ae110caa57108c49/9AKK108472A7059_vi_B_EL%20Vietnam%20Master%20price%20list%202026%20%28VIE%29.pdf','2026'),
 ('Schneider Electric','tmp/folder-web-review/schneider-2026.pdf','https://www.se.com/vn/vi/download/document/MasterPriceBook/','07/2026'),
 ('Shihlin','tmp/shihlin-pricebook.pdf','https://www.saigonelectric.vn/images/prices/SHIHLIN_01.02.2026.2.pdf','02/2026')]
MONEY=re.compile(r'^\d{1,3}(?:[,.]\d{3})+$')
def product_code(text,brand):
    text=text.strip(' ,;:®*')
    if brand=='ABB':return bool(re.fullmatch(r'[12][A-Z]{2,5}[A-Z0-9]{5,}',text))
    if brand=='Shihlin':return bool(re.fullmatch(r'(?:BHA|BHL|BHR|BMA?|BLA?|S-P|TH-P|SA|CU|RPC|ATS|CMD|SHT|UVT|LOK|MIL|MR-)[A-Za-z0-9./+_-]*\d[A-Za-z0-9./+_-]*',text))
    return bool(re.fullmatch(r'[A-Z][A-Z0-9./_-]{3,40}',text) and re.search(r'\d',text)
        and not re.match(r'^(?:IEC|EN\d|IP\d|ISO|CNS|GB\d|AC\d|DC\d|BS\d|IC\d|[A-Z]?\d+[AVWH]|I[CUNS]\d)',text))
def category(code,heading):
    if re.match(r'^(?:A9[RF]|R9[RF]|BHL|BHR)',code):return 'RCBO' if code.startswith(('A9D','R9D','BHL')) else 'RCCB'
    if re.match(r'^(?:ATV|AT[MV]|FRN)',code):return 'VFD'
    if re.match(r'^(?:LC1|LC2|S-P|1SBL)',code):return 'CONTACTOR'
    if re.match(r'^(?:TH-P|LRD|LR2|LR9)',code):return 'THERMAL_RELAY'
    if re.match(r'^(?:GV[234]|GZ)',code):return 'MOTOR_PROTECTION'
    if re.match(r'^(?:XB[457]|ZB[457])',code):return 'PUSHBUTTON'
    if re.match(r'^(?:BM|BL|LV[45]|C[123456][0-9])',code):return 'MCCB'
    if re.match(r'^(?:BHA|RPC|A9[FNPK]|R9[FN]|2CDS)',code):return 'MCB'
    if re.match(r'^(?:PM\d|METSE|A9MEM)',code):return 'METER'
    for word,kind in [('ACB','ACB'),('MCCB','MCCB'),('MCB','MCB'),('RCBO','RCBO'),('RCCB','RCCB'),('CONTAC','CONTACTOR'),('ATS','ATS')]:
        if word in heading.upper():return kind
    return 'ACCESSORY'
def main():
    payload=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))
    existing=[r for r in payload['items'] if not str(r.get('id','')).startswith('full-pricebook:')]
    known={(r['brand'],r.get('sku'),r.get('price'),r.get('source_page')) for r in existing}
    result=[];reports=[];private=[]
    for brand,file,url,edition in BOOKS:
        doc=pymupdf.open(ROOT/file);count=Counter();pages=[]
        for number,page in enumerate(doc,1):
            words=page.get_text('words')
            # Some PDFs split a printed model at the space after BM / BL.
            joined=[]
            if brand=='Shihlin':
                for w in words:
                    if w[4] not in {'BM','BMA','BL','BHA','S-P','TH-P'}:continue
                    following=[v for v in words if 0<=v[0]-w[2]<9 and abs(v[1]-w[1])<2 and re.match(r'^\d',v[4])]
                    if following:
                        v=min(following,key=lambda v:v[0]);joined.append((w[0],w[1],v[2],v[3],w[4]+v[4],*w[5:]))
            codes=[w for w in words+joined if product_code(w[4],brand)]
            prices=[w for w in words if MONEY.fullmatch(w[4]) and len(re.sub(r'\D','',w[4]))>=4]
            text=page.get_text();heading=' '.join(text.splitlines()[:9])
            vat='included' if re.search(r'(?:đã\s*)?bao gồm.*(?:VAT|GTGT)|incl[.]?\s*VAT',text,re.I) else 'excluded' if re.search(r'chưa.*(?:VAT|GTGT)',text,re.I) else 'unknown'
            claimed=set();matched_codes=set()
            for price in prices:
                cy=(price[1]+price[3])/2
                previous=max((w[2] for w in prices if w[2]<price[0] and abs((w[1]+w[3])/2-cy)<3),default=0)
                candidates=[w for w in codes if previous<w[0]<price[0] and abs((w[1]+w[3])/2-cy)<4]
                if not candidates:
                    count['unpaired_price_tokens']+=1;private.append({'brand':brand,'page':number,'price':price[4],'x':price[0],'y':price[1]});continue
                code=max(candidates,key=lambda w:w[0]);sku=code[4].strip(' ,;:®*')
                amount=int(re.sub(r'\D','',price[4]));matched_codes.add((code[0],code[1],code[4]));count['paired_price_tokens']+=1
                if (brand,sku,amount,number) in known:count['already_present']+=1;continue
                known.add((brand,sku,amount,number))
                left=previous+2
                desc=' '.join(w[4] for w in sorted(words,key=lambda w:w[0]) if left<=w[0]<code[0] and abs((w[1]+w[3])/2-cy)<4)
                desc=re.sub(r'\s+',' ',desc).strip()[:240]
                spec={}
                if desc:spec['Mô tả']=desc
                kind=category(sku,heading)
                name=desc if len(desc)>3 and re.search(r'[A-Za-zÀ-ỹ]',desc) else sku
                identifier=hashlib.sha256(f'{brand}:{number}:{round(code[0],1)}:{round(code[1],1)}:{sku}:{amount}'.encode()).hexdigest()[:24]
                result.append({'id':'full-pricebook:'+identifier,'brand':brand,'sku':sku,'item_name':name,'name':name,
                    'category':kind,'group':kind,'price':amount,'currency':'VND','specifications':spec,
                    'columns':['Tên hàng','Mã hàng','Giá bán'],'cells':[name,sku,str(amount)],
                    'source_kind':'supplier_pricebook','source_url':url,'source_page':number,
                    'edition':edition,'vat_status':vat,'checked_at':'2026-10-18'})
                count['new_priced_rows']+=1
            # Explicit unpriced accessory rows are useful too. Require a clear
            # accessory reference, not an illustrative family name in prose.
            if brand=='Shihlin':
                for code in codes:
                    sku=code[4].strip(' ,;:®*')
                    if not re.match(r'^(?:CMD|SHT|UVT|LOK|MIL)\d+$',sku):continue
                    if any(r['brand']==brand and r.get('sku')==sku for r in existing+result):continue
                    cy=(code[1]+code[3])/2
                    detail=' '.join(w[4] for w in words if w[0]>code[2] and abs((w[1]+w[3])/2-cy)<3)
                    identifier=hashlib.sha256(f'{brand}:{number}:{sku}'.encode()).hexdigest()[:24]
                    result.append({'id':'full-pricebook:'+identifier,'brand':brand,'sku':sku,'item_name':sku,'name':sku,
                        'category':'ACCESSORY','group':'Phụ kiện','price':None,'currency':'VND',
                        'specifications':{'Mô tả':detail} if detail else {},'source_kind':'manufacturer_catalog',
                        'columns':['Tên hàng','Mã hàng','Mô tả','Giá bán'],'cells':[sku,sku,detail,''],
                        'information_kind':'manufacturer_catalog','source_url':url,'source_page':number,
                        'edition':edition,'checked_at':'2026-10-18'})
                    count['new_unpriced_rows']+=1
            pages.append({'page':number,'price_tokens':len(prices),'model_tokens':len(codes)})
        reports.append({'brand':brand,'pages_scanned':len(doc),**count})
        print(json.dumps(reports[-1]),flush=True)
    target=ROOT/'app/data/supplier_pricebooks.json'
    payload['items']=existing+result
    target.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    out=ROOT/'tmp/priority-pricebooks';out.mkdir(exist_ok=True)
    (out/'unpaired-prices.json').write_text(json.dumps(private,ensure_ascii=False),encoding='utf8')
    (ROOT/'docs/priority-pricebook-source-scan.json').write_text(json.dumps({'books':reports},indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
