"""Add only external evidence matching the exact published model configuration."""
import json
import re
from pathlib import Path

def enrich(items):
    counts = {'ls_classified': 0, 'ls_dimensions': 0, 'chint_dimensions': 0}
    for row in items:
        if row['brand'] == 'LS Electric':
            model, group = row['item_name'].upper(), row['group'].upper()
            if re.match(r'^LA63[NHL] [1-4]P$', model):
                tier = 'standard' if model.startswith('LA63N ') else 'premium'
                row.update(product_line=tier, line_label=('Dòng thường' if tier=='standard' else 'Dòng cao cấp')+' · '+model.split()[0])
                row['line_evidence'] = 'https://dtech.vn/upload/file/bang-gia/Bang-gia-thiet-bi-dong-cat-LS-15-4-2026.pdf'
                row['line_classification_basis'] = 'Customer segment; external model and breaking-capacity cross-check'
            elif 'SUSOL' in group or re.match(r'^(?:TS|TD)\d', model):
                row.update(product_line='premium', line_label='Dòng cao cấp · Susol')
                row['line_evidence'] = 'https://pfinder.ls-electric.com/IEC/product/mccb_susol.do'
            elif 'METASOL' in group or re.match(r'^(?:AB[NHSL]|EB[NHSL])\d', model):
                row.update(product_line='standard', line_label='Dòng thường · Metasol')
                row['line_evidence'] = 'https://www.ls-electric.com/upload/customer/download/1213/Metasol_MCCB-ELCB_Technical%20Manual_E.pdf'
            else:
                continue  # Do not classify an unknown series from the user's JSON.
            counts['ls_classified'] += 1
            matched = re.fullmatch(r'(ABS3|ABN5|ABS5|ABH5|ABN6|ABS6|ABN10|ABS10|ABH10|ABN20|ABS20|ABH20)([234])c', row['item_name'])
            if matched:
                frame, poles = matched[1], int(matched[2])
                if frame.endswith('20'):
                    width, height, depth = (105 if poles<4 else 140),165,87
                elif frame in ('ABH5','ABS10','ABH10'):
                    width, height, depth = poles*30,155,82
                else:
                    width, height, depth = poles*25,130,82
                row['dimensions_mm'] = {'w':width,'h':height,'d':depth}
                dim_label = 'Kích thước bao W×H×D (mm)'
                row['specifications'].update({dim_label:f'{width} × {height} × {depth}',
                    'Độ sâu thân c1 (mm)':'60', 'Độ sâu vỏ c2 (mm)':'64',
                    'Ui':'750V','Uimp':'8kV','Lắp đặt':'Bắt vít'})
                if dim_label not in row['columns']:
                    index = next(i for i,c in enumerate(row['columns']) if 'giá' in c.lower())
                    row['columns'].insert(index,dim_label);row['cells'].insert(index,row['specifications'][dim_label])
                row['technical_evidence'] = {'url':row['line_evidence'],'pages':[8,9],
                    'checked_at':'2026-10-13','scope':'Exact Metasol c-series model; d includes handle envelope'}
                counts['ls_dimensions'] += 1
        match = re.fullmatch(r'NXB-63 ([1-4])P C(6|10|16|20|25|32|40|50|63) 6kA', row['item_name'])
        if row['brand'] != 'CHINT' or not match:
            continue
        poles = int(match[1])
        dims = {'w':18*poles, 'h':80, 'd':76.8 if poles==1 else 77.8}
        row['dimensions_mm'] = dims
        technical = {'Kích thước W×H×D (mm)':f"{dims['w']} × {dims['h']} × {dims['d']:g}",
                     'Ics': '6kA', 'Uimp': '4kV', 'Tần số': '50Hz',
                     'Lắp đặt': 'Ray DIN TH35-7.5', 'Tiêu chuẩn': 'IEC 60898-1'}
        row['specifications'].update(technical)
        label = 'Kích thước W×H×D (mm)'
        if label not in row['columns']:
            index = next(i for i,c in enumerate(row['columns']) if 'giá' in c.lower())
            row['columns'].insert(index,label); row['cells'].insert(index,technical[label])
        row['technical_evidence'] = {'url':'https://www.chint.eu/content/download/9434/file/Ficha_Chint_Serie%20NXB-63_032026.pdf',
                                     'page':1,'checked_at':'2026-10-13','scope':'NXB-63 C curve 6kA only'}
        counts['chint_dimensions'] += 1
    return counts

if __name__ == '__main__':
    path = Path(__file__).resolve().parents[1]/'app/data/supplier_pricebooks.json'
    data = json.loads(path.read_text(encoding='utf8'))
    print(json.dumps(enrich(data['items'])))
    pending = path.with_suffix('.json.tmp')
    pending.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    pending.replace(path)
