"""LS requires six source-backed orthographic views of the same CAD variant."""
from functools import lru_cache

@lru_cache(maxsize=512)
def _valid_dxf(path,modified_ns,size):
 import ezdxf
 try:
  drawing=ezdxf.readfile(path)
  return drawing.units==4 and len(drawing.modelspace())>0 and not drawing.audit().errors
 except (OSError,ValueError,ezdxf.DXFError):return False

REQUIRED=('front','rear','left','right','top','bottom')
LABELS={'front':'Mặt trước','rear':'Mặt sau','left':'Mặt bên trái','right':'Mặt bên phải','top':'Mặt trên','bottom':'Mặt dưới'}
def is_ls(brand):
 return str(brand or '').strip().casefold() in {'ls','ls electric','ls electric co., ltd.'}
def view_role(view):
 label=str(view.get('huong_nhin') or view.get('label') or view.get('name') or '').split(' · ')[0].strip()
 face=str(view.get('face') or '').split(' · ')[0].strip()
 roles={'Mặt trước':'front','Mặt đứng':'front','Mặt sau':'rear','Mặt bên trái':'left','Mặt bên phải':'right','Mặt trên':'top','Mặt bằng':'top','Mặt dưới':'bottom'}
 if label in roles:return roles[label]
 if face in roles:return roles[face]
 if face in {'front','rear','top','bottom','left','right'}:return face
 return None

def view_coverage(views):
 present={view_role(v) for v in views if v.get('available',True)}-{None}
 missing=[r for r in REQUIRED if r not in present]
 return {'status':'complete' if not missing else 'needs_cad_supplement','required_faces':list(REQUIRED),'available_faces':sorted(present),'missing_faces':missing,'missing_labels':[LABELS[r] for r in missing],'complete':not missing}

def asset_view_coverage(asset):
 from pathlib import Path
 from .catalogtb_assets import ROOT
 import json
 p=ROOT/asset['profile_path'];profile=json.loads(p.read_text(encoding='utf-8-sig'));variant=asset.get('variant_id')
 views=[]
 for v in profile.get('cad_don') or []:
  if (v.get('bien_the_cad') or v.get('bien_the'))!=variant:continue
  path=(p.parent/v.get('duong_dan','')).resolve()
  available=path.is_relative_to(ROOT.resolve()) and path.is_file() and path.suffix.lower()=='.dxf'
  views.append({**v,'available':available,'_path':path})
 status=view_coverage(views)
 if not status['complete']:return status
 for view in views:
  path=view['_path'];stat=path.stat()
  view['available']=_valid_dxf(str(path),stat.st_mtime_ns,stat.st_size)
 return view_coverage(views)

def require_complete_ls_views(asset, required_face=None):
 if not is_ls(asset.get('brand')):return None
 status=asset_view_coverage(asset)
 if required_face:
  if required_face not in status['available_faces']:
   raise ValueError('LS cần bổ sung CAD mặt '+str(LABELS.get(required_face, required_face))+'. Chưa đủ mặt để bố trí tủ.')
  return status
 if not status['complete']:
  raise ValueError('LS cần bổ sung CAD cùng biến thể: '+', '.join(status['missing_labels'])+'. Chưa đủ mặt để bố trí tủ.')
 return status


def require_ls_device_geometry(device, required_face=None):
 brand=device.get('detected_brand') or device.get('brand')
 cad=device.get('cad') or (device.get('parameters') or {}).get('cad') or {}
 if not str(cad.get('asset_id') or '').startswith('tb:'):
  if is_ls(brand):raise ValueError('Thiết bị LS chưa có CAD đủ mặt; cần bổ sung CAD trước khi bố trí.')
  return None
 from .catalogtb_assets import resolve
 asset=resolve(cad['asset_id'])
 if is_ls(brand) and not is_ls(asset.get('brand')):
  raise ValueError('Thiết bị yêu cầu LS phải dùng CAD LS đúng họ thiết bị.')
 return require_complete_ls_views(asset, required_face=required_face)
