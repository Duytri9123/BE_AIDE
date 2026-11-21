"""Propose complete native block extents; independent pixel auditing is mandatory."""
import re
from itertools import combinations


def unlabeled_ct_cluster(path, evidence):
    """Find a paired winding on a primary conductor feeding a labeled AS circuit."""
    import ezdxf
    from app.services.ingestion.cad_source_evidence import plain

    selectors = [label for label in evidence.get('labels', []) if plain(label['text']).strip() == 'AS']
    bounds = evidence.get('view_bounds')
    if len(selectors) != 1 or not bounds:
        return None
    selector = selectors[0]
    left, bottom, right, top = bounds
    modelspace = ezdxf.readfile(path).modelspace()
    arcs = [arc for arc in modelspace.query('ARC') if left <= arc.dxf.center.x <= right
            and bottom <= arc.dxf.center.y <= top
            and 250 <= (arc.dxf.end_angle - arc.dxf.start_angle) % 360 <= 290]
    wires = [(line.dxf.start, line.dxf.end, line.dxf.handle) for line in modelspace.query('LINE')
             if left <= line.dxf.start.x <= right and bottom <= line.dxf.start.y <= top]
    candidates = []
    for first, second in combinations(arcs, 2):
        upper, lower = sorted((first, second), key=lambda arc: -arc.dxf.center.y)
        a, b = upper.dxf.center, lower.dxf.center
        radius = upper.dxf.radius
        tolerance = radius * .08
        if (abs(radius - lower.dxf.radius) > tolerance or abs(a.x - b.x) > tolerance
                or not radius <= a.y - b.y <= radius * 1.8
                or upper.end_point.distance(lower.start_point) > tolerance):
            continue
        junction = upper.end_point
        primary = next((handle for p, q, handle in wires if abs(p.x-a.x) <= tolerance
                        and abs(q.x-a.x) <= tolerance and min(p.y,q.y) <= b.y-radius
                        and max(p.y,q.y) >= a.y+radius), None)
        secondary = next((handle for p, q, handle in wires if any(
            start.distance(junction) <= tolerance and abs(end.y-start.y) <= tolerance
            and abs(end.x-selector['x']) <= selector['height']*3
            and abs(end.y-selector['y']) <= selector['height']*3
            and start.distance(end) > radius*3 for start, end in ((p,q),(q,p)))), None)
        if primary and secondary:
            candidates.append([upper.dxf.handle, lower.dxf.handle, primary, secondary])
    if len(candidates) != 1:
        return None
    return {'category': 'CT', 'name': 'Biến dòng đo lường', 'spec': '', 'quantity': 1,
            'unit': 'Cụm', 'drawing_quantity': 1, 'section': 'Đo lường',
            'observed_text': 'Ký hiệu biến dòng nối với chuyển mạch AS',
            'source_evidence_ids': [selector['id'], *candidates[0]],
            'source_observations': {'extraction_method': 'native_current_transformer_winding'}}


def ground_ct_clusters(evidence,parts):
    """Generic AS and three phases do not identify a physical CT count."""
    from app.services.ingestion.cad_source_evidence import plain
    labels=[plain(l.get('text')).strip() for l in evidence.get('labels',[])]
    if 'AS' not in labels:return
    explicit=any(re.search(r'(?<!\d)\d+\s*(?:[X×]\s*)?(?:CT|TI)(?=\b|\d)|(?<!\d)\d+\s*BIEN DONG\b|\d+\s*[X×]\s*\d+\s*/\s*\d+\s*A',text) for text in labels)
    if explicit:return
    for part in parts:
        for row in part['devices']:
            if row.get('category')!='CT' or (row.get('drawing_quantity') or 1)>1:continue
            observed=row.get('source_observations') or {}
            row['source_observations']={**observed,
                'unverified_physical_quantity':observed.get('unverified_physical_quantity',row.get('quantity')),
                'quantity_interpretation':'Generic AS; source does not specify physical CT count'}
            row.update(quantity=1,unit='Cụm',quantity_review={'status':'needs_review','blocking':True,
                'verification_note':'Nguồn chưa ghi số CT vật lý hoặc kiểu đấu chuyển mạch AS để xác định.'},
                quantity_basis='Nguồn biểu diễn cụm CT nối AS và ampe kế; không đồng nhất số pha với số CT vật lý.')


def seed_named_symbols(path, evidence, devices, proposals):
    import ezdxf
    from ezdxf import bbox
    from app.services.ingestion.cad_source_evidence import plain
    bounds = evidence.get('view_bounds')
    if not bounds:
        return proposals
    left,bottom,right,top = bounds
    def normalized(b):
        return [max(0,(top-b[3])/(top-bottom)*1000),max(0,(b[0]-left)/(right-left)*1000),
                min(1000,(top-b[1])/(top-bottom)*1000),min(1000,(b[2]-left)/(right-left)*1000)]
    blocks=[]
    for entity in ezdxf.readfile(path).modelspace().query('INSERT'):
        extent=bbox.extents([entity],fast=True)
        if not extent.has_data or not (left<=extent.center.x<=right and bottom<=extent.center.y<=top):
            continue
        box=normalized([extent.extmin.x,extent.extmin.y,extent.extmax.x,extent.extmax.y])
        if box[2]-box[0]>200 or box[3]-box[1]>200:
            continue
        blocks.append({'name':plain(entity.dxf.name),'box':box,'handle':entity.dxf.handle})
    by_id={str(b.get('device_id')):dict(b) for b in proposals}
    for i,device in enumerate(devices):
        proposal=by_id.get(str(i))
        if not proposal or not proposal.get('symbol_box_2d'):
            continue
        kind=device.get('category');name=plain(device.get('name') or '')
        if kind in {'MCB','MCCB','RCBO','RCCB','ACB'} and proposal.get('geometry_source') == 'native_cad_block_and_rotated_text':
            continue  # Preserve the vertical seed used to resolve mechanical linkage.
        pattern=None
        if kind in {'MCB','MCCB','RCBO','RCCB','ACB'}:pattern=r'APTOMAT|BREAKER|(?:^|[_ -])(?:MCB|MCCB|RCBO|RCCB|CB)(?:$|[_ -])'
        elif kind in {'LIGHT','PILOT_LIGHT'}:pattern=r'DEN[ _-]*BAO|PILOT[ _-]*(?:LAMP|LIGHT)'
        elif kind=='SELECTOR_SWITCH':pattern=r'CHUYEN[ _-]*MACH|SELECTOR'
        elif kind in {'METER','AMMETER','VOLTMETER'}:
            if re.search(r'VON|VOLT|DIEN AP',name):pattern=r'VON|VOLT'
            elif re.search(r'AMPE|AMMETER|DONG DIEN',name):pattern=r'AMPE|AMMETER'
        elif kind=='CT':pattern=r'BIEN[ _-]*DONG|CURRENT[ _-]*TRANSFORMER|(?:^|[_ -])CT(?:$|[_ -])|^ICC-BI$'
        elif kind=='FUSE':pattern=r'.*'  # Class came from vision; propose the nearest complete block only.
        if not pattern:
            continue
        old=proposal['symbol_box_2d'];cy,cx=(old[0]+old[2])/2,(old[1]+old[3])/2
        candidates=[b for b in blocks if re.search(pattern,b['name'])
                    and abs((b['box'][0]+b['box'][2])/2-cy)<=max(45,old[2]-old[0]+10)
                    and abs((b['box'][1]+b['box'][3])/2-cx)<=max(60,old[3]-old[1]+10)]
        candidates.sort(key=lambda b:((b['box'][0]+b['box'][2])/2-cy)**2+((b['box'][1]+b['box'][3])/2-cx)**2)
        if kind=='FUSE':
            candidates=[b for b in candidates if abs((b['box'][0]+b['box'][2])/2-cy)<=20
                        and abs((b['box'][1]+b['box'][3])/2-cx)<=20]
        count=device.get('drawing_quantity') or (device.get('quantity') if kind in {'LIGHT','PILOT_LIGHT','METER','AMMETER','VOLTMETER'} else 1)
        if kind in {'LIGHT','PILOT_LIGHT','METER','AMMETER','VOLTMETER'} and isinstance(device.get('quantity'),int):
            count=max(count if isinstance(count,int) else 1,device['quantity'])
        if not isinstance(count,int) or count<1 or count>6 or len(candidates)<count:
            continue
        selected=candidates[:count]
        symbol=[min(b['box'][0] for b in selected),min(b['box'][1] for b in selected),
                max(b['box'][2] for b in selected),max(b['box'][3] for b in selected)]
        proposal.update(symbol_box_2d=symbol,verified=True,symbol_verified=True,
                        geometry_source='native_named_cad_blocks',source_symbol_handles=[b['handle'] for b in selected])
        # A/V inside a meter denotes its measurement function, not a separate
        # rating label. Keep the whole native circle and its internal marking.
        if kind in {'METER','AMMETER','VOLTMETER','SELECTOR_SWITCH','CT'} and not device.get('spec'):
            proposal['text_box_2d']=symbol
        if kind in {'CT','FUSE'}:
            spec=plain(device.get('spec') or '')
            ratios=re.findall(r'\d+(?:[.,]\d+)?\s*/\s*\d+(?:[.,]\d+)?\s*A',spec)
            labels=[r for r in evidence.get('labels',[]) if r.get('bounds')
                    and abs((r['x']-left)/(right-left)*1000-(symbol[1]+symbol[3])/2)<=60
                    and abs((top-r['y'])/(top-bottom)*1000-(symbol[0]+symbol[2])/2)<=45
                    and (any(re.sub(r'\s+','',ratio) in re.sub(r'\s+','',plain(r['text'])) for ratio in ratios)
                         if kind=='CT' and ratios else kind=='FUSE' and re.fullmatch(r'\s*(?:\d+\s*[X×]\s*)?\d+(?:[.,]\d+)?\s*A\s*',plain(r['text'])))]
            if len(labels)==1:
                proposal['text_box_2d']=normalized(labels[0]['bounds'])
        if kind in {'LIGHT','PILOT_LIGHT'}:
            nearby=[r['bounds'] for r in evidence.get('labels',[]) if r.get('bounds')
                    and plain(r['text']).strip() in {'R','Y','B'}
                    and symbol[1]-15<=(r['x']-left)/(right-left)*1000<=symbol[3]+15
                    and symbol[0]-30<=(top-r['y'])/(top-bottom)*1000<=symbol[2]]
            if nearby:
                label=[min(b[0] for b in nearby),min(b[1] for b in nearby),max(b[2] for b in nearby),max(b[3] for b in nearby)]
                proposal['text_box_2d']=normalized(label)
    return list(by_id.values())
