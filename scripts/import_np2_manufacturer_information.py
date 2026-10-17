"""Import explicitly printed NP2 catalog rows; never turn wildcards into SKUs."""
import argparse
import json
import re
from pathlib import Path
import pymupdf

ROOT=Path(__file__).resolve().parents[1]
URL='https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/industrial-control/push-button/np2/catalog/NP2-PUSH-BUTTON-Catalog.pdf'
MODEL=re.compile(r'(NP2-[A-Z]+[0-9][A-Z0-9]*)(?:\s+([0-9]+V)\s+LED)?')


def extract(document):
    rows={}
    for index,page in enumerate(document):
        # This manufacturer's NP2 section ends before the NP3/other series.
        if index>=17:break
        lines=[line.strip() for line in page.get_text().splitlines()]
        for pos,line in enumerate(lines):
            match=MODEL.fullmatch(line)
            if not match:continue
            sku=match[1];spec={'Tên hàng':'CHINT '+line,'Dòng sản phẩm':'NP2'}
            # Keep the voltage printed in this row, never the entire family's range.
            if match[2]:spec['Điện áp đèn theo cấu hình catalog']=match[2];spec['Loại đèn']='LED'
            contacts=lines[pos+1:pos+3]
            if len(contacts)==2 and all(re.fullmatch(r'[0-9]+|-',v) for v in contacts):
                spec['Tiếp điểm NO']=0 if contacts[0]=='-' else int(contacts[0])
                spec['Tiếp điểm NC']=0 if contacts[1]=='-' else int(contacts[1])
            # Voltage is part of the configuration identity when explicitly given.
            key=(sku,match[2] or '')
            row={'id':'external:chint:'+sku.lower()+(':'+match[2].lower() if match[2] else ''),
                 'brand':'CHINT','sku':sku,'item_name':spec['Tên hàng'],'name':spec['Tên hàng'],
                 'category':'CONTROL_COMPONENT','group':'CHINT NP2 · mã và phụ kiện điều khiển',
                 'specifications':spec,'columns':['Tên hàng','Thông số'],
                 'cells':[spec['Tên hàng'],'; '.join(f'{k}: {v}' for k,v in spec.items() if k!='Tên hàng')],
                 'price':None,'source_url':URL,'source_page':index+1}
            previous=rows.get(key)
            if previous:
                for field in ('Tiếp điểm NO','Tiếp điểm NC'):
                    if field in previous['specifications'] and field in spec and previous['specifications'][field]!=spec[field]:
                        raise ValueError(f'Conflicting manufacturer contact values for {sku}')
                if len(previous['specifications'])>=len(spec):continue
            rows[key]=row
    return list(rows.values())


def main():
    parser=argparse.ArgumentParser();parser.add_argument('pdf',type=Path);args=parser.parse_args()
    with pymupdf.open(args.pdf) as document:rows=extract(document)
    path=ROOT/'app/data/external_product_information.json';payload=json.loads(path.read_text(encoding='utf8'))
    payload['items']=[r for r in payload['items'] if not str(r.get('id','')).startswith('external:chint:np2-')]+rows
    path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'manufacturer':'CHINT','np2_configurations':len(rows),'np2_unique_codes':len({r['sku'] for r in rows}),'with_contact_facts':sum('Tiếp điểm NO' in r['specifications'] for r in rows)}))


if __name__=='__main__':main()
