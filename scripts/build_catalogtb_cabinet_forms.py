"""Publish source enclosure sheets as a separate form catalog, never insertion device CAD."""
raise SystemExit('Nguồn formtu cũ đã loại theo yêu cầu. Dùng rebuild_tudien_clean_forms.py với Tudien.')
import json,html,re,unicodedata
from pathlib import Path
import ezdxf
from ezdxf import bbox
from project_form_rejections import rejection,CACHE
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.config import Configuration,ColorPolicy
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page
from ezdxf.addons.drawing.properties import LayoutProperties
ROOT=Path(__file__).resolve().parents[1]/'data'
OUT=ROOT/'CatalogTB/Form tủ';OUT.mkdir(exist_ok=True);(OUT/'Previews').mkdir(exist_ok=True)
base=ROOT/'cabinet_templates/formtu';manifest=json.loads((base/'curated_manifest.json').read_text(encoding='utf-8'));rows=[]
def plain(text):
 return ''.join(c for c in unicodedata.normalize('NFD',text.lower().replace('đ','d')) if not unicodedata.combining(c))
accepted={};excluded=[]
denied_path=base/'user_excluded_manifest.json'
denied={x['id']:x for x in json.loads(denied_path.read_text(encoding='utf-8')).get('items',[])} if denied_path.exists() else {}
excluded.extend({'id':r['id'],'filename':r['filename'],'reason':r['reason']} for r in denied.values() if r['id'] not in {i['id'] for i in manifest['items']})
for item in manifest['items']:
 if item['id'] in denied:
  excluded.append({'id':item['id'],'filename':item['filename'],'reason':denied[item['id']]['reason']});continue
 doc=ezdxf.readfile(base/item['filename']);CACHE.clear();extent=bbox.extents(doc.modelspace(),fast=True)
 reason=rejection(doc,(extent.extmin.x,extent.extmin.y,extent.extmax.x,extent.extmax.y)) if extent.has_data else 'CAD không có hình học.'
 labels_text=' '.join(item.get('labels',[]))
 if re.search(r'không\s+(dùng|sử dụng)|\bhủy\b|báo lỗi|lỗi thiết kế',labels_text,re.I):reason='Nguồn có ghi chú không dùng/hủy/lỗi.'
 if reason:
  excluded.append({'id':item['id'],'reason':reason,'filename':item['filename']});continue
 labels=[plain(x) for x in item.get('labels',[])];combined=' '.join(labels)
 outside=any(any(t in x for t in ('mat canh','mat truoc','mat ngoai','ben ngoai')) for x in labels)
 inside=any(any(t in x for t in ('ben trong','mat trong','mat canh trong')) for x in labels)
 side=any('hong' in x or 'mat cat dung' in x or 'mat cat doc' in x for x in labels)
 parts=sum(bool(re.search(r'\d+\s*tam|\d+\s*bo',x)) for x in labels)
 reason='Bản cơ khí/khai triển hoặc chưa có nhãn mặt đủ để chọn bố trí.'
 if not (inside and (outside or side)) or parts>3:
  excluded.append({'id':item['id'],'reason':reason,'filename':item['filename']});continue
 dims=item['dimensions'];key=(item['kind'],dims['height'],dims['width'],dims['depth'])
 score=(outside+inside+side,len(labels),item.get('entity_count',0))
 if key in accepted:
  oldscore,old=accepted[key]
  if score<=oldscore:excluded.append({'id':item['id'],'reason':'Trùng cỡ và môi trường; giữ bản có nhãn mặt rõ hơn.','filename':item['filename']});continue
  excluded.append({'id':old['id'],'reason':'Trùng cỡ và môi trường; giữ bản có nhãn mặt rõ hơn.','filename':old['filename']})
 accepted[key]=(score,item)
source_count=len(manifest['items']);manifest['items']=[v[1] for v in accepted.values()]
(OUT/'loc_mau.json').write_text(json.dumps({'source_count':source_count,'selected_count':len(manifest['items']),'selection_basis':'Nhãn mặt trong + mặt ngoài/hông; loại bản nhiều chi tiết tấm; một bản đại diện mỗi cỡ/môi trường. Chưa phải kiểm chứng hình học từng mặt.','excluded':excluded},ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'form_loai_bo.json').write_text(json.dumps(excluded,ensure_ascii=False,indent=2),encoding='utf-8')

for i,item in enumerate(manifest['items'],1):
 f=base/item['filename'];preview=OUT/'Previews'/(item['id']+'.svg')
 if not preview.exists():
  doc=ezdxf.readfile(f);backend=SVGBackend();Frontend(RenderContext(doc),backend,config=Configuration(color_policy=ColorPolicy.BLACK)).draw_layout(doc.modelspace(),layout_properties=LayoutProperties('Model','#ffffff','#000000',units=4,dark_background=False))
  svg=backend.get_string(Page(0,0));svg=re.sub(r'stroke-width: ([0-9.]+)',lambda m:'stroke-width: '+str(max(700,float(m[1]))),svg);preview.write_text(svg,encoding='utf-8')
 dims=item['dimensions'];name=('Vỏ tủ trong nhà' if item['kind']=='indoor' else 'Vỏ tủ ngoài trời')+f" {dims['height']}×{dims['width']}×{dims['depth']} mm"
 rows.append({'id':item['id'],'name':name,'kind':item['kind'],'dimensions_mm':dims,'description':item['attributes'].get('#09',''),'preview':'Previews/'+preview.name,
 'source_dxf':'../../cabinet_templates/formtu/'+item['filename'],'source_handle':item['source_handle'],'drawing_labels':item.get('labels',[]),'cad_scope':'layout_candidate_sheet_multiple_views','insert_as_single_device':False,'verified_form':None,'auto_select':False})
 if i%25==0:print(i,'/',len(manifest['items']),flush=True)
forms=json.loads((ROOT/'form_tu_cong_nghiep/02_bay_form_iec_61439.json').read_text(encoding='utf-8'))['forms']
data={'schema':'cabinet_form_catalog_v1','dimension_order':['height','width','depth'],'shells':rows,'separation_forms':forms,'source':'BE_AIDE/data/cabinet_templates/formtu','rules':['CAD là tờ bản vẽ nhiều mặt, không chèn cả tờ như một mặt tủ.','Giữ nguyên khóa và đèn theo CAD nguồn.','Không lấy mẫu đã gạch bỏ/hủy/lỗi; bước lọc tự động chưa thay thế đối chiếu từng mặt.','Nhãn trong nhà/ngoài trời theo nguồn; chưa xác nhận IP/IK hoặc Form phân khoang.','Chọn vỏ, mặt làm việc, cánh trong/cánh ngoài/tấm lắp và khoảng gá theo hồ sơ dự án.'],'reference':'https://cache.industry.siemens.com/dl/files/936/107113936/att_1342112/v1/TIP_Planning_manual_SIVACON_S8_2025-02_EN.pdf'}
(OUT/'catalog.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
page=r"""<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Form tủ</title><style>body{font:15px system-ui;background:#edf3f8;color:#15344b;margin:0;padding:20px}header,.card{background:white;border:1px solid #ccdae6;border-radius:12px;padding:18px;margin-bottom:15px}input,select{padding:10px;border:1px solid #bdcedc;border-radius:7px}#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px}img{width:100%;height:210px;object-fit:contain;cursor:zoom-in}a{color:#0874b9}small{display:block;color:#627b8c;margin:8px 0}dialog{width:90vw;border:1px solid #ccdae6;border-radius:10px}dialog img{height:75vh}#forms{display:flex;gap:8px;flex-wrap:wrap}.form{max-width:350px;padding:12px;background:#edf3f8;border-radius:8px}button{padding:8px;cursor:pointer}</style><header><h1>Form tủ</h1><p>Mẫu bố trí đã lọc · kích thước theo thứ tự <b>Cao × Rộng × Sâu (mm)</b>.</p><p>Đã loại các bản khai triển và chi tiết gia công khỏi danh sách chính. Bản CAD nguồn có nhiều mặt trên cùng tờ. Xem và chọn mặt cần thiết trước khi bố trí.</p><input id="q" placeholder="Tìm kích thước, kiểu vỏ hoặc mã..."><select id="kind"><option value="">Tất cả</option><option value="indoor">Trong nhà</option><option value="outdoor">Ngoài trời</option></select><span id="count"></span><p><a href="catalog.json">JSON danh mục</a> · <a href="../index.html" target="_top">Thư viện thiết bị</a></p><details><summary>Form phân khoang 1, 2a, 2b, 3a, 3b, 4a, 4b</summary><p>Mức phân khoang phải xác nhận theo thiết kế; chưa gán tự động cho các vỏ bên dưới.</p><div id="forms"></div><a href="__REF__">Tài liệu Siemens về phân khoang</a></details></header><div id="grid"></div><script>const data=__DATA__;const e=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));function render(){const terms=document.querySelector('#q').value.toLowerCase().split(/\s+/).filter(Boolean),kind=document.querySelector('#kind').value;const rows=data.shells.filter(r=>(!kind||r.kind===kind)&&terms.every(t=>[r.name,r.id,r.description].join(' ').toLowerCase().includes(t)));document.querySelector('#count').textContent=' '+rows.length+' / '+data.shells.length+' mẫu';document.querySelector('#grid').innerHTML=rows.map(r=>`<article class="card"><h3>${e(r.name)}</h3><small>${e(r.id)} · ${e(r.description)}</small><img src="${r.preview}" loading="lazy" alt="${e(r.name)}"><small>${e(r.drawing_labels.join(' · '))}</small><a href="${r.source_dxf}" download>Tải bản CAD nguồn</a><small>Form phân khoang: chưa xác nhận</small></article>`).join('');for(const im of document.querySelectorAll('#grid img'))im.onclick=()=>{const dlg=document.createElement('dialog');const large=im.cloneNode();const close=document.createElement('button');close.textContent='Đóng';close.onclick=()=>dlg.close();dlg.append(large,close);dlg.onclose=()=>dlg.remove();document.body.append(dlg);dlg.showModal()}}document.querySelector('#forms').innerHTML=data.separation_forms.map(f=>`<div class="form"><b>Form ${e(f.code)}</b><p>${e(f.separation)}</p></div>`).join('');document.querySelector('#q').oninput=render;document.querySelector('#kind').onchange=render;render();</script></html>"""
(OUT/'index.html').write_text(page.replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('</',r'<\/')).replace('__REF__',data['reference']),encoding='utf-8')
print('Form catalog:',len(rows),'shell sheets')

