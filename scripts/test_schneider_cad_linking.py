import json
import re

with open('BE_AIDE/app/data/supplier_pricebooks.json', 'r', encoding='utf-8') as f:
    sp_data = json.load(f)

items = sp_data.get('items', [])
schneider_items = [it for it in items if it.get('brand') == 'Schneider Electric']

def resolve_schneider_cad(item):
    sku = str(item.get('sku') or '').upper()
    name = str(item.get('name') or item.get('item_name') or '').upper()
    specs = item.get('specifications') or {}
    poles = str(specs.get('Số cực') or specs.get('Poles') or '').upper()
    family = str(specs.get('Họ thiết bị') or '').upper()
    group = str(item.get('group') or '').upper()

    # extract poles from name if not in specs
    if not poles:
        m_p = re.search(r'\b([1-4])P\b', name) or re.search(r'\b([1-4])P\b', sku) or re.search(r'\b([1-4])P\b', group)
        if m_p:
            poles = f"{m_p.group(1)}P"

    # 1. iK60N
    if 'IK60' in family or 'IK60' in name or 'IK60' in group or sku.startswith('A9K'):
        if poles == '1P': return 'TB-64ce7e11085b43f8'
        if poles == '2P': return 'TB-66a8ff1a32b4b79e'
        if poles == '3P': return 'TB-e8cacd22e2ab35ba'
        if poles == '4P': return 'TB-429b4fe9a497237d'
        return 'TB-64ce7e11085b43f8'

    # 2. iC60
    if 'IC60' in family or 'IC60' in name or 'IC60' in group or sku.startswith('A9F'):
        if poles == '1P': return 'TB-49ae8f3071f94c61'
        if poles == '2P': return 'TB-e1e255d56a1c0054'
        if poles == '3P': return 'TB-d849389763b7f44c'
        if poles == '4P': return 'TB-c0120cdf0a87faf7'
        return 'TB-49ae8f3071f94c61'

    # 3. C120
    if 'C120' in family or 'C120' in name or 'C120' in group or sku.startswith('A9N18'):
        if poles == '1P': return 'TB-e3fc8970733974ad'
        if poles == '2P': return 'TB-213254590a9ed914'
        if poles == '3P': return 'TB-a6b013e73f33598f'
        if poles == '4P': return 'TB-c50afde0c81b2886'
        return 'TB-e3fc8970733974ad'

    # 4. A9D / Acti9 RCBO
    if 'A9D' in sku or 'A9D' in name:
        if poles in ('4P', '3P+N'): return 'TB-f164e25b45bffe10'
        return 'TB-728649ce3acf4905'

    # 5. iIDK / iID RCCB
    if 'IID' in family or 'IID' in name or 'IID' in group or sku.startswith('A9R'):
        if poles in ('4P', '3P+N'): return 'TB-0c2fc0e9ac12479c'
        return 'TB-1d1ab36d75cb2b5c'

    # 6. iCT Contactor
    if 'ICT' in family or 'ICT' in name or sku.startswith('A9C2'):
        return 'TB-03157e1509e3770e'

    # 7. EZC100
    if 'EZC100' in name or 'EZC100' in group or sku.startswith('EZC100'):
        if poles == '1P': return 'TB-2db736dd18a9914c'
        if poles == '2P': return 'TB-b26987552aa8750d'
        if poles == '3P': return 'TB-3bd2bd962e5e7024'
        if poles == '4P': return 'TB-1e0536a2f6d34ed1'
        return 'TB-3bd2bd962e5e7024'

    # 8. EZC250
    if 'EZC250' in name or 'EZC250' in group or sku.startswith('EZC250'):
        if poles == '2P': return 'TB-d7052dd5a9e5de7b'
        if poles == '3P': return 'TB-07d6c18d5a6e1e83'
        if poles == '4P': return 'TB-36f4ac1bec738cea'
        return 'TB-07d6c18d5a6e1e83'

    # 9. EZC400
    if 'EZC400' in name or 'EZC400' in group or sku.startswith('EZC400'):
        if poles == '4P': return 'TB-de932c87174f7640'
        return 'TB-ef7b5ab441b31e47'

    # 10. EZCV250
    if 'EZCV250' in name or 'EZCV250' in group or sku.startswith('EZCV250'):
        if poles == '4P': return 'TB-3f01e5faa3343ac2'
        return 'TB-13b7683c67553c13'

    # 11. EZS100
    if 'EZS100' in name or 'EZS100' in group or sku.startswith('EZS100'):
        if poles == '1P': return 'TB-7df8b9f5d5a5f1cd'
        if poles == '2P': return 'TB-04a81e62385986ea'
        if poles == '3P': return 'TB-ff1af150c1be7713'
        if poles == '4P': return 'TB-f36940a4a534aaa7'

    # 12. EZS250
    if 'EZS250' in name or 'EZS250' in group or sku.startswith('EZS250'):
        if poles == '2P': return 'TB-b932597472d6c4c9'
        if poles == '3P': return 'TB-325c5de9790bc60e'
        if poles == '4P': return 'TB-0a74fcb8ec23ebd4'

    # 13. EZS400
    if 'EZS400' in name or 'EZS400' in group or sku.startswith('EZS400'):
        if poles == '4P': return 'TB-8c17af72f7294f70'
        return 'TB-4927d8bb68415e42'

    # 14. CVS100 / CVS160 / CVS250
    if any(k in name or k in group for k in ('CVS100', 'CVS160', 'CVS250')) or sku.startswith(('LV510', 'LV516', 'LV525')):
        if poles == '4P': return 'TB-6b869a3c7294f6c8'
        return 'TB-caf9059b74d15cc8'

    # 15. CVS400 / CVS630
    if any(k in name or k in group for k in ('CVS400', 'CVS630')) or sku.startswith(('LV540', 'LV563')):
        if poles == '4P': return 'TB-bfdb79c4e8f2b4e0'
        return 'TB-edaa3c1aa248d7b4'

    # 16. NS100 / NS160 / NS250
    if any(k in name or k in group for k in ('NS100', 'NS160', 'NS250', 'NSX100', 'NSX160', 'NSX250')):
        if poles == '2P': return 'TB-b3fda8bc5e444540'
        if poles == '3P': return 'TB-ac46a1884987ae41'
        if poles == '4P': return 'TB-52bd625cb9dd1388'

    # 17. NS400 / NS630
    if any(k in name or k in group for k in ('NS400', 'NS630', 'NSX400', 'NSX630')):
        if poles == '4P': return 'TB-ed01ea45f4548aa4'
        return 'TB-2aa2a2859c5cfcff'

    # 18. NS630b / NS800 / NS1000 / NS1250 / NS1600
    if any(k in name or k in group for k in ('NS630B', 'NS800', 'NS1000', 'NS1250', 'NS1600')):
        if poles == '4P': return 'TB-ef65c9948cde2638'
        return 'TB-546fd887f249bd71'

    # 19. TeSys Deca Contactor LC1D
    if sku.startswith('LC1D') or 'LC1D' in name:
        m = re.search(r'LC1D(\d{2,3})', sku) or re.search(r'LC1D(\d{2,3})', name)
        if m:
            rating = int(m.group(1))
            if rating <= 18: return 'TB-77ad9af6edcecd8b' # LC1D9-18
            if rating <= 38: return 'TB-5a85d0fb1b71c309' # LC1D25-38
            if rating <= 65: return 'TB-46b3cfb457abd796' # LC1D40-65
            if rating <= 95: return 'TB-5bfee5cfd0ad64df' # LC1D40
        return 'TB-77ad9af6edcecd8b'

    # 20. Easy TeSys Contactor LC1E
    if sku.startswith('LC1E') or 'LC1E' in name:
        m = re.search(r'LC1E(\d{2,3})', sku) or re.search(r'LC1E(\d{2,3})', name)
        if m:
            rating = int(m.group(1))
            if rating <= 18: return 'TB-7d1974c4701a6074' # LC1E06-18
            if rating <= 25: return 'TB-db95704b91d7554c' # LC1E25
            if rating <= 38: return 'TB-c0c09ede8847559a' # LC1E32
            return 'TB-b25affd365b63fc4' # LC1E160
        return 'TB-7d1974c4701a6074'

    # 21. TeSys F Contactor LC1F
    if sku.startswith('LC1F') or 'LC1F' in name:
        if '115' in sku: return 'TB-042b1f4863190ee7'
        if '150' in sku: return 'TB-81ae850f258da70d'
        if '185' in sku: return 'TB-d4576b496449cbda'
        if '225' in sku: return 'TB-84b8d83b890186dc'
        if '265' in sku: return 'TB-bf1086a9a77cec6f'
        if '330' in sku: return 'TB-23c8a6cda269e108'
        return 'TB-042b1f4863190ee7'

    # 22. Thermal Relay LRD
    if sku.startswith('LRD') or 'LRD' in name:
        return 'TB-db54e2ec50351d5c'

    # 23. Motor Starter GV2ME
    if sku.startswith('GV2ME') or 'GV2ME' in name:
        return 'TB-40325d7c720932f8'

    # 24. Inverter ATV320
    if sku.startswith('ATV320') or 'ATV320' in name:
        return 'TB-de4306f8b83b75df'

    return None

matched_cad = 0
for it in schneider_items:
    cid = resolve_schneider_cad(it)
    if cid:
        matched_cad += 1

print(f"Total Schneider items: {len(schneider_items)}")
print(f"Schneider items matched to CAD: {matched_cad} ({matched_cad/len(schneider_items)*100:.1f}%)")
