"""Choose economical products within the requested brand; keep alternatives separate."""
from copy import deepcopy
from app.services.ai.manufacturer_registry import canonical_brand
from app.services.ai.takeoff_pricebook import match_device,published_rows

MAJOR_BRANDS={'LS Electric','Schneider Electric','ABB','Mitsubishi Electric','Siemens','CHINT'}

def apply_product_policy(devices,rows=None):
    rows=published_rows() if rows is None else rows
    cache={}
    for device in devices:
        data=device if isinstance(device,dict) else device.model_dump()
        def put(key,value):
            if isinstance(device,dict):device[key]=value
            else:setattr(device,key,value)
        if data.get('category')=='METER':
            put('name','Đồng hồ đa năng')
        if data.get('selection_source')!='user_request' or not data.get('brand'):
            continue
        brand=canonical_brand(data['brand'])
        # User-selected products bypass this policy; generic brand requests choose
        # by electrical requirements rather than an earlier AI-proposed order code.
        if not data.get('poles') or not data.get('in_a'):
            continue
        key=tuple(str(data.get(k) or '') for k in ('brand','category','spec','poles','in_a','icu_ka','part_number'))
        if key not in cache:
            own=match_device({**data,'part_number':'','sku':'','selected_product':None},rows)['candidates']
            own=[r for r in own if canonical_brand(r['brand'])==brand and isinstance(r.get('price'),(int,float)) and r['price']>0
                 and not (r.get('specifications') or {}).get('Phạm vi giá')]
            own.sort(key=lambda r:(r['price'],r['sku']))
            alternatives=[]
            for maker in sorted(MAJOR_BRANDS-{brand}):
                query={**data,'brand':maker,'detected_brand':'','part_number':'','sku':'','selected_product':None,'selection_source':'alternative'}
                candidates=match_device(query,rows)['candidates']
                candidate=next((c for c in candidates if isinstance(c.get('price'),(int,float)) and c['price']>0 and not (c.get('specifications') or {}).get('Phạm vi giá')),None)
                if candidate:
                    alternatives.append({**candidate,'requires_confirmation':True,'reason':'Gợi ý thay thế cùng thông số đã biết; cần kiểm tra điều kiện còn thiếu trước khi đổi hãng.'})
            cache[key]=(own,alternatives)
        own,alternatives=deepcopy(cache[key])
        put('suggested_alternatives',alternatives)
        put('catalog_candidates',{data['brand']:own})
        if not own:continue
        choice=own[0]
        complete=bool(data.get('icu_ka')) if data.get('category') in {'MCB','MCCB'} else False
        choice.update(auto_selectable=complete,rating_complete=complete,requires_confirmation=not complete,
                      selection_reason='Giá công bố thấp nhất trong các mã cùng hãng khớp thông số đã biết.'
                      +('' if complete else ' Chưa đủ khả năng cắt/cấu hình; đây là mã đề xuất, chưa chốt giá.'))
        put('part_number',choice['sku'])
        put('selected_product',choice)
        put('pricebook_match',{'status':'matched' if complete else 'needs_selection','row':choice if complete else None,
            'price_row_id':choice['price_row_id'] if complete else None,'candidates':own,'note':choice['selection_reason']})
    return devices
