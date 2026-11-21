"""Seed evidence proposals from explicit vertical CAD branch labels and breaker blocks.
Native coordinates are proposals only: the exported pixels still require visual audit.
"""
import re

def split_native_columns(regions,evidence):
    """Bound dense vertical reads at gaps between explicit CAD load labels."""
    from app.services.ingestion.cad_source_evidence import plain
    view=evidence.get('view_bounds')
    if not view:return regions
    left,bottom,right,top=view
    result=[]
    for region in regions:
        if region.get('rotation_degrees',0)!=0:
            result.append(region);continue
        y1,x1,y2,x2=region['box_2d'];columns=[]
        for label in evidence.get('labels',[]):
            box=label.get('bounds');tag=re.match(r'^((?:P|L|QF|Q|S|BT)\d+[A-Z]?)(?:[. :]|$)',plain(label.get('text')))
            if not box or not tag or box[3]-box[1] <= (box[2]-box[0])*2:continue
            x=((box[0]+box[2])/2-left)/(right-left)*1000
            y=(top-(box[1]+box[3])/2)/(top-bottom)*1000
            if x1<=x<=x2 and y1<=y<=y2:columns.append((x,tag[1]))
        columns=sorted(set(columns))
        if len(columns)<8:
            result.append(region);continue
        start=0;edge=x1
        while start<len(columns):
            end=min(start+5,len(columns))
            boundary=x2 if end==len(columns) else (columns[end-1][0]+columns[end][0])/2
            result.append({**region,'box_2d':[y1,edge,y2,boundary],
                'native_parent_box_2d':region['box_2d'],
                'native_branch_tags':[tag for _,tag in columns[start:end]]})
            start=end;edge=boundary
    return result


def horizontal_schedule_rows(evidence):
    labels={r['id']:r for r in evidence.get('labels', [])}
    return [r for r in evidence.get('rows', []) if r.get('tag') and r['id'] in labels and r['rating_id'] in labels
            and labels[r['id']]['x'] > labels[r['rating_id']]['x']
            and abs(labels[r['id']]['y']-labels[r['rating_id']]['y'])
                <= max(labels[r['id']]['height'],labels[r['rating_id']]['height'])*2]


def propose_vertical_ratings(evidence,parts):
    """Propose explicit native heading values; never certify their relationship."""
    from app.services.ingestion.cad_source_evidence import plain
    view=evidence.get('view_bounds');labels=evidence.get('labels',[])
    if not view:return
    left,bottom,right,top=view
    def normalized(box):return [(top-box[3])/(top-bottom)*1000,(box[0]-left)/(right-left)*1000,
        (top-box[1])/(top-bottom)*1000,(box[2]-left)/(right-left)*1000]
    for part in parts:
        boxes={str(b.get('device_id')):b for b in part['boxes']}
        for index,row in enumerate(part['devices']):
            if row.get('category') not in {'MCB','MCCB','RCBO','RCCB','ACB'}:continue
            tag=plain(row.get('tag')).strip();load=plain(row.get('connected_load')).strip()
            anchors=[l for l in labels if l.get('bounds') and (
                tag and re.match(r'^'+re.escape(tag)+r'(?:[. :]|$)',plain(l['text']))
                or load and plain(l['text']).strip()==load)]
            if len(anchors)!=1:continue
            anchor=anchors[0]['bounds']
            if anchor[3]-anchor[1]<=(anchor[2]-anchor[0])*2:continue
            proposal=boxes.get(str(index));symbol=(proposal or {}).get('symbol_box_2d')
            if not symbol:continue
            cx=(anchor[0]+anchor[2])/2;sy=top-(symbol[0]+symbol[2])/2000*(top-bottom)
            headings=[l for l in labels if l.get('bounds') and re.fullmatch(r'MCB|MCCB|RCBO|RCCB|ACB',plain(l['text']).strip())
                and l['x']<cx and abs(l['y']-sy)<l['height']*6]
            if not headings:continue
            heading=min(headings,key=lambda l:cx-l['x']);height=heading['height']
            cluster=[l for l in labels if l.get('bounds') and abs(l['x']-heading['x'])<height*2
                and heading['y']-height*6<=l['y']<=heading['y']+height]
            def unique(pattern):
                values={plain(l['text']).strip() for l in cluster if re.fullmatch(pattern,plain(l['text']).strip())}
                return next(iter(values)) if len(values)==1 else None
            pole=unique(r'[1-4]\s*P(?:\s*\+\s*N)?');amps=unique(r'\d+(?:[.,]\d+)?\s*A');icu=unique(r'\d+(?:[.,]\d+)?\s*KA')
            if not pole or not amps:continue
            family=plain(heading['text']).strip();spec=' '.join(v for v in (family,pole,amps,icu) if v)
            previous={k:row.get(k) for k in ('category','spec','poles','in_a','icu_ka')}
            row.update(category=family,spec=spec,poles=2 if '+' in pole else int(pole[0]),
                in_a=float(re.search(r'\d+(?:[.,]\d+)?',amps)[0].replace(',','.')),
                icu_ka=float(re.search(r'\d+(?:[.,]\d+)?',icu)[0].replace(',','.')) if icu else None,
                observed_text='\n'.join(l['text'] for l in sorted(cluster,key=lambda l:l['y'],reverse=True)))
            row['name']=re.sub(r'\b(?:MCB|MCCB|RCBO|RCCB|ACB)\b',family,str(row.get('name') or family),flags=re.I)
            row['source_observations']={**(row.get('source_observations') or {}),
                'native_heading_candidate':{'source_evidence_ids':[l['id'] for l in cluster],
                    'method':'native_heading_proposal_requires_pixel_relationship_check','previous_claim':previous}}
            native=[l['bounds'] for l in cluster]
            label=normalized([min(b[0] for b in native),min(b[1] for b in native),max(b[2] for b in native),max(b[3] for b in native)])
            proposal.update(text_box_2d=label,shared_label=True,
                group_reference_box_2d=[min(label[0],symbol[0]),min(label[1],symbol[1]),max(label[2],symbol[2]),max(label[3],symbol[3])],
                relationship_evidence='Tiêu đề CAD gốc bên trái nhánh; cần kiểm độc lập đường dây và ranh giới nhóm trên ảnh đầy đủ.')


def native_schedule_candidates(evidence):
    """Read explicit CAD table rows without asking vision to transcribe them.

    These are source candidates, not visual verification. Unnamed symbols and
    the rest of the panel still require independent inventory and crop checks.
    """
    from app.services.ingestion.cad_source_evidence import plain, signature
    rows=horizontal_schedule_rows(evidence)
    bounds=evidence.get('view_bounds')
    if len(rows)<4 or not bounds:return {'devices':[],'boxes':[]}
    left,bottom,right,top=bounds
    labels={r['id']:r for r in evidence.get('labels',[])}
    def normalized(box):
        return [max(0,(top-box[3])/(top-bottom)*1000),max(0,(box[0]-left)/(right-left)*1000),
                min(1000,(top-box[1])/(top-bottom)*1000),min(1000,(box[2]-left)/(right-left)*1000)]
    devices,boxes=[],[]
    for source in sorted(rows,key=lambda r:labels[r['id']]['y'],reverse=True):
        tag,rating=labels[source['id']],labels[source['rating_id']]
        kind=re.search(r'\b(MCB|MCCB|RCBO|RCCB|ACB)\b',plain(source['rating']))
        numbers=signature(source['rating'])
        if not kind or not tag.get('bounds') or not rating.get('bounds') or len(numbers.get('A',[]))!=1:
            continue
        spec=source['rating'];poles=numbers.get('P',set())
        row={'record_kind':'equipment','category':kind[1],'name':kind[1],'tag':source['tag'],
             'spec':spec,'quantity':1,'drawing_quantity':1,'unit':'Cái','section':'Nhánh ra',
             'in_a':next(iter(numbers['A'])),'poles':2 if re.search(r'1\s*P\s*\+\s*N',spec,re.I) else int(next(iter(poles))) if len(poles)==1 else None,
             'icu_ka':next(iter(numbers['KA'])) if len(numbers.get('KA',[]))==1 else None,
             'location':'Lộ '+source['tag'],'observed_text':spec,
             'source_evidence_ids':[source['id'],source['rating_id']],
             'source_observations':{'extraction_method':'native_cad_schedule'},
             'electrical_function':'Nhánh dự phòng' if plain(source['tag'])=='DP' else 'Đóng cắt và bảo vệ nhánh '+source['tag']}
        text=normalized(rating['bounds']);height=max(4,text[2]-text[0])
        boxes.append({'device_id':str(len(devices)),'verified':True,'symbol_verified':True,
            'text_box_2d':text,'tag_box_2d':normalized(tag['bounds']),
            'symbol_box_2d':[text[2],text[1],min(1000,text[2]+height*2),text[3]],
            'geometry_source':'native_cad_schedule_candidate'})
        devices.append(row)
    return {'devices':devices,'boxes':boxes}


def native_vertical_candidates(path,evidence):
    """Propose tagged branches from native blocks and printed shared headings."""
    from app.services.ingestion.cad_source_evidence import plain
    anchors=[]
    for label in evidence.get('labels',[]):
        box=label.get('bounds');match=re.match(r'^\s*((?:P|L|QF|Q|S|BT)\d+[A-Z]?)\s*[.: -]\s*(.+)$',str(label.get('text') or ''),re.I)
        if match and box and box[3]-box[1]>(box[2]-box[0])*2:anchors.append((label,match[1],match[2]))
    if not anchors or not evidence.get('view_bounds'):return {'devices':[],'boxes':[]}
    anchors.sort(key=lambda item:(item[0]['bounds'][0]+item[0]['bounds'][2])/2)
    import ezdxf
    from ezdxf import bbox
    left,bottom,right,top=evidence['view_bounds'];symbols=[]
    for entity in ezdxf.readfile(path).modelspace().query('INSERT'):
        if not re.search(r'^(?:CB|MCB|MCCB|RCBO|RCCB|BREAKER)(?:$|[_ -])',plain(entity.dxf.name)):continue
        extent=bbox.extents([entity],fast=True)
        if extent.has_data and left<=extent.center.x<=right and bottom<=extent.center.y<=top:
            symbols.append((extent.center.x,extent.center.y,[extent.extmin.x,extent.extmin.y,extent.extmax.x,extent.extmax.y],entity.dxf.handle))
    def normalized(b):return [(top-b[3])/(top-bottom)*1000,(b[0]-left)/(right-left)*1000,
        (top-b[1])/(top-bottom)*1000,(b[2]-left)/(right-left)*1000]
    devices=[];boxes=[]
    for label,tag,load in anchors:
        if sum(t==tag for _,t,_ in anchors)!=1:continue
        lb=label['bounds'];cx=(lb[0]+lb[2])/2
        candidates=sorted((s for s in symbols if s[1]>lb[3]),key=lambda s:abs(s[0]-cx))
        if not candidates or abs(candidates[0][0]-cx)>label['height']*1.5:continue
        if len(candidates)>1 and abs(candidates[1][0]-cx)-abs(candidates[0][0]-cx)<label['height']*.2:continue
        symbol=candidates[0];identity=str(len(devices))
        devices.append({'name':'CB','category':'MCB','tag':tag,'connected_load':load,'spec':'',
            'quantity':1,'drawing_quantity':1,'unit':'Cái','record_kind':'equipment','location':'Lộ '+tag,
            'source_evidence_ids':[label['id'],'cad_entity_'+symbol[3]],
            'source_observations':{'extraction_method':'native_vertical_branch_candidate'},
            'electrical_function':'Đóng cắt và bảo vệ nhánh '+tag})
        boxes.append({'device_id':identity,'symbol_box_2d':normalized(symbol[2]),
            'tag_box_2d':normalized(lb),'load_box_2d':normalized(lb),'load_label':label['text'],
            'relationship_evidence':'Mã lộ và tải nằm trên cột dây của block CB gốc; cần kiểm ảnh độc lập.',
            'geometry_source':'native_vertical_branch_candidate'})
    part={'devices':devices,'boxes':boxes}
    propose_vertical_ratings(evidence,[part])
    retained=[];result=[]
    for i,row in enumerate(devices):
        if not (row.get('source_observations') or {}).get('native_heading_candidate'):continue
        row['name']=row['category'];retained.append(row)
        result.append({**boxes[i],'device_id':str(len(retained)-1),'verified':True,'symbol_verified':True})
    return {'devices':retained,'boxes':result}


def merge_vertical_candidates(parts,regions,candidates):
    """Replace supported source branches and add any omitted native branch."""
    from app.services.ingestion.cad_source_evidence import plain
    by_tag={row['tag']:(row,box) for row,box in zip(candidates['devices'],candidates['boxes'])}
    assigned=set()
    def owner(tag,box):
        explicit=[i for i,r in enumerate(regions) if tag in (r.get('native_branch_tags') or [])]
        if explicit:return explicit[0]
        b=box['load_box_2d'];y,x=(b[0]+b[2])/2,(b[1]+b[3])/2
        matches=[i for i,r in enumerate(regions) if r['box_2d'][0]<=y<=r['box_2d'][2] and r['box_2d'][1]<=x<=r['box_2d'][3]]
        return min(matches,key=lambda i:(regions[i]['box_2d'][2]-regions[i]['box_2d'][0])*(regions[i]['box_2d'][3]-regions[i]['box_2d'][1])) if matches else None
    for pi,part in enumerate(parts):
        old_boxes={str(b.get('device_id')):b for b in part['boxes']};rows=[];boxes=[]
        for ri,row in enumerate(part['devices']):
            tag=row.get('tag');proposal=old_boxes.get(str(ri))
            breaker = row.get('category') in {'MCB','MCCB','RCBO','RCCB','ACB'}
            load = str(row.get('connected_load') or '')
            prefix = re.match(r'^([A-Z]+\d+[A-Z]?)(?:\s*[.:–-]\s*|\s+)(.+)$', load.strip(), re.I)
            if prefix and prefix[1].upper() in by_tag:
                candidate = by_tag[prefix[1].upper()][0]
                if plain(prefix[2]).strip() == plain(candidate.get('connected_load') or '').strip():
                    row = {**row, 'connected_load': candidate['connected_load']}
                    if breaker and not tag:
                        tag = candidate['tag']
            if breaker and tag in by_tag:
                if tag in assigned:continue
                native,source_box=by_tag[tag]
                row={**row,**native,'source_observations':{**(row.get('source_observations') or {}),**native['source_observations']}}
                proposal=dict(source_box);assigned.add(tag)
            elif breaker and proposal and proposal.get('symbol_box_2d'):
                b=proposal['symbol_box_2d']
                def covered(native_box):
                    n=native_box['symbol_box_2d'];area=(n[2]-n[0])*(n[3]-n[1])
                    overlap=max(0,min(b[2],n[2])-max(b[0],n[0]))*max(0,min(b[3],n[3])-max(b[1],n[1]))
                    return area>0 and overlap/area>=.65
                if any(covered(box) for _,box in by_tag.values()):continue
            identity=str(len(rows));rows.append(row)
            if proposal:boxes.append({**proposal,'device_id':identity})
        part.update(devices=rows,boxes=boxes)
    for tag,(row,box) in by_tag.items():
        if tag in assigned:continue
        pi=owner(tag,box)
        if pi is None:continue
        identity=str(len(parts[pi]['devices']));parts[pi]['devices'].append(dict(row))
        parts[pi]['boxes'].append({**box,'device_id':identity})

def bind_horizontal_rows(evidence, devices, proposals):
    """Bind a rating to one native table row and merge overlap reads of that row.

    Repeated DP tags at different CAD labels remain distinct. A matching rating
    alone is insufficient: its text crop must overlap that exact native label.
    """
    from app.services.ingestion.cad_source_evidence import plain, signature
    bounds = evidence.get('view_bounds')
    if not bounds:
        return devices, proposals
    left, bottom, right, top = bounds
    labels = {r['id']:r for r in evidence.get('labels', [])}
    by_id = {}
    for box in proposals:
        by_id.setdefault(str(box.get('device_id')), []).append(box)
    seen, result, boxes = set(), [], []
    for index, device in enumerate(devices):
        candidates = by_id.get(str(index), [])
        matches = []
        if len(candidates) == 1 and device.get('category') in {'MCB','MCCB','RCBO','RCCB','ACB'}:
            text_box = candidates[0].get('text_box_2d') or candidates[0].get('symbol_box_2d')
            if text_box:
                for row in evidence.get('rows', []):
                    tag, rating = labels.get(row['id']), labels.get(row['rating_id'])
                    if not tag or not rating or not rating.get('bounds'):
                        continue
                    if abs(tag['y']-rating['y']) > max(tag['height'], rating['height'])*2:
                        continue
                    if device.get('tag') and plain(device['tag']) != plain(row['tag']):
                        continue
                    if signature(device.get('spec') or '') != signature(row['rating']):
                        continue
                    native = rating['bounds']
                    crop = [left+text_box[1]/1000*(right-left), top-text_box[2]/1000*(top-bottom),
                            left+text_box[3]/1000*(right-left), top-text_box[0]/1000*(top-bottom)]
                    overlap = min(crop[2], native[2])-max(crop[0], native[0])
                    symbol_box = candidates[0].get('symbol_box_2d')
                    symbol_match = False
                    if symbol_box:
                        sx1, sx2 = left+symbol_box[1]/1000*(right-left), left+symbol_box[3]/1000*(right-left)
                        sy = top-(symbol_box[0]+symbol_box[2])/2000*(top-bottom)
                        symbol_match = min(sx2,native[2]) > max(sx1,native[0]) and 0 <= (native[1]+native[3])/2-sy <= rating['height']*3
                    if (overlap > 0 and abs((crop[1]+crop[3])/2-(native[1]+native[3])/2) <= rating['height']*1.5) or symbol_match:
                        matches.append(row)
        if len(matches) == 1:
            row = matches[0]
            identity = (row['rating_id'], device.get('category'), device.get('quantity',1))
            if identity in seen:
                continue
            seen.add(identity)
            device = {**device, 'tag':row['tag'] or None,
                      'source_evidence_ids':[row['id'],row['rating_id']]}
            if row['tag']:
                device['location']='Lộ '+row['tag']
        new_id = str(len(result))
        result.append(device)
        boxes.extend({**box,'device_id':new_id} for box in candidates)
    return result, boxes

def seed_horizontal_row_boxes(evidence, devices, proposals):
    """Repair text anchors using a unique CAD table row, before the pixel audit.

    Region discovery can cut off the load column. Native label bounds refer to
    the whole selected panel, so a clipped region must not be reused as a label.
    Symbol positions remain proposals and are still independently checked.
    """
    from app.services.ingestion.cad_source_evidence import plain, signature
    bounds = evidence.get('view_bounds')
    if not bounds:
        return proposals
    left, bottom, right, top = bounds
    labels = evidence.get('labels') or []
    by_label = {label['id']: label for label in labels}
    by_id = {str(p.get('device_id')): dict(p) for p in proposals if isinstance(p, dict)}
    def normalized(box):
        return [max(0, (top-box[3])/(top-bottom)*1000), max(0, (box[0]-left)/(right-left)*1000),
                min(1000, (top-box[1])/(top-bottom)*1000), min(1000, (box[2]-left)/(right-left)*1000)]
    for index, device in enumerate(devices):
        proposal = by_id.get(str(index))
        if not proposal or not proposal.get('symbol_box_2d'):
            continue
        ids=set(device.get('source_evidence_ids') or [])
        matches = [row for row in evidence.get('rows', [])
                   if (row['rating_id'] in ids or device.get('tag') and plain(row['tag']) == plain(device['tag']))
                   and signature(row['rating']) == signature(device.get('spec') or '')]
        if len(matches) != 1:
            continue
        row = matches[0]
        tag, rating = by_label.get(row['id']), by_label.get(row['rating_id'])
        if not tag or not rating or not tag.get('bounds') or not rating.get('bounds'):
            continue
        tb = tag['bounds']
        if tb[3]-tb[1] > (tb[2]-tb[0])*2:
            continue  # Vertical circuits use their separate native seeder.
        proposal.update(text_box_2d=normalized(rating['bounds']),verified=True,symbol_verified=True)
        if device.get('tag'):
            proposal['tag_box_2d']=normalized(tb)
        load = device.get('connected_load')
        candidates = [label for label in labels if load and label.get('bounds')
                      and plain(label['text']).strip() == plain(load).strip()
                      and abs(label['y']-tag['y']) <= max(label['height'], tag['height'])*1.5]
        if len(candidates) == 1:
            label = candidates[0]
            proposal.update(load_box_2d=normalized(label['bounds']), load_label=label['text'],
                relationship_evidence='Nhãn tải và nhãn lộ cùng hàng mạch CAD; kiểm lại đường nối trên ảnh nguồn.')
    return list(by_id.values())

def seed_vertical_branch_boxes(path, region, devices, proposals):
    import ezdxf
    from ezdxf import bbox
    from app.services.ingestion.cad_source_evidence import cad_evidence,plain
    evidence=cad_evidence(path,region);left,bottom,right,top=evidence['view_bounds']
    labels=evidence['labels'];doc=ezdxf.readfile(path);symbols=[]
    for entity in doc.modelspace().query('INSERT'):
        if not re.search(r'^(?:CB|MCB|MCCB|RCBO|RCCB|BREAKER)(?:$|[_ -])',plain(entity.dxf.name)):continue
        box=bbox.extents([entity],fast=True)
        if box.has_data and left<=box.center.x<=right and bottom<=box.center.y<=top:
            symbols.append((box.center.x,box.center.y,[box.extmin.x,box.extmin.y,box.extmax.x,box.extmax.y]))
    def normalized(window):
        x1,y1,x2,y2=window
        return [max(0,(top-y2)/(top-bottom)*1000),max(0,(x1-left)/(right-left)*1000),
                min(1000,(top-y1)/(top-bottom)*1000),min(1000,(x2-left)/(right-left)*1000)]
    def union(parts):return [min(p[0] for p in parts),min(p[1] for p in parts),max(p[2] for p in parts),max(p[3] for p in parts)]
    by_id={str(p.get('device_id')):p for p in proposals if isinstance(p,dict)}
    heading_groups={}
    seeded=[]
    for index,device in enumerate(devices):
        kind=str(device.get('category') or '').upper()
        if kind not in {'MCB','MCCB','RCBO','RCCB','ACB'}:continue
        tag=str(device.get('tag') or '').strip();load=plain(device.get('connected_load') or '').strip()
        matching=[r for r in labels if r.get('bounds') and ((tag and re.match(r'^'+re.escape(plain(tag))+r'(?:[. :]|$)',plain(r['text']))) or (load and plain(r['text']).strip()==load))]
        if len(matching)!=1:continue
        label=matching[0];lb=label['bounds']
        if lb[3]-lb[1] <= (lb[2]-lb[0])*2:continue  # This path handles truly vertical source labels only.
        center=(lb[0]+lb[2])/2
        candidates=sorted([s for s in symbols if s[1]>lb[3]],key=lambda s:abs(s[0]-center))
        if not candidates:continue
        symbol=candidates[0]
        if abs(symbol[0]-center)>label['height']*1.5:continue
        if len(candidates)>1 and abs(candidates[1][0]-center)-abs(symbol[0]-center)<label['height']*.2:continue
        headings=[r for r in labels if plain(r['text']).strip()==kind and r['x']<symbol[0]
                  and abs(r['y']-symbol[1])<r['height']*12]
        if not headings:continue
        heading=min(headings,key=lambda r:symbol[0]-r['x'])
        cluster=[r['bounds'] for r in labels if r.get('bounds') and abs(r['x']-heading['x'])<heading['height']*2
                 and heading['y']-heading['height']*6<=r['y']<=heading['y']+heading['height']]
        if not cluster:continue
        entry={**by_id.get(str(index),{}),'device_id':str(index),'verified':True,'symbol_verified':True,
               'symbol_box_2d':normalized(symbol[2]),'text_box_2d':normalized(union(cluster)),
               'load_box_2d':normalized(lb),'load_label':label['text'],
               'relationship_evidence':'Đối chiếu ký hiệu nhánh với đường dây và nhãn CAD '+label['text'],
               'geometry_source':'native_cad_block_and_rotated_text'}
        entry['shared_label'] = not (symbol[2][0] <= heading['x'] <= symbol[2][2])
        heading_groups.setdefault(heading['id'],[]).append(str(index))
        if tag:entry['tag_box_2d']=normalized(lb)
        by_id[str(index)]=entry;seeded.append(str(index))
    # Nearby labels stay separate if their union would include another branch's symbol.
    for identity in seeded:
        by_id[identity]['neighbor_symbol_boxes_2d']=[by_id[peer]['symbol_box_2d'] for peer in seeded if peer!=identity]
    for members in heading_groups.values():
        parts=[by_id[i][k] for i in members for k in ('symbol_box_2d','text_box_2d')]
        # A separate continuous view proves which branches the header spans.
        reference=[min(p[0] for p in parts),min(p[1] for p in parts),max(p[2] for p in parts),max(p[3] for p in parts)]
        for identity in members:
            by_id[identity]['group_reference_box_2d']=reference
    examples=[members for members in heading_groups.values() if len(members)>max(
        (devices[int(i)].get('poles') or 1) for i in members)]
    if examples:
        example=max(examples,key=len)
        comparison=by_id[example[0]]['group_reference_box_2d']
        for members in heading_groups.values():
            if len(members)>1:
                for identity in members:
                    by_id[identity].update(source_annotation='shared_rating',audit_comparison_box_2d=comparison)
    return list(by_id.values())


def seed_control_label_boxes(path, region, devices, proposals, *, evidence=None):
    """Use complete native control rectangles; adjacent functions retain separate crops."""
    import ezdxf
    from app.services.ingestion.cad_source_evidence import cad_evidence,plain
    evidence=evidence or cad_evidence(path,region);left,bottom,right,top=evidence['view_bounds']
    labels=evidence['labels'];rectangles=[]
    for entity in ezdxf.readfile(path).modelspace().query('LWPOLYLINE'):
        if not entity.closed:continue
        points=list(entity.get_points('xy'))
        if len(points)!=4:continue
        xs=[p[0] for p in points];ys=[p[1] for p in points]
        box=[min(xs),min(ys),max(xs),max(ys)]
        if left<=box[0]<box[2]<=right and bottom<=box[1]<box[3]<=top:rectangles.append(box)
    def normalize(b):return [(top-b[3])/(top-bottom)*1000,(b[0]-left)/(right-left)*1000,(top-b[1])/(top-bottom)*1000,(b[2]-left)/(right-left)*1000]
    rows={str(b['device_id']):dict(b) for b in proposals}
    for i,device in enumerate(devices):
        identity=' '.join(str(device.get(k) or '') for k in ('name','category','observed_text'))
        from app.services.ai.motor_starter_context import is_direct_starter_label
        pattern=r'^DOL$' if is_direct_starter_label(device) else r'^CONTACTOR$' if 'CONTACTOR' in plain(identity) else r'^24\s*H$' if re.search(r'24\s*H',identity,re.I) else None
        if not pattern:continue
        matches=[l for l in labels if re.fullmatch(pattern,plain(l['text']).strip()) and l.get('bounds')]
        if len(matches)>1 and pattern==r'^DOL$' and device.get('connected_load'):
            loads=[l for l in labels if plain(l['text']).strip()==plain(device['connected_load']).strip() and l.get('bounds')]
            if len(loads)==1:
                center=(loads[0]['bounds'][0]+loads[0]['bounds'][2])/2
                matches=[l for l in matches if abs((l['bounds'][0]+l['bounds'][2])/2-center)<l['height']*2]
        if len(matches)!=1:continue
        label=matches[0];lb=label['bounds'];cx=(lb[0]+lb[2])/2;cy=(lb[1]+lb[3])/2
        candidates=[b for b in rectangles if b[0]<=cx<=b[2] and b[1]-label['height']*.1<=cy<=b[3]+label['height']*.1 and b[3]-b[1]<label['height']*4]
        if not candidates:continue
        box=min(candidates,key=lambda b:(b[2]-b[0])*(b[3]-b[1]))
        adjacent=[b for b in rectangles if abs(b[1]-box[1])<label['height']*.1 and abs(b[3]-box[3])<label['height']*.1 and min(abs(b[0]-box[2]),abs(b[2]-box[0]))<label['height']*.1]
        union=[min([box[0],lb[0]]+[b[0] for b in adjacent]),min(box[1],lb[1]),max([box[2],lb[2]]+[b[2] for b in adjacent]),max(box[3],lb[3])]
        full=[min(box[0],lb[0]),min(box[1],lb[1]),max(box[2],lb[2]),max(box[3],lb[3])]
        h=full[3]-full[1]
        full=[full[0]-h*.1,full[1]-h*.1,full[2]+h*.25,full[3]+h*.1]
        rows[str(i)]={**rows.get(str(i),{}),'device_id':str(i),'verified':True,'symbol_verified':True,
            'symbol_box_2d':normalize(full),'text_box_2d':normalize(full),
            'group_reference_box_2d':normalize(union),'source_annotation':'adjacent_control_functions' if adjacent else 'native_control_label',
            'geometry_source':'native_cad_control_rectangle', 'cad_control_label_id':label['id'],
            'cad_control_label_text':label['text']}
        if device.get('connected_load'):
            loads=[l for l in labels if l.get('bounds') and
                re.sub(r'^(?:P|L|QF|Q|S|BT)\d+[A-Z]?[. :]+','',plain(l['text'])).strip()==plain(device['connected_load']).strip()]
            if len(loads)==1:
                rows[str(i)].update(load_box_2d=normalize(loads[0]['bounds']),load_label=loads[0]['text'],
                    relationship_evidence='Ô điều khiển và nhãn tải nằm trên cùng cột dây CAD; kiểm lại quan hệ trên ảnh nguồn.')
    return list(rows.values())
