from pathlib import Path
import json,hashlib,html,csv
from collections import Counter
ROOT=Path(__file__).resolve().parents[2];CAT=ROOT/'BE_AIDE/data/CatalogTB';OUT=ROOT/'outputs/catalogtb-84-evidence'
rows=json.loads((OUT/'evidence.json').read_text(encoding='utf8'))
sources={
'Chint':['https://www.chintglobal.com/global/en/products/low-voltage/iec/secondary-power-distribution/nm1.html','https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/secondary-power-distribution/mccb/nxm/catalog/NXM-MCCB-Catalog.pdf'],
'LS':['https://www.ls-electric.com/upload/customer/download/1213/Metasol_MCCB-ELCB_Technical%20Manual_E.pdf'],
'Schneider':['https://www.se.com/jp/ja/product/LV429640/circuit-breaker-compact-nsx100f-36ka-415vac-tmd-trip-unit-100a-4-poles-3d/']}
front={3,4,5,11,12,15,16,18,20,21,22,24,25,26,29,31,32,34,35,43,44,45,46,47,48,50,54,55,57,58,61,62,63,66,68,71,72,77,78,79,82,83}
side={2,6,7,8,9,10,13,14,17,19,27,28,30,37,39,42,49,51,52,56,59,60,67,69,73,76,80,81,84}
end={36,38,40,53,64,65,75}
compound={23,33,70,74}
manifest_path=CAT/'ai_library_manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf8'));by_path={x['profile']:x for x in manifest['items']};results=[]
for row in rows:
 n=row['number'];p=CAT/row['profile'];d=json.loads(p.read_text(encoding='utf8'));code='UNCLASSIFIED' if n==1 else 'CONTACTOR' if n in (41,62) else 'SWITCH_DISCONNECTOR' if n==71 else 'MCCB'
 urls=[] if n==1 else sources[row['group']][:]
 if row['group']=='Schneider' and 'NS100_' in row['name'] or row['group']=='Schneider' and 'NS400_' in row['name']:urls=['https://ckm-content.se.com/ckmContent/sfc/servlet.shepherd/document/download/0691H00000FWbNdQAL']
 if row['group']=='Schneider' and 'cvs-' in row['name']:urls=['https://www.se.com/sa/en/download/document/LVED210011EN/']
 if row['group']=='Schneider' and 'ezc' in row['name']:urls=['https://www.se.com/id/en/product-range/997-easypact-ezc/']
 if n==41:urls=['https://www.ls-electric.com/upload/customer/download/1416/Metasol_MC_E_1310.pdf']
 if n==62:urls=['https://eshop.se.com/om/ict-25a-1no-230-240v-50hz-contactor-a9c20731.html']
 if n==71:urls=['https://eshop.se.com/in/shop-by-category/low-voltage-products/switch-disconnector/compact-ins.html']
 face='Mặt trước' if n in front else 'Mặt bên' if n in side else None
 limitation='Đã xác định loại/họ bằng nhãn nguồn, hình CAD và tài liệu hãng; chưa xác nhận mã đặt hàng, điện áp, dòng hoặc tư thế lắp.'
 if n==1:limitation='MX100 không có chữ hãng/model đọc được trong CAD; hình bao chưa đủ phân biệt bộ điều khiển nào. Giữ chưa xác định.'
 if n in end:limitation+=' Hình nhìn theo đầu thiết bị hoặc nắp: chưa phân biệt chắc mặt trên/dưới và thành phần; không tự gán mặt.'
 if n in compound:limitation+=' CAD có nhiều thành phần/trạng thái hoặc hình chồng; chưa đủ để chèn nguyên bản như một thiết bị.'
 evidence=dict(review_date='2026-10-10',category_code=code,visual_review=True,preview=row['views'][0]['image'],source_block=(d.get('nguon_cad') or {}).get('block'),text_entities_found=sum(len(v['texts']) for v in row['views']),text_outline_note='No extractable TEXT/MTEXT/ATTRIB found; visible lettering may be linework, not searchable text.',face=face,face_basis='Visual linework review: front handle and terminals / body depth and protruding handle' if face else 'Unconfirmed',official_family_sources=urls,exact_sku_verified=False,automatic_insertion_approved=False,limitation=limitation)
 d['nhan_dien_bo_sung_20261010']=evidence
 if code!='UNCLASSIFIED':
  d.setdefault('nhan_dien_ai',{})['loai_thiet_bi_code']=code
  d['nhan_dien_ai']['exact_sku_verified']=False
 d['auto_select']=False;d['needs_review']=True
 for view in d.get('cad_don',[]):
  if face:view['huong_nhin']=face
  view.setdefault('bo_tri_trong_tu',{})['cho_phep_chen']=False
  view['recognition_evidence']='nhan_dien_bo_sung_20261010'
 d['muc_do_xac_nhan']=limitation
 d['tu_khoa_tim_kiem']=list(dict.fromkeys([*(d.get('tu_khoa_tim_kiem') or []),code]))
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 m=by_path[row['profile']];m.update(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),category_code=code,classification_basis='Reviewed CAD image + source block identity + official family documentation' if code!='UNCLASSIFIED' else 'Insufficient identity after visual review',recognition_status='function_identified' if code!='UNCLASSIFIED' else 'unresolved',source_auto_select=False,source_needs_review=True,identity_evidence=evidence)
 for v in m['views']:
  if face:v.update(source_face=face,face='front' if face=='Mặt trước' else 'side')
  v['entry_permission']=False
 results.append(dict(number=n,name=row['name'],profile=row['profile'],**evidence))
manifest['summary']['manifest_function_identified']=sum(i['category_code']!='UNCLASSIFIED' for i in manifest['items']);manifest['summary']['manifest_identity_unresolved']=sum(i['category_code']=='UNCLASSIFIED' for i in manifest['items'])
manifest['policy']['original_profiles_and_CAD_unchanged']=False;manifest['policy']['original_CAD_geometry_unchanged']=True
manifest['recognition_test_result']={'status':'pending_retest_after_84_evidence_update','live_backend_reload_verified':False,'ai_vision_all_images_benchmark_completed':False}
manifest['identity_review_84']={'classified':83,'unresolved':1,'face_identified':len(front|side),'rendered_profiles':84,'electrical_specifications_verified':False}
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(OUT/'decisions.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
parts=['<!doctype html><meta charset="utf-8"><title>Nhận diện 84 hồ sơ CatalogTB</title><style>body{font:15px Arial;margin:24px}img{max-width:320px;max-height:420px}article{border-bottom:1px solid #bbb;padding:18px}p{max-width:1000px}</style><h1>Nhận diện 84 hồ sơ CatalogTB</h1><p>83 xác định loại: 80 MCCB, 2 contactor, 1 switch-disconnector. MX100 còn chưa xác định. 71 mặt trước/bên nhận diện; 13 hồ sơ còn chưa rõ mặt/thành phần. Thông số điện và mã đặt hàng chưa xác nhận. CAD gốc không sửa. Không hồ sơ nào được tự chèn chỉ dựa vào phân loại này.</p><a href="evidence.json">Metadata gốc + chữ + bbox</a> · <a href="decisions.json">Quyết định nhận diện</a>']
for r in results:
 parts.append('<article><h2>'+str(r['number'])+'. '+html.escape(r['name'])+'</h2><img src="'+r['preview']+'"><p><b>'+r['category_code']+' — '+html.escape(r['face'] or 'Chưa xác nhận mặt')+'</b></p><p>'+html.escape(r['limitation'])+'</p><p>'+html.escape(r['profile'])+'</p>')
 for url in r['official_family_sources']:parts.append('<a href="'+html.escape(url,quote=True)+'">Tài liệu hãng</a> ')
 parts.append('</article>')
(OUT/'identity-review.html').write_text('\n'.join(parts),encoding='utf8')
print(json.dumps(Counter(r['category_code'] for r in results)));print('Face reviewed',len(front|side))
