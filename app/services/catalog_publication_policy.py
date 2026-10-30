"""Only identified equipment belongs in the customer procurement library."""
import re
from .ai.manufacturer_registry import canonical_brand

UNRESOLVED=re.compile(r'chưa\s*(?:rõ|xác\s*định)|unknown|unidentified|^\*|^(?:SRC_|SOURCE_|cluster)',re.I)

def public_device_allowed(device):
 if device.get('browser_hidden'):return False
 if device.get('brand_kind')=='generic':return True
 maker=canonical_brand(device.get('brand'))
 model=str(device.get('product_code') or '').strip()
 if not maker or maker.casefold() in {'asian','asia','unknown','chưa xác định'}:return False
 if not model or UNRESOLVED.search(model):return False
 if UNRESOLVED.search(str(device.get('display') or '')):return False
 return True

def normalized_brand_labels(values):
 return sorted({canonical_brand(v) for v in values if canonical_brand(v)})

def public_profile_allowed(profile,path,root):
 from .library_manufacturer_identity import identity_for_profile
 from .catalog_source_identification import apply_source_identification
 identity=identity_for_profile(profile,path,root)
 reviewed=identity.get('reviewed_description') or {}
 candidate={**identity,'browser_hidden':profile.get('browser_hidden'),
  'product_code':reviewed.get('product_code') or profile.get('ma_dong_san_pham'),
  'display':reviewed.get('display') or profile.get('ten_san_pham') or profile.get('ten_kieu')}
 # Use the same hash-bound source-label review as the browser. A missing raw
 # model field does not invalidate a label already read and verified in CAD.
 apply_source_identification(candidate,profile,path,root)
 return public_device_allowed(candidate)

def selected_model_rows(device,rows,model):
 if not model:return rows
 from .catalog_view_models import view_models
 if model not in {m for v in device.get('views',[]) for m in view_models(device,v)}:
  raise ValueError('Mã thiết bị không thuộc bộ CAD đã chọn.')
 pattern=re.compile(re.escape(model)+r'(?=$|[\s/,(])',re.I)
 return [r for r in rows if any(pattern.match(str(r.get(key) or '')) for key in ('sku','item_name','name'))]
