"""Render Mitsubishi prices in the same grouped table style as LS."""
import json

from group_mitsubishi_price_rows import write_grouped
from render_mitsubishi_views import render_views


CSS='''*{box-sizing:border-box}body{margin:0;background:#edf2f6;color:#173044;font:14px system-ui}main{max-width:1800px;margin:auto;padding:18px}h1{margin:0 0 7px;font-size:26px}.intro{background:#fff;border:1px solid #cbd9e3;border-radius:10px;padding:16px 20px;line-height:1.5}.intro p{margin:7px 0}.tools{position:sticky;top:0;z-index:5;display:flex;gap:8px;align-items:center;flex-wrap:wrap;background:#edf2f6;padding:10px 0}input,select{border:1px solid #afc4d5;border-radius:6px;padding:9px;font:inherit;background:#fff}input{min-width:250px;flex:1}.wrap{overflow:auto;background:#fff;border:1px solid #cbd9e3;border-radius:9px}table{width:100%;min-width:1500px;border-collapse:collapse}th,td{border-bottom:1px solid #dae4eb;padding:8px 9px;vertical-align:top;text-align:left}th{background:#e5edf3;position:sticky;top:0;z-index:2}td:nth-child(2){min-width:320px}td:nth-child(3),td:nth-child(5),td:nth-child(10){white-space:nowrap}td:nth-child(4){min-width:155px}td:nth-child(6){font-weight:700;text-align:right;white-space:nowrap}.cad{width:145px;height:155px;object-fit:contain;background:#fff;border:1px solid #d9e4ec}.muted{color:#718495}.status{display:block;color:#20643c;font-weight:650;max-width:235px}small{display:block;line-height:1.35;margin-top:4px;color:#536879;max-width:350px}.source-details{max-width:350px;margin-top:7px;color:#536879}.source-details summary{cursor:pointer;color:#075e9f;font-weight:600}.source-details ul{padding-left:18px;margin:6px 0}.source-details li{margin:3px 0;overflow-wrap:anywhere}a{color:#075e9f}footer{padding:14px 0;color:#536879}#more{display:block;margin:14px auto;padding:9px 18px;border:1px solid #afc4d5;border-radius:6px;background:#fff;color:#075e9f;cursor:pointer}#more[hidden]{display:none}@media(max-width:700px){main{padding:8px}h1{font-size:20px}}'''

HTML='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bảng giá Mitsubishi · CAD gốc</title><style>__CSS__</style><main><section class="intro"><h1>Bảng giá Mitsubishi · CAD thiết bị từ bản vẽ gốc</h1><p>Tên hàng, thông số và giá lấy từ <a href="source/Mitsubishi_2026_DGP.pdf">bảng giá Mitsubishi 2026</a>. Hình, DWG và DXF xuất từ các block vùng D04: giữ thiết bị, đầu cực và chữ bên trong; chỉ bỏ title ngoài block.</p><p>Các mức In cùng mã, số cực, cấu hình và giá được gộp vào một dòng như bảng LS. Mô tả và mã vật tư theo từng mức In được hiển thị ngay trong ô tên hàng; giá hoặc cấu hình khác vẫn tách dòng. Dòng 1P+N không dùng hình 1P nếu CAD chưa thể hiện cực N.</p><p><a href="cad_gallery.html">17 CAD nguồn · trạng thái theo từng thiết bị</a> · <a href="price_grouped.json">Dữ liệu đã gộp</a> · <a href="price_with_cad.json">Dòng PDF gốc</a> · <a href="../LS_D02_DU_LIEU_MOI/index.html">Bảng LS</a></p></section><div class="tools"><input id="q" placeholder="Tìm mã, dòng A, loại thiết bị..."><select id="page"><option value="">Mọi trang PDF</option></select><select id="cat"><option value="">Mọi nhóm</option></select><select id="state"><option value="">Tất cả dòng giá</option><option value="matched" selected>Có CAD</option><option value="unmatched">Chưa ghép CAD</option></select><span id="count"></span></div><div class="wrap"><table><thead><tr><th>STT</th><th>Tên hàng theo PDF</th><th>Số cực</th><th>In (A)</th><th>Icu (kA)</th><th>Giá theo PDF (VNĐ)</th><th>CAD nguyên bản</th><th>Kích thước ghi trong CAD</th><th>Đối chiếu CAD</th><th>Trang PDF</th></tr></thead><tbody id="body"></tbody></table></div><button id="more" type="button">Xem thêm 100 dòng</button><footer>“—” ở cột Icu hoặc kích thước nghĩa là chưa xác nhận được giá trị trong nguồn; không suy đoán theo khung CAD. Ô CAD trống khi chưa có bằng chứng ghép đúng.</footer></main><script>__JS__</script></html>'''

JS='''const rows=__DATA__, rawCount=__RAWCOUNT__;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const q=document.querySelector('#q'),pg=document.querySelector('#page'),cat=document.querySelector('#cat'),st=document.querySelector('#state'),more=document.querySelector('#more');
for(const p of [...new Set(rows.map(r=>r.page))])pg.insertAdjacentHTML('beforeend',`<option value="${p}">Trang ${p}</option>`);
for(const c of [...new Set(rows.map(r=>r.category))])cat.insertAdjacentHTML('beforeend',`<option>${esc(c)}</option>`);
let limit=100;
function details(r){
  if(r.row_count===1)return r.material_code?`<small>Mã vật tư: ${esc(r.material_code)}</small>`:'';
  return `<details class="source-details" open><summary>Mã vật tư theo từng In (${r.row_count} mức)</summary><ul>${r.source_variants.map(v=>`<li>${esc(v.current_a_pdf?v.current_a_pdf+'A':'—')} → ${esc(v.material_code||'Chưa có mã')}</li>`).join('')}</ul></details>`;
}
function render(){
  const query=q.value.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();
  const list=rows.filter(r=>(!pg.value||r.page==pg.value)&&(!cat.value||r.category===cat.value)&&(!st.value||(st.value==='matched'&&r.cad_dwg)||(st.value==='unmatched'&&!r.cad_dwg))&&[r.search_text,r.current_display,r.spec_group,r.category].join(' ').normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase().includes(query));
  document.querySelector('#count').textContent=`${list.length} / ${rows.length} dòng hiển thị · ${rawCount} dòng PDF`;
  more.hidden=list.length<=limit;
  document.querySelector('#body').innerHTML=list.slice(0,limit).map(r=>`<tr><td>${r.display_id}</td><td><strong>${esc(r.model||r.description_display||'—')}</strong><small>${esc(r.product_description)}</small>${r.spec_source_url?`<small><a href="${esc(r.spec_source_url)}" target="_blank" rel="noopener">Thông số hãng để đối chiếu</a> · ${esc(r.spec_source_note)}</small>`:''}${details(r)}</td><td>${esc(r.pole_display||'—')}</td><td>${esc(r.current_display||'—')}</td><td>—</td><td>${Number(r.price_vnd).toLocaleString('vi-VN')}</td><td>${r.cad_dwg?`<a href="${r.cad_preview}" target="_blank"><img class="cad" loading="lazy" src="${r.cad_preview}" alt="CAD ${esc(r.model)}"></a><small><a href="${r.cad_dwg}" download>DWG</a> · <a href="${r.cad_dxf}" download>DXF</a> · <a href="cad_gallery.html?state=${encodeURIComponent(r.cad_state_id)}#${r.cad_source_id}">Các góc nhìn</a></small>`:'<span class="muted">Chưa xác định</span>'}</td><td>—</td><td>${r.cad_dwg?`<span class="status">${esc(r.cad_basis)}</span><small>${esc(r.cad_option)}</small>`:'<span class="muted">Chưa có block đúng để ghép</span>'}</td><td>${r.page}</td></tr>`).join('');
}
for(const el of [q,pg,cat,st])el.addEventListener(el===q?'input':'change',()=>{limit=100;render()});
more.onclick=()=>{limit+=100;render()};render();'''


def render(base, rows, manifest, views):
    grouped=write_grouped(base,rows)
    data=json.dumps(grouped,ensure_ascii=False).replace('</','<\\/')
    js=JS.replace('__DATA__',data).replace('__RAWCOUNT__',str(len(rows)))
    css=CSS.replace('.source-details ul{padding-left:18px;margin:6px 0}.source-details li{margin:3px 0;overflow-wrap:anywhere}',
                    '.source-details ul{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:3px 8px;list-style:none;padding:0;margin:6px 0}.source-details li{font-size:12px;overflow-wrap:anywhere}')
    page=HTML.replace('__CSS__',css).replace('__JS__',js)
    page=page.replace('Bảng LS</a></p></section>',
                      'Bảng LS</a> · <a href="../SCHNEIDER_D01_DU_LIEU_MOI/index.html">Bảng Schneider 2026</a> · <a href="../ABB_D03_DU_LIEU_MOI/index.html">Bảng ABB 2026</a> · <a href="../SHIHLIN_D06_DU_LIEU_MOI/index.html">Bảng Shihlin 2026</a> · <a href="../OSUNG_D05_DU_LIEU_MOI/index.html">Bảng O-Sung 2026</a></p></section>')
    page=page.replace('Bảng O-Sung 2026</a></p></section>',
                      'Bảng O-Sung 2026</a> · <a href="../index_2026.html">Tất cả hãng</a></p></section>')
    page=page.replace('Tất cả hãng</a></p></section>',
                      'Tất cả hãng</a> · <a href="../THIET_BI_KHAC_2026/index.html">Bảng thiết bị khác</a></p></section>')
    (base/'index.html').write_text(page,encoding='utf8')
    render_views(base,manifest,views)

