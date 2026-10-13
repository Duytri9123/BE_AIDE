"""Curate Schneider families/poles from original AutoCAD visibility states."""
import json, re, shutil
from pathlib import Path
from populate_catalogtb_chint import drawing, save, ROOT

BASE=ROOT.parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/SCHNEIDER_D01_DU_LIEU_MOI'
STATES=json.loads((BASE/'reviewed_states/manifest.json').read_text(encoding='utf-8'))
SOURCE=ROOT.parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/04_BO_THIET_BI_DXF/D01'
TARGET=ROOT/'Schneider/ThietBi'
URLS={
 'MCB':'https://ckm-content.se.com/ckmContent/sfc/servlet.shepherd/document/download/0698V00000ddL7WQAU',
 'RCCB':'https://www.se.com/sg/en/product-range/7560-acti-9-iidk-rccb/',
 'RCD':'https://www.se.com/es/es/faqs/FAQ000234157/',
 'EZCV':'https://www.se.com/ae/en/faqs/FA171316/',
 'EZC':'https://www.se.com/za/en/product-range/997-easypact-ezc/',
 'CVS':'https://www.se.com/sg/en/product-range/61052-easypact-cvs/',
 'EZS':'https://download.se.com/files?p_Doc_Ref=ENNZ5379901&p_File_Name=ENNZ5379901_00.pdf&p_enDocType=Instruction+sheet',
 'NS':'https://www.se.com/us/en/download/document/51201640AA/',
 'LC1D':'https://www.se.com/ie/en/faqs/FA23827/',
 'LC1E':'https://download.se.com/files?p_Doc_Ref=HRB44994&p_File_Name=HRB4499401.pdf&p_enDocType=Instruction+sheet',
 'LC1F':'https://iportal.se.com/Contents/docs/SQD-LC1F265G7.PDF',
}

contactors={}
meta=json.loads(next(SOURCE.glob('*cluster2*/thong_tin.json')).read_text(encoding='utf-8'))
for i,v in enumerate(meta['views'],1):
    code=v['name'].replace('SN_','').replace('SN ','')
    contactors[f'SCH-D01-C2-I{i:02}']=None if code.startswith('*') else code

groups={};audit=[]
for s in STATES:
    sid=s['source_id'];a=s['attributes'];op=s['option']
    if sid in contactors:
        code=contactors[sid];kind='Contactor';poles='1P' if code=='iCT 1P' else '3P' if code else None
    else:
        code=a.get('TYPE');assert code,(sid,a)
        code='iIDK' if code=='ilDK' else code
        kind='MCB' if code in ('C120','iC60','iK60N') else 'RCCB' if code=='iIDK' else 'RCD' if code=='A9D' else 'MCCB'
        m=re.match(r'([1-4]P):',op);poles=m[1] if m else None
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
    uncertain=code is None or kind=='RCD'
    display_code='CVS100/160/250' if code=='CVS100' else code
    name=f'{kind} Schneider {display_code or "chưa rõ mã"}'+(f' · {"CAD " if kind=="RCD" else ""}{poles}' if poles else '')
    family=next((k for k in ('LC1D','LC1E','LC1F','EZCV','EZS','EZC','CVS','NS') if code and k in code),kind)
    urls=[URLS[family]] if family in URLS else []
    aliases=[name,code or '',source['source_group'],'Schneider Electric']
    models=[code] if code else []
    if code=='CVS100':models=['CVS100','CVS160','CVS250']
    if code=='LC1D9-18':models=['LC1D09','LC1D12','LC1D18']
    if code=='LC1D25-38':models=['LC1D25','LC1D32','LC1D38']
    aliases+=models
    category_vn={'Contactor':'Khởi động từ','MCB':'Aptomat tép','MCCB':'Aptomat khối','RCCB':'Cầu dao chống rò','RCD':'Thiết bị chống rò chưa xác nhận loại'}[kind]
    aliases+=[category_vn, 'khoi dong tu' if kind=='Contactor' else 'aptomat', 'CB']
    specs={'so_cuc':None if kind=='RCD' else poles,'so_cuc_cad':poles,'nhan_dong_tren_cad':rate,
           'dong_dinh_muc_da_chon':None,'dien_ap_da_chon':None,'kha_nang_cat_da_chon':None}
    if code=='C120':specs['dong_tham_khao']='63 / 80 / 100 / 125 A; chọn N/H và đặc tính tác động theo mã'
    if code=='iC60':specs['dong_tham_khao']='0,5–63 A; chọn a/N/H/L, đường cong và khả năng cắt theo mã'
    if code=='iK60N':specs.update({'dong_tham_khao':'1–63 A; chọn B/C theo mã','kha_nang_cat_tham_khao':'Icn 6 kA theo IEC/EN 60898-1, 230/400 VAC'})
    if code=='iIDK':specs.update({'dong_tham_khao':'25 / 40 / 63 A theo các mã tham khảo','dong_ro_tham_khao':'30 / 300 mA; kiểm tra đúng mã và thị trường'})
    notes=['Nhãn dòng trên CAD là dữ liệu nguồn, không phải cấu hình điện đã chọn.',
           'Mỗi CAD là một trạng thái gốc; nắp che là phương án biểu diễn, không phải góc nhìn khác.']
    if kind=='Contactor':
        specs.update({'dien_ap_cuon_hut':None,'cap_su_dung':'Chọn AC-3/AC-1 theo tải','tiep_diem_chinh':None})
        notes+=['Chọn đủ hậu tố cuộn hút và tiếp điểm. Các mã dùng chung thân CAD vẫn có thông số khác nhau.']
        if code and code.startswith('LC1F'):notes+=['Khối nhô bên phải là một phần của contactor ở mặt trước; không cắt thành mặt bên riêng. Đối chiếu bản vẽ kích thước hãng.']
    if kind=='RCCB':
        specs['chuc_nang_bao_ve']='Dòng rò; cần phối hợp bảo vệ quá dòng';specs['dong_ro_da_chon']=None
    if kind=='RCD':
        notes+=['A9D chỉ là tiền tố mã. Tài liệu có A9D iDPN Vigi 1P+N; trạng thái CAD ghi 2P/4P chưa đủ để xác nhận số cực điện hay RCBO/RCCB. Không tự chọn cho sơ đồ.']
    if code=='EZCV250':specs['chuc_nang_bao_ve']='Quá tải, ngắn mạch và dòng rò tích hợp; chọn dòng rò theo mã.'
    if code and code.startswith('EZS'):notes+=['Giữ nhãn EZS nguồn; không đổi thành EZC/CVS dù hình học giống.']
    if code and code.startswith('NS'):notes+=['CAD có nhãn Compact NS; không tự thay bằng NSX hoặc thế hệ ComPacT mới.']
    if len(g['sources'])>1:notes+=['Hai bản nguồn cùng nhãn được giữ như hai biến thể CAD; chưa xác nhận cùng thế hệ và cấu hình gá.']
    if code=='CVS100':notes+=['Block có trạng thái bên 100/160 và bên 250. Mặt trước dùng chung theo nguồn; chọn đúng mặt bên theo cỡ khung, không dùng mặt bên 250 cho CVS100/160.']
    mounting={'vi_tri_uu_tien':'ben_trong','vi_tri_phu_hop':['ben_trong','canh_trong'] if kind!='Contactor' else ['ben_trong'],
              'huong_dan':'Thân thiết bị gá trên ray/tấm lắp. Cánh trong chỉ để lộ tay gạt qua lỗ khoét; kiểm tra đúng kiểu gá, chiều sâu và khoảng đấu dây.'}
    d={'nhom':'Schneider','ten_kieu':name,'ten_san_pham':name,'hang_xac_nhan':'Schneider Electric',
       'ma_dong_san_pham':code,'ban_chat':category_vn+' ('+kind+')','cong_dung':'Đóng cắt tải theo mạch điều khiển.' if kind=='Contactor' else 'Đóng cắt và bảo vệ mạch theo chức năng của đúng mã thiết bị.',
       'vi_tri_lap_dat':mounting['huong_dan'],'bo_tri_lap_dat':mounting,'thong_so':specs,
       'quy_cach_hien_thi':((poles+' · ') if poles else '')+('Cần xác nhận mã/loại' if uncertain else 'Chọn thông số điện'),
       'cad_don':entries,'cac_hinh_cad':[v['id_hinh_goc'] for v in entries],
       'cad_chen_tu':{'id_hinh_goc':primary['id_hinh_goc'],'huong_nhin':primary['huong_nhin'],'duong_dan':'CadChenTu/ban_ve.dxf'},
       'tu_khoa_tim_kiem':list(dict.fromkeys(aliases)), 'nguon_tham_khao':urls,'tai_lieu_hang':urls[0] if urls else None,
       'muc_do_xac_nhan':'Nhãn nguồn chưa đủ xác nhận mã/loại; không tự chọn thiết bị.' if uncertain else 'Nhận diện dòng từ block/thuộc tính nguồn; chưa chọn mã đầy đủ và thông số điện.',
       'dac_diem':notes,'lua_chon_ky_thuat':['Chọn dòng, điện áp, số cực, khả năng cắt/tiếp điểm và phụ kiện theo đúng mã.'],
       'nhan_dien_ai':{'loai_thiet_bi_code':kind,'hang':'Schneider Electric','cac_ma_dong_san_pham':models,
                       'so_cuc':specs['so_cuc'],'so_cuc_cad':poles,'pham_vi_ma':'product_family_or_source_label',
                       'tu_dong_chon_theo_vai_tro':not uncertain,'ma_dat_hang_da_chon':None,'fabrication_ready':False},
       'cau_hinh_chon':{'can_chon':['Mã đầy đủ','Dòng/điện áp','Khả năng cắt hoặc cấp sử dụng','Phụ kiện','Biến thể và mặt CAD'], 'ma_da_chon':None},
       'yeu_cau_chon_day':{'vai_tro_ket_noi':['Nguồn vào','Ra tải','Cuộn hút và tiếp điểm phụ'] if kind=='Contactor' else ['Nguồn vào','Ra tải','Phụ kiện điều khiển nếu có'],
                           'tiet_dien_mac_dinh_mm2':None,'quy_tac':'Chọn theo từng cọc và kết nối, dòng tải, bảo vệ và giới hạn đầu nối của mã đầy đủ; không suy từ CAD.'},
       'yeu_cau_lap_dat':{'schema':'installation_contract.schema.json','status':'Cần tài liệu gá/cọc theo mã đầy đủ','unknown_value':None,'cad_rotation_is_mounting_approval':False}}
    save(folder/'thong_tin_thiet_bi.json',d)
    report.append({'profile':(folder/'thong_tin_thiet_bi.json').relative_to(ROOT).as_posix(),'name':name,'sources':sorted(g['sources']),'views':len(entries),'needs_identification_review':uncertain})
save(ROOT/'Schneider/kiem_tra_schneider.json',{'profiles':len(report),'views':sum(v['views'] for v in report),'items':report,
     'original_blocks':34,'exported_states':len(STATES),'source_coverage':sorted({s for r in report for s in r['sources']}),
     'reference_only_states':[s for s in STATES if 'Cover' in s['option']],
     'reference_only_reason':'Cover có hai phần CAD rời trong một trạng thái; giữ bản gốc tham khảo, không chèn toàn bộ như một mặt thiết bị.',
     'review_notes':['A9D giữ trạng thái CAD, không suy số cực điện hoặc loại bảo vệ.','LC1F có khối nhô thật, không tự cắt thành hai mặt.','CVS400 có hai bản nguồn; giữ riêng biến thể.'],
     'text_only_source':'D01_cluster7 chỉ có nhãn Schneider, không phải thiết bị.'})
print('Schneider:',len(report),'profiles,',sum(v['views'] for v in report),'CAD states')
