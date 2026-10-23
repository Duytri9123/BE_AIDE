"""Public, evidence-backed facts; evidence and selection notes stay private."""
import json,re
from pathlib import Path
from functools import lru_cache
PATH=Path(__file__).resolve().parents[1]/'data/catalog_customer_technical_facts.json'

def qualified_breaking_specs(brand,model):
    """Exact model facts from LS manual pp.8–9 / NXM catalogue p.27."""
    maker=str(brand or '').upper();model=str(model or '').strip()
    if maker in {'LS','LS ELECTRIC'}:
        table={}
        for prefix,frames,ratings in [('ABN',[52,53,54],(14,18,30)),('ABN',[102,103,104],(18,22,35)),('ABS',[102,103,104],(37,42,85)),('ABH',[102,103,104],(50,50,100))]:
            for frame in frames:table[prefix+str(frame)+'C']=ratings
        values=table.get(model.upper())
        if values:return {'Icu tại '+voltage+' V AC (kA)':str(v) for voltage,v in zip(['415/460','380','220/250'],values)}
    if maker=='CHINT' and re.match(r'^NXM-(160|250)S/[234]\d{3}[A-D]?(?:\s|$)',model,re.I):return {'Icu tại 380/400/415 V AC (kA)':'36'}
    if maker in {'MITSUBISHI','MITSUBISHI ELECTRIC'}:
        # Manufacturer Y0713C2303: IEC 61009-1 RCBO ratings, not MCCB Icu.
        rcbo={'BV-DN':'4.5','BV-DN6':'6'}.get(model.upper())
        if rcbo:return {'Icn tại 230 V AC (kA)':rcbo}
        # WS-V Y0720J2309, PDF pp.150/154 (printed pp.148/152).
        # Exact standard models only: do not transfer these to MB/UV/CVU variants.
        table={
            'NF125-CV':((10,5),(10,5),(10,5)),
            'NF125-SV':((30,30),(30,30),(25,25)),
            'NF125-HV':((50,38),(50,38),(50,38)),
            'NF250-CV':((25,19),(25,19),(15,12)),
            'NF250-SV':((36,36),(36,36),(36,36)),
            'NF250-HV':((75,75),(70,70),(65,65)),
        }
        values=table.get(model.upper())
        if values:return {f'{label} tại {voltage} V AC (kA)':str(pair[i]) for voltage,pair in zip((400,415,440),values) for i,label in enumerate(('Icu','Ics'))}
    return {}

@lru_cache(maxsize=2)
def _load(modified,size):
    return json.loads(PATH.read_text(encoding='utf8')).get('items',{})

def technical_specs(device,spec):
    if str(device.get('brand') or '').upper() not in {'ABB','LS','LS ELECTRIC','CHINT','SCHNEIDER','SCHNEIDER ELECTRIC','INVT','MITSUBISHI','MITSUBISHI ELECTRIC','SHIHLIN','SHIHLIN ELECTRIC'}:return spec
    if not PATH.is_file():return spec
    stat=PATH.stat();record=_load(stat.st_mtime_ns,stat.st_size).get(device.get('id'))
    if not record:return spec
    # Do not transfer the old model/geometry's facts to a renamed/rebuilt item.
    if record.get('model')!=device.get('product_code') or record.get('view_ids')!=sorted(v['id'] for v in device.get('views',[])):return spec
    result=dict(spec);facts=record['facts']
    if 'Số cực' in facts:
        for key in ['so_cuc','so_cuc_chinh','so_cuc_theo_nhan_hinh']:result.pop(key,None)
    result.update(facts)
    result.update(qualified_breaking_specs(device.get('brand'),device.get('product_code')))
    return result

def view_technical_specs(device,view_id):
    if not PATH.is_file():return {}
    stat=PATH.stat();record=_load(stat.st_mtime_ns,stat.st_size).get(device.get('id')) or {}
    if record.get('model')!=device.get('product_code') or record.get('view_ids')!=sorted(v['id'] for v in device.get('views',[])):return {}
    return record.get('view_facts',{}).get(view_id,{})
