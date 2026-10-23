"""Manufacturer corrections to imported headings, retaining the original source row."""
import re
from .ai.manufacturer_registry import canonical_brand
BVW_SOURCE='https://www.mitsubishielectric.com/dl/fa/document/catalog/lvcb/yn-c-0730/y0730d2209.pdf'

def reviewed_price_row(row):
 name=str(row.get('item_name') or row.get('name') or '')
 notation=re.search(r'(?<![A-Z0-9])([1-4])PN(?![A-Z0-9])',name,re.I)
 if notation and not any((row.get('specifications') or {}).get(k) for k in ('Số cực','Poles','so_cuc')):
  row={**row,'specifications':{**(row.get('specifications') or {}),'Số cực':notation[1]+'P+N'}}
 # The supplier groups BVW-T under "MCB Japan". It is an IEC 61008 RCCB;
 # the conditional short-circuit rating is not an MCB Icu/Icn rating.
 if canonical_brand(row.get('brand'))=='Mitsubishi Electric' and re.match(r'BVW-T(?=$|\s)',str(row.get('item_name') or row.get('name') or ''),re.I):
  return {**row,'category':'RCCB','source_category':row.get('category'),'category_evidence_url':BVW_SOURCE}
 if canonical_brand(row.get('brand'))=='Mitsubishi Electric' and re.match(r'BV-DN6?(?=$|\s)',name,re.I):
  return {**row,'category':'RCBO','source_category':row.get('category'),'category_evidence_url':'https://www.mitsubishifa.co.th/th/product-features/low-voltage-circuit-breakers/'}
 if canonical_brand(row.get('brand'))=='Mitsubishi Electric':
  name=str(row.get('item_name') or row.get('name') or '')
  # Only the exact standard three-main-contact models inspected in native CAD.
  matched=re.match(r'((?:S-T(?:10|12|20|21|25|32|35|50|65|80|100)|SD-T(?:12|20|21|32|35|50|65|80|100)|(?:S|SD)-T(?:12|20)(?:SA)?SQ|S-N(?:38|48|125|150|180|220|300|400|600AB|800AB)|SD-N(?:125|150|220|300|400)|TH-T(?:18|25|50|65|100)(?:KP)?|TH-T18(?:KP)?SQ|TH-N(?:120(?:KP|TA)?|220RH|400RH|600(?:KP)?)))(?=\s|$)',name,re.I)
  if matched:
   spec=dict(row.get('specifications') or {})
   if not any(spec.get(k) for k in ('Số cực','Poles','so_cuc')):spec['Số cực']='3P'
   return {**row,'specifications':spec,'pole_evidence':'Manufacturer original three-pole CAD; exact named family only'}
 return row
