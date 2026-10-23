"""Recover MCB family/poles/current from reviewed PDF rows and column headers."""
import hashlib,json,re,shutil
from pathlib import Path
import pymupdf
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/schneider-update-2026-10-21'

def extract(path):
 doc=pymupdf.open(path);assert len(doc)==282
 text=doc[43].get_text(sort=True);assert '1P, 2P, 3P, 4P MCBs' in text
 family=left=right=voltage=None;rows={}
 for line in text.splitlines():
  heading=re.search(r'(iK60N|iC60N)\s*-\s*([13])P\s*&\s*([24])P\s*,\s*6kA\s*,\s*(230|400)V',line)
  if heading:family,left,right,voltage=heading.groups()
  codes=re.findall(r'(A9[FK]\d{5})\s+\d{1,3}(?:\.\d{3})+',line)
  if not codes:continue
  assert len(codes)==2 and family and left and right and voltage,line
  current=re.search(r'(\d+)\s+'+re.escape(codes[0]),line);assert current,line
  for sku,pole in zip(codes,[left,right]):rows[sku]={'family':family,'poles':pole+'P','current':current[1],'voltage':voltage,'category':'MCB'}
 assert len(rows)==72,len(rows)
 return rows

def main():
 pdf=ROOT/'tmp/folder-web-review/schneider-2026.pdf';facts=extract(pdf)
 path=ROOT/'app/data/supplier_pricebooks.json';data=json.loads(path.read_text(encoding='utf8'));changed=[]
 for row in data['items']:
  if row.get('brand')!='Schneider Electric' or row['sku'] not in facts:continue
  fact=facts[row['sku']];before={'category':row['category'],'specifications':dict(row.get('specifications') or {})}
  row.update(category='MCB',group='MCB · '+fact['family'],item_name=fact['family']+' '+fact['poles']+' '+fact['current']+' A · C')
  row['name']=row['item_name'];row['specifications'].update({'Họ thiết bị':fact['family'],'Số cực':fact['poles'],'In (A)':fact['current'],'Đặc tuyến':'C','Khả năng cắt danh mục tại '+fact['voltage']+' V AC (kA)':'6'})
  row['technical_review']={'source_url':'https://www.se.com/vn/vi/download/document/MasterPriceBook/','pdf_page':44,'source_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'basis':'Exact PDF SKU row, current column and explicit pole/voltage section headers; no Icu/Ics relabelling'}
  for index,column in enumerate(row.get('columns') or []):
   if index>=len(row.get('cells') or []):continue
   if column in {'Tên hàng','Tên thiết bị'}:row['cells'][index]=row['item_name']
   if column=='Thông tin':row['cells'][index]=' · '.join(k+': '+str(v) for k,v in row['specifications'].items() if k!='Mô tả')
  changed.append({'sku':row['sku'],'id':row['id'],'before':before,'after':dict(fact)})
 assert len(changed)==72,len(changed)
 pending=path.with_suffix('.pending');pending.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8');pending.replace(path)
 (OUT/'mcb-pricebook-corrections.json').write_text(json.dumps(changed,ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps({'rows_verified_and_updated':len(changed),'additional_category_changes':sum(c['before']['category']!='MCB' for c in changed),'prices_changed':0}))

if __name__=='__main__':main()
