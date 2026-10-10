"""Use uniquely tagged CAD labels as quantity evidence, never count repeated text."""
import re
import copy
from collections import defaultdict
from app.core.device_patterns import DevicePatterns


def reconcile_tagged_labels(devices, texts, panel_count=1):
    if panel_count > 1:
        return devices, []
    labels = defaultdict(list)
    for text in texts:
        label = str(text.get('text') or '')
        tags = re.findall(r'\bQF\d+\b',label,re.I)
        matches = DevicePatterns.extract_all_devices(label)
        if len(tags)!=1 or len(matches)!=1:
            continue
        match=matches[0]
        if match.category not in ('MCB','MCCB','ACB','RCBO','RCCB') or not match.in_a or not match.poles:
            continue
        quantity=re.search(r'\b(?:QTY|SL)\s*[:=]?\s*(\d+)\b',label,re.I)
        labels[tags[0].upper()].append((match,int(quantity[1]) if quantity else 1))
    groups=defaultdict(list)
    for tag, occurrences in labels.items():
        keys={(m.category,m.in_a,m.poles,m.icu_ka,q) for m,q in occurrences}
        if len(keys)!=1:
            continue  # A reused/conflicting tag is not safe evidence of an extra device.
        match,qty=occurrences[0]
        if 0 < qty <= 100:
            groups[(match.category,float(match.in_a),int(match.poles))].append((tag,qty,match))
    result=list(devices)
    warnings=[]
    for key,sources in groups.items():
        candidates=[d for d in result if (str(d.category).upper(),float(d.in_a or 0),int(d.poles or 0))==key]
        if not candidates or any(d.panel_code != candidates[0].panel_code for d in candidates):
            continue
        if len(candidates)>1 and any(d.tag and d.tag.upper() not in {s[0] for s in sources} for d in candidates):
            continue
        mapped=[]
        for tag,qty,match in sources:
            specific=next((d for d in candidates if str(d.tag or '').upper()==tag),None)
            if specific is None and len(candidates)!=1:
                mapped=[]
                break
            original=specific or candidates[0]
            updates={'tag':tag,'quantity':qty,'drawing_quantity':qty,
                'procurement_quantity':qty,'quantity_basis':'unique_tagged_cad_label',
                'icu_ka':match.icu_ka if match.icu_ka is not None else original.icu_ka}
            device=copy.copy(original)
            for field,value in updates.items():
                setattr(device,field,value)
            mapped.append(device)
        if mapped:
            ids={id(d) for d in candidates}
            result=[d for d in result if id(d) not in ids]+mapped
            if sum(d.quantity for d in candidates)!=sum(d.quantity for d in mapped):
                warnings.append('Đối soát số lượng từ nhãn CAD riêng biệt: '+', '.join(s[0] for s in sources))
    return result,warnings
