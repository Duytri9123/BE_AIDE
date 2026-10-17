"""Cross-reference observed CAD labels against cached manufacturer documents.

The result identifies labels/families only. It does not claim that an unlabeled
outline uniquely determines an order code, electrical configuration or geometry.
"""
import json
import hashlib
import re
from collections import Counter
from pathlib import Path
from app.services.ai.manufacturer_registry import canonical_brand
from app.services.catalog_source_identification import model_pattern,source_fingerprint
from app.services.catalog_family_matching import source_identity
from app.services.library_manufacturer_identity import SOURCE_MAKERS,manufacturer_identity

ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'data/CatalogTB'
PATTERN=re.compile(r'\b(?:KBF|KBD|HYBT|HYTM|HYT|EM4H|BD01|CT0\.6|ME|SUP1|HDY3|HRB|YW1B|MFM|BEW|BE|VAF|FKL|FLK|NXM|NM1|NXB|NCH8|LC1[DEF]|ATV|MC|MT|PM|S8FS)[ -]?[A-Z0-9]+(?:[._/-][A-Z0-9]+)*',re.I)
BRAND_PREFIX=[(r'^(KB[DF])','LightStar'),(r'^HY[BMT]*T?','Hanyoung Nux'),
 (r'^ME[- ]?4[12]','EMIC'),(r'^CT0[.]6','EMIC'),(r'^SUP1','Suntree'),
 (r'^YW1B','IDEC'),(r'^MFM38','Selec'),(r'^FKL66','Leipole'),(r'^UK[ -]?3[ -]?N$','Phoenix Contact'),(r'^BD01','MITEX'),
 (r'^S7[- ]?1200$','Siemens')]


def candidates(raw,scan):
    values=[]
    for text in [raw.get('ma_dong_san_pham') or '',*((raw.get('nhan_dien_ai') or {}).get('cac_ma_dong_san_pham') or [])]:
        values.extend(x.strip() for x in re.split(r'\s*/\s*',text))
    explicit={re.sub(r'[^A-Z0-9]','',v.upper()) for v in values if v}
    source=raw.get('nguon_cad') or {}
    original_block=source.get('block') or '' if isinstance(source,dict) else ''
    observed='\n'.join([*scan['texts'],original_block,
        *(b for v in scan['views'] for b in v.get('referenced_blocks',[]) if not b.startswith('*')),
        *(a['text'] for c in scan.get('original_dwg_context') or [] for a in c['attributes'])])
    values.extend(m.group(0).strip() for m in PATTERN.finditer(observed))
    # These source library names append a projection index, not an order suffix.
    if re.fullmatch(r'(?:NXM|NM1)-[A-Z0-9-]+-[123]',original_block,re.I):
        values.append(original_block.rsplit('-',1)[0])
    for text in scan['texts']:
        if re.fullmatch(r'[A-Z][A-Z0-9]+(?:[._/-][A-Z0-9]+)*',text.strip(),re.I) and any(c.isdigit() for c in text):values.append(text.strip())
    for context in scan.get('original_dwg_context') or []:
        for attribute in context['attributes']:
            if re.match(r'^(?:TYPE|MODEL|MA)(?:\d+)?$',attribute.get('tag') or '',re.I):
                values.extend(x.strip() for x in re.split(r'\s*/\s*',attribute['text']))
    result={}
    for value in values:
        if len(value)<2 or len(value)>65 or not re.search(r'[A-Z]',value,re.I) or not re.search(r'\d',value):continue
        if re.fullmatch(r'\d+(?:[.]\d+)?(?:A|V|VA|KVA|KW|HZ|MM|P)',value,re.I):continue
        if re.fullmatch(r'M\d+[xX]\d+(?:MM)?',value,re.I):continue
        key=re.sub(r'[^A-Z0-9]','',value.upper())
        if len(key)<4 and key not in explicit:continue
        if re.fullmatch(r'[BCD]\d+',value,re.I) and key not in explicit:continue
        if re.match(r'^(?:IEC|EN\d|GBT|IP\d|AC\d|DC\d|S[12]$|P[12]$|L[123]$|I[12]$|U\d$)',value,re.I):continue
        pattern=model_pattern(value)
        if not pattern or not pattern.search(observed):continue
        result.setdefault(re.sub(r'[^A-Z0-9]','',value.upper()),value)
    return list(result.values()),observed


def main():
    scans=json.loads((ROOT/'docs/catalog-source-text-evidence.json').read_text(encoding='utf8'))['items']
    documents=[]
    reviews_path=ROOT/'app/data/catalog_document_model_reviews.json'
    document_reviews=json.loads(reviews_path.read_text(encoding='utf8')) if reviews_path.is_file() else {}
    for path in (ROOT/'outputs/catalog-identity-documents').glob('*.json'):
        row=json.loads(path.read_text(encoding='utf8'))
        if row.get('status')=='fetched':documents.append(row)
    memo={}
    def find_document(model,brand):
        key=(model,brand)
        if key in memo:return memo[key]
        pattern=model_pattern(model);matches=[]
        family_pattern=None
        if re.fullmatch(r'(?:(?:LC1[DEF]|EZ[CSV]|TS|TD|PM|C|SH|S)\d+|ATV\d+[A-Z]+\d+)',model,re.I):
            family_pattern=re.compile(pattern.pattern.replace('(?![A-Z0-9])','(?![0-9])'),re.I)
        for url,review in document_reviews.items():
            if not review.get('browsed_model_evidence') or canonical_brand(review.get('brand'))!=brand:continue
            if any(pattern.fullmatch(label) for label in review.get('table_models',[])):
                matches.append({'url':url,'sha256':None,'page':review['page'],'format':'browsed_page_excerpt',
                    'match':model,'basis':'manually_reviewed_official_product_page'})
        for doc in documents:
            review=document_reviews.get(doc['url']) or {}
            if doc.get('document_host_type')=='manufacturer_document_mirror_pending_visual_review' and not review.get('author_verified'):continue
            brands={canonical_brand(b) for b in doc.get('brands') or [] if b}
            if not brand or brand not in brands:continue
            model_key=re.sub(r'[^A-Z0-9]','',model.upper())
            if model_key in {re.sub(r'[^A-Z0-9]','',m.upper()) for m in review.get('table_models',[])}:
                matches.append({'url':doc['url'],'sha256':doc['sha256'],'page':review['page'],
                    'format':doc['format'],'match':model,'basis':'reviewed_manufacturer_model_table'})
                continue
            for page in doc['pages']:
                hit=pattern.search(page['text'])
                basis='literal_model_label'
                if not hit and family_pattern:
                    hit=family_pattern.search(page['text']);basis='manufacturer_ordering_code_family_prefix'
                if hit:
                    matches.append({'url':doc['url'],'sha256':doc['sha256'],'page':page['page'],
                        'format':doc['format'],'match':hit.group(0)[:80],'basis':basis})
                    break
        memo[key]=matches;return matches
    records={}
    ocr_reviews=json.loads((ROOT/'app/data/catalog_ocr_label_reviews.json').read_text(encoding='utf8'))
    for scan in scans:
        raw=json.loads((CAT/scan['profile']).read_text(encoding='utf8'))
        cid='TB-'+hashlib.sha1(scan['profile'].encode()).hexdigest()[:16]
        prior=manufacturer_identity({'id':cid},raw,CAT/scan['profile'])
        curated=prior.get('reviewed_description') or {}
        labels,observed=candidates(raw,scan)
        source_review=raw.get('source_catalog_review') or {}
        brands=[canonical_brand(raw.get('hang_xac_nhan') or '')]
        confirmed_brands={b for b in brands if b}
        confirmed_brands.update(canonical_brand(b) for b in source_review.get('brands_read_from_source') or [])
        source=raw.get('nguon_cad') or {}
        if isinstance(source,dict):
            maker=SOURCE_MAKERS.get(str(source.get('file') or '').replace('\\','/').rsplit('/',1)[-1].upper())
            if maker:brands.append(canonical_brand(maker))
        brands.extend(canonical_brand(b) for b in source_review.get('brands_read_from_source') or [])
        documented=[]
        for model in labels:
            candidate_brands=[b for b in brands if b]
            if not candidate_brands:
                candidate_brands=[canonical_brand(brand) for pattern,brand in BRAND_PREFIX if re.search(pattern,model,re.I)]
            for brand in dict.fromkeys(candidate_brands):
                docs=find_document(model,brand)
                if not docs:continue
                documented.append({'model':model,'brand':brand,'manufacturer_confirmed_on_source':brand in confirmed_brands,
                    'scope':'source_model_label','documents':docs[:3]})
        # Nested shorter labels must not obscure a more specific observed code.
        exact={re.sub(r'[^A-Z0-9]','',m['model'].upper()) for m in documented}
        documented=[m for m in documented if not any(other.startswith(code:=re.sub(r'[^A-Z0-9]','',m['model'].upper())) and other!=code for other in exact)]
        if curated.get('source_model_reference') and curated.get('product_code') and curated.get('manufacturer_document'):
            brand=canonical_brand(prior.get('brand'))
            if not any(m['model']==curated['product_code'] and m['brand']==brand for m in documented):
                documented.insert(0,{'model':curated['product_code'],'brand':brand,
                    'manufacturer_confirmed_on_source':False,'scope':'previously_reviewed_source_model_or_family',
                    'documents':[{'url':curated['manufacturer_document'],'sha256':None,'page':None,
                        'format':'previous_checksum_bound_manufacturer_review','match':curated['product_code'],
                        'basis':'existing_manufacturer_evidence_validated_against_source_dxf_hash'}]})
        role=str((raw.get('catalog_tham_khao') or {}).get('research',{}).get('status') or '')
        if role in {'generic_mechanical','drawing_or_assembly'}:status=role
        elif documented:status='documented_source_label'
        elif labels:status='source_labels_need_catalog'
        elif scan['texts']:status='source_text_without_unique_model'
        else:status='source_geometry_without_model_label'
        observation=ocr_reviews.get(scan['profile'])
        if observation:
            view=next((v for v in scan['views'] if v['id']==observation['view']),None)
            preview=(CAT/view['path']).with_name('xem_truoc.svg') if view else None
            if not preview or not preview.is_file() or hashlib.sha256(preview.read_bytes()).hexdigest()!=observation['preview_sha256']:
                observation=None
        if observation and observation.get('configuration_conflict'):status='source_label_conflict'
        records[scan['profile']]={'status':status,'checked_at':'2026-10-17','source_fingerprint':source_fingerprint(raw),
            'reviewed_outline_label':observation,
            'source_models_read':labels,'documented_models':documented,
            'views':[{k:v[k] for k in ('id','path','sha256')} for v in scan['views'] if v.get('sha256')],
            'source_text_count':len(scan['texts']),
            'contains_multiple_components':bool(source_review.get('contains_multiple_components')),
            'original_context':[{'basis':c['basis'],'block':c['block'],'handle':c.get('handle'),
                'source_sha256':c['source_sha256'],'dynamic_state_verified':False} for c in scan.get('original_dwg_context') or []],
            'ordering_code_verified':False,'geometry_verified':False}
    data={'schema_version':1,'checked_at':'2026-10-17','profiles':records}
    (ROOT/'app/data/catalog_source_identification.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    report={'profiles':len(records),'documents_read':len(documents),'statuses':dict(Counter(r['status'] for r in records.values())),
            'documented_source_models':sum(len(r['documented_models']) for r in records.values())}
    (ROOT/'docs/catalog-source-label-resolution.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
