"""Propose complete native block extents; independent pixel auditing is mandatory."""
import re


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
        if not pattern:
            continue
        old=proposal['symbol_box_2d'];cy,cx=(old[0]+old[2])/2,(old[1]+old[3])/2
        candidates=[b for b in blocks if re.search(pattern,b['name'])
                    and abs((b['box'][0]+b['box'][2])/2-cy)<=max(45,old[2]-old[0]+10)
                    and abs((b['box'][1]+b['box'][3])/2-cx)<=max(60,old[3]-old[1]+10)]
        candidates.sort(key=lambda b:((b['box'][0]+b['box'][2])/2-cy)**2+((b['box'][1]+b['box'][3])/2-cx)**2)
        count=device.get('drawing_quantity') or (device.get('quantity') if kind in {'LIGHT','PILOT_LIGHT','METER','AMMETER','VOLTMETER'} else 1)
        if not isinstance(count,int) or count<1 or count>6 or len(candidates)<count:
            continue
        selected=candidates[:count]
        symbol=[min(b['box'][0] for b in selected),min(b['box'][1] for b in selected),
                max(b['box'][2] for b in selected),max(b['box'][3] for b in selected)]
        proposal.update(symbol_box_2d=symbol,verified=True,symbol_verified=True,
                        geometry_source='native_named_cad_blocks',source_symbol_handles=[b['handle'] for b in selected])
        # A/V inside a meter denotes its measurement function, not a separate
        # rating label. Keep the whole native circle and its internal marking.
        if kind in {'METER','AMMETER','VOLTMETER','SELECTOR_SWITCH'} and not device.get('spec'):
            proposal['text_box_2d']=symbol
        if kind in {'LIGHT','PILOT_LIGHT'}:
            nearby=[r['bounds'] for r in evidence.get('labels',[]) if r.get('bounds')
                    and plain(r['text']).strip() in {'R','Y','B'}
                    and symbol[1]-15<=(r['x']-left)/(right-left)*1000<=symbol[3]+15
                    and symbol[0]-30<=(top-r['y'])/(top-bottom)*1000<=symbol[2]]
            if nearby:
                label=[min(b[0] for b in nearby),min(b[1] for b in nearby),max(b[2] for b in nearby),max(b[3] for b in nearby)]
                proposal['text_box_2d']=normalized(label)
    return list(by_id.values())
