"""Import reviewed manufacturer six-view CAD, quarantine unresolved source views."""
import hashlib,json,shutil,sqlite3,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from ezdxf import bbox
from ls_native_writer import write_profile,price_option
ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB';OUT=ROOT/'docs/schneider-update-2026-10-21'
LABELS={'front':('FRONT','Mặt trước'),'back':('REAR','Mặt sau'),'left':('SIDE-L','Mặt bên trái'),'right':('SIDE-R','Mặt bên phải'),'top':('TOP','Mặt trên'),'bottom':('BOTTOM','Mặt dưới')}
LR_HASH={'front':'34653986de4c49ab293120056cf8ec82bc91fd5a','back':'7a4a867e9a15ba95488626d3614a93949b504128','left':'a1c7dac286efd75c32018288d039493e0c7be4e5','right':'7785606979f0abc40a7d6ee923c86c6b832012ec','top':'73f87024700e5ba1f1e6217c6acb55b340fcf188','bottom':'e838cb494fb98d85983aaabec358e51807e928e5'}

def write(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);pending=path.with_suffix('.pending');pending.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8');pending.replace(path)

def main():
 OUT.mkdir(exist_ok=True)
 if (OUT/'changes.json').exists():raise RuntimeError('Already applied; verify instead')
 prices_path=ROOT/'app/data/supplier_pricebooks.json';prices=json.loads(prices_path.read_text(encoding='utf8'));shutil.copy2(prices_path,OUT/'supplier-pricebooks.before.json')
 corrections=[]
 for row in prices['items']:
  if row['sku'] not in {'A9F74150','A9F74216','A9F74316','A9F74416'} or row.get('brand')!='Schneider Electric':continue
  sku=row['sku'];pole={'A9F74150':'1P','A9F74216':'2P','A9F74316':'3P','A9F74416':'4P'}[sku];current='50' if sku=='A9F74150' else '16'
  corrections.append({'id':row['id'],'sku':sku,'old_category':row['category'],'new_category':'MCB','source_url':'https://www.se.com/sg/en/product/'+sku+'/'})
  row['category']='MCB';row['group']='MCB · Acti9 iC60N';row['item_name']=row['name']='MCB Schneider iC60N '+pole+' '+current+' A · C'
  row['specifications'].update({'Họ thiết bị':'iC60N','Số cực':pole,'In (A)':current,'Đặc tuyến':'C'})
  row['technical_review']={'source_url':'https://www.se.com/sg/en/product/'+sku+'/','checked_at':'2026-10-21','scope':'MCB category, poles, current, curve only; voltage-specific ratings remain separate'}
  if row.get('columns') and row.get('cells'):
   for i,k in enumerate(row['columns']):
    if i<len(row['cells']) and k in {'Tên hàng','Tên thiết bị'}:row['cells'][i]=row['item_name']
 write(prices_path,prices)
 additions=[]
 for family,prefix,sku,kind,poles,spec,page in [
  ('MCADFD0000998-iC60N-1P','MCADFD0000998','A9F74150','MCB','1P',{'In (A)':'50','Đặc tuyến':'C','Icn tại 230 V AC · IEC 60898-1 (kA)':'6','Icu tại 220–240 V AC · IEC 60947-2 (kA)':'10','Kiểu lắp':'Gài ray DIN','Vị trí thường lắp':'Ngăn phân phối nhánh'},'https://electgo.com/product/se-a9f74150'),
  ('MCADPD0004675-LRD21','MCADPD0004675','LRD21','THERMAL_RELAY',None,{'Dải chỉnh định (A)':'12–18','Cấp tác động':'10A','Tiếp điểm phụ':'1NO + 1NC','Kiểu lắp':'Ghép dưới contactor tương thích; gá riêng cần phụ kiện','Vị trí thường lắp':'Ngăn điều khiển và bảo vệ động cơ'},'https://nuovaelva.it/store/en/shop/brands/TEL/items/LRD21')]:
  native=CAT/'Schneider/NguonBenNgoai'/family;native.mkdir(parents=True,exist_ok=True);views=[];sources=[]
  for face,(code,label) in LABELS.items():
   filename=prefix+'_2D-'+face+'.dxf';original=Path('E:/Downloads')/filename;assert original.is_file(),original
   dest=native/filename;shutil.copy2(original,dest);doc=ezdxf.readfile(dest);assert doc.units==4
   audit=doc.audit();assert not audit.errors
   assert all(e.dxftype() in {'LINE','ARC','CIRCLE','ELLIPSE','SPLINE','LWPOLYLINE','POLYLINE'} for e in doc.modelspace())
   views.append((code,label,list(doc.modelspace())))
   url=('https://download.schneider-electric.com/files?p_enDocType=CAD&p_File_Name='+filename+'&p_Doc_Ref='+prefix+'_3D-CAD') if kind=='MCB' else 'https://media.distributordatasolutions.com/schneider_synd/2023q2/documents/'+LR_HASH[face]+'.dxf'
   size=bbox.extents(doc.modelspace()).size;sources.append({'face':face,'file':filename,'url':url,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'width_mm':size.x,'height_mm':size.y,'source_audit_fixes':len(audit.fixes)})
  sizes={s['face']:s for s in sources}
  assert abs(sizes['front']['height_mm']-sizes['left']['height_mm'])<.02 and abs(sizes['front']['width_mm']-sizes['top']['width_mm'])<.02
  assert abs(sizes['left']['width_mm']-sizes['top']['height_mm'])<.02
  source={'source_url':page,'manufacturer_document':'https://www.se.com/sg/en/product/'+sku+'/','cad_document_ref':prefix+'_3D-CAD','checked_at':'2026-10-21','original_views':sources,'coordinate_unit':'mm','geometry_resized':False}
  write(native/'source.json',source)
  rows=[r for r in prices['items'] if r['sku']==sku and r.get('brand')=='Schneider Electric'];assert len(rows)==1
  option=price_option(rows[0],brand='Schneider Electric');option['specifications'].update(spec);option['basis']='schneider_full_pricebook_native_family'
  name=('MCB Schneider iC60N · 1P · 50 A · Icn 6 kA/230 V AC' if kind=='MCB' else 'Rơ le nhiệt Schneider LRD21 · 12–18 A · 10A')
  profile=write_profile(family,name,kind,[sku],poles,[option],views,source,spec,brand='Schneider Electric')
  additions.append({'profile':profile.relative_to(CAT).as_posix(),'sku':sku,'views':6})
 # Preserve the rejected raw sources outside the active CadDon tree.
 issues=json.loads((ROOT/'docs/schneider-current-audit-2026-10-21/issues.json').read_text(encoding='utf8'));quarantine_path=ROOT/'app/data/catalog_quarantined_views.json';quarantine=json.loads(quarantine_path.read_text(encoding='utf8'))
 for issue in issues:
  profile=CAT/issue['profile'];raw=json.loads(profile.read_text(encoding='utf8'));backup=OUT/'before'/issue['profile'];backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(profile,backup)
  entry=next(v for v in raw['cad_don'] if v['id_hinh_goc']==issue['id']);source_dir=(profile.parent/entry['duong_dan']).parent.resolve();dest=(OUT/'quarantined-cad'/issue['id']).resolve()
  assert source_dir.is_relative_to(CAT.resolve()) and dest.is_relative_to(OUT.resolve()) and not dest.exists()
  dest.parent.mkdir(exist_ok=True);shutil.move(str(source_dir),str(dest))
  raw['cad_don']=[v for v in raw['cad_don'] if v['id_hinh_goc']!=issue['id']];raw['cac_hinh_cad']=[v for v in raw.get('cac_hinh_cad',[]) if v!=issue['id']]
  if not raw['cad_don']:raw['browser_hidden']=True;raw['cad_chen_tu']={}
  entry['quarantine_reason']='unresolved face or unverified multiple-device source';raw.setdefault('quarantined_cad_views',[]).append(entry);write(profile,raw)
  quarantine['items'].append({'catalog_id':issue['profile_id'],'view_id':issue['id'],'reason':entry['quarantine_reason'],'archived_path':dest.relative_to(ROOT).as_posix()})
 write(quarantine_path,quarantine)
 with sqlite3.connect(CAT/'_agent_index/equipment_catalog.sqlite') as db:
  for issue in issues:
   db.execute('DELETE FROM equipment WHERE catalog_id=?',(issue['profile_id'],));db.execute('DELETE FROM equipment_fts WHERE catalog_id=?',(issue['profile_id'],))
 write(OUT/'changes.json',{'price_category_corrections':corrections,'added_families':additions,'quarantined_views':issues,'pending_source':{'MCADPP0003369':'Downloaded from LC1D09M7 listing, but titled control relay AC and measured front width 59.26 mm, not the 45 mm device body; not imported without configuration review.'}})
 print(json.dumps({'new_faces':12,'quarantined_faces':len(issues),'price_rows_corrected':len(corrections)}),flush=True)

if __name__=='__main__':main()
