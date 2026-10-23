"""Import six observed Schneider syndicated projections; retain original geometry."""
import hashlib,json,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from ezdxf import bbox
from ls_native_writer import write_profile,price_option
from publish_abb_ct_index import main as publish
ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB'
FAMILY='MCADPD0003997-GV2ME10'
HASHES={'front':'5b66827ca679dbf27a84b2a1bcf603553cea20ac','back':'d12fb147723218df2aef75d25d506fa1a61ec97c','left':'8f3c723103cd12467b6e328a7ce5a9df285af491','right':'bf3a239014e9e28efcf175c617b09d0e0ee6bd9d','top':'41b16cd76156342eb6add61692e92595f14a08a1','bottom':'d480bdc7a99c0c2cb4222f385c97b34dff94a564'}
LABELS={'front':('FRONT','Mặt trước'),'back':('REAR','Mặt sau'),'left':('SIDE-L','Mặt bên trái'),'right':('SIDE-R','Mặt bên phải'),'top':('TOP','Mặt trên'),'bottom':('BOTTOM','Mặt dưới')}
def main():
 target=CAT/'Schneider/ThietBi'/('OFFICIAL-'+FAMILY)
 assert not target.exists(),'Already imported'
 native=CAT/'Schneider/NguonBenNgoai'/FAMILY;native.mkdir(parents=True,exist_ok=True)
 sources=[];views=[]
 for face,h in HASHES.items():
  dest=native/('MCADPD0003997_2D-'+face+'.dxf');shutil.copy2(Path('E:/Downloads')/(h+'.dxf'),dest)
  doc=ezdxf.readfile(dest);assert doc.units==4
  audit=doc.audit();assert not audit.errors
  assert all(e.dxftype() in {'LINE','CIRCLE','ARC','SPLINE','ELLIPSE','LWPOLYLINE','POLYLINE'} for e in doc.modelspace())
  size=bbox.extents(doc.modelspace()).size
  sources.append({'face':face,'file':dest.name,'url':'https://media.distributordatasolutions.com/schneider_synd/2023q2/documents/'+h+'.dxf','download_url':'https://media.nuovaelva.it/file/store-media/media/datasheet/schneider_synd/2023q2/documents/'+h+'.dxf','sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'width_mm':size.x,'height_mm':size.y,'source_audit_fixes':len(audit.fixes)})
  views.append((*LABELS[face],list(doc.modelspace())))
 sizes={s['face']:s for s in sources}
 assert abs(sizes['front']['height_mm']-sizes['right']['height_mm'])<.1
 assert abs(sizes['front']['width_mm']-sizes['top']['width_mm'])<.1
 source={'source_url':'https://nuovaelva.it/store/en/shop/brands/TEL/items/GV2ME10','manufacturer_document':'https://www.se.com/uk/en/product/GV2ME10/','cad_document_ref':'MCADPD0003997','checked_at':'2026-10-21','original_views':sources,'coordinate_unit':'mm','geometry_resized':False,'review_note':'Same six download anchors verified on GV2ME10 page. Source CAD title specifies 4–6.3 A; no electrical ratings transferred from GV2ME14 listing.'}
 (native/'source.json').write_text(json.dumps(source,ensure_ascii=False,indent=2),encoding='utf8')
 rows=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items']
 row=next(r for r in rows if r['sku']=='GV2ME10' and r['brand']=='Schneider Electric')
 spec={'Dải chỉnh định (A)':'4–6.3','Số cực':'3P','Kiểu bảo vệ':'Nhiệt – từ','Đầu nối':'Kẹp vít','Kiểu lắp':'Gài ray DIN 35 mm; gá tấm cần phụ kiện','Vị trí thường lắp':'Ngăn bảo vệ và điều khiển động cơ'}
 option=price_option(row,brand='Schneider Electric');option['basis']='schneider_full_pricebook_native_family';option['specifications'].update(spec)
 profile=write_profile(FAMILY,'MPCB Schneider Electric GV2ME10 · 3P · 4–6.3 A','MPCB',['GV2ME10'],'3P',[option],views,source,spec,brand='Schneider Electric')
 ledger=ROOT/'app/data/catalog_verified_view_health.json';health=json.loads(ledger.read_text(encoding='utf8'))
 for path in profile.parent.glob('CadDon/*/ban_ve.dxf'):
  d=ezdxf.readfile(path);audit=d.audit();assert d.units==4 and not audit.errors and not audit.fixes
  health['files'][path.relative_to(CAT).as_posix()]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'preview_sha256':hashlib.sha256(path.with_name('xem_truoc.svg').read_bytes()).hexdigest()}
 ledger.write_text(json.dumps(health,ensure_ascii=False,indent=2),encoding='utf8')
 publish(['OFFICIAL-'+FAMILY],report_name='schneider-full-faces-2026-10-21',brand='Schneider Electric',category='MPCB',profile_root='Schneider/ThietBi')
if __name__=='__main__':main()
