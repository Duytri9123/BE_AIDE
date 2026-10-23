"""Extract native LS ZCT projections without inventing size-specific geometry."""
import hashlib,json
from pathlib import Path
import ezdxf
from ezdxf import bbox,disassemble
from ezdxf.math import Matrix44
from ezdxf.addons.drawing import Frontend,RenderContext,svg,layout,matplotlib
ROOT=Path(__file__).resolve().parents[1]/'data/CatalogTB'
# The group drawings are schematic and must not be reused as exact size CAD.
SPECS=[('LZT-030','45886',False,[(-1390,253,-1275,366),(-1185,250,-1140,366),(-1110,234,-1070,366)]),('LZT-050-065-080-REFERENCE','45886',True,[(-900,265,-765,410),(-680,271,-640,407),(-580,250,-545,410)]),('LZR-030-050-065-V-REFERENCE','45887',True,[(1313,1040,1425,1150),(1483,1040,1530,1150),(1560,1020,1605,1150)]),('LZR-080-V','45887',False,[(1818,1020,1957,1165),(2027,1020,2078,1165),(2120,1020,2178,1165)])]
def main():
 report=[]
 for family,sid,schematic,windows in SPECS:
  folder=ROOT/'BienDong/LS/NguonBenNgoai'/sid;source=folder/'source.dxf';doc=ezdxf.readfile(source);ev=json.loads((folder/'source.json').read_text())
  geometry=[]
  for e in disassemble.recursive_decompose(doc.modelspace()):
   color=e.dxf.color;color=7 if color==0 else (doc.layers.get(e.dxf.layer).dxf.color if color==256 else color)
   if e.dxftype() not in {'LINE','ARC','CIRCLE','ELLIPSE','LWPOLYLINE','POLYLINE'} or color not in {7,4}:continue
   b=bbox.extents([e])
   if b.has_data:geometry.append((e,b))
  aliases={'LZT-030':['LZT-030'],'LZT-050-065-080-REFERENCE':['LZT-050','LZT-065','LZT-080'],'LZR-030-050-065-V-REFERENCE':['LZR-030','LZR-050','LZR-065'],'LZR-080-V':['LZR-080']}[family]
  display_family=family.replace('-REFERENCE',' · Sơ đồ họ thiết bị')
  name='Biến dòng thứ tự không LS '+family.replace('-REFERENCE','')+(' · Sơ đồ họ thiết bị' if schematic else '')
  path=ROOT/'BienDong/LS'/family/'thong_tin_thiet_bi.json';path.parent.mkdir(parents=True,exist_ok=True)
  warning='CAD gốc LS; sơ đồ chung nhiều cỡ, không đại diện kích thước của từng mã.' if schematic else 'CAD gốc LS; cần đối chiếu kích thước và đúng phiên bản với mã đặt hàng trước khi bố trí.'
  profile={'nhom':'BienDong','ten_kieu':name,'ten_san_pham':name,'hang_xac_nhan':'LS','ma_dong_san_pham':family.replace('-REFERENCE',''),'ban_chat':'ZCT','cong_dung':'Biến dòng thứ tự không dùng với bảo vệ chạm đất EMPR LS; không thay cho CT đo lường 1A/5A.','thong_so':{},'nhan_dien_ai':{'loai_thiet_bi_code':'ZCT','measurement_function':'earth_leakage','fabrication_ready':False},'tu_khoa_tim_kiem':['LS','LS ELECTRIC','EMPR','ZCT',family,'Biến dòng thứ tự không',*aliases],'nguon_tham_khao':[ev['source_url'],ev['source_page']],'cad_don':[],'cac_hinh_cad':[],'auto_select':False,'needs_review':True,'muc_do_xac_nhan':warning,'quy_tac_dung_chung_cad':{'relationship':'schematic_family_reference' if schematic else 'supplier_projection_pending_ordering_code','ratio_from_cad':False}}
  for index,window in enumerate(windows):
   code,label=[('WIRE','Mặt xuyên dây'),('SIDE','Mặt bên'),('MOUNT','Mặt đế gá theo bản vẽ')][index];x0,y0,x1,y1=window
   ents=[e for e,b in geometry if b.extmin.x>=x0 and b.extmax.x<=x1 and b.extmin.y>=y0 and b.extmax.y<=y1]
   assert len(ents)>=6,(family,code,len(ents))
   bounds=bbox.extents(ents);target=ezdxf.new('R2010');target.units=4
   for e in ents:
    entity=e.copy();entity.dxf.layer='0';entity.dxf.color=7;entity.dxf.linetype='CONTINUOUS';entity.transform(Matrix44.translate(-bounds.extmin.x,-bounds.extmin.y,0));target.modelspace().add_entity(entity)
   assert not target.audit().errors
   ident=f'LS-OFFICIAL-{family}-{code}';dest=path.parent/'CadDon'/ident;dest.mkdir(parents=True,exist_ok=True);output=dest/'ban_ve.dxf';target.saveas(output)
   backend=svg.SVGBackend();Frontend(RenderContext(target),backend).draw_layout(target.modelspace(),finalize=True);(dest/'xem_truoc.svg').write_text(backend.get_string(layout.Page(0,0,layout.Units.mm)),encoding='utf8');matplotlib.qsave(target.modelspace(),dest/'preview.png',dpi=100)
   size=bbox.extents(target.modelspace()).size
   evidence={**ev,'source_dxf_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'extraction_window':window,'width_mm':size.x,'height_mm':size.y,'entity_count':len(target.modelspace()),'coordinate_scale_to_mm':1,'unit_evidence':'Supplier drawing dimension table: mm; no coordinate rescaling','geometry_status':'schematic_reference' if schematic else 'supplier_reference_pending_dimensions','ordering_code_verified':False}
   (dest/'evidence.json').write_text(json.dumps(evidence,indent=2),encoding='utf8');(dest/'thong_tin_cad_chen.json').write_text(json.dumps({'hinh_hoc_lap_dat':{'don_vi':'mm','bao_hinh_mm':{'min_x':0,'min_y':0,'max_x':size.x,'max_y':size.y}},'evidence':evidence},indent=2),encoding='utf8')
   profile['cad_don'].append({'id_hinh_goc':ident,'huong_nhin':label,'nhan_hien_thi':f'LS · ZCT · {display_family} · {label}','duong_dan':output.relative_to(path.parent).as_posix(),'bien_the_cad':'ls_official_'+family,'unit_verification':evidence,'bo_tri_trong_tu':{'cho_phep_chen':False,'huong_dan':warning}});profile['cac_hinh_cad'].append(ident)
   report.append({'family':family,'view':code,'path':dest.relative_to(ROOT).as_posix(),**evidence})
  profile['cad_chen_tu']={k:profile['cad_don'][0][k] for k in ['id_hinh_goc','huong_nhin','duong_dan']};path.write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(family,'3 views',flush=True)
 (ROOT.parents[1]/'docs/ls-zct-faces-2026-10-20.json').write_text(json.dumps(report,indent=2),encoding='utf8')
if __name__=='__main__':main()
