"""Import dimension-checked native LS body projections and explicit pricebook options."""
import hashlib,json,re,sys,collections
from pathlib import Path
import ezdxf
from ezdxf import bbox,disassemble
from ezdxf.math import Matrix44
from ezdxf.addons.drawing import Frontend,RenderContext,svg,layout,matplotlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));CAT=ROOT/'data/CatalogTB'
# Source windows pin native supplier projections. No pole count is synthesized.
GROUPS=[
('META100','45190',[(2,(1753.94,1724.679,1803.943,1854.683),50,130),(3,(1998.94,1724.679,2073.943,1854.683),75,130),(4,(2268.94,1724.679,2368.943,1854.683),100,130)],(2559.954,1724.679,2640.101,1854.683),['ABN50c','ABN60c','ABN100c','ABS30c','ABS50c','ABS60c']),
('META125','45191',[(2,(1959.407,825.25,2019.41,980.253),60,155),(3,(2242.636,826.726,2332.639,981.729),90,155),(4,(2515.345,823.327,2635.348,978.33),120,155)],(2777.662,826.726,2859.665,981.729),['ABS125c','ABH50c','ABH125c','ABL125c']),
('META250','45192',[(3,(321.518,709.766,426.522,874.77),105,165),(4,(1635.414,704.146,1775.417,869.151),140,165)],(151.727,709.766,238.581,874.77),['ABN250c','ABS250c','ABH250c','ABL250c']),
('META400','45193',[(3,(2168.248,1095.216,2308.252,1352.22),140,257),(4,(2577.833,1095.216,2761.837,1352.22),184,257)],(3008.937,1095.216,3154.207,1352.22),['ABN400c','ABS400c','ABH400c','ABL400c'])]
CONTACTORS=[('MC6-18A-AC-1A1B','50302',['MC-6a','MC-9a','MC-12a','MC-18a'],(2728.275,3615.932,2773.279,3691.436),(2820.451,3615.832,2900.854,3691.436),45,75.5),('MC32-40A-AC','55918',['MC-32a','MC-40a'],(2109.134,4065.802,2154.137,4148.807),(2212.342,4065.802,2302.346,4148.807),45,83),('MC50-65A-AC','50316',['MC-50a','MC-65a'],(2163.53,4010.631,2218.534,4116.637),(2285.233,4010.671,2404.237,4116.677),55,106),('MC75-100A-AC','50320',['MC-75a','MC-85a','MC-100a'],(2146.651,4012.768,2216.655,4152.773),(2265.89,4013.304,2401.695,4153.309),70,140)]
PRICES=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items']
def options(group,kind,poles,models,width,height):
 found=[]
 for row in PRICES:
  if str(row.get('brand','')).lower() not in ['ls','ls electric'] or row.get('category')!=kind:continue
  sku=str(row.get('sku',''));spec=row.get('specifications') or {}
  if kind=='MCCB':
   m=re.fullmatch(r'(ABN|ABS|ABH|ABL)(\d+)([bc])',sku,re.I)
   if not m or int(m[2][-1])!=poles:continue
   dims=[float(v) for v in re.findall(r'\d+(?:\.\d+)?',str(spec.get('Kích thước bao W×H×D (mm)') or ''))]
   if dims:
    if len(dims)<2 or abs(dims[0]-width)>.1 or abs(dims[1]-height)>.1:continue
   elif not (group=='META400' and m[2][:-1]=='40'):continue
  else:
   if not any(re.match(re.escape(model)+r'(?![A-Za-z0-9])',sku,re.I) for model in models):continue
   # A 3-pole AC outline cannot stand for a DC-coil or four-pole CAD.
   if re.search(r'\b4P\b|\bDC\b|VDC|/4',sku+' '+str(row.get('group','')),re.I):continue
  found.append({'brand':'LS','model':sku,'source_row_id':row['id'],'specifications':{**spec,'Tên hàng':row.get('item_name') or sku},'source_url':row.get('source_url'),'source_page':row.get('source_page'),'basis':'ls_shared_body_price_configuration','exact_cad_match':False})
 return found

def main():
 report=[];profiles=[]
 jobs=[(group,sid,'MCCB',p,models,front,side,w,h) for group,sid,fronts,side,models in GROUPS for p,front,w,h in fronts]+[(group,sid,'CONTACTOR',3,models,front,side,w,h) for group,sid,models,front,side,w,h in CONTACTORS]
 for sid in dict.fromkeys(job[1] for job in jobs):
  source=CAT/'LS/NguonBenNgoai'/sid/'source.dxf';doc=ezdxf.readfile(source);ev=json.loads(source.with_name('source.json').read_text(encoding='utf8'));samples=[]
  for e in doc.modelspace().query('DIMENSION'):
   n=e.get_measurement();a=e.dxf.get('actual_measurement')
   if isinstance(n,(int,float)) and a and a>5:samples.append(round(n/a,5))
  counts=collections.Counter(samples);assert counts[1.0]>=10 and counts[1.0]/len(samples)>.9,(sid,counts)
  geometry=[]
  for src in doc.modelspace():
   if src.dxftype() in {'DIMENSION','ACAD_TABLE','LEADER','MLEADER'}:continue
   for e in disassemble.recursive_decompose([src]):
    if e.dxftype() not in {'LINE','ARC','CIRCLE','SPLINE','ELLIPSE','LWPOLYLINE','POLYLINE'}:continue
    if e.dxf.layer.lower() in {'di','ce','barrier','busbar','dim','defpoints','center','center line','demension','3_all_axes'}:continue
    box=bbox.extents([e])
    if box.has_data:geometry.append((e,box))
  for group,_,kind,poles,models,front,side,width,height in [job for job in jobs if job[1]==sid]:
   family=group+f'-{poles}P';profile_path=CAT/'LS/ThietBi'/('OFFICIAL-'+family)/'thong_tin_thiet_bi.json';profile_path.parent.mkdir(parents=True,exist_ok=True)
   refs=options(group,kind,poles,models,width,height);kas=sorted(set(str(o['specifications'].get('Icu(KA)') or '').replace('KA','').strip() for o in refs)-{''})
   model_text=' / '.join(models);rating=' · Icu '+('/'.join(kas))+' kA theo bảng giá' if kas else ''
   name=f'LS · {kind} · {model_text} · {poles}P'+rating
   note='CAD thân gốc LS, đơn vị mm đã đối chiếu kích thước. Các mã trong bảng giá là lựa chọn cấu hình; xác nhận In, Icu/Ics tại điện áp sử dụng, đầu nối và phụ kiện trước khi chọn mã.' if kind=='MCCB' else 'CAD contactor cuộn AC gốc LS; chọn điện áp cuộn hút, tiếp điểm phụ và mã đặt hàng riêng. Không dùng hình này cho cuộn DC hoặc bản 4P.'
   profile={'nhom':'LS','ten_kieu':name,'ten_san_pham':name,'hang_xac_nhan':'LS','ma_dong_san_pham':model_text,'ban_chat':kind,'cong_dung':note,'thong_so':{'so_cuc':f'{poles}P','Kích thước mặt trước (mm)':f'{width} × {height}'},'nhan_dien_ai':{'loai_thiet_bi_code':kind,'so_cuc':poles,'cac_ma_dong_san_pham':models,'exact_SKU_confirmed':False},'tu_khoa_tim_kiem':['LS','LS ELECTRIC',kind,*models,*[o['model'] for o in refs]],'nguon_tham_khao':[ev['source_url']],'cad_don':[],'cac_hinh_cad':[],'auto_select':False,'needs_review':True,'muc_do_xac_nhan':note,'catalog_tham_khao':{'category':kind,'options':refs},'quy_tac_dung_chung_cad':{'relationship':'one_geometry_many_configuration_options','electrical_rating_from_geometry':False,'requirements':['Đúng họ, số cực, kiểu lắp và đầu nối','Icu/Ics phải kiểm tra tại điện áp làm việc','Đúng In và cơ cấu bảo vệ; contactor cần đúng cuộn hút và tiếp điểm phụ']}}
   if kind=='CONTACTOR':profile['thong_so']['Loại cuộn hút']='AC'
   for code,label,window in [('FRONT','Mặt trước',front),('SIDE','Mặt bên',side)]:
    x,y,X,Y=window;ents=[e for e,b in geometry if b.extmin.x>=x and b.extmax.x<=X and b.extmin.y>=y and b.extmax.y<=Y];assert len(ents)>=50,(family,code,len(ents));bounds=bbox.extents(ents)
    assert abs(bounds.size.y-height)<.3,(family,code,bounds.size)
    if code=='FRONT':assert abs(bounds.size.x-width)<.3,(family,bounds.size)
    target=ezdxf.new('R2010');target.units=4
    for e in ents:
     ent=e.copy();ent.dxf.layer='0';ent.dxf.color=7;ent.dxf.linetype='CONTINUOUS';ent.transform(Matrix44.translate(-bounds.extmin.x,-bounds.extmin.y,0));target.modelspace().add_entity(ent)
    assert not target.audit().errors
    ident=f'LS-OFFICIAL-{family}-{code}';dest=profile_path.parent/'CadDon'/ident;dest.mkdir(parents=True,exist_ok=True);output=dest/'ban_ve.dxf';target.saveas(output)
    back=svg.SVGBackend();Frontend(RenderContext(target),back).draw_layout(target.modelspace(),finalize=True);(dest/'xem_truoc.svg').write_text(back.get_string(layout.Page(0,0,layout.Units.mm)),encoding='utf8');matplotlib.qsave(target.modelspace(),dest/'preview.png',dpi=85)
    size=bbox.extents(target.modelspace()).size;evidence={**ev,'source_dxf_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'extraction_window':window,'width_mm':size.x,'height_mm':size.y,'entity_count':len(ents),'coordinate_scale_to_mm':1,'dimension_scale_samples':dict((str(k),v) for k,v in counts.items()),'ordering_code_verified':False}
    (dest/'evidence.json').write_text(json.dumps(evidence,indent=2),encoding='utf8');(dest/'thong_tin_cad_chen.json').write_text(json.dumps({'hinh_hoc_lap_dat':{'don_vi':'mm','bao_hinh_mm':{'min_x':0,'min_y':0,'max_x':size.x,'max_y':size.y}},'evidence':evidence},indent=2),encoding='utf8')
    profile['cad_don'].append({'id_hinh_goc':ident,'huong_nhin':label,'nhan_hien_thi':name+' · '+label,'duong_dan':output.relative_to(profile_path.parent).as_posix(),'bien_the_cad':family,'unit_verification':evidence,'bo_tri_trong_tu':{'cho_phep_chen':True,'huong_dan':'CAD tham khảo bố trí; xác nhận mã và phụ kiện trước gia công.'}});profile['cac_hinh_cad'].append(ident);report.append({'family':family,'view':code,'path':dest.relative_to(CAT).as_posix(),**evidence})
   profile['cad_chen_tu']={k:profile['cad_don'][0][k] for k in ['id_hinh_goc','huong_nhin','duong_dan']};profile_path.write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf8');profiles.append({'profile':profile_path.relative_to(CAT).as_posix(),'configuration_count':len(refs)});print(family,'2 views',len(refs),'price options',flush=True)
 (ROOT/'docs/ls-main-faces-2026-10-20.json').write_text(json.dumps(report,indent=2),encoding='utf8');(ROOT/'docs/ls-main-profiles-2026-10-20.json').write_text(json.dumps(profiles,indent=2),encoding='utf8')
if __name__=='__main__':main()
