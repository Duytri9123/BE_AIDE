"""Build an offline, source-linked browser for data/CatalogTB."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1] / 'data' / 'CatalogTB'


def url(path: Path) -> str:
    return quote(path.relative_to(ROOT).as_posix(), safe='/')


categories = []
for folder in sorted((p for p in ROOT.iterdir() if p.is_dir()), key=lambda p: p.name.casefold()):
    categories.append({
        'name': folder.name,
        'records': len(list(folder.rglob('thong_tin.json'))),
        'profiles': len(list(folder.rglob('thong_tin_thiet_bi.json'))),
    })

profiles = []
PROFILE_CATEGORIES = ('BienDong', 'ThietBiDoLuongHienThi', 'DenBaoNutNhanCauChiContactor', 'Bộ điều khiển', 'Cầu đấu')
for profile_path in sorted(p for folder in (ROOT / name for name in PROFILE_CATEGORIES) for p in folder.rglob('thong_tin_thiet_bi.json')):
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
    profiles.append({
        'category': next(name for name in PROFILE_CATEGORIES if name in profile_path.parts),
        'name': profile['ten_kieu'],
        'display': profile.get('ten_san_pham', profile['ten_kieu']),
        'brand': profile.get('hang_xac_nhan'),
        'folder': folder.parent.name,
        'type': profile['ban_chat'],
        'product_code': profile.get('ma_dong_san_pham'),
        'match_status': profile.get('muc_do_xac_nhan'),
        'use': profile['cong_dung'],
        'placement': profile['vi_tri_lap_dat'],
        'spec': profile['thong_so'],
        'spec_note': profile.get('luu_y_thong_so'),
        'measurement_spec_note': profile.get('ghi_chu_thong_so'),
        'features': profile.get('dac_diem', []),
        'size': profile.get('kich_thuoc_hinh_mm'),
        'manufacturer_config': profile.get('cau_hinh_dong_san_pham'),
        'selection': profile.get('lua_chon_ky_thuat', []),
        'selection_status': profile.get('trang_thai_lua_chon'),
        'sources': profile.get('nguon_tham_khao', []),
        'alternatives': profile.get('phuong_an_cung_loai', []),
        'compatibility_note': profile.get('luu_y_tuong_thich'),
        'json': url(profile_path),
        'drawings': drawings,
    })

data = {'categories': categories, 'profiles': profiles,
        'dwg': url(ROOT / 'THƯ VIỆN PHỤ KIỆN( Mới nhất).dwg')}
assert len([p for p in profiles if p['category']=='BienDong']) == 43
assert len([p for p in profiles if p['category']=='ThietBiDoLuongHienThi']) == 17
assert len([p for p in profiles if p['category']=='DenBaoNutNhanCauChiContactor']) == 19
assert len([p for p in profiles if p['category']=='Bộ điều khiển']) == 19
assert len([p for p in profiles if p['category']=='Cầu đấu']) == 37
assert sum(len(p['drawings']) for p in profiles) == 216
embedded = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')

html = r'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CatalogTB · Thư viện bản vẽ thiết bị</title>
<style>
:root{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:#142338;background:#eef3f8}
*{box-sizing:border-box}body{margin:0}button,input{font:inherit}button{cursor:pointer}
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
.drawings{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px}.drawing{border:1px solid #dce6ef;border-radius:9px;overflow:hidden}
.drawing .image{height:140px;background:#edf3f8;display:flex;align-items:center;justify-content:center}.drawing img{width:100%;height:100%;object-fit:contain}.drawing .body{padding:10px;font-size:12px}.drawing strong{display:block;overflow-wrap:anywhere}.drawing .links{display:flex;gap:9px;margin-top:8px}
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
const node=(tag,cls,text)=>{const el=document.createElement(tag);if(cls)el.className=cls;if(text!=null)el.textContent=text;return el};
const link=(label,href,download=false)=>{const a=node('a','',label);a.href=href;if(download)a.download='';return a};
const add=(parent,...children)=>children.forEach(c=>parent.append(c));
const value=v=>v===null||v===undefined||v===''?'Chưa xác minh':String(v);
function renderCategories(){const host=$('categories');host.replaceChildren();for(const item of data.categories){const button=node('button','category'+(state.category===item.name?' active':''));add(button,node('span','',item.name==='ThietBiDoLuongHienThi'?'Thiết bị đo lường hiển thị':item.name==='DenBaoNutNhanCauChiContactor'?'Đèn báo · Nút nhấn · Cầu chì · Contactor':item.name),node('span','',item.records?item.profiles+' hồ sơ':'Trống'));button.onclick=()=>{state.category=item.name;state.selected='';renderCategories();renderProfiles()};host.append(button)}}
function selectedKey(item){return item.json}
function filtered(){const q=$('search').value.trim().toLocaleLowerCase('vi');return data.profiles.filter(p=>p.category===state.category&&(!q||[p.name,p.display,p.brand,p.folder,p.type].join(' ').toLocaleLowerCase('vi').includes(q)))}
function renderProfiles(){const host=$('profiles');host.replaceChildren();const found=filtered();$('list-title').textContent=(state.category==='BienDong'?'Biến dòng':state.category==='ThietBiDoLuongHienThi'?'Thiết bị đo lường hiển thị':state.category==='DenBaoNutNhanCauChiContactor'?'Đèn báo · Nút nhấn · Cầu chì · Contactor':state.category)+' · '+found.length+' loại/cỡ';if(!found.length){host.append(node('p','empty','Không có hồ sơ thiết bị phù hợp.'));$('detail').replaceChildren(node('p','empty','Chọn một thiết bị để xem thông tin.'));return}if(!found.some(p=>selectedKey(p)===state.selected))state.selected=selectedKey(found[0]);for(const item of found){const button=node('button','profile'+(selectedKey(item)===state.selected?' active':''));add(button,node('strong','',item.display),node('small','',item.brand||'Phân theo loại thiết bị'),node('small','',item.drawings.length+' hình CAD'));button.onclick=()=>{state.selected=selectedKey(item);renderProfiles()};host.append(button)}renderDetail(found.find(p=>selectedKey(p)===state.selected))}
function section(title){const el=node('section','section');el.append(node('h3','',title));return el}
const extraLabels={nhan_tren_hinh:'Nhãn trên hình',so_hinh_cung_nhan:'Số hình cùng nhãn',kich_thuoc_hinh_dai_dien_mm:'Kích thước hình đại diện (mm)',so_ban_ve_6x42_5_mm:'Hình 6 × 42,5 mm',so_hinh_phong_120_phan_tram:'Hình phóng 120%',so_cuc_theo_nhan_hinh:'Số cực theo nhãn',dong_A_theo_nhan_hinh:'Trị số A theo nhãn',tham_khao_UK3N_TOSUN:'UK3N TOSUN tương tự',tham_khao_Hanyoung_Nux:'HYT Hanyoung NUX tương tự'};
function renderDetail(item){const host=$('detail');host.replaceChildren();if(!item)return;host.append(node('h2','',item.display));host.append(node('p','muted',item.type));const chips=node('div','chips');for(const text of [item.brand||'Theo loại thiết bị',item.product_code?'Dòng '+item.product_code:'Chưa xác định mã sản phẩm',item.drawings.length+' hình CAD'])chips.append(node('span','chip',text));host.append(chips);if(item.match_status)host.append(node('p','note',item.match_status));
const intro=section('Thông tin thiết bị');intro.append(node('p','',item.use),node('p','',item.placement));if(item.features?.length){const list=node('ul');for(const fact of item.features)list.append(node('li','',fact));intro.append(list)}host.append(intro);
if(item.alternatives?.length){const choices=section('Hãng và dòng cùng chức năng');const list=node('ul');for(const alt of item.alternatives)list.append(node('li','',alt.hang+' · '+alt.dong));choices.append(list);if(item.compatibility_note)choices.append(node('p','note',item.compatibility_note));host.append(choices)}
if(item.category!=='BienDong'){const specs=section('Thông số và lựa chọn');const grid=node('div','specs');const labels={so_pha:'Số pha',so_day:'Số dây',dien_nang:'Điện năng',mat_truoc_mm:'Mặt trước',truyen_thong:'Truyền thông',ngo_vao_dong_A:'Ngõ dòng',trang_thai:'Trạng thái',dien_ap_dinh_muc_V:'Điện áp định mức (V)',tan_so_Hz:'Tần số (Hz)',dong_dinh_muc_A:'Dòng định mức (A)',cap_chinh_xac:'Cấp chính xác',so_day_tuy_chon:'Số dây',dien_ap_3p4d_V:'Điện áp 3P4D (V)',dien_ap_3p3d_V:'Điện áp 3P3D (V)',dai_do:'Đại lượng / dải đo',do_sau_lap_dat_mm:'Độ sâu lắp đặt (mm)',dien_ap_dinh_muc:'Điện áp danh định',so_cuc_chinh:'Số cực chính',so_cuc:'Số cực',kich_thuoc_mat_truoc_mm:'Kích thước mặt trước (mm)',kich_thuoc_hinh_mm:'Kích thước hình (mm)',kieu_tac_dong:'Kiểu tác động',mau_hien_thi:'Màu hiển thị',nhom_khung:'Nhóm vỏ',dong_ac3_380_440V_A:'Dòng AC-3 tại 380–440 V (A)',kich_thuoc_ung_vien_mm:'Kích thước nhóm mã (mm)',ma_ung_vien:'Mã ứng viên',lo_lap_ung_vien_mm:'Lỗ lắp ứng viên (mm)',chieu_dai_ung_vien_mm:'Chiều dài ứng viên (mm)',ky_hieu_tren_hinh:'Ký hiệu trên hình',so_cap_theo_nhan_hinh:'Số cấp theo nhãn hình',dong_ung_vien:'Dòng ứng viên'};for(const [key,v] of Object.entries(item.spec||{})){if(v==null||v==='')continue;const box=node('div','spec');add(box,node('small','',labels[key]||extraLabels[key]||key),node('strong','',v));grid.append(box)}if(grid.childElementCount)specs.append(grid);if(item.measurement_spec_note)specs.append(node('p','note',item.measurement_spec_note));if(item.selection?.length){const list=node('ul');for(const fact of item.selection)list.append(node('li','',fact));specs.append(list)}host.append(specs);}else{const specs=section('Thông số');const grid=node('div','specs');if(item.size){for(const [label,v] of [['Ngang hình chiếu',item.size.ngang+' mm'],['Cao hình chiếu',item.size.cao+' mm']]){const box=node('div','spec');add(box,node('small','',label),node('strong','',v));grid.append(box)}}let known=0;for(const [label,v] of [['Dòng sơ cấp',item.spec.dong_so_cap_dinh_muc_A],['Dòng thứ cấp',item.spec.dong_thu_cap_dinh_muc_A],['Cấp chính xác',item.spec.cap_chinh_xac],['Công suất VA',item.spec.cong_suat_VA]]){if(v===null||v===undefined||v==='')continue;known++;const box=node('div','spec');add(box,node('small','',label),node('strong','',value(v)));grid.append(box)}if(grid.childElementCount)specs.append(grid);if(!known)specs.append(node('p','muted','Chưa xác định cấu hình điện của đúng biến thể.'));if(item.spec_note)specs.append(node('p','note',item.spec_note));if(item.manufacturer_config){const c=item.manufacturer_config;specs.append(node('p','',`Dòng sản phẩm một tỷ số; thứ cấp có tùy chọn ${c.dong_thu_cap_tuy_chon_A.join(' hoặc ')} A. Đầu sơ cấp ${c.ky_hieu_dau_so.so_cap}, thứ cấp ${c.ky_hieu_dau_so.thu_cap}.`))}host.append(specs);
if(item.selection?.length){const sel=section('Cấu hình chọn thiết bị');const wrap=node('div','selection-wrap');const table=node('table','selection');const head=node('thead');const tr=node('tr');for(const label of ['Dòng sơ cấp','Thứ cấp','Lỗ xuyên','Cấp chính xác','VA'])tr.append(node('th','',label));head.append(tr);table.append(head);const body=node('tbody');for(const row of item.selection){const line=node('tr');for(const key of ['so_cap_A','thu_cap_A','lo_xuyen_mm','cap_chinh_xac','tai_VA'])line.append(node('td','',row[key]??'—'));body.append(line)}table.append(body);wrap.append(table);sel.append(wrap);sel.append(node('p','muted',item.selection_status||'Chọn đúng biến thể theo yêu cầu của hệ thống.'));host.append(sel)}}
const gallery=section('Hình CAD');const cards=node('div','drawings');item.drawings.forEach((drawing,index)=>{const card=node('div','drawing');const preview=node('div','image');if(drawing.preview){const img=node('img');img.src=drawing.preview;img.alt='Hình CAD '+(index+1);img.loading='lazy';preview.append(img)}else preview.append(node('span','muted','Chưa có hình xem trước'));const body=node('div','body');add(body,node('strong','','Hình '+(index+1)));if(drawing.assembly)body.append(node('div','muted',drawing.assembly));if(drawing.size)body.append(node('div','muted','Kích thước hình: '+drawing.size.ngang+' × '+drawing.size.cao+' mm'));const links=node('div','links');add(links,link('DXF',drawing.dxf,true),link('Chi tiết',drawing.json));body.append(links);add(card,preview,body);cards.append(card)});gallery.append(cards);host.append(gallery);host.append(link('Xem JSON thiết bị',item.json))}
$('dwg-link').href=data.dwg;
const stats=$('stats');for(const text of [data.categories.length+' nhóm thư mục',data.profiles.length+' loại/cỡ thiết bị',data.profiles.reduce((n,p)=>n+p.drawings.length,0)+' hình gắn thiết bị'])stats.append(node('span','',text));
$('search').addEventListener('input',renderProfiles);renderCategories();renderProfiles();
</script>
</body></html>'''

(ROOT / 'index.html').write_text(html.replace('__CATALOG_DATA__', embedded), encoding='utf-8')
print(json.dumps({'categories': len(categories), 'profiles': len(profiles),
                  'drawings': sum(len(p['drawings']) for p in profiles),
                  'html_bytes': (ROOT / 'index.html').stat().st_size}, ensure_ascii=False))






