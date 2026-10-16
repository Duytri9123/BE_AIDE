"""Populate reusable catalog references; never turn reference ratings into CAD facts."""
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from app.services.ai.manufacturer_registry import canonical_brand
from app.services.catalogtb_browser import _build_browser_data, _snapshot_path
from app.services.catalog_family_matching import matching_rows, information_choice, row_poles, poles

ROOT = Path(__file__).resolve().parents[1]
CAT = ROOT/'data/CatalogTB'
MORELE = 'https://vanvh.com/upload/files/BG2021morele1.pdf'
ALIASES = {
    'INDICATOR':'LIGHT', 'PILOTLAMP':'LIGHT', 'SELECTOR':'SELECTOR_SWITCH',
    'VFD':'INVERTER', 'PHASERELAY':'PHASE_RELAY', 'FUSEASSEMBLY':'FUSE_HOLDER',
    'RCD':'RCCB', 'AUXCONTACT':'AUX_CONTACT', 'THERMALRELAY':'THERMAL_RELAY',
    'POWERFACTORCONTROLLER':'POWER_FACTOR_CONTROLLER', 'POWERSUPPLY':'POWER_SUPPLY',
    'RƠLEBẢOVỆPHA':'PHASE_RELAY', 'RƠLENHIỆT':'THERMAL_RELAY',
    'QUẠTLỌCGIÓTỦĐIỆN':'FAN', 'DÃYCẦUĐẤUNHIỀUCỰCBẮTVÍT':'TERMINAL_BLOCK',
    'DÃYCẦUĐẤUBẮTVÍT':'TERMINAL_BLOCK', 'CẦUĐẤUXUYÊNDÂYMỘTTẦNGLẮPRAY':'TERMINAL_BLOCK',
    'ỔCẮMĐIỆN':'SOCKET',
    'EARTHLEAKAGERELAY':'EARTH_LEAKAGE_RELAY', 'EARTHFAULTRELAY':'EARTH_FAULT_RELAY',
    'VOLTAGERELAY':'VOLTAGE_RELAY',
}


def kind(value):
    key = re.sub(r'[\s_-]', '', str(value or '')).upper()
    return ALIASES.get(key, str(value or '').upper().replace(' ', '_'))


def choice(brand, model, specs, url='', basis='catalog_type_reference', note=''):
    return dict(brand=canonical_brand(brand), model=model or '---', specifications=specs or {},
                source_url=url or '', basis=basis, price='---', exact_cad_match=False,
                note=note or 'Mẫu tham khảo cùng loại; có thể dùng chung hình CAD để bố trí. Thông số dưới đây thuộc mã tham khảo.')


def supplemental_references(typ):
    """Manufacturer facts checked 2026-10-16; these remain layout references."""
    ndk=choice('CHINT','NDK',{'Loại':'Biến áp điều khiển một pha','Công suất lựa chọn':'25–5000 VA','Tần số':'50/60 Hz'},
               'https://www.chintglobal.com/in/en/products/low-voltage/iec/industrial-control/ndk.html')
    supply=choice('MEAN WELL','LRS-150-24',{'Đầu ra DC':'24 V','Dòng đầu ra':'6.5 A','Công suất':'156 W'},
                  'https://www.meanwell.com/Upload/PDF/LRS-150/LRS-150-SPEC.PDF')
    return {
        'ATS_CONTROLLER':[choice('SmartGen','HAT560N',{'Chức năng':'Đo và điều khiển chuyển đổi hai nguồn; đo điện áp một pha/ba pha'},
                                 'https://www.smartgen.com.cn/data/download/HAT560N_HAT560NB_en.pdf')],
        'GENERATOR_CONTROLLER':[choice('Deep Sea Electronics','DSE8610 MKII',{'Chức năng':'Điều khiển hòa đồng bộ/chia tải máy phát','Nguồn DC':'8–35 V','Kích thước W×H×D':'245 × 184 × 51 mm'},
                                       'https://www.deepseaelectronics.com/genset/load-sharing-synchronising-control-modules/dse8610-mkii')],
        'TRANSFORMER':[ndk], 'NGUỒN_VÀ_BIẾN_ÁP':[ndk,supply], 'POWER_SUPPLY':[supply],
        'TERMINAL_BLOCK':[choice('Phoenix Contact','UK 5 N / 3004362',{'Điện áp danh định':'800 V','Dòng danh định':'32 A','Tiết diện danh định':'4 mm²','Đơn vị':'Một cầu đấu; dãy trong CAD có thể ghép nhiều cầu'},
                                 'https://www.phoenixcontact.com/en-us/products/feed-through-terminal-block-uk-5-n-3004362')],
        'CUỘN_KHÁNG_BA_PHA_LÕI_THÉP':[choice('TDK / EPCOS','B44066D5050M440',{'Loại':'Cuộn kháng lọc sóng hài; chọn định mức theo datasheet của mã'},
                                             'https://product.tdk.com/de/search/capacitor/pfc/key-comp_reactor/info?part_no=B44066D5050M440')],
        'SOCKET':[choice('Schneider Electric','A9A15310',{'Loại':'Ổ cắm iPC gá ray DIN','Cực':'2P+E','Dòng':'16 A','Điện áp':'250 VAC'},
                         'https://www.se.com/uk/en/product/A9A15310/din-socket-acti9-ipc-2p%20e-16a-250vac/',
                         note='Ổ cắm ray DIN tham khảo cùng công dụng; kiểu gá và mặt ổ có thể khác CAD nguồn.')],
        'SWITCH_DISCONNECTOR':[choice('Schneider Electric','A9S65363',{'Dòng thiết bị':'Acti9 iSW','Cực':'3P','Dòng':'63 A'},
                                      'https://www.se.com/it/it/product/A9S65363/interruttore-sezionatore-isw-3p-63a/')],
    }.get(typ, [])


def main():
    paths = sorted(CAT.rglob('thong_tin_thiet_bi.json'))
    backup = ROOT/'outputs/catalog-before-reference-completion-20261016.zip'
    if not backup.exists():
        with ZipFile(backup, 'w', ZIP_DEFLATED) as z:
            for p in paths:
                z.write(p, p.relative_to(CAT).as_posix())
    # Use manufacturer/model/spec fields from source records; prices are ignored.
    pool = defaultdict(list)
    for filename in ('supplier_pricebooks.json', 'web_catalog_offers.json'):
        data = json.loads((ROOT/'app/data'/filename).read_text(encoding='utf8'))
        for r in data['items']:
            if r.get('sku') and r.get('brand'):
                pool[kind(r.get('category'))].append(r)
    all_rows = [r for rows in pool.values() for r in rows]
    rows_by_brand = defaultdict(list)
    for row in all_rows:
        rows_by_brand[canonical_brand(row['brand'])].append(row)
    fresh = _build_browser_data()['items']
    display = {}
    for d in fresh:
        for cid in d.get('member_profile_ids') or [d['id']]:
            display[cid] = d
    report = []
    for p in paths:
        raw = json.loads(p.read_text(encoding='utf-8-sig'))
        cid = 'TB-'+hashlib.sha1(p.relative_to(CAT).as_posix().encode()).hexdigest()[:16]
        d = display.get(cid) or dict(display=raw.get('ten_san_pham'),type=(raw.get('nhan_dien_ai') or {}).get('loai_thiet_bi_code'),
                                    spec=raw.get('thong_so'),product_code=raw.get('ma_dong_san_pham'),brand=raw.get('hang_xac_nhan'))
        typ = kind((raw.get('source_catalog_review') or {}).get('component_type') or d.get('type'))
        if typ=='CT' and re.search(r'\bZCT',str(raw.get('ma_dong_san_pham') or raw.get('ten_kieu') or ''),re.I):
            typ='ZCT'
        options = []
        model = d.get('product_code') or raw.get('ma_dong_san_pham')
        specs = {k:v for k,v in (d.get('spec') or raw.get('thong_so') or {}).items() if v is not None and v != ''}
        specs.setdefault('Loại thiết bị',d.get('type') or raw.get('ban_chat') or raw.get('nhom'))
        placement=raw.get('vi_tri_lap_dat') or (raw.get('bo_tri_lap_dat') or {}).get('huong_dan')
        if placement:specs.setdefault('Lắp đặt tham khảo',placement)
        source_codes=[]
        for view in raw.get('cad_don') or []:
            metadata=p.parent/'HinhChieu'/view['id_hinh_goc']/'thong_tin.json'
            if metadata.is_file():
                shape=json.loads(metadata.read_text(encoding='utf-8-sig'))
                if shape.get('ten_hinh'):source_codes.append(shape['ten_hinh'])
                dimensions=shape.get('kich_thuoc_hinh_mm') or {}
                if dimensions.get('ngang') and dimensions.get('cao'):
                    label=view.get('huong_nhin') or view['id_hinh_goc']
                    specs[f'Hình chiếu {label} (ngang × cao, mm)']=f"{dimensions['ngang']} × {dimensions['cao']}"
        if raw.get('kich_thuoc_cad_goc_mm'):
            specs['Kích thước CAD nguồn (mm)']=raw['kich_thuoc_cad_goc_mm']
        if d.get('brand') or model:
            options.append(choice(d.get('brand') or 'Chưa xác định', model or (source_codes[0] if source_codes else None), specs,
                                  d.get('manufacturer_document'), 'source_profile' if model else 'cad_reference_code',
                                  'Hãng/mã và thông số theo hồ sơ nguồn. Các mã tham khảo khác dùng chung hình CAD theo loại thiết bị.'))
        if not options:
            options.append(choice('Gia công / phổ thông' if d.get('brand_kind') == 'generic' else 'Chưa xác định',
                                  (source_codes[0] if source_codes else None) or raw.get('ten_kieu') or p.parent.name, specs,
                                  basis='cad_reference_code',
                                  note='Mã/tên mẫu CAD nguồn để tra cứu và dùng chung; chưa phải mã hàng thương mại.'))
        for variant in (raw.get('source_catalog_review') or {}).get('shared_source_variants',[]):
            for source_model in variant.get('models') or []:
                options.append(choice(variant.get('brand') or 'Chưa xác định',source_model,
                                      {'Nhãn trên CAD nguồn':variant.get('name') or source_model},
                                      basis='shared_source_model',
                                      note='Mã/hãng trong một bản CAD nguồn có cùng hình học; dùng chung mẫu hình, chọn định mức theo catalog.'))
        for opt in raw.get('lua_chon_den') or raw.get('lamp_options') or []:
            if opt.get('hang'):
                options.append(choice(opt['hang'], opt.get('ma') or opt.get('dong'),
                                      {k:v for k,v in opt.items() if k in {'mau','dien_ap','lo_lap_mm'}},
                                      opt.get('nguon') or ''))
        if typ in {'LIGHT','FUSE_HOLDER','FUSE'}:
            if typ == 'LIGHT':
                options.append(choice('Morele','AD16-22CS',{'Lỗ lắp':'Ø22 mm','Màu lựa chọn':'Đỏ / vàng / xanh','Điện áp biến thể tham khảo':'220 VAC'},MORELE,
                                      note='Dòng Morele trong tài liệu nhà cung cấp; hình CAD dùng tham khảo, chọn điện áp và màu khi dùng.'))
            elif typ == 'FUSE_HOLDER':
                options.append(choice('Morele','RT18-32',{'Loại':'Đế/vỏ cầu chì; chọn ruột cầu chì riêng'},MORELE))
            options.append(choice('Andex','---',{'Loại':d.get('display'),'Mã và định mức':'Chọn theo sản phẩm thực tế'},basis='user_shared_cad_reference',
                                  note='Hãng dùng chung mẫu CAD theo yêu cầu người dùng; chưa có mã catalog để xác nhận thông số.'))
        if typ=='BUZZER':
            options.append(choice('Morele','AD22',{'Loại':'Còi báo âm thanh','Lỗ lắp':'Ø22 mm','Điện áp tham khảo':'220 VAC'},MORELE))
        source_brand = canonical_brand(raw.get('hang_xac_nhan') or d.get('brand') or '')
        family_matches = matching_rows(raw, d, rows_by_brand.get(source_brand, []) if source_brand else all_rows, typ)
        options.extend(information_choice(row, basis) for row, basis in family_matches)
        by_brand = defaultdict(list)
        for r in pool[typ]:
            by_brand[canonical_brand(r['brand'])].append(r)
        for brand, rows in sorted(by_brand.items()):
            if family_matches:
                continue
            wanted=str(specs.get('so_cuc') or specs.get('so_cuc_chinh') or (raw.get('nhan_dien_ai') or {}).get('so_cuc') or '').upper().replace(' ','')
            if re.fullmatch(r'[1-4]',wanted):wanted+='P'
            if re.fullmatch(r'[1-4]P(?:\+N)?',wanted):
                rows=[r for r in rows if row_poles(r) in {None,wanted}]
                if not rows:continue
            # Prefer matching source families, and explicit matching pole counts.
            code = re.sub(r'[^A-Z0-9]', '', str(model or '').upper())
            def rank(r):
                text = re.sub(r'[^A-Z0-9]', '', str(r.get('item_name') or r.get('name') or r['sku']).upper())
                poles = str((r.get('specifications') or {}).get('Số cực') or '')
                wanted = str(specs.get('so_cuc') or '')
                return (not bool(code and code in text), bool(wanted and poles and wanted != poles),
                        not bool(r.get('specifications')), str(r['sku']))
            r = min(rows, key=rank)
            options.append(choice(brand, r['sku'], r.get('specifications'), r.get('source_url')))
        options.extend(supplemental_references('CUỘN_KHÁNG_BA_PHA_LÕI_THÉP' if typ=='REACTOR' else typ))
        research_path=ROOT/'app/data/source_reference_research.json'
        research=json.loads(research_path.read_text(encoding='utf8'))['references'] if research_path.is_file() else {}
        for reference in research.get(typ,[]):
            options.append(choice(reference['brand'],reference['model'],reference['specifications'],reference['source_url'],basis='manufacturer_web_reference'))
        unique = {}
        for opt in options:
            unique.setdefault((opt['brand'], opt['model'], opt.get('source_row_id')), opt)
        options = list(unique.values())
        def priority(o):
            value={'catalog_family_match':0,'catalog_function_match':0,'catalog_series_reference':2}.get(o['basis'],3)
            if o['basis']=='manufacturer_web_reference':
                value=1 if not source_brand or o['brand']==source_brand else 3
            return (value,o['brand'] in {'Chưa xác định','Gia công / phổ thông'},o['basis']=='cad_reference_code',o['model']=='---')
        options.sort(key=priority)
        reference = dict(schema_version=1, category=typ, price='---',
                         shared_cad=True, exact_cad_match=False, options=options,
                         observed_specifications=specs,
                         note='CAD có thể dùng chung cho các hãng/dòng cùng kiểu. Thông số mã tham khảo được ghi riêng với thông số đọc từ CAD.',
                         updated_at='2026-10-16')
        raw['catalog_tham_khao'] = reference
        old = raw.get('gia_ban') or {}
        if old.get('don_gia') not in (None,'-','---') and 'gia_ban_tham_khao_cu' not in raw:
            raw['gia_ban_tham_khao_cu'] = old
        raw['gia_ban'] = {**old, 'don_gia':'---','don_vi_tien_te':'VND',
                          'trang_thai':'Không yêu cầu giá', 'ghi_chu':'Giá để --- theo yêu cầu; tra cứu hãng, mã và thông số trong catalog_tham_khao.'}
        # Source attribution remains intact; shared brands are separately searchable.
        raw['tu_khoa_tim_kiem'] = list(dict.fromkeys([*(raw.get('tu_khoa_tim_kiem') or []),
                                                     *(str(o[k]) for o in options for k in ('brand','model') if o[k] != '---')]))
        p.write_text(json.dumps(raw,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        report.append(dict(profile=p.relative_to(CAT).as_posix(), name=d['display'], category=typ,
                           source_model=model, reference_count=len(options),
                           brands=sorted({o['brand'] for o in options}),
                           family_rows=sum(basis!='catalog_series_reference' for row,basis in family_matches),
                           related_series_rows=sum(basis=='catalog_series_reference' for row,basis in family_matches),
                           missing_model=not any(o['model'] != '---' and o['basis'] != 'cad_reference_code' for o in options)))
    result = dict(profiles=len(report), with_references=sum(bool(r['reference_count']) for r in report),
                  reference_choices=sum(r['reference_count'] for r in report),
                  family_matched_profiles=sum(bool(r['family_rows']) for r in report),
                  family_information_rows=sum(r['family_rows'] for r in report),
                  related_series_profiles=sum(bool(r['related_series_rows']) for r in report),
                  related_series_information_rows=sum(r['related_series_rows'] for r in report),
                  unresolved_models=sum(r['missing_model'] for r in report), items=report)
    (ROOT/'docs/catalog-reference-completion.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    lines=['# Cập nhật catalog dùng chung CAD — 16/10/2026','',
           'Giá toàn bộ hồ sơ để `---`. Giữ hãng/mã gốc; bổ sung lựa chọn tham khảo theo loại, không tự gán định mức tham khảo thành thông số của bản vẽ.', '',
           f"Rà {len(report)} hồ sơ; {result['with_references']} có hồ sơ tham chiếu; tổng {result['reference_choices']} lựa chọn; {result['unresolved_models']} hồ sơ chưa có mã thương mại tham khảo cụ thể (gồm phụ kiện gia công và mẫu lắp đặt).", '',
           f"Ghép theo hãng/dòng hoặc chức năng: {result['family_matched_profiles']} hồ sơ, {result['family_information_rows']} dòng thông tin từ bảng giá đang có. Giữ đủ biến thể và các dòng cùng mã ở nguồn khác nhau; không lấy giá. Có bảng tham khảo không đồng nghĩa đã nhận diện đúng dòng thiết bị. Các dòng ghép theo họ/chức năng được phân biệt với tham khảo cùng loại.", '',
           '| Thư mục | Hồ sơ | Có lựa chọn | Chưa có mã cụ thể |','| --- | ---: | ---: | ---: |']
    grouped=defaultdict(list)
    for row in report:grouped[Path(row['profile']).parts[0]].append(row)
    for name, rows in sorted(grouped.items()):
        lines.append(f"| {name} | {len(rows)} | {sum(bool(r['reference_count']) for r in rows)} | {sum(r['missing_model'] for r in rows)} |")
    lines+=['','## Các mục chưa có mã cụ thể','','Không tự đặt mã cho phụ kiện cơ khí, mẫu lắp đặt hoặc thiết bị chưa có tài liệu. Hãng tham khảo do người dùng cung cấp được ghi riêng.','']
    lines += [f"- {r['profile']}: {r['name']}" for r in report if r['missing_model']]
    (ROOT/'docs/catalog-reference-completion.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    data=_build_browser_data()
    _snapshot_path().write_text(json.dumps(data,ensure_ascii=False),encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='items'},ensure_ascii=False))


if __name__ == '__main__':
    main()
