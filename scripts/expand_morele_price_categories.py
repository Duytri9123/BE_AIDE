"""Import visually reviewed historical rows without inventing CAD or ordering variants."""
import hashlib,json,re
from pathlib import Path
import pymupdf
ROOT=Path(__file__).resolve().parents[1]
URL='https://vanvh.com/upload/files/BG2021morele1.pdf'
OUT=ROOT/'docs/catalog-expansion-2026-10-24'

def reviewed_rows(path):
 doc=pymupdf.open(path);digest=hashlib.sha256(path.read_bytes()).hexdigest();rows=[];held=[]
 def add(page,index,cells,kind,variant='',bbox=None):
  name,sku,maker,unit,amount=[re.sub(r'\s+',' ',s or '').strip() for s in cells]
  brand={'MORELE/ CHINA':'Morele','CML/ CHINA':'CML'}[maker]
  assert re.fullmatch(r'\d{1,3}(?:,\d{3})+|\d+',amount)
  identity=f'{page}:{index}:{brand}:{sku}:{variant}'
  spec={'Mô tả':name,'Đơn vị tính':unit}
  if variant:spec['Biến thể']=variant
  if kind=='CT':
   m=re.fullmatch(r'(RCT-\d+) (\d+/5) CLASS1,?',name);assert m and sku==m[2]
   sku=m[1]+' '+m[2]+'A';spec.update({'Họ thiết bị':m[1],'Tỷ số CT':m[2]+'A','Cấp chính xác':'1'})
  if kind=='WIRING_DUCT':
   size=re.search(r'(\d+)\s*x\s*(\d+)\s*mm',name,re.I);assert size
   spec.update({'Rộng × cao (mm)':size[1]+' × '+size[2],'Chiều dài thanh (mm)':'2000','Màu':'Ghi'})
  if sku=='AD16-22CS':spec.update({'Điện áp':'220 V AC','Lỗ lắp':'Ø22 mm'})
  rows.append({'id':'reviewed-pdf:'+hashlib.sha1((URL+'|expanded|'+identity).encode()).hexdigest()[:20],'sku':sku,'item_name':name,'name':name,'brand':brand,'category':kind,'price':int(amount.replace(',','')),'currency':'VND','group':kind+' · 2021','source_kind':'supplier_pricebook','source_url':URL,'source_label':'Bảng giá phụ kiện '+brand+' 2021','source_page':page,'source_sha256':digest,'source_line':identity,'source_region':bbox,'edition':'2021','effective_date':'2021-04-01','checked_at':'2026-10-24','vat_status':'excluded','specifications':spec,'columns':['Tên hàng','Mã hàng','Biến thể','Đơn vị','Đơn giá'],'cells':[name,sku,variant,unit,amount],'price_note':'Giá lịch sử năm 2021, chưa VAT; không phải báo giá hiện hành.','cad_matching_policy':'requires_independently_verified_named_manufacturer_geometry'})
 tables=[page.find_tables().tables for page in doc]
 for ti,table in enumerate(tables[0]):
  for ri,c in enumerate(table.extract()):
   if len(c)!=5 or c[2] not in ('MORELE/ CHINA','CML/ CHINA'):continue
   bounds=list(table.rows[ri].bbox)
   if ti==0:add(1,f'{ti}:{ri}',c,'METER',bbox=bounds)
   elif ti==1 and c[2]=='CML/ CHINA':
    c=[*c];c[4]=c[4].replace('VAT)\n','');add(1,f'{ti}:{ri}',c,'CT',bbox=bounds)
   elif ti==2:
    if c[1]=='Cam Swicth':held.append({'page':1,'cells':c,'reason':'Generic model and contradictory position count; no exact ordering code.'})
    else:add(1,f'{ti}:{ri}',c,'SELECTOR_SWITCH',variant=c[0],bbox=bounds)
 for ti,table in enumerate(tables[1]):
  for ri,c in enumerate(table.extract()):
   if len(c)!=5 or c[2]!='MORELE/ CHINA':continue
   bounds=list(table.rows[ri].bbox)
   if ti==1:add(2,f'{ti}:{ri}',c,'WIRING_DUCT',bbox=bounds)
   elif c[1] in ('LAY5-EW3361-LED','LAY7-11ZS'):add(2,f'{ti}:{ri}',c,'PUSHBUTTON',bbox=bounds)
   elif c[1]=='AD16-22CS' and '220VAC' in c[0]:add(2,f'{ti}:{ri}',c,'LIGHT',variant='220 V AC',bbox=bounds)
   elif c[1] not in ('RT18-32','AD22'):held.append({'page':2,'cells':c,'reason':'Combined/ambiguous order codes, unspecified label model, or erroneous voltage text; do not expand to invented SKUs.'})
 text=doc[1].get_text();assert re.search(r'CB2-ED25\s+MORELE/ CHINA\s+Cái\s+30,000',text)
 add(2,'continuation-top',['Công tắc 2 Vị Trí: 1 - 2 (NO+NC)','CB2-ED25','MORELE/ CHINA','Cái','30,000'],'SELECTOR_SWITCH',bbox=[0,0,doc[1].rect.width,45])
 assert len(rows)==41,len(rows)
 return rows,held

def main():
 OUT.mkdir(exist_ok=True);rows,held=reviewed_rows(ROOT/'tmp/morele-external-pricebook.pdf');p=ROOT/'app/data/supplier_pricebooks.json';original=p.read_bytes();data=json.loads(original);by_id={r['id']:r for r in data['items']}
 previous={r['id']:(r.get('price'),r.get('sku')) for r in data['items']}
 for r in rows:by_id[r['id']]=r
 data['items']=list(by_id.values())
 for brand in ('Morele','CML'):
  models={}
  for r in data['items']:
   if r.get('brand')==brand:models.setdefault(r['item_name'],[]).append(r['id'])
  data.setdefault('manufacturers',{}).setdefault(brand,{})['models']=models
 assert all((by_id[k].get('price'),by_id[k].get('sku'))==v for k,v in previous.items())
 assert p.read_bytes()==original,'Pricebook changed concurrently'
 temp=p.with_suffix('.expanded.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8');temp.replace(p)
 report={'added_or_verified_rows':len(rows),'previous_rows_preserved':True,'cad_profiles_created':0,'historical_edition':'2021','items':rows,'held':held}
 (OUT/'morele-cml-price-import.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in report.items() if k not in ('items','held')}),flush=True)

if __name__=='__main__':main()
