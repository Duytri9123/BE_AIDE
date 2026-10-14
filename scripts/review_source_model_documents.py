"""Curated source block -> manufacturer model evidence, not CAD geometry approval.

Only explicit model tokens in unchanged source blocks are admitted. Ratings,
coil voltages and trip settings remain unselected. Cutouts and vague frame labels
are excluded. This is deliberately not a fuzzy bulk manufacturer promotion.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'data/CatalogTB'
LS_MC = 'https://www.ls-electric.com/upload/customer/download/4d8b99a1-c93d-4cd3-807b-1382f0c39384/Metasol_MS_E_180903.pdf'
LS_BKN = 'https://www.ls-electric.com/upload/customer/download/1483/150905_MCB_E.pdf'
CHINT_NXB = 'https://www.chintglobal.com/global/en/products/low-voltage/iec/final-power-distribution/nxb-63.html'
SE_D = 'https://iportal.se.com/Contents/docs/0100CT1501_SEC-18.PDF'
SE_F = 'https://www.se.com/us/en/faqs/FA102501/'
SE_E = 'https://www.se.com/us/en/download/document/EAV78697/'
SE_E_SMALL = 'https://www.se.com/au/en/download/document/EAV84852/'
SE_EZC = 'https://www.se.com/uk/en/download/document/LVED212091ENWEB/'
SE_ICT = 'https://www.se.com/nl/en/product/A9C20731/ict-25a-1no-230-240v-50hz-contactor/'


def documented_model(maker, block):
    """Return only manually reviewed model families; no guessed range expansion."""
    upper = block.upper().strip()
    if any(word in upper for word in ('LỖ', 'LÕ', 'HCC', 'HCN', 'ROTARY', ' CC ', 'CC ')):
        return None
    if maker == 'CHINT':
        if upper == 'NXM-1600S-3':
            return 'NXM-1600S', 'MCCB', 'https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/secondary-power-distribution/mccb/nxm/certificate/2406-NXM-1600-MCCB-CB%20Certificate.pdf', {'so_cuc':'3P'}
        if upper == 'ATS CHINT NZ7-125 100A 4P':
            return 'NZ7-125', 'ATS', 'https://chintglobal.vn/wp-content/uploads/2021/09/nz7-catalog.pdf', {'so_cuc':'4P'}
        match = re.fullmatch(r'NXB63-([123])P?', upper)
        if match:
            return 'NXB-63', 'MCB', CHINT_NXB, {'so_cuc': match[1]+'P'}
    if maker == 'LS Electric':
        # Exact suffixes only: ABS103 is not silently converted to ABS103c.
        match = re.fullmatch(r'(?:LS )?(ABH52C|ABS403C|ABN53C|ABN203C)(?: ([2-4])P)?', upper)
        if match:
            poles = match[2] or {'ABH52C':'2','ABS403C':'3','ABN53C':'3','ABN203C':'3'}[match[1]]
            return match[1][:-1]+'c', 'MCCB', 'https://www.ls-electric.com/upload/customer/download/1526/Metasol_MCCB_E_1407.pdf', {'so_cuc':poles+'P'}
        match = re.fullmatch(r'MT-?(12|63)', upper)
        if match:
            return 'MT-'+match[1], 'THERMAL_RELAY', LS_MC, {}
        match = re.fullmatch(r'MC[ -](185|265|500)A', upper)
        if match:
            return 'MC-'+match[1]+'a', 'CONTACTOR', LS_MC, {}
        match = re.fullmatch(r'BKN ([1-4])P', upper)
        if match:
            return 'BKN', 'MCB', LS_BKN, {'so_cuc': match[1]+'P'}
    if maker == 'Schneider Electric':
        if upper == 'LC1E160':
            return upper, 'CONTACTOR', 'https://www.se.com/pl/pl/faqs/FAQ000267489/', {}
        if upper in {'LC1D40-65','06 - N - SC CTT LC1D40~65','06 - N - SC CTT CHIẾU HÔNG LC1D40~65'}:
            return 'LC1D40-65', 'CONTACTOR', 'https://www.se.com/es/es/faqs/FA279562/', {'documented_model_options':['LC1D40','LC1D50','LC1D65']}
        if re.fullmatch(r'NS100_160NHL(?:_[45])?_[CD]', upper):
            return 'NS100 / NS160', 'MCCB', 'https://ckm-content.se.com/ckmContent/sfc/servlet.shepherd/document/download/0691H00000FWbNdQAL', {'documented_model_options':['NS100N','NS100H','NS100L','NS160N','NS160H','NS160L']}
        drive_groups = {
            'ATV630U07~55N4':['ATV630'+v+'N4' for v in ('U07','U15','U22','U30','U40','U55')],
            'ATV630U75~D11N4':['ATV630U75N4','ATV630D11N4'],
            'ATV630D15~D22N4':['ATV630'+v+'N4' for v in ('D15','D18','D22')],
            'ATV630D30~D45N4':['ATV630'+v+'N4' for v in ('D30','D37','D45')],
            'ATV630D55~D90N4':['ATV630'+v+'N4' for v in ('D55','D75','D90')],
            'ATV630C11~C16N4':['ATV630'+v+'N4' for v in ('C11','C13','C16')],
            'ATV320U22~40N4C':['ATV320'+v+'N4C' for v in ('U22','U30','U40')],
            'ATV320U55~75N4B':['ATV320U55N4B','ATV320U75N4B'],
            'ATV212H075~U22N4':['ATV212H'+v+'N4' for v in ('075','U15','U22')],
            'ATV212HU30~U55N4':['ATV212H'+v+'N4' for v in ('U30','U40','U55')],
            'ATV212HU75~D11N4':['ATV212HU75N4','ATV212HD11N4'],
            'ATV212HD15~18N4':['ATV212HD15N4','ATV212HD18N4'],
        }
        for label, models in drive_groups.items():
            if upper.endswith(' '+label):
                document = ('https://www.se.com/us/en/faqs/FA302753/' if label.startswith('ATV630') else
                    'https://download.schneider-electric.com/files?filename=Catalog&p_Doc_Ref=DIA2ED2160311EN' if label.startswith('ATV320') else
                    'https://iportal.se.com/Contents/docs/ATV212_CATALOG.PDF')
                return label, 'VFD', document, {'documented_model_options':models}
        # The model itself must terminate the block, not be a substring of an SKU.
        match = re.search(r'\b(LC1D(?:09|18|25|32|80|115|150))$', upper)
        if match:
            return match[1], 'CONTACTOR', SE_D, {}
        if upper == 'LC1D40':
            return 'LC1D40', 'CONTACTOR', 'https://www.se.com/us/en/product/LC1D40M7/', {}
        match = re.fullmatch(r'LC1F(115|150|185|225|265|330)', upper)
        if match:
            return match[0], 'CONTACTOR', SE_F, {}
        match = re.fullmatch(r'SN_(LC1E25|LC1E32)', upper)
        if match:
            return match[1], 'CONTACTOR', SE_E, {}
        if upper == 'SN_LC1E06-18':
            return 'LC1E06-18', 'CONTACTOR', SE_E_SMALL, {}
        if upper in {'LC1D9-18', 'LC1D25-38'}:
            return upper, 'CONTACTOR', SE_D, {}
        match = re.search(r'\b(EZC100|EZC250) ([234]) PHASE$', upper)
        if match:
            return match[1], 'MCCB', SE_EZC, {'so_cuc':match[2]+'P'}
        if re.search(r'\b1P A9C20731$', upper):
            return 'A9C20731', 'CONTACTOR', SE_ICT, {'so_cuc':'1P'}
    return None


def run():
    baseline = json.loads((ROOT/'docs/library-dxf-identity-audit.json').read_text(encoding='utf8'))
    targets = {d['id']:d for d in baseline['items'] if d.get('brand_identification_status')=='source_library'}
    path = ROOT/'app/data/library_manufacturer_evidence.json'
    registry = json.loads(path.read_text(encoding='utf8'))
    results = []
    for profile_path in CATALOG.rglob('thong_tin_thiet_bi.json'):
        cid = 'TB-'+hashlib.sha1(profile_path.relative_to(CATALOG).as_posix().encode()).hexdigest()[:16]
        item = targets.get(cid)
        if not item:
            continue
        current = json.loads(profile_path.read_text(encoding='utf8'))
        source = current.get('nguon_cad') or {}
        block = source.get('block') or ''
        found = documented_model(item['brand'], block)
        result = {'id':cid, 'source_block':block, 'brand':item['brand'], 'status':'pending_specific_model_research'}
        if found:
            code, kind, url, spec = found
            spec = dict(spec)
            options = spec.pop('documented_model_options', [])
            # Every original view must still exist and have the audit's checksum.
            paths = {v['id_hinh_goc']:v['duong_dan'] for v in current['cad_don']}
            for view in item['views']:
                drawing = profile_path.parent/paths[view['view_id']]
                if hashlib.sha256(drawing.read_bytes()).hexdigest()!=view['sha256']:
                    raise ValueError('Stale source drawing '+cid)
            registry['evidence'][cid] = {
                'brand':item['brand'], 'status':'source_model_documented',
                'source':{key:source[key] for key in ('file','sha256','block')},
                'manufacturer_document':url, 'views':item['views'],
                'basis':'Explicit source block model cross-referenced with manufacturer documentation; no direct logo claim or geometry approval.',
                'note':'Hãng và dòng/mã trong block nguồn đã đối chiếu tài liệu hãng. Cần chọn cấu hình đặt hàng; chưa xác nhận hình học CAD.',
                'library_description':{'display':f'{kind} {item["brand"]} {code}', 'type':kind, 'product_code':code,
                    'manufacturer_document':url, 'source_model_reference':True, 'reviewed_spec':spec,
                    'price_family_codes':options,
                    'use':'Mã/dòng tra từ block CAD nguồn và tài liệu hãng. Chọn thông số điện, điện áp điều khiển và mã đặt hàng riêng; kiểm tra kích thước trước khi bố trí.'}}
            result.update(status='source_model_documented', product_code=code, manufacturer_document=url)
        elif any(word in block.upper() for word in ('LỖ', 'LÕ', 'ROTARY')):
            result.update(status='mounting_or_cutout_reference', note='Nhãn bản vẽ lỗ khoét/lắp đặt; cần đối chiếu hình trước khi phân loại riêng, không gán giá cả thiết bị chỉ từ nhãn.')
        elif any(word in block.upper() for word in ('HCC', 'HCN')):
            result.update(status='projection_reference_requires_review', note='Tên viết tắt HCC/HCN; chưa đủ để khẳng định lỗ khoét hay thiết bị, cần đối chiếu hình và tài liệu.')
        elif any(word in block.upper() for word in ('~','XXX','AF','MCB')):
            result.update(status='shared_family_or_generic_frame', note='Dòng dùng chung/khung hoặc loại chung; phải tìm tài liệu và phân biệt cấu hình.')
        results.append(result)
    # Grouped references have public IDs and multiple source profiles; keep explicit pending records.
    for cid, item in targets.items():
        if not any(row['id']==cid for row in results):
            results.append({'id':cid, 'source_block':item['spec'].get('nhan_block_nguon'), 'brand':item['brand'],
                            'status':'grouped_reference_requires_member_review'})
    assert len(results)==251
    path.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    report={'scope':'All 251 original source-library public CAD entries; resolved subset is documented model identity, never automatic CAD approval.',
            'items':results}
    (ROOT/'docs/library-source-model-research.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    from collections import Counter
    counts = dict(Counter(row['status'] for row in results))
    lines = ['# Tìm mã cho 251 CAD theo thư viện nguồn', '',
        f'Đối chiếu tài liệu hãng ngày 14/10/2026: {counts["source_model_documented"]} CAD có mã/dòng hoặc nhóm mã được tài liệu hãng xác nhận. Các bản vẽ vẫn cần kiểm tra kích thước, mặt nhìn và cấu hình đặt hàng trước khi dùng; không bật tự chèn CAD.', '',
        'Nguồn nhận diện là tên block trong thư viện có checksum và tài liệu hãng, không phải khẳng định đã đọc logo trực tiếp trên bản vẽ. Bộ nhận diện kiểm tra cả block, checksum thư viện và checksum DXF để tránh dùng chứng cứ cũ.', '',
        'Các mục còn lại được ghi thành việc cụ thể. HCC/HCN chỉ là viết tắt chưa xác minh, không mặc định là lỗ khoét. Nhãn NS400_600 và LC1D185 không tự sửa thành NS400/630 hay LC1F185.', '',
        '| Kết quả | CAD |', '| --- | ---: |']
    labels={'source_model_documented':'Đã đối chiếu mã/dòng với hãng', 'pending_specific_model_research':'Cần tiếp tục tìm đúng mã/nhãn',
            'mounting_or_cutout_reference':'Nhãn lỗ khoét/lắp đặt; cần kiểm tra phân loại',
            'projection_reference_requires_review':'Nhãn HCC/HCN chưa rõ ý nghĩa',
            'shared_family_or_generic_frame':'Nhãn dùng chung/khung; chưa xác định mã riêng',
            'grouped_reference_requires_member_review':'Nhóm CAD cần đối chiếu từng thành viên'}
    lines += [f'| {labels[k]} | {v} |' for k,v in counts.items()]
    lines += ['', '| CAD | Nhãn nguồn | Hãng | Mã/dòng tra được | Kết quả | Nguồn hãng |', '| --- | --- | --- | --- | --- | --- |']
    for r in results:
        cells=[r['id'],r['source_block'],r['brand'],r.get('product_code',''),labels[r['status']],
               '[Tài liệu hãng]('+r['manufacturer_document']+')' if r.get('manufacturer_document') else 'Chưa có đối chiếu đủ cho CAD này']
        lines.append('| '+' | '.join(str(c or '').replace('|','/') for c in cells)+' |')
    (ROOT/'docs/library-source-model-research.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(counts)


if __name__=='__main__':
    run()
