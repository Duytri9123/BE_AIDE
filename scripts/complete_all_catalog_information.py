"""Audit and enrich every source profile; preserve evidence and report unresolved identity.

Unlike generic type suggestions, family matches require a source label/model and
compatible manufacturer/category/poles. No electrical rating or CAD identity is
inferred from a related catalog product.
"""
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from app.services.catalog_family_matching import matching_rows, information_choice, category_key, source_identity
from app.services.ai.manufacturer_registry import canonical_brand
from app.services.catalogtb_browser import _build_browser_data
from scripts.complete_catalog_references import ndk_references, choice

ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'data/CatalogTB'
DATE='2026-10-17'
FACE_LABELS={'mặt trước','mặt sau','mặt bên','mặt trên','mặt dưới','mặt đấu dây','front','rear','side','top','bottom'}

# Official family pages researched for this pass. Family scope stays explicit.
FAMILY_DOCUMENTS=[
 ('CHINT','MCCB',r'\bNXM', 'NXM', 'https://www.chintglobal.com/sg/en/products/low-voltage/iec/secondary-power-distribution/nxm.html'),
 ('CHINT','MCCB',r'\bNM1', 'NM1', 'https://www.chintglobal.com/global/en/products/low-voltage/iec/secondary-power-distribution/nm1.html'),
 ('CHINT','MCB',r'\bNXB', 'NXB-63', 'https://www.chintglobal.com/global/en/products/low-voltage/iec/final-power-distribution/nxb-63.html'),
 ('CHINT','CONTACTOR',r'\bNCH8', 'NCH8', 'https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/industrial-control/modular-ac-contactor/nch8/catalog/NCH8-Modular%20AC%20Contactors-Catalog.pdf'),
 ('LS Electric','MCCB',r'\b(?:AB[NHSE]|ABS|LS\s+\d+)', 'Metasol MCCB/ELCB', 'https://pfinder.ls-electric.com/IEC/product/mccb_metasol.do'),
 ('LS Electric','CONTACTOR',r'\bMC[ -]?\d', 'Metasol MS', 'https://www.ls-electric.com/products/view/Smart_Power_Solution/Low_Voltage/Contactor_%26_Overload_Relay/Metasol_MS'),
 ('LS Electric','THERMAL_RELAY',r'\bMT[ -]?\d', 'Metasol MT', 'https://www.ls-electric.com/products/view/Smart_Power_Solution/Low_Voltage/Contactor_%26_Overload_Relay/Metasol_MS'),
 ('Schneider Electric','ACB',r'\bNW', 'MasterPact NW', 'https://www.se.com/fr/fr/download/document/LVPED208008FR_WEB/'),
 ('Mitsubishi Electric','MCCB',r'\bNF', 'WS-V / NF', 'https://us.mitsubishielectric.com/fa/en/products/lvd/circuit-breakers/molded-case/'),
 ('Mitsubishi Electric','INVERTER',r'\bFR[ -]?S5', 'FR-S500', 'https://dl.mitsubishielectric.com/dl/fa/document/manual/inv/ib0600026/ib0600026d.pdf'),
 ('Shihlin','MCB',r'.', 'BHA', 'https://cht.seec.com.tw/Content/Goods/GCont.aspx?CatId=2016102709295716333&MSID=655607566254022725&MmmID=655575436061073254&SiteID=10'),
 ('Leipole','FILTER',r'\bFKL66', 'FKL66', 'https://www.leipole.net/products/fkl66-fan-and-filter.html'),
 ('Leipole','FAN',r'\bFKL66', 'FKL66', 'https://www.leipole.net/products/fkl66-fan-and-filter.html'),
]


def is_face_label(value):
    return str(value or '').strip().casefold() in FACE_LABELS


def research_category(raw, display):
    value=(raw.get('source_catalog_review') or {}).get('component_type') or display.get('type') or (raw.get('catalog_tham_khao') or {}).get('category')
    key=category_key(value)
    if key in {'LƯỚILỌCTHÔNGGIÓTHỤĐỘNG,KHÔNGCÓĐỘNGCƠ','LƯỚITHÔNGGIÓTHỤĐỘNG,KHÔNGCÓĐỘNGCƠ'}:
        return 'FILTER'
    return value or ''


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def enrich(raw, display, pool, research):
    reference=dict(raw.get('catalog_tham_khao') or {})
    before=reference.get('options') or []
    options=[dict(o) for o in before if not is_face_label(o.get('model'))]
    typ=research_category(raw,display)
    identity=source_identity(raw,display)
    brand=canonical_brand(raw.get('hang_xac_nhan') or display.get('brand') or '')
    matches=matching_rows(raw,{**display,'type':typ},pool,typ)
    options.extend(information_choice(row,basis) for row,basis in matches)
    reviewed=display.get('reviewed_description') or {}
    if reviewed.get('source_model_reference') and reviewed.get('product_code') and reviewed.get('manufacturer_document'):
        options.append(choice(brand,reviewed['product_code'],reviewed.get('reviewed_spec') or {},
            reviewed['manufacturer_document'],'documented_source_model',
            'Mã/dòng trong block nguồn đã đối chiếu tài liệu hãng và checksum CAD; chưa chọn cấu hình đặt hàng.'))
    family_documents=[]
    for maker,category,pattern,family,url in FAMILY_DOCUMENTS:
        if canonical_brand(maker)==brand and category_key(category)==category_key(typ) and re.search(pattern,identity):
            family_documents.append({'brand':brand,'family':family,'url':url,'scope':'manufacturer_family','checked_at':DATE})
            options.append(choice(brand,family,{'Dòng thiết bị':family},url,'manufacturer_family_document',
                'Tài liệu đúng hãng/dòng để tiếp tục đối chiếu mã trong CAD; không xác nhận mã đầy đủ hoặc kích thước.'))
    if category_key(typ)=='TRANSFORMER':
        options.extend(ndk_references())
    for category,refs in research.items():
        if category_key(category)!=category_key(typ):continue
        for r in refs:
            options.append(choice(r['brand'],r['model'],r.get('specifications'),r.get('source_url'),
                'manufacturer_web_reference','Sản phẩm tham khảo cùng chức năng; đối chiếu hãng, mã và kích thước riêng.'))
    # Existing sourced specifications are retained; only missing fields are filled.
    merged={}
    for option in options:
        key=(canonical_brand(option.get('brand')),option.get('model'),option.get('source_row_id'))
        if key not in merged:
            merged[key]=option
        else:
            old=merged[key]
            old['specifications']={**(option.get('specifications') or {}),**(old.get('specifications') or {})}
            if not old.get('source_url') and option.get('source_url'):old['source_url']=option['source_url']
    options=list(merged.values())
    priority={'documented_source_model':0,'catalog_family_match':1,'catalog_function_match':2,
              'manufacturer_family_document':3,'catalog_series_reference':4,'source_profile':5,'cad_reference_code':9}
    options.sort(key=lambda o:(priority.get(o.get('basis'),6),canonical_brand(o.get('brand'))!=brand))
    if not options:
        options=[choice(brand or 'Chưa xác định','---',raw.get('thong_so'),basis='cad_reference_code',
                        note='Chưa xác định mã thương mại; xem thông số đọc từ nguồn CAD.')]
    reference.update(options=options,updated_at=DATE,category=typ or reference.get('category'),
                     manufacturer_family_documents=family_documents)
    model=display.get('product_code') or raw.get('ma_dong_san_pham')
    if is_face_label(model):model=None
    role=category_key(typ)
    mechanical=display.get('brand_kind')=='generic' or role in {'MOUNTINGSUPPORT','COPPERBUSBAR'}
    if role in {'MOUNTINGTEMPLATE','ASSEMBLYREFERENCE'}:state='drawing_or_assembly'
    elif mechanical:state='generic_mechanical'
    elif reviewed.get('source_model_reference'):state='documented_source_model'
    elif model:state='source_model_requires_catalog_check'
    elif any(basis!='catalog_series_reference' for _,basis in matches):state='source_family_candidates'
    else:state='requires_source_identification'
    gaps=[]
    if state=='requires_source_identification':gaps.append('Xác định hãng/mã từ nhãn hoặc block CAD nguồn')
    if state not in {'generic_mechanical','drawing_or_assembly'}:
        if not model:gaps.append('Đối chiếu và chọn mã đặt hàng đầy đủ')
        if not matches and not family_documents and not reviewed.get('manufacturer_document'):
            gaps.append('Tra catalog đúng hãng/dòng; các mã cùng loại hiện có chỉ là tham khảo')
        gaps.append('Đối chiếu thông số điện và kích thước gá của biến thể đã chọn')
    reference['research']={'checked_at':DATE,'status':state,'source_model':model,
        'matched_catalog_rows':len(matches),'model_identity_verified':bool(reviewed.get('source_model_reference')),
        'remaining_tasks':gaps,'exact_cad_match':False}
    raw['catalog_tham_khao']=reference
    # Remove previously injected catalog model aliases; reference options are searched
    # explicitly, while aliases retain only the source identity and user terms.
    injected={str(o.get(k) or '') for o in before for k in ('brand','model')}
    aliases=[x for x in raw.get('tu_khoa_tim_kiem',[]) if x and not is_face_label(x) and x not in injected]
    raw['tu_khoa_tim_kiem']=list(dict.fromkeys([*aliases,*(str(raw.get(k) or '') for k in ('ten_san_pham','ma_dong_san_pham','ban_chat'))]))
    return {'name':raw.get('ten_san_pham'),'category':typ,'brand':brand,
            **reference['research'],'reference_count':len(options),
            'removed_face_models':sum(is_face_label(o.get('model')) for o in before),
            'added_choices':len(set((o.get('brand'),o.get('model'),o.get('source_row_id')) for o in options)-
                                set((o.get('brand'),o.get('model'),o.get('source_row_id')) for o in before))}


def main():
    paths=sorted(CAT.rglob('thong_tin_thiet_bi.json'))
    backup=ROOT/'outputs/catalog-before-all-information-20261017.zip'
    if not backup.exists():
        with ZipFile(backup,'w',ZIP_DEFLATED) as archive:
            for path in paths:archive.write(path,path.relative_to(CAT).as_posix())
            archive.write(ROOT/'app/data/catalogtb_published_information.json','published_information.json')
    snapshot=_build_browser_data()
    display={cid:d for d in snapshot['items'] for cid in d.get('member_profile_ids') or [d['id']]}
    pool=[]
    for filename in ('supplier_pricebooks.json','web_catalog_offers.json'):
        pool.extend(read_json(ROOT/'app/data'/filename)['items'])
    research=read_json(ROOT/'app/data/source_reference_research.json')['references']
    with ZipFile(backup) as archive:
        baseline={name:json.loads(archive.read(name).decode('utf-8-sig')) for name in archive.namelist()
                  if name.endswith('thong_tin_thiet_bi.json')}
    by_brand=defaultdict(list)
    for row in pool:by_brand[canonical_brand(row.get('brand'))].append(row)
    results=[]
    for path in paths:
        raw=read_json(path);relative=path.relative_to(CAT).as_posix()
        cid='TB-'+hashlib.sha1(relative.encode()).hexdigest()[:16]
        d=display.get(cid) or {'brand':raw.get('hang_xac_nhan'),'type':(raw.get('nhan_dien_ai') or {}).get('loai_thiet_bi_code')}
        brand=canonical_brand(raw.get('hang_xac_nhan') or d.get('brand') or '')
        row=enrich(raw,d,by_brand.get(brand,[]) if brand else pool,research)
        original_options=(baseline.get(relative,{}).get('catalog_tham_khao') or {}).get('options') or []
        current_options=raw['catalog_tham_khao']['options']
        row['removed_face_models']=sum(is_face_label(o.get('model')) for o in original_options)
        row['added_choices']=len({(o.get('brand'),o.get('model'),o.get('source_row_id')) for o in current_options}-
                                 {(o.get('brand'),o.get('model'),o.get('source_row_id')) for o in original_options})
        row.update(profile=relative,id=cid)
        path.write_text(json.dumps(raw,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        results.append(row)
    summary={'checked_at':DATE,'profiles':len(results),'public_devices':snapshot['total'],
        'source_catalog_rows':len(pool),'added_choices':sum(r['added_choices'] for r in results),
        'removed_face_models':sum(r['removed_face_models'] for r in results),
        'statuses':dict(Counter(r['status'] for r in results)),
        'matched_profiles':sum(r['matched_catalog_rows']>0 for r in results),
        'scope':'All source profiles; catalog references do not establish exact CAD identity.',
        'items':results}
    (ROOT/'docs/all-catalog-information-2026-10-17.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    lines=['# Rà soát thông tin toàn thư viện — 17/10/2026','',
        f"Đã xử lý {len(results)} hồ sơ nguồn, tương ứng {snapshot['total']} thiết bị hiển thị.",
        f"Đối chiếu {len(pool)} dòng catalog có sẵn; bổ sung {summary['added_choices']} lựa chọn; bỏ {summary['removed_face_models']} nhãn mặt nhìn bị dùng làm mã.",
        '', 'Mã tham khảo và mã đã nhận diện từ nguồn được thống kê riêng. Không coi một bảng tham khảo là xác nhận mã chính xác của CAD.', '',
        '| Trạng thái | Hồ sơ |','| --- | ---: |']
    lines += [f'| {k} | {v} |' for k,v in summary['statuses'].items()]
    lines += ['', '| Thư mục | Hồ sơ | Có dòng catalog ghép từ nhãn nguồn |','| --- | ---: | ---: |']
    for group in sorted({r['profile'].split('/')[0] for r in results}):
        members=[r for r in results if r['profile'].split('/')[0]==group]
        lines.append(f"| {group} | {len(members)} | {sum(r['matched_catalog_rows']>0 for r in members)} |")
    lines += ['', '| Hồ sơ | Mã nguồn | Trạng thái | Việc còn cần xác minh |', '| --- | --- | --- | --- |']
    for r in results:
        cells=[r['profile'],r['source_model'] or '',r['status'],'; '.join(r['remaining_tasks'])]
        lines.append('| '+' | '.join(str(c).replace('|','/').replace('\n',' ') for c in cells)+' |')
    (ROOT/'docs/all-catalog-information-2026-10-17.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    from scripts.export_published_catalog_information import main as publish
    from scripts.refresh_catalogtb_offline_information import main as offline
    publish();offline()
    print(json.dumps({k:v for k,v in summary.items() if k!='items'},ensure_ascii=True))


if __name__=='__main__':main()
