"""Shared writer for source-backed LS CAD additions; never approves a procurement SKU."""
import json,hashlib,re
from pathlib import Path
from ls_projection_compaction import source_segment_count
import ezdxf
from ezdxf import bbox
from ezdxf.math import Matrix44
from ezdxf.addons.drawing import Frontend,RenderContext,svg,layout,matplotlib
ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB';REPORT=ROOT/'docs/ls-full-faces-2026-10-20.json'
def write_profile(family,name,kind,models,poles,options,views,source,extra_spec=None, *, brand="LS", native_document=None):
 assert brand in {"LS","CHINT","Schneider Electric","ABB","INVT","Mitsubishi Electric","Shihlin"}
 brand_folder={"LS":"LS","CHINT":"Chint","Schneider Electric":"Schneider","ABB":"ABB","INVT":"INVT","Mitsubishi Electric":"Mitsubishi","Shihlin":"Shihlin"}[brand]
 report_path=ROOT/'docs/abb-s200-faces-2026-10-22.json' if brand=='ABB' else REPORT if brand=="LS" else ROOT/("docs/chint-full-faces-2026-10-21.json" if brand=="CHINT" else "docs/schneider-full-faces-2026-10-21.json")
 if brand=='INVT':report_path=ROOT/'docs/invt-full-faces-2026-10-22.json'
 if brand=='Mitsubishi Electric':report_path=ROOT/'docs/mitsubishi-full-faces-2026-10-22.json'
 if brand=='Shihlin':report_path=ROOT/'docs/shihlin-full-faces-2026-10-23.json'
 path=CAT/brand_folder/'ThietBi'/('OFFICIAL-'+family)/'thong_tin_thiet_bi.json';path.parent.mkdir(parents=True,exist_ok=True)
 note=f'CAD gốc {brand} theo họ và kiểu lắp ghi trong nguồn; chưa xác nhận SKU. Chọn riêng cấu hình điện, cơ cấu bảo vệ, phụ kiện và đối chiếu đầu nối trước gia công.'
 spec={**({'so_cuc':poles} if poles else {}),**(extra_spec or {})}
 profile={'nhom':brand,'ten_kieu':name,'ten_san_pham':name,'hang_xac_nhan':brand,'ma_dong_san_pham':' / '.join(models),'ban_chat':kind,'cong_dung':note,'thong_so':spec,'nhan_dien_ai':{'loai_thiet_bi_code':kind,'cac_ma_dong_san_pham':models,'exact_SKU_confirmed':False},'tu_khoa_tim_kiem':[brand,{'LS':'LS ELECTRIC','CHINT':'CHINT','Schneider Electric':'Schneider','ABB':'ABB','INVT':'INVT','Mitsubishi Electric':'Mitsubishi','Shihlin':'Shihlin'}[brand],kind,*models,*[o['model'] for o in options]],'nguon_tham_khao':[source['source_url']],'cad_don':[],'cac_hinh_cad':[],'auto_select':False,'needs_review':True,'muc_do_xac_nhan':note,'catalog_tham_khao':{'category':kind,'options':options,**({'source_row_scope':'explicit_only','row_links_reviewed':True} if brand=='LS' else {})},'quy_tac_dung_chung_cad':{'relationship':'one_geometry_many_configuration_options','electrical_rating_from_geometry':False,'requirements':['Đúng họ, số cực, kiểu lắp, đầu nối và phụ kiện','Xác nhận In/Icu/Ics tại điện áp làm việc theo mã đã chọn','CAD họ thiết bị không xác nhận cuộn hút, relay hoặc phụ kiện bên trong']}}
 if poles and poles.rstrip('P').isdigit():profile['nhan_dien_ai']['so_cuc']=int(poles.rstrip('P'))
 if poles and re.fullmatch(r'[1-3]P\+N',poles):profile['nhan_dien_ai']['so_cuc']=int(poles[0])+1
 report=json.loads(report_path.read_text()) if report_path.exists() else []
 report=[r for r in report if r['family']!=family]
 depth_code='SIDE' if any(v[0]=='SIDE' for v in views) else 'SIDE-R'
 for code,label,entities in views:
  segments=source_segment_count(entities)
  native_simple=(source.get('complete_manufacturer_step_projection') is True and len(source.get('step_sha256',''))==64 and source.get('six_views_verified') is True)
  assert segments>5 or (native_simple and segments>=3),(family,code,len(entities))
  bounds=bbox.extents(entities)
  assert bounds.has_data and bounds.size.x>0 and bounds.size.y>0,(family,code,'empty extent')
  target=ezdxf.new('R2010');target.units=4
  if native_document is not None:
   from ezdxf.addons import Importer
   importer=Importer(native_document,target);importer.import_entities(entities);importer.finalize()
   import sys
   if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
   from app.services.cad.layer_resource_links import repair_invalid_layer_resources
   repair_invalid_layer_resources(target)
   for ent in target.modelspace():ent.transform(Matrix44.translate(-bounds.extmin.x,-bounds.extmin.y,0))
  else:
   for e in entities:
    ent=e.copy();ent.dxf.layer='0';ent.dxf.color=7;ent.dxf.linetype='CONTINUOUS';ent.transform(Matrix44.translate(-bounds.extmin.x,-bounds.extmin.y,0));target.modelspace().add_entity(ent)
  assert not target.audit().errors
  ident=({'Schneider Electric':'SCHNEIDER','Mitsubishi Electric':'MITSUBISHI'}.get(brand,brand))+'-OFFICIAL-'+family+'-'+code;dest=path.parent/'CadDon'/ident;dest.mkdir(parents=True,exist_ok=True);drawing=dest/'ban_ve.dxf';target.saveas(drawing)
  backend=svg.SVGBackend();Frontend(RenderContext(target),backend).draw_layout(target.modelspace(),finalize=True);(dest/'xem_truoc.svg').write_text(backend.get_string(layout.Page(0,0,layout.Units.mm)),encoding='utf8');matplotlib.qsave(target.modelspace(),dest/'preview.png',dpi=80)
  size=bbox.extents(target.modelspace()).size;evidence={**source,'sha256':hashlib.sha256(drawing.read_bytes()).hexdigest(),'width_mm':size.x,'height_mm':size.y,'entity_count':len(entities),'coordinate_scale_to_mm':1,'ordering_code_verified':False}
  (dest/'evidence.json').write_text(json.dumps(evidence,indent=2),encoding='utf8');(dest/'thong_tin_cad_chen.json').write_text(json.dumps({'hinh_hoc_lap_dat':{'don_vi':'mm','bao_hinh_mm':{'min_x':0,'min_y':0,'max_x':size.x,'max_y':size.y}},'evidence':evidence},indent=2),encoding='utf8')
  profile['cad_don'].append({'id_hinh_goc':ident,'huong_nhin':label,'nhan_hien_thi':label,'duong_dan':drawing.relative_to(path.parent).as_posix(),'bien_the_cad':family,'unit_verification':evidence,'bo_tri_trong_tu':{'cho_phep_chen':code in ['FRONT','SIDE','SIDE-L','SIDE-R','TOP','BOTTOM','REAR'],'envelope_depth_source':code==depth_code,'huong_dan':note}});profile['cac_hinh_cad'].append(ident);report.append({'family':family,'view':code,'path':dest.relative_to(CAT).as_posix(),**evidence})
 profile['cad_chen_tu']={k:profile['cad_don'][0][k] for k in ['id_hinh_goc','huong_nhin','duong_dan']};temp=path.with_suffix('.tmp');temp.write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf8');temp.replace(path);contribution=[r for r in report if r['family']==family]
 import msvcrt,os
 with report_path.with_suffix('.lock').open('a+b') as lock:
  if lock.tell()==0:lock.write(b'0');lock.flush()
  lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_LOCK,1)
  try:
   current=json.loads(report_path.read_text()) if report_path.exists() else []
   merged=[r for r in current if r['family']!=family]+contribution
   temp_report=report_path.with_suffix('.'+str(os.getpid())+'.tmp');temp_report.write_text(json.dumps(merged,indent=2),encoding='utf8');temp_report.replace(report_path)
  finally:
   lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
 print(family,len(views),'faces',len(options),'price options',flush=True)
 return path

def price_option(row, brand="LS"):
 return {'brand':brand,'model':row['sku'],'source_row_id':row['id'],'specifications':{**(row.get('specifications') or {}),'Tên hàng':row['item_name']},'source_url':row.get('source_url'),'source_page':row.get('source_page'),'basis':brand.lower()+'_full_pricebook_native_family','exact_cad_match':False}
