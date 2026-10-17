"""Import explicit LS model/order-number pairs from official technical catalogs."""
import json
import re
from pathlib import Path
import pymupdf

ROOT=Path(__file__).resolve().parents[1]
CATALOGS=[('2022-04','ls-mcb-2022.pdf','https://tbs.ls-electric.com/tbsdata/FileRepository/CTLG/%5BMCB%5D%20MCB_RCD_Catalog_EN_202204.pdf'),
          ('2018','ls-mcb-2018.pdf','https://www.ls-electric.com/upload/customer/download/1483/MCB_E_180131.pdf')]
LINE=re.compile(r'(BKN(?:-[bc])?|BKH|BKD|BKP|BFN)\s+([1-4]P(?:\s*\+\s*N)?)\s+([BCD]?)(\d+(?:\.\d+)?)A',re.I)
KGR=re.compile(r'(32KGR[cd])\s+(15|20|30)A\s+(15|30)mA\s+0\.03s',re.I)
BKP=re.compile(r'BKP\s+([BCD])(\d+)A',re.I)
ORDER=re.compile(r'[0-9]{8,12}(?:R[0-9]+)?')

def extract(document,edition,url):
    rows=[]
    for page_no,page in enumerate(document,1):
        lines=[s.strip() for s in page.get_text().splitlines()]
        for i,line in enumerate(lines[:-1]):
            match=LINE.fullmatch(line);kgr=KGR.fullmatch(line)
            bkp=BKP.fullmatch(line) if '1P+N' in lines and 'BKP type' in lines else None
            order=lines[i+1]
            if not (match or kgr or bkp) or not ORDER.fullmatch(order):continue
            if match:
                family,pole,curve,current=match.groups();family=family.upper() if '-' not in family else family[:3].upper()+family[3:].lower()
                spec={'Dòng sản phẩm':family,'Số cực':re.sub(r'\s','',pole).upper(),'In (A)':current}
                if curve:spec['Đặc tính tác động']=curve.upper()
                category='ISOLATOR' if family=='BKD' else 'MCB'
                if family=='BKD':spec['Chức năng']='Cách ly'
            elif bkp:
                curve,current=bkp.groups();family='BKP';category='MCB'
                spec={'Dòng sản phẩm':family,'Số cực':'1P+N','In (A)':current,
                      'Đặc tính tác động':curve.upper(),'Điện áp định mức':'230 VAC','Icn':'4.5 kA'}
            else:
                family,current,leakage=kgr.groups();family=family[:5].upper()+family[5:].lower()
                # 2022's In column prints 32 A against a 30 A model name.
                # Keep the consistent 2018 row for these identical order codes.
                if edition=='2022-04' and current=='30':continue
                category='RCBO';spec={'Dòng sản phẩm':family,'Số cực':'2P','In (A)':current,
                    'Dòng rò (mA)':leakage,'Điện áp định mức':'110/220 VAC','Thời gian cắt dòng rò':'≤ 0.03 s',
                    'Icn':'1.5 kA' if family.lower().endswith('c') else '2.5 kA'}
            spec['Mã đặt hàng']=order
            rows.append({'id':'external:ls-technical:'+order,'brand':'LS Electric','sku':order,'item_name':line,'name':line,
                'category':category,'group':family,'price':None,'edition':'Catalog kỹ thuật '+edition,
                'specifications':spec,'source_url':url,'source_page':page_no,
                'columns':['Tên hàng','Mã đặt hàng','Số cực','Dòng định mức (A)','Thông số'],
                'cells':[line,order,spec['Số cực'],current,'; '.join(f'{k}: {v}' for k,v in spec.items() if k not in {'Mã đặt hàng','Số cực','In (A)'})]})
    return rows

def main():
    selected={}
    for edition,file,url in CATALOGS:
        with pymupdf.open(ROOT/'tmp/catalog-research'/file) as document:
            rows=extract(document,edition,url)
        print(edition,'explicit model/order rows:',len(rows),flush=True)
        for row in rows:selected.setdefault(row['sku'],row)
    dest=ROOT/'app/data/external_product_information.json';data=json.loads(dest.read_text(encoding='utf8'))
    data['items']=[r for r in data['items'] if not r.get('id','').startswith('external:ls-technical:')]+list(selected.values())
    dest.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Imported unique LS order numbers:',len(selected),flush=True)

if __name__=='__main__':main()
