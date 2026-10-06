"""Index line-level Mitsubishi 2026 PDF prices with source page and raw text."""
import json
import re
from pathlib import Path
from pypdf import PdfReader

BASE=Path(__file__).resolve().parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/MITSUBISHI_D04_DU_LIEU_MOI'
PDF=BASE/'source/Mitsubishi_2026_DGP.pdf'
PRICE=re.compile(r'(?<!\d)\d{1,3}(?:,\d{3})+(?!\d)')
MODEL=re.compile(r'\b(?:AE\d{3,4}(?:-[A-Z0-9]+)?|(?:NF|NV|MB)\d{2,4}(?:-[A-Z0-9]+)?|BH-[A-Z0-9-]+|BV[A-Z0-9-]*|S(?:D)?-T\d+[A-Z0-9-]*|TH-T\d+[A-Z0-9-]*)\b',re.I)
CODE=re.compile(r'\b(?=[A-Z0-9./-]*\d)[A-Z0-9][A-Z0-9./-]{6,}\b',re.I)

def category(page):
    if page<=8: return 'ACB và phụ kiện'
    if page<=18: return 'MCCB'
    if page<=32: return 'ELCB'
    if page<=40: return 'Phụ kiện MCCB/ELCB'
    if page<=43: return 'MCB'
    if page==44: return 'RCBO'
    if page<=46: return 'MCB'
    if page==47: return 'RCCB'
    if page<=52: return 'Thiết bị bảo vệ mạch'
    if page<=61: return 'Contactor'
    if page==62: return 'Phụ kiện contactor'
    if page<=65: return 'Rơ le nhiệt'
    return 'Đo lường và giám sát'

reader=PdfReader(PDF)
rows=[]
audit=[]
for page_no,page in enumerate(reader.pages,1):
    lines=page.extract_text().splitlines()
    (BASE/'source'/f'page_{page_no:02d}.txt').write_text('\n'.join(lines)+'\n',encoding='utf8')
    count=0
    for line_no,line in enumerate(lines,1):
        amounts=list(PRICE.finditer(line))
        if not amounts: continue
        # PDF text is ordered left column, then right column, per visual row.
        start=0
        for amount in amounts:
            segment=line[start:amount.start()].strip()
            start=amount.end()
            if not segment: continue
            models=list(MODEL.finditer(segment))
            model=models[-1].group(0).upper() if models else None
            # If a repeated model appears in the material code (e.g. BVW-T),
            # the first model is the visible product identity.
            if models and segment.count(model)>1: model=models[0].group(0).upper()
            codes=list(CODE.finditer(segment))
            material=codes[-1].group(0) if codes else None
            if material==model: material=None
            poles=re.search(r'\b([1-4])P\b|\b([1-4])PN\b',segment,re.I)
            # A lowercase "a" in contactor descriptions marks auxiliary
            # contacts (1a/1b), not rated current in amperes.
            current=re.search(r'(?<!\d)(\d+(?:\.\d+)?)\s*A\b',segment)
            price=int(amount.group().replace(',',''))
            # Prices listed in tables are positive VND amounts; skip prose
            # without a product-like code, but retain it in audit counts.
            if price<1000 or not (model or material): continue
            rows.append({'row_id':len(rows)+1,'model':model,'description_pdf':segment,
                         'material_code':material,'poles_pdf':int((poles[1] or poles[2])) if poles else None,
                         'current_a_pdf':current[1] if current else None,
                         'price_vnd':price,'category':category(page_no),
                         'page':page_no,'line':line_no,'source_line':line,
                         'source_pdf':PDF.name,'source_url':'https://www.thietbidiendgp.vn/posts/bang-gia-thiet-bi-dien-mitsubishi'})
            count+=1
    audit.append({'page':page_no,'prices_indexed':count,'text_lines':len(lines)})
(BASE/'price_index.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(BASE/'price_extract_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'pages':len(reader.pages),'rows':len(rows),'with_model':sum(bool(r['model']) for r in rows),
                  'per_page':[(x['page'],x['prices_indexed']) for x in audit]},ensure_ascii=False))
