from pathlib import Path
import json,re,unicodedata
root=Path(__file__).resolve().parents[1]/'data/CatalogTB';before=[]
for p in sorted(root.rglob('thong_tin_thiet_bi.json')):
 d=json.loads(p.read_text(encoding='utf8'))
 if 'BienDong' not in p.parts and 'ThietBiDoLuongHienThi' not in p.parts:
  if (d.get('nhan_dien_ai') or {}).get('loai_thiet_bi_code'):continue
  text=' '.join(str(d.get(k) or '') for k in ['ten_san_pham','ban_chat'])
  text=''.join(c for c in unicodedata.normalize('NFD',text) if not unicodedata.combining(c)).replace('đ','d').upper()
  typ=next((code for pattern,code in [(r'\bCONTACTOR\b|KHOI DONG TU','CONTACTOR'),(r'\bRCBO\b','RCBO'),(r'\bRCCB\b','RCCB'),(r'\bMCCB\b','MCCB'),(r'\bMCB\b','MCB'),(r'\bACB\b','ACB'),(r'CAU CHI','FUSE'),(r'DEN BAO','LIGHT'),(r'NUT NHAN','BUTTON'),(r'CONG TAC XOAY|CHUYEN MACH','SELECTOR')] if re.search(pattern,text)),None)
  if not typ:continue
  ai={'loai_thiet_bi_code':typ,'recognition_basis':'Tên và bản chất trong hồ sơ hiện có; không xác nhận SKU','exact_SKU_confirmed':False}
  poles=(d.get('thong_so') or {}).get('so_cuc_chinh') or (d.get('thong_so') or {}).get('so_cuc')
  if poles:ai['so_cuc']=poles
  d['nhan_dien_ai']=ai
  before.append(str(p.relative_to(root)))
  p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
  continue
 if 'BienDong' in p.parts:
  typ='CT';sub=(d.get('phan_loai_chon') or {}).get('muc_dich');aliases=['CT','biến dòng','bien dong','current transformer',d.get('ma_dong_san_pham') or '',d.get('ten_san_pham') or '']
 else:
  name=p.parent.name;typ='SELECTOR' if name in ['ChuyenMachAmpe','ChuyenMachVon','CongTacOnOff'] else 'METER';sub='current' if name in ['AmpeKeKim','ChuyenMachAmpe'] else 'voltage' if name in ['VonKeKim','Omega_BE-96_500V','ChuyenMachVon'] else None
  aliases=[d.get('ten_san_pham') or '',d.get('ma_dong_san_pham') or '']
  if name=='AmpeKeKim':aliases+=['A','ampe kế','ampe ke','ammeter','đồng hồ đo dòng','dong ho do dong']
  if name=='ChuyenMachAmpe':aliases+=['AS','chọn dòng','chon dong','ammeter selector']
  if name=='ChuyenMachVon':aliases+=['VS','chọn áp','chon ap','voltmeter selector']
 old=d.get('nhan_dien_ai') or {};new={**old,'loai_thiet_bi_code':typ,'measurement_function':sub,'recognition_basis':'Vai trò trong hồ sơ hiện có; không suy model hoặc thang đo từ phân loại','exact_SKU_confirmed':False}
 if typ=='CT':
  units=(d.get('phan_loai_chon') or {}).get('so_CT_trong_cum',1) or 1
  d['cau_truc_cum']={**(d.get('cau_truc_cum') or {}),'physical_units_per_cad':units}
 d['nhan_dien_ai']=new;d['tu_khoa_tim_kiem']=list(dict.fromkeys([*(d.get('tu_khoa_tim_kiem') or []),*(x for x in aliases if x)]))
 if not old.get('loai_thiet_bi_code'):before.append(str(p.relative_to(root)))
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
index=[]
for p in sorted(root.rglob('thong_tin_thiet_bi.json')):
 d=json.loads(p.read_text(encoding='utf8'));index.append({'profile':p.relative_to(root).as_posix(),'name':d.get('ten_san_pham'),'category':d.get('nhom'),'brand':d.get('hang_xac_nhan'),'auto_select':d.get('auto_select'),'needs_review':d.get('needs_review'),'search_aliases':d.get('tu_khoa_tim_kiem',[]),'type':d.get('ban_chat'),'use':d.get('cong_dung'),'spec':d.get('thong_so'),'identification':d.get('nhan_dien_ai',{}),'conductor_requirements':d.get('yeu_cau_chon_day'),'installation_requirements':d.get('yeu_cau_lap_dat'),'parametric_cad':d.get('cad_tham_so'),'views':[{'id':v['id_hinh_goc'],'face':v.get('huong_nhin'),'dxf':(p.parent/v['duong_dan']).relative_to(root).as_posix(),'placement':v.get('bo_tri_trong_tu',{})} for v in d.get('cad_don',[])]})
(root/'ai_device_index.json').write_text(json.dumps({'rules':'ai_selection_rules.json','count':len(index),'items':index},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
audit_path=Path(__file__).resolve().parents[2]/'outputs/order-447-457-audit/catalog-recognition-repair.json'
audit_path.parent.mkdir(parents=True,exist_ok=True)
previous=json.loads(audit_path.read_text(encoding='utf8')) if audit_path.exists() else {}
audit_path.write_text(json.dumps({'formerly_missing_category':list(dict.fromkeys(previous.get('formerly_missing_category',[])+before)),'profile_count':len(index),'scope':'Classification from existing explicit profile identity; CAD geometry and electrical specifications preserved'},ensure_ascii=False,indent=2),encoding='utf8')
print('Profiles indexed',len(index),'newly visible classification',len(before))

