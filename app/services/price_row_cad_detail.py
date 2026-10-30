"""Return explicitly linked public CAD for one commercial row, never a guessed brand."""
import hashlib,re,copy
from .ai.manufacturer_registry import canonical_brand
from .customer_equipment_information import customer_device,customer_information_rows
from .catalog_publication_policy import public_device_allowed
from .library_catalog_information import information_rows
from .cad.ls_view_coverage import view_coverage

def linked_cad_for_row(row,devices):
 result=[]
 for device in devices:
  if not public_device_allowed(device) or canonical_brand(device.get('brand'))!=canonical_brand(row.get('brand')):continue
  options=(device.get('catalog_references') or {}).get('options',[])
  if not any(o.get('source_row_id')==row['id'] for o in options):continue
  matches=information_rows(device,[row])
  if not any(r.get('match_scope')=='source_family' for r in matches):continue
  public=customer_device(device)
  # A source family may contain differently engraved model states.
  from .catalog_view_models import view_models
  codes={c for v in device.get('views',[]) for c in view_models(device,v)}
  selected=[c for c in codes if re.match(re.escape(c)+r'(?=$|[\s/,(])',str(row.get('sku') or ''),re.I)]
  if codes and not selected:continue
  allowed={v['id'] for v in device.get('views',[]) if not view_models(device,v) or set(view_models(device,v))&set(selected)}
  if codes:
   from .customer_equipment_information import public_view_id
   public['views']=[v for v in public['views'] if v['id'] in {public_view_id(x) for x in allowed}]
  if not public['views']:continue
  public['selected_model']=max(selected,key=len) if selected else row.get('sku')
  public['link_scope']='reviewed_family_configuration'
  from .customer_equipment_information import public_view_id
  groups={}
  for view in device.get('views',[]):
   key=view.get('cad_variant_id') or device['id']
   groups.setdefault(key,set()).add(public_view_id(view['id']))
  for variant,ids in groups.items():
   item=copy.deepcopy(public);item['views']=[v for v in public['views'] if v['id'] in ids]
   if not item['views']:continue
   item['selection_id']=device['id']+':'+hashlib.sha256(variant.encode()).hexdigest()[:12]
   result.append(item)
 result.sort(key=lambda d:(-len(d['views']),d['id']))
 return result

def price_row_detail(public_id,rows,devices):
 row=next((r for r in rows if hashlib.sha256(r['id'].encode()).hexdigest()[:24]==public_id),None)
 if row is None:return None
 product=customer_information_rows([{**row,'information_kind':'pricebook'}],{'brand':row['brand']})[0]
 product['id']=public_id
 return {'product':product,'cad_devices':linked_cad_for_row(row,devices)}
