"""Audit source drawing occurrences with actual visible geometry and native states."""
from pathlib import Path
import json
from functools import lru_cache
import ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.recorder import Recorder


def visible_occurrences(dxf_path, native_rows):
    doc=ezdxf.readfile(dxf_path)
    if doc.units!=4:raise ValueError('Source CAD units must be millimetres')
    context=RenderContext(doc);native={r['handle'].upper():r for r in native_rows};result=[]
    for entity in doc.modelspace().query('INSERT'):
        record=native.get(entity.dxf.handle.upper())
        if not record:continue
        recorder=Recorder();front=Frontend(context,recorder)
        front.draw_entities([entity]);bounds=recorder.player().bbox()
        row={**record,'visible_bounds_mm':([bounds.extmin.x,bounds.extmin.y,bounds.extmax.x,bounds.extmax.y] if bounds.has_data else None),
             'raw_bounds_are_mounting_envelope':False,'insertion_point_is_body_corner':False}
        result.append(row)
    return result


def physical_occurrences(rows, categories):
    """Projection state is not an additional physical device or a verified SKU."""
    result=[]
    for row in rows:
        name=row['effective_name'];category=categories.get(name)
        if not category:continue
        if row.get('owner_face')!='mounting_plate':continue
        # A sideways-mounted supply can use a side CAD on the equipment face.
        # Ownership establishes physical counting; the word SIDE alone cannot.
        result.append({**row,'category':category,'exact_model_verified':False})
    return result
