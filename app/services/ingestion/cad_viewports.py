"""Conservative CAD block bounds and source sheet windows; never infer devices."""
import re
from ezdxf import bbox
from ezdxf.math import BoundingBox

def overlapping_entities(doc, window):
    """Cache block-local bounds before transforming instances instead of exploding each copy."""
    blocks={};active=set();cache=bbox.Cache()
    def bounds(entity):
        if entity.dxftype()!='INSERT':
            return bbox.extents([entity],fast=True,cache=cache)
        if entity.mcount > 1:
            combined=BoundingBox()
            for instance in entity.multi_insert():
                part=bounds(instance)
                if part is None:return None
                if part.has_data:combined.extend((part.extmin,part.extmax))
            return combined
        name=entity.dxf.name
        if name not in blocks:
            if name in active:return None
            active.add(name)
            block=doc.blocks.get(name)
            box=BoundingBox()
            if block:
                for child in block:
                    part=bounds(child)
                    if part is None:active.remove(name);return None
                    if part.has_data:box.extend((part.extmin,part.extmax))
            blocks[name]=box;active.remove(name)
        box=blocks[name]
        transformed=BoundingBox(entity.matrix44().transform_vertices(box.cube_vertices())) if box.has_data else BoundingBox()
        for attribute in entity.attribs:
            part=bbox.extents([attribute],fast=True,cache=cache)
            if part.has_data:transformed.extend((part.extmin,part.extmax))
        return transformed
    left,bottom,right,top=window
    result=[]
    for entity in doc.modelspace():
        try:box=bounds(entity)
        except (ValueError,TypeError,KeyError,RecursionError):box=None
        # Unknown geometry is retained rather than silently discarded.
        if box is None or (box.has_data and box.extmin.x<=right and box.extmax.x>=left and box.extmin.y<=top and box.extmax.y>=bottom):
            result.append(entity)
    return result

def schematic_sheet_windows(doc, labels, world_bounds):
    from app.services.ingestion.cad_source_evidence import plain,region_normalized
    titles=[r for r in labels if 'SO DO NGUYEN LY' in plain(r['text']) or 'SINGLE LINE' in plain(r['text'])]
    electrical=[r for r in labels if re.match(r'^(?:MCCB|MCB|RCBO|RCCB|ACB)(?:\b|[-])',plain(r['text']).strip())]
    if not titles or not electrical:return []
    rectangles={};candidates=[]
    for insert in doc.modelspace().query('INSERT'):
        name=insert.dxf.name
        if name not in rectangles:
            rectangles[name]=[]
            block=doc.blocks.get(name)
            if block:
                for poly in block.query('LWPOLYLINE'):
                    if not poly.closed or len(poly) not in (4,5) or any(p[0] for p in poly.get_points('b')):continue
                    points=list(poly.get_points('xy'))
                    xs=sorted({round(p[0],6) for p in points});ys=sorted({round(p[1],6) for p in points})
                    if len(xs)==2 and len(ys)==2 and xs[1]>xs[0] and ys[1]>ys[0]:
                        rectangles[name].append([(x,y,0) for x,y in points])
        for rectangle in rectangles[name]:
            box=BoundingBox(insert.matrix44().transform_vertices(rectangle))
            window=[box.extmin.x,box.extmin.y,box.extmax.x,box.extmax.y]
            inside=lambda r:window[0]<=r['x']<=window[2] and window[1]<=r['y']<=window[3]
            if any(inside(t) for t in titles) and any(inside(r) for r in electrical):candidates.append(window)
    chosen=[]
    for title in titles:
        containing=[w for w in candidates if w[0]<=title['x']<=w[2] and w[1]<=title['y']<=w[3]]
        if containing:
            window=min(containing,key=lambda w:(w[2]-w[0])*(w[3]-w[1]))
            if window not in chosen:chosen.append(window)
        else:
            return []  # Never omit a titled schematic that lacks a safe native frame.
    return [region_normalized(world_bounds,w) for w in chosen]
