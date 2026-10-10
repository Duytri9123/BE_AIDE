"""Compare independent schematic, quotation and CAD facts without hiding changes."""
from __future__ import annotations
import re
import unicodedata

FIELDS=('category','quantity','poles','pole_designation','current_a','breaking_capacity_ka','residual_current_ma','model','brand','mounting_face')


def normalize_text(value):
    value=''.join(c for c in unicodedata.normalize('NFD',str(value or '')) if not unicodedata.combining(c))
    return re.sub(r'\s+',' ',value.replace('đ','d').replace('Đ','D')).strip().upper()


def selected_number(text, unit):
    values=re.findall(r'(\d+(?:[.,]\d+)?)\s*'+unit+r'\b',text,re.I)
    return float(values[-1].replace(',','.')) if values else None


def quote_spec(text):
    # The quote may explicitly contain an engineering change such as 16A => 20A.
    n=normalize_text(text);pol=re.search(r'(?<!\d)(\d+)\s*P(?:\s*\+\s*N)?\b',n)
    category=next((x for x in ['RCBO','RCCB','MCCB','MCB','CONTACTOR'] if re.search(r'\b'+x+r'\b',n)),None)
    return {'category':category,'poles':int(pol[1]) if pol else None,
            'current_a':selected_number(n,r'A'),'breaking_capacity_ka':selected_number(n,r'K\s*A'),
            'residual_current_ma':selected_number(n,r'M\s*A'),'original_text':text,
            'has_explicit_revision':'=>' in text or '→' in text,
            'pole_designation':pol[0] if pol else None}


def compare_item(key, observations, fields=FIELDS):
    """Unknown is different from absent and can never certify a match."""
    checks=[]
    for field in fields:
        values={source:row.get(field) for source,row in observations.items()}
        known={source:value for source,value in values.items() if value is not None}
        if not known:status='unknown'
        elif len(known)!=len(observations):status='unresolved'
        else:
            normalized=[normalize_text(v) if isinstance(v,str) else v for v in known.values()]
            status='same' if all(v==normalized[0] for v in normalized) else 'different'
        checks.append({'field':field,'status':status,'values':values})
    differences=[c for c in checks if c['status']=='different']
    pending=[c for c in checks if c['status'] in ('unresolved','unknown')]
    status='different' if differences else 'unresolved' if pending else 'same'
    return {'key':key,'observations':observations,'checks':checks,'status':status,
            'differences':differences,'pending':pending,'release_ready':status=='same' and all(row.get('evidence') for row in observations.values())}


def release_review(items, unanalysed=None):
    unresolved=[r['key'] for r in items if not r.get('release_ready')]
    return {'release_ready':not unresolved and not unanalysed,'unresolved_items':unresolved,
            'unanalysed':unanalysed or [],'compared_items':len(items)}


def reconcile_devices(devices):
    items=[];missing=[]
    for i,device in enumerate(devices):
        key=device.get('tag') or device.get('name') or str(i)
        observations=device.get('source_observations') or {}
        if not all(source in observations for source in ('schematic','quotation','cad')):
            missing.append(str(key)+': thiếu bằng chứng độc lập sơ đồ/báo giá/CAD')
            continue
        items.append(compare_item(key,observations))
    result=release_review(items,missing)
    result['items']=items
    return result
