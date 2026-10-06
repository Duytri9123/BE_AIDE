"""Write the offline browser, merged catalog records and structural verification."""
from build_tudien_v2 import *
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

def run():
    catalog=load(OUT/'catalog.json');assets=catalog['cad_assets'];index={a['id']:a for a in assets}
    # Keep an annotated source counterpart beside each clean insertion drawing.
    for a in assets:
        ev=a['evidence']
        if ev['origin']=='Tudien':source=OLD/'geometry'/ev['source_profile_id']/'cad.dxf'
        elif ev['origin']=='FOMTU':source=DATA/'cabinet_templates/formtu'/(ev['source_sheet']+'.dxf')
        else:source=Path(ev['original_filename'])
        target=(OUT/a['cad']).with_name('ban_ve_nguon.dxf')
        if not target.exists():shutil.copyfile(source,target)
        a['reference_cad']=target.relative_to(OUT).as_posix()
        a['reference_note']='Bản nguồn có chữ/kích thước; dùng cad.dxf cho hình học thành phần đã tách.'
        save(OUT/a['metadata'],a)
    active_metadata={(OUT/a['metadata']).resolve() for a in assets}
    archived=[]
    for kind in ['form_tu','thiet_bi','phu_kien']:
        for path in list((OUT/kind).rglob('metadata.json')):
            if path.resolve() in active_metadata:continue
            old_folder=path.parent.resolve()
            destination=(OUT/'cho_doi_chieu/ban_xuat_truoc'/old_folder.relative_to(OUT.resolve())).resolve()
            if not old_folder.is_relative_to(OUT.resolve()) or not destination.is_relative_to(OUT.resolve()):
                raise ValueError('Archive outside new library')
            if destination.exists():raise ValueError('Archive already exists: '+str(destination))
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.move(str(old_folder),str(destination));archived.append(str(destination.relative_to(OUT.resolve())))
    save(OUT/'cho_doi_chieu/ban_xuat_truoc.json',archived)
    accessory_catalog=load(DATA/'catalog_accessories.json');accessory_products=[]
    for category,group in accessory_catalog.items():
        if not isinstance(group,dict):continue
        for row in group.get('items',[]):
            accessory_products.append({'id':'accessory_'+str(row['id']),'name':row['name'],'manufacturer':'chua_xac_dinh',
                                       'category':category,'specifications':row,'source':'nguon/catalog_accessories_goc.json',
                                       'cad_links':[],'cad_status':'unverified_matching_not_invented'})
    catalog['accessory_products']=accessory_products
    for sku in catalog['products']:
        file=OUT/'san_pham'/slug(sku['manufacturer'])/slug(sku['series'])/(slug(sku['sku'])+'__'+sku['id']+'.json')
        sku['metadata']=file.relative_to(OUT).as_posix();save(file,sku)
    for item in catalog['quotation_products']:
        item['name']=item['description'];item['cad_links']=[]
        for gid in item.get('candidate_geometry_profile_ids',[]):
            a=index.get('td_'+gid)
            if a:item['cad_links'].append({'asset_id':a['id'],'cad':a['cad'],'preview':a['preview'],'status':'quotation_family_candidate_not_verified'})
    save(OUT/'catalog.json',catalog)
    save(OUT/'san_pham/phu_kien_catalog.json',accessory_products)
    save(OUT/'cho_doi_chieu/sai_lech_geometry_nguon.json',load(OLD/'validation.json')['geometry_transform_bound_differences'])
    errors=[];warnings=[];checked=0
    if len(index)!=len(assets):errors.append({'error':'duplicate_asset_ids'})
    for a in assets:
        for field in ['cad','preview','metadata','reference_cad']:
            path=(OUT/a[field]).resolve()
            if not path.is_relative_to(OUT.resolve()) or not path.is_file() or path.stat().st_size==0:
                errors.append({'asset':a['id'],'missing_or_unsafe_path':a[field]})
        try:
            doc=ezdxf.readfile(OUT/a['cad'])
            entities=list(doc.modelspace())
            if not entities:errors.append({'asset':a['id'],'error':'empty_cad'})
            bad=[e.dxftype() for e in entities if e.dxftype() in ['INSERT','TEXT','MTEXT','DIMENSION','ATTRIB','ATTDEF','OLE2FRAME','ACAD_TABLE']]
            if bad:errors.append({'asset':a['id'],'forbidden_entities':dict(collections.Counter(bad))})
            report=doc.audit()
            if report.errors:errors.append({'asset':a['id'],'dxf_audit_errors':[str(e) for e in report.errors]})
            if report.fixes:warnings.append({'asset':a['id'],'dxf_audit_fixes':len(report.fixes)})
            ET.parse(OUT/a['preview'])
            if a['kind']=='form_tu' and (a.get('contains_electrical_equipment') is not False or not a.get('visual_review')):
                errors.append({'asset':a['id'],'error':'shell_not_reviewed_empty'})
            checked+=1
        except Exception as exc:errors.append({'asset':a['id'],'error':str(exc)})
        if checked%300==0:print('Verified DXF/SVG',checked,flush=True)
    original=load(DATA/'catalog_data.json')
    if len(catalog['products'])!=len(original):errors.append({'error':'catalog_rows_lost'})
    for item in catalog['products']:
        source=original[item['source_catalog_record']]
        expected={k:v for k,v in source.items() if k not in ('ma','n','brand','brand_display','series','t')}
        if item['specifications']!=expected or item['sku']!=source['ma']:
            errors.append({'sku':item['id'],'error':'source_catalog_values_changed'})
        for link in item['cad_links']:
            asset=index.get(link['asset_id'])
            if not asset or asset['kind']!='thiet_bi' or asset['manufacturer']!=item['manufacturer']:
                errors.append({'sku':item['id'],'error':'invalid_cad_link'})
            if link.get('approved_for_manufacture'):
                errors.append({'sku':item['id'],'error':'unapproved_automatic_certification'})
    source_exclusions=load(OUT/'cho_doi_chieu/loi_xuat.json')
    validation={'checked_at':datetime.now(timezone.utc).isoformat(),'cad_files_checked':checked,'svg_files_checked':checked,
                'catalog_products_preserved':len(original),'empty_shell_assets_reviewed':len(catalog['forms']),
                'errors':errors,'audit_warnings':warnings,'source_export_exclusions':source_exclusions,
                'scope':'All exported DXFs reopened, audited, checked nonempty and free of drawing titles/text/dimensions/nested INSERTs. SVG XML and local links checked. All promoted shell assets visually reviewed; device SKU/manufacturer dimensions are not certified by this audit.'}
    save(OUT/'validation.json',validation)
    summary=load(OUT/'summary.json');summary['accessory_catalog_records']=len(accessory_products)
    summary['validation_errors']=len(errors);save(OUT/'summary.json',summary)
    browser_assets=[{k:v for k,v in a.items() if k not in ['evidence']} for a in assets]
    db={'summary':summary,'assets':browser_assets,'products':catalog['products'],'quotation_products':catalog['quotation_products'],
        'accessory_products':accessory_products}
    page=Path(__file__).with_name('tudien_v2_browser.html').read_text(encoding='utf8')
    (OUT/'index.html').write_text(page.replace('__DATA__',json.dumps(db,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')),encoding='utf8')
    report=f'''# Thư viện tủ điện phiên bản 2

Mở `index.html` để xem trực tiếp hình CAD, lọc theo loại/hãng, tải DXF và đọc metadata. `catalog.json` là catalog tổng mới, không thay thế tự động dữ liệu đang dùng của website.

## Định nghĩa form tủ

Form tủ là **vỏ/khung tủ trống, không có thiết bị điện bên trong**. Giữ cánh, tấm lưng, tấm panel, lỗ khoét và cơ khí gắn vỏ (bản lề, khóa, gá, tai treo). Khung tên, bản vẽ bố trí đã lắp và toàn bộ sheet không được coi là form tủ.

Đã xem trực tiếp và đưa vào thư viện {summary['empty_shell_multi_view_sets']} bộ vỏ nhiều mặt và {summary['empty_shell_other_view_assets']} mục mặt vỏ riêng. Các bản FOMTU khác còn ở `cho_doi_chieu/formtu_sheets_chua_xac_nhan_vo_trong.json`; không tự nâng toàn bộ 339 sheet thành 339 vỏ tủ. Kích thước H×W×D của FOMTU được lấy từ thuộc tính khung tên, có ghi rõ nguồn, chưa phải phép đo/chứng nhận độc lập.

## Số liệu

- {summary['cad_assets']} mục CAD thực, gồm {summary['by_kind'].get('thiet_bi',0)} thiết bị, {summary['by_kind'].get('phu_kien',0)} phụ kiện và {summary['by_kind'].get('form_tu',0)} bộ/mặt vỏ.
- Giữ đủ {len(original)} mục `catalog_data.json`, {len(catalog['quotation_products'])} mục trích từ báo giá và {len(accessory_products)} thông tin phụ kiện.
- {summary['products_with_reference_cad']} mục catalog có liên kết CAD tham khảo theo mã/series và hãng; {summary['products_without_cad']} mục chưa có CAD phù hợp trong nguồn. Liên kết này không xác nhận mọi định mức dùng chung housing.
- {checked} DXF và SVG đã kiểm tra; {len(errors)} lỗi cấu trúc/tham chiếu. {len(source_exclusions)} mục nguồn không xuất được geometry thực, được ghi rõ trong `validation.json`.

## Cấu trúc

```text
catalog.json                         # Catalog tổng có thông tin và liên kết CAD
index.html                           # Xem hình/tìm kiếm offline
form_tu/<loai>/<hang>/<mau>/           # Vỏ tủ trống
thiet_bi/<loai>/<hang>/<mau>/          # CAD thiết bị
phu_kien/<vi_tri>/<loai>/<hang>/<mau>/  # CAD phụ kiện
    cad.dxf                          # Hình học riêng, đã bỏ annotation và block lồng
    ban_ve_nguon.dxf                  # Bản đối chiếu có chữ/kích thước nguồn
    preview.svg                      # Xem hình
    metadata.json                    # Thông tin, nguồn và liên kết SKU
    geometry_report.json             # Bao hình/đơn vị/phép dịch tọa độ
san_pham/<hang>/<series>/<sku>.json    # Thông số catalog; tham chiếu CAD dùng chung
bo_tri_da_lap/index.json              # Bố trí nguồn có thiết bị; không phải form trống
nguon/                               # Snapshot catalog và kiểm kê nguồn
cho_doi_chieu/                        # Mã thiếu CAD, đối tượng chưa phân loại, sai lệch
validation.json                      # Kết quả kiểm tra
```

CAD thiết bị/phụ kiện được tách từ hình nguồn, không vẽ hình chữ nhật giả và không nhân bản theo từng dòng điện. Một bản vẽ có thể được nhiều SKU tham chiếu. Mục chưa nhận dạng, đối tượng chú thích và profile động cũ được kiểm kê riêng, không đưa vào danh sách CAD thiết bị đang dùng.

## Các trường cần phân biệt

- `products[].specifications`: thông số gốc, gồm kích thước/định mức/giá và cờ xác minh của catalog cũ. Không nâng trạng thái xác minh.
- `cad_assets[].geometry.drawing_extent`: bao hình CAD sau bỏ chữ/kích thước; không phải kích thước sản phẩm hoặc kích thước tủ H×W×D.
- `cad_links[].evidence`: căn cứ ghép bản vẽ. `approved_for_manufacture=false` khi mới đối chiếu mã/series.
- `evidence.brand_basis`: hãng lấy từ tên/chữ trong hình hoặc mã model duy nhất trong catalog; không lấy hãng từ tên file @LS/@CHINT.
- `bo_tri_da_lap[].parts[].source_transform`: đã bù phần dịch về gốc của CAD mới. Những sai lệch bao hình trước đó vẫn được giữ để đối chiếu nguồn.

Các thư viện cũ và cơ sở dữ liệu ứng dụng không bị ghi đè. Nguồn Tudien thực tế: `{ROOT.parent / 'Tudien'}`. Không có file tên đúng `catalog.json` trong dự án lúc bắt đầu; catalog gốc đang dùng là `data/catalog_data.json`.

## Tái tạo

Chạy `scripts/build_tudien_v2.py`, sau đó `scripts/publish_tudien_v2.py` bằng Python có ezdxf và các thư viện trong `tmp/tudien_deps`. Danh sách form đã duyệt nằm ở `scripts/tudien_v2_reviewed_forms.json`.
'''
    (OUT/'README.md').write_text(report,encoding='utf8')
    print(json.dumps({'summary':summary,'validation_errors':errors,'audit_warnings':len(warnings)},ensure_ascii=False,indent=2),flush=True)
    return bool(errors)

if __name__=='__main__':raise SystemExit(run())
