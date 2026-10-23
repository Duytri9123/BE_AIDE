"""Render actual schematic geometry for CAD takeoff, including non-text symbols."""
import re
import unicodedata
from pathlib import Path


def render_schematic_source(file_path):
    import ezdxf
    from ezdxf import bbox
    from ezdxf.addons.drawing.matplotlib import qsave
    from ezdxf.addons.drawing.config import Configuration, ColorPolicy, BackgroundPolicy
    source=Path(file_path)
    output=source.parent/'.cad-analysis'/(source.stem+'-sld-v2.png')
    if output.is_file() and output.stat().st_mtime_ns>=source.stat().st_mtime_ns:
        return str(output)
    drawing=ezdxf.readfile(source)
    def plain(value):
        return ''.join(c for c in unicodedata.normalize('NFD',value.upper().replace('Đ','D')) if not unicodedata.combining(c))
    layers={str(layer.dxf.name) for layer in drawing.layers
            if re.search(r'NGUYEN\s*L[IY]|SINGLE[ _-]*LINE|SCHEMATIC|\bSLD\b',plain(str(layer.dxf.name)))}
    if not layers:
        return None
    schematic=[e for e in drawing.modelspace() if e.dxf.layer in layers]
    bounds=bbox.extents(schematic,fast=True)
    if not bounds.has_data:return None
    left,bottom= bounds.extmin.x,bounds.extmin.y
    right,top= bounds.extmax.x,bounds.extmax.y
    pad=max(right-left,top-bottom)*.02
    left-=pad;bottom-=pad;right+=pad;top+=pad
    def in_region(entity):
        if entity.dxf.layer in layers:return True
        kind=entity.dxftype()
        if kind in {'TEXT','MTEXT','INSERT','ATTRIB'}:
            p=entity.dxf.insert
            return left<=p.x<=right and bottom<=p.y<=top
        if kind in {'CIRCLE','ARC','ELLIPSE'}:
            p=entity.dxf.center
            return left<=p.x<=right and bottom<=p.y<=top
        if kind=='LINE':
            a,b=entity.dxf.start,entity.dxf.end
            return max(a.x,b.x)>=left and min(a.x,b.x)<=right and max(a.y,b.y)>=bottom and min(a.y,b.y)<=top
        if kind=='LWPOLYLINE':
            points=list(entity.get_points('xy'))
            return bool(points) and any(left<=p[0]<=right and bottom<=p[1]<=top for p in points)
        return False
    output.parent.mkdir(parents=True,exist_ok=True)
    qsave(drawing.modelspace(),output,bg='#FFFFFF',fg='#000000',dpi=220,
          config=Configuration(color_policy=ColorPolicy.BLACK,background_policy=BackgroundPolicy.WHITE),
          size_inches=(18,13),filter_func=in_region)
    return str(output)
