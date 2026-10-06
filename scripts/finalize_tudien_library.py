from build_tudien_library import *
import html,os
def load(p):return json.loads(p.read_text(encoding='utf8'))
coverage=load(OUT/'coverage.json');profiles=load(OUT/'geometry_profiles.json');skus=load(OUT/'sku_registry.json');frames=load(OUT/'form_tu/frames.json');families=load(OUT/'family_index.json')
summary=load(OUT/'summary.json');summary.update(status_counts=dict(collections.Counter(c['status'] for c in coverage)),geometry_profiles=len(profiles),sku_records=len(skus),frames=len(frames),families=len(families),visible_state_profiles=sum('hidden_entity_count_removed' in g for g in profiles),approved_sku_geometry_links=sum(bool(s.get('geometry_profile_id')) for s in skus))
summary['embedded']=load(OUT/'embedded_summary.json')
validation=load(OUT/'validation.json')
summary['geometry_files_checked']=validation['geometry_files_checked']
summary['geometry_transform_bound_differences']=len(validation['geometry_transform_bound_differences'])
save(OUT/'summary.json',summary)
for c in coverage:
 if c['source_file'].endswith('.dwg'):
  src=OUT/'nguon'/c['id']/'drawing.dxf';dest=OUT/'form_tu'/c['id']/'source_form.dxf'
  if not dest.exists():os.link(src,dest)
sources_by_id={c['id']:c['source_file'] for c in coverage}
rows={
 'Thiết bị / SKU':[{'name':s['description'],'brand':s['manufacturer'],'category':s['category'],'model':s['model'] or '', 'status':s['geometry_status'],'path':'sku_registry.json','source':' ; '.join(sorted(set(sources_by_id.get(x['source_id'],x['source_id']) for x in s['sources'])))} for s in skus],
 'CAD': [{'name':' / '.join(g['block_names'])+' | '+' '.join(g.get('visible_labels',[])), 'brand':g['manufacturer'],'category':g['category'],'model':g.get('poles_from_visible_label') or '', 'status':g['view_status'],'path':g['cad_views']['source_view'],'source':' ; '.join(sorted(set(sources_by_id.get(x['source_id'],x['source_id']) for x in g['sources'])))} for g in profiles],
 'Form tủ / Khung bản vẽ':[{'name':f['name'],'brand':'','category':'form_tu','model':' / '.join(f['view_labels']),'status':str(f['placements'])+' placements; khung bản vẽ không đồng nghĩa một tủ','path':f['path'],'cad':'form_tu/'+f['source_id']+'/source_form.dxf','preview':'form_tu/'+f['source_id']+'/frames/'+f['id'].split('_')[-1]+'/preview.svg','source':sources_by_id[f['source_id']]} for f in frames],
 'Nguồn':[{'name':c['source_file'],'brand':'','category':Path(c['source_file']).suffix,'model':c['id'],'status':c['status'],'path':'nguon/'+c['id']+('/drawing.dxf' if c['source_file'].endswith('.dwg') else '/workbook.json' if c['source_file'].endswith(('.xls','.xlsx')) else '/visual_evidence.json' if c['source_file'].endswith('.pdf') else '/image_transcription.json'),'source':c['sha256']} for c in coverage]
}
rows['Ảnh nhúng / OCR']=[{'name':m.get('observed_text',m['id']),'brand':'','category':'anh_nhung','model':m['id'],'status':'Đã đọc máy; mã hàng cần đối chiếu ảnh','path':m['path'],'source':' ; '.join(sources_by_id.get(x['source_id'],x['source_id']) for x in m['sources'])} for m in load(OUT/'embedded_media.json')]
data=json.dumps(rows,ensure_ascii=False).replace('<','\\u003c')
page='''<!doctype html><html lang="vi"><meta charset="utf-8"><title>Thư viện tủ điện</title><style>body{font:15px system-ui;margin:28px;color:#173047;background:#f6f8fb}h1{margin-bottom:6px}p{max-width:1100px;line-height:1.6}button,input,select{padding:10px;margin:4px;border:1px solid #ccd5e0;border-radius:6px;background:white}button{cursor:pointer}button.active{background:#17496b;color:white}table{width:100%;border-collapse:collapse;background:white}td,th{text-align:left;padding:12px;border-bottom:1px solid #dfe5ed;vertical-align:top}small{display:block;color:#66798a;max-width:700px;overflow-wrap:anywhere}a{color:#086b9a}#count{margin:12px 0}.bar{position:sticky;top:0;background:#f6f8fb;padding:8px 0}</style><h1>Thư viện tủ điện</h1><p>65 tệp nguồn • CAD thiết bị và phụ kiện • Form tủ và tọa độ bố trí. File CAD có thể là block nhiều trạng thái hoặc hình học tĩnh đã loại phần ẩn; xem trạng thái trước khi dùng. Liên kết SKU–geometry chưa xác minh không được dùng như kích thước sản xuất.</p><p><a href="README.md">Hướng dẫn</a> · <a href="coverage.json">Kiểm kê đầy đủ</a> · <a href="bo_tri/rules.json">Quy tắc tái sử dụng</a> · <a href="validation.json">Kiểm tra dữ liệu</a></p><div class="bar"><div id="tabs"></div><input id="q" placeholder="Tìm hãng, model, nguồn, loại thiết bị..." size="60"><span id="count"></span><button id="prev">Trước</button><button id="next">Sau</button></div><table><thead><tr><th>Tên / mô tả</th><th>Loại · Hãng · Model</th><th>Trạng thái và tệp</th></tr></thead><tbody id="body"></tbody></table><script>const data=DATA;let tab=Object.keys(data)[0],page=0;const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));function render(){const q=document.querySelector('#q').value.toLowerCase();const all=data[tab].filter(r=>Object.values(r).join(' ').toLowerCase().includes(q));page=Math.max(0,Math.min(page,Math.ceil(all.length/80)-1));document.querySelector('#count').textContent=`${all.length} mục · Trang ${page+1}`;document.querySelector('#body').innerHTML=all.slice(page*80,page*80+80).map(r=>`<tr><td>${esc(r.name)}<small>${esc(r.source)}</small></td><td>${esc(r.category)}<br>${esc(r.brand)}<br>${esc(r.model)}</td><td>${esc(r.status)}<br><a href="${encodeURI(r.path)}">Mở dữ liệu</a>${r.cad?` · <a href="${encodeURI(r.cad)}">CAD nguồn</a>`:''}${r.preview?` · <a href="${encodeURI(r.preview)}">Xem hình</a>`:''}</td></tr>`).join('');document.querySelectorAll('#tabs button').forEach(b=>b.classList.toggle('active',b.textContent===tab))}Object.keys(data).forEach(k=>{const b=document.createElement('button');b.textContent=k;b.onclick=()=>{tab=k;page=0;render()};document.querySelector('#tabs').append(b)});document.querySelector('#q').oninput=()=>{page=0;render()};document.querySelector('#prev').onclick=()=>{page--;render()};document.querySelector('#next').onclick=()=>{page++;render()};render();</script></html>'''.replace('DATA',data)
(OUT/'index.html').write_text(page,encoding='utf8')
report=f'''# Thư viện tủ điện từ bản vẽ và báo giá

Nguồn: `{SOURCE}`. Thư viện: `{OUT}`. Mở `index.html` để tìm kiếm offline.

## Phạm vi đã đọc

- {len(coverage)} tệp: 33 DWG, 24 XLSX, 5 XLS, 2 PDF và 1 JPG.
- {summary['sheets_read']} sheet, kể cả sheet ẩn; {summary['nonempty_rows_read']} dòng không rỗng. Giá trị, công thức và cache Excel được lưu ở `nguon/<id>/workbook.json`; không sửa báo giá gốc.
- {summary['drawing_projects']} bản DWG đã chuyển sang DXF và đọc cấu trúc. `cad_inventory.json` lưu chữ, kích thước, block và INSERT của mọi layout; bản DXF đầy đủ giữ cả hình đã explode và OLE.
- Hai PDF và ảnh đã có ghi nhận đọc hình riêng. PDF sơ đồ nguyên lý không được coi là bản bố trí vật lý.
- {len(profiles)} profile block CAD, trong đó {summary['visible_state_profiles']} profile trạng thái hiển thị. Đây KHÔNG phải số thiết bị thương mại; bao gồm block vô danh, chi tiết cơ khí và khung tên.
- {len(skus)} bản ghi sản phẩm theo mô tả/mã từ nguồn. `models.json` là dòng trích thô, `sku_registry.json` là nhóm sản phẩm; mã không có trong nguồn để trống, không tự tạo SKU hãng.
- {len(frames)} khung bản vẽ được lập chỉ mục; một tủ có thể xuất hiện ở nhiều khung/mặt nhìn. Không coi số khung là số form tủ độc lập.

## Cấu trúc

```text
tudien/
  form_tu/<source_id>/source_form.dxf
    form.json
    frames/<handle>/layout.json
    frames/<handle>/preview.svg
  thiet_bi/<loai>/<hang>/<dong_so_cuc>/
    family.json
    cad/<geometry_id>.dxf
    sku/<id>.json
  phu_kien/trong_tu/
  phu_kien/ngoai_tu/
  phu_kien/chua_xac_dinh/
  geometry/<geometry_id>/cad.dxf
  nguon/<source_id>/
  bo_tri/rules.json
  coverage.json
  geometry_profiles.json
  sku_registry.json
  family_index.json
```

CAD trong các thư mục hãng là hard link tới kho geometry: cùng một nội dung vật lý trên đĩa, không nhân bản CAD theo dòng định mức. Không chỉnh sửa trực tiếp hard link nếu muốn giữ bản nguồn; copy ra dự án trước khi chỉnh.

## Dùng cho Electrical AI

1. Tra loại thiết bị → hãng → mã/series → số cực → geometry phù hợp → mặt nhìn. Không dùng kích thước mặc định của một MCB chung cho mọi hãng.
2. `geometry_profile_id` chỉ được điền khi liên kết SKU được xác minh. `candidate_geometry_profile_ids` và `family_index.json` là ứng viên, không chứng minh mọi định mức cùng housing. Chưa có liên kết SKU được phê duyệt tự động trong lần trích này.
3. Profile có `hidden_entity_count_removed` đã bỏ entity ẩn của block động. Profile gốc chưa bỏ ẩn có thể chứa đồng thời 1P, 2P, 3P, 4P; bbox đó không phải kích thước một thiết bị.
4. `visible_width_drawing_units`/`visible_height_drawing_units` là bao hình 2D, có thể bao gồm nhãn/lỗ/phụ kiện. Chỉ đổi sang mm khi đơn vị và tỉ lệ nguồn được chứng minh. Chưa có kích thước 3D được chứng nhận từ catalog hãng.
5. Khi lấy bố trí, dùng `visible_world_bounds`, `visible_world_center`, scale, rotation và `normalized_to_source_matrix`. INSERT có thể đặt rất xa hình do base point; không dùng riêng tọa độ INSERT để gán thiết bị vào tủ.
6. `view_observations` trong khung là gợi ý theo khoảng cách tới nhãn mặt nhìn, chưa phải phân vùng mặt nhìn đã kiểm duyệt. Không học khoảng cách an toàn điện hoặc độ hở sản xuất từ khoảng cách chữ.
7. Phụ kiện `trong_tu/ngoai_tu` chỉ vị trí lắp bên trong/trên vỏ/cánh; không thay thế phân loại tủ trong nhà/ngoài trời. Vị trí suy từ tên chi tiết được đánh dấu suy luận. Mục thiếu bằng chứng ở `chua_xac_dinh`.

## Điểm cần lưu ý từ nguồn

- Ảnh bảng kê tủ 400V–300A: vỏ 1600 cao × 800 rộng × 500 sâu, tôn 2mm, hai lớp cánh, ngoài trời treo cột. Lỗ biến dòng ghi 50mm nhưng ghi chú yêu cầu ≥80mm: giữ cả hai, cần giải quyết trước chế tạo.
- PDF đơn 447: T.BV1/T.BV2 vỏ 600×400×250mm; DB.HT tủ nhựa âm tường 6 module. PDF thể hiện nguyên lý điện và mặt bằng công trình, không có CAD housing của hãng.
- PDF đơn 453: DB-LS là mã tủ LOAD SHED, không phải bằng chứng hãng LS. Nhà cung cấp cửa cuốn còn phải cung cấp sơ đồ điều khiển motor và UPS.
- Bộ nhập DXF bỏ một số FIELD/dữ liệu điều khiển block động/DIMASSOC. Hình học tĩnh được giữ; không hứa giữ khả năng chỉnh tham số block động. DWG gốc và DXF toàn bộ vẫn là nguồn đối chiếu.

## Mức hoàn thiện

Đã trích và lập chỉ mục toàn bộ tệp đọc được, không bỏ qua tệp lỗi (đơn 431 đã chuyển đổi lại). Tuy nhiên, đọc dữ liệu toàn bộ không có nghĩa mọi block đã được nhận diện thủ công hoặc mọi SKU đã ghép đúng housing. Các block chưa phân loại, mặt nhìn chưa đặt tên và SKU chưa có CAD tương ứng được giữ rõ trạng thái; không tạo CAD giả để lấp chỗ thiếu.

Xem `validation.json` cho kết quả kiểm tra file/link và `coverage.json` để truy về từng nguồn. Preview SVG bỏ chữ và hatch để xem bố cục; chữ và kích thước đầy đủ có trong CAD/JSON.
'''
(OUT/'README.md').write_text(report,encoding='utf8')
with (OUT/'README.md').open('a',encoding='utf8') as f:
 f.write('\n## Nguồn nhúng bổ sung\n\n'+json.dumps(summary['embedded'],ensure_ascii=False,indent=2)+'\n\nCác workbook nhúng được giải mã ở `nguon/embedded_ole/*.json`, kèm liên kết handle trong `embedded_ole.json`. Các ảnh Excel có ghi chú xem hình và OCR cục bộ ở `nguon/embedded_media/*_ocr.json`; mã OCR chưa phải SKU được xác nhận. Hai OLE ảnh có bản ghi `_visual.json`. Một OLE có payload rỗng trong nguồn.\n\nForm FACCO đã đối chiếu trực quan và tách riêng: `form_tu/FACCO_100A_6MCB_2P_32A/equipment_layout.dxf`, quy tắc ở `layout_rules.json`.\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
