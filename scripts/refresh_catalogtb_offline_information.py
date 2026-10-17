"""Refresh the actual CatalogTB/index.html, including price-free information.

The standalone file uses embedded data and relative CAD links so it works when
opened directly from Windows Explorer. No backend or price lookup is required.
"""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import quote,unquote

ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'data/CatalogTB'
BEGIN='// BEGIN PUBLISHED DEVICE INFORMATION'
END='// END PUBLISHED DEVICE INFORMATION'
JAVASCRIPT=r'''
// BEGIN PUBLISHED DEVICE INFORMATION
function renderOriginalCatalogRows(item){
 const host=node('div');const rows=item.catalog_information||[];
 host.append(node('h4','','Danh mục mã và thông số từ bảng giá / catalog'));
 host.append(node('p','muted',rows.length+' mã / cấu hình. Giữ thông tin gốc; giá có thể để trống. Các dòng tham khảo chưa xác nhận mã của CAD.'));
 const books=new Map();for(const row of rows){if(!books.has(row.book_key))books.set(row.book_key,[]);books.get(row.book_key).push(row)}
 for(const entries of books.values()){
  const first=entries[0];host.append(node('p','',first.brand+' · '+(first.group||'Catalog')+(first.edition?' · '+first.edition:'')));
  const wrap=node('div','selection-wrap'),table=node('table','selection'),head=node('tr');
  for(const title of ['Mã hàng',...first.columns,...(first.columns.some(c=>/^(đơn\s*giá|giá|price)/i.test(c))?[]:['Giá'])])head.append(node('th','',title));table.append(head);
  for(const row of entries){const tr=node('tr'),code=node('td');code.append(node('strong','',row.sku||row.item_name));
   if(/^https?:\/\//.test(row.source_url||'')){const a=link('Nguồn ↗',row.source_url);a.target='_blank';a.rel='noopener noreferrer';code.append(node('br'),a)}tr.append(code);
   const price=typeof row.price==='number'?new Intl.NumberFormat('vi-VN').format(row.price)+' ₫':'—';
   for(let i=0;i<first.columns.length;i++)tr.append(node('td','',/^(đơn\s*giá|giá|price)/i.test(first.columns[i])?price:row.cells[i]??'—'));
   if(!first.columns.some(c=>/^(đơn\s*giá|giá|price)/i.test(c)))tr.append(node('td','',price));table.append(tr);
  }wrap.append(table);host.append(wrap);
 }return host;
}
function renderCatalogInformation(item){
 const part=section('Bảng thông tin thiết bị');
 part.append(renderOriginalCatalogRows(item));
 if(item.visual_candidates?.length){
  part.append(node('h4','','Đối chiếu theo hình ảnh CAD'));
  part.append(node('p','muted','Các mẫu có nét vẽ tương tự; chưa xác nhận mã của thiết bị đang xem. Một hình có thể dùng chung cho nhiều mã.'));
  for(const candidate of item.visual_candidates){
   const image=node('img');image.src=candidate.comparison_preview;image.alt=candidate.comparison_name;image.style.cssText='width:240px;height:160px;object-fit:contain;background:#222a31';part.append(image);
   part.append(node('p','',candidate.comparison_name));
   part.append(node('p','muted','Mã trên mẫu đối chiếu: '+candidate.models.map(m=>m.brand+' '+m.model).join(' · ')));
   for(const [n,document] of candidate.documents.entries()){if(!/^https?:\/\//.test(document.url))continue;const a=link('Nguồn '+(n+1)+(document.page?' · trang '+document.page:'')+' ↗',document.url);a.target='_blank';a.rel='noopener noreferrer';part.append(a,node('br'))}
  }
 }
 const research=item.catalog_references?.research;
 if(research){const labels={source_geometry_without_model_label:'Chưa tìm thấy nhãn mã trong CAD · đã rà soát nguồn',source_labels_need_catalog:'Đã đọc được nhãn nguồn · đang đối chiếu tài liệu hãng',source_text_without_unique_model:'CAD có chữ nhưng chưa có mã nhận diện duy nhất',source_label_conflict:'Nhãn CAD mâu thuẫn với cấu hình hình vẽ · cần đối chiếu',documented_source_label:'Nhãn mã CAD đã đối chiếu tài liệu sản phẩm',documented_source_model:'Mã nguồn đã đối chiếu tài liệu hãng',source_model_requires_catalog_check:'Có mã nguồn; cần đối chiếu cấu hình catalog',source_family_candidates:'Đã tìm được các cấu hình cùng dòng',requires_source_identification:'Có catalog tham khảo; chưa xác định mã CAD nguồn',generic_mechanical:'Chi tiết cơ khí; tra theo quy cách bản vẽ',drawing_or_assembly:'Bản vẽ lắp đặt hoặc cụm thiết bị'};part.append(node('p','muted',(labels[research.status]||'Đang bổ sung thông tin')+' · Cập nhật '+research.checked_at))}
 part.append(node('p','muted','Tên hàng, mã và thông số từ catalog tham khảo. Một CAD có thể dùng cho nhiều mã/hãng; giá để ---.'));
 const options=item.catalog_references?.options||[];
 if(!options.length){part.append(node('p','','Thông tin theo bản vẽ nguồn: '+item.display));return part}
 const wrap=node('div','selection-wrap'),table=node('table','selection');table.style.width='100%';
 const header=node('tr');for(const title of ['Hãng','Tên / mã hàng','Thông tin thiết bị','Giá'])header.append(node('th','',title));table.append(header);
 for(const option of options){
  const row=node('tr');row.append(node('td','',option.brand));
  const model=node('td');model.append(node('strong','',option.model));
  if(option.source_url){let url=option.source_url;if(url.startsWith('/device-catalog/'))url='http://127.0.0.1:8000/api/v1'+url;
   if(/^https?:\/\//.test(url)){const source=link('Tài liệu hãng ↗',url);source.target='_blank';source.rel='noopener noreferrer';model.append(node('br'),source)}}
  row.append(model);const specs=node('td');
  for(const [key,value] of Object.entries(option.specifications||{})){
   if(value==null||value==='')continue;
   specs.append(node('div','',key.replace(/_/g,' ')+': '+(typeof value==='object'?JSON.stringify(value):value)));
  }
  if(option.basis==='catalog_series_reference')specs.append(node('small','',option.note));
  row.append(specs,node('td','','---'));table.append(row);
 }
 wrap.append(table);part.append(wrap);return part;
}
// END PUBLISHED DEVICE INFORMATION
'''.replace(r'\/\/',r'\/\/')


def refresh_from_snapshot(snapshot):
    from app.services.library_catalog_information import information_rows
    from app.services.customer_equipment_information import customer_device,customer_information_rows
    target=CAT/'index.html';html=target.read_text(encoding='utf-8-sig')
    pattern=r'(<script id="catalog-data" type="application/json">)(.*?)(</script>)'
    match=re.search(pattern,html,re.S)
    if not match:raise ValueError('Offline library data block missing')
    old=json.loads(match[2]);records={}
    for path in CAT.rglob('thong_tin_thiet_bi.json'):
        relative=path.relative_to(CAT).as_posix()
        cid='TB-'+hashlib.sha1(relative.encode()).hexdigest()[:16]
        records[cid]=(path,json.loads(path.read_text(encoding='utf-8-sig')))
    profiles=[]
    visual_assets={v['id_hinh_goc']:quote((path.parent/v['duong_dan']).with_name('xem_truoc.svg').relative_to(CAT).as_posix(),safe='/')
                   for path,raw in records.values() for v in raw.get('cad_don',[])}
    for item in snapshot['items']:
        members=item.get('member_profile_ids') or [item['id']]
        sources=[records[cid] for cid in members if cid in records]
        if not sources:raise ValueError('No source for offline device '+item['id'])
        canonical=sources[0][0]
        views=[]
        for view in item['views']:
            candidates=[(path,entry) for path,raw in sources for entry in raw.get('cad_don',[]) if entry['id_hinh_goc']==view['id']]
            if not candidates:
                candidates=[(path,entry) for path,raw in records.values() for entry in raw.get('cad_don',[]) if entry['id_hinh_goc']==view['id']]
            if not candidates:raise ValueError('No source for offline view '+view['id'])
            path,entry=candidates[0];drawing=path.parent/entry['duong_dan']
            preview=drawing.with_name('xem_truoc.svg')
            metadata=drawing.with_name('thong_tin_cad_chen.json')
            if not drawing.is_file() or not preview.is_file():raise FileNotFoundError(str(drawing))
            url=lambda p:quote(p.relative_to(CAT).as_posix(),safe='/')
            views.append(dict(source_id=view['id'],face=view['face'],label=view['label'],
                              dxf=url(drawing),preview=url(preview),json=url(metadata if metadata.is_file() else path),
                              placement=entry.get('bo_tri_trong_tu') or {}))
        profile={**item,'catalog_information':information_rows(item),'name':item['display'],'json':quote(canonical.relative_to(CAT).as_posix(),safe='/'),
                 'single_views':views,'primary':next((v for v in views if v['source_id']==item['primary_view']),views[0]),'drawings':[]}
        profile['visual_candidates']=[{**c,'comparison_preview':visual_assets[c['comparison_view']]}
                                      for c in item.get('visual_candidates',[]) if c['comparison_view'] in visual_assets]
        # Apply the same customer allowlist as the website API. Relative CAD
        # assets remain local; internal JSON/evidence links are never rendered.
        public=customer_device(profile)
        public.update(name=public['display'],single_views=profile['single_views'],primary=profile['primary'],drawings=[],
                      catalog_information=customer_information_rows(profile['catalog_information'],item))
        profiles.append(public)
    categories=[dict(name=c['name'],profiles=c['count'],records=c['count']) for c in snapshot['categories']]
    form=next((c for c in old['categories'] if c['name']=='Form tủ'),None)
    if form:
        categories=[form if c['name']=='Form tủ' else c for c in categories]
    data={**old,'categories':categories,'profiles':profiles,'information_version':'2026-10-16'}
    payload=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    html=html[:match.start(2)]+payload+html[match.end(2):]
    html=re.sub(re.escape(BEGIN)+r'.*?'+re.escape(END),'',html,flags=re.S)
    anchor='function renderDetail(item)'
    if anchor not in html:raise ValueError('Offline detail renderer missing')
    html=html.replace(anchor,JAVASCRIPT+'\n'+anchor,1)
    html=html.replace("host.append(link('Xem JSON thiết bị',item.json))",'')
    html=html.replace(",link('Tọa độ và kích thước',view.json)",'')
    # Search manufacturer model choices as well as the original drawing label.
    old_search="...(p.search_aliases||[])].join(' ')"
    new_search="...(p.search_aliases||[]),...(p.catalog_references?.options||[]).map(o=>[o.brand,o.model,JSON.stringify(o.specifications||{})].join(' '))].join(' ')"
    html=html.replace(old_search,new_search)
    offline_filter=r'''function filtered(){const terms=$('search').value.trim().split(/\s+/).map(searchKey).filter(Boolean);return data.profiles.filter(p=>{if(p.category!==state.category)return false;const text=[p.name,p.display,p.brand,p.folder,p.type,p.product_code,...(p.search_aliases||[]),...(p.catalog_references?.options||[]).map(o=>[o.brand,o.model].join(' '))].join(' ').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d');const words=(text.match(/[a-z0-9]+(?:[-_/][a-z0-9]+)*/g)||[]).map(searchKey);return terms.every(t=>/\d/.test(t)?words.some(w=>w===t||(w.startsWith(t)&&/\d$/.test(t)&&/^[a-z]/.test(w.slice(t.length)))):text.includes(t))})}'''
    html=re.sub(r'^function filtered\(\).*$',lambda _:offline_filter,html,flags=re.M)
    injection='host.append(chips);host.append(renderCatalogInformation(item));'
    if injection not in html:
        html=html.replace('host.append(chips);',injection,1)
    target.write_text(html,encoding='utf8')
    print('Offline library refreshed:',len(profiles),'devices;',sum(len(p['single_views']) for p in profiles),'CAD views; information tables:',sum(bool(p['catalog_references'].get('options')) for p in profiles))


def main():
    from app.services.catalogtb_browser import _build_browser_data
    refresh_from_snapshot(_build_browser_data())


if __name__=='__main__':main()
