"""Read original catalog/pricebook information independently of price availability."""
import hashlib
import json
import math
import re
from functools import lru_cache
from pathlib import Path
from .catalog_family_matching import matching_rows, category_key,poles,row_poles
from .catalog_source_identification import model_pattern
from .ai.manufacturer_registry import canonical_brand
from .library_reference_prices import reference_matches,price_index

ROOT=Path(__file__).resolve().parents[1]/'data'

def catalog_model_pattern(value):
    # Only split explicitly written, complete alternatives. Never expand
    # abbreviated suffixes such as "MC-6a / 9a" into guessed model numbers.
    alternatives=re.split(r'\s+/\s+',str(value or '').strip())
    if len(alternatives)>1:
        patterns=[model_pattern(v) for v in alternatives if re.match(r'^[A-Za-z]',v)]
        patterns=[p for p in patterns if p]
        return re.compile('|'.join('(?:'+p.pattern+')' for p in patterns),re.I) if patterns else None
    pattern=model_pattern(value)
    if pattern:return pattern
    text=str(value or '').strip().upper()
    from .catalog_family_matching import STOP
    if re.fullmatch('[A-Z]{2,12}',text) and text not in STOP|{'ABB','SIEMENS','OEM'}:
        return re.compile(r'(?<![A-Z0-9])'+re.escape(text)+r'(?![A-Z0-9])',re.I)
    return None

def explicit_family_compatible(model,row):
    family=(row.get('specifications') or {}).get('Dòng sản phẩm')
    return not (family and str(model).isalpha()) or str(family).casefold()==str(model).casefold()


def optional_price(value):
    return value if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>0 else None


@lru_cache(maxsize=2)
def _rows(revision):
    rows=[]
    for name,_,_ in revision:
        kind='pricebook' if Path(name).name=='supplier_pricebooks.json' else 'manufacturer_catalog' if Path(name).name=='external_product_information.json' else 'price_reference'
        rows.extend({**row,'information_kind':kind} for row in json.loads(Path(name).read_text(encoding='utf8')).get('items',[]))
    from .reviewed_product_taxonomy import reviewed_price_row
    return [reviewed_price_row(r) for r in rows]


def source_rows():
    files=[ROOT/name for name in ('supplier_pricebooks.json','web_catalog_offers.json','external_product_information.json')]
    return _rows(tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) for p in files if p.is_file()))


def named_family_rows(model,brand,kind,spec,rows):
    pattern=catalog_model_pattern(model)
    if not pattern:return []
    if str(model)[-1:].isdigit():pattern=re.compile(pattern.pattern.replace('(?![A-Z0-9])','(?![0-9])'),re.I)
    wanted=poles(spec.get('so_cuc') or spec.get('so_cuc_chinh'))
    return [r for r in rows if canonical_brand(r.get('brand'))==canonical_brand(brand)
        and explicit_family_compatible(model,r)
        and category_key(r.get('category'))==category_key(kind)
        and (not wanted or not row_poles(r) or wanted==row_poles(r))
        and pattern.search(' '.join(str(r.get(k) or '') for k in ('sku','item_name','name','group')))]


def information_rows(device,rows=None):
    rows=source_rows() if rows is None else rows
    from .catalog_product_sections import pole_compatible, coil_compatible, aux_contacts_compatible
    references=device.get('catalog_references') or {}
    maker=canonical_brand(device.get('brand'))
    if maker:
        rows=[row for row in rows if canonical_brand(row.get('brand'))==maker]
        own_ids={row['id'] for row in rows}
        references={**references,'options':[o for o in references.get('options',[])
            if canonical_brand(o.get('brand'))==maker or (not o.get('brand') and o.get('source_row_id') in own_ids)]}
    # Some pricebooks repeat a model/pole pair for physically different terminals.
    # A reviewed native body can explicitly restrict links to the source row IDs
    # that actually describe its mounting/terminal configuration. Fail closed.
    if references.get('source_row_scope')=='explicit_only':
        allowed={o.get('source_row_id') for o in references.get('options',[]) if o.get('source_row_id')}
        rows=[row for row in rows if row.get('id') in allowed]
    rows=[row for row in rows if pole_compatible(device,row) and coil_compatible(device,row) and aux_contacts_compatible(device,row)]
    kind=references.get('category') or device.get('type')
    selected={}
    index=price_index(rows)
    observed=list((device.get('source_identification') or {}).get('source_models_read') or [])
    if device.get('product_code'):observed.append(device['product_code'])
    for row in rows:
        if not str(row.get('id') or '').startswith('external:'):continue
        if device.get('brand') and canonical_brand(device['brand'])!=canonical_brand(row.get('brand')):continue
        if any(explicit_family_compatible(label,row) and (pattern:=catalog_model_pattern(label)) and pattern.search(' '.join(str(row.get(k) or '') for k in ('sku','item_name','name'))) for label in observed):
            selected[row['id']]=(row,'documented_product_information',0)
    identity={'ma_dong_san_pham':device.get('product_code'),'ten_san_pham':device.get('display'),
              'hang_xac_nhan':device.get('brand'),'thong_so':device.get('spec') or {}}
    if device.get('brand') and device.get('product_code'):
        for row in named_family_rows(device['product_code'],device['brand'],kind,device.get('spec') or {},rows):
            selected[row['id']]=(row,'catalog_family_match',0)
        for row in reference_matches({'brand':device['brand'],'model':device['product_code']},kind,index):
            selected[row['id']]=(row,'catalog_family_match',0)
        for row,basis in matching_rows(identity,device,rows,kind):
            # A series-only fallback is useful catalog information, but never
            # establishes that this particular frame is the priced CAD body.
            selected[row['id']]=(row,basis,1 if basis=='catalog_series_reference' else 0)
        # Compare complete, explicit hyphenated model alternatives (MR-4,
        # MC-50a, AN-06D3), never series prefixes. Configuration suffixes
        # may continue after a hyphen or parenthesis.
        codes=re.split(r'\s+/\s+',str(device['product_code']))
        for row in rows:
            if category_key(row.get('category'))!=category_key(kind):continue
            if any(re.match(re.escape(code)+r'(?=$|[\s(/-])',str(row.get('sku') or ''),re.I)
                   for code in codes if re.fullmatch(r'[A-Z]+-\d+[A-Z0-9]*',code,re.I)):
                selected[row['id']]=(row,'catalog_family_match',0)
    # Resolve explicit row IDs first, retaining unpriced rows and their original cells.
    by_id={r['id']:r for r in rows}
    pools={}
    for row in rows:pools.setdefault((canonical_brand(row.get('brand')),category_key(row.get('category'))),[]).append(row)
    by_brand={}
    for option in references.get('options',[]):
        for row in reference_matches(option,kind,index):
            selected.setdefault(row['id'],(row,option.get('basis') or 'catalog_reference',1))
        source=by_id.get(option.get('source_row_id'))
        if source:
            reviewed=(references.get('source_row_scope')=='explicit_only' and references.get('row_links_reviewed') is True)
            if reviewed:
                # A broad option lookup may already have found this row as a
                # candidate. The reviewed, exact row ID takes precedence after
                # brand/pole/coil/contact and explicit scope filters above.
                selected[source['id']]=(source,option.get('basis') or 'catalog_reference',0)
            else:
                selected.setdefault(source['id'],(source,option.get('basis') or 'catalog_reference',1))
        brand=canonical_brand(option.get('brand'))
        if brand and option.get('model'):by_brand.setdefault(brand,[]).append(option['model'])
    for brand,models in by_brand.items():
        for model in dict.fromkeys(models):
            for row in named_family_rows(model,brand,kind,device.get('spec') or {},pools.get((brand,category_key(kind)),[])):
                selected.setdefault(row['id'],(row,'catalog_reference',1))
            raw={'ma_dong_san_pham':model,'hang_xac_nhan':brand,'thong_so':device.get('spec') or {}}
            for row,basis in matching_rows(raw,{'type':kind},pools.get((brand,category_key(kind)),[]),kind):
                if basis=='catalog_series_reference':continue
                selected.setdefault(row['id'],(row,basis,1))
    result=[]
    for row,basis,priority in sorted(selected.values(),key=lambda r:(r[2],canonical_brand(r[0].get('brand')),r[0].get('source_page') or 0,str(r[0].get('sku')))):
        if not row.get('sku') and not row.get('item_name'):continue
        item={k:row.get(k) for k in ('sku','item_name','name','brand','category','group','columns','cells',
             'specifications','source_url','source_label','source_page','edition','effective_date','vat_status','vat_rate_percent','vat_rate_evidence','information_kind')}
        item['information_kind']=item.get('information_kind') or ('pricebook' if row.get('source_kind')=='supplier_pricebook' else 'manufacturer_catalog')
        item.update(id=hashlib.sha256(row['id'].encode()).hexdigest()[:24],price=optional_price(row.get('price')),
            basis=basis,identity_verified=False,match_scope='source_family' if priority==0 else 'catalog_reference')
        item['item_name']=item.get('item_name') or item.get('name') or item['sku']
        item['book_key']=hashlib.sha256(json.dumps([item.get(k) for k in ('brand','group','source_url','source_page','edition','columns')],ensure_ascii=False).encode()).hexdigest()[:24]
        item['columns']=item.get('columns') or ['Tên hàng','Mã hàng','Thông tin']
        item['cells']=item.get('cells') or [item['item_name'],item['sku'],json.dumps(item.get('specifications') or {},ensure_ascii=False)]
        result.append(item)
    existing={(canonical_brand(r['brand']),r['sku']) for r in result}
    for option in references.get('options',[]):
        brand=canonical_brand(option.get('brand'));model=str(option.get('model') or '').strip()
        from .customer_equipment_information import reference_specs
        specs=reference_specs(option.get('specifications'))
        if not pole_compatible(device,{'specifications':specs,'sku':model}):continue
        if not model or not specs or (brand,model) in existing:continue
        existing.add((brand,model))
        name=str(specs.get('Tên hàng') or model)
        detail='; '.join(f'{k}: {v}' for k,v in specs.items() if k!='Tên hàng')
        identifier=hashlib.sha256(json.dumps([brand,model,option.get('source_url')],ensure_ascii=False).encode()).hexdigest()[:24]
        result.append({'id':identifier,'book_key':'catalog-information-'+brand,'brand':brand,'sku':model,
            'item_name':name,'name':name,'group':'Thông tin catalog bổ sung','specifications':specs,
            'source_url':option.get('source_url'),'source_page':option.get('source_page'),
            'columns':['Tên hàng','Mã hàng','Thông số'],'cells':[name,model,detail],
            'price':optional_price(option.get('price')),'basis':option.get('basis'),
            'information_kind':'catalog_reference',
            'identity_verified':False,'match_scope':'catalog_reference'})
    return result
