"""Read LS pole/coil metadata explicitly printed in the supplier table section."""
import json,re,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];path=ROOT/'app/data/supplier_pricebooks.json';data=json.loads(path.read_text(encoding='utf8'));changes=[]
for row in data['items']:
 if str(row.get('brand','')).lower() not in ['ls','ls electric'] or row.get('category') not in {'MCB','MCCB','ACB','RCBO','RCCB','ELCB','CONTACTOR','MOTOR_PROTECTION'}:continue
 original=json.dumps(row,sort_keys=True,ensure_ascii=False);spec=row.setdefault('specifications',{});group=str(row.get('group') or '').upper();name=str(row.get('sku') or '').upper()
 explicit=re.search(r'(?<![A-Z0-9])([1-4])\s*P(?:OLES?)?(?![A-Z0-9])',name)
 section=re.search(r'(?<![A-Z0-9])([1-4])\s*(?:POLES?|PHA)(?![A-Z0-9])',group)
 pole=(explicit or section)
 added={}
 if pole and not spec.get('Số cực'):added['Số cực']=pole[1]+'P'
 if row['category']=='CONTACTOR' and not spec.get('Loại cuộn hút'):
  if re.search(r'\bDC\s*(?:COIL|VOLT)',group):added['Loại cuộn hút']='DC'
  elif re.search(r'\bAC\s*COIL|4\s*PHA\s*AC',group):added['Loại cuộn hút']='AC'
 if added:
  before=dict(spec);spec.update(added);changes.append({'row_id':row['id'],'sku':row['sku'],'group':row.get('group'),'source_page':row.get('source_page'),'added':added,'previous_specifications':before,'price':row.get('price')})
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(ROOT/'docs/ls-library-rebuild-2026-10-20/explicit-pricebook-metadata.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf8');print('LS explicit section metadata:',len(changes),'price rows; no prices changed')
