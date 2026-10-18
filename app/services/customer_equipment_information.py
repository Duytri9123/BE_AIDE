"""Customer contract: product facts and public external references only.

Internal evidence remains available to recognition services, never to the UI.
"""
import re
import hashlib
import ipaddress
from urllib.parse import urlparse
from .ai.manufacturer_registry import canonical_brand

INTERNAL=re.compile(r'CatalogTB|thong_tin_|TuLieuBanVe|SOURCE[-_]|SRC_|cluster\d|sha256|checksum|fingerprint|provenance|(?<![A-Z])[A-Z]:[\\/]|nguồn (?:CAD|DWG|hệ thống|bóc)|hồ sơ nguồn|nhãn (?:CAD|block)|bóc tách|trang tài liệu|căn cứ',re.I)
PRIVATE_KEYS=re.compile(r'^nguon$|^nguồn$|nguon_cad|nhan_block|nhan_tren_hinh|tom_tat|luu_y|source|checksum|fingerprint|profile|file|handle|evidence|basis|căn cứ|phạm vi|trang tài liệu|nhan_dien|review|trên nguồn|từ nguồn|nhãn thông số',re.I)
DRAWING_KEYS=re.compile(r'(?:^|_)cad(?:_|$)|nhan_tren|nhan_nhin|nhan_nguon|ban_ve|ung_vien|tham_khao|theo_hinh|^so_hinh|^so_ban_ve|cac_ma_dung_chung',re.I)


def external_url(value):
    if not isinstance(value,str):return ''
    url=urlparse(value)
    host=(url.hostname or '').lower()
    if url.scheme!='https' or not host or host in {'localhost','127.0.0.1','0.0.0.0'}:return ''
    if host.endswith(('.local','.internal')):return ''
    try:
        if not ipaddress.ip_address(host).is_global:return ''
    except ValueError:pass
    if url.username or url.password or INTERNAL.search(value):return ''
    return value


def public_view_id(value):
    return 'v-'+hashlib.sha256(value.encode()).hexdigest()[:20]


def product_specs(spec):
    return {key:value for key,value in (spec or {}).items() if not PRIVATE_KEYS.search(key) and not DRAWING_KEYS.search(key)
            and value is not None and value!='' and str(value).strip().casefold() not in {'chưa xác định','{}','[]','null'}
            and not re.match(r'^(?:chọn\b|dòng định mức in:\s*chọn)',str(value).strip(),re.I)
            and not INTERNAL.search(str(value))}


def reference_specs(spec):
    # Drawing measurements and generic installation prose are not product facts.
    return {k:v for k,v in product_specs(spec).items()
            if not re.search(r'hình chiếu|lắp đặt tham khảo|kích thước.*(?:CAD|bản vẽ)',k,re.I)}


def reference_options(device):
    own={};other={};maker=canonical_brand(device.get('brand'))
    from .catalog_other_manufacturers import other_manufacturer_options
    original=(device.get('catalog_references') or {}).get('options',[])
    known={(canonical_brand(o.get('brand')),str(o.get('model') or '').casefold()) for o in original}
    registry=[o for o in other_manufacturer_options(device)
              if (canonical_brand(o.get('brand')),str(o.get('model') or '').casefold()) not in known]
    options=[*original,*registry]
    for option in options:
        model=str(option.get('model') or '').strip();brand=canonical_brand(option.get('brand'))
        if not model or model.startswith('*') or INTERNAL.search(model) or not brand:continue
        specs=reference_specs(option.get('specifications'))
        from .catalog_product_sections import pole_compatible
        if not pole_compatible(device,{'specifications':specs,'sku':model}):continue
        if not specs:continue
        bucket=other if maker and brand!=maker else own
        key=(brand,model.casefold())
        item={'brand':brand,'model':model,'specifications':specs,
              'source_url':external_url(option.get('source_url')),'basis':'product_reference',
              'price':option.get('price') if isinstance(option.get('price'),(int,float)) and not isinstance(option.get('price'),bool) else None}
        if key in bucket:
            previous=bucket[key]
            previous['specifications'].update({k:v for k,v in specs.items() if k not in previous['specifications']})
            if previous['price']!=item['price']:previous['price']=None
            if not previous['source_url']:previous['source_url']=item['source_url']
        else:bucket[key]=item
    return list(own.values()),list(other.values())


def customer_device(device):
    fields=('id','display','brand','type','category','product_code','spec_hint','primary_view',
            'brand_label','brand_kind','brand_identification_status','use','placement')
    out={k:device[k] for k in fields if k in device}
    out['brand_identification_status']='verified' if device.get('brand_identification_status')=='verified' else 'candidate' if device.get('brand') else 'unknown'
    out['type']={'SOURCE_REFERENCE':'DRAWING','ASSEMBLY_REFERENCE':'ASSEMBLY'}.get(out.get('type'),out.get('type'))
    out['display']=re.sub(r'mẫu nguồn','Mẫu thiết bị',str(out.get('display') or ''),flags=re.I)
    out['display']=re.sub(r'\s*·\s*nhãn CAD','',out['display'],flags=re.I)
    if INTERNAL.search(out['display']):out['display']=' '.join(str(out.get(k) or '') for k in ('type','brand')).strip() or 'Thiết bị'
    for key in ('use','placement','spec_hint'):
        if INTERNAL.search(str(out.get(key) or '')):out.pop(key,None)
    if INTERNAL.search(str(out.get('product_code') or '')):out.pop('product_code',None)
    out['spec']=product_specs(device.get('spec'))
    out['views']=[]
    for view in device.get('views',[]):
        item={k:view[k] for k in ('label','face','preview','download') if k in view}
        item['id']=public_view_id(view['id'])
        for key in ('label','face'):
            if INTERNAL.search(str(item.get(key) or '')):item[key]='Bản vẽ'
        for key in ('preview','download'):
            if item.get(key):item[key]=re.sub(r'/views/[^/]+/',f'/views/{item["id"]}/',item[key])
        out['views'].append(item)
    if device.get('primary_view'):out['primary_view']=public_view_id(device['primary_view'])
    maker=canonical_brand(device.get('brand'))
    options,other=reference_options(device)
    out['catalog_references']={'options':options}
    out['other_brand_references']=other
    out['reference_product_codes']=list(dict.fromkeys(o['model'] for o in options))
    doc=external_url(device.get('manufacturer_document'))
    if doc:out['manufacturer_document']=doc
    return out


def customer_browser(payload):
    out={k:v for k,v in payload.items() if k in {'categories','brands','total','view_count','skip','limit'}}
    out['labels']=product_specs(payload.get('labels'))
    out['items']=[customer_device(d) for d in payload['items']]
    return out


def customer_information_rows(rows,device):
    maker=canonical_brand(device.get('brand'));out=[]
    for row in rows:
        if str(row.get('sku') or '').startswith('*'):continue
        if maker and canonical_brand(row.get('brand'))!=maker:continue
        item={k:row[k] for k in ('id','book_key','sku','item_name','name','brand','category','group','price','columns','cells','edition','vat_status','information_kind','compatibility_note') if k in row}
        item['specifications']=product_specs(row.get('specifications'))
        item['source_url']=external_url(row.get('source_url'))
        if item.get('information_kind')=='pricebook':
            # A page boundary is not a new price table. Keep book identity opaque
            # while letting the UI join identical sections across source pages.
            item['book_key']=hashlib.sha256(repr(tuple(row.get(k) for k in
                ('brand','source_url','edition','effective_date'))).encode()).hexdigest()[:24]
        # Source-only metadata is not a product specification or table column.
        pairs=[]
        for index,column in enumerate(item.get('columns',[])):
            value=(item.get('cells') or [])[index] if index<len(item.get('cells') or []) else ''
            if PRIVATE_KEYS.search(column):continue
            if isinstance(value,str):
                value='; '.join(part.strip() for part in re.split(r'\r?\n|;\s*',value)
                    if not INTERNAL.search(part) and not re.match(r'\s*phạm vi\s*:',part,re.I))
            pairs.append((column,value))
        item['columns']=[p[0] for p in pairs];item['cells']=[p[1] for p in pairs]
        if item.get('information_kind') in {'price_reference','manufacturer_catalog','catalog_reference','device'} or not item['columns']:
            # Discovery offers carry structured facts rather than source-table
            # columns. Publish those facts instead of an empty one-cell table.
            item['columns']=['Tên hàng','Mã hàng','Thông số','Đơn giá']
            item['cells']=[item.get('item_name') or item.get('name') or item.get('sku') or '',
                item.get('sku') or '',
                '; '.join(f'{key}: {value}' for key,value in item['specifications'].items()),'']
        if not any(INTERNAL.search(str(item.get(k) or '')) for k in ('sku','item_name','name','group')):out.append(item)
    if not out:
        spec=product_specs(device.get('spec'))
        name=customer_device(device)['display'];model=device.get('product_code') or 'Chưa có mã sản phẩm'
        out=[{'id':device['id'],'book_key':'device-information','brand':device.get('brand') or 'Chưa xác định',
            'sku':model,'item_name':name,'name':name,'group':'Thông tin thiết bị','price':None,
            'columns':['Tên thiết bị','Mã / dòng','Thông số'],
            'cells':[name,model,'; '.join(f'{k}: {v}' for k,v in spec.items()) or 'Thông số đang được bổ sung'],
            'specifications':spec,'source_url':'','information_kind':'device'}]
    return out
