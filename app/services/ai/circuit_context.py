"""Read circuit-table details only from the uniquely identified CAD row."""
import re
from app.services.ingestion.cad_source_evidence import plain, signature


def enrich_circuit_context(devices, evidence):
    labels = evidence.get('labels') or []
    by_id = {r['id']: r for r in labels}
    for device in devices:
        ids = set(device.get('source_evidence_ids') or [])
        choices = [r for r in evidence.get('rows', []) if ids.intersection({r['id'], r['rating_id']})]
        if not choices and device.get('tag'):
            choices = [r for r in evidence.get('rows', []) if plain(r['tag']) == plain(device['tag'])]
            expected = signature(device.get('spec') or '')
            choices = [r for r in choices if not expected or signature(r['rating']) == expected]
        if len(choices) > 1:
            region = device.get('evidence_region') or {}
            bounds = region.get('source_world_bounds') or evidence.get('view_bounds')
            box = region.get('text_box_2d')
            if bounds and box:
                y = bounds[3] - (box[0]+box[2])/2000*(bounds[3]-bounds[1])
                ranked = sorted(choices, key=lambda r: abs(by_id[r['rating_id']]['y']-y))
                if abs(by_id[ranked[0]['rating_id']]['y']-y) <= by_id[ranked[0]['rating_id']]['height']*2:
                    choices = ranked[:1]
        if len(choices) != 1 or not choices[0].get('tag'):
            continue
        row = choices[0]
        anchor = by_id[row['id']]
        nearby = [r for r in labels if abs(r['y']-anchor['y']) <= max(r['height'],anchor['height'])*1.5]
        context = {'source': 'cad_row', 'evidence_ids': [row['id'],row['rating_id']],
                   'relationship_verified': (device.get('evidence_region') or {}).get('load_verified') is True}
        cables = [r for r in nearby if re.search(r'XLPE|PVC|CVV|MM[²2]|\bDN\s*D?\d+', r['text'], re.I)]
        if len(cables) == 1:
            cable = cables[0];context['evidence_ids'].append(cable['id'])
            text = cable['text'].strip()
            method = re.search(r'(?:ĐI |LẮP |LUỒN |CHÔN ).*$', text, re.I)
            context['cable_spec'] = text[:method.start()].rstrip(' -;,') if method else text
            if method: context['installation_method'] = method[0]
        load = [r for r in nearby if device.get('connected_load') and plain(r['text']) == plain(device['connected_load'])]
        if not load and len(cables) == 1:
            load = [r for r in nearby if r['x'] > cables[0]['x'] and re.search(r'[^\W\d_]', r['text'], re.U) and r not in cables]
        if len(load) == 1:
            context['supply_location'] = load[0]['text'];context['evidence_ids'].append(load[0]['id'])
        phases = [r for r in nearby if re.fullmatch(r'(?:A|B|C|ABC|A,B,C)', r['text'].strip(), re.I)]
        if len(phases) == 1: context['phase'] = phases[0]['text']
        numeric = [r for r in nearby if re.fullmatch(r'\d+(?:[.,]\d+)?', r['text'].strip())]
        headers = [r for r in labels if 'CONG SUAT' in plain(r['text'])]
        candidates = [(n,h) for n in numeric for h in headers if abs(n['x']-h['x']) <= max(h['height']*12,1)]
        if candidates:
            n,h = min(candidates,key=lambda pair:abs(pair[0]['x']-pair[1]['x']))
            unit_text = ' '.join(r['text'] for r in labels if abs(r['x']-h['x']) < h['height']*12 and abs(r['y']-h['y']) < h['height']*5)
            units = set(re.findall(r'\b(KW|HP|CV|W)\b', plain(unit_text)))
            unit = next(iter(units)) if len(units) == 1 else None
            unit = 'kW' if unit == 'KW' else unit
            context.update(power_value=float(n['text'].replace(',','.')),power_unit=unit)
            if unit:
                from app.services.ai.motor_starter_context import POWER_FACTORS
                context['power_w'] = context['power_value'] * POWER_FACTORS[unit.lower()]
            context['evidence_ids'].append(n['id'])
        if len(context) > 3:
            device['circuit_context'] = context
            observations = device.get('source_observations')
            device['source_observations'] = {**(observations if isinstance(observations,dict) else {}),'circuit':context}
    return devices
