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
        if tag:entry['tag_box_2d']=normalized(lb)
        by_id[str(index)]=entry;seeded.append(str(index))
    # Nearby labels stay separate if their union would include another branch's symbol.
    for identity in seeded:
        by_id[identity]['neighbor_symbol_boxes_2d']=[by_id[peer]['symbol_box_2d'] for peer in seeded if peer!=identity]
    return list(by_id.values())
