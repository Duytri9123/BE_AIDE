"""Build an offline, source-linked browser for data/CatalogTB."""
from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path
from urllib.parse import quote
from normalize_catalogtb_search_names import normalize

ROOT = Path(__file__).resolve().parents[1] / 'data' / 'CatalogTB'
if '--skip-normalize' not in sys.argv:
    normalize()


def url(path: Path) -> str:
    return quote(path.relative_to(ROOT).as_posix(), safe='/')


def projection_metadata(directory, entry):
    data=json.loads((directory/'thong_tin_cad_chen.json').read_text(encoding='utf8'))
    data.setdefault('id_hinh_goc',entry['id_hinh_goc'])
    data.setdefault('huong_nhin',entry.get('huong_nhin'))
    data.setdefault('tep',{'cad_dxf':Path(entry['duong_dan']).name,'preview':'xem_truoc.svg'})
    for key in ['cad_dxf','preview']:
        if not (directory/data['tep'][key]).is_file():raise ValueError('Missing projection asset: '+str(directory))
    return data


categories = []
for folder in sorted((p for p in ROOT.iterdir() if p.is_dir()), key=lambda p: p.name.casefold()):
    categories.append({
        'name': folder.name,
        'records': len(list(folder.rglob('thong_tin.json'))),
        'profiles': len(list(folder.rglob('thong_tin_thiet_bi.json'))),
    })

for category in categories:
    if category['name']=='Form tủ':
        catalog=json.loads((ROOT/'Form tủ/catalog.json').read_text(encoding='utf-8'))
        category.update(records=len(catalog['shells']),profiles=len(catalog['shells']),link='Form%20t%E1%BB%A7/index.html',count_label=str(len(catalog['shells']))+' mẫu vỏ')

profiles = []
PROFILE_CATEGORIES = ('BienDong', 'ThietBiDoLuongHienThi', 'DenBaoNutNhanCauChiContactor', 'Bộ điều khiển', 'Cầu đấu', 'Quạt', 'Cuộn kháng', 'Phụ kiện tủ điện', 'Phíp', 'Tụ bù', 'Ổ cắm', 'Khóa', 'LS', 'Mitsubishi', 'Chint', 'Schneider', 'Shihlin', 'ABB', 'O-Sung', 'RMU', 'Đồng', 'Đố', 'Biến tần', 'Nguồn và biến áp', 'Chống sét')
for profile_path in sorted(ROOT.rglob('thong_tin_thiet_bi.json')):
    profile = json.loads(profile_path.read_text(encoding='utf-8'))
    folder = profile_path.parent
    drawings = []
    for record_path in sorted(folder.rglob('thong_tin.json')):
        record = json.loads(record_path.read_text(encoding='utf-8'))
        drawings.append({
            'id': record['id'],
            'name': record['ten_hinh'],
            'kind': record['loai_hinh'],
            'size': record.get('kich_thuoc_hinh_mm'),
            'assembly': record.get('cau_hinh_lap_ghep'),
            'preview': url(record_path.parent / record['tep']['preview']) if record['tep'].get('preview') else None,
            'dxf': url(record_path.parent / record['tep']['cad_dxf']),
            'json': url(record_path),
        })
    insert_dir = folder / 'CadChenTu'
    selected=(profile.get('cad_chen_tu') or {}).get('id_hinh_goc')
    entry=next((v for v in profile['cad_don'] if v['id_hinh_goc']==selected),None)
    if entry is None:raise ValueError('No explicitly declared primary CAD: '+str(profile_path))
    if not (insert_dir/'thong_tin_cad_chen.json').is_file():
        insert_dir=(folder/entry['duong_dan']).parent
    insert = projection_metadata(insert_dir,entry)
    # Some officially supplemented assets have CadDon without HinhChieu records.
    for view in profile['cad_don']:
        if view['id_hinh_goc'] in {drawing['id'] for drawing in drawings}:continue
        cad_dir=(folder/view['duong_dan']).parent
        metadata=projection_metadata(cad_dir,view)
        drawings.append({'id':view['id_hinh_goc'],'name':view.get('nhan_hien_thi') or view['huong_nhin'],
            'kind':'declared_projection','size':None,'assembly':None,
            'preview':url(cad_dir/metadata['tep']['preview']),
            'dxf':url(cad_dir/metadata['tep']['cad_dxf']),
            'json':url(cad_dir/'thong_tin_cad_chen.json')})
    assert insert['id_hinh_goc'] in {drawing['id'] for drawing in drawings}
    single_views = []
    unique_previews = {}
    by_id = {drawing['id']: drawing for drawing in drawings}
    for view in profile['cad_don']:
        cad_dir = folder / 'CadDon' / view['id_hinh_goc']
        metadata = projection_metadata(cad_dir,view)
        assert metadata['id_hinh_goc'] == view['id_hinh_goc']
        fingerprint = hashlib.sha256((cad_dir / metadata['tep']['preview']).read_bytes()).digest()
        # Equal previews do not prove equal CAD, orientation or insertion anchor.
        # Preserve every separately identified source view for agent/FE discovery.
        duplicate_preview_of = unique_previews.get(fingerprint)
        unique_previews[fingerprint] = view['id_hinh_goc']
        single_views.append({
            'source_id': view['id_hinh_goc'],
            'duplicate_preview_of': duplicate_preview_of,
            'name': by_id[view['id_hinh_goc']]['name'],
            'face': metadata['huong_nhin'],
            'label': view.get('nhan_hien_thi') or metadata.get('nhan_hien_thi') or metadata['huong_nhin'],
            'placement': metadata.get('bo_tri_trong_tu', {}),
            'dxf': url(cad_dir / metadata['tep']['cad_dxf']),
            'preview': url(cad_dir / metadata['tep']['preview']),
            'json': url(cad_dir / 'thong_tin_cad_chen.json'),
        })
    profiles.append({
        'mounting': profile.get('bo_tri_lap_dat', {}),
        'spec_hint': profile.get('quy_cach_hien_thi', ''),
        'search_aliases': profile.get('tu_khoa_tim_kiem', []),
        'lamp_options': profile.get('cau_hinh_den_tham_khao', []),
        'category': profile_path.relative_to(ROOT).parts[0],
        'name': profile['ten_kieu'],
        'display': profile.get('ten_san_pham', profile['ten_kieu']),
        'brand': profile.get('hang_xac_nhan'),
        'folder': folder.parent.name,
        'type': profile.get('ban_chat') or (profile.get('nhan_dien_ai') or {}).get('loai_thiet_bi_code'),
        'product_code': profile.get('ma_dong_san_pham'),
        'match_status': profile.get('muc_do_xac_nhan'),
        'use': profile.get('cong_dung'),
        'placement': profile.get('vi_tri_lap_dat'),
        'spec': profile.get('thong_so') or {},
        'spec_note': profile.get('luu_y_thong_so'),
        'measurement_spec_note': profile.get('ghi_chu_thong_so'),
        'features': profile.get('dac_diem', []),
        'size': profile.get('kich_thuoc_hinh_mm'),
        'manufacturer_config': profile.get('cau_hinh_dong_san_pham'),
        'selection': profile.get('lua_chon_ky_thuat', []),
        'selection_status': profile.get('trang_thai_lua_chon'),
        'sources': profile.get('nguon_tham_khao', []),
        'manufacturer_document': profile.get('tai_lieu_hang'),
        'alternatives': profile.get('phuong_an_cung_loai', []),
        'compatibility_note': profile.get('luu_y_tuong_thich'),
        'json': url(profile_path),
        'primary': {'source_id': insert['id_hinh_goc'],
                    'face': insert['huong_nhin'],
                    'dxf': url(insert_dir / insert['tep']['cad_dxf']),
                    'preview': url(insert_dir / insert['tep']['preview']),
                    'json': url(insert_dir / 'thong_tin_cad_chen.json')},
        'single_views': single_views,
        'drawings': drawings,
    })

data = {'categories': categories, 'profiles': profiles,
        'dwg': url(ROOT / 'THƯ VIỆN PHỤ KIỆN( Mới nhất).dwg')}
assert len([p for p in profiles if p['category']=='BienDong']) == 43
assert len([p for p in profiles if p['category']=='ThietBiDoLuongHienThi']) >= 21
assert len([p for p in profiles if p['category']=='DenBaoNutNhanCauChiContactor']) == 20
assert len([p for p in profiles if p['category']=='Bộ điều khiển']) == 19
assert len([p for p in profiles if p['category']=='Cầu đấu']) == 37
assert len([p for p in profiles if p['category']=='Quạt']) >= 9
assert len([p for p in profiles if p['category']=='Cuộn kháng']) == 1
assert len([p for p in profiles if p['category']=='Phụ kiện tủ điện']) >= 55
assert len([p for p in profiles if p['category']=='Phíp']) == 13
assert len([p for p in profiles if p['category']=='Tụ bù']) == 29
assert len([p for p in profiles if p['category']=='Ổ cắm']) == 7
assert len([p for p in profiles if p['category']=='Khóa']) == 17
assert len([p for p in profiles if p['category']=='LS']) >= 29
assert sum(len(p['drawings']) for p in profiles if p['category'] not in ('LS', 'Mitsubishi')) >= 447
assert all(p['primary']['dxf'] and p['primary']['preview'] for p in profiles)
assert all(1 <= len(p['single_views']) <= len(p['drawings']) for p in profiles)
assert len(profiles)==len(list(ROOT.rglob('thong_tin_thiet_bi.json')))
embedded = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')

html = r'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CatalogTB · Thư viện bản vẽ thiết bị</title>
<style>
:root{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:#142338;background:#eef3f8}
*{box-sizing:border-box}body{margin:0}button,input{font:inherit}button{cursor:pointer}[hidden]{display:none!important}
a{color:#075ab5;text-decoration:none}a:hover{text-decoration:underline}
.hero{background:linear-gradient(115deg,#112e4d,#176388);color:white;padding:30px clamp(16px,4vw,56px)}
.hero small{font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:#9edeee}
.hero h1{margin:8px 0 6px;font-size:clamp(26px,3vw,38px)}.hero p{margin:0;color:#d6e9f2}
.hero-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}.hero-actions a{color:white;border:1px solid #8bb8ca;border-radius:8px;padding:9px 13px}
.stats{display:flex;gap:10px;flex-wrap:wrap;margin-top:17px}.stats span{background:#ffffff1f;border:1px solid #ffffff38;border-radius:8px;padding:7px 10px;font-size:13px}
.layout{display:grid;grid-template-columns:250px minmax(280px,400px) minmax(360px,1fr);gap:14px;max-width:1700px;margin:16px auto;padding:0 16px}
.panel{background:white;border:1px solid #d8e3ee;border-radius:13px;min-width:0;overflow:hidden}
.panel-head{padding:16px;border-bottom:1px solid #e4ebf2}.panel-head h2{margin:0;font-size:17px}.panel-head p{margin:5px 0 0;color:#60758a;font-size:12px}
.category-list,.profile-list{max-height:calc(100vh - 260px);overflow:auto;padding:8px}
.category,.profile{display:block;width:100%;text-align:left;border:0;background:transparent;border-radius:9px;padding:11px;color:inherit}
.category:hover,.profile:hover{background:#eef6fc}.category.active,.profile.active{background:#e5f3ff;outline:1px solid #9acaf0}
.category{display:flex;justify-content:space-between;gap:8px}.category span:last-child{font-size:11px;color:#507b9c;white-space:nowrap}
.profile{border-bottom:1px solid #edf1f5}.profile strong{display:block;font-size:14px}.profile small{display:block;color:#687c91;margin-top:4px}
.search{width:100%;margin-top:12px;padding:9px 11px;border:1px solid #cbd9e7;border-radius:8px}
.detail{padding:18px;max-height:calc(100vh - 228px);overflow:auto}.detail h2{margin:0 0 7px;font-size:24px}.muted{color:#647990}
.chips{display:flex;gap:7px;flex-wrap:wrap;margin:10px 0 18px}.chip{background:#eaf3fa;color:#18547d;border-radius:100px;padding:5px 9px;font-size:12px}
.section{border-top:1px solid #e5ebf1;padding-top:14px;margin-top:18px}.section h3{margin:0 0 9px;font-size:16px}
.specs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.spec{background:#f5f8fb;padding:9px;border-radius:8px}.spec small{display:block;color:#677c90}.spec strong{font-size:13px}
.note{background:#fff8e7;border-left:3px solid #e7a832;padding:10px 12px;border-radius:6px;color:#705424;font-size:13px}
.selection-wrap{overflow:auto}.selection{width:100%;border-collapse:collapse;font-size:13px}.selection th,.selection td{padding:9px 10px;border-bottom:1px solid #e4ebf2;text-align:left;white-space:nowrap}.selection th{background:#f3f7fb;color:#38556e}.selection td{vertical-align:top}
.drawings{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px}.drawing{border:1px solid #dce6ef;border-radius:9px;overflow:hidden}.drawing.main-view{border:2px solid #16845d}.section summary{cursor:pointer;font-weight:700;margin:0 0 12px}.main-badge{display:inline-block;background:#def7eb;color:#075b3c;border-radius:5px;padding:4px 7px;margin-bottom:7px;font-weight:700}.main-action{border:1px solid #98b8ce;background:#fff;color:#075ab5;border-radius:6px;padding:6px 8px;margin-top:9px}.main-action:disabled{border-color:#b9d8c8;color:#075b3c;background:#ecfaf2;cursor:default}
.drawing .image{height:240px;background:#edf3f8;display:flex;align-items:center;justify-content:center}.drawing img{width:100%;height:100%;object-fit:contain;padding:8px;cursor:zoom-in}.drawing .body{padding:10px;font-size:12px}.drawing strong{display:block;overflow-wrap:anywhere}.drawing .links{display:flex;gap:9px;margin-top:8px}
.empty{padding:30px 15px;color:#698097;text-align:center}.footer{padding:12px 16px;color:#708298;font-size:12px;text-align:center}
@media(max-width:1050px){.layout{grid-template-columns:220px minmax(280px,1fr)}.detail-panel{grid-column:1/-1}.category-list,.profile-list,.detail{max-height:none}}
@media(max-width:650px){.layout{display:block}.panel{margin-bottom:12px}.category-list{max-height:200px}.profile-list{max-height:330px}.specs{grid-template-columns:1fr}}
</style>
</head>
<body>
<header class="hero"><small>CatalogTB</small><h1>Thư viện thiết bị</h1>
<p>Tra cứu loại thiết bị, kích thước và các hình chiếu.</p>
<div class="hero-actions"><a id="dwg-link" download>Tải bản vẽ DWG</a></div><div class="stats" id="stats"></div></header>
<main class="layout">
<aside class="panel"><div class="panel-head"><h2>Nhóm thư mục</h2><p>Chọn nhóm để xem dữ liệu hiện có</p></div><div class="category-list" id="categories"></div></aside>
<section class="panel"><div class="panel-head"><h2 id="list-title">Hồ sơ thiết bị</h2><input id="search" class="search" type="search" placeholder="Tìm hãng, kiểu, vùng CAD…" aria-label="Tìm thiết bị"></div><div class="profile-list" id="profiles"></div></section>
<section class="panel detail-panel"><div class="detail" id="detail"></div></section>
</main><footer class="footer">Các kích thước được thể hiện theo từng hình chiếu. Tỷ số dòng và cấp chính xác chỉ hiển thị khi đã xác định.</footer>
<script id="catalog-data" type="application/json">__CATALOG_DATA__</script>
<script>
const data=JSON.parse(document.getElementById('catalog-data').textContent);
const $=id=>document.getElementById(id);
const state={category:'BienDong',selected:data.profiles.find(p=>p.name==='EM4H03')?.json||''};
const mainSelections=new Map();
function mainKey(item){return 'catalogtb.main.'+item.json}
function getMainView(item){let id=mainSelections.get(item.json);if(!id){try{id=localStorage.getItem(mainKey(item))}catch(_){}}return item.single_views.find(v=>v.source_id===id)||item.single_views.find(v=>v.source_id===item.primary.source_id)||item.single_views[0]}
function setMainView(item,view){mainSelections.set(item.json,view.source_id);try{localStorage.setItem(mainKey(item),view.source_id)}catch(_){}}
const node=(tag,cls,text)=>{const el=document.createElement(tag);if(cls)el.className=cls;if(text!=null)el.textContent=text;return el};
const link=(label,href,download=false)=>{const a=node('a','',label);a.href=href;if(download)a.download='';return a};
const add=(parent,...children)=>children.forEach(c=>parent.append(c));
const value=v=>v===null||v===undefined||v===''?'Chưa xác minh':String(v);
function renderCategories(){const host=$('categories');host.replaceChildren();for(const item of data.categories){const button=node('button','category'+(state.category===item.name?' active':''));add(button,node('span','',item.name==='ThietBiDoLuongHienThi'?'Thiết bị đo lường hiển thị':item.name==='DenBaoNutNhanCauChiContactor'?'Đèn báo · Nút nhấn · Cầu chì · Contactor':item.name),node('span','',item.count_label||(item.records?item.profiles+' hồ sơ':'Trống')));button.onclick=()=>{if(item.link){location.href=item.link;return}state.category=item.name;state.selected='';renderCategories();renderProfiles()};host.append(button)}}
function selectedKey(item){return item.json}
function searchKey(s){return String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').replace(/[^a-z0-9]/g,'')}
function filtered(){const terms=$('search').value.trim().split(/\s+/).map(searchKey).filter(Boolean);return data.profiles.filter(p=>p.category===state.category&&terms.every(t=>searchKey([p.name,p.display,p.brand,p.folder,p.type,p.product_code,...(p.search_aliases||[])].join(' ')).includes(t)))}
function renderProfiles(){const host=$('profiles');host.replaceChildren();const found=filtered();$('list-title').textContent=(state.category==='BienDong'?'Biến dòng':state.category==='ThietBiDoLuongHienThi'?'Thiết bị đo lường hiển thị':state.category==='DenBaoNutNhanCauChiContactor'?'Đèn báo · Nút nhấn · Cầu chì · Contactor':state.category)+' · '+found.length+' loại/cỡ';if(!found.length){host.append(node('p','empty','Không có hồ sơ thiết bị phù hợp.'));$('detail').replaceChildren(node('p','empty','Chọn một thiết bị để xem thông tin.'));return}if(!found.some(p=>selectedKey(p)===state.selected))state.selected=selectedKey(found[0]);for(const item of found){const button=node('button','profile'+(selectedKey(item)===state.selected?' active':''));add(button,node('strong','',item.display),node('small','',item.spec_hint||item.brand||item.type),node('small','',item.single_views.length+' bản CAD'));button.onclick=()=>{state.selected=selectedKey(item);renderProfiles()};host.append(button)}renderDetail(found.find(p=>selectedKey(p)===state.selected))}
function section(title){const el=node('section','section');el.append(node('h3','',title));return el}
const extraLabels={cap_su_dung:'Cấp sử dụng',tieu_chuan:'Tiêu chuẩn',kieu_nan:'Kiểu nan',dung_luong_goi_y_kvar:'Dung lượng gợi ý (kvar)',dong_dien_goi_y_A:'Dòng điện tính gần đúng (A)',dac_tinh_tac_dong:'Đặc tính tác động',dong_ro_tac_dong:'Dòng rò tác động',chuc_nang_bao_ve:'Chức năng bảo vệ',dai_dong_cua_dong_san_pham:'Dải dòng của dòng sản phẩm',be_rong_moi_de_mm:"Bề rộng mỗi đế (mm)",cap_cat_N_H_L:"Cấp khả năng cắt N/H/L",chuc_nang_tiep_diem:"Chức năng tiếp điểm",co_day_chay:"Cỡ dây chảy",co_khung:"Cỡ khung",co_phu_kien_chan_hai_ben:"Phụ kiện chặn hai bên",cong_suat_VA:"Công suất (VA)",dau_do:"Đầu đo",dien_ap_cuon_hut:"Điện áp cuộn hút",dien_ap_den:"Điện áp đèn",dong_ac3_cua_bien_the:"Dòng AC-3 của biến thể",dong_chinh_dinh:"Dòng chỉnh định",dong_dinh_muc:"Dòng định mức",dong_dinh_muc_de:"Dòng định mức đế",dong_so_cap_dinh_muc_A:"Dòng sơ cấp định mức (A)",dong_thu_cap_dinh_muc_A:"Dòng thứ cấp định mức (A)",ghi_chu:"Ghi chú",kha_nang_cat:"Khả năng cắt",kieu_hien_thi:"Kiểu hiển thị",lo_lap_cua_dong_ung_vien_mm:"Lỗ lắp của dòng ứng viên (mm)",mau_den:"Màu đèn",nhan_nhin_thay_tren_hinh:"Nhãn hiển thị",so_cuc_moi_de:"Số cực mỗi đế",so_de_trong_hinh:"Số đế",so_tiep_diem:"Số tiếp điểm",so_vi_tri_ky_hieu:"Số vị trí",thang_hien_thi:"Thang hiển thị",ty_so:"Tỷ số biến dòng",vi_tri_chan_PE:"Vị trí chân tiếp địa PE",nhan_tren_hinh:'Nhãn trên hình',so_hinh_cung_nhan:'Số hình cùng nhãn',kich_thuoc_hinh_dai_dien_mm:'Kích thước hình đại diện (mm)',so_ban_ve_6x42_5_mm:'Hình 6 × 42,5 mm',so_hinh_phong_120_phan_tram:'Hình phóng 120%',so_cuc_theo_nhan_hinh:'Số cực theo nhãn',dong_A_theo_nhan_hinh:'Trị số A theo nhãn',tham_khao_UK3N_TOSUN:'UK3N TOSUN tương tự',tham_khao_Hanyoung_Nux:'HYT Hanyoung NUX tương tự',dien_ap_VAC:'Điện áp (VAC)',luu_luong_tu_do_m3_h:'Lưu lượng tự do (m³/h)',luu_luong_voi_mot_tam_loc_m3_h:'Lưu lượng với một tấm lọc (m³/h)',dong_co:'Động cơ',so_pha_theo_hinh:'Số pha theo hình',tam_loc_cung_co_tham_khao:'Tấm lọc cùng cỡ tham khảo',ma_tren_ban_ve:'Mã trên bản vẽ',co_ren_theo_nhan:'Cỡ ren',ky_hieu_tren_hinh:'Ký hiệu trên hình',kich_thuoc_chi_tiet_mm:'Kích thước chi tiết (mm)',nhan_tren_ban_ve:'Nhãn trên bản vẽ',hang_theo_nhan_ban_ve:'Hãng ghi trên bản vẽ',kieu_theo_nhan_ban_ve:'Kiểu ghi trên bản vẽ',dien_ap_theo_nhan_ban_ve_V:'Điện áp ghi trên bản vẽ (V)',kich_thuoc_hinh_chieu_mm:'Cỡ hình chiếu (mm)',so_lo_tron_tren_cad:'Số lỗ tròn trên hình CAD',nhom_lo_theo_duong_kinh_mm:'Số lỗ theo đường kính'};
function renderDetail(item){const host=$('detail');host.replaceChildren();if(!item)return;host.append(node('h2','',item.display));if(item.spec_hint)host.append(node('p','muted',item.spec_hint));host.append(node('p','muted',item.type));const chips=node('div','chips');for(const text of [item.brand||'Theo loại thiết bị',item.product_code?'Dòng '+item.product_code:'Chưa xác định mã sản phẩm',item.single_views.length+' mặt CAD'])chips.append(node('span','chip',text));host.append(chips);if(item.mounting?.vi_tri_uu_tien){const labels={canh_ngoai:'Cánh ngoài',canh_trong:'Cánh trong',ben_trong:'Bên trong tủ',vach_tu:'Vách tủ',khung_vo:'Khung / vỏ tủ',mat_sau_canh:'Mặt sau cánh'};const mount=section('Vị trí lắp phù hợp');mount.append(node('p','','Ưu tiên: '+labels[item.mounting.vi_tri_uu_tien]));mount.append(node('p','','Có thể bố trí: '+item.mounting.vi_tri_phu_hop.map(k=>labels[k]).join(' · ')));mount.append(node('p','',item.mounting.huong_dan));host.append(mount)}if(item.lamp_options?.length){const part=section('Chọn màu và điện áp đèn');const table=node('table');table.style.width='100%';const head=node('tr');for(const text of ['Hãng','Màu','Điện áp','Mã tham khảo'])head.append(node('th','',text));table.append(head);for(const option of item.lamp_options){const row=node('tr');for(const text of [option.hang,option.mau,option.dien_ap,option.ma])row.append(node('td','',text));table.append(row)}part.append(table,node('p','muted','Mã sản phẩm thực tế để lựa chọn; chưa xác nhận khớp CAD hiện có.'));host.append(part)}if(item.match_status)host.append(node('p','note',item.match_status));if(item.manufacturer_document){const source=link('Xem catalog của hãng',item.manufacturer_document);source.target='_blank';source.rel='noopener noreferrer';host.append(source)}
const intro=section('Thông tin thiết bị');intro.append(node('p','',item.use),node('p','',item.placement));if(item.features?.length){const list=node('ul');for(const fact of item.features)list.append(node('li','',fact));intro.append(list)}host.append(intro);
if(item.alternatives?.length){const choices=section('Hãng và dòng cùng chức năng');const list=node('ul');for(const alt of item.alternatives)list.append(node('li','',alt.hang+' · '+alt.dong));choices.append(list);if(item.compatibility_note)choices.append(node('p','note',item.compatibility_note));host.append(choices)}
if(item.category!=='BienDong'){const specs=section('Thông số và lựa chọn');const grid=node('div','specs');const labels={so_pha:'Số pha',so_day:'Số dây',dien_nang:'Điện năng',mat_truoc_mm:'Mặt trước',truyen_thong:'Truyền thông',ngo_vao_dong_A:'Ngõ dòng',trang_thai:'Trạng thái',dien_ap_dinh_muc_V:'Điện áp định mức (V)',tan_so_Hz:'Tần số (Hz)',dong_dinh_muc_A:'Dòng định mức (A)',cap_chinh_xac:'Cấp chính xác',so_day_tuy_chon:'Số dây',dien_ap_3p4d_V:'Điện áp 3P4D (V)',dien_ap_3p3d_V:'Điện áp 3P3D (V)',dai_do:'Đại lượng / dải đo',do_sau_lap_dat_mm:'Độ sâu lắp đặt (mm)',dien_ap_dinh_muc:'Điện áp danh định',so_cuc_chinh:'Số cực chính',so_cuc:'Số cực',kich_thuoc_mat_truoc_mm:'Kích thước mặt trước (mm)',kich_thuoc_hinh_mm:'Kích thước hình (mm)',kieu_tac_dong:'Kiểu tác động',mau_hien_thi:'Màu hiển thị',nhom_khung:'Nhóm vỏ',dong_ac3_380_440V_A:'Dòng AC-3 tại 380–440 V (A)',kich_thuoc_ung_vien_mm:'Kích thước nhóm mã (mm)',ma_ung_vien:'Mã ứng viên',lo_lap_ung_vien_mm:'Lỗ lắp ứng viên (mm)',chieu_dai_ung_vien_mm:'Chiều dài ứng viên (mm)',ky_hieu_tren_hinh:'Ký hiệu trên hình',so_cap_theo_nhan_hinh:'Số cấp theo nhãn hình',dong_ung_vien:'Dòng ứng viên'};for(const [key,v] of Object.entries(item.spec||{})){if(v==null||v==='')continue;const box=node('div','spec');add(box,node('small','',labels[key]||extraLabels[key]||'Thông số bổ sung'),node('strong','',v));grid.append(box)}if(grid.childElementCount)specs.append(grid);if(item.measurement_spec_note)specs.append(node('p','note',item.measurement_spec_note));if(item.selection?.length){const list=node('ul');for(const fact of item.selection)list.append(node('li','',fact));specs.append(list)}host.append(specs);}else{const specs=section('Thông số');const grid=node('div','specs');if(item.size){for(const [label,v] of [['Ngang hình chiếu',item.size.ngang+' mm'],['Cao hình chiếu',item.size.cao+' mm']]){const box=node('div','spec');add(box,node('small','',label),node('strong','',v));grid.append(box)}}let known=0;for(const [label,v] of [['Dòng sơ cấp',item.spec.dong_so_cap_dinh_muc_A],['Dòng thứ cấp',item.spec.dong_thu_cap_dinh_muc_A],['Cấp chính xác',item.spec.cap_chinh_xac],['Công suất VA',item.spec.cong_suat_VA]]){if(v===null||v===undefined||v==='')continue;known++;const box=node('div','spec');add(box,node('small','',label),node('strong','',value(v)));grid.append(box)}if(grid.childElementCount)specs.append(grid);if(!known)specs.append(node('p','muted','Chưa xác định cấu hình điện của đúng biến thể.'));if(item.spec_note)specs.append(node('p','note',item.spec_note));if(item.manufacturer_config){const c=item.manufacturer_config;specs.append(node('p','',`Dòng sản phẩm một tỷ số; thứ cấp có tùy chọn ${c.dong_thu_cap_tuy_chon_A.join(' hoặc ')} A. Đầu sơ cấp ${c.ky_hieu_dau_so.so_cap}, thứ cấp ${c.ky_hieu_dau_so.thu_cap}.`))}host.append(specs);
if(item.selection?.length){const sel=section('Cấu hình chọn thiết bị');const wrap=node('div','selection-wrap');const table=node('table','selection');const head=node('thead');const tr=node('tr');for(const label of ['Dòng sơ cấp','Thứ cấp','Lỗ xuyên','Cấp chính xác','VA'])tr.append(node('th','',label));head.append(tr);table.append(head);const body=node('tbody');for(const row of item.selection){const line=node('tr');for(const key of ['so_cap_A','thu_cap_A','lo_xuyen_mm','cap_chinh_xac','tai_VA'])line.append(node('td','',row[key]??'—'));body.append(line)}table.append(body);wrap.append(table);sel.append(wrap);sel.append(node('p','muted',item.selection_status||'Chọn đúng biến thể theo yêu cầu của hệ thống.'));host.append(sel)}}
const main=section(`CAD của thiết bị · ${item.single_views.length} bản CAD`);main.append(node('p','muted','Các mặt và biến thể được gom trong hồ sơ này. Mỗi bản CAD có DXF riêng; chọn đúng kiểu và mặt chính để bố trí vào tủ.'));const chosen=node('p');const mainDownload=link('Tải DXF mặt chính','#',true);main.append(chosen,mainDownload);const faceSelect=node('select');for(const label of ['Mặt trước','Mặt bên','Mặt trên','Mặt dưới','Mặt sau']){const option=node('option','',label);option.value=label;faceSelect.append(option)}const mounting=node('input');mounting.type='checkbox';const mountingLabel=node('label','', ' Thiết bị lắp theo tư thế khác');mountingLabel.prepend(mounting);main.append(node('p','','Mặt form tủ:'),faceSelect,mountingLabel);const cards=node('div','drawings');const entries=[];for(const view of item.single_views){const card=node('div','drawing');const preview=node('div','image');const img=node('img');img.src=view.preview;img.alt=(view.label||view.face)+' của '+item.display;img.loading='lazy';img.title='Bấm để xem CAD lớn';img.onclick=()=>{const dialog=node('dialog');dialog.style.cssText='width:min(900px,92vw);border:1px solid #cbd9e3;border-radius:12px';const large=node('img');large.src=view.preview;large.alt=img.alt;large.style.cssText='width:100%;height:70vh;object-fit:contain';const close=node('button','','Đóng');close.onclick=()=>dialog.close();add(dialog,node('h3','',view.label||view.face),large,close);dialog.onclose=()=>dialog.remove();document.body.append(dialog);dialog.showModal()};preview.append(img);const body=node('div','body');const badge=node('span','main-badge','Mặt chính');const title=node('strong','',view.label||view.face);const links=node('div','links');add(links,link('Tải DXF',view.dxf,true),link('Tọa độ và kích thước',view.json));const button=node('button','main-action','Chọn làm mặt chính');button.onclick=()=>{setMainView(item,view);refreshMain(view)};const guidance=node('p','muted',view.placement?.huong_dan||'Đối chiếu tư thế lắp trước khi chọn.');const suitability=node('p');add(body,badge,title,suitability,guidance,links,button);add(card,preview,body);cards.append(card);entries.push({view,card,badge,button,suitability})}function refreshMain(selected){chosen.textContent='Mặt chính: '+(selected.label||selected.face);mainDownload.href=selected.dxf;for(const entry of entries){const active=entry.view===selected;entry.card.classList.toggle('main-view',active);entry.badge.hidden=!active;entry.button.disabled=active;entry.button.textContent=active?'Đang là mặt chính':'Chọn làm mặt chính'}}function updateSuitability(){for(const entry of entries){const place=entry.view.placement||{};entry.suitability.textContent=place.cho_phep_chen===false?'Cần sửa CAD trước khi chèn':mounting.checked?'Đối chiếu theo tư thế lắp đã đổi':!place.mat_form_mac_dinh?'Cần đối chiếu hướng nhìn':place.mat_form_mac_dinh===faceSelect.value?'Phù hợp với tư thế lắp chuẩn':'Khác hướng nhìn form đang chọn'}}faceSelect.onchange=updateSuitability;mounting.onchange=updateSuitability;main.append(cards);host.append(main);refreshMain(getMainView(item));updateSuitability();host.append(link('Xem JSON thiết bị',item.json))}
$('dwg-link').href=data.dwg;
const stats=$('stats');for(const text of [data.categories.length+' nhóm thư mục',data.profiles.length+' loại/cỡ thiết bị',data.profiles.reduce((n,p)=>n+p.single_views.length,0)+' mặt CAD'])stats.append(node('span','',text));
$('search').addEventListener('input',renderProfiles);renderCategories();renderProfiles();
</script>
</body></html>'''

(ROOT / 'index.html').write_text(html.replace('__CATALOG_DATA__', embedded), encoding='utf-8')
print(json.dumps({'categories': len(categories), 'profiles': len(profiles),
                  'drawings': sum(len(p['drawings']) for p in profiles),
                  'html_bytes': (ROOT / 'index.html').stat().st_size}, ensure_ascii=False))







