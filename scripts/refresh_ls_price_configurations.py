"""Refresh LS price configurations and customer-facing CAD names only."""
import json,re,hashlib,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));CAT=ROOT/'data/CatalogTB';OUT=ROOT/'docs/ls-library-rebuild-2026-10-20'
from app.services.library_catalog_information import named_family_rows
from app.services.catalog_family_matching import row_poles
from app.services.cad.catalogtb_assets import face_code
rows=[r for r in json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'] if str(r.get('brand','')).lower() in ['ls','ls electric']]
report=[]
with sqlite3.connect(CAT/'_agent_index/equipment_catalog.sqlite') as db:
 for p in CAT.rglob('thong_tin_thiet_bi.json'):
  d=json.loads(p.read_text(encoding='utf8'));rel=p.relative_to(CAT)
  if d.get('browser_hidden') or (rel.parts[0]!='LS' and str(d.get('hang_xac_nhan','')).upper() not in ['LS','LS ELECTRIC']):continue
  backup=OUT/'before'/rel;backup.parent.mkdir(parents=True,exist_ok=True)
  if not backup.exists():backup.write_bytes(p.read_bytes())
  kind=(d.get('nhan_dien_ai') or {}).get('loai_thiet_bi_code') or '';spec=d.get('thong_so') or {};pole=str(spec.get('so_cuc') or spec.get('so_cuc_chinh') or '')
  if re.fullmatch('[1-4]',pole):pole+='P'
  if p.parent.name.startswith('OFFICIAL-MC') and kind=='CONTACTOR':spec['Loại cuộn hút']='AC'
  removed=[k for k,v in spec.items() if v is None or re.fullmatch(r'\s*(?:chưa xác định|chưa có thông tin|N/A|---|—)?\s*',str(v),re.I)]
  for k in removed:spec.pop(k)
  d['thong_so']=spec;code=str(d.get('ma_dong_san_pham') or '').strip();refs=d.setdefault('catalog_tham_khao',{'category':kind,'options':[]});existing=[o for o in (refs.get('options') or []) if o.get('basis')!='ls_pricebook_configuration']
  selected={r['id']:r for r in named_family_rows(code,'LS',kind,spec,rows)} if code else {}
  # The legacy CAD folders encode reviewed Metasol shared body sizes.
  frame=re.match(r'Metasol_(29|30|31|32|33|35)(?:_|$)',p.parent.name)
  if frame and kind=='MCCB':
   groups={'29':{'ABN':{'5','6','10'},'ABS':{'3','5','6'}},'30':{'ABS':{'10','12'},'ABH':{'5','12'}},'31':{'ABN':{'20','25'},'ABS':{'20','25'},'ABH':{'20','25'}},'32':{'ABN':{'40'},'ABS':{'40'},'ABH':{'40'}},'33':{'ABN':{'80'},'ABS':{'80'}},'35':{'ABS':{'100','120'}}}[frame[1]]
   for row in rows:
    m=re.fullmatch(r'(ABN|ABS|ABH|ABL)(\d+)([bc])',str(row.get('sku','')),re.I)
    if row.get('category')=='MCCB' and m and m[2][:-1] in groups.get(m[1].upper(),set()) and (not pole or pole==m[2][-1]+'P'):selected[row['id']]=row
  if p.parent.name.startswith('OFFICIAL-MC') and kind=='CONTACTOR':
   selected={key:r for key,r in selected.items() if (r.get('specifications') or {}).get('Loại cuộn hút')=='AC' and not re.search(r'/4|VDC',str(r.get('sku','')),re.I)}
  # Keep pole constraints even where supplier names encode poles in ABxNN3c.
  if pole:
   for key,row in list(selected.items()):
    m=re.fullmatch(r'(?:ABN|ABS|ABH|ABL)(\d+)[bc]',str(row.get('sku','')),re.I);actual=m[1][-1]+'P' if m else row_poles(row)
    if actual and actual!=pole:selected.pop(key)
  options=[{'brand':'LS','model':r['sku'],'source_row_id':r['id'],'specifications':{**(r.get('specifications') or {}),'Tên hàng':r['item_name']},'source_url':r.get('source_url'),'source_page':r.get('source_page'),'basis':'ls_pricebook_configuration','exact_cad_match':False} for r in selected.values()]
  by_id={o.get('source_row_id'):o for o in existing if o.get('source_row_id')}
  for o in options:by_id[o['source_row_id']]=o
  refs['options']=[o for o in existing if not o.get('source_row_id')]+list(by_id.values())
  capacities=sorted(set(str((r.get('specifications') or {}).get('Icu(KA)') or '').replace('KA','').replace('kA','').strip() for r in selected.values())-{''})
  rating='Icu '+('/'.join(capacities))+' kA theo bảng giá' if capacities else ''
  if code and not p.parent.name.startswith('OFFICIAL-'):
   name=' · '.join(x for x in ['LS',kind,code,pole,rating] if x)
   d['ten_san_pham']=name;d['ten_kieu']=name
   for v in d.get('cad_don',[]):
    if face_code(v.get('huong_nhin'))=='unknown':raise AssertionError(rel)
    old=str(v.get('nhan_hien_thi') or '');state=' · Nắp che' if re.search(r'COVER|nắp che',old+' '+v['id_hinh_goc'],re.I) else ''
    v['nhan_hien_thi']=name+' · '+v['huong_nhin']+state
  if options:d['quy_tac_dung_chung_cad']={**(d.get('quy_tac_dung_chung_cad') or {}),'relationship':'one_geometry_many_configuration_options','electrical_rating_from_geometry':False,'requirements':['Đối chiếu họ, số cực, kích thước, đầu nối và phụ kiện','Chọn In và Icu/Ics tại điện áp sử dụng theo từng dòng giá','Contactor và rơ le cần chọn đúng cuộn hút/dải chỉnh dòng']}
  p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8');cid='TB-'+hashlib.sha1(rel.as_posix().encode()).hexdigest()[:16]
  saved=db.execute('SELECT record_json FROM equipment WHERE catalog_id=?',(cid,)).fetchone()
  if saved:
   record=json.loads(saved[0]);record['display_name']=d['ten_san_pham']
   entries={v['id_hinh_goc']:v for v in d.get('cad_don',[])}
   for v in record.get('cad',{}).get('views',[]):
    if v['id'] in entries:v['name']=entries[v['id']].get('nhan_hien_thi') or entries[v['id']]['huong_nhin']
   db.execute('UPDATE equipment SET display_name=?,record_json=? WHERE catalog_id=?',(record['display_name'],json.dumps(record,ensure_ascii=False),cid));db.execute('UPDATE equipment_fts SET display_name=? WHERE catalog_id=?',(record['display_name'],cid))
  report.append({'profile':rel.as_posix(),'configuration_count':len(options),'price_row_ids':list(selected),'empty_specifications_removed':removed,'view_count':len(d.get('cad_don',[]))})
(OUT/'price-configurations.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('Updated LS profiles',len(report),'configuration links',sum(r['configuration_count'] for r in report),'distinct price rows',len(set(i for r in report for i in r['price_row_ids'])))

# Update the shipped information overlay so it cannot restore older LS names/options.
overlay_path=ROOT/'app/data/catalogtb_published_information.json'
overlay=json.loads(overlay_path.read_text(encoding='utf8'))
for entry in report:
 relative=entry['profile'];profile=json.loads((CAT/relative).read_text(encoding='utf8'))
 published=overlay.setdefault('profiles',{}).setdefault(relative,{})
 for key in ['ten_san_pham','ma_dong_san_pham','catalog_tham_khao']:
  if key in profile:published[key]=profile[key]
overlay_path.write_text(json.dumps(overlay,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
from app.services.catalogtb_browser import _refresh_browser_data
_refresh_browser_data(CAT)
print('Published LS information overlay and browser snapshot refreshed')
