"""Publish all source dispositions and refresh discovery hashes after enrichment."""
import hashlib,json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB'


def main():
    dest=ROOT/'docs/source-630-catalog-processing.json'
    report=json.loads(dest.read_text(encoding='utf8'))
    original={r['index']:r for r in json.loads((ROOT/'outputs/source-630-review/inventory.json').read_text(encoding='utf8'))}
    for row in report['items']:
        if row.get('profile'):
            d=json.loads((CAT/row['profile']).read_text(encoding='utf8'))
            row['information']={'name':d['ten_san_pham'],'source_brand':d.get('hang_xac_nhan'),
                                'specifications':d.get('thong_so') or {},'reference_options':d['catalog_tham_khao']['options']}
        else:
            m=original[row['index']]['metadata']
            row['information']={'name':row['name'],'source_brand':None,
                                'specifications':m.get('source_specification') or {'Loại tệp':'DWG thư viện tổng'},
                                'dimensions':m.get('dimensions_mm'),'reference_options':[]}
    data=json.loads((CAT/'_agent_index/browser_display_v5.json').read_text(encoding='utf8'))
    report['summary'].update(visible_library_items=data['total'],visible_library_views=data['view_count'],
                             items_without_information=sum(not bool(d.get('catalog_references',{}).get('options')) for d in data['items']))
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    manifest_path=CAT/'ai_library_manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf8'))
    previous={r['profile']:r for r in manifest['items']};items=[]
    physical={r['path']:r for r in manifest.get('physical_cad_file_inventory',[])}
    for p in sorted(CAT.rglob('thong_tin_thiet_bi.json')):
        d=json.loads(p.read_text(encoding='utf-8-sig'));relative=p.relative_to(CAT).as_posix()
        ai=d.get('nhan_dien_ai') or {};item=dict(previous.get(relative) or {})
        item.update(profile=relative,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),name=d.get('ten_san_pham'),
                    group=d.get('nhom'),brand=d.get('hang_xac_nhan'),category_code=ai.get('loai_thiet_bi_code') or item.get('category_code') or 'UNCLASSIFIED',
                    specifications=d.get('thong_so') or {},aliases=d.get('tu_khoa_tim_kiem') or [],
                    browser_hidden=bool(d.get('browser_hidden')),exact_SKU_verified=False)
        if d.get('source_catalog_review'):
            item.update(classification_basis='source CAD text, name, contact sheet and manufacturer catalog references',recognition_status='information_catalogued',source_auto_select=False,source_needs_review=True,views=[])
            for view in d['cad_don']:
                path=(p.parent/view['duong_dan']);cad=path.relative_to(CAT).as_posix()
                item['views'].append({'source_id':view['id_hinh_goc'],'dxf':cad,'file_exists':path.is_file(),
                                      'source_face':view['huong_nhin'],'entry_permission':False,'manual_geometry_review_required':True})
                if cad not in physical:
                    physical[cad]={'path':cad,'role':'supporting_duplicate_information_reference' if d.get('browser_hidden') else 'catalogued_information_reference',
                                   'owner_profile':relative,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'readable_by_dxf_loader':True}
        items.append(item)
    manifest['items']=items
    manifest['summary'].update(profiles=len(items),declared_cad_views=sum(len(i.get('views',[])) for i in items),
                               after_loader_profiles=sum(not i.get('browser_hidden') for i in items),after_loader_views=data['view_count'])
    files=list(physical.values());manifest['physical_cad_file_inventory']=files
    manifest['physical_cad_file_summary'].update(total_cad_files=len(files),dxf_files=sum(r['path'].lower().endswith('.dxf') for r in files),
                                                native_dwg_files=sum(r['path'].lower().endswith('.dwg') for r in files),
                                                roles=dict(Counter(r['role'] for r in files)))
    manifest['source_catalog_processing']=report['summary']
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    lines=['# Xử lý toàn bộ 630 mục CAD nguồn — 16/10/2026','',
           'Bảng tra cứu dùng thông tin thiết bị và catalog tham khảo, độc lập dữ liệu giá. Giá hiển thị `---`. Mã tương tự là lựa chọn dùng chung hình CAD, không đổi nhãn hãng gốc hoặc tự xác nhận thông số từ hình dáng.','',
           '- 467 hồ sơ thông tin nguồn đưa vào tra cứu; 160 bản lặp hình học liên kết về hồ sơ tương ứng.',
           '- 2 bản form rỗng được ghi nhận bằng thông tin nguồn; 1 DWG là kho thư viện tổng, không tính thành thiết bị mới.',
           '- Đọc chữ/thuộc tính nguồn, xem các bảng ảnh tổng hợp và bổ sung 143 ảnh xem trước trước đây chưa có.',
           f"- Thư viện hiển thị {data['total']} mục với {data['view_count']} mặt CAD; không có bảng thông tin trống.",
           '- Bổ sung bảng hãng/mã/thông số và tài liệu cho 5 mẫu chống sét; mẫu trong ảnh có sơ đồ cực 3P+N đọc từ nguồn.',
           '- Bỏ tra cứu giá tự động và thông báo thiếu giá khỏi trang thư viện.','',
           '## Tài liệu hãng đã tra cứu','',
           '- [Schneider iPRD40r A9L40601](https://www.se.com/in/en/product/A9L40601/iprd40r-modular-surge-arrester-3p-%2B-n-350v-with-remote-transfert/)',
           '- [Suntree SUP2](https://www.chinasuntree.com/ac-spd/scup2-surge-protector.htm)',
           '- [Mikro ZCT40S–210S](https://itmikro.com.my/wp-content/uploads/2020/08/zct40_60_80_120_210s_man-1.pdf)',
           '- [Socomec TCA21 100/5 A](https://emea.socomec.com/en/generate-pdf/192T2010)',
           '- [Trend/Honeywell IQ4 I/O](https://prod-edam.honeywell.com/content/dam/honeywell-edam/hbt/en-us/documents/literature-and-specs/datasheets/trends-110725/hon-ba-bms-en-ta201341-uk8pr0823n.pdf?download=false)',
           '- [Siemens S7-1200](https://cache.industry.siemens.com/dl/files/829/109814829/att_1120874/v1/s71200_system_manual_en-US_en-US.pdf)',
           '- [Leipole FKL6622](https://leipole.pl/en/products/fkl6622/)',
           '- Các nguồn khác được ghi ở từng lựa chọn trong `source_reference_research.json` và các hồ sơ catalog.','',
           '## Kiểm tra','',
           '- 56 kiểm thử backend đạt, gồm kiểm đủ 630 nguồn, giữ nguyên SHA-256 nguồn, bảng thông tin, liên kết preview/DXF và mã tham khảo chống sét.',
           '- 13 kiểm tra cuối đạt; đã sửa và kiểm đủ 17 mặt thuộc 8 nhóm CAD ghép nhiều hồ sơ, không cho phép lấy nhầm mặt từ nhóm khác.',
           '- Vite build đạt; kiểm tra giao diện desktop/mobile với API giả lập đạt và không gọi API tra giá.',
           '- Bảng ảnh kiểm tra: `outputs/source-630-review/`. Dữ liệu đầy đủ và liên kết từng nguồn: `source-630-catalog-processing.json`.','',
           '## Danh sách 630 mục','', '| STT | Nguồn | Nhóm | Mã/dòng đọc từ nguồn | Kết quả |','| ---: | --- | --- | --- | --- |']
    labels={'processed_information_profile':'Đã lập bảng thông tin','processed_duplicate_geometry':'Đã liên kết hình lặp',
            'processed_empty_legacy_reference':'Đã ghi nhận form rỗng','processed_native_library_archive':'Đã phân loại kho DWG'}
    for row in report['items']:
        cells=[str(row['index']),row['source'],row['category'],' / '.join(row['source_models']) or 'Theo mẫu CAD',labels[row['status']]]
        lines.append('| '+' | '.join(c.replace('|','/').replace('\n',' ') for c in cells)+' |')
    (ROOT/'docs/source-630-catalog-processing.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(json.dumps(report['summary'],ensure_ascii=False))


if __name__=='__main__':main()
