"""Use exact model text already read from a view, without expanding suffix aliases."""
import re

def view_models(device,view):
 explicit=view.get('model_codes')
 if explicit:return explicit
 named=[m.strip() for m in re.split(r'\s+/\s+',str(device.get('product_code') or '')) if m.strip()]
 label=str((view.get('source_info') or {}).get('Mã trên CAD') or '').strip()
 return [m for m in named if m.casefold()==label.casefold()]
