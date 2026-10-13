"""Recover source columns from actual header and row coordinates."""
import re

def page_price_columns(page, records):
    headers=[]
    for table in page.find_tables().tables:
        for index,cells in enumerate(table.extract()):
            if not any(c and c.strip()=='Đơn giá' for c in cells):continue
            if not any(c and c.strip()=='Mô tả' for c in cells):continue
            columns=[(re.sub(r'\s+',' ',c).strip(),bbox) for c,bbox in zip(cells,table.rows[index].cells) if c and bbox and len(c)<50]
            headers.append(columns)
    anchors=[]
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines',[]):
            text=''.join(s['text'] for s in line['spans']).strip()
            match=re.fullmatch(r'VND\s+(\d{1,3}(?:,\d{3})+)',text)
            if match:anchors.append((int(match[1].replace(',','')),line['bbox']))
    if [v for v,_ in anchors]!=[r['price'] for r in records]:
        return 0  # Never pair source positions by a guessed ordinal.
    words=page.get_text('words');enriched=0
    for record,(_,bbox) in zip(records,anchors):
        candidates=[cols for cols in headers if max(b[3] for _,b in cols)<bbox[3]
                    and any(name=='Đơn giá' and b[0]<=bbox[0]<=b[2] for name,b in cols)]
        if not candidates:continue
        columns=max(candidates,key=lambda cols:max(b[3] for _,b in cols))
        center=(bbox[1]+bbox[3])/2
        values=[]
        for name,rect in columns:
            tokens=[w for w in words if rect[0]-1<=(w[0]+w[2])/2<=rect[2]+1 and abs((w[1]+w[3])/2-center)<5.5]
            tokens.sort(key=lambda w:(round(w[1],1),w[0]))
            values.append(' '.join(w[4] for w in tokens).strip())
        source_code=values[next(i for i,(name,_) in enumerate(columns) if name=='Mã hàng')] if any(name=='Mã hàng' for name,_ in columns) else ''
        expected_code=record['specifications'].get('Mã đặt hàng')
        if source_code!=expected_code:continue
        names=[name for name,_ in columns];model_index=names.index('Mô tả')
        order=[model_index]+[i for i in range(len(names)) if i!=model_index and not re.search(r'SL\s*/\s*Thùng',names[i],re.I)]
        names=[names[i] for i in order];values=[values[i] for i in order]
        names[0]='Tên hàng';values[0]=record['item_name']
        names=['Icn' if name.lower()=='lcn' else name for name in names]
        record['columns']=names;record['cells']=values
        record['specifications']={name:value for name,value in zip(names[1:],values[1:]) if value and name!='Đơn giá'}
        record['column_evidence']='PDF header and row geometry; material code matched'
        enriched+=1
    return enriched
