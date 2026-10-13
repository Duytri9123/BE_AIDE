"""Audit the actual loader, then publish complete discovery metadata without guessing SKUs."""
from pathlib import Path
import sys,json,re,unicodedata,hashlib,html,csv
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB';OUT=ROOT.parent/'outputs/catalogtb-agent-audit';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT));sys.stdout.reconfigure(encoding='utf8')
from app.services.cad import catalogtb_assets as loader

def norm(t):return ''.join(c for c in unicodedata.normalize('NFD',str(t or '')) if not unicodedata.combining(c)).replace('đ','d').replace('Đ','D').upper()
def write(p,d):
 temporary=p.with_suffix(p.suffix+'.tmp')
 temporary.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 temporary.replace(p)
def infer(d):
 old=(d.get('nhan_dien_ai') or {}).get('loai_thiet_bi_code')
 if old:return str(old).upper(),'profile.nhan_dien_ai'
 text=norm(' '.join(str(d.get(k) or '') for k in ['ten_san_pham','ban_chat']))
 rules=[(r'THANH TIEP DIA\s+PE','PE_BAR'),(r'THANH TRUNG TINH\s+N','NEUTRAL_BAR'),(r'SU DO|DO CACH DIEN|KEP CACH DIEN','MOUNTING_SUPPORT'),(r'THANH DAU NOI CO VIT','TERMINAL_BAR'),(r'BO DIEU KHIEN MAY PHAT','GENERATOR_CONTROLLER'),(r'BO ON AP','VOLTAGE_STABILIZER'),(r'CHOT CUA','DOOR_LATCH'),(r'TAY NAM.*CUA','DOOR_HANDLE'),(r'BU LONG','BOLT'),(r'DAI OC','NUT'),(r'CUA SO QUAN SAT','VIEWING_WINDOW'),(r'KHAY TAI LIEU','DOCUMENT_HOLDER'),(r'NHAN CAI|NHAN CANH BAO','LABEL'),(r'MOC CAU|TAI CAU','LIFTING_LUG'),(r'TAI TREO TU','MOUNTING_LUG'),(r'VIT VAN','SCREW'),(r'CAU DAU|DOMINO|TERMINAL','TERMINAL'),(r'BO NGUON|NGUON .*24VDC','POWER_SUPPLY'),(r'BIEN AP','TRANSFORMER'),(r'ROLE NHIET|RO LE NHIET','THERMAL_RELAY'),(r'ROLE TRUNG GIAN|RO LE TRUNG GIAN','RELAY'),(r'GIAM SAT PHA|BAO VE PHA','PHASE_RELAY'),(r'HEN GIO|TIMER','TIMER'),(r'BO DIEU KHIEN.*ATS|BO DIEU KHIEN CHUYEN NGUON','ATS_CONTROLLER'),(r'\bATS\b','ATS'),(r'BIEN TAN','VFD'),(r'CAU CHI','FUSE'),(r'DEN BAO','LIGHT'),(r'NUT NHAN','PUSHBUTTON'),(r'CHUYEN MACH|CONG TAC XOAY','SELECTOR'),(r'KHOI DONG TU|CONTACTOR','CONTACTOR'),(r'CUON KHANG','REACTOR'),(r'TU BU','CAPACITOR'),(r'QUAT','FAN'),(r'CHOP THOANG|THONG GIO','LOUVER'),(r'BAN LE','HINGE'),(r'KHOA','LOCK'),(r'O CAM','SOCKET'),(r'CHONG SET','SPD'),(r'PHIP|GOI DO|KEP THANH','MOUNTING_SUPPORT'),(r'DAU COS','CABLE_LUG'),(r'RAY DIN|THANH RAY','DIN_RAIL'),(r'MANG','DUCT')]
 for pattern,code in rules:
  if re.search(pattern,text):return code,'explicit existing product name / functional description'
 return 'UNCLASSIFIED','insufficient identity; retained for discovery, not automatic insertion'

before_assets=[r for r in loader.assets(refresh=True) if r.get('classification_source')=='profile' and r['category']!='UNCLASSIFIED'];items=[];groups=Counter();issues=[]
for p in sorted(CAT.rglob('thong_tin_thiet_bi.json')):
 try:d=json.loads(p.read_text(encoding='utf8'))
 except Exception as e:issues.append({'profile':p.relative_to(CAT).as_posix(),'issue':'invalid_json','detail':str(e)});continue
 profile=p.relative_to(CAT).as_posix();code,basis=infer(d);group=str(d.get('nhom') or p.relative_to(CAT).parts[0]);groups[group]+=1
 views=[]
 for v in d.get('cad_don') or []:
  path=(p.parent/v.get('duong_dan',f"CadDon/{v.get('id_hinh_goc')}/ban_ve.dxf")).resolve();inside=path.is_relative_to(CAT.resolve());exists=inside and path.is_file()
  face=loader.face_code(v.get('huong_nhin'));unit=None;raw_unit=None
  if exists:
   # Header scan only: this is not a complete DXF geometry validation.
   with path.open('r',encoding='utf8',errors='replace') as f:head=f.read(65536)
   match=re.search(r'\$INSUNITS\s*\n\s*70\s*\n\s*(-?\d+)',head)
   unit=int(match[1]) if match else None
   raw_unit=unit
   normalized=loader.normalized_source(path)
   if normalized!=path:
    with normalized.open('r',encoding='utf8',errors='replace') as f:head=f.read(65536)
    match=re.search(r'\$INSUNITS\s*\n\s*70\s*\n\s*(-?\d+)',head)
    unit=int(match[1]) if match else None
  view={'source_id':v.get('id_hinh_goc'),'dxf':path.relative_to(CAT.resolve()).as_posix() if inside else str(path),'file_exists':exists,'source_face':v.get('huong_nhin'),'face':face,'units_code':unit,'entry_permission':(v.get('bo_tri_trong_tu') or {}).get('cho_phep_chen'),'manual_geometry_review_required':True}
  views.append(view)
  view['original_units_code']=raw_unit
  view['unit_verification']=v.get('unit_verification') or {}
  for condition,label in [(not exists,'missing_or_outside_cad'),(face=='unknown','unconfirmed_view'),(exists and unit!=4,'units_not_verified_mm')]:
   if condition:issues.append({'profile':profile,'view':v.get('id_hinh_goc'),'issue':label})
 if not (d.get('nhan_dien_ai') or {}).get('loai_thiet_bi_code'):issues.append({'profile':profile,'issue':'missing_profile_classification','manifest_category':code})
 if code=='UNCLASSIFIED':issues.append({'profile':profile,'issue':'identity_unresolved'})
 items.append({'profile':profile,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'name':d.get('ten_san_pham') or d.get('ten_kieu'),'group':group,'brand':d.get('hang_xac_nhan'),'category_code':code,'classification_basis':basis,'recognition_status':'unresolved' if code=='UNCLASSIFIED' else 'function_identified','exact_SKU_verified':False,'aliases':list(dict.fromkeys([str(x) for x in [d.get('ten_san_pham'),d.get('ten_kieu'),d.get('ma_dong_san_pham'),*(d.get('tu_khoa_tim_kiem') or [])] if x])),'specifications':d.get('thong_so') or {},'source_auto_select':d.get('auto_select'),'source_needs_review':d.get('needs_review'),'views':views,'physical_units_per_cad':(d.get('cau_truc_cum') or {}).get('physical_units_per_cad',1),'source_document':'thong_tin_thiet_bi.json'})

summary={'profiles':len(items),'declared_cad_views':sum(len(r['views']) for r in items),'before_loader_profiles':len({r['profile_path'] for r in before_assets}),'before_loader_views':len(before_assets),'missing_profile_classification':sum(not (json.loads((CAT/r['profile']).read_text(encoding='utf8')).get('nhan_dien_ai') or {}).get('loai_thiet_bi_code') for r in items),'manifest_function_identified':sum(r['category_code']!='UNCLASSIFIED' for r in items),'manifest_identity_unresolved':sum(r['category_code']=='UNCLASSIFIED' for r in items),'issues':dict(Counter(r['issue'] for r in issues))}
previous_manifest=json.loads((CAT/'ai_library_manifest.json').read_text(encoding='utf8')) if (CAT/'ai_library_manifest.json').is_file() else {}
manifest={'schema_version':1,'scope':'Complete live CatalogTB profile discovery; device, assembly, accessory and mechanical part are not one physical quantity','summary':summary,'policy':{'never_report_unclassified_as_absent':True,'unknown_SKU_is_not_missing_geometry':True,'do_not_guess_view_or_units':True,'unclassified_is_discoverable_not_insertable':True,'original_profiles_and_CAD_unchanged':True},'items':items,'issues':issues}
for field in ('physical_cad_file_summary','physical_cad_file_inventory','source_cad_documents'):
 if field in previous_manifest:manifest[field]=previous_manifest[field]
write(CAT/'ai_library_manifest.json',manifest);loader.assets(refresh=True)
after=loader.assets();summary.update(after_loader_profiles=len({r['profile_path'] for r in after}),after_loader_views=len(after))
requirements={}
for category in ['MCB','CONTACTOR','TIMER','SELECTOR','POWER_SUPPLY','RELAY','TERMINAL','FUSE']:
 matches=loader.candidates(category);all_known=[r for r in items if loader.category_matches(category,r['category_code'])]
 requirements[category]={'discoverable_profiles':len(all_known),'eligible_reference_families':len(matches),'profiles':[r['profile'] for r in all_known],'candidate_ids':[r['id'] for r in matches],'status':'reference_available' if matches else 'present_but_view_or_permission_pending' if all_known else 'identity_not_yet_mapped'}
manifest['order_457_requirements']=requirements;write(CAT/'ai_library_manifest.json',manifest);write(OUT/'audit.json',manifest)
with (OUT/'issues.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['profile','view','issue','manifest_category','detail']);w.writeheader();w.writerows(issues)
esc=lambda v:html.escape(str(v if v is not None else 'Chưa xác nhận'))
parts=['<!doctype html><meta charset="utf-8"><title>Kiểm tra nhận diện CatalogTB</title><style>body{font:15px Arial;margin:28px;color:#263746}table{border-collapse:collapse;width:100%;margin:16px 0}th,td{padding:8px;border:1px solid #ccd6dc;text-align:left}th{background:#edf3f7}input{padding:10px;width:420px}.note{padding:16px;background:#fff0c9}</style><h1>AGENT đọc được gì trong CatalogTB?</h1><p class="note">Kiểm tra bộ nạp và bộ lọc thực tế, không phải chứng nhận AI nhìn đúng mọi hình hoặc tất cả mã thiết bị đã đủ điều kiện chế tạo. Hồ sơ chưa rõ vẫn có trong manifest, không được báo thành thư viện không có CAD.</p><table><tr><th>Chỉ số</th><th>Số lượng</th></tr>']
for k,v in summary.items():parts.append('<tr><td>'+esc(k)+'</td><td>'+esc(v)+'</td></tr>')
parts.append('</table><h2>Các nhóm cần cho đơn 457</h2><table><tr><th>Loại</th><th>Hồ sơ tìm được</th><th>Họ có mặt CAD để chọn tham khảo</th><th>Trạng thái</th></tr>')
for k,v in requirements.items():parts.append('<tr>'+''.join('<td>'+esc(x)+'</td>' for x in [k,v['discoverable_profiles'],v['eligible_reference_families'],v['status']])+'</tr>')
parts.append('</table><h2>Toàn bộ hồ sơ</h2><input placeholder="Lọc tên, nhóm, đường dẫn…" oninput="document.querySelectorAll(\'#items tr[data-row]\').forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(this.value.toLowerCase()))"><table id="items"><tr><th>Tên / hồ sơ</th><th>Loại nhận diện</th><th>Số CAD</th><th>Hướng nhìn</th><th>Trạng thái</th></tr>')
for r in items:parts.append('<tr data-row>'+''.join('<td>'+esc(v)+'</td>' for v in [str(r['name'])+' / '+r['profile'],r['category_code'],len(r['views']),', '.join(v['source_face'] or '?' for v in r['views']),r['recognition_status']])+'</tr>')
parts.append('</table><p><a href="audit.json">JSON kiểm tra đầy đủ</a> · <a href="issues.csv">CSV các chỗ thiếu</a> · <a href="http://127.0.0.1:5173/workspace/16">Dự án 457 trên FE</a></p>')
(OUT/'review.html').write_text('\n'.join(parts),encoding='utf8')
print(json.dumps({'summary':summary,'order457':{k:{a:b for a,b in v.items() if a not in ('profiles','candidate_ids')} for k,v in requirements.items()}},ensure_ascii=False))
