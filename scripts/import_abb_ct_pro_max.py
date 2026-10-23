"""Import six native ABB projections per CT PRO/CT MAX supplier DXF."""
import hashlib,json,sys
from pathlib import Path
import ezdxf
from ezdxf import bbox,disassemble
from ezdxf.addons.drawing import Frontend,RenderContext,svg,layout,matplotlib
from ezdxf.math import Matrix44
from PIL import Image,ImageOps,ImageDraw
from import_abb_ct_faces import ROOT,TYPES
FAMILIES=['CT-PRO-XT','CT-MAX']
def main():
 report=[]
 for family in FAMILIES:
  source=ROOT/'BienDong/ABB/NguonBenNgoai'/family/'source.dxf'
  evidence=json.loads(source.with_name('source.json').read_text(encoding='utf8'))
  doc=ezdxf.readfile(source)
  texts=[e.dxf.text for e in doc.modelspace().query('TEXT')]
  assert 'mm' in texts and '1:1' in texts
  template=ROOT/'BienDong/ABB/CT1M-2/thong_tin_thiet_bi.json'
  profile=json.loads(template.read_text(encoding='utf8'))
  name='Biến dòng ABB '+family
  profile.update(ten_kieu=name,ten_san_pham=name,ma_dong_san_pham=family,thong_so={},tu_khoa_tim_kiem=['ABB',family,'Biến dòng','Current transformer'],nguon_tham_khao=[evidence['source_url']],cad_don=[],cac_hinh_cad=[])
  profile['nhan_dien_ai']['cac_ma_dong_san_pham']=[family]
  profile['muc_do_xac_nhan']='Hình học gốc ABB, đơn vị mm và tỷ lệ 1:1 theo khung tên; chưa xác nhận mã đặt hàng, tỷ số, cấp chính xác và VA.'
  path=ROOT/'BienDong/ABB'/family/'thong_tin_thiet_bi.json';path.parent.mkdir(parents=True,exist_ok=True)
  views=[(10,'WIRE','Mặt xuyên dây'),(11,'SIDE-R','Mặt bên phải'),(12,'SIDE-L','Mặt bên trái'),(13,'TOP' if family=='CT-PRO-XT' else 'BOTTOM','Mặt trên' if family=='CT-PRO-XT' else 'Mặt dưới'),(14,'BOTTOM' if family=='CT-PRO-XT' else 'TOP','Mặt dưới' if family=='CT-PRO-XT' else 'Mặt trên'),(15,'ISO','Hình trục đo')]
  for number,code,label in views:
   insert=next(e for e in doc.modelspace().query('INSERT') if e.dxf.name==f'BLOCK{number}')
   geometry=[e for e in disassemble.recursive_decompose([insert]) if e.dxftype() in TYPES]
   assert len(geometry)>100
   bounds=bbox.extents(geometry);target=ezdxf.new('R2010');target.units=4
   for e in geometry:
    entity=e.copy();entity.dxf.layer='0';entity.dxf.color=7;entity.dxf.linetype='CONTINUOUS'
    entity.transform(Matrix44.translate(-bounds.extmin.x,-bounds.extmin.y,0));target.modelspace().add_entity(entity)
   audit=target.audit();assert not audit.errors
   identity=f'ABB-OFFICIAL-{family}-{code}';destination=path.parent/'CadDon'/identity;destination.mkdir(parents=True,exist_ok=True)
   output=destination/'ban_ve.dxf';target.saveas(output)
   backend=svg.SVGBackend();Frontend(RenderContext(target),backend).draw_layout(target.modelspace(),finalize=True)
   (destination/'xem_truoc.svg').write_text(backend.get_string(layout.Page(0,0,layout.Units.mm)),encoding='utf8')
   matplotlib.qsave(target.modelspace(),destination/'preview.png',dpi=90)
   size=bbox.extents(target.modelspace()).size
   verification={**evidence,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'source_block':insert.dxf.name,'coordinate_scale_to_mm':1,'unit_evidence':'Supplier title block: mm, 1:1','width_mm':size.x,'height_mm':size.y,'entity_count':len(target.modelspace()),'geometry_status':'supplier_reference','ordering_code_verified':False}
   (destination/'evidence.json').write_text(json.dumps(verification,indent=2),encoding='utf8')
   (destination/'thong_tin_cad_chen.json').write_text(json.dumps({'hinh_hoc_lap_dat':{'don_vi':'mm','bao_hinh_mm':{'min_x':0,'min_y':0,'max_x':size.x,'max_y':size.y}},'evidence':verification},indent=2),encoding='utf8')
   profile['cad_don'].append({'id_hinh_goc':identity,'huong_nhin':label,'nhan_hien_thi':f'ABB · CT · {family} · {label}','duong_dan':output.relative_to(path.parent).as_posix(),'bien_the_cad':'abb_official_'+family.lower(),'unit_verification':verification,'bo_tri_trong_tu':{'cho_phep_chen':code!='ISO','huong_dan':'Đối chiếu mã đặt hàng, cửa sổ và tư thế lắp trước khi dùng.'}})
   profile['cac_hinh_cad'].append(identity)
   report.append({'family':family,'view':code,'path':destination.relative_to(ROOT).as_posix(),**verification})
  profile['cad_chen_tu']={k:profile['cad_don'][0][k] for k in ['id_hinh_goc','huong_nhin','duong_dan']}
  path.write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
  print(family,'6 verified projections',flush=True)
 docs=ROOT.parents[1]/'docs';(docs/'abb-ct-pro-max-faces-2026-10-20.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 canvas=Image.new('RGB',(1800,700),'white');draw=ImageDraw.Draw(canvas)
 for i,item in enumerate(report):
  im=ImageOps.contain(Image.open(ROOT/item['path']/'preview.png').convert('RGB'),(285,305));x=i%6*300;y=i//6*350
  canvas.paste(im,(x+(300-im.width)//2,y+35));draw.text((x+8,y+8),item['family']+' '+item['view'],fill='black')
 canvas.save(docs/'abb-ct-pro-max-faces-2026-10-20.png')
if __name__=='__main__':main()
