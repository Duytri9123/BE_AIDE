"""Explicit material annotations are source evidence, not electrical glyphs."""
import re
from app.services.ingestion.cad_source_evidence import plain


def material_annotation(row):
    quote=str(row.get('observed_text') or '')
    name=plain(' '.join(str(row.get(k) or '') for k in ('category','name')))
    kind='BUTTON' if re.search(r'NUT (?:AN|NHAN)|BUTTON',name) else 'FAN' if re.search(r'QUAT TAN NHIET|\bFAN\b',name) else None
    pattern=r'(?<!\d)(\d+)\s*NUT\s+(?:AN|NHAN)' if kind=='BUTTON' else r'(?<!\d)(\d+)\s*QUAT\s+TAN\s+NHIET' if kind=='FAN' else None
    text=plain(quote)
    matches=list(re.finditer(pattern,text)) if pattern else []
    totals=[m for m in matches if not re.search(r'MOI LO\s*$',text[max(0,m.start()-18):m.start()])
            and not re.match(r'\s*/\s*LO',text[m.end():])]
    quantities={int(m[1]) for m in totals}
    if len(quantities)!=1 or row.get('quantity') not in quantities:return None
    return {'category':kind,'quantity':row['quantity'],'text':quote}


def native_material_notes(evidence,parts):
    labels=evidence.get('labels',[]);bounds=evidence.get('view_bounds')
    if not bounds or not parts:return
    left,bottom,right,top=bounds
    existing={str(((r.get('source_observations') or {}).get('material_annotation') or {}).get('text') or '')
              for p in parts for r in p['devices']}
    for label in labels:
        text=label['text']
        match=re.search(r'(?<!\d)(\d+)\s*QUAT\s+TAN\s+NHIET',plain(text))
        if not match or not label.get('bounds') or text in existing:continue
        # Existing matching material rows keep their identity; do not add twice.
        found=next(((p,i,r) for p in parts for i,r in enumerate(p['devices'])
                    if material_annotation(r) and plain(r.get('observed_text'))==plain(text)),None)
        if not found:
            candidates=[(p,i,r) for p in parts for i,r in enumerate(p['devices'])
                        if (material_annotation(r) or {}).get('category')=='FAN'
                        and r.get('quantity')==int(match[1])]
            source_notes=[l for l in labels if re.search(r'(?<!\d)\d+\s*QUAT\s+TAN\s+NHIET',plain(l['text']))]
            if len(candidates)==1 and len(source_notes)==1:found=candidates[0]
        if found:part,index,row=found
        else:
            part=parts[0];index=len(part['devices'])
            row={'category':'FAN','name':'Quạt tản nhiệt tủ','spec':'','quantity':int(match[1]),
                 'drawing_quantity':0,'unit':'Cái','record_kind':'equipment','observed_text':text,
                 'electrical_function':'Thông gió và tản nhiệt cho tủ điện',
                 'quantity_basis':text,'source_evidence_ids':[label['id']]}
            part['devices'].append(row)
        observed=row.get('source_observations') or {}
        row.update(observed_text=text,source_evidence_ids=[label['id']])
        row['source_observations']={**observed,'material_annotation':material_annotation(row)}
        b=label['bounds'];box=[(top-b[3])/(top-bottom)*1000,(b[0]-left)/(right-left)*1000,
                               (top-b[1])/(top-bottom)*1000,(b[2]-left)/(right-left)*1000]
        part['boxes']=[b for b in part['boxes'] if str(b.get('device_id'))!=str(index)]
        part['boxes'].append({'device_id':str(index),'verified':True,'evidence_kind':'material_note',
                              'text_box_2d':box,'symbol_box_2d':box})
        existing.add(text)
