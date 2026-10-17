"""Customer contract: product facts and public external references only.

Internal evidence remains available to recognition services, never to the UI.
"""
import re
import hashlib
import ipaddress
from urllib.parse import urlparse
from .ai.manufacturer_registry import canonical_brand

INTERNAL=re.compile(r'CatalogTB|thong_tin_|TuLieuBanVe|SOURCE[-_]|SRC_|cluster\d|sha256|checksum|fingerprint|provenance|(?<![A-Z])[A-Z]:[\\/]|nguồn (?:CAD|DWG|hệ thống|bóc)|hồ sơ nguồn|nhãn (?:CAD|block)|bóc tách|trang tài liệu|căn cứ',re.I)
PRIVATE_KEYS=re.compile(r'nguon_cad|nhan_block|nhan_tren_hinh|tom_tat|luu_y|source|checksum|fingerprint|profile|file|handle|evidence|basis|căn cứ|phạm vi|trang tài liệu|nhan_dien|review|trên nguồn|từ nguồn|nhãn thông số',re.I)


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
    return {key:value for key,value in (spec or {}).items() if not PRIVATE_KEYS.search(key)
            and value is not None and value!='' and not INTERNAL.search(str(value))}


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
    options=[]
    for option in (device.get('catalog_references') or {}).get('options',[]):
        if str(option.get('model') or '').startswith('*') or INTERNAL.search(str(option.get('model') or '')):continue
        if maker and canonical_brand(option.get('brand'))!=maker:continue
        specs=product_specs(option.get('specifications'))
        if not specs:continue
        item={k:option[k] for k in ('brand','model','price') if k in option}
        item.update(specifications=specs,source_url=external_url(option.get('source_url')),basis='product_reference')
        options.append(item)
    out['catalog_references']={'options':options}
    out['reference_product_codes']=list(dict.fromkeys(o['model'] for o in options))
    doc=external_url(device.get('manufacturer_document'))
    if doc:out['manufacturer_document']=doc
    candidates=[]
    for candidate in device.get('visual_candidates',[]):
        models=[m for m in candidate['models'] if not maker or canonical_brand(m['brand'])==maker]
        if not models:continue
        candidates.append({'comparison_name':re.sub(r'mẫu nguồn','Mẫu thiết bị',candidate['comparison_name'],flags=re.I),
            'comparison_preview':re.sub(r'/views/([^/]+)/',lambda m:'/views/'+public_view_id(m[1])+'/',candidate['comparison_preview']),
            'models':models,'documents':[{'url':url} for d in candidate.get('documents',[]) if (url:=external_url(d.get('url')))],
            'identity_verified':False})
    if candidates:out['visual_candidates']=candidates
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
        item={k:row[k] for k in ('id','book_key','sku','item_name','name','brand','category','group','price','columns','cells','edition','vat_status') if k in row}
        item['specifications']=product_specs(row.get('specifications'))
        item['source_url']=external_url(row.get('source_url'))
        # Source-only metadata is not a product specification or table column.
        pairs=[]
        for column,value in zip(item.get('columns',[]),item.get('cells',[])):
            if PRIVATE_KEYS.search(column):continue
            if column.casefold() in {'thông số','thông tin'} and row.get('specifications'):
                value='; '.join(f'{k}: {v}' for k,v in item['specifications'].items())
            if not INTERNAL.search(str(value)):pairs.append((column,value))
        item['columns']=[p[0] for p in pairs];item['cells']=[p[1] for p in pairs]
        if not any(INTERNAL.search(str(item.get(k) or '')) for k in ('sku','item_name','name','group')):out.append(item)
    if not out:
        spec=product_specs(device.get('spec'))
        name=customer_device(device)['display'];model=device.get('product_code') or 'Chưa có mã sản phẩm'
        out=[{'id':device['id'],'book_key':'device-information','brand':device.get('brand') or 'Chưa xác định',
            'sku':model,'item_name':name,'name':name,'group':'Thông tin thiết bị','price':None,
            'columns':['Tên thiết bị','Mã / dòng','Thông số'],
            'cells':[name,model,'; '.join(f'{k}: {v}' for k,v in spec.items()) or 'Thông số đang được bổ sung'],
            'specifications':spec,'source_url':''}]
    return out
