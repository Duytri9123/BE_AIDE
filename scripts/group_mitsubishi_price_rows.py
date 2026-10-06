"""Present repeated amperage rows like LS without losing PDF line details."""
import json
import re


GROUP_CATEGORIES={'MCCB','ELCB','MCB','RCBO','RCCB'}

PRODUCT_NAMES={
    'MCCB':'Cầu dao tự động dạng khối (MCCB)',
    'MCB':'Cầu dao tự động (MCB)',
    'ELCB':'Thiết bị chống dòng rò (ELCB)',
    'RCBO':'Thiết bị RCBO',
    'RCCB':'Thiết bị RCCB',
    'Contactor':'Khởi động từ (Contactor)',
}


def signature(row):
    current=row['current_a_pdf']
    spec=row['spec_display']
    if not current:
        return None
    pattern=r'(?<![\d.])'+re.escape(str(current))+r'\s*A\b'
    replacement,count=re.subn(pattern,'{In}',spec,count=1)
    if count!=1:
        return None
    return ' '.join(replacement.split())


def group_rows(rows):
    groups={}
    for row in rows:
        sig=signature(row) if row['category'] in GROUP_CATEGORIES else None
        if row['model'] and sig:
            key=(row['model'],row['pole_display'],row['price_vnd'],row['page'],
                 row['category'],row['cad_state_id'],sig)
        else:
            key=('single',row['row_id'])
        groups.setdefault(key,[]).append(row)

    result=[]
    for members in groups.values():
        first=members[0]
        item={k:v for k,v in first.items() if k not in ('source_line','description_pdf')}
        item['display_id']=len(result)+1
        item['row_count']=len(members)
        item['source_row_ids']=[m['row_id'] for m in members]
        item['source_variants']=[{
            'row_id':m['row_id'],'current_a_pdf':m['current_a_pdf'],
            'material_code':m['material_code'],'description_pdf':m['description_pdf'],
            'page':m['page'],'line':m['line']}
            for m in members]
        currents=list(dict.fromkeys(m['current_a_pdf'] for m in members if m['current_a_pdf']))
        if len(members)>1:
            item['current_display']='-'.join(currents)+'A'
            item['spec_group']=re.sub(r'\s+',' ',signature(first).replace('{In}','')).strip()
        else:
            item['current_display']=(currents[0]+'A') if currents else None
            item['spec_group']=first['spec_display']
        parts=[PRODUCT_NAMES.get(first['category'],first['category'])]
        pole=first['pole_display']
        if pole:
            parts.append((pole.replace('P+N',' cực + N') if 'P+N' in pole else pole.replace('P',' cực')))
        if item['current_display']:
            parts.append(('AC-3 (380–440 V): ' if first.get('ac3_current_a_380_440v_pdf') else 'In: ')+item['current_display'])
        if first.get('ac3_kw_400v_pdf'):
            parts.append('AC-3 (400 V): '+first['ac3_kw_400v_pdf']+' kW')
        if first.get('auxiliary_contacts_pdf'):
            parts.append('Tiếp điểm phụ: '+first['auxiliary_contacts_pdf']+' (a=NO, b=NC)')
        if first.get('coil_voltage_pdf'):
            parts.append('Cuộn hút: '+first['coil_voltage_pdf'])
        extra=re.sub(r'^\s*[1-4]P(?:N)?\b\s*','',item['spec_group']).strip()
        if len(members)==1 and first['current_a_pdf']:
            extra=re.sub(r'(?<![\d.])'+re.escape(first['current_a_pdf'])+r'\s*A\b','',extra,count=1).strip()
        if extra:
            parts.append('Thông số PDF: '+extra)
        item['product_description']=' · '.join(parts)
        item['search_text']=' '.join(str(value or '') for m in members for value in
                                     (m['model'],m['description_pdf'],m['material_code']))
        result.append(item)
    return result


def write_grouped(base, rows):
    grouped=group_rows(rows)
    (base/'price_grouped.json').write_text(
        json.dumps(grouped,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return grouped
