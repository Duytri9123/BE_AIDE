"""Restore source column labels using exact PDF row cells; retain all prices/IDs."""
import json,re
from pathlib import Path
import pymupdf
from scripts.import_ls_pricebook import split_position

ROOT=Path(__file__).resolve().parents[1]

def main():
    path=ROOT/'app/data/supplier_pricebooks.json'
    data=json.loads(path.read_text(encoding='utf8'));lookup={}
    for number,page in enumerate(pymupdf.open(ROOT/'storage/catalog-pricebooks/ls-2026-10-01.pdf'),1):
        split=split_position(page)
        for left,right in ((0,split),(split,page.rect.width)):
            for table in page.find_tables(clip=pymupdf.Rect(left,45,right,page.rect.height-20)).tables:
                headers=[];previous=''
                for raw in table.extract():
                    cells=[re.sub(r'\s+',' ',str(c or '')).strip() for c in raw]
                    if 'Giá bán' in cells:headers=cells;continue
                    if len([c for c in cells if c])==1:previous='';continue
                    if not cells or not re.fullmatch(r'\d{1,3}(?:,\d{3})+',cells[-1]):continue
                    if not cells[0] and previous:cells[0]=previous
                    elif cells[0]:previous=cells[0]
                    if len(headers)==len(cells) and all(headers):lookup[(number,tuple(cells))]=headers[:]
    count=0
    for row in data['items']:
        if not str(row.get('id','')).startswith('ls-pdf:') or 'Thông tin' not in row.get('columns',[]):continue
        headers=lookup.get((row.get('source_page'),tuple(row.get('cells') or [])))
        if not headers:continue
        row['columns']=headers
        spec=row.setdefault('specifications',{});spec.pop('Thông tin',None)
        spec.update({h:v for h,v in zip(headers[1:-1],row['cells'][1:-1]) if v})
        count+=1
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(f'Restored exact PDF headers on {count} rows; prices and IDs retained')

if __name__=='__main__':main()
