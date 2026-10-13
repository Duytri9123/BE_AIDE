"""Curate Shihlin families/poles from original AutoCAD visibility states."""
import json, re, shutil
from pathlib import Path
from populate_catalogtb_chint import drawing, save, ROOT

BASE=ROOT.parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/SHIHLIN_D06_DU_LIEU_MOI'
STATES=json.loads((BASE/'reviewed_states/manifest.json').read_text(encoding='utf-8'))
SOURCE=ROOT.parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/04_BO_THIET_BI_DXF/D06'
TARGET=ROOT/'Shihlin/ThietBi'
MAPPINGS={
 'SHI-D06-C3-I01':('RCBO','BHL', ['BHL'], '4P'),
 'SHI-D06-C3-I02':('RCBO','BHL', ['BHL'], '2P'),
 'SHI-D06-C3-I03':('MCB','BHA', ['BHA'], None),
 'SHI-D06-C3-I04':('MCB',None, [], None),
 'SHI-D06-C5-I01':('MCCB','BM630/800', [f'BM{n}-{v}' for n in (630,800) for v in ('CN','SN','HN','RN','UN')], None),
 'SHI-D06-C5-I02':('MCCB','BM1600-HS',['BM1600-HS'],None),
 'SHI-D06-C5-I03':('MCCB','BM1000-HE/BM1200-HS',['BM1000-HE','BM1200-HS'],None),
 'SHI-D06-C6-I01':('MCCB','BM60-HBN/BM100-HN/BM125',['BM60-HBN','BM100-HN','BM125-SN','BM125-HN'],'3P'),
 'SHI-D06-C6-I02':('MCCB','BM30/50/60/100',['BM30-SN','BM50-CN','BM60-SN','BM60-HN','BM100-MN','BM100-SN'],None),
 'SHI-D06-C6-I03':('MCCB','BM400',[f'BM400-{v}' for v in ('CN','SN','HN','RN','UN')],None),
}
OFFICIAL='https://circuit-breaker.seec.com.tw/Templates/att/VIEW_BSE-MCCB-230612.pdf?lng=en'
URLS={'MCB':'https://global.seec.com.tw/en/product/7100.html','RCBO':'https://global.seec.com.tw/en/product/7101.html','MCCB':OFFICIAL}

groups={};audit=[]
for s in STATES:
    sid=s['source_id'];a=s['attributes'];op=s['option']
    kind,code,models,fixed_poles=MAPPINGS[sid]
    m=re.match(r'([1-4]P):',op);poles=m[1] if m else fixed_poles
    if 'Front' not in op:continue
    key=(code or sid,poles)
    group=groups.setdefault(key,{'code':code,'kind':kind,'poles':poles,'states':{},'sources':set()})
    group['states'][s['id']]=s;group['sources'].add(sid)
    for view in STATES:
        if view['source_id']!=sid or 'Front' in view['option'] or 'Cover' in view['option']:continue
        m=re.match(r'([1-4]P):',view['option'])
        if m and m[1]!=poles:continue
        group['states'][view['id']]=view

report=[]
for (identity,poles),g in groups.items():
    code=g['code'];kind=g['kind'];key=re.sub('[^A-Za-z0-9]+','_',identity)+(('_'+poles) if poles and not (kind=='Contactor' and poles=='3P') else '')
    folder=TARGET/key;entries=[]
    for s in g['states'].values():
        op=s['option'];face='Mặt bên' if 'Side' in op else 'Mặt trước'
        label='Nắp che đầu cực' if 'Cover' in op else face
        if 'Connecting' in op:label+=' · có đầu nối'
    if 'Spreader' in op:label+=' · có đầu nối mở rộng'
        if '(Fix' in op:label+=' · lắp cố định'
        if '100; 160' in op:label+=' · khung 100/160'
        if 'Side View 250' in op:label+=' · khung 250'
        if len(g['sources'])>1:label+=' · '+s['source_id'].replace('SCH-D01-','')
        view=drawing(folder,s['id'],face,label,source_path=BASE/s['dxf'])
        view['vai_tro_cad']='cover' if 'Cover' in op else 'device_view'
        view['trang_thai_nguon']=op
        entries.append(view)
    fronts=[v for v in entries if v['vai_tro_cad']=='device_view' and v['huong_nhin']=='Mặt trước']
    # CVS400 has an old C5 and a second C6 source; retain both as variants.
    primary=next((v for v in fronts if '-C6-' in v['id_hinh_goc']),fronts[0])
    dest=folder/'CadChenTu';dest.mkdir(exist_ok=True)
    for f in ('ban_ve.dxf','xem_truoc.svg','thong_tin_cad_chen.json'):shutil.copy2(folder/'CadDon'/primary['id_hinh_goc']/f,dest/f)
    source=next(iter(g['states'].values()));rate=source['attributes'].get('RATE')
    uncertain=code is None
    display_code='CVS100/160/250' if code=='CVS100' else code
    name=f'{kind} Shihlin {display_code or "chưa rõ mã"}'+(f' · {"CAD " if kind=="RCD" else ""}{poles}' if poles else '')
    family=next((k for k in ('LC1D','LC1E','LC1F','EZCV','EZS','EZC','CVS','NS') if code and k in code),kind)
    urls=[URLS[kind]]
    aliases=[name,code or '',source['source_group'],'Shihlin Electric']
    models=MAPPINGS[source['source_id']][2]
    if code=='CVS100':models=['CVS100','CVS160','CVS250']
    if code=='LC1D9-18':models=['LC1D09','LC1D12','LC1D18']
    if code=='LC1D25-38':models=['LC1D25','LC1D32','LC1D38']
    aliases+=models
    category_vn={'RCBO':'Aptomat chống rò và quá dòng','Contactor':'Khởi động từ','MCB':'Aptomat tép','MCCB':'Aptomat khối','RCCB':'Cầu dao chống rò','RCD':'Thiết bị chống rò chưa xác nhận loại'}[kind]
    aliases+=[category_vn, 'khoi dong tu' if kind=='Contactor' else 'aptomat', 'CB']
    specs={'so_cuc':None if kind=='RCD' else poles,'so_cuc_cad':poles,'nhan_dong_tren_cad':rate,
           'dong_dinh_muc_da_chon':None,'dien_ap_da_chon':None,'kha_nang_cat_da_chon':None}
    if code=='C120':specs['dong_tham_khao']='63 / 80 / 100 / 125 A; chọn N/H và đặc tính tác động theo mã'
    if code=='iC60':specs['dong_tham_khao']='0,5–63 A; chọn a/N/H/L, đường cong và khả năng cắt theo mã'
    if code=='iK60N':specs.update({'dong_tham_khao':'1–63 A; chọn B/C theo mã','kha_nang_cat_tham_khao':'Icn 6 kA theo IEC/EN 60898-1, 230/400 VAC'})
    if code=='iIDK':specs.update({'dong_tham_khao':'25 / 40 / 63 A theo các mã tham khảo','dong_ro_tham_khao':'30 / 300 mA; kiểm tra đúng mã và thị trường'})
    notes=['Mã dùng chung thân CAD có thể khác dòng, khả năng cắt và phụ kiện; chọn mã đầy đủ trước khi lắp.',
           'Thuộc tính ORIGIN=LS trong nguồn là nhãn sao chép mâu thuẫn với thư mục và chữ Shihlin trên CAD; không dùng để xác nhận hãng.',
           'Giữ nguyên kích thước CAD gốc; chưa xác nhận mọi mã trong nhóm dùng được mọi số cực CAD.']
    specs['so_cuc']=poles
    if kind=='RCBO':
        specs.update({'dong_tham_khao':'1–63 A theo dòng BHL','dong_ro_tham_khao':'30 mA','kha_nang_cat_tham_khao':'4,5 / 6 kA; đối chiếu mã','chuc_nang_bao_ve':'Quá dòng và dòng rò','dong_ro_da_chon':None})
    if kind=='MCB':
        specs['kha_nang_cat_nhan_cad']=source['attributes'].get('TYPE')
        notes.append('Không suy mã BHA125 từ nhãn D100/10 kA. Bản 6 kA chưa có mã dòng rõ trên CAD.')
    if code=='BM630/800':notes.append('CAD ghi BM630-800; nhãn 800A không áp cho BM630. Chọn đúng khung 630 hoặc 800 và hậu tố.')
    specs['cac_ma_dung_chung_cad']=models
    mounting={'vi_tri_uu_tien':'ben_trong','vi_tri_phu_hop':['ben_trong','canh_trong'] if kind!='Contactor' else ['ben_trong'],
              'huong_dan':'Thân thiết bị gá trên ray/tấm lắp. Cánh trong chỉ để lộ tay gạt qua lỗ khoét; kiểm tra đúng kiểu gá, chiều sâu và khoảng đấu dây.'}
    d={'nhom':'Shihlin','ten_kieu':name,'ten_san_pham':name,'hang_xac_nhan':'Shihlin Electric',
       'ma_dong_san_pham':code,'ban_chat':category_vn+' ('+kind+')','cong_dung':'Đóng cắt tải theo mạch điều khiển.' if kind=='Contactor' else 'Đóng cắt và bảo vệ mạch theo chức năng của đúng mã thiết bị.',
       'vi_tri_lap_dat':mounting['huong_dan'],'bo_tri_lap_dat':mounting,'thong_so':specs,
       'quy_cach_hien_thi':((poles+' · ') if poles else '')+('Cần xác nhận mã/loại' if uncertain else 'Chọn thông số điện'),
       'cad_don':entries,'cac_hinh_cad':[v['id_hinh_goc'] for v in entries],
       'cad_chen_tu':{'id_hinh_goc':primary['id_hinh_goc'],'huong_nhin':primary['huong_nhin'],'duong_dan':'CadChenTu/ban_ve.dxf'},
       'tu_khoa_tim_kiem':list(dict.fromkeys(aliases)), 'nguon_tham_khao':urls,'tai_lieu_hang':urls[0] if urls else None,
       'muc_do_xac_nhan':'Nhãn nguồn chưa đủ xác nhận mã/loại; không tự chọn thiết bị.' if uncertain else 'Nhận diện dòng từ block/thuộc tính nguồn; chưa chọn mã đầy đủ và thông số điện.',
       'dac_diem':notes,'lua_chon_ky_thuat':['Chọn dòng, điện áp, số cực, khả năng cắt/tiếp điểm và phụ kiện theo đúng mã.'],
       'nhan_dien_ai':{'loai_thiet_bi_code':kind,'hang':'Shihlin Electric','cac_ma_dong_san_pham':models,
                       'so_cuc':specs['so_cuc'],'so_cuc_cad':poles,'pham_vi_ma':'product_family_or_source_label',
                       'tu_dong_chon_theo_vai_tro':not uncertain,'ma_dat_hang_da_chon':None,'fabrication_ready':False},
       'cau_hinh_chon':{'can_chon':['Mã đầy đủ','Dòng/điện áp','Khả năng cắt hoặc cấp sử dụng','Phụ kiện','Biến thể và mặt CAD'], 'ma_da_chon':None},
       'yeu_cau_chon_day':{'vai_tro_ket_noi':['Nguồn vào','Ra tải','Cuộn hút và tiếp điểm phụ'] if kind=='Contactor' else ['Nguồn vào','Ra tải','Phụ kiện điều khiển nếu có'],
                           'tiet_dien_mac_dinh_mm2':None,'quy_tac':'Chọn theo từng cọc và kết nối, dòng tải, bảo vệ và giới hạn đầu nối của mã đầy đủ; không suy từ CAD.'},
       'yeu_cau_lap_dat':{'schema':'installation_contract.schema.json','status':'Cần tài liệu gá/cọc theo mã đầy đủ','unknown_value':None,'cad_rotation_is_mounting_approval':False}}
    if code=='BHL':
        d['thong_so']['so_cuc']=None;d['nhan_dien_ai']['so_cuc']=None
        d['nhan_dien_ai']['tu_dong_chon_theo_vai_tro']=False
        d['ten_kieu']=d['ten_san_pham']=name.replace(' · ',' · CAD ')
        d['quy_cach_hien_thi']='Cần xác nhận số cực điện và mã BHL'
        d['dac_diem'].append('Tên block BHL 2P/4P và chữ BHL33 chưa thống nhất; số cực tên CAD chưa xác nhận số cực điện.')
        name=d['ten_kieu'];uncertain=True
    save(folder/'thong_tin_thiet_bi.json',d)
    report.append({'profile':(folder/'thong_tin_thiet_bi.json').relative_to(ROOT).as_posix(),'name':name,'sources':sorted(g['sources']),'views':len(entries),'needs_identification_review':uncertain})
save(ROOT/'Shihlin/kiem_tra_shihlin.json',{'profiles':len(report),'views':sum(v['views'] for v in report),'items':report,
 'original_blocks':10,'exported_states':len(STATES),'source_coverage':sorted({s for r in report for s in r['sources']}),
 'reference_only_states':[s for s in STATES if 'Cover' in s['option']],
 'review_notes':['Nhận diện từ TEXT trong CAD; ORIGIN=LS là xung đột nhãn nguồn.','Không gán 800A cho BM630; nhóm CAD chứa BM630 và BM800.','Cluster2 chỉ có khung và tiêu đề MC+OVR, chưa có CAD contactor có thể chọn.','BHL chỉ có mặt trước trong nguồn; không dựng mặt bên.','Mã nhóm và số cực CAD chưa phải mã đặt hàng đã xác nhận.']})
print('Shihlin:',len(report),'profiles,',sum(v['views'] for v in report),'CAD states')
