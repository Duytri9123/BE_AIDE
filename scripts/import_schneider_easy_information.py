"""Read explicit description/reference pairs on the same PDF table row."""
import json
import re
from pathlib import Path
import pymupdf

ROOT=Path(__file__).resolve().parents[1]
URL='https://download.schneider-electric.com/files?p_Doc_Ref=Easy_Catalogue&p_File_Ext=.PDF'
DESCRIPTION=re.compile(r'(\d+(?:\.\d+)?)\s*A\s+EasyPact\s+(EZC[V]?\d+[A-Z]+)\s+([1-4]P)(?:\s*([1-4])d)?\b',re.I)

def pairs(lines):
    """Require one reference on the same baseline and matching printed family."""
    result=[]
    for text,box in lines:
        match=DESCRIPTION.match(text.strip())
        if not match:continue
        current,family,pole,protected=match.groups()
        codes=[value.strip() for value,position in lines
            if position[0]>box[2] and abs(position[1]-box[1])<2
            and re.fullmatch(re.escape(family)+r'[0-9]+[A-Z]?',value.strip(),re.I)]
        if len(codes)!=1:continue
        spec={'Dòng sản phẩm':family,'Số cực':pole.upper(),'In (A)':current}
        if protected:spec['Số cực được bảo vệ']=protected
        if 'earth leakage' in text.lower():spec['Bảo vệ dòng rò']='Có'
        result.append((text.strip(),codes[0],spec))
    return result

def main():
    rows=[]
    with pymupdf.open(ROOT/'tmp/catalog-research/schneider-easy.pdf') as document:
        for page_no,page in enumerate(document,1):
            lines=[(' '.join(s['text'] for s in line['spans']),line['bbox'])
                for block in page.get_text('dict')['blocks'] if 'lines' in block for line in block['lines']]
            for name,code,spec in pairs(lines):
                rows.append({'id':'external:schneider-easy:'+code,'brand':'Schneider Electric',
                    'sku':code,'name':name,'item_name':name,'category':'MCCB',
                    'group':'EasyPact · Catalog sản phẩm','price':None,'specifications':spec,
                    'source_url':URL,'source_page':page_no,
                    'columns':['Tên hàng','Mã hàng','Số cực','In (A)','Thông số'],
                    'cells':[name,code,spec['Số cực'],spec['In (A)'],
                        '; '.join(f'{k}: {v}' for k,v in spec.items() if k not in {'Số cực','In (A)'})]})
    unique={r['id']:r for r in rows}
    path=ROOT/'app/data/external_product_information.json';data=json.loads(path.read_text(encoding='utf8'))
    data['items']=[r for r in data['items'] if not r.get('id','').startswith('external:schneider-easy:')]+list(unique.values())
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Imported explicit same-row Schneider references:',len(unique))

if __name__=='__main__':main()
