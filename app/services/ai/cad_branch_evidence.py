"""Seed evidence proposals from explicit vertical CAD branch labels and breaker blocks.
Native coordinates are proposals only: the exported pixels still require visual audit.
"""
import re

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
    return list(by_id.values())


def seed_control_label_boxes(path, region, devices, proposals):
    """Use complete native control rectangles; adjacent functions retain separate crops."""
    import ezdxf
    from app.services.ingestion.cad_source_evidence import cad_evidence,plain
    evidence=cad_evidence(path,region);left,bottom,right,top=evidence['view_bounds']
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
        pattern=r'^CONTACTOR$' if 'CONTACTOR' in plain(identity) else r'^24\s*H$' if re.search(r'24\s*H',identity,re.I) else None
        if not pattern:continue
        matches=[l for l in labels if re.fullmatch(pattern,plain(l['text']).strip()) and l.get('bounds')]
        if len(matches)!=1:continue
        label=matches[0];lb=label['bounds'];cx=(lb[0]+lb[2])/2;cy=(lb[1]+lb[3])/2
        candidates=[b for b in rectangles if b[0]<=cx<=b[2] and b[1]-label['height']*.1<=cy<=b[3]+label['height']*.1 and b[3]-b[1]<label['height']*4]
        if not candidates:continue
        box=min(candidates,key=lambda b:(b[2]-b[0])*(b[3]-b[1]))
        adjacent=[b for b in rectangles if abs(b[1]-box[1])<label['height']*.1 and abs(b[3]-box[3])<label['height']*.1 and min(abs(b[0]-box[2]),abs(b[2]-box[0]))<label['height']*.1]
        union=[min([box[0],lb[0]]+[b[0] for b in adjacent]),min(box[1],lb[1]),max([box[2],lb[2]]+[b[2] for b in adjacent]),max(box[3],lb[3])]
        full=[min(box[0],lb[0]),min(box[1],lb[1]),max(box[2],lb[2]),max(box[3],lb[3])]
        rows[str(i)]={**rows.get(str(i),{}),'device_id':str(i),'verified':True,'symbol_verified':True,
            'symbol_box_2d':normalize(full),'text_box_2d':normalize(full),
            'group_reference_box_2d':normalize(union),'source_annotation':'adjacent_control_functions',
            'geometry_source':'native_cad_control_rectangle'}
    return list(rows.values())
