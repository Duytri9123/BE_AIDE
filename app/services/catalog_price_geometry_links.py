"""Conservative family-level geometry links, separate from electrical approval."""
import re
from .ai.manufacturer_registry import canonical_brand
from .catalog_family_matching import category_key,row_poles
from .catalog_product_sections import device_poles,current_kinds

BREAKERS={'MCB','MCCB','ACB','RCBO','RCCB','ISOLATOR','MOTORPROTECTION','MPCB'}
def model_key(value):
 text=re.sub(r'[^A-Z0-9]','',str(value or '').upper())
 return re.sub(r'\d+',lambda m:str(int(m[0])),text)

def source_models(raw,device):
 value=str(raw.get('ma_dong_san_pham') or device.get('product_code') or '').strip()
 if not value or re.search(r'chưa|unknown|reference|\*',value,re.I):return []
 parts=[s.strip() for s in re.split(r'\s*/\s*',value) if s.strip()]
 # Expand explicitly printed shorthand, not unrelated members of the same series.
 prefix=re.match(r'([A-Z]+)\d',parts[0],re.I) if parts else None
 if prefix:parts=[prefix[1]+s if s.isdigit() else s for s in parts]
 return parts

def row_models(row):
 spec=row.get('specifications') or {};values=[row.get('sku'),row.get('item_name'),row.get('name')]
 values.extend(spec.get(k) for k in ['Mã thân','Họ thiết bị','Dòng sản phẩm'])
 return [str(v).strip().split()[0] for v in values if v and str(v).strip()]

def compatible_categories(a,b):
 a,b=category_key(a),category_key(b)
 aliases={'VFD':'INVERTER','MPCB':'MOTORPROTECTION','NGUỒNVÀBIẾNÁP':'TRANSFORMER','RƠLEBẢOVỆPHA':'PHASERELAY','EARTHLEAKAGERELAY':'EARTHLEAKAGERELAY'}
 a,b=aliases.get(a,a),aliases.get(b,b)
 if a==b:return True
 return a in {'AUXCONTACT','INTERLOCK'} and b=='ACCESSORY'

def family_link(raw,device,row):
 if canonical_brand(device.get('brand'))!=canonical_brand(row.get('brand')):return None
 kind=category_key(device.get('type'))
 if kind in {'ASSEMBLYREFERENCE','SOURCEREFERENCE','DRAWING','MOUNTINGTEMPLATE','UNKNOWN'}:return None
 if not compatible_categories(kind,row.get('category')):return None
 wanted=device_poles(device);actual=row_poles(row)
 if kind in BREAKERS and (not wanted or actual!=wanted):return None
 if wanted and actual and wanted!=actual:return None
 models=source_models(raw,device);keys={model_key(v) for v in row_models(row)}
 source_spec=raw.get('thong_so') or {};spec=row.get('specifications') or {}
 if kind=='CONTACTOR':
  source_coil=current_kinds(source_spec.get('Loại cuộn hút') or source_spec.get('dien_ap_cuon_hut'))
  target_coil=current_kinds(' '.join(str(spec.get(k) or '') for k in ['Loại cuộn hút','Điện áp cuộn hút','Điện áp cuộn dây'])+' '+' '.join(str(row.get(k) or '') for k in ['group','item_name','sku']))
  if source_coil and (not target_coil or not source_coil&target_coil):return None
  if not source_coil and 'DC' in target_coil:return None
 for model in models:
  key=model_key(model)
  if len(key)<2 or not re.search(r'\d',key):
   if key not in {'BHA','BHL','BHDN','BVD'}:continue
  basis=None
  if key in keys:basis='explicit_source_model_or_family'
  # Current suffixes belong to a specific named body (NF125-CV, TA25-DU...).
  elif len(key)>=5 and key[-1].isalpha() and any(k.startswith(key) and len(k)>len(key) and k[len(key)].isdigit() for k in keys):
   basis='explicit_body_with_configuration_suffix'
  if not basis:continue
  # Do not attach high-current/enlarged modular bodies to a <=63 A drawing.
  current=spec.get('In (A)') or spec.get('In') or spec.get('Dòng định mức (A)')
  numbers=[float(x) for x in re.findall(r'\d+(?:\.\d+)?',str(current or ''))]
  limit=None
  if canonical_brand(device.get('brand'))=='ABB':
   limit={'A1':125,'A2':250,'A3':630,'T1':160,'T2':160,'T3':250,'T4':250,'T5':630,'T6':800,'T7':1600,'T7M':1600,'XT1':160,'XT2':160,'XT3':250,'XT4':250}.get(key)
   if key.startswith(('S20','SH20','FH20','DS201')):limit=63
  if canonical_brand(device.get('brand'))=='Mitsubishi Electric':
   m=re.match(r'NF(\d+)',key)
   if m:limit=int(m[1])
  if limit and numbers and max(numbers)>limit:return None
  if kind=='MCB' and key in {'IK60N','IC60N','BHD6','BHDN','SH200','S200'} and numbers and max(numbers)>63:return None
  # A fixed source is never an equivalent drawout/plug-in unit.
  text=' '.join(str(row.get(k) or '') for k in ['sku','item_name','name']).upper()
  if re.search(r'\bDRAWOUT\b|\bWITHDRAW|\bPLUG[- ]?IN\b|\bWITHDRAWABLE\b',text):return None
  return {'source_model':model,'basis':basis,'source_poles':wanted,'price_poles':actual,'current_frame_limit_a':limit,'exact_cad_match':False,'electrical_approval':False}
 return None
