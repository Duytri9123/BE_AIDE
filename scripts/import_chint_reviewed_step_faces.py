"""Publish only dimension/pose-reviewed CHINT sources; keep questionable STEP files outside the library."""
import json,hashlib,re,sys
from ls_native_writer import ROOT,CAT,write_profile,price_option
from import_ls_step_family import entities

ACB=[('FRONT','SIDE-L',90),('REAR','SIDE',-90),('SIDE-L','TOP',180),('SIDE','BOTTOM',0),('TOP','FRONT',90),('BOTTOM','REAR',90)]
NXM250=[('FRONT','SIDE-L',0),('REAR','SIDE',0),('SIDE-L','REAR',0),('SIDE','FRONT',0),('TOP','TOP',90),('BOTTOM','BOTTOM',-90)]
JOBS=[('NXM-160S-2P',ACB,63,155),('NXM-160S-3P',ACB,90,155),('NXM-160S-4P',ACB,120,155),('NXM-250S-3P',NXM250,105,165)]

def main():
 rows=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items']
 for ident,mapping,width,height in JOBS:
  if len(sys.argv)>1 and ident not in sys.argv[1:]:continue
  frame,poles=ident.rsplit('-',1);pole=poles[0]
  options=[r for r in rows if r.get('brand','').upper()=='CHINT' and r.get('category')=='MCCB' and r['sku'].startswith(frame+'/'+pole)]
  assert options,ident
  views,prefix=entities(ident,mapping,'Chint');assert views
  from ezdxf import bbox
  size=bbox.extents(views[0][2]).size
  assert abs(size.x-width)<.2 and abs(size.y-height)<.2,(ident,tuple(size))
  p=CAT/'Chint/NguonBenNgoai'/ident;source=json.loads((p/'source.json').read_text())
  source.update(step_sha256=hashlib.sha256((p/'source.step').read_bytes()).hexdigest(),projection_method='Open CASCADE polygonal visible-edge HLR; absolute mesh deflection 0.05 mm',unit_evidence='Manufacturer STEP; STEPControl import MM; output INSUNITS=4',axis_mapping=[{'view':c,'source_projector':o,'rotation_degrees':a} for c,o,a in mapping],six_views_verified=True,family_compatibility_evidence={'catalogue':'NXM-CATALOG/source.pdf','pdf_page':27,'coding_page':9,'front_width_mm':width,'front_height_mm':height,'review':'Fixed front connection, correct pole count and S frame only. Geometry includes the original handle pose; full projection depth is larger than nominal body depth. 4P neutral arrangement and ordered electrical release require separate verification.'})
  values=sorted({str(v) for r in options for k,v in (r.get('specifications') or {}).items() if k.lower().startswith('icu')})
  name='CHINT · MCCB · '+frame+' · '+poles+(' · Icu '+ '/'.join(values)+' theo bảng giá' if values else '')
  write_profile('STEP-'+ident,name,'MCCB',[frame],poles,[price_option(r,brand='CHINT') for r in options],views,source,{'Kiểu lắp':'Cố định; đấu nối phía trước','Đối chiếu cấu hình':'Kiểm tra In, Icu/Ics tại điện áp làm việc, cơ cấu bảo vệ, cực N và đầu nối theo mã đặt hàng','Bao hình':'Giữ tư thế tay gạt và toàn bộ hình học gốc STEP'},brand='CHINT')
if __name__=='__main__':main()
