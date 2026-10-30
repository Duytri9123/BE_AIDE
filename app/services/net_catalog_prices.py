"""Publish documented original list prices excluding VAT; preserve raw source records."""
import copy,re
from decimal import Decimal,InvalidOperation,ROUND_HALF_UP

PRICE_COLUMN=re.compile(r'^(?:đơn\s*giá|giá(?:\s|$|\()|(?:unit\s+|list\s+)?price)',re.I)

def net_price_row(row):
 if row.get('price_basis')=='net_list':return row
 out=copy.deepcopy(row);value=None;status=row.get('vat_status')
 try:
  gross=Decimal(str(row.get('price')))
  if gross.is_finite() and gross>0:
   if status=='excluded':value=gross
   elif status=='included' and row.get('vat_rate_evidence'):
    rate=Decimal(str(row.get('vat_rate_percent')))
    if rate.is_finite() and 0<=rate<=100:value=(gross/(1+rate/100)).quantize(Decimal('1'),rounding=ROUND_HALF_UP)
 except (InvalidOperation,TypeError,ValueError):pass
 out['price']=float(value) if value is not None else None
 out['price_basis']='net_list';out['vat_status']='excluded' if value is not None else 'unknown'
 columns=list(out.get('columns') or []);cells=list(out.get('cells') or [])
 for i,key in enumerate(columns):
  if PRICE_COLUMN.match(str(key).strip()):
   columns[i]='Đơn giá gốc chưa VAT'
   if i<len(cells):cells[i]=(f'{value:,.0f}' if value%1==0 else format(value,',f')) if value is not None else ''
 out['columns']=columns;out['cells']=cells
 return out
