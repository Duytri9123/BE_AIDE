"""Complete missing role codes from explicit profile roles; preserve CAD/identity/selection."""
import copy,hashlib,json,sqlite3,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.services.cad.catalogtb_assets import assets,face_code
CAT=ROOT/'data/CatalogTB';OUT=ROOT/'docs/catalog-classification-2026-10-20';OUT.mkdir(parents=True,exist_ok=True)
ROLE_GROUPS={
'SOCKET':['Ổ cắm điện'], 'THERMAL_RELAY':['Rơ le nhiệt'], 'FAN':['Quạt lọc gió tủ điện'],
'VENT_FILTER':['Lưới lọc thông gió thụ động, không có động cơ','Lưới thông gió thụ động'], 'FAN_GUARD':['Tấm che bảo vệ quạt'],
'HINGE':['Bản lề cửa tủ'], 'FASTENER':['Chi tiết liên kết cơ khí'], 'TERMINAL_BAR':['Thanh phân phối N và PE','Thanh đấu nối'],
'INSULATING_SUPPORT':['Giá đỡ cách điện','Bộ đỡ cách điện','Trụ đỡ cách điện','Thanh đỡ cách điện'],
'CABLE_LUG':['Đầu cốt cáp bắt bu lông'], 'INSPECTION_WINDOW':['Cửa sổ quan sát'], 'BUSBAR_CLAMP':['Kẹp giữ thanh dẫn'],
'DOCUMENT_POCKET':['Túi đựng sơ đồ'], 'CABINET_LOCK':['Khóa cửa tủ điện','Khóa xoay tay nắm','Khóa tay nắm âm','Khóa bật','Khóa móc','Khóa cam dùng chìa tam giác'],
'WIRING_DUCT':['Máng dây trong tủ'], 'LABEL_HOLDER':['Giá giữ nhãn'], 'SAFETY_LABEL':['Nhãn an toàn'],
'LIFTING_ATTACHMENT':['Điểm nâng tủ','Bản mã nâng tủ'], 'WALL_BRACKET':['Bản mã treo tủ'], 'CABINET_LATCH':['Chốt vặn cửa tủ','Chốt trượt cửa tủ'],
'CABINET_HANDLE':['Tay nắm cửa tủ'], 'TERMINAL_BLOCK':['Dãy cầu đấu nhiều cực bắt vít','Cầu đấu xuyên dây một tầng lắp ray','Dãy cầu đấu bắt vít'],
'TERMINAL_END_STOP':['Phụ kiện cố định cầu đấu'], 'REACTOR':['Cuộn kháng ba pha lõi thép'], 'ATS':['ATS']}
ROLES={role:code for code,names in ROLE_GROUPS.items() for role in names}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stats():
 a=assets(refresh=True)
 return {'assets':len(a),'unclassified_assets':sum(x['category']=='UNCLASSIFIED' for x in a),'unknown_faces':sum(x['face']=='unknown' for x in a)}
def main():
 before=stats();changes=[];unresolved=[]
 for path in sorted(CAT.rglob('thong_tin_thiet_bi.json')):
  original=json.loads(path.read_text(encoding='utf8'));profile=copy.deepcopy(original);relative=path.relative_to(CAT).as_posix();typ=None
  if not (profile.get('nhan_dien_ai') or {}).get('loai_thiet_bi_code'):
   role=profile.get('ban_chat');typ=ROLES.get(role)
   if role=='Nguồn và biến áp':
    if profile.get('ten_san_pham')=='Biến áp · nhãn TR':typ='TRANSFORMER'
    # A voltage label alone does not establish the construction of a supply.
   if typ:
    profile['nhan_dien_ai']={**(profile.get('nhan_dien_ai') or {}),'loai_thiet_bi_code':typ,'recognition_basis':'Vai trò ghi rõ trong ban_chat của hồ sơ hiện có; chưa xác nhận mã hàng hoặc thông số điện.','role_evidence':role,'exact_SKU_confirmed':False}
    profile['tu_khoa_tim_kiem']=list(dict.fromkeys([*(profile.get('tu_khoa_tim_kiem') or []),role,typ]))
   else:unresolved.append({'profile':relative,'role':role,'name':profile.get('ten_san_pham')})
  labels=[]
  for view in profile.get('cad_don',[]):
   label=str(view.get('nhan_hien_thi') or '')
   if face_code(view.get('huong_nhin'))!='unknown' and any(x in label.casefold() for x in ['chưa xác','chua xac','unknown']):
    view['nhan_hien_thi']=view['huong_nhin'];labels.append(view['id_hinh_goc'])
  if profile==original:continue
  paths={v['id_hinh_goc']:path.parent/v['duong_dan'] for v in original.get('cad_don',[]) if v.get('duong_dan') and (path.parent/v['duong_dan']).is_file()}
  hashes={k:digest(p) for k,p in paths.items()}
  for key in ['hang_xac_nhan','ma_dong_san_pham','thong_so','auto_select','needs_review','cad_chen_tu']:
   assert profile.get(key)==original.get(key),(relative,key)
  for old,new in zip(original.get('cad_don',[]),profile.get('cad_don',[])):
   assert {k:v for k,v in old.items() if k!='nhan_hien_thi'}=={k:v for k,v in new.items() if k!='nhan_hien_thi'}
  backup=OUT/'before'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
  if not backup.exists():backup.write_bytes(path.read_bytes())
  path.write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
  assert all(digest(paths[k])==sha for k,sha in hashes.items())
  changes.append({'profile':relative,'type_added':typ,'labels_corrected':labels,'cad_hashes':hashes})
 with sqlite3.connect(CAT/'_agent_index/equipment_catalog.sqlite') as db:
  for change in changes:
   relative=change['profile'];path=CAT/relative;profile=json.loads(path.read_text(encoding='utf8'));cid='TB-'+hashlib.sha1(relative.encode()).hexdigest()[:16]
   row=db.execute('SELECT record_json FROM equipment WHERE catalog_id=?',(cid,)).fetchone()
   if not row:continue
   record=json.loads(row[0]);typ=change['type_added']
   if typ:record['category']=typ
   for view in record.get('cad',{}).get('views',[]):
    entry=next((v for v in profile['cad_don'] if v['id_hinh_goc']==view['id']),None)
    if entry and entry['id_hinh_goc'] in change['labels_corrected']:view['name']=entry['nhan_hien_thi']
   if typ:
    db.execute('UPDATE equipment SET category=?,record_json=? WHERE catalog_id=?',(typ,json.dumps(record,ensure_ascii=False),cid))
    db.execute('UPDATE equipment_fts SET category=? WHERE catalog_id=?',(typ,cid))
   else:db.execute('UPDATE equipment SET record_json=? WHERE catalog_id=?',(json.dumps(record,ensure_ascii=False),cid))
 index=CAT/'ai_device_index.json'
 if index.exists():
  data=json.loads(index.read_text(encoding='utf8'));changed={x['profile'] for x in changes}
  for row in data.get('items',[]):
   if row['profile'] not in changed:continue
   p=json.loads((CAT/row['profile']).read_text(encoding='utf8'));row['identification']=p.get('nhan_dien_ai',{});row['search_aliases']=p.get('tu_khoa_tim_kiem',[])
  index.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 after=stats();report={'before':before,'after':after,'classified_profiles':sum(bool(c['type_added']) for c in changes),'corrected_view_labels':sum(len(c['labels_corrected']) for c in changes),'types_added':dict(Counter(c['type_added'] for c in changes if c['type_added'])),'changes':changes,'still_unclassified_profiles':unresolved}
 (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps({k:v for k,v in report.items() if k not in ['changes','still_unclassified_profiles']},ensure_ascii=True),flush=True)
 from app.services.catalogtb_browser import _refresh_browser_data
 _refresh_browser_data(CAT);print('Browser index refreshed',flush=True)
if __name__=='__main__':main()
