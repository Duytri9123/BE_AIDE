"""Shared type/pole constraints for current products and replacement candidates."""
import re
from .catalog_family_matching import category_key
from .ai.manufacturer_registry import canonical_brand

BREAKERS={'MCB','MCCB','RCBO','RCCB','ACB','ISOLATOR'}

def current_kinds(value):
    text=str(value or '').upper()
    return {kind for kind in ('AC','DC') if re.search(r'(?<![A-Z])V?'+kind+r'(?![A-Z])',text)}

def auxiliary_contacts(value):
    text=str(value or '')
    m=re.search(r'(?<![A-Z0-9])(\d+)\s*A\s*(\d+)\s*B(?![A-Z0-9])',text,re.I)
    if m:return tuple(map(int,m.groups()))
    m=re.search(r'(\d+)\s*NO\s*[+/]\s*(\d+)\s*NC',text,re.I)
    return tuple(map(int,m.groups())) if m else None


def aux_contacts_compatible(device,row):
    if category_key(device.get('type'))!='CONTACTOR' or canonical_brand(device.get('brand'))!='LS Electric':return True
    expected=auxiliary_contacts((device.get('spec') or {}).get('Tiếp điểm phụ'))
    if expected is None:return True
    actual=auxiliary_contacts(' '.join([str(row.get('sku') or ''),*[str(v) for v in (row.get('specifications') or {}).values()]]))
    return actual==expected


def device_poles(device):
    spec=device.get('spec') or {}
    # GMP -2P/-3P denotes CT/protection configuration, not main power poles.
    if canonical_brand(device.get('brand'))=='LS Electric' and re.match(r'^GMP(?:22|40)(?:-|\b)',str(device.get('product_code') or ''),re.I) and not any(spec.get(k) for k in ('so_cuc','so_cuc_chinh','so_cuc_theo_nhan_hinh','Số cực')):return None
    text=str(spec.get('so_cuc') or spec.get('so_cuc_chinh') or spec.get('so_cuc_theo_nhan_hinh') or spec.get('Số cực') or device.get('display') or '').strip().upper()
    text=re.sub(r'(?<![A-Z0-9])([1-4])PN(?![A-Z0-9])',r'\1P+N',text)
    if re.fullmatch(r'[1-9]\d?',text):return text+'P'
    match=re.search(r'(?<![A-Z0-9])[1-9]\d?\s*P(?:\s*\+\s*N)?(?![A-Z0-9])',text)
    return re.sub(r'\s+','',match[0]) if match else None

def pole_compatible(device,row):
    wanted=device_poles(device)
    if not wanted:return True
    spec=row.get('specifications') or {}
    explicit=spec.get('Số cực') or spec.get('Poles') or spec.get('so_cuc')
    text=str(explicit or ' '.join(str(row.get(k) or '') for k in ('sku','model','item_name','name'))).upper()
    text=re.sub(r'(?<![A-Z0-9])([1-4])PN(?![A-Z0-9])',r'\1P+N',text)
    found={re.sub(r'\s+','',p) for p in re.findall(r'(?<![A-Z0-9])[1-9]\d?\s*P(?:\s*\+\s*N)?(?![A-Z0-9])',text)}
    if explicit and not found and re.fullmatch(r'[1-9]\d?',str(explicit).strip()):found={str(explicit).strip()+'P'}
    return found=={wanted}


def coil_compatible(device,row):
    if category_key(device.get('type')) != 'CONTACTOR':
        return True
    source=device.get('spec') or {}
    wanted=current_kinds(source.get('Loại cuộn hút') or source.get('Nguồn cuộn hút') or source.get('dien_ap_cuon_hut'))
    if not wanted:
        return True
    spec=row.get('specifications') or {}
    actual=current_kinds(spec.get('Loại cuộn hút') or spec.get('Điện áp cuộn hút') or ' '.join(str(row.get(k) or '') for k in ('item_name','name','group')))
    return bool(wanted & actual)

def candidate_rows(device,rows,other=False):
    maker=canonical_brand(device.get('brand'));kind=category_key(device.get('type'))
    if not maker or not kind or kind in {'DRAWING','SOURCE_REFERENCE','ASSEMBLY_REFERENCE'}:return []
    # Do not infer a breaker's pole configuration from its family name.
    if kind in BREAKERS and not device_poles(device):return []
    result=[]
    for row in rows:
        same=canonical_brand(row.get('brand'))==maker
        if same==other or category_key(row.get('category'))!=kind or not pole_compatible(device,row) or not coil_compatible(device,row) or not aux_contacts_compatible(device,row):continue
        model=str(row.get('sku') or '')
        if not model or model.casefold()==str(device.get('product_code') or '').casefold():continue
        spec=row.get('specifications') or {}
        source=device.get('spec') or {}
        if other and kind not in BREAKERS:
            anchors=1 if device_poles(device) else 0
            conflict=False;missing=[]
            comparisons=[
                (('dong_dinh_muc_A','dong_dinh_muc'),('In (A)','Dòng định mức (A)','In'),'dòng định mức'),
                (('dien_ap_cuon_hut',),('Điện áp cuộn hút','Điện áp cuộn dây','Coil voltage'),'điện áp cuộn hút'),
                (('dien_ap_ra',),('Điện áp đầu ra','Điện áp ra','Output voltage'),'điện áp đầu ra'),
                (('cong_suat_kW',),('Công suất (kW)','Công suất kW'),'công suất'),
                (('cong_suat_VA',),('Công suất (VA)','Công suất VA'),'công suất'),
                (('dong_so_cap_dinh_muc_A',),('Dòng sơ cấp (A)','Dòng sơ cấp'),'dòng sơ cấp'),
                (('dong_thu_cap_dinh_muc_A',),('Dòng thứ cấp (A)','Dòng thứ cấp'),'dòng thứ cấp')]
            for source_keys,target_keys,label in comparisons:
                wanted=next((source[k] for k in source_keys if source.get(k)),None)
                actual=next((spec[k] for k in target_keys if spec.get(k)),None)
                values=lambda value:{float(n) for n in re.findall(r'\d+(?:\.\d+)?',str(value))}
                if not wanted or not values(wanted):continue
                if not actual or not values(actual):missing.append(label);continue
                if 'điện áp' in label and current_kinds(wanted) and current_kinds(actual) and not current_kinds(wanted)&current_kinds(actual):conflict=True;break
                if not values(wanted)&values(actual):conflict=True;break
                anchors+=1
            if conflict or not anchors:continue
            if missing:row={**row,'compatibility_note':'Cần xác nhận '+', '.join(missing)}
        if kind in BREAKERS:
            wanted=source.get('dong_dinh_muc_A') or source.get('dong_dinh_muc')
            actual=spec.get('In (A)') or spec.get('In') or spec.get('Dòng định mức (A)') or spec.get('Dòng định mức')
            if wanted:
                numbers=lambda value:{float(n.replace(',','.')) for n in re.findall(r'\d+(?:\.\d+)?',str(value))}
                if numbers(wanted) and (not actual or not (numbers(wanted)&numbers(actual))):continue
            if other:
                numbers=lambda value:{float(n) for n in re.findall(r'\d+(?:\.\d+)?',str(value))}
                voltage=source.get('dien_ap_V') or source.get('dien_ap_dinh_muc')
                actual_voltage=spec.get('Ue (V)') or spec.get('Điện áp định mức') or spec.get('Điện áp (V)')
                if voltage and actual_voltage and numbers(voltage) and numbers(actual_voltage) and not numbers(voltage)&numbers(actual_voltage):continue
                if current_kinds(voltage) and current_kinds(actual_voltage) and not current_kinds(voltage)&current_kinds(actual_voltage):continue
                leakage=source.get('dong_ro_mA') or source.get('dong_ro_tac_dong')
                actual_leakage=spec.get('Dòng rò (mA)') or spec.get('Dòng rò tác động (mA)')
                if leakage and (not actual_leakage or not numbers(leakage)&numbers(actual_leakage)):continue
                breaking=source.get('kha_nang_cat')
                actual_breaking=spec.get('Icu(KA)') or spec.get('Icu (kA)') or spec.get('Icn') or spec.get('Khả năng cắt (kA)')
                if breaking and actual_breaking and numbers(breaking) and numbers(actual_breaking) and min(numbers(actual_breaking))<max(numbers(breaking)):continue
                missing=[]
                if voltage and not actual_voltage:missing.append('điện áp')
                if breaking and not actual_breaking:missing.append('khả năng cắt')
                if missing:row={**row,'compatibility_note':'Cần xác nhận '+', '.join(missing)}
        result.append(row)
    return result
