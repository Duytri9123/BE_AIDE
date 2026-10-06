"""Combine DGP Mitsubishi prices with verified original D04 dynamic CAD states."""
import html
import json
import re
from pathlib import Path

base = Path(__file__).resolve().parents[2] / 'Tudien/CATALOG_PHU_KIEN_DOC_LAP/MITSUBISHI_D04_DU_LIEU_MOI'
native = base / 'native'
prices = json.loads((base / 'price_index.json').read_text(encoding='utf8'))
manifest = json.loads((native / 'manifest.json').read_text(encoding='utf8'))
views = json.loads((native / 'views.json').read_text(encoding='utf8'))
sources = {d['id']: d for d in manifest}
states = {v['id']: v for v in views}

def slug(s):
    return re.sub(r'-+', '-', re.sub(r'[^A-Z0-9]+', '-', s.upper())).strip('-')

def state(source, option):
    prop = sources[source]['dynamic_properties'][0]
    if option not in prop['allowed']:
        return None
    key = source if option == prop['value'] else source + '-VIEW-' + slug(option)
    return key if key == source or key in states else None

def candidate(row):
    model = (row['model'] or '').upper()
    pole = row['poles_pdf']
    desc = row['description_pdf'].upper()
    # Descriptions of accessories can mention the breaker model; require a
    # priced device entry with a distinct pole specification.
    if model.startswith('NF'):
        if row['category'] != 'MCCB':
            return None
        if pole not in (2, 3, 4) or '/' in desc.split(model, 1)[-1].split(' ', 1)[0]:
            return None
        mapping = {
            'NF32-SV': ('MIT-D04-C6-I06', {2}),
            'NF63-SV': ('MIT-D04-C6-I06', {3, 4}),
            'NF125-CV': ('MIT-D04-C6-I02', {2, 3, 4}),
            'NF250-CV': ('MIT-D04-C6-I03', {2, 3, 4}),
            'NF400-CW': ('MIT-D04-C6-I04', {2, 3, 4}),
            'NF630-CW': ('MIT-D04-C6-I05', {2, 3, 4}),
            'NF800-CEW': ('MIT-D04-C5-I01', {3, 4}),
            'NF1000-SEW': ('MIT-D04-C5-I02', {3, 4}),
            'NF1600-SEW': ('MIT-D04-C5-I03', {3, 4}),
        }
        if model not in mapping:
            return None
        source, allowed = mapping[model]
        if pole not in allowed:
            return None
        connector = source.endswith(('C5-I01', 'C6-I04', 'C6-I05'))
        option = f'{pole}P: Front View' + (' w.Connector' if connector else '')
        return source, option, 'Trùng mã trong CAD và số cực ở trạng thái động gốc'
    if row['category']=='MCB' and model == 'BH-D6' and pole in (1, 2, 3, 4) and not re.search(r'\b1PN\b', desc):
        # C3 placements: I01=2P, I02=3P, I03=4P, I04=1P.
        source = {1:'MIT-D04-C3-I04', 2:'MIT-D04-C3-I01',
                  3:'MIT-D04-C3-I02', 4:'MIT-D04-C3-I03'}[pole]
        return source, f'{pole}P: Front View', 'Trùng BH-D6 và số cực trong CAD gốc'
    contactor = {'S-T10':('MIT-D04-C2-I01','S-T10: Front View'),
                 'S-T12':('MIT-D04-C2-I02','S-T12, S-T20: Front View'),
                 'S-T20':('MIT-D04-C2-I02','S-T12, S-T20: Front View'),
                 'S-T21':('MIT-D04-C2-I03','S-T21, S-T25: Front View'),
                 'S-T25':('MIT-D04-C2-I03','S-T21, S-T25: Front View'),
                 'S-T35':('MIT-D04-C2-I04','S-T35, S-T50: Front View'),
                 'S-T50':('MIT-D04-C2-I04','S-T35, S-T50: Front View')}
    if row['category']=='Contactor' and model in contactor and re.search(r'\b'+re.escape(model)+r'\b', desc):
        return *contactor[model], 'Mã nằm trong tên trạng thái CAD động gốc'
    return None


CONTACTOR_SPEC = re.compile(
    r'(?<![\w.])(?P<kw>\d+(?:\.\d+)?)\s+(?P<amps>\d+)\s+'
    r'(?P<aux>\d+a(?:\d+b)?|\d+b)\s+(?P<model>S-T\d+)\b', re.I)
CONTACTOR_SOURCE = 'https://dl.mitsubishielectric.com/dl/fa/document/catalog/lvsw/l02030/L%28NA%2902030ENG-J.pdf'


def price_specs(price):
    """Read the three leading contactor columns in the priced PDF row."""
    if price['category'] != 'Contactor' or not price['model']:
        return {}
    found = [m for m in CONTACTOR_SPEC.finditer(price['description_pdf'])
             if m['model'].upper() == price['model'].upper()]
    if not found:
        return {}
    match = found[-1]
    coil = re.search(r'\bAC\s*(\d+)V\b', price['description_pdf'][match.end():], re.I)
    return {'current_a_pdf': match['amps'],
            'ac3_kw_400v_pdf': match['kw'],
            'ac3_current_a_380_440v_pdf': match['amps'],
            'auxiliary_contacts_pdf': match['aux'],
            'coil_voltage_pdf': ('AC' + coil[1] + 'V') if coil else None,
            'spec_source_url': CONTACTOR_SOURCE,
            'spec_source_note': f"PDF bảng giá trang {price['page']}: AC-3 380–440 V / 400 V; tài liệu hãng để đối chiếu dòng S-T"}

rows = []
for price in prices:
    description=price['description_pdf']
    model=price['model']
    if model and model in description.upper():
        # PDF text extraction can prepend a neighbouring table header/row.
        # Keep the original source text, but start the display at the priced model.
        matches=list(re.finditer(r'\b'+re.escape(model)+r'\b',description,re.I))
        if matches:
            description=description[matches[-1].start():]
    spec=description
    if model:
        spec=re.sub(r'^'+re.escape(model)+r'\b\s*','',spec,flags=re.I)
    material=price['material_code']
    if material:
        spec=re.sub(r'\s+'+re.escape(material)+r'\s*$','',spec,flags=re.I)
    pole_display='1P+N' if re.search(r'\b1PN\b',price['description_pdf'],re.I) else (str(price['poles_pdf'])+'P' if price['poles_pdf'] else None)
    row = {**price, **price_specs(price), 'description_display':description,'spec_display':spec.strip(),
           'pole_display':pole_display,
           'cad_source_id':None, 'cad_state_id':None, 'cad_option':None,
           'cad_preview':None, 'cad_dwg':None, 'cad_dxf':None, 'cad_basis':None}
    found = candidate(price)
    if found:
        source, option, basis = found
        key = state(source, option)
        if key:
            preview = native / (key + '-crop.png')
            dwg = native / (key + '.dwg')
            dxf = native / (key + '.dxf')
            if preview.exists() and dwg.exists() and dxf.exists():
                row.update(cad_source_id=source, cad_state_id=key, cad_option=option,
                           cad_preview='native/'+preview.name, cad_dwg='native/'+dwg.name,
                           cad_dxf='native/'+dxf.name, cad_basis=basis)
    rows.append(row)
(base / 'price_with_cad.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

from render_mitsubishi_catalog import render
render(base, rows, manifest, views)

print(json.dumps({'price_rows':len(rows),'linked':sum(bool(r['cad_dwg']) for r in rows),'source_cad':len(manifest),'view_states':len(views)},ensure_ascii=False))

