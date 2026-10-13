"""Import reviewed ABB, O-Sung and RMU geometry with explicit identity evidence."""
import json,re,shutil
from pathlib import Path
from populate_catalogtb_chint import ROOT, drawing, save
BASE=ROOT.parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
ABBURL={
 'MCB':'https://new.abb.com/docs/librariesprovider74/lp-materials/prom-2014-2csc400002d0211.pdf?sfvrsn=2',
 'MCCB':'https://new.abb.com/low-voltage/products/circuit-breakers/tmax/iec',
 'FORMULA':'https://new.abb.com/docs/librariesprovider22/technical-documentation/formula.pdf?sfvrsn=2',
 'Motor':'https://new.abb.com/low-voltage/en-CA/products/motor-protection',
 'SPD':'https://new.abb.com/docs/librariesprovider74/lp-materials/main-catalog_surge-and-lightning-protection-solutions_en.pdf?sfvrsn=2',
 'RCBO':'https://new.abb.com/products/2CSR245180R0064/ds201-l-c6-a10',
 'RCCB':'https://new.abb.com/low-voltage/el/products/system-pro-m/residual-current-devices/rccb'}
reports={}
def profile(brand,key,kind,code,poles,states,urls,notes=(),uncertain=False,specs=None):
 folder=ROOT/brand/'ThietBi'/key;entries=[]
 for s,face,label,path in states:
  v=drawing(folder,s,face,label,source_path=path);v['vai_tro_cad']='device_view';entries.append(v)
  for svg in [folder/'HinhChieu'/s/'xem_truoc.svg',folder/'CadDon'/s/'xem_truoc.svg']:
   text=svg.read_text(encoding='utf-8');text=re.sub(r'stroke-width: ([0-9.]+)',lambda m:'stroke-width: '+str(max(1000,float(m[1]))),text);svg.write_text(text,encoding='utf-8')
 primary=next((v for v in entries if v['huong_nhin']=='Mặt trước'),entries[0])
 dest=folder/'CadChenTu';dest.mkdir(exist_ok=True)
 for f in ('ban_ve.dxf','xem_truoc.svg','thong_tin_cad_chen.json'):shutil.copy2(folder/'CadDon'/primary['id_hinh_goc']/f,dest/f)
 name=f'{kind} {"" if brand=="RMU" else brand+" "}{code or "chưa rõ mã"}'+(f' · {poles}' if poles else '')
 mounting={'vi_tri_uu_tien':'san_phong_dien' if kind=='RMU' else 'ben_trong','vi_tri_phu_hop':['san_phong_dien'] if kind=='RMU' else ['ben_trong'],
 'huong_dan':'Cụm tủ trung thế độc lập; kiểm tra nền, khoảng thao tác, cáp và thoát áp theo tài liệu đúng cấu hình.' if kind=='RMU' else 'Gá ray/tấm lắp hoặc gắn trên thiết bị chủ theo tài liệu mã đầy đủ; kiểm tra chiều sâu, cọc và khoảng đấu dây.'}
 aliases=[name,code or '',brand,kind,{'MCB':'aptomat tép','MCCB':'aptomat khối','RCBO':'chống rò quá dòng','RCCB':'chống rò','Contactor':'khởi động từ','Thermal Relay':'rơ le nhiệt','Aux Contact':'tiếp điểm phụ','Interlock':'liên động','SPD':'chống sét lan truyền','ATS':'chuyển nguồn tự động','RMU':'tủ trung thế'}.get(kind,kind)]
 d={'nhom':brand,'ten_kieu':name,'ten_san_pham':name,'hang_xac_nhan':None if brand=='RMU' else ('O-Sung / OSEMCO' if brand=='O-Sung' else brand),
 'ma_dong_san_pham':code,'ban_chat':kind,'cong_dung':aliases[-1],'bo_tri_lap_dat':mounting,'vi_tri_lap_dat':mounting['huong_dan'],
 'thong_so':{'so_cuc':poles,'dong_dinh_muc_da_chon':None,'dien_ap_da_chon':None,'kha_nang_cat_da_chon':None,**(specs or {})},
 'quy_cach_hien_thi':(poles+' · ' if poles else '')+('Cần xác nhận mã/cấu hình' if uncertain else 'Chọn thông số điện'),
 'cad_don':entries,'cac_hinh_cad':[v['id_hinh_goc'] for v in entries],
 'cad_chen_tu':{'id_hinh_goc':primary['id_hinh_goc'],'huong_nhin':primary['huong_nhin'],'duong_dan':'CadChenTu/ban_ve.dxf'},
 'tu_khoa_tim_kiem':aliases,'nguon_tham_khao':urls,'tai_lieu_hang':urls[0] if urls else None,
 'muc_do_xac_nhan':'Nhãn CAD nguồn; chưa xác nhận đầy đủ mã và cấu hình lắp.' if uncertain else 'Mã/dòng trong CAD; tài liệu hãng tham khảo, chưa chọn mã đặt hàng đầy đủ.',
 'dac_diem':['Giữ kích thước CAD gốc; không suy thông số điện từ nhãn mẫu.','Mỗi CAD là một mặt hoặc biến thể; chọn đúng mặt chính theo bố trí.',*notes],
 'lua_chon_ky_thuat':['Chọn mã đầy đủ, thông số điện, phụ kiện, kiểu gá và mặt CAD trước lắp.'],
 'nhan_dien_ai':{'loai_thiet_bi_code':kind.replace(' ','_'),'hang':None if brand=='RMU' else brand,'cac_ma_dong_san_pham':[code] if code else [],'so_cuc':poles,
 'pham_vi_ma':'source_model_or_family','tu_dong_chon_theo_vai_tro':not uncertain,'ma_dat_hang_da_chon':None,'fabrication_ready':False},
 'cau_hinh_chon':{'can_chon':['Mã đầy đủ','Thông số điện','Phụ kiện','Kiểu gá','Mặt CAD'],'ma_da_chon':None},
 'yeu_cau_chon_day':{'vai_tro_ket_noi':['Nguồn vào','Ra tải','Điều khiển/phụ kiện nếu có'],'tiet_dien_mac_dinh_mm2':None,'quy_tac':'Chọn theo từng cọc, dòng tải, bảo vệ và giới hạn đầu nối mã đầy đủ; không suy từ CAD.'},
 'yeu_cau_lap_dat':{'schema':'installation_contract.schema.json','status':'Cần dữ liệu gá và cọc theo mã đầy đủ','unknown_value':None,'cad_rotation_is_mounting_approval':False}}
 if kind in ('Aux Contact','Interlock','Thermal Relay'):d['nhan_dien_ai']['vai_tro']='accessory_or_motor_protection';d['cau_hinh_chon']['can_chon'].append('Thiết bị chủ tương thích')
 if kind=='Interlock':d['yeu_cau_chon_day']['quy_tac']='Xác nhận liên động cơ hay điện theo mã; chỉ lập dây cho cọc thực sự có.'
 save(folder/'thong_tin_thiet_bi.json',d)
 reports.setdefault(brand,[]).append({'profile':(folder/'thong_tin_thiet_bi.json').relative_to(ROOT).as_posix(),'name':name,'views':len(entries),'sources':[s[0] for s in states],'needs_review':uncertain})
 return d,folder

def abb():
 base=BASE/'ABB_D03_DU_LIEU_MOI';rows=json.loads((base/'reviewed_states/manifest.json').read_text(encoding='utf-8'));groups={}
 for s in rows:
  sid=s['source_id'];op=s['option'];code=s['attributes'].get('TYPE');poles=None
  if '-C2-' in sid:
   kind='Contactor' if sid[-2:] in ('03','04','05','06') else 'Thermal Relay' if sid.endswith('07') else 'Aux Contact' if sid.endswith('01') else 'Interlock' if sid.endswith('02') else 'Accessory'
   if op in ('Back View','Side View') or '/side' in op:continue
   if kind=='Contactor':code=re.sub(r'AX[0-9]+', 'AX'+str(int(op.split('A:')[0])),code);poles='3P'
   if kind in ('Thermal Relay','Interlock'):code=op
  else:
   kind='SPD' if 'OVR' in (code or '') else 'RCBO' if code=='DS201L' else 'RCCB' if code=='FH202' else 'MCB' if code in ('S200','S280UC-K','SH200') else 'MCCB'
   if kind=='SPD':
    if not op.startswith('OVR'):continue
    code=op
   else:
    if 'Front' not in op:continue
    m=re.match(r'([1-4]P):',op);poles=m[1] if m else '1P+N' if kind=='RCBO' else None
    if kind=='RCCB':code='FH204' if poles=='4P' else 'FH202'
  key=re.sub('[^A-Za-z0-9]+','_',code or sid)+(('_'+poles) if poles else '')
  states=[(s['id'],'Mặt trước','Mặt trước',base/s['dxf'])]
  for v in rows:
   if v['source_id']!=sid:continue
   if kind=='Thermal Relay':include=v['option']==op+'/side'
   else:include=v['option'] in ('Side View','Back View')
   if include:states.append((v['id'],'Mặt sau' if 'Back' in v['option'] else 'Mặt bên','Mặt sau' if 'Back' in v['option'] else 'Mặt bên',base/v['dxf']))
  url='https://new.abb.com/docs/librariesprovider54/publikationer/katalog-tmax-xt.pdf?sfvrsn=ce6cc113_2' if code and code.startswith('XT') else ABBURL['FORMULA' if code in ('A1','A2','A3') else 'Motor' if '-C2-' in sid else kind]
  notes=['Nhãn dòng nguồn: '+str(s['attributes'].get('RATE'))+'; không phải dòng đã chọn.']
  if kind=='SPD':notes+=['25 kA là dòng xung theo nhãn OVR, không phải dòng tải. TS là tiếp điểm báo trạng thái; chọn hệ thống nối đất và bảo vệ dự phòng theo hãng.']
  if kind=='RCCB':notes+=['RCCB bảo vệ dòng rò; cần phối hợp bảo vệ quá dòng.']
  if code=='S280UC-K':notes+=['Dòng UC có ứng dụng AC/DC; đấu nối DC phải theo cực tính và sơ đồ hãng, không tự nối như MCB AC.']
  d,folder=profile('ABB',key,kind,code,poles,states,[url],notes,uncertain=code is None)
  if kind=='MCB' and poles:d['tu_khoa_tim_kiem'] += [code.replace('200','20'+poles[0])] if code in ('S200','SH200') else []
  save(folder/'thong_tin_thiet_bi.json',d)
 save(ROOT/'ABB/kiem_tra_abb.json',{'items':reports['ABB'],'original_blocks':29,'exported_states':len(rows),'source_coverage':sorted({s['source_id'] for s in rows}),'cover_policy':'Cover và trạng thái chỉ ghi số cực giữ trong DWG gốc; chưa nhập như mặt thiết bị.'})

def osung():
 base=BASE/'OSUNG_D05_DU_LIEU_MOI';rows=json.loads((base/'reviewed_states/manifest.json').read_text(encoding='utf-8'))
 states=[(s['id'],{'Front':'Mặt trước','Side':'Mặt bên','Top':'Mặt trên'}[s['option']],{'Front':'Mặt trước','Side':'Mặt bên','Top':'Mặt trên'}[s['option']],base/s['dxf']) for s in rows]
 profile('O-Sung','OSS_612_PC_4P','ATS','OSS-612-PC','4P',states,['https://www.osemco.co.th/index.php/product/'],['Chữ OSS-612-PC-4P có trong CAD; không gán dòng 1600/2000/2500/3200 A từ tên nhóm OSS-612.','Chọn đúng kiểu PC/PCN/TN, dòng, chu kỳ chuyển và bộ điều khiển; chưa xác nhận bản CAD khớp mã đặt hàng.'],True)
 save(ROOT/'O-Sung/kiem_tra_osung.json',{'items':reports['O-Sung'],'original_blocks':1,'exported_states':3,'source_coverage':['OSU-D05-C6-I01']})

def rmu():
 source=BASE/'04_BO_THIET_BI_DXF'
 facemap={'E01':['Mặt trên','Mặt trước'],'E02':['Mặt trên','Mặt trước'],'E03':['Mặt bên','Mặt trước','Mặt trên'],
 'E04':['Mặt bên','Mặt trước','Mặt trên'],'E05':['Mặt trước','Mặt trên','Mặt bên'],'E06':['Mặt trên','Mặt trước'],'E07':['Mặt trước','Mặt trên']}
 for zone,faces in facemap.items():
  candidates=[]
  for f in sorted((source/zone).glob('*/thong_tin.json')):
   meta=json.loads(f.read_text(encoding='utf-8'))
   for v in meta['views']:candidates.append((meta,v))
  assert len(candidates)==len(faces),(zone,len(candidates))
  label=candidates[0][0]['name'].replace('RMU-','').replace('_',' ')
  states=[(zone+'-V'+str(i+1),face,face,BASE/v['file']) for i,((meta,v),face) in enumerate(zip(candidates,faces))]
  sch=zone in ('E06','E07');urls=['https://download.schneider-electric.com/files?p_Doc_Ref=AMTED398032EN'] if sch else []
  d,folder=profile('RMU',zone,'RMU',label,None,states,urls,
  ['Đây là một cụm tủ hoàn chỉnh; các ngăn C/V không phải nhiều góc nhìn.','Nhãn cấu hình lấy từ vùng nguồn; không suy hãng hoặc dòng định mức từ nhãn vùng.','RM6 tham khảo tối đa 24 kV; không dùng tài liệu này để xác nhận bản 40,5 kV.'],True,
  {'dien_ap_nhan_nguon_kV':40.5 if zone in ('E04','E05') else 24 if zone in ('E01','E02','E03') else None,'dong_dinh_muc_A':None,'dong_ngan_mach_kA':None})
  d['nhan_dien_ai']['cad_represents']='complete_switchgear_assembly'
  if sch:d['hang_xac_nhan']='Schneider Electric (dòng RM6; cần đối chiếu cấu hình CAD)';d['nhan_dien_ai']['hang']='Schneider Electric'
  save(folder/'thong_tin_thiet_bi.json',d)
 save(ROOT/'RMU/kiem_tra_rmu.json',{'items':reports['RMU'],'zones_covered':list(facemap),'source_views':17,'unknown_brands':['E01','E02','E03','E04','E05'],'review_notes':['RMU là nhóm chức năng, không phải hãng.','Giữ một hồ sơ cho mỗi cụm; chọn mặt riêng khi chèn.']})

if __name__=='__main__':
 import sys
 if sys.argv[1]=='abb':abb()
 elif sys.argv[1]=='osung':osung()
 elif sys.argv[1]=='rmu':rmu()
 print({k:{'profiles':len(v),'views':sum(x['views'] for x in v)} for k,v in reports.items()})
