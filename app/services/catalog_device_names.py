"""Concise CHINT names from the selected CAD family, never unrelated catalog options."""
import re
from .catalog_product_sections import device_poles

LABELS={'PUSHBUTTON':'Nút nhấn','PUSH':'Nút nhấn','INDICATOR':'Đèn báo','LIGHT':'Đèn báo',
        'SELECTOR':'Công tắc chọn','CONTACTOR':'Khởi động từ','TRANSFORMER':'Biến áp điều khiển',
        'TIMER':'Rơ le thời gian','RELAY':'Rơ le','PHASERELAY':'Rơ le bảo vệ pha',
        'PHASE_RELAY':'Rơ le bảo vệ pha','FUSEASSEMBLY':'Bộ cầu chì','FUSE':'Cầu chì','ATS':'ATS'}
BREAKERS={'MCB','MCCB','RCBO','RCCB','ACB'}

def _numbers(value):
    return [float(n.replace(',','.')) for n in re.findall(r'\d+(?:[.,]\d+)?',str(value or ''))]

def _row_poles(option):
    spec=option.get('specifications') or {}
    poles=device_poles({'spec':spec,'display':option.get('model')})
    if poles:return poles
    # CHINT NXM ordering syntax encodes poles as the first digit after '/'.
    match=re.match(r'NXM-\d+[A-Z]+/([234])\d{3}',str(option.get('model') or ''),re.I)
    return match[1]+'P' if match else None

def apply_device_name(profile):
    if str(profile.get('brand') or '').upper()!='CHINT':return False
    kind=str(profile.get('type') or '').upper();model=str(profile.get('product_code') or '').strip().upper()
    spec=profile.get('spec') or {};previous=str(profile.get('display') or '')
    if kind in BREAKERS:
        # A shared frame without a pole/rating suffix must not inherit S/H or a
        # different pole count from suggested products in the reference table.
        if not model:return False
        poles=device_poles(profile);parts=[kind+' CHINT '+model]
        if poles:parts.append(poles)
        options=[]
        if poles:
            for option in (profile.get('catalog_references') or {}).get('options',[]):
                if str(option.get('brand') or '').upper()!='CHINT':continue
                if not re.match(re.escape(model)+r'(?![A-Z0-9-])',str(option.get('model') or ''),re.I):continue
                if _row_poles(option)!=poles:continue
                options.append(option)
        currents=set();ratings={key:set() for key in ('Icu','Icn','Inc')}
        for option in options:
            values=option.get('specifications') or {}
            for key,value in values.items():
                normalized=str(key).strip().lower()
                if normalized in {'in','in (a)','dòng định mức (a)','dòng định mức'}:currents.update(_numbers(value))
                for designation in ratings:
                    if normalized==designation.lower():ratings[designation].update(_numbers(value))
        if currents:
            low,high=min(currents),max(currents)
            parts.append((format(low,'g') if low==high else format(low,'g')+'–'+format(high,'g'))+' A')
        for designation,values in ratings.items():
            if values:parts.append(designation+' '+ '/'.join(format(v,'g') for v in sorted(values))+' kA')
        if not poles:parts.append('CAD tham khảo')
        profile['display']=' · '.join(parts)
        if currents or any(ratings.values()):
            profile['spec_hint']='Dải mã tham khảo · kiểm tra điện áp và cấu hình khi chọn'
        return True
    if kind not in LABELS:return False
    parts=[LABELS[kind]+' CHINT'+(' '+model if model else '')]
    if kind in {'PUSHBUTTON','PUSH'}:
        contact=spec.get('tiep_diem_tren_cad')
        if contact in {'NC','NO','1NO+1NC'}:parts.append(contact)
        else:
            source_tag=re.search(r'\bNB[CD]+\b',previous)
            if source_tag:parts.append(source_tag[0])
        if spec.get('head_shape_reference') in {'đầu tròn','đầu nhô'}:parts.append(spec['head_shape_reference'])
    elif kind=='CONTACTOR':
        # This reviewed drawing explicitly covers both NCH8-20 and NCH8-25.
        if not model and (('NCH8-20' in previous and 'NCH8-25' in previous) or 'NCH8-20/25' in previous):parts[0]+=' NCH8-20/25'
        poles=device_poles(profile)
        if poles:parts.append(poles)
        current=spec.get('dong_dinh_muc')
        if current:parts.append(str(current))
    elif kind in {'PHASERELAY','PHASE_RELAY'}:
        voltage=spec.get('dien_ap_tham_khao') or spec.get('Điện áp ghi trong block nguồn')
        if voltage:parts.append(str(voltage))
    elif kind=='ATS':
        poles=device_poles(profile)
        if poles:parts.append(poles)
    elif kind=='TRANSFORMER' and not model:parts.append('CAD tham khảo')
    elif kind in {'FUSE','FUSEASSEMBLY'} and '160A' in previous.replace(' ',''):parts.append('160 A')
    elif kind=='TIMER' and spec.get('tiep_diem_tham_khao'):parts.append(spec['tiep_diem_tham_khao'])
    elif kind in {'INDICATOR','LIGHT'} and 'FAULT' in previous:parts.append('FAULT')
    profile['display']=' · '.join(parts)
    return True
